"""Campaign report: an auditable XLSX workbook and a one-page HTML summary (print to PDF from the browser)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from html import escape
from io import BytesIO

import pandas as pd

from . import DISCLAIMER, __version__
from .compliance import (
    STATUS_COMPLETE,
    STATUS_ISSUE,
    STATUS_MISSING,
    STATUS_NOT_PUBLISHED,
    STATUS_OVERRIDE,
    applicable_rules,
    campaign_restricted_categories,
    checklist_status,
)
from .demo import DEMO_NOTICE
from .io import safe_frame
from .metrics import GENERAL_NOTES, METRIC_LABELS, row_notes, summarize_results
from .rules import RuleSet
from .storage import Store

ANSWER_LABELS = {"yes": "Yes", "no": "No", "na": "Not applicable", "": "Not answered"}


@dataclass(frozen=True)
class CampaignReport:
    campaign: dict
    is_demo: bool
    deliverables: pd.DataFrame
    creators: pd.DataFrame
    totals: dict
    checklist: pd.DataFrame
    compliance_counts: dict[str, int]
    restricted: list[str]
    notes: list[str]
    rules: RuleSet


def build_report(store: Store, campaign_id: int, rules: RuleSet) -> CampaignReport:
    campaign = store.campaign(campaign_id)
    deliverables = store.deliverables(campaign_id)
    engagements = store.engagements(campaign_id)

    status_rows, checklist_rows = [], []
    for row in deliverables.to_dict("records"):
        answers = store.answers(int(row["id"]))
        status = checklist_status(row, campaign, answers, rules)
        status_rows.append(
            {
                "compliance_status": status.label,
                "open_items": "; ".join(
                    [f"{rules.by_id(rule_id).label_en}: answered No" for rule_id in status.failing]
                    + [f"{rules.by_id(rule_id).label_en}: not answered" for rule_id in (*status.missing, *status.invalid)]
                )
                if status.published
                else "",
            }
        )
        for rule in applicable_rules(row, campaign, rules):
            checklist_rows.append(
                {
                    "deliverable_id": row["id"],
                    "creator": row["creator_name"],
                    "platform": row["platform"],
                    "format": row["format"],
                    "rule_id": rule.id,
                    "rule": f"{rule.label_en} / {rule.label_no}",
                    "answer": ANSWER_LABELS.get(answers.get(rule.id, ""), answers.get(rule.id, "")),
                    "source_url": rule.primary_url or (rule.categories[0].url if rule.categories else ""),
                }
            )
    deliverables = pd.concat([deliverables.reset_index(drop=True), pd.DataFrame(status_rows)], axis=1)
    if deliverables.empty:
        deliverables = deliverables.reindex(columns=[*deliverables.columns, "compliance_status", "open_items"])

    per_creator = summarize_results(deliverables, by=["creator_name"]) if not deliverables.empty else pd.DataFrame()
    stages = engagements[["creator_name", "stage", "followers"]]
    creators = stages.merge(per_creator, on="creator_name", how="left") if not per_creator.empty else stages.copy()
    if not deliverables.empty:
        worst = (
            deliverables.groupby("creator_name")["compliance_status"]
            .agg(lambda values: _worst_status(list(values)))
            .rename("compliance_status")
        )
        creators = creators.merge(worst, on="creator_name", how="left")
    totals = summarize_results(deliverables).iloc[0].to_dict() if not deliverables.empty else {"deliverables": 0, "spend_nok": 0.0}
    counts = deliverables["compliance_status"].value_counts().to_dict() if not deliverables.empty else {}
    notes = [*row_notes(totals), *GENERAL_NOTES]
    return CampaignReport(
        campaign=campaign,
        is_demo=bool(campaign.get("is_demo")),
        deliverables=deliverables,
        creators=creators,
        totals=totals,
        checklist=pd.DataFrame(checklist_rows),
        compliance_counts={str(k): int(v) for k, v in counts.items()},
        restricted=campaign_restricted_categories(campaign, rules),
        notes=notes,
        rules=rules,
    )


_STATUS_ORDER = (STATUS_ISSUE, STATUS_MISSING, STATUS_NOT_PUBLISHED, STATUS_OVERRIDE, STATUS_COMPLETE)


def _worst_status(statuses: list[str]) -> str:
    for status in _STATUS_ORDER:
        if status in statuses:
            return status
    return statuses[0] if statuses else ""


def _fmt_nok(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "–"
    return f"{float(value):,.0f} NOK".replace(",", " ")


def _fmt_num(value: object, decimals: int = 0) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "–"
    return f"{float(value):,.{decimals}f}".replace(",", " ")


DELIVERABLE_EXPORT_COLUMNS = [
    "id", "creator_name", "stage", "platform", "format", "due_date", "published_date", "fee_nok", "discount_code",
    "tracked_url", "post_url", "reach", "views", "clicks", "redemptions", "revenue_nok", "compliance_status",
    "open_items", "override_reason",
]


def build_xlsx(report: CampaignReport) -> bytes:
    campaign = report.campaign
    read_me = [
        ("report", "InfluenceSignal campaign report"),
        ("campaign", campaign["name"]),
        ("brand", campaign["brand"]),
        ("goal", campaign["goal"]),
        ("period", f"{campaign['start_date']} – {campaign['end_date']}"),
        ("budget_nok", campaign["budget_nok"]),
        ("generated", date.today().isoformat()),
        ("influencesignal_version", __version__),
        ("rules_fetched", report.rules.fetched),
        ("compliance_disclaimer", DISCLAIMER),
        ("restricted_category_flags", ", ".join(report.restricted) or "none"),
    ]
    if report.is_demo:
        read_me.insert(1, ("demo_notice", DEMO_NOTICE))
    totals = pd.DataFrame([report.totals]).drop(columns=["_all"], errors="ignore")
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        safe_frame(pd.DataFrame(read_me, columns=["field", "value"])).to_excel(writer, sheet_name="read_me", index=False)
        safe_frame(totals).to_excel(writer, sheet_name="campaign_totals", index=False)
        safe_frame(report.creators).to_excel(writer, sheet_name="creators", index=False)
        columns = [column for column in DELIVERABLE_EXPORT_COLUMNS if column in report.deliverables.columns]
        safe_frame(report.deliverables[columns]).to_excel(writer, sheet_name="deliverables", index=False)
        safe_frame(report.checklist).to_excel(writer, sheet_name="compliance_checklist", index=False)
        rules_rows = [
            {
                "rule_id": rule.id,
                "label_no": rule.label_no,
                "label_en": rule.label_en,
                "legal_basis": rule.legal_basis,
                "source_url": rule.primary_url,
                "quote": rule.sources[0].quote if rule.sources else "",
            }
            for rule in report.rules.rules
        ]
        safe_frame(pd.DataFrame(rules_rows)).to_excel(writer, sheet_name="rules_and_sources", index=False)
        safe_frame(pd.DataFrame({"what_the_numbers_can_and_cannot_say": report.notes})).to_excel(
            writer, sheet_name="notes", index=False
        )
    return output.getvalue()


def build_html(report: CampaignReport) -> str:
    """A self-contained one-page summary. Open it in a browser and print to PDF."""
    campaign, totals = report.campaign, report.totals
    e = escape
    kpis = [
        ("Spend (agreed fees)", _fmt_nok(totals.get("spend_nok"))),
        ("Budget", _fmt_nok(campaign.get("budget_nok"))),
        ("Views", _fmt_num(totals.get("views"))),
        ("Code redemptions", _fmt_num(totals.get("redemptions"))),
        ("Revenue (code-attributed)", _fmt_nok(totals.get("revenue_nok"))),
        (METRIC_LABELS["cpm_nok"], _fmt_nok(totals.get("cpm_nok"))),
        (METRIC_LABELS["cpc_nok"], _fmt_nok(totals.get("cpc_nok"))),
        (METRIC_LABELS["cost_per_redemption_nok"], _fmt_nok(totals.get("cost_per_redemption_nok"))),
        (METRIC_LABELS["roas"], _fmt_num(totals.get("roas"), 2)),
    ]
    kpi_html = "".join(f"<div class='kpi'><span>{e(label)}</span><b>{e(value)}</b></div>" for label, value in kpis)

    creator_rows = []
    for row in report.creators.to_dict("records"):
        creator_rows.append(
            "<tr>"
            f"<td>{e(str(row.get('creator_name', '')))}</td><td>{e(str(row.get('stage', '')))}</td>"
            f"<td class='n'>{_fmt_nok(row.get('spend_nok'))}</td><td class='n'>{_fmt_num(row.get('views'))}</td>"
            f"<td class='n'>{_fmt_num(row.get('redemptions'))}</td>"
            f"<td class='n'>{_fmt_nok(row.get('cost_per_redemption_nok'))}</td>"
            f"<td class='n'>{_fmt_num(row.get('roas'), 2)}</td>"
            f"<td>{e(str(row.get('compliance_status') or '–'))}</td>"
            "</tr>"
        )
    counts = report.compliance_counts
    compliance_items = "".join(
        f"<li><b>{counts.get(status, 0)}</b> {e(status.lower())}</li>"
        for status in (STATUS_COMPLETE, STATUS_OVERRIDE, STATUS_ISSUE, STATUS_MISSING, STATUS_NOT_PUBLISHED)
    )
    issues = report.deliverables.loc[
        report.deliverables.get("compliance_status", pd.Series(dtype=str)).isin([STATUS_ISSUE, STATUS_MISSING])
    ] if not report.deliverables.empty else report.deliverables
    issue_items = "".join(
        f"<li>#{row['id']} {e(str(row['creator_name']))} · {e(row['platform'])} {e(row['format'])}: "
        f"{e(row['compliance_status'])} — {e(str(row['open_items']))}</li>"
        for row in issues.to_dict("records")
    ) or "<li>None recorded.</li>"
    restricted = ""
    if report.restricted:
        categories = report.rules.restricted_categories
        restricted = (
            "<div class='flag'><b>Restricted category flagged:</b> "
            + ", ".join(e(categories[key].label) for key in report.restricted)
            + ". Stricter Norwegian rules apply. InfluenceSignal flags this only and makes no assessment.</div>"
        )
    demo = f"<div class='demo'>{e(DEMO_NOTICE)}</div>" if report.is_demo else ""
    notes = "".join(f"<li>{e(note)}</li>" for note in report.notes)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(campaign['name'])} — InfluenceSignal report</title>
<style>
:root {{ --ink:#17322e; --coral:#d95b40; --mint:#83d2b4; --gold:#f2c66d; --paper:#f8f5ed; --line:#d9ded8; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; padding:24px; background:var(--paper); color:var(--ink); font:13px/1.45 Inter,Arial,sans-serif; }}
main {{ max-width:960px; margin:0 auto; background:white; padding:28px 32px; border-radius:14px; }}
header {{ display:flex; justify-content:space-between; gap:16px; border-bottom:3px solid var(--ink); padding-bottom:10px; }}
h1 {{ margin:0; font-size:24px; letter-spacing:-.02em; }} h2 {{ font-size:14px; margin:18px 0 6px; text-transform:uppercase; letter-spacing:.08em; color:var(--coral); }}
.meta {{ color:#59716c; text-align:right; font-size:12px; }}
.kpis {{ display:grid; grid-template-columns:repeat(3,1fr); gap:8px; margin-top:12px; }}
.kpi {{ border:1px solid var(--line); border-radius:10px; padding:8px 10px; }} .kpi span {{ display:block; color:#59716c; font-size:11px; }} .kpi b {{ font-size:16px; }}
table {{ width:100%; border-collapse:collapse; font-size:12px; }} th,td {{ border-bottom:1px solid var(--line); padding:4px 6px; text-align:left; }}
th {{ background:#eef2eb; }} td.n {{ text-align:right; white-space:nowrap; }}
.cols {{ display:grid; grid-template-columns:1fr 1fr; gap:18px; }} ul {{ margin:4px 0; padding-left:18px; }}
.disclaimer {{ margin-top:10px; padding:8px 10px; border-left:4px solid var(--gold); background:#fbf3df; font-weight:700; }}
.flag {{ margin-top:10px; padding:8px 10px; border-left:4px solid var(--coral); background:#fbe9e4; }}
.demo {{ margin-top:10px; padding:8px 10px; border-left:4px solid var(--mint); background:#eaf6f1; }}
.notes li {{ margin-bottom:3px; color:#47645e; }} footer {{ margin-top:14px; color:#617670; font-size:11px; text-align:center; }}
@media print {{ body {{ padding:0; background:white; }} main {{ padding:0; border-radius:0; }} @page {{ size:A4; margin:12mm; }} }}
@media (max-width:640px) {{ .kpis,.cols {{ grid-template-columns:1fr; }} header {{ display:block; }} .meta {{ text-align:left; }} }}
</style></head>
<body><main>
<header><div><h1>{e(campaign['name'])}</h1><div>{e(campaign['brand'])} · goal: {e(campaign['goal'])}</div></div>
<div class="meta">{e(campaign['start_date'])} – {e(campaign['end_date'])}<br>Generated {date.today().isoformat()} · InfluenceSignal v{e(__version__)}</div></header>
{demo}
<h2>Spend and results</h2><div class="kpis">{kpi_html}</div>
<h2>Creators</h2>
<table><thead><tr><th>Creator</th><th>Stage</th><th>Spend</th><th>Views</th><th>Redemptions</th><th>Cost / redemption</th><th>ROAS</th><th>Checklist</th></tr></thead>
<tbody>{''.join(creator_rows)}</tbody></table>
<div class="cols"><div><h2>Compliance checklist status</h2><ul>{compliance_items}</ul></div>
<div><h2>Open checklist items</h2><ul>{issue_items}</ul></div></div>
{restricted}
<div class="disclaimer">{e(DISCLAIMER)} Statuses record what the team answered on the checklist; they are not a finding that any post is lawful.</div>
<h2>What these numbers can and cannot say</h2><ul class="notes">{notes}</ul>
<footer>InfluenceSignal · local-first · part of the Signal suite · AGPL-3.0-or-later</footer>
</main></body></html>
"""
