"""4 · Deliverables: posts, discount codes and tracked links."""

from __future__ import annotations

from datetime import date

import streamlit as st

from influencesignal.errors import DataProblem
from influencesignal.storage import FORMATS
from influencesignal.utm import PLATFORMS, build_tracked_url, creator_token
from influencesignal.ui import signal_theme as sig

from .ui import (
    date_or_none,
    demo_note,
    require_campaign,
    store,
)


def render() -> None:
    sig.header(
        "4 · Deliverables",
        "Deliverables, codes and tracked links",
        "One row per post: platform, format, due date, agreed fee, discount code and a tracked link in one "
        "consistent UTM scheme. Mark a deliverable published to open its compliance checklist.",
    )
    campaign = require_campaign()
    if campaign is None:
        return
    db = store()
    demo_note(bool(campaign["is_demo"]))
    engagements = db.engagements(int(campaign["id"]))
    deliverables = db.deliverables(int(campaign["id"]))
    st.markdown(
        "UTM scheme: `utm_source=<platform>&utm_medium=influencer&utm_campaign="
        f"{campaign['slug']}&utm_content=<creator handle>`"
    )
    if not campaign["landing_url"]:
        st.warning("This campaign has no landing page, so tracked links are empty. Add one on **2 · Campaigns**.")
    if deliverables.empty:
        st.info("No deliverables yet.")
    else:
        st.dataframe(
            deliverables[
                ["id", "creator_name", "platform", "format", "due_date", "fee_nok", "discount_code", "published_date",
                 "tracked_url"]
            ],
            hide_index=True,
            width="stretch",
            column_config={
                "fee_nok": st.column_config.NumberColumn("Fee (NOK)", format="%d"),
                "tracked_url": st.column_config.LinkColumn("Tracked link"),
            },
        )

    if engagements.empty:
        st.info("Add creators to the pipeline first.")
        return
    options = dict(zip(engagements["id"], engagements["creator_name"]))
    with st.expander("Add a deliverable", expanded=deliverables.empty):
        engagement_id = st.selectbox("Creator", list(options), format_func=options.get, key="new_deliv_creator")
        row = engagements[engagements["id"] == engagement_id].iloc[0].to_dict()
        default_platform = next((platform for platform in PLATFORMS if row.get(platform)), "instagram")
        cols = st.columns(3)
        platform = cols[0].selectbox("Platform", PLATFORMS, index=PLATFORMS.index(default_platform), key="new_deliv_platform")
        fmt = cols[1].selectbox("Format", FORMATS, key="new_deliv_format")
        due = cols[2].date_input("Due date", date_or_none(campaign["start_date"]) or date.today(), key="new_deliv_due")
        cols = st.columns(3)
        fee = cols[0].number_input("Agreed fee (NOK)", min_value=0, step=500, key="new_deliv_fee")
        code = cols[1].text_input("Discount code", key="new_deliv_code")
        shows_person = cols[2].checkbox(
            "Shows a person's body or face", value=True, key="new_deliv_person",
            help="Turns on the retouched-advertising check for this deliverable.",
        )
        if campaign["landing_url"]:
            handle = row.get(platform) or next((row[p] for p in PLATFORMS if row.get(p)), "")
            try:
                preview = build_tracked_url(campaign["landing_url"], platform, campaign["slug"], creator_token(handle, row["creator_name"]))
                st.code(preview, language=None)
            except DataProblem as exc:
                st.warning(str(exc))
        if st.button("Add deliverable", type="primary"):
            db.add_deliverable(
                int(engagement_id),
                {"platform": platform, "format": fmt, "due_date": due.isoformat(), "fee_nok": fee,
                 "discount_code": code, "shows_person": shows_person},
            )
            st.success("Deliverable added.")
            st.rerun()

    if deliverables.empty:
        return
    with st.expander("Edit, publish or delete a deliverable", expanded=True):
        labels = {
            int(row["id"]): f"#{row['id']} · {row['creator_name']} · {row['platform']} {row['format']}"
            for row in deliverables.to_dict("records")
        }
        chosen = st.selectbox("Deliverable", list(labels), format_func=labels.get, key="edit_deliv")
        current = db.deliverable(int(chosen))
        key = f"d{chosen}"
        cols = st.columns(3)
        platform = cols[0].selectbox("Platform", PLATFORMS, index=PLATFORMS.index(current["platform"]), key=f"{key}_p")
        fmt = cols[1].selectbox("Format", FORMATS, index=FORMATS.index(current["format"]), key=f"{key}_f")
        due = cols[2].date_input("Due date", date_or_none(current["due_date"]) or date.today(), key=f"{key}_due")
        cols = st.columns(3)
        fee = cols[0].number_input("Agreed fee (NOK)", min_value=0, step=500, value=int(current["fee_nok"] or 0), key=f"{key}_fee")
        code = cols[1].text_input("Discount code", current["discount_code"] or "", key=f"{key}_code")
        shows_person = cols[2].checkbox("Shows a person's body or face", bool(current["shows_person"]), key=f"{key}_person")
        cols = st.columns(3)
        published = cols[0].checkbox("Published", bool(current["published_date"]), key=f"{key}_pub")
        published_on = cols[1].date_input(
            "Published on", date_or_none(current["published_date"]) or date.today(), key=f"{key}_pubdate",
            disabled=not published,
        )
        post_url = cols[2].text_input("Post URL (optional)", current["post_url"] or "", key=f"{key}_post")
        st.markdown("**Tracked link**")
        st.code(current["tracked_url"] or "– (no landing page)", language=None)
        b1, b2, b3 = st.columns(3)
        if b1.button("Save deliverable", type="primary", key=f"{key}_save"):
            db.update_deliverable(
                int(chosen),
                {"platform": platform, "format": fmt, "due_date": due.isoformat(), "fee_nok": fee, "discount_code": code,
                 "shows_person": shows_person, "published_date": published_on.isoformat() if published else "",
                 "post_url": post_url},
            )
            st.success("Saved.")
            st.rerun()
        if b2.button("Rebuild tracked link", key=f"{key}_regen", help="Use after changing platform, handle or landing page."):
            db.regenerate_tracked_url(int(chosen))
            st.rerun()
        confirm = b3.checkbox("Confirm delete", key=f"{key}_delok")
        if b3.button("Delete deliverable", disabled=not confirm, key=f"{key}_del"):
            db.delete_deliverable(int(chosen))
            st.rerun()
