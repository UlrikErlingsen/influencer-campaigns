"""End-to-end through the Streamlit UI, starting from an empty workspace (no demo).

Campaign → creator → shortlist → deliverable with tracked link → published → checklist → Paid → results → report.
"""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from influencesignal.storage import Store

APP = str(Path(__file__).parents[1] / "app.py")


@pytest.fixture
def workspace(tmp_path, monkeypatch) -> Path:
    monkeypatch.setenv("INFLUENCESIGNAL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("INFLUENCESIGNAL_NO_DEMO", "1")
    return tmp_path / "influencesignal.db"


def _open(page: str) -> AppTest:
    app = AppTest.from_file(APP, default_timeout=120)
    app.query_params["page"] = page
    app.run()
    _ok(app)
    return app


def _ok(app: AppTest) -> None:
    assert not app.exception, [error.value for error in app.exception]
    assert not app.error, [error.value for error in app.error]


def _button(app: AppTest, label: str):
    return next(button for button in app.button if button.label == label)


def test_full_campaign_workflow_through_the_ui(workspace: Path) -> None:
    # Empty workspace: no demo, and pages say what to do first.
    app = _open("pipeline")
    assert any("Create a campaign" in str(info.value) for info in app.info)
    store = Store(workspace)
    assert store.is_empty() and not store.has_demo_data()

    # 1. Campaign.
    app = _open("campaigns")
    app.text_input(key="newc_name").set_value("Vinter Test 2026")
    app.text_input(key="newc_brand").set_value("Testmerke")
    app.selectbox(key="newc_goal").set_value("sales")
    app.number_input(key="newc_budget").set_value(50000)
    app.text_input(key="newc_url").set_value("https://shop.example/vinter?src=ig")
    _button(app, "Create campaign").click().run()
    _ok(app)
    campaign = store.campaigns().iloc[0]
    assert campaign["slug"] == "vinter-test-2026" and campaign["budget_nok"] == 50000

    # 2. Creator; unknown followers stay unknown.
    app = _open("creators")
    app.text_input(key="new_name").set_value("Åse Test")
    app.text_input(key="new_instagram").set_value("@ase.test")
    app.selectbox(key="new_region").set_value("Trøndelag")
    _button(app, "Add creator").click().run()
    _ok(app)
    creator = store.creators().iloc[0]
    assert creator["instagram"] == "ase.test" and creator["region"] == "Trøndelag"
    assert creator["followers"] is None or creator["followers"] != creator["followers"]  # None or NaN

    # 3. Shortlist.
    app = _open("pipeline")
    app.multiselect[0].set_value([int(creator["id"])]).run()
    _button(app, "Add to shortlist").click().run()
    _ok(app)
    engagements = store.engagements(int(campaign["id"]))
    assert list(engagements["stage"]) == ["Shortlist"]

    # 4. Deliverable with a tracked link in the house UTM scheme.
    app = _open("deliverables")
    app.selectbox(key="new_deliv_format").set_value("reel")
    app.number_input(key="new_deliv_fee").set_value(4000)
    app.text_input(key="new_deliv_code").set_value("VINTER-ASE")
    _button(app, "Add deliverable").click().run()
    _ok(app)
    deliverable = store.deliverables(int(campaign["id"])).iloc[0]
    assert deliverable["tracked_url"] == (
        "https://shop.example/vinter?src=ig&utm_source=instagram&utm_medium=influencer"
        "&utm_campaign=vinter-test-2026&utm_content=ase_test"
    )
    deliverable_id = int(deliverable["id"])

    # The gate refuses Paid before publishing and checking.
    app = _open("pipeline")
    app.selectbox(key=f"stage_{int(engagements['id'].iloc[0])}_Shortlist").set_value("Paid").run()
    assert any("Cannot move to Paid" in str(error.value) for error in app.error)
    assert store.engagements(int(campaign["id"]))["stage"].iloc[0] == "Shortlist"

    # 5. Mark it published.
    app = _open("deliverables")
    app.checkbox(key=f"d{deliverable_id}_pub").check()
    app.text_input(key=f"d{deliverable_id}_post").set_value("https://www.instagram.com/p/example")
    app.button(key=f"d{deliverable_id}_save").click().run()
    _ok(app)
    assert store.deliverable(deliverable_id)["published_date"]

    # 6. Checklist: answer every applicable rule.
    app = _open("compliance")
    radios = [radio for radio in app.radio if radio.key and radio.key.startswith(f"ans_{deliverable_id}_")]
    assert {radio.key.split("_", 2)[2] for radio in radios} == {"ad_identified", "label_wording", "retouch_label"}
    for radio in radios:
        radio.set_value("na" if radio.key.endswith("retouch_label") else "yes")
    _button(app, "Save checklist").click().run()
    _ok(app)
    assert store.answers(deliverable_id) == {"ad_identified": "yes", "label_wording": "yes", "retouch_label": "na"}

    # 7. Now Paid is allowed.
    app = _open("pipeline")
    app.selectbox(key=f"stage_{int(engagements['id'].iloc[0])}_Shortlist").set_value("Paid").run()
    _ok(app)
    assert store.engagements(int(campaign["id"]))["stage"].iloc[0] == "Paid"

    # 8. Results and metrics.
    store.set_results(deliverable_id, {"views": 20000, "clicks": 160, "redemptions": 20, "revenue_nok": 9000})
    app = _open("results")
    metrics = {metric.label: metric.value for metric in app.metric}
    assert metrics["CPM"] == "200 NOK"
    assert metrics["CPC"] == "25.0 NOK"
    assert metrics["Cost / redemption"] == "200 NOK"
    assert metrics["ROAS"] == "2.25"

    # 9. Report renders with download buttons.
    app = _open("report")
    assert {"Checklists complete": "1", "Open checklist items": "0"}.items() <= {
        metric.label: metric.value for metric in app.metric
    }.items()


def test_restricted_category_and_workspace_actions(workspace: Path) -> None:
    store = Store(workspace)
    campaign_id = store.add_campaign({"name": "Øl Test", "goal": "awareness", "landing_url": "https://x.example/"})
    creator_id = store.add_creator({"name": "Kim Test", "tiktok": "kim_t"})
    store.add_to_shortlist(campaign_id, [creator_id])
    engagement_id = int(store.engagements(campaign_id)["id"].iloc[0])
    store.add_deliverable(engagement_id, {"platform": "tiktok", "format": "video", "published_date": "2026-10-01"})

    # Edit the campaign to a restricted category through the form.
    app = _open("campaigns")
    app.selectbox(key=f"c{campaign_id}_cat").set_value("alcohol")
    _button(app, "Save campaign").click().run()
    _ok(app)
    assert store.campaign(campaign_id)["category"] == "alcohol"
    assert any("Restricted category flagged" in str(warning.value) for warning in app.warning)

    # The compliance page flags it, links the source, and adds the acknowledgement question.
    app = _open("compliance")
    flags = [str(warning.value) for warning in app.warning if "Restricted category: Alcohol" in str(warning.value)]
    assert flags and "lovdata.no" in flags[0] and "never says the campaign is compliant" in flags[0]
    assert any(radio.key.endswith("_restricted_category") for radio in app.radio if radio.key)

    # Destructive actions need their confirm box first.
    app = _open("settings")
    assert _button(app, "Delete all data").disabled
    app.checkbox(key="confirm_empty").check().run()
    _button(app, "Delete all data").click().run()
    _ok(app)
    assert store.is_empty()

    app = _open("settings")
    assert _button(app, "Reload demo").disabled
    app.checkbox(key="confirm_demo").check().run()
    _button(app, "Reload demo").click().run()
    assert not app.exception, [error.value for error in app.exception]
    assert store.has_demo_data() and len(store.creators()) == 25
