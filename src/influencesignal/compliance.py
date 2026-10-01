"""Checklist status per deliverable and the gate that guards the *Paid* stage.

Checklist support, not legal advice. Status labels describe what was *recorded*; InfluenceSignal never labels a
post or campaign "compliant".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .rules import Rule, RuleSet

ANSWERS = ("yes", "no", "na")
MIN_OVERRIDE_CHARS = 15
GATED_STAGES = ("Paid", "Reported")

STATUS_NOT_PUBLISHED = "Not published yet"
STATUS_COMPLETE = "Checklist complete"
STATUS_MISSING = "Answers missing"
STATUS_ISSUE = "Issue recorded"
STATUS_OVERRIDE = "Override recorded"


def campaign_restricted_categories(campaign: Mapping[str, object], rules: RuleSet) -> list[str]:
    """Restricted-category keys that apply to a campaign (its category, plus children if it targets them)."""
    known = rules.restricted_categories
    flagged = []
    category = str(campaign.get("category") or "").strip()
    if category in known:
        flagged.append(category)
    if campaign.get("targets_children") and "children" in known:
        flagged.append("children")
    return flagged


def rule_applies(rule: Rule, deliverable: Mapping[str, object], campaign: Mapping[str, object], rules: RuleSet) -> bool:
    if rule.applies_when == "always":
        return True
    if rule.applies_when == "shows_person":
        return bool(deliverable.get("shows_person"))
    if rule.applies_when == "format_story":
        return str(deliverable.get("format") or "").lower() == "story"
    if rule.applies_when == "restricted_category":
        return bool(campaign_restricted_categories(campaign, rules))
    return False


def applicable_rules(deliverable: Mapping[str, object], campaign: Mapping[str, object], rules: RuleSet) -> list[Rule]:
    return [rule for rule in rules.rules if rule_applies(rule, deliverable, campaign, rules)]


@dataclass(frozen=True)
class ChecklistStatus:
    published: bool
    applicable: tuple[str, ...]
    missing: tuple[str, ...]
    failing: tuple[str, ...]
    invalid: tuple[str, ...]
    override_reason: str

    @property
    def complete(self) -> bool:
        """Every applicable rule answered acceptably (yes, or not-applicable where the rule allows it)."""
        return self.published and not self.missing and not self.failing and not self.invalid

    @property
    def has_override(self) -> bool:
        return len(self.override_reason.strip()) >= MIN_OVERRIDE_CHARS

    @property
    def label(self) -> str:
        if self.complete:
            return STATUS_COMPLETE
        if self.has_override:
            return STATUS_OVERRIDE
        if not self.published:
            return STATUS_NOT_PUBLISHED
        if self.failing or self.invalid:
            return STATUS_ISSUE
        return STATUS_MISSING


def checklist_status(
    deliverable: Mapping[str, object],
    campaign: Mapping[str, object],
    answers: Mapping[str, str | None],
    rules: RuleSet,
) -> ChecklistStatus:
    """Evaluate one deliverable's recorded answers against the applicable rules."""
    applicable = applicable_rules(deliverable, campaign, rules)
    missing, failing, invalid = [], [], []
    for rule in applicable:
        answer = (answers.get(rule.id) or "").strip().lower()
        if not answer:
            missing.append(rule.id)
        elif answer == "no":
            failing.append(rule.id)
        elif answer == "na" and not rule.allow_not_applicable:
            invalid.append(rule.id)
        elif answer not in ANSWERS:
            invalid.append(rule.id)
    return ChecklistStatus(
        published=bool(str(deliverable.get("published_date") or "").strip()),
        applicable=tuple(rule.id for rule in applicable),
        missing=tuple(missing),
        failing=tuple(failing),
        invalid=tuple(invalid),
        override_reason=str(deliverable.get("override_reason") or ""),
    )


@dataclass(frozen=True)
class GateResult:
    allowed: bool
    reasons: tuple[str, ...]
    via_override: bool = False


def paid_gate(status: ChecklistStatus, rules: RuleSet, deliverable_label: str = "Deliverable") -> GateResult:
    """Can this deliverable move to *Paid*? Only with a complete checklist or a written override reason."""
    if status.complete:
        return GateResult(True, ())
    reasons = []
    if not status.published:
        reasons.append(f"{deliverable_label}: not marked as published (no publish date).")
    for rule_id in status.missing:
        reasons.append(f"{deliverable_label}: '{rules.by_id(rule_id).label_en}' not answered.")
    for rule_id in status.failing:
        reasons.append(f"{deliverable_label}: '{rules.by_id(rule_id).label_en}' answered No.")
    for rule_id in status.invalid:
        reasons.append(f"{deliverable_label}: '{rules.by_id(rule_id).label_en}' has an answer this rule does not allow.")
    if status.has_override:
        return GateResult(True, tuple(reasons), via_override=True)
    reasons.append(
        f"{deliverable_label}: complete the checklist or write an override reason "
        f"(at least {MIN_OVERRIDE_CHARS} characters)."
    )
    return GateResult(False, tuple(reasons))
