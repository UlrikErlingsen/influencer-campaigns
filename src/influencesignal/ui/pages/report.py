"""7 · Report: XLSX workbook and one-page HTML summary."""

from __future__ import annotations

import streamlit as st

from influencesignal.compliance import (
    STATUS_COMPLETE,
    STATUS_ISSUE,
    STATUS_MISSING,
)
from influencesignal.report import build_html, build_report, build_xlsx
from influencesignal.ui import signal_theme as sig

from ..shell import (
    k,
    current_rules,
    demo_note,
    legal_note,
    nok,
    require_campaign,
    store,
)


def render() -> None:
    sig.header(
        "7 · Report",
        "Campaign report",
        "An XLSX workbook with every table and the rule sources, and a one-page HTML summary you can print to PDF "
        "from the browser.",
    )
    campaign = require_campaign()
    if campaign is None:
        return
    rules = current_rules()
    report = build_report(store(), int(campaign["id"]), rules)
    demo_note(report.is_demo)
    legal_note()
    totals = report.totals
    cols = st.columns(4)
    cols[0].metric("Deliverables", int(totals.get("deliverables") or 0))
    cols[1].metric("Spend", nok(totals.get("spend_nok")))
    cols[2].metric("Checklists complete", report.compliance_counts.get(STATUS_COMPLETE, 0))
    open_items = report.compliance_counts.get(STATUS_ISSUE, 0) + report.compliance_counts.get(STATUS_MISSING, 0)
    cols[3].metric("Open checklist items", open_items)
    c1, c2 = st.columns(2)
    c1.download_button(
        "Download XLSX workbook", build_xlsx(report), f"influencesignal-{campaign['slug']}.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary", key=k("report_xlsx"),
    )
    html = build_html(report)
    c2.download_button("Download one-page HTML (print to PDF)", html.encode("utf-8"), f"influencesignal-{campaign['slug']}.html", "text/html",
        key=k("report_html"),
    )
    st.markdown("#### Preview")
    st.components.v1.html(html, height=1250, scrolling=True)
