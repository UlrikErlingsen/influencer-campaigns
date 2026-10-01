"""Welcome: what Influence Signal does and how to try the fictional demo."""

from __future__ import annotations

import streamlit as st

from influencesignal.ui import signal_theme as sig

from .ui import (
    KEY,
    demo_note,
    legal_note,
    store,
)


def render() -> None:
    sig.hero(
        KEY,
        eyebrow="INFLUENCER CAMPAIGNS · NORWAY",
        title="Which creators delivered — and was every post",
        em="labelled properly?",
        body="Run the whole campaign in one local app: roster, pipeline, deliverables with tracked links and codes, "
        "results at cost per result, and a Norwegian advertising-label checklist on every published post.",
        pills=["creator roster", "kanban pipeline", "UTM links & codes", "«reklame» checklist", "retouching mark",
               "CPM · CPC · ROAS", "XLSX + one-page report"],
    )
    demo_note(store().has_demo_data())
    sig.cards(
        [
            ("01 · RUN", "One pipeline per campaign",
             "Shortlist → Contacted → Negotiating → Contracted → Content in review → Published → Paid → Reported. "
             "Every move is logged."),
            ("02 · CHECK", "A checklist before payment",
             "Each published post gets the Norwegian advertising-label and retouching-mark checklist. A creator cannot "
             "be marked Paid until it is complete or someone writes down why not."),
            ("03 · LEARN", "Cost per result, honestly",
             "CPM, CPC, cost per redemption and ROAS per creator and campaign — with plain notes on what they cannot "
             "show. Codes leak; numbers are not causes."),
        ]
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
    sig.note(
        "boundary",
        "**Boundaries.** Influence Signal never contacts creators, never calls a social-network API and never scrapes "
        "profiles. Everything you type stays in a SQLite file on this computer. The checklist records what your team "
        "checked; it is not a legal assessment.",
    )
