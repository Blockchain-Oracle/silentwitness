"""Sigma rule evaluation — the auto-detection pre-staging engine.

After EVTX ingest, every event is matched against a curated pack of Sigma rules so the
agent can *start* from concrete detection hits (RDP, suspicious PowerShell, brute-force
logon, cloud-exfil tooling) instead of blind keyword search — the single biggest recall
lever from the competitive analysis. Detection hits are written into the same FTS index
as ``sigma:<level>`` rows, so ``search_evidence`` (and a future ``list_detections``)
surfaces them with full provenance.

Why a small in-process matcher rather than Hayabusa/Chainsaw/Zircolite: those are GPL-3.0
(Hayabusa/Chainsaw) or assume a wide per-field SQLite schema (Zircolite) — neither fits an
MIT submission over a single-FTS-text-column index. ``pysigma`` (LGPL-2.1, runtime-linked
— permitted per ``scripts/license_gate.py``) is a rule *parser*, not an evaluator, but its
parsed-condition AST is walkable. We compile each rule's AST into a closure predicate at
load time, so per-event matching is just dict lookups and precompiled regex — pysigma is
touched only when the ruleset is built, never in the hot per-event path.

The compiler (``_compile_condition``/``_compile_value``) and the matcher are pure and
unit-tested; pysigma is a pure-Python dependency so the whole engine runs in CI.
"""

from __future__ import annotations

import logging
import os
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

_LOG = logging.getLogger(__name__)
# The bundled rules are a small, offline *seed* — NOT the product. The engine is
# pack-agnostic: point ``SILENTWITNESS_SIGMA_RULES_DIR`` at a full community SigmaHQ
# Windows ruleset (install.sh can fetch a pinned release) and every compatible rule is
# loaded. Rules this lightweight matcher can't represent are skipped loudly, so a broad
# pack degrades gracefully to the supported subset instead of failing.
_SEED_RULES_DIR = Path(__file__).parent / "rules"
_RULES_DIR_ENV = "SILENTWITNESS_SIGMA_RULES_DIR"


def _resolve_rules_dir() -> Path:
    override = os.environ.get(_RULES_DIR_ENV)
    if override:
        path = Path(override)
        if path.is_dir():
            return path
        _LOG.error("sigma: %s=%s is not a directory — using bundled seed", _RULES_DIR_ENV, override)
    return _SEED_RULES_DIR


# Process-creation events: Sysmon EID 1 and Security EID 4688. Rules whose logsource is
# ``category: process_creation`` are gated to these so an ``Image|endswith`` rule can't fire
# on an unrelated channel that happens to carry a same-named field.
_PROC_EVENT_IDS = frozenset({"1", "4688"})

# A compiled rule predicate: True iff the event dict satisfies the rule's condition.
_Predicate = Callable[[Mapping[str, str]], bool]
# A compiled value test: True iff a single field value satisfies one Sigma value.
_ValueTest = Callable[[str | None], bool]


class UnsupportedRuleError(Exception):
    """A rule uses a Sigma construct this lightweight matcher does not implement.

    Raised at compile time so the rule is skipped *loudly* (counted + logged) rather than
    silently matching nothing — a rule that can never fire must not masquerade as one that
    simply found nothing."""


@dataclass(frozen=True)
class Detection:
    """One Sigma rule that fired on an event: enough to cite, rank and attribute it."""

    rule_id: str
    title: str
    level: str
    author: str
    tags: tuple[str, ...]


def _sigmastring_regex(value: Any, *, anchored: bool) -> re.Pattern[str]:
    """Compile a ``SigmaString`` (literal parts + ``*``/``?`` wildcards) to a regex.

    ``anchored`` distinguishes the two Sigma string semantics: a *field* value is a
    full-value match (``^…$``; modifiers like ``contains`` already bake the surrounding
    ``*`` in), whereas a *keyword* (value-only, no field) is a substring match against the
    event. Both are case-insensitive."""
    from sigma.types import SpecialChars

    out: list[str] = []
    for part in value.s:
        if part == SpecialChars.WILDCARD_MULTI:
            out.append(".*")
        elif part == SpecialChars.WILDCARD_SINGLE:
            out.append(".")
        else:
            out.append(re.escape(part))
    body = "".join(out)
    pattern = f"^{body}$" if anchored else body
    return re.compile(pattern, re.IGNORECASE | re.DOTALL)


def _compile_value(value: Any, *, anchored: bool = True) -> _ValueTest:
    """Compile one Sigma value to a field-value test. Raises ``UnsupportedRuleError`` if unknown.

    ``anchored=False`` (keyword/value-only matching) makes string/regex tests substring
    rather than full-value."""
    from sigma.types import (
        SigmaNull,
        SigmaNumber,
        SigmaRegularExpression,
        SigmaString,
    )

    if isinstance(value, SigmaNull):
        return lambda actual: actual is None or actual == ""
    if isinstance(value, SigmaString):
        pattern = _sigmastring_regex(value, anchored=anchored)
        return lambda actual: actual is not None and pattern.search(actual) is not None
    if isinstance(value, SigmaNumber):
        target = float(value.number)
        return lambda actual: _num_eq(actual, target)
    if isinstance(value, SigmaRegularExpression):
        try:
            rx = re.compile(str(value.regexp), re.IGNORECASE)
        except re.error as exc:  # a malformed rule regex can never fire — skip the rule
            raise UnsupportedRuleError(f"bad regex: {exc}") from exc
        return lambda actual: actual is not None and rx.search(actual) is not None
    raise UnsupportedRuleError(f"value type {type(value).__name__}")


def _num_eq(actual: str | None, target: float) -> bool:
    if actual is None:
        return False
    try:
        return float(actual) == target
    except ValueError:
        return False


def _compile_condition(node: Any) -> _Predicate:
    """Compile a parsed Sigma condition node into an event predicate (recursive).

    Dispatch is by class *name* so a pysigma minor-version reshuffle of the class hierarchy
    doesn't silently break matching. ``1 of``/``all of`` selectors are already expanded into
    AND/OR by pysigma, so only the three boolean nodes plus the two leaf forms occur."""
    cls = type(node).__name__
    if cls == "ConditionAND":
        subs = [_compile_condition(a) for a in node.args]
        return lambda ev: all(sub(ev) for sub in subs)
    if cls == "ConditionOR":
        subs = [_compile_condition(a) for a in node.args]
        return lambda ev: any(sub(ev) for sub in subs)
    if cls == "ConditionNOT":
        sub = _compile_condition(node.args[0])
        return lambda ev: not sub(ev)
    if cls == "ConditionFieldEqualsValueExpression":
        field = node.field
        test = _compile_value(node.value)
        return lambda ev: test(ev.get(field))
    if cls == "ConditionValueExpression":  # keyword (no field): substring-match any value
        test = _compile_value(node.value, anchored=False)
        return lambda ev: any(test(v) for v in ev.values())
    raise UnsupportedRuleError(f"condition node {cls}")


def _logsource_predicate(logsource: Any) -> _Predicate | None:
    """A channel guard derived from a rule's ``logsource``, or None if no gate is needed.

    Generic Windows-log semantics (not case-specific): a ``process_creation`` rule may have
    no EventID in its condition (only ``Image|endswith``), so without a gate it would fire on
    any channel carrying a same-named field. Restrict those to Sysmon EID 1 / Security 4688.
    EventID-gated rules need no logsource guard — their condition already self-selects."""
    category = str(getattr(logsource, "category", "") or "").lower()
    if category == "process_creation":
        return lambda ev: (
            ev.get("EventID") in _PROC_EVENT_IDS or "sysmon" in ev.get("Channel", "").lower()
        )
    return None


def _compile_rule(rule: Any) -> _Predicate:
    """Compile a rule's (multi-expression) condition + logsource gate into one predicate."""
    preds = [_compile_condition(sc.parse()) for sc in rule.detection.parsed_condition]
    condition = preds[0] if len(preds) == 1 else (lambda ev: any(p(ev) for p in preds))
    gate = _logsource_predicate(rule.logsource)
    if gate is None:
        return condition
    return lambda ev: gate(ev) and condition(ev)


class SigmaRuleset:
    """A loaded, compiled pack of Sigma rules ready to match against event dicts."""

    def __init__(self, rules_dir: Path | None = None) -> None:
        self._rules: list[tuple[Detection, _Predicate]] = []
        self._skipped: list[tuple[str, str]] = []  # (rule title/id, reason)
        self._load(rules_dir if rules_dir is not None else _resolve_rules_dir())

    def _load(self, rules_dir: Path) -> None:
        from sigma.collection import SigmaCollection
        from sigma.exceptions import SigmaError

        # Recursive: a real community pack (SigmaHQ) is a nested tree of category dirs.
        paths = sorted(rules_dir.rglob("*.yml")) + sorted(rules_dir.rglob("*.yaml"))
        if not paths:
            _LOG.error("sigma: no rule files in %s — detection is OFF for this run", rules_dir)
            return
        # Load one file at a time so a single malformed rule in a large community pack is
        # skipped (counted) rather than aborting the whole ruleset — and so a parse failure
        # never propagates out to abort the EVTX ingest carrying the underlying evidence.
        for path in paths:
            try:
                rules = SigmaCollection.load_ruleset([str(path)]).rules
            except Exception as exc:  # a bad rule file must never be fatal to detection
                _LOG.debug("sigma: skipped unparseable rule file %s: %s", path.name, exc)
                self._skipped.append((path.name, str(exc)))
                continue
            for rule in rules:
                label = rule.title or str(rule.id)
                try:
                    predicate = _compile_rule(rule)
                except (UnsupportedRuleError, SigmaError) as exc:
                    # A rule this matcher can't represent is skipped *loudly* — it must not
                    # look like a rule that found nothing. Full SigmaHQ packs use modifiers /
                    # pipelines we don't implement, so a non-zero skip count is expected there.
                    _LOG.debug("sigma: skipped rule %r: %s", label, exc)
                    self._skipped.append((label, str(exc)))
                    continue
                self._rules.append((_detection_of(rule), predicate))
        _LOG.info(
            "sigma: %d rule(s) compiled, %d skipped from %s",
            len(self._rules),
            len(self._skipped),
            rules_dir,
        )

    @property
    def rule_count(self) -> int:
        return len(self._rules)

    @property
    def skipped(self) -> list[tuple[str, str]]:
        return list(self._skipped)

    def match(self, event: Mapping[str, str]) -> list[Detection]:
        """Every Detection whose rule fires on ``event`` (a field-name -> value dict)."""
        return [det for det, pred in self._rules if pred(event)]


def _detection_of(rule: Any) -> Detection:
    return Detection(
        rule_id=str(rule.id or ""),
        title=str(rule.title or ""),
        level=str(rule.level.name).lower() if rule.level is not None else "informational",
        author=str(rule.author or ""),
        tags=tuple(t.name for t in rule.tags),
    )


@lru_cache(maxsize=1)
def default_ruleset() -> SigmaRuleset:
    """The process-wide curated ruleset, compiled once (per worker process)."""
    return SigmaRuleset()


def evaluate_event(event: Mapping[str, str]) -> list[Detection]:
    """Match one event dict against the default curated ruleset."""
    return default_ruleset().match(event)


__all__ = [
    "Detection",
    "SigmaRuleset",
    "UnsupportedRuleError",
    "default_ruleset",
    "evaluate_event",
]
