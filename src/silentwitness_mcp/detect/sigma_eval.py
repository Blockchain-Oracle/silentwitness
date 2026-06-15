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
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

_LOG = logging.getLogger(__name__)
_RULES_DIR = Path(__file__).parent / "rules"

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


def _sigmastring_regex(value: Any) -> re.Pattern[str]:
    """Compile a ``SigmaString`` (literal parts + ``*``/``?`` wildcards) to an anchored regex.

    Sigma string matching is full-value (modifiers like ``contains`` already bake the
    surrounding ``*`` into the value) and case-insensitive by default."""
    from sigma.types import SpecialChars

    out: list[str] = []
    for part in value.s:
        if part == SpecialChars.WILDCARD_MULTI:
            out.append(".*")
        elif part == SpecialChars.WILDCARD_SINGLE:
            out.append(".")
        else:
            out.append(re.escape(part))
    return re.compile("^" + "".join(out) + "$", re.IGNORECASE | re.DOTALL)


def _compile_value(value: Any) -> _ValueTest:
    """Compile one Sigma value to a field-value test. Raises ``UnsupportedRuleError`` if unknown."""
    from sigma.types import (
        SigmaNull,
        SigmaNumber,
        SigmaRegularExpression,
        SigmaString,
    )

    if isinstance(value, SigmaNull):
        return lambda actual: actual is None or actual == ""
    if isinstance(value, SigmaString):
        pattern = _sigmastring_regex(value)
        return lambda actual: actual is not None and pattern.match(actual) is not None
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
    if cls == "ConditionValueExpression":  # keyword (no field): match any field's value
        test = _compile_value(node.value)
        return lambda ev: any(test(v) for v in ev.values())
    raise UnsupportedRuleError(f"condition node {cls}")


def _compile_rule(rule: Any) -> _Predicate:
    """Compile a rule's (possibly multi-expression) condition into one OR-combined predicate."""
    preds = [_compile_condition(sc.parse()) for sc in rule.detection.parsed_condition]
    if len(preds) == 1:
        return preds[0]
    return lambda ev: any(p(ev) for p in preds)


class SigmaRuleset:
    """A loaded, compiled pack of Sigma rules ready to match against event dicts."""

    def __init__(self, rules_dir: Path = _RULES_DIR) -> None:
        self._rules: list[tuple[Detection, _Predicate]] = []
        self._skipped: list[tuple[str, str]] = []  # (rule title/id, reason)
        self._load(rules_dir)

    def _load(self, rules_dir: Path) -> None:
        from sigma.collection import SigmaCollection
        from sigma.exceptions import SigmaError

        paths = sorted(rules_dir.glob("*.yml"))
        if not paths:
            _LOG.warning("sigma: no rule files found in %s", rules_dir)
            return
        collection = SigmaCollection.load_ruleset([str(p) for p in paths])
        for rule in collection.rules:
            label = rule.title or str(rule.id)
            try:
                predicate = _compile_rule(rule)
            except (UnsupportedRuleError, SigmaError) as exc:
                _LOG.warning("sigma: skipped rule %r: %s", label, exc)
                self._skipped.append((label, str(exc)))
                continue
            self._rules.append((_detection_of(rule), predicate))

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
