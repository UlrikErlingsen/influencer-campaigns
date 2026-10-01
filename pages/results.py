"""6 · Results: results entry and cost per result."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

from influencesignal.io import (
    RESULT_IMPORT_COLUMNS,
    dataframe_csv_bytes,
    read_table,
    validate_results,
)
from influencesignal.metrics import GENERAL_NOTES, METRIC_LABELS, RESULT_COLUMNS, row_notes, summarize_results
from influencesignal.ui import signal_theme as sig

from .ui import (
    GOAL_METRIC,
    KEY,
    demo_note,
    nok,
    num,
    require_campaign,
    store,
)


def render() -> None:
    sig.header(
        "6 · Results",
        "Results and cost per result",
        "Type in reach, views, clicks, code redemptions and revenue per deliverable, or import a CSV. Influence Signal "
        "computes CPM, CPC, cost per redemption and ROAS per creator and for the campaign.",
    )
    campaign = require_campaign()
    if campaign is None:
        return
    db = store()
    demo_note(bool(campaign["is_demo"]))
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
                x=chart[metric], y=chart["creator_name"], orientation="h", marker_color=sig.roles(KEY)["highlight"],
                text=[num(value, 2 if metric == "roas" else 0) for value in chart[metric]], textposition="outside",
                hovertemplate="%{y}: %{x:,.2f}<extra></extra>",
            )
        )
        figure.update_layout(
            height=max(260, 34 * len(chart) + 80), margin=dict(l=10, r=40, t=30, b=30),
            xaxis_title=METRIC_LABELS[metric], yaxis=dict(autorange="reversed", automargin=True),
            title=dict(text=("Higher is better" if metric == "roas" else "Lower is cheaper") + " — differences between a few posts are mostly noise", font=dict(size=13)),
        )
        # Streamlit 1.64 writes its own font and plot background into the layout even with theme=None, which beats
        # template values; pin the Signal template's font and backgrounds on the figure so they survive.
        signal_layout = pio.templates[sig.template(KEY)].layout
        figure.update_layout(font=signal_layout.font, paper_bgcolor=signal_layout.paper_bgcolor,
                             plot_bgcolor=signal_layout.plot_bgcolor)
        sig.chart(KEY, figure)  # per-app Signal template, Streamlit chart theme off
    st.dataframe(
        per_creator,
        hide_index=True,
        width="stretch",
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
        width="stretch",
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
            f"influencesignal-results-{campaign['slug']}.csv", "text/csv",
        )
        st.caption("Required: `deliverable_id`. Any of " + ", ".join(f"`{c}`" for c in RESULT_IMPORT_COLUMNS[1:]) + ". Blank cells are left unchanged.")
        upload = st.file_uploader("Upload results (CSV or XLSX)", type=["csv", "xlsx"], key="results_upload")
        if upload is not None:
            clean = validate_results(read_table(upload.name, upload.getvalue()), set(deliverables["id"].astype(int)))
            st.dataframe(clean, hide_index=True, width="stretch")
            if st.button("Import these results", type="primary"):
                for row in clean.to_dict("records"):
                    values = {k: v for k, v in row.items() if k != "deliverable_id" and v is not None and not pd.isna(v)}
                    db.set_results(int(row["deliverable_id"]), values)
                st.success(f"Imported results for {len(clean)} deliverables.")
    st.markdown("#### What these numbers can and cannot say")
    sig.note("boundary", "\n\n".join(GENERAL_NOTES))  # one note, one paragraph per caveat
