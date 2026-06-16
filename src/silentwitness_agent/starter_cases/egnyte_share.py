"""Egnyte public-share API client used by `starter-cases` downloads.

Split out from the CLI driver so each file fits the 400-LOC architecture
gate and the API surface can be tested in isolation.

Egnyte API (undocumented but stable, mirrors the browser UI's calls):

1. ``GET /fl/{token}`` — open the public-link session (sets share cookie
   + CSRF token; required before any subsequent POST).
2. ``POST /rest/public/1.0/links/info/{token}/contents`` — paginated
   folder listing. Body: ``{path, limit, offset, sortBy, sortDirection,
   _method, pageNumber}``.
3. ``GET /dd/{token}/?entryId={entry_id}`` — stream one file's bytes.
   ``entry_id`` is the share-scoped ``entryId`` (NOT the permanent
   ``id``; the two are different UUIDs).

Quality contract: httpx (project standard); HTTP retry on
5xx/408/429/TransportError; Range resume from ``<file>.part`` on restart;
SHA256 sidecar per file (verified on skip); ProtocolError on captive-portal
/ rate-limit / schema-drift / duplicate-entry pagination; strict entry_id
(no silent fallback to permanent id). See PR #238 silent-failure review.
"""

from __future__ import annotations

import hashlib
import sys
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import httpx
except ImportError:  # pragma: no cover — install bootstrap
    print(
        "scripts/egnyte_share.py needs the `httpx` package.\n"
        "Install it with: `uv sync` (it's in pyproject.toml) "
        "or `pip install 'httpx>=0.27'`.",
        file=sys.stderr,
    )
    sys.exit(2)

SHARE_TOKEN = "HhH7crTYT4JK"  # noqa: S105 — public share token, not a secret
SHARE_BASE = "https://sansorg.egnyte.com"
SHARE_URL = f"{SHARE_BASE}/fl/{SHARE_TOKEN}"
ROOT_PATH = "/HACKATHON-2026"
CONTENTS_URL = f"{SHARE_BASE}/rest/public/1.0/links/info/{SHARE_TOKEN}/contents"
DOWNLOAD_URL = f"{SHARE_BASE}/dd/{SHARE_TOKEN}/"
PAGE_LIMIT = 48
CHUNK_BYTES = 1 << 20  # 1 MiB
MAX_RETRIES = 5
BACKOFF_BASE_SECONDS = 2.0
USER_AGENT = "silentwitness-egnyte/1.1 (+https://github.com/Blockchain-Oracle/silentwitness)"
SESSION_TIMEOUT = httpx.Timeout(30.0, read=600.0)


class ProtocolError(RuntimeError):
    """Raised when the Egnyte API returns a response shape we don't recognise
    (captive-portal HTML, missing envelope, duplicate-paged entries, etc.).
    Without this guard, Egnyte's 200+HTML rate-limit page would parse as an
    empty listing and we'd silently report "0 files" to the user."""


class ChecksumMismatchError(RuntimeError):
    """Raised when a previously-downloaded file's SHA256 sidecar disagrees
    with the bytes on disk. Silent corruption is the worst case for evidence
    integrity; better to re-download than to ship a tainted artefact."""


def _is_transient_status(status_code: int) -> bool:
    return status_code in (408, 429) or 500 <= status_code < 600


@dataclass(frozen=True)
class Entry:
    """One share item — file or folder. ``path`` begins with the share root;
    ``entry_id`` is the share-scoped Egnyte ``entryId`` (file-only — folders
    carry only ``id``, which is never used in download URLs)."""

    path: str
    name: str
    type: str  # "folder" or "file"
    size: int | None
    last_modified: int | None
    entry_id: str | None  # None for folders; required for files


def open_session() -> httpx.Client:
    """Open the public-link session.

    GETs the share page first so Egnyte sets the share session cookie +
    CSRF; asserts the response is HTML containing the share token before we
    trust the cookies. Captive-portal / rate-limit pages return 200+HTML
    without the token and we fail loudly rather than continue with an
    unauthenticated session that returns empty listings."""
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json, text/plain, */*"}
    client = httpx.Client(
        headers=headers,
        timeout=SESSION_TIMEOUT,
        follow_redirects=True,
        http2=False,  # Egnyte's TLS hangs on h2 negotiation from python httpx
    )
    r = client.get(SHARE_URL)
    r.raise_for_status()
    if "text/html" not in r.headers.get("Content-Type", ""):
        client.close()
        raise ProtocolError("share page did not return HTML; may be rate-limited or expired")
    if SHARE_TOKEN not in r.text:
        client.close()
        raise ProtocolError("share page HTML missing share token; Egnyte redirected somewhere")
    return client


def request_with_retry(
    client: httpx.Client, method: str, url: str, **kwargs: Any
) -> httpx.Response:
    """Issue an HTTP request with exponential backoff on transient failures.

    Retries on 5xx, 408 (Request Timeout), 429 (Too Many Requests), and on
    ``httpx.TransportError`` (DNS / TCP / TLS / read-timeout). Non-transient
    failures (4xx other than 408/429) propagate immediately — a 404 should
    not be retried."""
    last_exc: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            r = client.request(method, url, **kwargs)
            if _is_transient_status(r.status_code):
                wait = BACKOFF_BASE_SECONDS * (2**attempt)
                print(
                    f"  retry {attempt + 1}/{MAX_RETRIES} HTTP {r.status_code} on {url} "
                    f"(sleep {wait:.1f}s)",
                    file=sys.stderr,
                )
                time.sleep(wait)
                continue
            return r
        except httpx.TransportError as exc:
            last_exc = exc
            wait = BACKOFF_BASE_SECONDS * (2**attempt)
            print(
                f"  retry {attempt + 1}/{MAX_RETRIES} after {type(exc).__name__}: {exc} "
                f"(sleep {wait:.1f}s)",
                file=sys.stderr,
            )
            time.sleep(wait)
    raise RuntimeError(
        f"giving up after {MAX_RETRIES} retries on {method} {url}; last error: {last_exc!r}"
    )


def list_contents(client: httpx.Client, path: str) -> Iterator[Entry]:
    """Enumerate one folder, paginating until exhausted.

    Guards: non-JSON response → ProtocolError; missing ``contents`` envelope
    → ProtocolError; duplicate entries across pages → ProtocolError."""
    seen: set[str] = set()
    page = 1
    offset = 0
    while True:
        body = {
            "limit": PAGE_LIMIT,
            "offset": offset,
            "sortBy": "name",
            "sortDirection": "ASC",
            "_method": "GET",
            "path": path,
            "pageNumber": page,
        }
        r = request_with_retry(client, "POST", CONTENTS_URL, json=body)
        r.raise_for_status()
        if "application/json" not in r.headers.get("Content-Type", ""):
            raise ProtocolError(
                f"listing for {path!r} returned non-JSON; share may be rate-limited"
            )
        try:
            payload = r.json()
        except ValueError as exc:
            raise ProtocolError(f"listing for {path!r} returned malformed JSON") from exc
        if not isinstance(payload, dict) or "contents" not in payload:
            keys = sorted(payload)[:5] if isinstance(payload, dict) else type(payload).__name__
            raise ProtocolError(f"listing for {path!r} missing `contents` envelope; got {keys}")
        contents = payload["contents"]
        results = contents.get("results")
        if results is None:
            raise ProtocolError(f"listing for {path!r} missing `contents.results`; schema drift?")
        if not results:
            return
        for raw in results:
            entry_type = raw["type"]
            # Files MUST carry entryId. Folders MAY carry only `id`. Mixing the
            # two produces 404s downstream (PR #238 round-1 bug).
            entry_id = raw.get("entryId")
            if entry_type == "file" and not entry_id:
                raise ProtocolError(
                    f"file entry {raw.get('name')!r} at {raw.get('path')!r} "
                    "is missing `entryId` field; cannot construct download URL."
                )
            path_str = raw["path"]
            if path_str in seen:
                raise ProtocolError(
                    f"duplicate entry {path_str!r} across page {page} — pagination loop"
                )
            seen.add(path_str)
            yield Entry(
                path=path_str,
                name=raw["name"],
                type=entry_type,
                size=raw.get("size"),
                last_modified=raw.get("lastModified"),
                entry_id=entry_id,
            )
        total = contents.get("totalFileCount", 0) + contents.get("totalFolderCount", 0)
        offset += len(results)
        page += 1
        if offset >= total:
            return


def walk(client: httpx.Client, root: str) -> Iterator[Entry]:
    """Depth-first walk under ``root`` (a folder path). Yields files only;
    folders are descended silently. Pagination's duplicate-detect guards
    against any runaway recursion."""
    for entry in list_contents(client, root):
        if entry.type == "folder":
            yield from walk(client, entry.path)
        else:
            yield entry


def human_size(n: int | None) -> str:
    if n is None:
        return "—"
    if n < 1024:
        return f"{n} B"
    if n < 1024**2:
        return f"{n / 1024:.1f} KiB"
    if n < 1024**3:
        return f"{n / 1024**2:.1f} MiB"
    return f"{n / 1024**3:.2f} GiB"


def _sha256_of_file(path: Path) -> str:
    """SHA256 of an on-disk file via 1 MiB chunks."""
    sha = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(CHUNK_BYTES)
            if not chunk:
                break
            sha.update(chunk)
    return sha.hexdigest()


def verify_sidecar(target: Path) -> bool:
    """True iff ``<target>.sha256`` exists AND matches the current bytes."""
    sidecar = target.with_suffix(target.suffix + ".sha256")
    if not sidecar.exists():
        return False
    expected = sidecar.read_text(encoding="utf-8").strip().split()[0]
    return expected == _sha256_of_file(target)


def stream_file(
    client: httpx.Client,
    entry: Entry,
    target: Path,
    progress: Callable[[int, int | None], None] | None = None,
) -> str:
    """Download one file to ``target`` with Range resume + SHA verify.

    Resume: ``<target>.part`` size → ``Range: bytes=N-``. Server-ignored-
    Range (200 instead of 206) restarts cleanly with a loud RESTART line.
    On success: writes ``<target>.sha256`` sidecar then atomically renames
    ``.part`` → ``target``.

    Raises ``ProtocolError`` if entry has no entry_id (folder),
    ``ChecksumMismatchError`` on final-size disagreement with Egnyte's
    advertised size, or ``RuntimeError`` after MAX_RETRIES exhausted."""
    if entry.entry_id is None:
        raise ProtocolError(f"cannot download {entry.name!r}: no entryId (folder)")
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".part")
    url = f"{DOWNLOAD_URL}?entryId={entry.entry_id}"
    last_exc: Exception | None = None
    for attempt in range(MAX_RETRIES):
        resume_from = tmp.stat().st_size if tmp.exists() else 0
        sha = hashlib.sha256()
        headers: dict[str, str] = {}
        mode = "wb"
        if resume_from > 0:
            with tmp.open("rb") as fh:
                while chunk := fh.read(CHUNK_BYTES):
                    sha.update(chunk)
            print(f"  RESUME {human_size(resume_from):>10}  {target}", file=sys.stderr)
            headers = {"Range": f"bytes={resume_from}-"}
            mode = "ab"
        try:
            with client.stream("GET", url, headers=headers) as r:
                if _is_transient_status(r.status_code):
                    wait = BACKOFF_BASE_SECONDS * (2**attempt)
                    print(
                        f"  retry {attempt + 1}/{MAX_RETRIES} HTTP {r.status_code} on {url} "
                        f"(sleep {wait:.1f}s)",
                        file=sys.stderr,
                    )
                    time.sleep(wait)
                    continue
                r.raise_for_status()
                if resume_from > 0 and r.status_code == 200:
                    print(
                        f"  RESTART {human_size(resume_from):>10}  {target} (server ignored Range)",
                        file=sys.stderr,
                    )
                    tmp.unlink(missing_ok=True)
                    continue
                written = resume_from
                if progress:
                    progress(written, entry.size)
                with tmp.open(mode) as fh:
                    for chunk in r.iter_bytes(chunk_size=CHUNK_BYTES):
                        if not chunk:
                            continue
                        fh.write(chunk)
                        sha.update(chunk)
                        written += len(chunk)
                        if progress:
                            progress(written, entry.size)
            break
        except httpx.TransportError as exc:
            last_exc = exc
            wait = BACKOFF_BASE_SECONDS * (2**attempt)
            print(
                f"  retry {attempt + 1}/{MAX_RETRIES} after {type(exc).__name__}: {exc} "
                f"(sleep {wait:.1f}s)",
                file=sys.stderr,
            )
            time.sleep(wait)
    else:
        raise RuntimeError(
            f"giving up after {MAX_RETRIES} retries on GET {url}; last error: {last_exc!r}"
        )
    final_size = tmp.stat().st_size
    if entry.size is not None and final_size != entry.size:
        raise ChecksumMismatchError(
            f"size mismatch on {target}: got {final_size} bytes, Egnyte said {entry.size}"
        )
    digest = sha.hexdigest()
    sidecar = target.with_suffix(target.suffix + ".sha256")
    sidecar.write_text(f"{digest}  {target.name}\n", encoding="utf-8")
    tmp.replace(target)
    return digest


def resolve_case_root(client: httpx.Client, case_name: str | None) -> str:
    """Map a user-friendly case label to the share path. ``None`` or empty
    ``case_name`` returns the share root."""
    if not case_name:
        return ROOT_PATH
    for entry in list_contents(client, ROOT_PATH):
        if entry.type == "folder" and entry.name == case_name:
            return entry.path
    raise SystemExit(
        f"case {case_name!r} not found at share root. "
        "Run `silentwitness starter-cases catalog` to see what's available."
    )


__all__ = [
    "CHUNK_BYTES",
    "PAGE_LIMIT",
    "ROOT_PATH",
    "SHARE_TOKEN",
    "ChecksumMismatchError",
    "Entry",
    "ProtocolError",
    "human_size",
    "list_contents",
    "open_session",
    "request_with_retry",
    "resolve_case_root",
    "stream_file",
    "verify_sidecar",
    "walk",
]
