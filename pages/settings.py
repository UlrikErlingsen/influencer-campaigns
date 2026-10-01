"""Settings & data: workspace folder, demo reload, rules overview."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from influencesignal.demo import load_demo
from influencesignal.ui import signal_theme as sig

from .ui import (
    current_db_path,
    current_rules,
    legal_note,
    open_store,
    rules_path,
    select_campaign_next_run,
    store,
)


def render() -> None:
    sig.header(
        "Settings & data",
        "Your local workspace",
        "Influence Signal saves everything in one SQLite file. Choose where it lives, reload the demo or start empty.",
    )
    db = store()
    st.markdown(f"**Current database:** `{db.path.resolve()}`")
    with st.form("data_dir"):
        folder = st.text_input("Data folder", str(Path(current_db_path()).parent))
        if st.form_submit_button("Use this folder"):
            candidate = str((Path(folder).expanduser() / "influencesignal.db").resolve())
            try:
                open_store(candidate)
            except Exception as exc:
                st.error(f"Could not use that folder, so the current database stays active: {exc}")
            else:
                st.session_state["db_path"] = candidate
                select_campaign_next_run(None)
                st.rerun()
    st.caption("A new folder starts with the fictional demo unless INFLUENCESIGNAL_NO_DEMO=1 is set.")
    cols = st.columns(2)
    with cols[0], st.container(border=True):
        st.markdown("**Reload the fictional demo**")
        st.caption("Replaces everything in the current database with the demo.")
        confirm = st.checkbox("Yes, replace all data with the demo", key="confirm_demo")
        if st.button("Reload demo", disabled=not confirm):
            load_demo(db, current_rules())
            select_campaign_next_run(None)
            st.rerun()
    with cols[1], st.container(border=True):
        st.markdown("**Start empty**")
        st.caption("Deletes every creator, campaign, deliverable and checklist answer in the current database.")
        confirm = st.checkbox("Yes, delete all data in this database", key="confirm_empty")
        if st.button("Delete all data", disabled=not confirm):
            db.clear()
            select_campaign_next_run(None)
            st.rerun()
    st.markdown("#### Compliance rules")
    rules = current_rules()
    st.markdown(f"Loaded from `{rules_path()}` · fetched {rules.fetched} · {len(rules.rules)} rules. "
                "Edit the YAML to change labels, questions or sources; the app picks up changes on the next action.")
    st.dataframe(
        pd.DataFrame([{"id": r.id, "label (no)": r.label_no, "label (en)": r.label_en, "applies when": r.applies_when,
                       "source": r.primary_url or (r.categories[0].url if r.categories else "")} for r in rules.rules]),
        hide_index=True, width="stretch",
    )
    legal_note()
    sig.note(
        "boundary",
        "**Privacy.** Creator names, contact details and fees stay in the SQLite file on this computer. Influence "
        "Signal has no accounts, no telemetry and no external AI calls, and never contacts a social network. You are "
        "the data controller for the personal data you store here; see PRIVACY.md.",
    )
