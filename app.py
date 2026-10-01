"""CreatorSignal Streamlit application."""

from __future__ import annotations

import os

# Keep Arrow serialization stable on macOS. This must be set before Streamlit imports Arrow.
os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")

import base64
from datetime import date
from pathlib import Path
import sys
import traceback

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from creatorsignal import DISCLAIMER, __version__
from creatorsignal.compliance import (
    STATUS_COMPLETE,
    STATUS_ISSUE,
    STATUS_MISSING,
    STATUS_NOT_PUBLISHED,
    STATUS_OVERRIDE,
    MIN_OVERRIDE_CHARS,
    applicable_rules,
    campaign_restricted_categories,
    checklist_status,
    paid_gate,
)
from creatorsignal.demo import DEMO_NOTICE, load_demo
from creatorsignal.errors import DataProblem, GateBlocked, friendly_message
from creatorsignal.io import (
    CREATOR_COLUMNS,
    FYLKER,
    RESULT_IMPORT_COLUMNS,
    creator_template,
    dataframe_csv_bytes,
    read_table,
    validate_creators,
    validate_results,
)
from creatorsignal.metrics import GENERAL_NOTES, METRIC_LABELS, RESULT_COLUMNS, row_notes, summarize_results
from creatorsignal.report import build_html, build_report, build_xlsx
from creatorsignal.rules import DEFAULT_RULES_PATH, load_rules
from creatorsignal.storage import CATEGORIES, FORMATS, GOALS, STAGES, Store, default_db_path
from creatorsignal.utm import PLATFORMS, build_tracked_url, creator_token


COLORS = {
    "ink": "#17322E",
    "teal": "#173C3A",
    "coral": "#D95B40",
    "mint": "#83D2B4",
    "gold": "#F2C66D",
    "paper": "#F8F5ED",
    "muted": "#59716C",
}
mark_path = ROOT / "assets" / "creatorsignal-mark.svg"
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


st.set_page_config(page_title="CreatorSignal | Influencer campaigns", page_icon="◉", layout="wide")

st.markdown(
    """
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
    """,
    unsafe_allow_html=True,
)


# ── workspace ────────────────────────────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def _open_store(path: str) -> Store:
    db_path = Path(path)
    is_new = not db_path.exists()
    store = Store(db_path)
    if is_new and os.getenv("CREATORSIGNAL_NO_DEMO") != "1" and store.is_empty():
        load_demo(store, _rules())
    return store


def _rules_path() -> Path:
    custom = os.getenv("CREATORSIGNAL_RULES", "").strip()
    return Path(custom) if custom else DEFAULT_RULES_PATH


@st.cache_resource(show_spinner=False)
def _load_rules_cached(path: str, modified: float):
    return load_rules(path)


def _rules():
    path = _rules_path()
    modified = path.stat().st_mtime if path.exists() else 0.0
    return _load_rules_cached(str(path), modified)


def _db_path() -> str:
    if "db_path" not in st.session_state:
        st.session_state["db_path"] = str(default_db_path().resolve())
    return st.session_state["db_path"]


def store() -> Store:
    return _open_store(_db_path())


def show_error(exc: Exception) -> None:
    """Render a useful error while keeping tracebacks opt-in."""
    st.error(friendly_message(exc))
    if not isinstance(exc, (DataProblem, ValueError)) and os.getenv("CREATORSIGNAL_DEBUG") == "1":
        with st.expander("Technical details"):
            st.code("".join(traceback.format_exception(exc)))


# ── shell ────────────────────────────────────────────────────────────────────────────────────────
def masthead() -> None:
    mark = f'<img class="ps-mark" src="{MARK_URI}" alt="">' if MARK_URI else ""
    st.markdown(
        f"""
        <div class="ps-masthead">
          <div class="ps-lockup">{mark}<div><div class="ps-wordmark">Creator<span>Signal</span></div>
          <div class="ps-kicker">SHORTLIST → PUBLISH → CHECK → REPORT</div></div></div>
          <div class="ps-promise">Cost per result <span>◆</span> Norwegian label checklist <span>◆</span> Local data</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def footer() -> None:
    st.markdown(
        f'<div class="ps-footer">CreatorSignal v{__version__} <span>◆</span> {DISCLAIMER} '
        '<span>◆</span> Part of the Signal suite <span>◆</span> AGPL-3.0-or-later</div>',
        unsafe_allow_html=True,
    )


def _header(kicker: str, title: str, subtitle: str) -> None:
    st.markdown(f'<div class="pulse-kicker">{kicker}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="pulse-title">{title}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="pulse-subtitle">{subtitle}</div>', unsafe_allow_html=True)


def _legal_note() -> None:
    st.markdown(f'<div class="legal-note">{DISCLAIMER}</div>', unsafe_allow_html=True)


def _demo_note(is_demo: bool) -> None:
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


def _active_campaign() -> dict | None:
    campaign_id = st.session_state.get("campaign_id")
    if campaign_id is None:
        return None
    try:
        return store().campaign(int(campaign_id))
    except DataProblem:
        return None


def _select_campaign_next_run(campaign_id: int | None) -> None:
    """Pages cannot change the sidebar widget after it rendered; queue the change for the next run."""
    st.session_state["_next_campaign"] = campaign_id


def _require_campaign() -> dict | None:
    campaign = _active_campaign()
    if campaign is None:
        st.info("Create a campaign on the **2 · Campaigns** page, then choose it in the sidebar.")
    return campaign


def _handle(row: dict) -> str:
    for platform in PLATFORMS:
        if row.get(platform):
            return f"@{row[platform]} ({platform})"
    return "no handle"


def _date_or_none(text: object) -> date | None:
    try:
        return date.fromisoformat(str(text)) if text else None
    except ValueError:
        return None


# ── pages ────────────────────────────────────────────────────────────────────────────────────────
def page_welcome() -> None:
    st.markdown(
        """
        <section class="ps-hero">
          <div class="ps-eyebrow">INFLUENCER CAMPAIGNS · NORWAY</div>
          <h1>Which creators delivered — and was every post <em>labelled properly?</em></h1>
          <p>Run the whole campaign in one local app: roster, pipeline, deliverables with tracked links and codes,
          results at cost per result, and a Norwegian advertising-label checklist on every published post.</p>
          <div class="ps-pills"><span class="ps-pill">creator roster</span><span class="ps-pill">kanban pipeline</span>
          <span class="ps-pill">UTM links & codes</span><span class="ps-pill">«reklame» checklist</span>
          <span class="ps-pill">retouching mark</span><span class="ps-pill">CPM · CPC · ROAS</span>
          <span class="ps-pill">XLSX + one-page report</span></div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    _demo_note(store().has_demo_data())
    st.markdown(
        """
        <div class="ps-grid">
          <div class="ps-card"><b>01 · RUN</b><h3>One pipeline per campaign</h3><p>Shortlist → Contacted →
          Negotiating → Contracted → Content in review → Published → Paid → Reported. Every move is logged.</p></div>
          <div class="ps-card"><b>02 · CHECK</b><h3>A checklist before payment</h3><p>Each published post gets the
          Norwegian advertising-label and retouching-mark checklist. A creator cannot be marked Paid until it is
          complete or someone writes down why not.</p></div>
          <div class="ps-card"><b>03 · LEARN</b><h3>Cost per result, honestly</h3><p>CPM, CPC, cost per redemption
          and ROAS per creator and campaign — with plain notes on what they cannot show. Codes leak; numbers are
          not causes.</p></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("### Try the fictional demo")
    st.markdown(
        "1. **3 · Pipeline** — see ten creators across the stages of *Fjellbrus Høstfjell 2026*. "
        "Try moving *Mathias R. (demo)* to **Paid**: the gate refuses because his post has no advertising label.\n"
        "2. **5 · Compliance** — open the warning, read the rule, its source and quote.\n"
        "3. **6 · Results** — switch to *Fjellbrus Vårløp 2026* in the sidebar and compare cost per result by creator.\n"
        "4. **7 · Report** — download the XLSX workbook and the one-page HTML summary."
    )
    _legal_note()
    st.markdown(
        '<div class="boundary"><strong>Boundaries.</strong> CreatorSignal never contacts creators, never calls a '
        "social-network API and never scrapes profiles. Everything you type stays in a SQLite file on this "
        "computer. The checklist records what your team checked; it is not a legal assessment.</div>",
        unsafe_allow_html=True,
    )


def page_creators() -> None:
    _header(
        "1 · Creators",
        "Creator roster",
        "Everyone you might work with, across campaigns. Enter figures manually or import a CSV. Follower counts and "
        "engagement rates are whatever you or the creator report — CreatorSignal never fetches them.",
    )
    db = store()
    creators = db.creators()
    _demo_note(bool(creators["is_demo"].any()) if not creators.empty else False)

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
        use_container_width=True,
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
            "Download empty template", dataframe_csv_bytes(creator_template()), "creatorsignal-creators-template.csv",
            "text/csv",
        )
        c2.download_button(
            "Export roster CSV", dataframe_csv_bytes(creators.drop(columns=["id", "is_demo"], errors="ignore")),
            "creatorsignal-creators.csv", "text/csv",
        )
        upload = st.file_uploader("Upload creators (CSV or XLSX)", type=["csv", "xlsx"], key="creator_upload")
        if upload is not None:
            clean, warnings = validate_creators(read_table(upload.name, upload.getvalue()))
            for warning in warnings:
                st.warning(warning)
            st.success(f"{len(clean)} rows passed validation. Review them, then import.")
            st.dataframe(clean, hide_index=True, use_container_width=True)
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
        "Followers (main platform)", min_value=0, step=500, value=int(current.get("followers") or 0), key=f"{key}_followers"
    )
    data["engagement_rate"] = cols[1].number_input(
        "Engagement rate %", min_value=0.0, max_value=100.0, step=0.1,
        value=float(current.get("engagement_rate") or 0.0), key=f"{key}_er",
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


def page_campaigns() -> None:
    _header(
        "2 · Campaigns",
        "Campaigns",
        "Name, brand, goal, budget, dates, brief and the deliverables you expect. The landing page drives every "
        "tracked link; the category decides whether the restricted-category flag appears.",
    )
    db = store()
    campaigns = db.campaigns()
    rules = _rules()
    if not campaigns.empty:
        st.dataframe(
            campaigns[["name", "brand", "goal", "category", "budget_nok", "start_date", "end_date", "slug"]],
            hide_index=True,
            use_container_width=True,
            column_config={"budget_nok": st.column_config.NumberColumn("Budget (NOK)", format="%d")},
        )
    campaign = _active_campaign()
    if campaign is not None:
        _demo_note(bool(campaign["is_demo"]))
        flagged = campaign_restricted_categories(campaign, rules)
        if flagged:
            categories = rules.restricted_categories
            st.warning(
                "Restricted category flagged: "
                + ", ".join(f"[{categories[key].label}]({categories[key].url})" for key in flagged)
                + ". Stricter Norwegian rules apply. CreatorSignal flags this only and never says the campaign is "
                "compliant."
            )
            _legal_note()
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
                _select_campaign_next_run(None)
                st.rerun()
        with st.container(border=True):
            st.markdown(f"**Brief** — {campaign['brief'] or '–'}")
            st.markdown(f"**Deliverables template** — {campaign['deliverables_template'] or '–'}")
            st.markdown(f"**Landing page** — `{campaign['landing_url'] or 'not set'}`")
    with st.expander("Create a new campaign", expanded=campaigns.empty):
        with st.form("new_campaign", clear_on_submit=True):
            data = _campaign_fields({}, "newc")
            if st.form_submit_button("Create campaign", type="primary"):
                _select_campaign_next_run(db.add_campaign(data))
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
        "Budget (NOK)", min_value=0, step=5000, value=int(current.get("budget_nok") or 0), key=f"{key}_budget"
    )
    data["targets_children"] = st.checkbox(
        "This campaign targets children", bool(current.get("targets_children")), key=f"{key}_kids"
    )
    cols = st.columns(2)
    start = cols[0].date_input("Start date", _date_or_none(current.get("start_date")) or date.today(), key=f"{key}_start")
    end = cols[1].date_input("End date", _date_or_none(current.get("end_date")) or date.today(), key=f"{key}_end")
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


def _move_card(engagement_id: int, key: str, previous: str, name: str) -> None:
    target = st.session_state.get(key)
    try:
        store().move_engagement(engagement_id, target, _rules())
        st.session_state["pipeline_flash"] = ("success", f"Moved {name} to {target}.", ())
    except GateBlocked as exc:
        st.session_state["pipeline_flash"] = ("error", f"{name}: {exc}", exc.reasons)
        del st.session_state[key]
    except DataProblem as exc:
        st.session_state["pipeline_flash"] = ("error", str(exc), ())
        del st.session_state[key]


def page_pipeline() -> None:
    _header(
        "3 · Pipeline",
        "Campaign pipeline",
        "Move each creator with the stage selector on their card. Paid and Reported are guarded: every deliverable "
        "needs a complete checklist or a written override reason first.",
    )
    campaign = _require_campaign()
    if campaign is None:
        return
    db, rules = store(), _rules()
    _demo_note(bool(campaign["is_demo"]))
    engagements = db.engagements(int(campaign["id"]))
    deliverables = db.deliverables(int(campaign["id"]))
    committed = float(deliverables["fee_nok"].fillna(0).sum()) if not deliverables.empty else 0.0
    budget = float(campaign["budget_nok"] or 0)
    cols = st.columns(4)
    cols[0].metric("Creators in pipeline", len(engagements))
    cols[1].metric("Budget", nok(budget))
    cols[2].metric("Agreed fees", nok(committed))
    cols[3].metric("Unallocated", nok(budget - committed))

    flash = st.session_state.pop("pipeline_flash", None)
    if flash:
        kind, message, reasons = flash
        (st.success if kind == "success" else st.error)(message)
        for reason in reasons:
            st.markdown(f"- {reason}")
        if kind == "error" and reasons:
            st.caption("Fix it on **5 · Compliance** (answer the checklist or write an override reason).")

    candidates = db.creators()
    candidates = candidates[~candidates["id"].isin(engagements["creator_id"])]
    with st.expander("Add creators to the shortlist"):
        options = dict(zip(candidates["id"], candidates["name"]))
        chosen = st.multiselect("Creators", list(options), format_func=options.get)
        if st.button("Add to shortlist", type="primary", disabled=not chosen):
            db.add_to_shortlist(int(campaign["id"]), [int(value) for value in chosen])
            st.rerun()

    deliverable_counts = deliverables.groupby("engagement_id").size().to_dict() if not deliverables.empty else {}
    statuses: dict[int, list[str]] = {}
    for row in deliverables.to_dict("records"):
        status = checklist_status(row, campaign, db.answers(int(row["id"])), rules)
        statuses.setdefault(int(row["engagement_id"]), []).append(status.label)

    for lane_group in (STAGES[:4], STAGES[4:]):
        lanes = st.columns(4)
        for lane, stage in zip(lanes, lane_group):
            members = engagements[engagements["stage"] == stage]
            with lane:
                st.markdown(f'<div class="lane-title">{stage}<span>{len(members)}</span></div>', unsafe_allow_html=True)
                for row in members.to_dict("records"):
                    engagement_id = int(row["id"])
                    with st.container(border=True):
                        labels = statuses.get(engagement_id, [])
                        flags = " ".join(STATUS_ICONS.get(label, "") for label in labels if label != STATUS_NOT_PUBLISHED)
                        st.markdown(
                            f'<div class="card-name">{row["creator_name"]} {flags}</div>'
                            f'<div class="card-meta">{_handle(row)} · {num(row["followers"])} followers<br>'
                            f'{deliverable_counts.get(engagement_id, 0)} deliverable(s)</div>',
                            unsafe_allow_html=True,
                        )
                        key = f"stage_{engagement_id}_{stage}"
                        st.selectbox(
                            "Stage", STAGES, index=STAGES.index(stage), key=key, label_visibility="collapsed",
                            on_change=_move_card, args=(engagement_id, key, stage, row["creator_name"]),
                        )
        st.write("")
    st.caption("Card icons: ✅ checklist complete · 📝 override recorded · ⚠️ issue recorded · ⏳ answers missing")
    with st.expander("Stage history"):
        st.dataframe(db.stage_log(int(campaign["id"])), hide_index=True, use_container_width=True)
    with st.expander("Remove a creator from this campaign"):
        options = dict(zip(engagements["id"], engagements["creator_name"]))
        if options:
            chosen = st.selectbox("Creator", list(options), format_func=options.get, key="remove_engagement")
            confirm = st.checkbox("Also delete their deliverables and checklist answers for this campaign")
            if st.button("Remove from campaign", disabled=not confirm):
                db.remove_engagement(int(chosen))
                st.rerun()


def page_deliverables() -> None:
    _header(
        "4 · Deliverables",
        "Deliverables, codes and tracked links",
        "One row per post: platform, format, due date, agreed fee, discount code and a tracked link in one "
        "consistent UTM scheme. Mark a deliverable published to open its compliance checklist.",
    )
    campaign = _require_campaign()
    if campaign is None:
        return
    db = store()
    _demo_note(bool(campaign["is_demo"]))
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
            use_container_width=True,
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
        due = cols[2].date_input("Due date", _date_or_none(campaign["start_date"]) or date.today(), key="new_deliv_due")
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
        due = cols[2].date_input("Due date", _date_or_none(current["due_date"]) or date.today(), key=f"{key}_due")
        cols = st.columns(3)
        fee = cols[0].number_input("Agreed fee (NOK)", min_value=0, step=500, value=int(current["fee_nok"] or 0), key=f"{key}_fee")
        code = cols[1].text_input("Discount code", current["discount_code"] or "", key=f"{key}_code")
        shows_person = cols[2].checkbox("Shows a person's body or face", bool(current["shows_person"]), key=f"{key}_person")
        cols = st.columns(3)
        published = cols[0].checkbox("Published", bool(current["published_date"]), key=f"{key}_pub")
        published_on = cols[1].date_input(
            "Published on", _date_or_none(current["published_date"]) or date.today(), key=f"{key}_pubdate",
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


def page_compliance() -> None:
    _header(
        "5 · Compliance",
        "Norwegian advertising checklist",
        "For every published deliverable: is it labelled as advertising at the start, with the recommended wording, "
        "and with the retouching mark where a body was altered? Rules, sources and quotes come from an editable "
        "YAML file.",
    )
    _legal_note()
    campaign = _require_campaign()
    if campaign is None:
        return
    db, rules = store(), _rules()
    _demo_note(bool(campaign["is_demo"]))
    flagged = campaign_restricted_categories(campaign, rules)
    if flagged:
        categories = rules.restricted_categories
        for key in flagged:
            category = categories[key]
            st.warning(
                f"**Restricted category: {category.label}.** {category.note} "
                f"[Source]({category.url}). CreatorSignal flags this only; it never says the campaign is compliant."
            )

    deliverables = db.deliverables(int(campaign["id"]))
    if deliverables.empty:
        st.info("No deliverables yet. Add them on **4 · Deliverables**.")
        return
    rows, statuses = [], {}
    for row in deliverables.to_dict("records"):
        status = checklist_status(row, campaign, db.answers(int(row["id"])), rules)
        statuses[int(row["id"])] = status
        rows.append(
            {
                "id": row["id"],
                "status": f"{STATUS_ICONS.get(status.label, '')} {status.label}",
                "creator": row["creator_name"],
                "platform": row["platform"],
                "format": row["format"],
                "published": row["published_date"] or "–",
                "stage": row["stage"],
                "answered no": ", ".join(rules.by_id(r).label_en for r in status.failing),
                "not answered": ", ".join(rules.by_id(r).label_en for r in (*status.missing, *status.invalid))
                if status.published else "",
            }
        )
    table = pd.DataFrame(rows)
    counts = table["status"].str.split(" ", n=1).str[1].value_counts()
    cols = st.columns(5)
    for col, status in zip(cols, (STATUS_COMPLETE, STATUS_OVERRIDE, STATUS_ISSUE, STATUS_MISSING, STATUS_NOT_PUBLISHED)):
        col.metric(f"{STATUS_ICONS[status]} {status}", int(counts.get(status, 0)))
    issues = [r for r in rows if STATUS_ISSUE in r["status"]]
    for issue in issues:
        missing = f" Not answered yet: {issue['not answered']}." if issue["not answered"] else ""
        st.error(f"⚠️ #{issue['id']} {issue['creator']} ({issue['platform']} {issue['format']}): answered No on "
                 f"{issue['answered no']}.{missing} Fix the post or record why before payment.")
    st.dataframe(table, hide_index=True, use_container_width=True)

    published = [r for r in rows if r["published"] != "–"]
    if not published:
        st.info("Nothing is published yet. Mark a deliverable published on **4 · Deliverables** to open its checklist.")
        return
    labels = {int(r["id"]): f"#{r['id']} · {r['creator']} · {r['platform']} {r['format']} — {r['status']}" for r in published}
    default = next((i for i, r in enumerate(published) if STATUS_ISSUE in r["status"]), 0)
    chosen = st.selectbox("Open checklist for", list(labels), index=default, format_func=labels.get, key="checklist_deliverable")
    deliverable = db.deliverable(int(chosen))
    answers = db.answers(int(chosen))
    st.markdown(f"#### Checklist · #{chosen}")
    _legal_note()
    with st.form(f"checklist_{chosen}"):
        new_answers = {}
        for rule in applicable_rules(deliverable, campaign, rules):
            with st.container(border=True):
                st.markdown(f"**{rule.label_no}** · {rule.label_en}")
                st.markdown(f"{rule.question_no}  \n*{rule.question_en}*")
                choices = ["", "yes", "no"] + (["na"] if rule.allow_not_applicable else [])
                names = {"": "Not answered", "yes": "Yes", "no": "No", "na": rule.not_applicable_label_en}
                current = answers.get(rule.id, "")
                new_answers[rule.id] = st.radio(
                    "Answer", choices, index=choices.index(current) if current in choices else 0,
                    format_func=names.get, horizontal=True, key=f"ans_{chosen}_{rule.id}", label_visibility="collapsed",
                )
                with st.expander("Source, quote and guidance"):
                    if rule.help_en:
                        st.markdown(rule.help_en)
                    if rule.legal_basis:
                        st.caption(f"Legal basis: {rule.legal_basis}")
                    for source in rule.sources:
                        st.markdown(f"[{source.title}]({source.url})")
                        if source.quote:
                            st.markdown(f"> «{source.quote}»")
                        st.caption(f"Fetched {source.fetched}. Verify the current wording at the source.")
                    for key in campaign_restricted_categories(campaign, rules) if rule.applies_when == "restricted_category" else []:
                        category = rules.restricted_categories[key]
                        st.markdown(f"[{category.label}]({category.url}) — {category.note}")
                        if category.quote:
                            st.markdown(f"> «{category.quote}»")
        if st.form_submit_button("Save checklist", type="primary"):
            for rule_id, answer in new_answers.items():
                db.set_answer(int(chosen), rule_id, answer or None)
            st.success("Checklist saved.")
            st.rerun()

    status = statuses[int(chosen)]
    gate = paid_gate(status, rules, f"#{chosen}")
    if gate.allowed and not gate.via_override:
        st.success("Checklist complete: this deliverable does not block the Paid stage.")
    elif gate.allowed:
        st.info("An override reason is recorded: this deliverable will not block the Paid stage. Open items stay visible in the report.")
    else:
        st.warning("This deliverable blocks the Paid stage:\n\n" + "\n".join(f"- {reason}" for reason in gate.reasons))
    with st.form(f"override_{chosen}"):
        reason = st.text_area(
            "Override reason (lets the creator move to Paid with open items — written into the report)",
            deliverable["override_reason"] or "", height=90,
            help=f"At least {MIN_OVERRIDE_CHARS} characters. Explain what was checked instead, by whom and when.",
        )
        if st.form_submit_button("Save override reason"):
            db.set_override(int(chosen), reason)
            st.rerun()


def page_results() -> None:
    _header(
        "6 · Results",
        "Results and cost per result",
        "Type in reach, views, clicks, code redemptions and revenue per deliverable, or import a CSV. CreatorSignal "
        "computes CPM, CPC, cost per redemption and ROAS per creator and for the campaign.",
    )
    campaign = _require_campaign()
    if campaign is None:
        return
    db = store()
    _demo_note(bool(campaign["is_demo"]))
    deliverables = db.deliverables(int(campaign["id"]))
    if deliverables.empty:
        st.info("No deliverables yet.")
        return

    totals = summarize_results(deliverables).iloc[0].to_dict()
    cols = st.columns(5)
    cols[0].metric("Spend (agreed fees)", nok(totals["spend_nok"]))
    cols[1].metric("CPM", nok(totals["cpm_nok"]), help=METRIC_LABELS["cpm_nok"])
    cols[2].metric("CPC", nok(totals["cpc_nok"], 1), help=METRIC_LABELS["cpc_nok"])
    cols[3].metric("Cost / redemption", nok(totals["cost_per_redemption_nok"]), help=METRIC_LABELS["cost_per_redemption_nok"])
    cols[4].metric("ROAS", num(totals["roas"], 2), help=METRIC_LABELS["roas"])
    for note in row_notes(totals):
        st.caption(f"ⓘ {note}")

    per_creator = summarize_results(deliverables, by=["creator_name"])
    default_metric = GOAL_METRIC.get(campaign["goal"], "cost_per_redemption_nok")
    metric_options = list(METRIC_LABELS)
    metric = st.radio(
        "Compare creators on", metric_options, index=metric_options.index(default_metric),
        format_func=METRIC_LABELS.get, horizontal=True,
        help="Defaults to the campaign goal: awareness → CPM, traffic → CPC, sales → cost per redemption.",
    )
    chart = per_creator.dropna(subset=[metric]).sort_values(metric, ascending=(metric != "roas"))
    if chart.empty:
        st.info("No creator has the results needed for this metric yet.")
    else:
        figure = go.Figure(
            go.Bar(
                x=chart[metric], y=chart["creator_name"], orientation="h", marker_color=COLORS["coral"],
                text=[num(value, 2 if metric == "roas" else 0) for value in chart[metric]], textposition="outside",
                hovertemplate="%{y}: %{x:,.2f}<extra></extra>",
            )
        )
        figure.update_layout(
            height=max(260, 34 * len(chart) + 80), margin=dict(l=10, r=40, t=30, b=30),
            xaxis_title=METRIC_LABELS[metric], yaxis=dict(autorange="reversed"),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(255,255,255,.6)", font=dict(color=COLORS["ink"]),
            title=dict(text=("Higher is better" if metric == "roas" else "Lower is cheaper") + " — differences between a few posts are mostly noise", font=dict(size=13)),
        )
        st.plotly_chart(figure, use_container_width=True)
    st.dataframe(
        per_creator,
        hide_index=True,
        use_container_width=True,
        column_config={
            "creator_name": "Creator",
            "spend_nok": st.column_config.NumberColumn("Spend (NOK)", format="%d"),
            "cpm_nok": st.column_config.NumberColumn("CPM", format="%.0f"),
            "cpc_nok": st.column_config.NumberColumn("CPC", format="%.1f"),
            "cost_per_redemption_nok": st.column_config.NumberColumn("Cost / redemption", format="%.0f"),
            "roas": st.column_config.NumberColumn("ROAS", format="%.2f"),
        },
    )

    st.markdown("#### Enter results")
    editable = deliverables[["id", "creator_name", "platform", "format", "fee_nok", *RESULT_COLUMNS]].copy()
    edited = st.data_editor(
        editable,
        hide_index=True,
        use_container_width=True,
        disabled=["id", "creator_name", "platform", "format", "fee_nok"],
        column_config={column: st.column_config.NumberColumn(column, min_value=0) for column in RESULT_COLUMNS},
        key=f"results_editor_{campaign['id']}",
    )
    if st.button("Save results", type="primary"):
        for row in edited.to_dict("records"):
            db.set_results(int(row["id"]), {column: row[column] for column in RESULT_COLUMNS})
        st.success("Results saved.")
        st.rerun()
    with st.expander("Import results from CSV"):
        template = deliverables[["id", "creator_name", "platform", "format", *RESULT_COLUMNS]].rename(columns={"id": "deliverable_id"})
        st.download_button(
            "Download results template for this campaign", dataframe_csv_bytes(template),
            f"creatorsignal-results-{campaign['slug']}.csv", "text/csv",
        )
        st.caption("Required: `deliverable_id`. Any of " + ", ".join(f"`{c}`" for c in RESULT_IMPORT_COLUMNS[1:]) + ". Blank cells are left unchanged.")
        upload = st.file_uploader("Upload results (CSV or XLSX)", type=["csv", "xlsx"], key="results_upload")
        if upload is not None:
            clean = validate_results(read_table(upload.name, upload.getvalue()), set(deliverables["id"].astype(int)))
            st.dataframe(clean, hide_index=True, use_container_width=True)
            if st.button("Import these results", type="primary"):
                for row in clean.to_dict("records"):
                    values = {k: v for k, v in row.items() if k != "deliverable_id" and v is not None and not pd.isna(v)}
                    db.set_results(int(row["deliverable_id"]), values)
                st.success(f"Imported results for {len(clean)} deliverables.")
    st.markdown("#### What these numbers can and cannot say")
    st.markdown(
        '<div class="boundary">' + "".join(f"<p>{note}</p>" for note in GENERAL_NOTES) + "</div>",
        unsafe_allow_html=True,
    )


def page_report() -> None:
    _header(
        "7 · Report",
        "Campaign report",
        "An XLSX workbook with every table and the rule sources, and a one-page HTML summary you can print to PDF "
        "from the browser.",
    )
    campaign = _require_campaign()
    if campaign is None:
        return
    rules = _rules()
    report = build_report(store(), int(campaign["id"]), rules)
    _demo_note(report.is_demo)
    _legal_note()
    totals = report.totals
    cols = st.columns(4)
    cols[0].metric("Deliverables", int(totals.get("deliverables") or 0))
    cols[1].metric("Spend", nok(totals.get("spend_nok")))
    cols[2].metric("Checklists complete", report.compliance_counts.get(STATUS_COMPLETE, 0))
    open_items = report.compliance_counts.get(STATUS_ISSUE, 0) + report.compliance_counts.get(STATUS_MISSING, 0)
    cols[3].metric("Open checklist items", open_items)
    c1, c2 = st.columns(2)
    c1.download_button(
        "Download XLSX workbook", build_xlsx(report), f"creatorsignal-{campaign['slug']}.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary",
    )
    html = build_html(report)
    c2.download_button("Download one-page HTML (print to PDF)", html.encode("utf-8"), f"creatorsignal-{campaign['slug']}.html", "text/html")
    st.markdown("#### Preview")
    st.components.v1.html(html, height=1250, scrolling=True)


def page_settings() -> None:
    _header(
        "Settings & data",
        "Your local workspace",
        "CreatorSignal saves everything in one SQLite file. Choose where it lives, reload the demo or start empty.",
    )
    db = store()
    st.markdown(f"**Current database:** `{db.path.resolve()}`")
    with st.form("data_dir"):
        folder = st.text_input("Data folder", str(Path(_db_path()).parent))
        if st.form_submit_button("Use this folder"):
            target = Path(folder).expanduser()
            st.session_state["db_path"] = str((target / "creatorsignal.db").resolve())
            _select_campaign_next_run(None)
            st.rerun()
    st.caption("A new folder starts with the fictional demo unless CREATORSIGNAL_NO_DEMO=1 is set.")
    cols = st.columns(2)
    with cols[0], st.container(border=True):
        st.markdown("**Reload the fictional demo**")
        st.caption("Replaces everything in the current database with the demo.")
        confirm = st.checkbox("Yes, replace all data with the demo", key="confirm_demo")
        if st.button("Reload demo", disabled=not confirm):
            load_demo(db, _rules())
            _select_campaign_next_run(None)
            st.rerun()
    with cols[1], st.container(border=True):
        st.markdown("**Start empty**")
        st.caption("Deletes every creator, campaign, deliverable and checklist answer in the current database.")
        confirm = st.checkbox("Yes, delete all data in this database", key="confirm_empty")
        if st.button("Delete all data", disabled=not confirm):
            db.clear()
            _select_campaign_next_run(None)
            st.rerun()
    st.markdown("#### Compliance rules")
    rules = _rules()
    st.markdown(f"Loaded from `{_rules_path()}` · fetched {rules.fetched} · {len(rules.rules)} rules. "
                "Edit the YAML to change labels, questions or sources; the app picks up changes on the next action.")
    st.dataframe(
        pd.DataFrame([{"id": r.id, "label (no)": r.label_no, "label (en)": r.label_en, "applies when": r.applies_when,
                       "source": r.primary_url or (r.categories[0].url if r.categories else "")} for r in rules.rules]),
        hide_index=True, use_container_width=True,
    )
    _legal_note()
    st.markdown(
        '<div class="boundary"><strong>Privacy.</strong> Creator names, contact details and fees stay in the SQLite '
        "file on this computer. CreatorSignal has no accounts, no telemetry and no external AI calls, and never "
        "contacts a social network. You are the data controller for the personal data you store here; see "
        "PRIVACY.md.</div>",
        unsafe_allow_html=True,
    )


PAGES = {
    "Welcome": page_welcome,
    "1 · Creators": page_creators,
    "2 · Campaigns": page_campaigns,
    "3 · Pipeline": page_pipeline,
    "4 · Deliverables": page_deliverables,
    "5 · Compliance": page_compliance,
    "6 · Results": page_results,
    "7 · Report": page_report,
    "Settings & data": page_settings,
}
PAGE_SLUGS = {
    "welcome": "Welcome", "creators": "1 · Creators", "campaigns": "2 · Campaigns", "pipeline": "3 · Pipeline",
    "deliverables": "4 · Deliverables", "compliance": "5 · Compliance", "results": "6 · Results",
    "report": "7 · Report", "settings": "Settings & data",
}

try:
    _db = store()
except Exception as exc:  # pragma: no cover - only on unusable folders
    show_error(exc)
    st.stop()

with st.sidebar:
    mark = f'<img class="ps-mark" src="{MARK_URI}" alt="">' if MARK_URI else ""
    st.markdown(
        f'<div class="ps-lockup">{mark}<div class="ps-name">Creator<span>Signal</span></div></div>'
        '<p class="ps-tag">Influencer campaigns for Norway, with the label checklist built in.</p>',
        unsafe_allow_html=True,
    )
    st.caption(f"Influencer campaign manager · v{__version__}")
    requested = PAGE_SLUGS.get(str(st.query_params.get("page", "")).lower())
    page_names = list(PAGES)
    page = st.radio("Workflow", page_names, index=page_names.index(requested) if requested else 0)
    st.markdown("---")
    campaigns = _db.campaigns()
    if campaigns.empty:
        st.caption("No campaigns yet.")
    else:
        options = dict(zip(campaigns["id"].astype(int), campaigns["name"]))
        requested_campaign = str(st.query_params.get("campaign", ""))
        if "_next_campaign" in st.session_state:
            queued = st.session_state.pop("_next_campaign")
            st.session_state["campaign_id"] = queued if queued in options else next(iter(options))
        if st.session_state.get("campaign_id") not in options:
            by_slug = dict(zip(campaigns["slug"], campaigns["id"].astype(int)))
            st.session_state["campaign_id"] = by_slug.get(requested_campaign, next(iter(options)))
        st.selectbox("Active campaign", list(options), format_func=options.get, key="campaign_id")
    if _db.has_demo_data():
        st.info("Fictional demo data loaded. No real person, brand or result.")
    st.caption(DISCLAIMER)
    st.caption("Local mode · no telemetry · no external AI calls · no social-network APIs")

masthead()
try:
    PAGES[page]()
except Exception as exc:
    show_error(exc)
footer()
