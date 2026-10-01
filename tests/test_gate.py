"""A creator cannot be marked Paid until every deliverable's checklist is complete or an override is written."""

import pytest

from influencesignal.compliance import (
    STATUS_COMPLETE,
    STATUS_ISSUE,
    STATUS_MISSING,
    STATUS_NOT_PUBLISHED,
    STATUS_OVERRIDE,
    applicable_rules,
    checklist_status,
    paid_gate,
)
from influencesignal.errors import GateBlocked
from influencesignal.storage import STAGES

PUBLISHED = {"platform": "instagram", "format": "reel", "published_date": "2026-09-10", "shows_person": True}


def _walk_to(store, engagement_id, rules, stage):
    for step in STAGES[1 : STAGES.index(stage) + 1]:
        store.move_engagement(engagement_id, step, rules)


def test_no_deliverables_blocks_paid(campaign_with_creator, rules) -> None:
    store, _, engagement_id = campaign_with_creator
    _walk_to(store, engagement_id, rules, "Published")
    with pytest.raises(GateBlocked) as blocked:
        store.move_engagement(engagement_id, "Paid", rules)
    assert any("No deliverables" in reason for reason in blocked.value.reasons)


def test_unanswered_checklist_blocks_paid_and_reported(campaign_with_creator, rules) -> None:
    store, _, engagement_id = campaign_with_creator
    store.add_deliverable(engagement_id, PUBLISHED)
    _walk_to(store, engagement_id, rules, "Published")
    for stage in ("Paid", "Reported"):
        with pytest.raises(GateBlocked):
            store.move_engagement(engagement_id, stage, rules)
    assert store.engagements(1)["stage"].iloc[0] == "Published"


def test_a_no_answer_blocks_paid(campaign_with_creator, rules) -> None:
    store, campaign_id, engagement_id = campaign_with_creator
    deliverable_id = store.add_deliverable(engagement_id, PUBLISHED)
    campaign = store.campaign(campaign_id)
    for rule in applicable_rules(store.deliverable(deliverable_id), campaign, rules):
        store.set_answer(deliverable_id, rule.id, "yes")
    store.set_answer(deliverable_id, "ad_identified", "no")
    _walk_to(store, engagement_id, rules, "Published")
    with pytest.raises(GateBlocked) as blocked:
        store.move_engagement(engagement_id, "Paid", rules)
    assert any("answered No" in reason for reason in blocked.value.reasons)


def test_complete_checklist_allows_paid_and_is_logged(campaign_with_creator, rules) -> None:
    store, campaign_id, engagement_id = campaign_with_creator
    deliverable_id = store.add_deliverable(engagement_id, PUBLISHED)
    campaign = store.campaign(campaign_id)
    for rule in applicable_rules(store.deliverable(deliverable_id), campaign, rules):
        store.set_answer(deliverable_id, rule.id, "na" if rule.allow_not_applicable else "yes")
    _walk_to(store, engagement_id, rules, "Reported")
    assert store.engagements(campaign_id)["stage"].iloc[0] == "Reported"
    log = store.stage_log(campaign_id)
    assert "Paid" in set(log["to_stage"])


def test_written_override_allows_paid(campaign_with_creator, rules) -> None:
    store, campaign_id, engagement_id = campaign_with_creator
    deliverable_id = store.add_deliverable(engagement_id, PUBLISHED)
    _walk_to(store, engagement_id, rules, "Published")
    store.set_override(deliverable_id, "short")
    with pytest.raises(GateBlocked):
        store.move_engagement(engagement_id, "Paid", rules)
    store.set_override(deliverable_id, "Checked the archived post by screenshot on 12 Sept; label present.")
    store.move_engagement(engagement_id, "Paid", rules)
    assert store.engagements(campaign_id)["stage"].iloc[0] == "Paid"


def test_unpublished_deliverable_blocks_paid(campaign_with_creator, rules) -> None:
    store, _, engagement_id = campaign_with_creator
    store.add_deliverable(engagement_id, {**PUBLISHED, "published_date": ""})
    _walk_to(store, engagement_id, rules, "Published")
    with pytest.raises(GateBlocked) as blocked:
        store.move_engagement(engagement_id, "Paid", rules)
    assert any("not marked as published" in reason for reason in blocked.value.reasons)


def test_every_deliverable_must_pass(campaign_with_creator, rules) -> None:
    store, campaign_id, engagement_id = campaign_with_creator
    first = store.add_deliverable(engagement_id, PUBLISHED)
    store.add_deliverable(engagement_id, {**PUBLISHED, "format": "story"})
    campaign = store.campaign(campaign_id)
    for rule in applicable_rules(store.deliverable(first), campaign, rules):
        store.set_answer(first, rule.id, "yes")
    _walk_to(store, engagement_id, rules, "Published")
    with pytest.raises(GateBlocked):
        store.move_engagement(engagement_id, "Paid", rules)


def test_not_applicable_only_where_the_rule_allows_it(rules) -> None:
    campaign = {"category": "general"}
    answers = {"ad_identified": "na", "label_wording": "yes", "retouch_label": "na"}
    status = checklist_status(PUBLISHED, campaign, answers, rules)
    assert status.invalid == ("ad_identified",)
    assert not status.complete


def test_rule_applicability(rules) -> None:
    general = {"category": "general"}
    no_person = {**PUBLISHED, "shows_person": False}
    assert "retouch_label" not in [r.id for r in applicable_rules(no_person, general, rules)]
    story = {**PUBLISHED, "format": "story"}
    assert "stories_each_labelled" in [r.id for r in applicable_rules(story, general, rules)]
    assert "stories_each_labelled" not in [r.id for r in applicable_rules(PUBLISHED, general, rules)]
    assert "restricted_category" not in [r.id for r in applicable_rules(PUBLISHED, general, rules)]
    assert "restricted_category" in [r.id for r in applicable_rules(PUBLISHED, {"category": "alcohol"}, rules)]
    assert "restricted_category" in [r.id for r in applicable_rules(PUBLISHED, {"category": "general", "targets_children": 1}, rules)]


def test_status_labels_never_say_compliant(rules) -> None:
    campaign = {"category": "general"}
    labels = {
        checklist_status({**PUBLISHED, "published_date": ""}, campaign, {}, rules).label,
        checklist_status(PUBLISHED, campaign, {}, rules).label,
        checklist_status(PUBLISHED, campaign, {"ad_identified": "no"}, rules).label,
        checklist_status({**PUBLISHED, "override_reason": "x" * 20}, campaign, {}, rules).label,
        checklist_status(PUBLISHED, campaign, {"ad_identified": "yes", "label_wording": "yes", "retouch_label": "yes"}, rules).label,
    }
    assert labels == {STATUS_NOT_PUBLISHED, STATUS_MISSING, STATUS_ISSUE, STATUS_OVERRIDE, STATUS_COMPLETE}
    assert not any("compliant" in label.lower() for label in labels)


def test_gate_function_reports_reasons(rules) -> None:
    status = checklist_status(PUBLISHED, {"category": "general"}, {"ad_identified": "no"}, rules)
    gate = paid_gate(status, rules, "#1")
    assert not gate.allowed
    assert any("override reason" in reason for reason in gate.reasons)
