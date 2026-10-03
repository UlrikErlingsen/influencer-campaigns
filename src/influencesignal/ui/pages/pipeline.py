"""3 · Pipeline: kanban stages with the Paid gate."""

from __future__ import annotations

import streamlit as st

from influencesignal.compliance import (
    STATUS_NOT_PUBLISHED,
    checklist_status,
)
from influencesignal.errors import DataProblem, GateBlocked
from influencesignal.storage import STAGES
from influencesignal.ui import signal_theme as sig

from ..shell import (
    k,
    STATUS_ICONS,
    creator_card,
    current_rules,
    demo_note,
    handle_label,
    OPTION_LIMIT,
    lane_title,
    limited_options,
    nok,
    num,
    require_campaign,
    store,
)


def render() -> None:
    sig.header(
        "3 · Pipeline",
        "Campaign pipeline",
        "Move each creator with the stage selector on their card. Paid and Reported are guarded: every deliverable "
        "needs a complete checklist or a written override reason first.",
    )
    campaign = require_campaign()
    if campaign is None:
        return
    db, rules = store(), current_rules()
    demo_note(bool(campaign["is_demo"]))
    engagements = db.engagements(int(campaign["id"]))
    deliverables = db.deliverables(int(campaign["id"]))
    committed = float(deliverables["fee_nok"].fillna(0).sum()) if not deliverables.empty else 0.0
    budget = float(campaign["budget_nok"] or 0)
    cols = st.columns(4)
    cols[0].metric("Creators in pipeline", len(engagements))
    cols[1].metric("Budget", nok(budget))
    cols[2].metric("Agreed fees", nok(committed))
    cols[3].metric("Unallocated", nok(budget - committed))

    flash = st.session_state.pop(k("pipeline_flash"), None)
    if flash:
        kind, message, reasons = flash
        (st.success if kind == "success" else st.error)(message)
        for reason in reasons:
            st.markdown(f"- {reason}")
        if kind == "error" and reasons:
            st.caption("Fix it on **5 · Compliance** (answer the checklist or write an override reason).")

    candidates = db.creators()
    candidates = candidates[~candidates["id"].isin(engagements["creator_id"])]
    with st.expander("Add creators to the shortlist"):
        if len(candidates) > OPTION_LIMIT:
            needle = st.text_input("Find creators by name", key=k("shortlist_search")).strip().casefold()
            if needle:
                candidates = candidates[candidates["name"].astype(str).str.casefold().str.contains(needle, regex=False)]
        options = limited_options(dict(zip(candidates["id"], candidates["name"])), "creators")
        chosen = st.multiselect("Creators", list(options), format_func=options.get, key=k("shortlist_add"))
        if st.button("Add to shortlist", type="primary", disabled=not chosen, key=k("shortlist_submit")):
            db.add_to_shortlist(int(campaign["id"]), [int(value) for value in chosen])
            st.rerun()

    deliverable_counts = deliverables.groupby("engagement_id").size().to_dict() if not deliverables.empty else {}
    statuses: dict[int, list[str]] = {}
    for row in deliverables.to_dict("records"):
        status = checklist_status(row, campaign, db.answers(int(row["id"])), rules)
        statuses.setdefault(int(row["engagement_id"]), []).append(status.label)

    for lane_group in (STAGES[:4], STAGES[4:]):
        lanes = st.columns(4)
        for lane, stage in zip(lanes, lane_group):
            members = engagements[engagements["stage"] == stage]
            with lane:
                lane_title(stage, len(members))
                for row in members.to_dict("records"):
                    engagement_id = int(row["id"])
                    with st.container(border=True):
                        labels = statuses.get(engagement_id, [])
                        flags = " ".join(STATUS_ICONS.get(label, "") for label in labels if label != STATUS_NOT_PUBLISHED)
                        creator_card(
                            str(row["creator_name"]),
                            flags,
                            [
                                f"{handle_label(row)} · {num(row['followers'])} followers",
                                f"{deliverable_counts.get(engagement_id, 0)} deliverable(s)",
                            ],
                        )
                        key = k(f"stage_{engagement_id}_{stage}")
                        st.selectbox(
                            "Stage", STAGES, index=STAGES.index(stage), key=key, label_visibility="collapsed",
                            on_change=_move_card, args=(engagement_id, key, stage, row["creator_name"]),
                        )
        st.write("")
    st.caption("Card icons: ✅ checklist complete · 📝 override recorded · ⚠️ issue recorded · ⏳ answers missing")
    with st.expander("Stage history"):
        st.dataframe(db.stage_log(int(campaign["id"])), hide_index=True, width="stretch")
    with st.expander("Remove a creator from this campaign"):
        options = dict(zip(engagements["id"], engagements["creator_name"]))
        if options:
            chosen = st.selectbox("Creator", list(options), format_func=options.get, key=k("remove_engagement"))
            confirm = st.checkbox(
                "Also delete their deliverables and checklist answers for this campaign", key=k("confirm_remove")
            )
            if st.button("Remove from campaign", disabled=not confirm, key=k("remove_submit")):
                db.remove_engagement(int(chosen))
                st.rerun()


def _move_card(engagement_id: int, key: str, previous: str, name: str) -> None:
    target = st.session_state.get(key)
    try:
        store().move_engagement(engagement_id, target, current_rules())
        st.session_state[k("pipeline_flash")] = ("success", f"Moved {name} to {target}.", ())
    except GateBlocked as exc:
        st.session_state[k("pipeline_flash")] = ("error", f"{name}: {exc}", exc.reasons)
        del st.session_state[key]
    except DataProblem as exc:
        st.session_state[k("pipeline_flash")] = ("error", str(exc), ())
        del st.session_state[key]
