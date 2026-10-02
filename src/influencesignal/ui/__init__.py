"""Influence Signal user interface: the Signal Hub entry point.

The only package under ``influencesignal`` that imports Streamlit (it also holds the Signal theme synced from Signal
Hub, ``signal_theme``). ``render()`` draws the whole app on the current page and never calls ``st.set_page_config``;
the standalone ``app.py`` or Signal Hub owns the page config. With ``SIGNAL_HUB=1`` the workspace is an in-memory
SQLite database per session, seeded with the fictional demo, and nothing touches the disk.
"""

from influencesignal import __version__
from influencesignal.ui import signal_theme
from influencesignal.ui.app import render

APP_INFO = {"product": "Influence Signal", "version": __version__, "repo": "influencer-campaigns", "slug": "influence"}

__all__ = ["APP_INFO", "render", "signal_theme"]
