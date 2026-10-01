from pathlib import Path

import pytest

from creatorsignal.demo import load_demo
from creatorsignal.rules import load_rules
from creatorsignal.storage import Store


@pytest.fixture(scope="session")
def rules():
    return load_rules()


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "test.db")


@pytest.fixture
def demo_store(store: Store, rules) -> Store:
    load_demo(store, rules)
    return store


@pytest.fixture
def campaign_with_creator(store: Store):
    """A campaign with one creator on the shortlist; returns (store, campaign_id, engagement_id)."""
    campaign_id = store.add_campaign(
        {"name": "Test Kampanje", "brand": "Testmerke", "goal": "sales", "landing_url": "https://shop.example/x"}
    )
    creator_id = store.add_creator({"name": "Test Person", "instagram": "@test_person"})
    store.add_to_shortlist(campaign_id, [creator_id])
    engagement_id = int(store.engagements(campaign_id)["id"].iloc[0])
    return store, campaign_id, engagement_id
