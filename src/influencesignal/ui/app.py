"""Influence Signal Streamlit UI: the page list, sidebar, masthead, footer and ``render()``.

``render()`` draws the whole app on the current page for Signal Hub (and any script): the theme, the sidebar with a
namespaced page radio, the masthead, the selected page and the footer. It never calls ``st.set_page_config`` or
``st.navigation``. The standalone ``app.py`` uses the same page functions and shell pieces with its own
``st.navigation`` menu. Module-level code here only defines constants and functions.
"""

from __future__ import annotations

from typing import Callable

import streamlit as st

from influencesignal import DISCLAIMER, __version__
from influencesignal.storage import Store
from influencesignal.ui import signal_theme as sig
from influencesignal.ui.pages import (
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
from influencesignal.ui.shell import NS, hub_mode, k, open_workspace, show_error

# (url slug, title, icon, render function, navigation section)
PAGES: list[tuple[str, str, str, Callable[[], None], str]] = [
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
PAGE_TITLES = {title: render_page for _, title, _, render_page, _ in PAGES}
SIDEBAR_TAGLINE = "Influencer campaigns for Norway, with the label checklist built in."
MASTHEAD_PROMISES = ["Cost per result", "Norwegian label checklist", "Local data"]
MASTHEAD_KICKER = "SHORTLIST → PUBLISH → CHECK → REPORT"


def campaign_sidebar(db: Store, requested_slug: str = "") -> None:
    """Active-campaign selector and status captions (call inside ``with st.sidebar``)."""
    campaigns_frame = db.campaigns()
    if campaigns_frame.empty:
        st.caption("No campaigns yet.")
    else:
        options = dict(zip(campaigns_frame["id"].astype(int), campaigns_frame["name"]))
        if k("next_campaign") in st.session_state:
            queued = st.session_state.pop(k("next_campaign"))
            st.session_state[k("campaign_id")] = queued if queued in options else next(iter(options))
        if st.session_state.get(k("campaign_id")) not in options:
            by_slug = dict(zip(campaigns_frame["slug"], campaigns_frame["id"].astype(int)))
            st.session_state[k("campaign_id")] = by_slug.get(requested_slug, next(iter(options)))
        st.selectbox("Active campaign", list(options), format_func=options.get, key=k("campaign_id"))
    if db.has_demo_data():
        st.info("Fictional demo data loaded. No real person, brand or result.")
    st.caption(f"Influencer campaign manager · v{__version__}")
    st.caption(DISCLAIMER)
    if hub_mode():
        st.caption("Signal Hub · in-memory demo workspace · nothing saved · no external AI calls · "
                   "no social-network APIs")
    else:
        st.caption("Local mode · no telemetry · no external AI calls · no social-network APIs")


def masthead() -> None:
    sig.masthead(NS, MASTHEAD_PROMISES, kicker=MASTHEAD_KICKER)


def footer() -> None:
    sig.footer(NS, __version__, DISCLAIMER)


def run_page(page: Callable[[], None]) -> None:
    """Run one page; errors show the friendly message instead of a traceback."""
    try:
        page()
    except Exception as exc:
        show_error(exc)


def render() -> None:
    """Draw the whole Influence Signal app on the current page. Never calls st.set_page_config or st.navigation."""
    sig.apply(NS)
    sig.sidebar_brand(NS, SIDEBAR_TAGLINE)
    with st.sidebar:
        title = st.radio("Page", list(PAGE_TITLES), key=k("page"))
    db = open_workspace()
    if db is not None:
        with st.sidebar:
            st.markdown("---")
            campaign_sidebar(db)
    masthead()
    if db is not None:
        run_page(PAGE_TITLES[title])
    footer()
