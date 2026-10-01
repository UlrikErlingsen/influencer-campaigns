"""5 · Compliance: the Norwegian advertising checklist per published deliverable."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from influencesignal.compliance import (
    GATED_STAGES,
    MIN_OVERRIDE_CHARS,
    STATUS_COMPLETE,
    STATUS_ISSUE,
    STATUS_MISSING,
    STATUS_NOT_PUBLISHED,
    STATUS_OVERRIDE,
    applicable_rules,
    campaign_restricted_categories,
    checklist_status,
    paid_gate,
)

from .ui import (
    STATUS_ICONS,
    current_rules,
    demo_note,
    legal_note,
    page_header,
    require_campaign,
    store,
)


def render() -> None:
    page_header(
        "5 · Compliance",
        "Norwegian advertising checklist",
        "For every published deliverable: is it labelled as advertising at the start, with the recommended wording, "
        "and with the retouching mark where a body was altered? Rules, sources and quotes come from an editable "
        "YAML file.",
    )
    legal_note()
    campaign = require_campaign()
    if campaign is None:
        return
    db, rules = store(), current_rules()
    demo_note(bool(campaign["is_demo"]))
    flagged = campaign_restricted_categories(campaign, rules)
    if flagged:
        categories = rules.restricted_categories
        for key in flagged:
            category = categories[key]
            st.warning(
                f"**Restricted category: {category.label}.** {category.note} "
                f"[Source]({category.url}). InfluenceSignal flags this only; it never says the campaign is compliant."
            )

    deliverables = db.deliverables(int(campaign["id"]))
    if deliverables.empty:
        st.info("No deliverables yet. Add them on **4 · Deliverables**.")
        return
    rows, statuses = [], {}
    for row in deliverables.to_dict("records"):
        status = checklist_status(row, campaign, db.answers(int(row["id"])), rules)
        statuses[int(row["id"])] = status
        rows.append(
            {
                "id": row["id"],
                "status": f"{STATUS_ICONS.get(status.label, '')} {status.label}",
                "creator": row["creator_name"],
                "platform": row["platform"],
                "format": row["format"],
                "published": row["published_date"] or "–",
                "stage": row["stage"],
                "answered no": ", ".join(rules.by_id(r).label_en for r in status.failing),
                "not answered": ", ".join(rules.by_id(r).label_en for r in (*status.missing, *status.invalid))
                if status.published else "",
            }
        )
    table = pd.DataFrame(rows)
    counts = table["status"].str.split(" ", n=1).str[1].value_counts()
    cols = st.columns(5)
    for col, status in zip(cols, (STATUS_COMPLETE, STATUS_OVERRIDE, STATUS_ISSUE, STATUS_MISSING, STATUS_NOT_PUBLISHED)):
        col.metric(f"{STATUS_ICONS[status]} {status}", int(counts.get(status, 0)))
    issues = [r for r in rows if STATUS_ISSUE in r["status"]]
    for issue in issues:
        missing = f" Not answered yet: {issue['not answered']}." if issue["not answered"] else ""
        st.error(f"⚠️ #{issue['id']} {issue['creator']} ({issue['platform']} {issue['format']}): answered No on "
                 f"{issue['answered no']}.{missing} Fix the post or record why before payment.")
    after_payment = [
        r for r in rows
        if r["stage"] in GATED_STAGES and not any(ok in r["status"] for ok in (STATUS_COMPLETE, STATUS_OVERRIDE))
    ]
    for row in after_payment:
        st.warning(
            f"#{row['id']} {row['creator']} is already {row['stage']}, but this deliverable now has open checklist "
            "items (changed after payment). Complete the checklist or record an override reason."
        )
    st.dataframe(table, hide_index=True, width="stretch")

    published = [r for r in rows if r["published"] != "–"]
    if not published:
        st.info("Nothing is published yet. Mark a deliverable published on **4 · Deliverables** to open its checklist.")
        return
    labels = {int(r["id"]): f"#{r['id']} · {r['creator']} · {r['platform']} {r['format']} — {r['status']}" for r in published}
    default = next((i for i, r in enumerate(published) if STATUS_ISSUE in r["status"]), 0)
    chosen = st.selectbox("Open checklist for", list(labels), index=default, format_func=labels.get, key="checklist_deliverable")
    deliverable = db.deliverable(int(chosen))
    answers = db.answers(int(chosen))
    st.markdown(f"#### Checklist · #{chosen}")
    legal_note()
    with st.form(f"checklist_{chosen}"):
        new_answers = {}
        for rule in applicable_rules(deliverable, campaign, rules):
            with st.container(border=True):
                st.markdown(f"**{rule.label_no}** · {rule.label_en}")
                st.markdown(f"{rule.question_no}  \n*{rule.question_en}*")
                choices = ["", "yes", "no"] + (["na"] if rule.allow_not_applicable else [])
                names = {"": "Not answered", "yes": "Yes", "no": "No", "na": rule.not_applicable_label_en}
                current = answers.get(rule.id, "")
                new_answers[rule.id] = st.radio(
                    "Answer", choices, index=choices.index(current) if current in choices else 0,
                    format_func=names.get, horizontal=True, key=f"ans_{chosen}_{rule.id}", label_visibility="collapsed",
                )
                with st.expander("Source, quote and guidance"):
                    if rule.help_en:
                        st.markdown(rule.help_en)
                    if rule.legal_basis:
                        st.caption(f"Legal basis: {rule.legal_basis}")
                    for source in rule.sources:
                        st.markdown(f"[{source.title}]({source.url})")
                        if source.quote:
                            st.markdown(f"> «{source.quote}»")
                        st.caption(f"Fetched {source.fetched}. Verify the current wording at the source.")
                    for key in campaign_restricted_categories(campaign, rules) if rule.applies_when == "restricted_category" else []:
                        category = rules.restricted_categories[key]
                        st.markdown(f"[{category.label}]({category.url}) — {category.note}")
                        if category.quote:
                            st.markdown(f"> «{category.quote}»")
        if st.form_submit_button("Save checklist", type="primary"):
            for rule_id, answer in new_answers.items():
                db.set_answer(int(chosen), rule_id, answer or None)
            st.success("Checklist saved.")
            st.rerun()

    status = statuses[int(chosen)]
    gate = paid_gate(status, rules, f"#{chosen}")
    if gate.allowed and not gate.via_override:
        st.success("Checklist complete: this deliverable does not block the Paid stage.")
    elif gate.allowed:
        st.info("An override reason is recorded: this deliverable will not block the Paid stage. Open items stay visible in the report.")
    else:
        st.warning("This deliverable blocks the Paid stage:\n\n" + "\n".join(f"- {reason}" for reason in gate.reasons))
    with st.form(f"override_{chosen}"):
        reason = st.text_area(
            "Override reason (lets the creator move to Paid with open items — written into the report)",
            deliverable["override_reason"] or "", height=90,
            help=f"At least {MIN_OVERRIDE_CHARS} characters. Explain what was checked instead, by whom and when.",
        )
        if st.form_submit_button("Save override reason"):
            db.set_override(int(chosen), reason)
            st.rerun()
