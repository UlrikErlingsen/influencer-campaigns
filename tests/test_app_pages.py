from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from creatorsignal import DISCLAIMER

ROOT = Path(__file__).parents[1]
APP = str(ROOT / "app.py")
PAGES = [
    "Welcome",
    "1 · Creators",
    "2 · Campaigns",
    "3 · Pipeline",
    "4 · Deliverables",
    "5 · Compliance",
    "6 · Results",
    "7 · Report",
    "Settings & data",
]


@pytest.fixture(autouse=True)
def isolated_data(tmp_path, monkeypatch):
    monkeypatch.setenv("CREATORSIGNAL_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("CREATORSIGNAL_NO_DEMO", raising=False)


def _app() -> AppTest:
    app = AppTest.from_file(APP, default_timeout=120)
    app.run()
    return app


def _text(app: AppTest) -> str:
    parts = [str(item.value) for item in app.markdown]
    parts += [str(item.value) for item in app.caption]
    parts += [str(item.value) for item in app.sidebar.caption]
    parts += [str(item.value) for kind in (app.warning, app.error, app.info, app.success) for item in kind]
    return "\n".join(parts)


@pytest.mark.parametrize("page", PAGES)
def test_every_page_renders_with_the_demo(page: str) -> None:
    app = _app()
    app.sidebar.radio[0].set_value(page).run()
    assert not app.exception, [error.value for error in app.exception]
    assert not app.error or page == "5 · Compliance", [error.value for error in app.error]
    assert "Fictional demo" in _text(app)


@pytest.mark.parametrize("page", ["5 · Compliance", "7 · Report", "Settings & data", "Welcome"])
def test_compliance_screens_carry_the_disclaimer(page: str) -> None:
    app = _app()
    app.sidebar.radio[0].set_value(page).run()
    assert DISCLAIMER in _text(app)


def test_compliance_page_shows_the_missing_label_warning() -> None:
    app = _app()
    app.sidebar.selectbox[0].set_value(2).run()  # Fjellbrus Høstfjell 2026 (created second)
    app.sidebar.radio[0].set_value("5 · Compliance").run()
    assert any("answered No" in str(error.value) for error in app.error)


def test_pipeline_gate_refuses_paid_for_the_unlabelled_post() -> None:
    app = _app()
    app.sidebar.selectbox[0].set_value(2).run()
    app.sidebar.radio[0].set_value("3 · Pipeline").run()
    stage_boxes = [box for box in app.selectbox if box.key and box.key.startswith("stage_") and box.value == "Published"]
    assert stage_boxes
    for box in stage_boxes:
        box.set_value("Paid").run()
        assert not app.exception, [error.value for error in app.exception]
        assert any("Cannot move to Paid" in str(error.value) for error in app.error)
        break


def test_no_external_calls_in_source() -> None:
    sources = [Path(APP).read_text(encoding="utf-8")]
    sources += [path.read_text(encoding="utf-8") for path in (ROOT / "src" / "creatorsignal").glob("*.py")]
    joined = "\n".join(sources)
    for forbidden in ("requests.", "urllib.request", "httpx", "graph.facebook", "api.tiktok", "openai", "anthropic"):
        assert forbidden not in joined, forbidden
