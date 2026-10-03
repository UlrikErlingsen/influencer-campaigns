"""Shared Streamlit shell for Influence Signal: workspace, namespaced keys, notes and small display helpers.

Every session-state and widget key goes through ``k()`` (prefixed with the slug ``influence:``) so the app can share
one Streamlit session with the other Signal apps inside Signal Hub.

Hub mode (``SIGNAL_HUB=1``): the workspace is one private in-memory SQLite database per browser session, seeded
with the fictional demo. Nothing is read from or written to disk, and the database-folder settings are off.
"""

from __future__ import annotations

from datetime import date
from html import escape
import os
from pathlib import Path
import traceback

import pandas as pd
import streamlit as st

from influencesignal import DISCLAIMER
from influencesignal.compliance import (
    STATUS_COMPLETE,
    STATUS_ISSUE,
    STATUS_MISSING,
    STATUS_NOT_PUBLISHED,
    STATUS_OVERRIDE,
)
from influencesignal.demo import DEMO_NOTICE, load_demo
from influencesignal.errors import DataProblem, friendly_message
from influencesignal.rules import DEFAULT_RULES_PATH, load_rules
from influencesignal.storage import MEMORY, Store, default_db_path
from influencesignal.ui import signal_theme as sig
from influencesignal.utm import PLATFORMS

NS = "influence"  # app slug: namespace for session-state and widget keys
KEY = NS  # Signal theme key: Influence Signal, Market family
ACCENT = sig.app(KEY)["fam"]["600"]  # own/highlighted chart series
MARK_SVG = sig.ASSETS / "marks" / f"{sig.app(KEY)['slug']}-mark.svg"
STATUS_ICONS = {
    STATUS_COMPLETE: "✅",
    STATUS_OVERRIDE: "📝",
    STATUS_ISSUE: "⚠️",
    STATUS_MISSING: "⏳",
    STATUS_NOT_PUBLISHED: "·",
}
GOAL_METRIC = {"awareness": "cpm_nok", "traffic": "cpc_nok", "sales": "cost_per_redemption_nok"}
# Large tables: the browser gets a preview, not millions of rows; pick lists get the first matches, not the roster.
PREVIEW_ROWS = 1_000
OPTION_LIMIT = 2_000
HUB_WORKSPACE_NOTE = (
    "**Signal Hub demo workspace.** This session keeps its data in memory only, seeded with the fictional demo; "
    "nothing is saved and it is gone when you close the tab. Database folders are off in Signal Hub — run the app "
    "locally to keep a SQLite workspace on your own computer."
)


def k(name: str) -> str:
    """Namespace a session-state or widget key with the app slug, so apps can share one Hub session."""
    return f"{NS}:{name}"


def hub_mode() -> bool:
    """True inside Signal Hub: in-memory workspace only, no disk, no local workspace, no network."""
    return os.environ.get("SIGNAL_HUB") == "1"


@st.cache_resource(show_spinner=False)
def open_store(path: str) -> Store:
    db_path = Path(path)
    is_new = not db_path.exists()
    store = Store(db_path)
    if is_new and os.getenv("INFLUENCESIGNAL_NO_DEMO") != "1" and store.is_empty():
        load_demo(store, current_rules())
    return store


def rules_path() -> Path:
    if hub_mode():
        return DEFAULT_RULES_PATH  # the packaged rules; never a local file named by the environment
    custom = os.getenv("INFLUENCESIGNAL_RULES", "").strip()
    return Path(custom) if custom else DEFAULT_RULES_PATH


@st.cache_resource(show_spinner=False)
def _load_rules_cached(path: str, modified: float):
    return load_rules(path)


def current_rules():
    path = rules_path()
    modified = path.stat().st_mtime if path.exists() else 0.0
    return _load_rules_cached(str(path), modified)


def current_db_path() -> str:
    if k("db_path") not in st.session_state:
        st.session_state[k("db_path")] = str(default_db_path().resolve())
    return st.session_state[k("db_path")]


def hub_store() -> Store:
    """This session's private in-memory workspace, created with the fictional demo on first use."""
    if k("memory_store") not in st.session_state:
        memory = Store(MEMORY)
        load_demo(memory, current_rules())
        st.session_state[k("memory_store")] = memory
    return st.session_state[k("memory_store")]


def store() -> Store:
    if hub_mode():
        return hub_store()
    return open_store(current_db_path())


def open_workspace() -> Store | None:
    """The workspace for this run. If the chosen folder is unusable, fall back to the default so Settings stays
    reachable; returns None only when even the default cannot be opened (the error is shown)."""
    try:
        return store()
    except Exception as exc:  # pragma: no cover - only on unusable folders
        show_error(exc)
        if hub_mode():
            return None
        default_path = str(default_db_path().resolve())
        if st.session_state.get(k("db_path")) == default_path:
            return None
        st.session_state[k("db_path")] = default_path
        st.warning(f"Switched back to the default database: {default_path}")
        return store()


def show_error(exc: Exception) -> None:
    """Render a useful error while keeping tracebacks opt-in."""
    st.error(friendly_message(exc))
    if not isinstance(exc, (DataProblem, ValueError)) and os.getenv("INFLUENCESIGNAL_DEBUG") == "1":
        with st.expander("Technical details"):
            st.code("".join(traceback.format_exception(exc)))


def legal_note() -> None:
    sig.note("warn", f"**{DISCLAIMER}**")


def demo_note(is_demo: bool) -> None:
    if is_demo:
        sig.note("info", f"**Demo data.** {DEMO_NOTICE}")


def hub_note() -> None:
    """Explain the in-memory workspace where a disk feature is off (Signal Hub only)."""
    if hub_mode():
        sig.note("muted", HUB_WORKSPACE_NOTE)


def lane_title(stage: str, count: int) -> None:
    """Pipeline lane heading (stage name and card count) in the Signal accent."""
    st.markdown(
        f'<div class="lane-title" style="font-size:.74rem;font-weight:800;letter-spacing:.1em;text-transform:uppercase;'
        f'border-bottom:3px solid var(--sg-a600);padding-bottom:.3rem;margin-bottom:.5rem">{escape(stage)}'
        f'<span style="color:var(--sg-a700);padding-left:.3rem">{count}</span></div>',
        unsafe_allow_html=True,
    )


def creator_card(name: str, flags: str, meta_lines: list[str]) -> None:
    """Pipeline card text. Name and meta lines are escaped here; flags are fixed status icons."""
    meta = "<br>".join(escape(line) for line in meta_lines)
    st.markdown(
        f'<div class="card-name" style="font-weight:800;line-height:1.2">{escape(name)} {flags}</div>'
        f'<div class="card-meta" style="font-size:.76rem;color:var(--sg-muted);line-height:1.35">{meta}</div>',
        unsafe_allow_html=True,
    )


def preview_table(frame: pd.DataFrame, **kwargs) -> None:
    """``st.dataframe`` for tables that can be huge: shows the first PREVIEW_ROWS rows and says so."""
    if len(frame) > PREVIEW_ROWS:
        st.caption(
            f"Showing the first {PREVIEW_ROWS:,} of {len(frame):,} rows. Every row is validated and imported; "
            "the preview only keeps the browser responsive."
        )
        frame = frame.head(PREVIEW_ROWS)
    st.dataframe(frame, **kwargs)


def limited_options(options: dict, what: str) -> dict:
    """Cap a pick list at OPTION_LIMIT entries (a roster of millions would freeze the browser), with a visible note."""
    if len(options) <= OPTION_LIMIT:
        return options
    st.caption(f"{len(options):,} {what} — the list shows the first {OPTION_LIMIT:,}. Search to narrow it down.")
    return dict(list(options.items())[:OPTION_LIMIT])


def nok(value: object, decimals: int = 0) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "–"
    return f"{float(value):,.{decimals}f} NOK".replace(",", " ")


def num(value: object, decimals: int = 0) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "–"
    return f"{float(value):,.{decimals}f}".replace(",", " ")


def active_campaign() -> dict | None:
    campaign_id = st.session_state.get(k("campaign_id"))
    if campaign_id is None:
        return None
    try:
        return store().campaign(int(campaign_id))
    except DataProblem:
        return None


def select_campaign_next_run(campaign_id: int | None) -> None:
    """Pages cannot change the sidebar widget after it rendered; queue the change for the next run."""
    st.session_state[k("next_campaign")] = campaign_id


def require_campaign() -> dict | None:
    campaign = active_campaign()
    if campaign is None:
        st.info("Create a campaign on the **2 · Campaigns** page, then choose it in the sidebar.")
    return campaign


def handle_label(row: dict) -> str:
    for platform in PLATFORMS:
        if row.get(platform):
            return f"@{row[platform]} ({platform})"
    return "no handle"


def float_or_none(value: object) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return float(value)


def int_or_none(value: object) -> int | None:
    number = float_or_none(value)
    return None if number is None else int(number)


def date_or_none(text: object) -> date | None:
    try:
        return date.fromisoformat(str(text)) if text else None
    except ValueError:
        return None
