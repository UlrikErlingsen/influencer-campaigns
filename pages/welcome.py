"""Welcome: what InfluenceSignal does and how to try the fictional demo."""

from __future__ import annotations

import streamlit as st


from .ui import (
    demo_note,
    legal_note,
    store,
)


def render() -> None:
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
    demo_note(store().has_demo_data())
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
    legal_note()
    st.markdown(
        '<div class="boundary"><strong>Boundaries.</strong> InfluenceSignal never contacts creators, never calls a '
        "social-network API and never scrapes profiles. Everything you type stays in a SQLite file on this "
        "computer. The checklist records what your team checked; it is not a legal assessment.</div>",
        unsafe_allow_html=True,
    )
