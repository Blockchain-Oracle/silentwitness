"""Entity gate — NER + regex catalog + cited-span presence check (architecture §4.7).

The citation gate's complement. Where the citation gate proves "the bytes
the agent claims to have read exist and contain the claimed substring,"
the entity gate proves "every DFIR-relevant entity (IPs, hashes, paths,
registry keys, accounts) the agent names in the observation text actually
appears in at least one cited span." Together they close the
closed-domain hallucination surface: the citation gate prevents fabricated
quotes, the entity gate prevents fabricated entities (a path the tool
never emitted, a hash the agent invented).

Five steps (architecture §4.7), applied in order:

  1. **Extract regex entities** from ``observation_text`` using the
     ordered :data:`REGEX_RULES` catalog. Earlier rules consume their
     match spans so later rules don't double-extract (SHA-256's 64-hex
     match wins over SHA-1's 40-hex prefix; URLs win over POSIX paths).
  2. **Extract NER entities** via spaCy ``en_core_web_lg``, filtering to
     the architecture-listed kinds (PERSON / ORG / GPE / PRODUCT /
     WORK_OF_ART). spaCy is lazy-loaded at first call.
  3. **Concatenate cited bytes** — join every ``CitedSpan.span_text``
     into one searchable corpus.
  4. **Check presence** for each extracted entity. Path-typed entities
     (Windows / POSIX / Registry) are normalised (lowercase + forward-
     slash) on both sides before substring comparison so cited
     ``"C:\\Program Files\\Ethereal\\"`` matches observation
     ``"c:/program files/ethereal/"``. Non-path entities use
     case-insensitive direct substring.
  5. **Return** :class:`EntityResult` — ``success=True`` iff every
     extracted entity was found; otherwise ``success=False`` with the
     ``hallucinated`` list naming the entities the agent claimed but
     the evidence doesn't carry.

spaCy load cost: ~3 s + ~750 MB on first invocation. The model is
cached at module level via :func:`_get_nlp` so subsequent calls in the
same process are free. Not safe for fork-multiprocessing without
re-initialisation; the MCP server is single-process anyway.

The gate is pure: same inputs → same outputs. No global state mutation
beyond the spaCy cache (which is monotonic — never invalidated within a
process).
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from silentwitness_common.types import CitedSpan
from silentwitness_mcp.verification._entity_patterns import (
    REGEX_RULES,
    SPACY_NER_KINDS,
    EntityKind,
)

_BASE_CONFIG = ConfigDict(frozen=True, extra="forbid")
_PATH_KINDS: frozenset[EntityKind] = frozenset(
    {EntityKind.WINDOWS_PATH, EntityKind.POSIX_PATH, EntityKind.REGISTRY_KEY}
)


# ---------------------------------------------------------------------------
# Pydantic contracts
# ---------------------------------------------------------------------------


class ExtractedEntity(BaseModel):
    """A single entity extracted from observation text (architecture §4.7)."""

    model_config = _BASE_CONFIG

    text: str = Field(min_length=1)
    kind: EntityKind
    source: str = Field(pattern=r"^(spacy|regex)$")


class EntityResult(BaseModel):
    """Tagged-union result of :func:`verify_entities`.

    ``success=True`` ⇒ ``hallucinated`` is empty; the observation's named
    entities all appear in the cited evidence. ``success=False`` ⇒
    ``reason`` names the failure (currently only ``HALLUCINATED_ENTITIES``)
    and ``hallucinated`` lists the entities the agent claimed but the
    evidence doesn't carry.
    """

    model_config = _BASE_CONFIG

    success: bool
    extracted: tuple[ExtractedEntity, ...]
    hallucinated: tuple[ExtractedEntity, ...]
    reason: str | None = None

    @model_validator(mode="after")
    def _check_tag(self) -> EntityResult:
        if self.success:
            if self.hallucinated:
                raise ValueError("EntityResult.success=True must have empty hallucinated")
            if self.reason is not None:
                raise ValueError("EntityResult.success=True must not carry reason")
        else:
            if not self.hallucinated:
                raise ValueError("EntityResult.success=False requires non-empty hallucinated")
            if self.reason != "HALLUCINATED_ENTITIES":
                raise ValueError(
                    "EntityResult.success=False requires reason='HALLUCINATED_ENTITIES'"
                )
        return self


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


_nlp_cache: Any = None  # spacy.Language at runtime; Any to avoid import at type-check
_NLP_LOAD_FAILED: object = object()  # sentinel — distinguishes "tried + failed" from "untried"


class EntityGateModelError(RuntimeError):
    """Raised when the spaCy ``en_core_web_lg`` model required by the gate
    is not installed. Wraps the underlying ``OSError`` with an actionable
    install command so operators see context, not a raw spaCy traceback
    (PR-112 silent-failure HIGH-9).
    """


def _get_nlp() -> Any:
    """Lazy-load and cache spaCy ``en_core_web_lg``. First call: ~3 s + 750 MB.

    Raises :class:`EntityGateModelError` if the model isn't installed. The
    CI workflow ``ci.yml`` includes a ``python -m spacy download en_core_web_lg``
    step before running gate tests. PR-112 code-reviewer #5 — once a load
    attempt fails we cache the failure sentinel so subsequent calls
    re-raise immediately instead of retrying the (expensive) filesystem
    scan from scratch.
    """
    global _nlp_cache
    if _nlp_cache is _NLP_LOAD_FAILED:
        raise EntityGateModelError(
            "spaCy en_core_web_lg model unavailable — install via "
            "`uv run python -m spacy download en_core_web_lg`"
        )
    if _nlp_cache is None:
        import spacy as _spacy

        try:
            _nlp_cache = _spacy.load("en_core_web_lg")
        except OSError as exc:
            _nlp_cache = _NLP_LOAD_FAILED
            raise EntityGateModelError(
                "Entity gate requires spaCy model 'en_core_web_lg' (~750 MB). "
                "Install via: uv run python -m spacy download en_core_web_lg. "
                f"Underlying spaCy error: {exc}"
            ) from exc
    return _nlp_cache


def verify_entities(observation_text: str, cited_spans: Sequence[CitedSpan]) -> EntityResult:
    """Run the five-step entity-gate algorithm. See module docstring."""
    extracted = tuple(_extract_all_entities(observation_text))
    corpus = _build_cited_corpus(cited_spans)
    hallucinated = tuple(e for e in extracted if not _entity_in_corpus(e, corpus))
    if hallucinated:
        return EntityResult(
            success=False,
            extracted=extracted,
            hallucinated=hallucinated,
            reason="HALLUCINATED_ENTITIES",
        )
    return EntityResult(success=True, extracted=extracted, hallucinated=())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_all_entities(text: str) -> list[ExtractedEntity]:
    """Regex catalog first (with span-consumption), then spaCy NER on the
    residual — so spaCy doesn't double-classify a hash as a PRODUCT.
    """
    consumed: list[tuple[int, int]] = []
    out: list[ExtractedEntity] = []
    for rule in REGEX_RULES:
        for match in rule.pattern.finditer(text):
            span = (match.start(), match.end())
            if _overlaps(span, consumed):
                continue
            consumed.append(span)
            captured = match.group(1) if rule.pattern.groups >= 1 else match.group(0)
            out.append(ExtractedEntity(text=captured, kind=rule.kind, source="regex"))
    out.extend(_extract_spacy_entities(text, consumed))
    return _dedupe(out)


def _extract_spacy_entities(text: str, consumed: list[tuple[int, int]]) -> list[ExtractedEntity]:
    nlp = _get_nlp()
    doc = nlp(text)
    out: list[ExtractedEntity] = []
    for ent in doc.ents:
        label = ent.label_
        try:
            kind = EntityKind(label)
        except ValueError:
            continue
        if kind not in SPACY_NER_KINDS:
            continue
        if _overlaps((ent.start_char, ent.end_char), consumed):
            continue
        out.append(ExtractedEntity(text=ent.text, kind=kind, source="spacy"))
    return out


def _overlaps(span: tuple[int, int], consumed: list[tuple[int, int]]) -> bool:
    s, e = span
    return any(not (e <= cs or s >= ce) for cs, ce in consumed)


def _dedupe(entities: list[ExtractedEntity]) -> list[ExtractedEntity]:
    seen: set[tuple[str, EntityKind]] = set()
    out: list[ExtractedEntity] = []
    for entity in entities:
        key = (entity.text.casefold(), entity.kind)
        if key in seen:
            continue
        seen.add(key)
        out.append(entity)
    return out


def _build_cited_corpus(cited_spans: Sequence[CitedSpan]) -> str:
    return "\n".join(span.span_text for span in cited_spans)


def _entity_in_corpus(entity: ExtractedEntity, corpus: str) -> bool:
    """Anchored substring check (PR-112 silent-failure CRITICAL-3).

    The previous ``entity.text in corpus`` permitted ``10.0.0.1`` in
    observation to match ``10.0.0.10`` in corpus — a false-positive
    acceptance because pure substring containment doesn't enforce token
    equality. Now use a regex with non-word-char boundaries on either
    side so ``10.0.0.1`` only matches when surrounded by whitespace,
    punctuation, or end-of-string.

    Path entities are still pre-normalised (case-fold + backslash →
    forward-slash) before the boundary check.
    """
    needle = entity.text
    haystack = corpus
    if entity.kind in _PATH_KINDS:
        needle = _path_normalise(needle)
        haystack = _path_normalise(haystack)
    else:
        needle = needle.casefold()
        haystack = haystack.casefold()
    # ``(?<!\w)`` / ``(?!\w)`` are non-word boundaries — exactly what we
    # want for IPs, hashes, accounts, ports, etc. that may contain dots,
    # slashes, or backslashes (none of which are ``\w``).
    pattern = re.compile(r"(?<!\w)" + re.escape(needle) + r"(?!\w)")
    return pattern.search(haystack) is not None


def _path_normalise(text: str) -> str:
    return text.replace("\\", "/").casefold()


__all__ = [
    "EntityGateModelError",
    "EntityKind",
    "EntityResult",
    "ExtractedEntity",
    "verify_entities",
]
