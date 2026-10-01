"""Shared Streamlit shell for InfluenceSignal: theme, workspace, masthead and small display helpers.

Streamlit code lives only in app.py and pages/. Everything here calls the influencesignal package.
"""

from __future__ import annotations

import base64
from datetime import date
import os
from pathlib import Path
import traceback

import pandas as pd
import streamlit as st

from influencesignal import DISCLAIMER, __version__
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
from influencesignal.storage import Store, default_db_path
from influencesignal.utm import PLATFORMS

ROOT = Path(__file__).resolve().parents[1]

COLORS = {
    "ink": "#17322E",
    "teal": "#173C3A",
    "coral": "#D95B40",
    "mint": "#83D2B4",
    "gold": "#F2C66D",
    "paper": "#F8F5ED",
    "muted": "#59716C",
}
mark_path = ROOT / "assets" / "influencesignal-mark.svg"
MARK_URI = (
    "data:image/svg+xml;base64," + base64.b64encode(mark_path.read_bytes()).decode("ascii")
    if mark_path.exists()
    else ""
)
STATUS_ICONS = {
    STATUS_COMPLETE: "✅",
    STATUS_OVERRIDE: "📝",
    STATUS_ISSUE: "⚠️",
    STATUS_MISSING: "⏳",
    STATUS_NOT_PUBLISHED: "·",
}
GOAL_METRIC = {"awareness": "cpm_nok", "traffic": "cpc_nok", "sales": "cost_per_redemption_nok"}

THEME_CSS = """
    <style>
    :root {
        --ps-ink:#17322e; --ps-deep:#102c2a; --ps-teal:#173c3a;
        --ps-coral:#d95b40; --ps-mint:#83d2b4; --ps-gold:#f2c66d;
        --ps-paper:#f8f5ed; --ps-line:rgba(23,50,46,.14);
    }
    [data-testid="stAppViewContainer"] {
        background:radial-gradient(circle at 94% 2%,rgba(131,210,180,.17),transparent 28rem),
                   radial-gradient(circle at 3% 93%,rgba(242,198,109,.14),transparent 25rem),
                   linear-gradient(180deg,#fbf9f3 0%,var(--ps-paper) 100%);
    }
    [data-testid="stHeader"] { background:rgba(248,245,237,.78); }
    [data-testid="stSidebar"] { background:linear-gradient(165deg,#173c3a 0%,#102c2a 65%,#0c2422 100%); }
    [data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p,[data-testid="stSidebar"] label,[data-testid="stSidebar"] span { color:#f8f5ed; }
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] p { color:#b9cbc5; }
    [data-testid="stSidebar"] [data-testid="stAlert"] { background:rgba(242,198,109,.12); }
    [data-testid="stSidebar"] [data-baseweb="select"] span { color:var(--ps-ink); }
    [data-testid="stSidebar"] button {
        background:rgba(255,255,255,.08); color:#f8f5ed !important; border-color:rgba(255,255,255,.23);
    }
    [data-testid="stSidebar"] button * { color:#f8f5ed !important; }
    .block-container { max-width:1320px; padding-top:4.4rem; padding-bottom:4rem; }
    h1,h2,h3 { color:var(--ps-ink); letter-spacing:-.025em; }
    a { color:#9b3e2b; }
    [data-testid="stMetric"] {
        background:rgba(255,255,255,.75); border:1px solid var(--ps-line); border-radius:16px;
        padding:1rem 1.05rem; box-shadow:0 8px 28px rgba(23,50,46,.045);
    }
    [data-testid="stMetricValue"] { color:var(--ps-ink); font-size:clamp(1.2rem,2.1vw,1.7rem); }
    .stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {
        background:linear-gradient(135deg,#e26748,#c94c34); color:white; border:0;
        box-shadow:0 8px 20px rgba(217,91,64,.22); font-weight:750;
    }
    button:focus-visible,a:focus-visible,input:focus-visible,[role="radio"]:focus-visible {
        outline:3px solid #f2c66d !important; outline-offset:2px;
    }
    [data-testid="stExpander"],[data-testid="stAlert"],[data-testid="stVerticalBlockBorderWrapper"] { border-radius:14px; }
    .ps-lockup { display:flex; align-items:center; gap:.65rem; }
    .ps-mark { width:38px; height:38px; }
    .ps-name { color:white; font-size:1.28rem; line-height:1; font-weight:850; letter-spacing:-.04em; }
    .ps-name span { color:#f2c66d !important; }
    .ps-tag { margin:.55rem 0 0 !important; color:#b9cbc5 !important; font-size:.77rem; line-height:1.4; }
    .ps-masthead {
        display:flex; justify-content:space-between; align-items:center; gap:1rem; padding:.72rem 1rem .72rem .78rem;
        margin-bottom:1.35rem; background:rgba(255,255,255,.65); border:1px solid var(--ps-line);
        border-radius:18px; box-shadow:0 10px 36px rgba(23,50,46,.05);
    }
    .ps-masthead .ps-mark { width:48px; height:48px; }
    .ps-wordmark { color:var(--ps-ink); font-weight:850; letter-spacing:-.045em; font-size:1.55rem; line-height:1; }
    .ps-wordmark span { color:var(--ps-coral); }
    .ps-kicker { margin-top:.32rem; color:#59716c; font-size:.67rem; font-weight:800; letter-spacing:.13em; }
    .ps-promise { color:#47645e; font-size:.78rem; font-weight:700; white-space:nowrap; }
    .ps-promise span { color:var(--ps-coral); padding:0 .3rem; }
    .ps-hero {
        position:relative; overflow:hidden; padding:clamp(1.7rem,4vw,3.4rem); margin-bottom:1.3rem;
        background:linear-gradient(135deg,#173c3a 0%,#102c2a 75%); border-radius:26px;
        box-shadow:0 18px 50px rgba(23,50,46,.17);
    }
    .ps-hero:after {
        content:""; position:absolute; width:330px; height:330px; right:-105px; top:-148px;
        border-radius:50%; border:56px solid rgba(131,210,180,.12);
    }
    .ps-eyebrow { color:#83d2b4; font-size:.72rem; font-weight:850; letter-spacing:.16em; }
    .ps-hero h1 { color:white; font-size:clamp(2.1rem,4.6vw,4.3rem); line-height:.98; margin:.75rem 0 1rem; max-width:980px; }
    .ps-hero h1 em { color:#f2c66d; font-style:normal; }
    .ps-hero p { color:#d7e3df; font-size:1.06rem; line-height:1.6; max-width:820px; }
    .ps-pills { display:flex; flex-wrap:wrap; gap:.55rem; margin-top:1.15rem; }
    .ps-pill {
        padding:.4rem .72rem; border:1px solid rgba(255,255,255,.16); border-radius:999px;
        color:#f8f5ed; font-size:.78rem; font-weight:700; background:rgba(255,255,255,.055);
    }
    .ps-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:1rem; margin:1.2rem 0 1.5rem; }
    .ps-card {
        height:100%; padding:1.2rem 1.2rem 1rem; background:rgba(255,255,255,.68);
        border:1px solid var(--ps-line); border-radius:18px;
    }
    .ps-card b { color:var(--ps-coral); font-size:.72rem; letter-spacing:.12em; }
    .ps-card h3 { margin:.4rem 0 .5rem; }
    .ps-card p { color:#59716c; font-size:.9rem; line-height:1.55; }
    .pulse-kicker {font-size:.72rem;font-weight:800;letter-spacing:.14em;color:var(--ps-coral);text-transform:uppercase;}
    .pulse-title {font-size:2.15rem;line-height:1.08;font-weight:850;color:var(--ps-ink);margin:.2rem 0 .6rem;}
    .pulse-subtitle {font-size:1.02rem;color:#526a65;max-width:880px;margin-bottom:1.2rem;line-height:1.55;}
    .boundary {border-left:4px solid var(--ps-mint);background:rgba(255,255,255,.62);border-radius:0 14px 14px 0;padding:1rem 1.1rem;color:#47645e;margin:.6rem 0 1rem;}
    .warning-box {border-left:4px solid var(--ps-gold);background:rgba(242,198,109,.17);border-radius:0 14px 14px 0;padding:1rem 1.1rem;color:#604b1f;margin:.6rem 0 1rem;}
    .legal-note {border-left:4px solid var(--ps-gold);background:rgba(242,198,109,.2);border-radius:0 12px 12px 0;padding:.55rem .9rem;color:#604b1f;font-weight:750;margin:.2rem 0 1rem;}
    .demo-note {border-left:4px solid var(--ps-mint);background:rgba(131,210,180,.16);border-radius:0 12px 12px 0;padding:.55rem .9rem;color:#2d5149;margin:.2rem 0 1rem;font-size:.9rem;}
    .lane-title {font-size:.74rem;font-weight:850;letter-spacing:.1em;text-transform:uppercase;color:var(--ps-ink);
        border-bottom:3px solid var(--ps-mint);padding-bottom:.3rem;margin-bottom:.5rem;}
    .lane-title span {color:var(--ps-coral);padding-left:.3rem;}
    .card-name {font-weight:800;color:var(--ps-ink);line-height:1.2;}
    .card-meta {font-size:.76rem;color:#59716c;line-height:1.35;}
    .small-note {font-size:.86rem;color:#617670;}
    .ps-footer { margin-top:3.2rem; padding-top:1rem; border-top:1px solid var(--ps-line); color:#617670; font-size:.76rem; text-align:center; }
    .ps-footer span { color:var(--ps-coral); padding:0 .38rem; }
    @media (max-width:1050px) { .ps-grid{grid-template-columns:1fr} }
    @media (max-width:760px) { .ps-promise{display:none}.ps-hero{border-radius:20px}.block-container{padding-top:3.5rem} }
    @media (prefers-reduced-motion:reduce) { * { scroll-behavior:auto !important; transition:none !important; } }
    </style>
    """


def apply_theme() -> None:
    st.markdown(THEME_CSS, unsafe_allow_html=True)



@st.cache_resource(show_spinner=False)
def open_store(path: str) -> Store:
    db_path = Path(path)
    is_new = not db_path.exists()
    store = Store(db_path)
    if is_new and os.getenv("INFLUENCESIGNAL_NO_DEMO") != "1" and store.is_empty():
        load_demo(store, current_rules())
    return store


def rules_path() -> Path:
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
    if "db_path" not in st.session_state:
        st.session_state["db_path"] = str(default_db_path().resolve())
    return st.session_state["db_path"]


def store() -> Store:
    return open_store(current_db_path())


def show_error(exc: Exception) -> None:
    """Render a useful error while keeping tracebacks opt-in."""
    st.error(friendly_message(exc))
    if not isinstance(exc, (DataProblem, ValueError)) and os.getenv("INFLUENCESIGNAL_DEBUG") == "1":
        with st.expander("Technical details"):
            st.code("".join(traceback.format_exception(exc)))


def masthead() -> None:
    mark = f'<img class="ps-mark" src="{MARK_URI}" alt="">' if MARK_URI else ""
    st.markdown(
        f"""
        <div class="ps-masthead">
          <div class="ps-lockup">{mark}<div><div class="ps-wordmark">Influence<span>Signal</span></div>
          <div class="ps-kicker">SHORTLIST → PUBLISH → CHECK → REPORT</div></div></div>
          <div class="ps-promise">Cost per result <span>◆</span> Norwegian label checklist <span>◆</span> Local data</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def footer() -> None:
    st.markdown(
        f'<div class="ps-footer">InfluenceSignal v{__version__} <span>◆</span> {DISCLAIMER} '
        '<span>◆</span> Part of the Signal suite <span>◆</span> AGPL-3.0-or-later</div>',
        unsafe_allow_html=True,
    )


def page_header(kicker: str, title: str, subtitle: str) -> None:
    st.markdown(f'<div class="pulse-kicker">{kicker}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="pulse-title">{title}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="pulse-subtitle">{subtitle}</div>', unsafe_allow_html=True)


def legal_note() -> None:
    st.markdown(f'<div class="legal-note">{DISCLAIMER}</div>', unsafe_allow_html=True)


def demo_note(is_demo: bool) -> None:
    if is_demo:
        st.markdown(f'<div class="demo-note"><strong>Demo data.</strong> {DEMO_NOTICE}</div>', unsafe_allow_html=True)


def nok(value: object, decimals: int = 0) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "–"
    return f"{float(value):,.{decimals}f} NOK".replace(",", " ")


def num(value: object, decimals: int = 0) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "–"
    return f"{float(value):,.{decimals}f}".replace(",", " ")


def active_campaign() -> dict | None:
    campaign_id = st.session_state.get("campaign_id")
    if campaign_id is None:
        return None
    try:
        return store().campaign(int(campaign_id))
    except DataProblem:
        return None


def select_campaign_next_run(campaign_id: int | None) -> None:
    """Pages cannot change the sidebar widget after it rendered; queue the change for the next run."""
    st.session_state["_next_campaign"] = campaign_id


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
