import pandas as pd
import pytest

from influencesignal.errors import DataProblem
from influencesignal.io import (
    FYLKER,
    creator_template,
    dataframe_csv_bytes,
    read_table,
    safe_frame,
    validate_creators,
    validate_results,
)


def _csv(text: str) -> pd.DataFrame:
    return read_table("creators.csv", text.encode("utf-8"))


def test_template_round_trips_through_validation() -> None:
    frame = read_table("t.csv", dataframe_csv_bytes(creator_template()))
    clean, _ = validate_creators(frame)
    assert clean.loc[0, "region"] == "Vestland"
    assert clean.loc[0, "followers"] == 12000


def test_semicolon_csv_with_norwegian_numbers_and_handles() -> None:
    clean, warnings = validate_creators(
        _csv(
            "Name;Instagram;TikTok;Followers;Engagement rate;Region;Niche tags\n"
            "Kari Test;@kari.test;;12 500;4,2%;møre og romsdal;Trening, Ski\n"
            "Ola Test;;ola_t;3000;3.1;Oslo;\n"
        )
    )
    assert list(clean["instagram"]) == ["kari.test", ""]
    assert clean.loc[0, "followers"] == 12500
    assert clean.loc[0, "engagement_rate"] == pytest.approx(4.2)
    assert clean.loc[0, "region"] == "Møre og Romsdal"
    assert clean.loc[0, "niche_tags"] == "trening, ski"
    assert not warnings


def test_name_column_is_required() -> None:
    with pytest.raises(DataProblem, match="'name' column"):
        validate_creators(_csv("handle\nx\n"))


@pytest.mark.parametrize(
    "row, message",
    [
        (",a,,,,", "name is required"),
        ("A,bad handle!,,,,", "handle"),
        ("A,a,ten,,,", "followers 'ten' is not a number"),
        ("A,a,-5,,,", "whole number"),
        ("A,a,,250,,", "between 0 and 100"),
        ("A,a,,,Viken,", "not one of Norway's 15 counties"),
        ("A,a,,,,not-an-email", "does not look like an e-mail"),
    ],
)
def test_invalid_rows_are_rejected_with_row_numbers(row: str, message: str) -> None:
    with pytest.raises(DataProblem, match=message) as problem:
        validate_creators(_csv("name,instagram,followers,engagement_rate,region,contact_email\n" + row + "\n"))
    assert "Row 2" in str(problem.value)


def test_duplicates_in_file_are_rejected() -> None:
    with pytest.raises(DataProblem, match="more than once"):
        validate_creators(_csv("name,instagram\nA,x\nB,x\n"))
    with pytest.raises(DataProblem, match="more than once"):
        validate_creators(_csv("name\nA\na\n"))


def test_unknown_columns_and_missing_handles_warn() -> None:
    _, warnings = validate_creators(_csv("name,favourite_colour\nA,blue\n"))
    assert any("favourite_colour" in warning for warning in warnings)
    assert any("no platform handle" in warning for warning in warnings)


def test_fylker_are_the_fifteen_counties_from_2024() -> None:
    assert len(FYLKER) == 15
    assert "Viken" not in FYLKER and "Vestfold og Telemark" not in FYLKER


def test_import_updates_existing_creators_by_name(store) -> None:
    clean, _ = validate_creators(_csv("name,followers\nKari,100\nOla,200\n"))
    assert store.import_creators(clean) == (2, 0)
    clean, _ = validate_creators(_csv("name,followers\nkari,150\n"))
    assert store.import_creators(clean) == (0, 1)
    creators = store.creators().set_index("name")
    assert creators.loc["kari", "followers"] == 150


def test_results_validation(store) -> None:
    good = validate_results(_csv("deliverable_id,views,clicks,revenue_nok\n1,1000,20,\n2,2 000,,3500\n"), {1, 2})
    assert good.loc[1, "views"] == 2000
    assert pd.isna(good.loc[0, "revenue_nok"])
    with pytest.raises(DataProblem, match="not a deliverable"):
        validate_results(_csv("deliverable_id,views\n9,10\n"), {1})
    with pytest.raises(DataProblem, match="negative"):
        validate_results(_csv("deliverable_id,views\n1,-10\n"), {1})
    with pytest.raises(DataProblem, match="more than once"):
        validate_results(_csv("deliverable_id,views\n1,10\n1,20\n"), {1})
    with pytest.raises(DataProblem, match="at least one of"):
        validate_results(_csv("deliverable_id,colour\n1,red\n"), {1})


def test_upload_guards() -> None:
    with pytest.raises(DataProblem, match="empty"):
        read_table("x.csv", b"")
    with pytest.raises(DataProblem, match="CSV or XLSX"):
        read_table("x.xlsm", b"data")


def test_exports_are_formula_injection_safe() -> None:
    frame = pd.DataFrame({"=cmd": ["=HYPERLINK(\"x\")", "+1", "-2", "@SUM(A1)", "safe"]})
    safe = safe_frame(frame)
    assert safe.columns[0] == "'=cmd"
    assert all(str(value).startswith("'") for value in safe.iloc[:4, 0])
    assert safe.iloc[4, 0] == "safe"
