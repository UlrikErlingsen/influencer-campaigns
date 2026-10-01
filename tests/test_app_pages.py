from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from influencesignal import DISCLAIMER
from influencesignal.demo import load_demo
from influencesignal.rules import load_rules
from influencesignal.storage import Store

ROOT = Path(__file__).parents[1]
APP = str(ROOT / "app.py")
AUTUMN = "fjellbrus-hostfjell-2026"
# url slug -> text that only that page renders (its kicker), proving navigation landed on it
PAGES = {
    "welcome": "INFLUENCER CAMPAIGNS · NORWAY",
    "creators": "1 · Creators",
    "campaigns": "2 · Campaigns",
    "pipeline": "3 · Pipeline",
    "deliverables": "4 · Deliverables",
    "compliance": "5 · Compliance",
    "results": "6 · Results",
    "report": "7 · Report",
    "settings": "Settings & data",
}


@pytest.fixture(autouse=True)
def isolated_data(tmp_path, monkeypatch):
    monkeypatch.setenv("INFLUENCESIGNAL_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("INFLUENCESIGNAL_NO_DEMO", raising=False)


def _app(page: str = "welcome", campaign: str | None = None) -> AppTest:
    app = AppTest.from_file(APP, default_timeout=120)
    app.query_params["page"] = page
    if campaign:
        app.query_params["campaign"] = campaign
    app.run()
    assert not app.exception, [error.value for error in app.exception]
    return app


def _text(app: AppTest) -> str:
    parts = [str(item.value) for item in app.markdown]
    parts += [str(item.value) for item in app.caption]
    parts += [str(item.value) for item in app.sidebar.caption]
    parts += [str(item.value) for kind in (app.warning, app.error, app.info, app.success) for item in kind]
    return "\n".join(parts)


def _demo_store(folder: Path) -> Store:
    store = Store(folder / "influencesignal.db")
    load_demo(store, load_rules())
    return store


@pytest.mark.parametrize("page", list(PAGES))
def test_every_page_renders_with_the_demo(page: str) -> None:
    app = _app(page)
    assert PAGES[page] in _text(app), f"navigation did not open {page}"
    assert not app.error or page == "compliance", [error.value for error in app.error]
    assert "Fictional demo" in _text(app)


def test_unknown_page_falls_back_to_welcome() -> None:
    assert PAGES["welcome"] in _text(_app("no-such-page"))


@pytest.mark.parametrize("page", ["compliance", "report", "settings", "welcome"])
def test_compliance_screens_carry_the_disclaimer(page: str) -> None:
    assert DISCLAIMER in _text(_app(page))


def test_campaign_query_parameter_selects_the_campaign() -> None:
    app = _app("results", campaign="fjellbrus-varlop-2026")
    store = Store(Path(app.session_state["db_path"]))
    assert store.campaign(app.session_state["campaign_id"])["slug"] == "fjellbrus-varlop-2026"


def test_compliance_page_shows_the_missing_label_warning() -> None:
    app = _app("compliance", campaign=AUTUMN)
    assert any("answered No" in str(error.value) for error in app.error)


def test_pipeline_gate_refuses_paid_for_the_unlabelled_post() -> None:
    app = _app("pipeline", campaign=AUTUMN)
    stage_boxes = [box for box in app.selectbox if box.key and box.key.startswith("stage_") and box.value == "Published"]
    assert stage_boxes
    stage_boxes[0].set_value("Paid").run()
    assert not app.exception, [error.value for error in app.exception]
    assert any("Cannot move to Paid" in str(error.value) for error in app.error)
    assert PAGES["pipeline"] in _text(app), "the page must not change after a refused move"


def test_pipeline_cards_escape_creator_text(tmp_path) -> None:
    store = _demo_store(tmp_path)
    campaign_id = int(store.campaigns().query(f"slug == '{AUTUMN}'")["id"].iloc[0])
    creator_id = store.add_creator({"name": '<img src=x onerror="alert(1)">', "instagram": "x"})
    store.add_to_shortlist(campaign_id, [creator_id])

    app = _app("pipeline", campaign=AUTUMN)
    cards = [str(item.value) for item in app.markdown if "card-name" in str(item.value)]
    assert any("&lt;img src=x" in card for card in cards)
    assert not any("<img src=x" in card for card in cards)


def test_unusable_data_folder_keeps_current_database(tmp_path) -> None:
    blocker = tmp_path / "not-a-folder"
    blocker.write_text("a file, not a folder", encoding="utf-8")
    app = _app("settings")
    before = app.session_state["db_path"]
    next(box for box in app.text_input if box.label == "Data folder").set_value(str(blocker))
    next(button for button in app.button if button.label == "Use this folder").click().run()
    assert not app.exception, [error.value for error in app.exception]
    assert app.session_state["db_path"] == before
    assert any("Could not use that folder" in str(error.value) for error in app.error)


def test_compliance_page_flags_changes_after_payment(tmp_path) -> None:
    store = _demo_store(tmp_path)
    campaign_id = int(store.campaigns().query(f"slug == '{AUTUMN}'")["id"].iloc[0])
    paid = store.deliverables(campaign_id).query("stage == 'Paid'").iloc[0]
    store.set_answer(int(paid["id"]), "ad_identified", "no")

    app = _app("compliance", campaign=AUTUMN)
    assert any("changed after payment" in str(warning.value) for warning in app.warning)


def test_no_external_calls_in_source() -> None:
    files = [Path(APP), *(ROOT / "pages").glob("*.py"), *(ROOT / "src" / "influencesignal").glob("*.py")]
    joined = "\n".join(path.read_text(encoding="utf-8") for path in files)
    for forbidden in ("requests.", "urllib.request", "httpx", "graph.facebook", "api.tiktok", "openai", "anthropic"):
        assert forbidden not in joined, forbidden
