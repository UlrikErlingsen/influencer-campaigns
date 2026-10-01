"""Cost-per-result metrics and the plain-language limits that travel with them."""

from __future__ import annotations

import math

import pandas as pd

RESULT_COLUMNS = ("reach", "views", "clicks", "redemptions", "revenue_nok")

# Each metric divides cost (or revenue) by one result column. Cost is counted only for deliverables
# that report that result, so a missing number never makes the remaining ones look cheaper or dearer.
METRICS = {
    "cpm_nok": ("views", 1000.0),
    "cpc_nok": ("clicks", 1.0),
    "cost_per_redemption_nok": ("redemptions", 1.0),
}

METRIC_LABELS = {
    "cpm_nok": "CPM (NOK per 1,000 views)",
    "cpc_nok": "CPC (NOK per click)",
    "cost_per_redemption_nok": "Cost per redemption (NOK)",
    "roas": "ROAS (revenue ÷ fee)",
}

GENERAL_NOTES = (
    "These are descriptive cost-per-result figures. They do not show that the posts caused the clicks, "
    "redemptions or revenue: some buyers would have bought anyway, and others saw the post but bought later "
    "without a code.",
    "Discount codes leak. Codes get shared on coupon sites and in group chats, so redemptions can include people "
    "who never saw the creator's post — and miss people who did.",
    "Views and reach are defined differently by each platform and are often reported by the creator from "
    "screenshots. Compare like with like (same platform and format) before ranking creators.",
    "ROAS here is code-attributed revenue divided by the agreed fee. It leaves out product cost, gifted products, "
    "production and agency time, so it is not profit.",
    "With few deliverables, one viral post or one quiet week can dominate a creator's numbers. Treat small "
    "differences as noise.",
)


def _number(value: object) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(number) else number


def safe_ratio(numerator: object, denominator: object, scale: float = 1.0) -> float | None:
    """numerator / denominator × scale, or None when either is missing or the denominator is not positive."""
    top, bottom = _number(numerator), _number(denominator)
    if top is None or bottom is None or bottom <= 0:
        return None
    return top / bottom * scale


def cpm(cost: object, views: object) -> float | None:
    """Cost per 1,000 views."""
    return safe_ratio(cost, views, 1000.0)


def cpc(cost: object, clicks: object) -> float | None:
    """Cost per click."""
    return safe_ratio(cost, clicks)


def cost_per_redemption(cost: object, redemptions: object) -> float | None:
    """Cost per discount-code redemption."""
    return safe_ratio(cost, redemptions)


def roas(revenue: object, cost: object) -> float | None:
    """Return on ad spend: attributed revenue divided by cost."""
    return safe_ratio(revenue, cost)


def summarize_results(frame: pd.DataFrame, by: list[str] | None = None) -> pd.DataFrame:
    """Aggregate deliverable rows (columns ``fee_nok`` + result columns) and compute the metrics.

    Each metric uses only the fees of deliverables that reported the metric's denominator; ROAS uses the
    fees of deliverables that reported revenue.
    """
    by = list(by or [])
    data = frame.copy()
    for column in ("fee_nok", *RESULT_COLUMNS):
        if column not in data:
            data[column] = float("nan")
        data[column] = pd.to_numeric(data[column], errors="coerce")
    if not by:
        data["_all"] = "All"
        by = ["_all"]

    rows = []
    for keys, group in data.groupby(by, dropna=False, sort=True):
        keys = keys if isinstance(keys, tuple) else (keys,)
        row: dict[str, object] = dict(zip(by, keys))
        row["deliverables"] = len(group)
        row["spend_nok"] = float(group["fee_nok"].fillna(0).sum())
        row["with_results"] = int(group[list(RESULT_COLUMNS)].notna().any(axis=1).sum())
        for column in RESULT_COLUMNS:
            reported = group[column].notna()
            row[column] = float(group.loc[reported, column].sum()) if reported.any() else None
        for metric, (denominator, scale) in METRICS.items():
            reported = group[denominator].notna()
            cost = group.loc[reported, "fee_nok"].fillna(0).sum() if reported.any() else None
            row[metric] = safe_ratio(cost, row[denominator], scale)
        reported_revenue = group["revenue_nok"].notna()
        revenue_cost = group.loc[reported_revenue, "fee_nok"].fillna(0).sum() if reported_revenue.any() else None
        row["roas"] = roas(row["revenue_nok"], revenue_cost)
        rows.append(row)
    result = pd.DataFrame(rows)
    return result.drop(columns=["_all"], errors="ignore")


def row_notes(row: pd.Series | dict) -> list[str]:
    """Specific caveats for one summary row (in addition to GENERAL_NOTES)."""
    get = row.get
    notes: list[str] = []
    deliverables = int(get("deliverables") or 0)
    with_results = int(get("with_results") or 0)
    if deliverables and with_results < deliverables:
        notes.append(f"{deliverables - with_results} of {deliverables} deliverables have no results yet; "
                     "their fees are excluded from each cost-per-result figure.")
    redemptions = _number(get("redemptions"))
    if redemptions is not None and redemptions < 10:
        notes.append("Fewer than 10 code redemptions: cost per redemption and ROAS are very unstable.")
    clicks = _number(get("clicks"))
    if clicks is not None and clicks < 50:
        notes.append("Fewer than 50 clicks: CPC can swing widely with a handful of clicks.")
    if _number(get("revenue_nok")) is None:
        notes.append("No revenue reported, so ROAS cannot be calculated.")
    return notes
