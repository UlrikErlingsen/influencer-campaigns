"""Large-data tier: the old 20 MB / 50,000-row limits no longer block, and the new limits explain themselves."""

from pathlib import Path

import pandas as pd
import pytest

from influencesignal import io
from influencesignal.errors import DataProblem
from influencesignal.io import read_table, validate_creators, validate_results

ROOT = Path(__file__).resolve().parents[1]


def test_limits_match_the_data_heavy_tier() -> None:
    assert io.MAX_UPLOAD_MB == 1000
    assert io.MAX_UPLOAD_BYTES == 1000 * 1024 * 1024
    assert io.MAX_TABLE_ROWS >= 5_000_000
    assert io.MAX_EXPANDED_WORKBOOK_BYTES >= io.MAX_UPLOAD_BYTES


def test_more_rows_than_the_old_limit_validate_and_import(store) -> None:
    rows = 60_000  # the old limit was 50,000 rows
    text = "name;instagram;followers;engagement_rate;region\n" + "".join(
        f"Skaper {i};demo_{i};{1000 + i};3,5;Oslo\n" for i in range(rows)
    )
    clean, warnings = validate_creators(read_table("roster.csv", text.encode("utf-8")))
    assert len(clean) == rows and not warnings
    assert clean["engagement_rate"].iloc[-1] == pytest.approx(3.5)
    assert store.import_creators(clean) == (rows, 0)
    assert store.import_creators(clean.head(10)) == (0, 10)
    assert len(store.creators()) == rows


def test_upload_and_row_limit_messages(monkeypatch) -> None:
    monkeypatch.setattr(io, "MAX_UPLOAD_BYTES", 8)
    with pytest.raises(DataProblem, match="limited to 1,000 MB"):
        read_table("x.csv", b"name\nKari Nordmann\n")
    monkeypatch.setattr(io, "MAX_UPLOAD_BYTES", 1000 * 1024 * 1024)
    monkeypatch.setattr(io, "MAX_TABLE_ROWS", 2)
    with pytest.raises(DataProblem, match="3 rows, above the 2-row limit. Split the file"):
        read_table("x.csv", b"name\na\nb\nc\n")


def test_many_problems_are_summarized_not_listed() -> None:
    text = "name,followers\n" + "".join(f"P{i},ten\n" for i in range(100))
    with pytest.raises(DataProblem) as problem:
        validate_creators(read_table("x.csv", text.encode()))
    message = str(problem.value)
    assert message.count("is not a number") == io.MAX_PROBLEMS_SHOWN
    assert "…and 75 more." in message


def test_bulk_results_import_keeps_blank_cells(campaign_with_creator) -> None:
    store, campaign_id, engagement_id = campaign_with_creator
    first = store.add_deliverable(engagement_id, {"platform": "instagram", "format": "reel", "fee_nok": 1000})
    second = store.add_deliverable(engagement_id, {"platform": "instagram", "format": "story", "fee_nok": 500})
    store.set_results(first, {"views": 100, "clicks": 5})
    clean = validate_results(
        read_table("r.csv", f"deliverable_id,views,clicks\n{first},2 500,\n{second},,7\n".encode()), {first, second}
    )
    assert store.import_results(clean) == 2
    stored = store.deliverables(campaign_id).set_index("id")
    assert stored.loc[first, "views"] == 2500 and stored.loc[first, "clicks"] == 5
    assert pd.isna(stored.loc[second, "views"]) and stored.loc[second, "clicks"] == 7


def test_launchers_and_docker_pass_the_upload_cap() -> None:
    bat = (ROOT / "run_app.bat").read_text(encoding="utf-8")
    assert "set INFLUENCESIGNAL_MAX_UPLOAD_MB=1000" in bat
    assert "--server.maxUploadSize=%INFLUENCESIGNAL_MAX_UPLOAD_MB%" in bat
    command = (ROOT / "run_app.command").read_text(encoding="utf-8")
    assert '--server.maxUploadSize="${INFLUENCESIGNAL_MAX_UPLOAD_MB:-1000}"' in command
    docker = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "STREAMLIT_SERVER_MAX_UPLOAD_SIZE=1000" in docker
    assert "--server.maxUploadSize" not in docker
