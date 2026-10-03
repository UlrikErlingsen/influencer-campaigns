"""Data limits: none locally (the old 20 MB / 50,000-row limits are gone); demo caps only with SIGNAL_PUBLIC=1."""

from pathlib import Path

import pandas as pd
import pytest

from influencesignal import limits
from influencesignal.errors import DataProblem, friendly_message
from influencesignal.io import read_table, validate_creators, validate_results

ROOT = Path(__file__).resolve().parents[1]


def _roster(rows: int, columns: int = 0) -> bytes:
    extra = "".join(f";extra_{index}" for index in range(columns))
    body = "".join(f"Skaper {i};demo_{i};{1000 + i};3,5;Oslo{';x' * columns}\n" for i in range(rows))
    return ("name;instagram;followers;engagement_rate;region" + extra + "\n" + body).encode("utf-8")


def test_local_mode_accepts_input_beyond_the_demo_caps(store, monkeypatch) -> None:
    monkeypatch.delenv("SIGNAL_PUBLIC", raising=False)
    rows = limits.DEMO_MAX_TABLE_ROWS + 10_000  # also above the old 50,000-row limit
    clean, warnings = validate_creators(read_table("roster.csv", _roster(rows)))
    assert len(clean) == rows and not warnings
    assert clean["engagement_rate"].iloc[-1] == pytest.approx(3.5)
    assert store.import_creators(clean) == (rows, 0)
    assert store.import_creators(clean.head(10)) == (0, 10)
    assert len(store.creators()) == rows
    wide = read_table("wide.csv", _roster(2, columns=limits.DEMO_MAX_TABLE_COLUMNS))
    assert len(wide.columns) > limits.DEMO_MAX_TABLE_COLUMNS


def test_public_demo_enforces_its_caps(monkeypatch) -> None:
    monkeypatch.setenv("SIGNAL_PUBLIC", "1")
    monkeypatch.setattr(limits, "DEMO_MAX_UPLOAD_MB", 0)
    with pytest.raises(DataProblem, match="Uploads are limited to 0 MB. This is a limit of the public demo"):
        read_table("x.csv", b"name\nKari Nordmann\n")
    monkeypatch.setattr(limits, "DEMO_MAX_UPLOAD_MB", 20)
    monkeypatch.setattr(limits, "DEMO_MAX_TABLE_ROWS", 2)
    with pytest.raises(DataProblem, match="3 rows, above the 2-row limit. This is a limit of the public demo"):
        read_table("x.csv", b"name\na\nb\nc\n")
    monkeypatch.setattr(limits, "DEMO_MAX_TABLE_ROWS", 50_000)
    with pytest.raises(DataProblem, match="column limit. This is a limit of the public demo; the downloaded app"):
        read_table("wide.csv", _roster(2, columns=limits.DEMO_MAX_TABLE_COLUMNS))
    monkeypatch.setattr(limits, "DEMO_MAX_EXPANDED_WORKBOOK_MB", 0)
    with pytest.raises(DataProblem, match="expands beyond 0 MB"):
        limits.check_workbook_expansion(1)


def test_out_of_memory_is_a_plain_message(monkeypatch) -> None:
    assert "not enough memory" in friendly_message(MemoryError())

    def no_memory(*args, **kwargs):
        raise MemoryError

    monkeypatch.setattr(pd, "read_csv", no_memory)
    with pytest.raises(DataProblem, match="not enough memory on this computer"):
        read_table("x.csv", b"name\nKari\n")


def test_many_problems_are_summarized_not_listed() -> None:
    text = "name,followers\n" + "".join(f"P{i},ten\n" for i in range(100))
    with pytest.raises(DataProblem) as problem:
        validate_creators(read_table("x.csv", text.encode()))
    message = str(problem.value)
    assert message.count("is not a number") == 25
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
    assert "set INFLUENCESIGNAL_MAX_UPLOAD_MB=10000" in bat
    assert "--server.maxUploadSize=%INFLUENCESIGNAL_MAX_UPLOAD_MB%" in bat
    command = (ROOT / "run_app.command").read_text(encoding="utf-8")
    assert '--server.maxUploadSize="${INFLUENCESIGNAL_MAX_UPLOAD_MB:-10000}"' in command
    docker = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "STREAMLIT_SERVER_MAX_UPLOAD_SIZE=10000" in docker
    assert "--server.maxUploadSize" not in docker
    config = (ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    assert "maxUploadSize = 10000" in config
