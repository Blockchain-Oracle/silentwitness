"""One-off bootstrap: create one GitHub issue per story enumerated in sprint-status.yaml.

Reads:
  - docs/sprint-status.yaml  (canonical story list + dependency graph)
  - docs/stories/story-<slug>.md  (BDD criteria, file modification map, etc.)

Writes:
  - One GitHub issue per story with title, body (linked story file + BDD criteria
    excerpt + dependency hints), labels (epic:N + stage:bootstrap / stage:cut /
    stage:optional).
  - sprint-status.yaml in-place: fills `issue_url` for every story it creates.

Idempotency:
  - Skips stories that already have a non-empty `issue_url` in sprint-status.yaml.
  - Search is by exact title prefix `[story-<slug>]` to avoid duplicates if
    something fails mid-run.

Runs the gh CLI in the active auth context. Requires:
  - gh CLI authed with `repo` scope (verify with `gh auth status`)
  - pyyaml in the local venv OR python stdlib only (the loader below is stdlib).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SPRINT_PATH = REPO_ROOT / "docs" / "sprint-status.yaml"
STORIES_DIR = REPO_ROOT / "docs" / "stories"
REPO = "Blockchain-Oracle/silentwitness"


def _parse_sprint_yaml(path: Path) -> tuple[dict, list[dict]]:
    """Hand-rolled minimal YAML parser for our known shape.

    We avoid the PyYAML dependency for a bootstrap script. The sprint-status.yaml
    shape is constrained (top-level scalars + a stories: list of mappings).
    """
    text = path.read_text(encoding="utf-8")
    meta: dict[str, str | int] = {}
    stories: list[dict[str, str | bool | list[str]]] = []
    current: dict | None = None
    in_stories = False
    in_optional_epics = False
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if line.startswith("optional_epics:"):
            in_optional_epics = True
            in_stories = False
            continue
        if line.startswith("stories:"):
            in_stories = True
            in_optional_epics = False
            continue
        if in_optional_epics and line.lstrip().startswith("-"):
            continue
        if not in_stories:
            if ":" in line and not line.startswith(" "):
                k, _, v = line.partition(":")
                meta[k.strip()] = v.strip().strip('"')
            continue
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if indent == 2 and stripped.startswith("- id:"):
            if current is not None:
                stories.append(current)
            current = {"id": stripped[len("- id:") :].strip().strip('"')}
        elif indent == 4 and ":" in stripped and current is not None:
            k, _, v = stripped.partition(":")
            k = k.strip()
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                inner = v[1:-1].strip()
                current[k] = (
                    [item.strip().strip('"') for item in inner.split(",") if item.strip()]
                    if inner
                    else []
                )
            elif v.lower() in {"true", "false"}:
                current[k] = v.lower() == "true"
            else:
                current[k] = v.strip('"')
    if current is not None:
        stories.append(current)
    return meta, stories


def _story_title_and_body(story: dict) -> tuple[str, str]:
    """Pull the story title (first H1) and a body excerpt from the .md file."""
    slug = story["id"][len("story-") :]
    md_path = STORIES_DIR / f"{story['id']}.md"
    if not md_path.exists():
        return slug, f"Story file missing: `{md_path.relative_to(REPO_ROOT)}`"

    text = md_path.read_text(encoding="utf-8")
    h1_match = re.search(r"^# (Story — .+)$", text, re.MULTILINE)
    title = h1_match.group(1) if h1_match else slug

    # Extract sections: User story, File modification map, BDD acceptance criteria.
    sections: dict[str, str] = {}
    for header in ("User story", "File modification map", "Acceptance criteria"):
        pattern = rf"^## {header}.*?\n(.*?)(?=\n## |\Z)"
        m = re.search(pattern, text, re.DOTALL | re.MULTILINE)
        if m:
            sections[header] = m.group(1).strip()

    repo_rel = md_path.relative_to(REPO_ROOT)
    parts = [
        f"**Story file:** [`{repo_rel}`](../blob/main/{repo_rel})",
        "",
        f"**Epic:** {story.get('epic', '(unknown)')}",
        f"**Depends on:** {', '.join(story.get('depends_on') or ['(none)'])}",
    ]
    if story.get("optional"):
        parts.append("**Optional:** yes")
    if story.get("cut"):
        parts.append("**CUT for v1:** yes — DO NOT implement; see DEEP_AUDIT_REPORT.md Decision B.")
    parts.append("")
    if "User story" in sections:
        parts.append("## User story\n")
        parts.append(sections["User story"])
        parts.append("")
    if "Acceptance criteria" in sections:
        parts.append("## Acceptance criteria (BDD)\n")
        # Cap at first ~4000 chars to stay under issue body limits.
        acc = sections["Acceptance criteria"]
        if len(acc) > 4000:
            acc = acc[:4000] + "\n\n*(truncated — see full criteria in the story file)*"
        parts.append(acc)
        parts.append("")
    if "File modification map" in sections:
        parts.append("## File modification map\n")
        fm = sections["File modification map"]
        if len(fm) > 1500:
            fm = fm[:1500] + "\n\n*(truncated — see full map in the story file)*"
        parts.append(fm)
    return title, "\n".join(parts)


def _existing_issue(slug: str) -> str | None:
    """Return URL of an existing issue for this slug, if any."""
    cmd = [
        "gh",
        "issue",
        "list",
        "--repo",
        REPO,
        "--state",
        "all",
        "--search",
        f'"[{slug}]"',
        "--json",
        "number,title,url",
        "--limit",
        "5",
    ]
    out = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if out.returncode != 0:
        return None
    try:
        items = json.loads(out.stdout)
    except json.JSONDecodeError:
        return None
    for item in items:
        if item["title"].startswith(f"[{slug}]"):
            return item["url"]
    return None


def _epic_label(epic_string: str) -> str:
    m = re.match(r"Epic (\d+) —", epic_string)
    return f"epic:{m.group(1)}" if m else "epic:unknown"


def _create_issue(slug: str, title: str, body: str, labels: list[str]) -> str:
    cmd = [
        "gh",
        "issue",
        "create",
        "--repo",
        REPO,
        "--title",
        f"[{slug}] {title}",
        "--body",
        body,
    ]
    for lbl in labels:
        cmd.extend(["--label", lbl])
    out = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if out.returncode != 0:
        # Likely missing label — retry without labels.
        cmd_no_label = [c for c in cmd if c != "--label" and c not in labels]
        out2 = subprocess.run(cmd_no_label, capture_output=True, text=True, check=False)
        if out2.returncode != 0:
            raise RuntimeError(f"gh issue create failed for {slug}:\n{out.stderr}\n{out2.stderr}")
        url = out2.stdout.strip()
        return url
    return out.stdout.strip()


def _ensure_labels() -> None:
    """Best-effort: create the epic + stage labels we'll use."""
    desired = [
        ("epic:1", "Project scaffolding + CI/CD", "0E8A16"),
        ("epic:2", "Common types + audit infra", "1D76DB"),
        ("epic:3", "Verification gates", "5319E7"),
        ("epic:4", "MCP server skeleton", "B60205"),
        ("epic:5", "Memory tools (Vol3)", "D93F0B"),
        ("epic:6", "Disk + Registry tools", "FBCA04"),
        ("epic:7", "Log + Network tools", "0E8A16"),
        ("epic:8", "Hypothesis + investigator", "1D76DB"),
        ("epic:9", "Specialists", "5319E7"),
        ("epic:10", "Critic", "B60205"),
        ("epic:11", "Report-as-state", "D93F0B"),
        ("epic:12", "CLI + Claude Code drop-in", "FBCA04"),
        ("epic:13", "Streaming HUD (optional)", "C5DEF5"),
        ("epic:14", "Accuracy harness", "0E8A16"),
        ("epic:15", "Adversary pair (CUT)", "5C5C5C"),
        ("epic:16", "Documentation + submission", "1D76DB"),
        ("stage:optional", "Optional stretch", "C5DEF5"),
        ("stage:cut", "CUT for v1 — do not implement", "5C5C5C"),
    ]
    for name, desc, color in desired:
        subprocess.run(
            [
                "gh",
                "label",
                "create",
                name,
                "--repo",
                REPO,
                "--description",
                desc,
                "--color",
                color,
            ],
            capture_output=True,
            text=True,
            check=False,
        )


def _write_sprint_with_urls(meta: dict, stories: list[dict]) -> None:
    """Re-render sprint-status.yaml in place with updated issue_url values."""
    text = SPRINT_PATH.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    out_lines: list[str] = []
    current_id: str | None = None
    story_by_id = {s["id"]: s for s in stories}
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- id:"):
            current_id = stripped[len("- id:") :].strip().strip('"')
            out_lines.append(line)
            continue
        if current_id and stripped.startswith("issue_url:"):
            new_url = story_by_id.get(current_id, {}).get("issue_url", "")
            indent = line[: len(line) - len(line.lstrip())]
            out_lines.append(f'{indent}issue_url: "{new_url}"\n')
            continue
        out_lines.append(line)
    SPRINT_PATH.write_text("".join(out_lines), encoding="utf-8")


def main() -> int:
    meta, stories = _parse_sprint_yaml(SPRINT_PATH)
    print(f"Loaded {len(stories)} stories from sprint-status.yaml")
    _ensure_labels()
    created = 0
    skipped = 0
    failed: list[str] = []
    for story in stories:
        slug = story["id"][len("story-") :]
        if story.get("issue_url"):
            print(f"  ✓ skip (already has url): {slug}")
            skipped += 1
            continue
        existing = _existing_issue(slug)
        if existing:
            story["issue_url"] = existing
            print(f"  ✓ found existing: {slug} → {existing}")
            skipped += 1
            continue
        title, body = _story_title_and_body(story)
        labels = [_epic_label(str(story.get("epic", "")))]
        if story.get("optional"):
            labels.append("stage:optional")
        if story.get("cut"):
            labels.append("stage:cut")
        try:
            url = _create_issue(slug, title, body, labels)
            story["issue_url"] = url
            created += 1
            print(f"  + created: {slug} → {url}")
        except RuntimeError as exc:
            failed.append(slug)
            print(f"  ✗ FAILED: {slug}: {exc}", file=sys.stderr)
    _write_sprint_with_urls(meta, stories)
    print(f"\nResult: {created} created, {skipped} skipped, {len(failed)} failed.")
    if failed:
        print("Failed slugs: " + ", ".join(failed), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
