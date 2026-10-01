"""2 · Campaigns: create and edit campaigns; restricted-category flag."""

from __future__ import annotations

from datetime import date

import streamlit as st

from influencesignal.compliance import (
    campaign_restricted_categories,
)
from influencesignal.storage import CATEGORIES, GOALS
from influencesignal.ui import signal_theme as sig

from .ui import (
    active_campaign,
    current_rules,
    date_or_none,
    demo_note,
    int_or_none,
    legal_note,
    select_campaign_next_run,
    store,
)


def render() -> None:
    sig.header(
        "2 · Campaigns",
        "Campaigns",
        "Name, brand, goal, budget, dates, brief and the deliverables you expect. The landing page drives every "
        "tracked link; the category decides whether the restricted-category flag appears.",
    )
    db = store()
    campaigns = db.campaigns()
    rules = current_rules()
    if not campaigns.empty:
        st.dataframe(
            campaigns[["name", "brand", "goal", "category", "budget_nok", "start_date", "end_date", "slug"]],
            hide_index=True,
            width="stretch",
            column_config={"budget_nok": st.column_config.NumberColumn("Budget (NOK)", format="%d")},
        )
    campaign = active_campaign()
    if campaign is not None:
        demo_note(bool(campaign["is_demo"]))
        flagged = campaign_restricted_categories(campaign, rules)
        if flagged:
            categories = rules.restricted_categories
            st.warning(
                "Restricted category flagged: "
                + ", ".join(f"[{categories[key].label}]({categories[key].url})" for key in flagged)
                + ". Stricter Norwegian rules apply. Influence Signal flags this only and never says the campaign is "
                "compliant."
            )
            legal_note()
        with st.expander(f"Edit “{campaign['name']}”", expanded=False):
            with st.form(f"edit_campaign_{campaign['id']}"):
                data = _campaign_fields(campaign, f"c{campaign['id']}")
                st.caption(f"Slug (used as utm_campaign, fixed once created): `{campaign['slug']}`")
                if st.form_submit_button("Save campaign", type="primary"):
                    db.update_campaign(int(campaign["id"]), data)
                    st.success("Saved.")
                    st.rerun()
            confirm = st.checkbox("I want to delete this campaign, its pipeline, deliverables and checklist answers")
            if st.button("Delete campaign", disabled=not confirm):
                db.delete_campaign(int(campaign["id"]))
                select_campaign_next_run(None)
                st.rerun()
        with st.container(border=True):
            st.markdown(f"**Brief** — {campaign['brief'] or '–'}")
            st.markdown(f"**Deliverables template** — {campaign['deliverables_template'] or '–'}")
            st.markdown(f"**Landing page** — `{campaign['landing_url'] or 'not set'}`")
    with st.expander("Create a new campaign", expanded=campaigns.empty):
        with st.form("new_campaign", clear_on_submit=True):
            data = _campaign_fields({}, "newc")
            if st.form_submit_button("Create campaign", type="primary"):
                select_campaign_next_run(db.add_campaign(data))
                st.rerun()


def _campaign_fields(current: dict, key: str) -> dict:
    data: dict[str, object] = {}
    cols = st.columns(2)
    data["name"] = cols[0].text_input("Campaign name *", current.get("name", ""), key=f"{key}_name")
    data["brand"] = cols[1].text_input("Brand", current.get("brand", ""), key=f"{key}_brand")
    cols = st.columns(3)
    goal = current.get("goal", "awareness")
    data["goal"] = cols[0].selectbox("Goal", GOALS, index=GOALS.index(goal) if goal in GOALS else 0, key=f"{key}_goal")
    category = current.get("category", "general")
    data["category"] = cols[1].selectbox(
        "Category", CATEGORIES, index=CATEGORIES.index(category) if category in CATEGORIES else 0, key=f"{key}_cat",
        help="Alcohol, gambling and tobacco/nicotine have stricter Norwegian rules and trigger a flag.",
    )
    data["budget_nok"] = cols[2].number_input(
        "Budget (NOK)", min_value=0, step=5000, value=int_or_none(current.get("budget_nok")), placeholder="not set",
        key=f"{key}_budget",
    )
    data["targets_children"] = st.checkbox(
        "This campaign targets children", bool(current.get("targets_children")), key=f"{key}_kids"
    )
    cols = st.columns(2)
    start = cols[0].date_input("Start date", date_or_none(current.get("start_date")) or date.today(), key=f"{key}_start")
    end = cols[1].date_input("End date", date_or_none(current.get("end_date")) or date.today(), key=f"{key}_end")
    data["start_date"], data["end_date"] = start.isoformat(), end.isoformat()
    data["landing_url"] = st.text_input(
        "Landing page (https://…)", current.get("landing_url", ""), key=f"{key}_url",
        help="Tracked links add utm_source, utm_medium=influencer, utm_campaign and utm_content to this page.",
    )
    data["brief"] = st.text_area("Brief", current.get("brief", ""), key=f"{key}_brief", height=110)
    data["deliverables_template"] = st.text_input(
        "Deliverables template", current.get("deliverables_template", ""), key=f"{key}_tmpl",
        placeholder="e.g. 1 × reel + 1 × story · discount code CODE-<NAME>",
    )
    return data
