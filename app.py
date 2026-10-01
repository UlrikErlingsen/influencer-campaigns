"""InfluenceSignal Streamlit application: entry point, navigation and sidebar.

The pages live in ``pages/`` (one module per page, each exposing ``render()``); all logic and storage live in
the ``influencesignal`` package under ``src/``.
"""

from __future__ import annotations

import os

# Keep Arrow serialization stable on macOS. This must be set before Streamlit imports Arrow.
os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")

from pathlib import Path
import sys

import streamlit as st


ROOT = Path(__file__).resolve().parent
for path in (ROOT / "src", ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from influencesignal import DISCLAIMER, __version__
from influencesignal.storage import default_db_path
from pages import (
    campaigns,
    compliance,
    creators,
    deliverables,
    pipeline,
    report,
    results,
    settings,
    welcome,
)
from pages.ui import apply_theme, footer, masthead, show_error, store

# (url slug, title, icon, render function, navigation section)
PAGES = [
    ("welcome", "Welcome", ":material/home:", welcome.render, ""),
    ("creators", "1 · Creators", ":material/groups:", creators.render, "Campaign workflow"),
    ("campaigns", "2 · Campaigns", ":material/campaign:", campaigns.render, "Campaign workflow"),
    ("pipeline", "3 · Pipeline", ":material/view_kanban:", pipeline.render, "Campaign workflow"),
    ("deliverables", "4 · Deliverables", ":material/link:", deliverables.render, "Campaign workflow"),
    ("compliance", "5 · Compliance", ":material/fact_check:", compliance.render, "Campaign workflow"),
    ("results", "6 · Results", ":material/insights:", results.render, "Campaign workflow"),
    ("report", "7 · Report", ":material/summarize:", report.render, "Campaign workflow"),
    ("settings", "Settings & data", ":material/settings:", settings.render, "Workspace"),
]

st.set_page_config(page_title="InfluenceSignal | Influencer campaigns", page_icon="◉", layout="wide")
apply_theme()
logo = ROOT / "assets" / "influencesignal-lockup-dark.svg"
if logo.exists():
    st.logo(str(logo), size="large", icon_image=str(ROOT / "assets" / "influencesignal-mark.svg"))

try:
    db = store()
except Exception as exc:  # pragma: no cover - only on unusable folders
    # Fall back to the default workspace so Settings stays reachable.
    show_error(exc)
    default_path = str(default_db_path().resolve())
    if st.session_state.get("db_path") == default_path:
        st.stop()
    st.session_state["db_path"] = default_path
    st.warning(f"Switched back to the default database: {default_path}")
    db = store()

# ?page=<slug> opens that page first (deep links, screenshots, tests); the navigation menu works as usual.
requested = str(st.query_params.get("page", "")).lower()
if requested not in {slug for slug, *_ in PAGES}:
    requested = "welcome"
sections: dict[str, list] = {}
for slug, title, icon, render, section in PAGES:
    page = st.Page(render, title=title, icon=icon, url_path=slug, default=slug == requested)
    sections.setdefault(section, []).append(page)
current = st.navigation(sections)

with st.sidebar:
    campaigns_frame = db.campaigns()
    if campaigns_frame.empty:
        st.caption("No campaigns yet.")
    else:
        options = dict(zip(campaigns_frame["id"].astype(int), campaigns_frame["name"]))
        requested_campaign = str(st.query_params.get("campaign", ""))
        if "_next_campaign" in st.session_state:
            queued = st.session_state.pop("_next_campaign")
            st.session_state["campaign_id"] = queued if queued in options else next(iter(options))
        if st.session_state.get("campaign_id") not in options:
            by_slug = dict(zip(campaigns_frame["slug"], campaigns_frame["id"].astype(int)))
            st.session_state["campaign_id"] = by_slug.get(requested_campaign, next(iter(options)))
        st.selectbox("Active campaign", list(options), format_func=options.get, key="campaign_id")
    if db.has_demo_data():
        st.info("Fictional demo data loaded. No real person, brand or result.")
    st.caption("Influencer campaigns for Norway, with the label checklist built in.")
    st.caption(f"Influencer campaign manager · v{__version__}")
    st.caption(DISCLAIMER)
    st.caption("Local mode · no telemetry · no external AI calls · no social-network APIs")

masthead()
try:
    current.run()
except Exception as exc:
    show_error(exc)
footer()
