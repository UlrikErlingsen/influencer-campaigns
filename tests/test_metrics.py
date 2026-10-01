import math

import pandas as pd
import pytest

from influencesignal.metrics import (
    GENERAL_NOTES,
    cost_per_redemption,
    cpc,
    cpm,
    roas,
    row_notes,
    safe_ratio,
    summarize_results,
)


def test_basic_metrics() -> None:
    assert cpm(5000, 100_000) == pytest.approx(50.0)
    assert cpc(5000, 250) == pytest.approx(20.0)
    assert cost_per_redemption(5000, 40) == pytest.approx(125.0)
    assert roas(15000, 5000) == pytest.approx(3.0)


@pytest.mark.parametrize("denominator", [0, None, float("nan"), -5, "not a number"])
def test_metrics_are_undefined_rather_than_infinite(denominator) -> None:
    assert safe_ratio(100, denominator) is None
    assert cpm(100, denominator) is None
    assert roas(100, denominator) is None


def test_missing_numerator_is_undefined() -> None:
    assert cpc(None, 10) is None
    assert cpc(float("nan"), 10) is None


def test_zero_cost_gives_zero_not_undefined() -> None:
    assert cpc(0, 10) == 0.0


def test_summary_only_counts_fees_of_deliverables_that_report_the_metric() -> None:
    frame = pd.DataFrame(
        {
            "creator_name": ["A", "A", "B"],
            "fee_nok": [1000.0, 3000.0, 2000.0],
            "views": [10_000, None, 40_000],
            "clicks": [50, 100, None],
            "redemptions": [None, None, None],
            "revenue_nok": [2000.0, None, None],
        }
    )
    total = summarize_results(frame).iloc[0]
    assert total["spend_nok"] == 6000.0
    # CPM: fees of rows with views (1000 + 2000) over 50 000 views.
    assert total["cpm_nok"] == pytest.approx(3000 / 50_000 * 1000)
    # CPC: fees of rows with clicks (1000 + 3000) over 150 clicks.
    assert total["cpc_nok"] == pytest.approx(4000 / 150)
    assert total["cost_per_redemption_nok"] is None or math.isnan(total["cost_per_redemption_nok"])
    # ROAS: revenue 2000 over the fee of the one row with revenue (1000).
    assert total["roas"] == pytest.approx(2.0)

    per_creator = summarize_results(frame, by=["creator_name"]).set_index("creator_name")
    assert per_creator.loc["A", "spend_nok"] == 4000.0
    assert per_creator.loc["B", "cpm_nok"] == pytest.approx(50.0)
    assert per_creator.loc["A", "deliverables"] == 2


def test_notes_flag_small_numbers_and_missing_results() -> None:
    notes = " ".join(row_notes({"deliverables": 3, "with_results": 1, "redemptions": 4, "clicks": 20, "revenue_nok": None}))
    assert "2 of 3 deliverables have no results" in notes
    assert "Fewer than 10 code redemptions" in notes
    assert "Fewer than 50 clicks" in notes
    assert "ROAS cannot be calculated" in notes


def test_general_notes_make_no_causal_claim_and_mention_code_leakage() -> None:
    text = " ".join(GENERAL_NOTES).lower()
    assert "do not show that the posts caused" in text
    assert "codes leak" in text
    assert "not profit" in text
