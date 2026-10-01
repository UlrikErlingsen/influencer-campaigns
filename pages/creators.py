"""1 · Creators: roster, filters, add/edit, CSV import and export."""

from __future__ import annotations

import streamlit as st

from influencesignal.io import (
    CREATOR_COLUMNS,
    FYLKER,
    creator_template,
    dataframe_csv_bytes,
    read_table,
    validate_creators,
)
from influencesignal.utm import PLATFORMS

from .ui import (
    demo_note,
    float_or_none,
    int_or_none,
    page_header,
    store,
)


def render() -> None:
    page_header(
        "1 · Creators",
        "Creator roster",
        "Everyone you might work with, across campaigns. Enter figures manually or import a CSV. Follower counts and "
        "engagement rates are whatever you or the creator report — InfluenceSignal never fetches them.",
    )
    db = store()
    creators = db.creators()
    demo_note(bool(creators["is_demo"].any()) if not creators.empty else False)

    with st.container(border=True):
        cols = st.columns([2, 2, 2, 2])
        query = cols[0].text_input("Search name or handle", key="creator_search")
        all_tags = sorted({tag.strip() for tags in creators.get("niche_tags", []) for tag in str(tags).split(",") if tag.strip()})
        tags = cols[1].multiselect("Niche tags", all_tags)
        regions = cols[2].multiselect("Region (fylke)", list(FYLKER))
        platforms = cols[3].multiselect("Has a handle on", list(PLATFORMS))
    view = creators.copy()
    if query:
        needle = query.strip().lstrip("@").casefold()
        haystack = view[["name", *PLATFORMS]].astype(str).apply(lambda row: " ".join(row).casefold(), axis=1)
        view = view[haystack.str.contains(needle, regex=False)]
    if tags:
        view = view[view["niche_tags"].apply(lambda value: any(tag in str(value).split(", ") for tag in tags))]
    if regions:
        view = view[view["region"].isin(regions)]
    for platform in platforms:
        view = view[view[platform].astype(str).str.len() > 0]
    st.caption(f"{len(view)} of {len(creators)} creators")
    st.dataframe(
        view[["name", *PLATFORMS, "followers", "engagement_rate", "niche_tags", "region", "contact_email", "rate_card"]],
        hide_index=True,
        width="stretch",
        column_config={
            "followers": st.column_config.NumberColumn("Followers", format="%d"),
            "engagement_rate": st.column_config.NumberColumn("Engagement %", format="%.1f"),
        },
    )

    left, right = st.columns(2)
    with left, st.expander("Add a creator"):
        with st.form("add_creator", clear_on_submit=True):
            data = _creator_fields({}, "new")
            if st.form_submit_button("Add creator", type="primary"):
                db.add_creator(data)
                st.success(f"Added {data['name']}.")
                st.rerun()
    with right, st.expander("Edit or delete a creator"):
        if creators.empty:
            st.caption("No creators yet.")
        else:
            options = dict(zip(creators["id"], creators["name"]))
            chosen = st.selectbox("Creator", list(options), format_func=options.get, key="edit_creator_id")
            current = db.creator(int(chosen))
            with st.form(f"edit_creator_{chosen}"):
                data = _creator_fields(current, f"edit{chosen}")
                if st.form_submit_button("Save changes", type="primary"):
                    db.update_creator(int(chosen), data)
                    st.success("Saved.")
                    st.rerun()
            confirm = st.checkbox("I want to delete this creator and their campaign history", key=f"del_creator_{chosen}")
            if st.button("Delete creator", disabled=not confirm):
                db.delete_creator(int(chosen))
                st.rerun()

    with st.expander("Import or export CSV"):
        st.markdown(
            "Columns: `" + "`, `".join(CREATOR_COLUMNS) + "`. Only `name` is required. Comma or semicolon "
            "separators both work; decimal commas are fine. Region must be one of the 15 counties from 2024. "
            "Rows whose name already exists update that creator."
        )
        c1, c2 = st.columns(2)
        c1.download_button(
            "Download empty template", dataframe_csv_bytes(creator_template()), "influencesignal-creators-template.csv",
            "text/csv",
        )
        c2.download_button(
            "Export roster CSV", dataframe_csv_bytes(creators.drop(columns=["id", "is_demo"], errors="ignore")),
            "influencesignal-creators.csv", "text/csv",
        )
        upload = st.file_uploader("Upload creators (CSV or XLSX)", type=["csv", "xlsx"], key="creator_upload")
        if upload is not None:
            clean, warnings = validate_creators(read_table(upload.name, upload.getvalue()))
            for warning in warnings:
                st.warning(warning)
            st.success(f"{len(clean)} rows passed validation. Review them, then import.")
            st.dataframe(clean, hide_index=True, width="stretch")
            if st.button("Import these creators", type="primary"):
                added, updated = db.import_creators(clean)
                st.success(f"Imported: {added} added, {updated} updated.")


def _creator_fields(current: dict, key: str) -> dict:
    data: dict[str, object] = {}
    data["name"] = st.text_input("Name *", current.get("name", ""), key=f"{key}_name")
    cols = st.columns(2)
    for index, platform in enumerate(PLATFORMS):
        data[platform] = cols[index % 2].text_input(f"{platform.capitalize()} handle", current.get(platform, ""), key=f"{key}_{platform}")
    cols = st.columns(2)
    data["followers"] = cols[0].number_input(
        "Followers (main platform)", min_value=0, step=500, value=int_or_none(current.get("followers")),
        placeholder="unknown", key=f"{key}_followers",
    )
    data["engagement_rate"] = cols[1].number_input(
        "Engagement rate %", min_value=0.0, max_value=100.0, step=0.1,
        value=float_or_none(current.get("engagement_rate")), placeholder="unknown", key=f"{key}_er",
    )
    data["niche_tags"] = st.text_input("Niche tags (comma separated)", current.get("niche_tags", ""), key=f"{key}_tags")
    region_options = ["", *FYLKER]
    data["region"] = st.selectbox(
        "Region (fylke)", region_options,
        index=region_options.index(current.get("region")) if current.get("region") in region_options else 0,
        key=f"{key}_region",
    )
    cols = st.columns(2)
    data["contact_email"] = cols[0].text_input("E-mail", current.get("contact_email", ""), key=f"{key}_email")
    data["contact_phone"] = cols[1].text_input("Phone", current.get("contact_phone", ""), key=f"{key}_phone")
    data["rate_card"] = st.text_input("Rate card", current.get("rate_card", ""), key=f"{key}_rate")
    data["notes"] = st.text_area("Notes", current.get("notes", ""), key=f"{key}_notes", height=80)
    return data
