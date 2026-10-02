"""Influence Signal standalone entry point: page config, st.navigation menu, sidebar and the selected page.

The pages live in ``src/influencesignal/ui/pages/`` (one module per page, each exposing ``render()``) and the shared
shell in ``src/influencesignal/ui/``; Signal Hub draws the same pages through ``influencesignal.ui.render()``, which
uses a sidebar radio instead of ``st.navigation``. All logic and storage live in the ``influencesignal`` package.
"""

from __future__ import annotations

import os

# Keep Arrow serialization stable on macOS. This must be set before Streamlit imports Arrow.
os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")

from pathlib import Path
import sys

import streamlit as st


SRC = Path(__file__).resolve().parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from influencesignal.ui import signal_theme as sig
from influencesignal.ui.app import PAGES, campaign_sidebar, footer, masthead, run_page
from influencesignal.ui.shell import KEY, MARK_SVG, open_workspace

st.set_page_config(**sig.page_config(KEY, "Influencer campaigns"))
sig.apply(KEY)
if MARK_SVG.exists():
    st.logo(str(MARK_SVG), size="large", icon_image=str(MARK_SVG))

db = open_workspace()
if db is None:  # pragma: no cover - only when even the default folder is unusable
    st.stop()

# ?page=<slug> opens that page first (deep links, screenshots, tests); the navigation menu works as usual.
requested = str(st.query_params.get("page", "")).lower()
if requested not in {slug for slug, *_ in PAGES}:
    requested = "welcome"
sections: dict[str, list] = {}
for slug, title, icon, render_page, section in PAGES:
    page = st.Page(render_page, title=title, icon=icon, url_path=slug, default=slug == requested)
    sections.setdefault(section, []).append(page)
current = st.navigation(sections)

with st.sidebar:
    campaign_sidebar(db, str(st.query_params.get("campaign", "")))
    st.caption("Influencer campaigns for Norway, with the label checklist built in.")

masthead()
run_page(current.run)
footer()
