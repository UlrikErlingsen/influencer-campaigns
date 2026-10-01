from urllib.parse import parse_qsl, urlsplit

import pytest

from influencesignal.errors import DataProblem
from influencesignal.utm import build_tracked_url, creator_token, slugify, utm_params


def test_scheme_is_exactly_as_specified() -> None:
    url = build_tracked_url("https://fjellbrus.example/varlop", "Instagram", "fjellbrus-varlop-2026", "demo_kari_trener")
    assert url == (
        "https://fjellbrus.example/varlop?utm_source=instagram&utm_medium=influencer"
        "&utm_campaign=fjellbrus-varlop-2026&utm_content=demo_kari_trener"
    )


def test_parameter_order_is_fixed() -> None:
    assert list(utm_params("tiktok", "x", "y")) == ["utm_source", "utm_medium", "utm_campaign", "utm_content"]


def test_existing_query_and_fragment_are_kept_and_old_utm_replaced() -> None:
    url = build_tracked_url(
        "https://shop.example/p?ref=abc&utm_source=old&utm_term=x#top", "youtube", "Høstfjell 2026", "@Åse_Ø"
    )
    parts = urlsplit(url)
    params = parse_qsl(parts.query)
    assert ("ref", "abc") in params
    assert ("utm_source", "old") not in params and all(key != "utm_term" for key, _ in params)
    assert dict(params)["utm_campaign"] == "hostfjell-2026"
    assert dict(params)["utm_content"] == "ase_o"
    assert parts.fragment == "top"


def test_norwegian_letters_are_transliterated() -> None:
    assert slugify("Ærlig Østlandsk Årstid") == "aerlig-ostlandsk-arstid"
    assert slugify("  --Vår!!løp-- ") == "var-lop"


def test_creator_token_prefers_handle_and_falls_back_to_name() -> None:
    assert creator_token("@Demo.Kari", "Kari") == "demo_kari"
    assert creator_token("", "Kari Nordmann") == "kari_nordmann"
    with pytest.raises(DataProblem):
        creator_token("", "")


@pytest.mark.parametrize("landing", ["", "fjellbrus.example", "ftp://x.example/", "javascript:alert(1)"])
def test_landing_page_must_be_http_url(landing: str) -> None:
    with pytest.raises(DataProblem):
        build_tracked_url(landing, "instagram", "c", "x")


def test_unknown_platform_and_empty_campaign_are_rejected() -> None:
    with pytest.raises(DataProblem):
        utm_params("myspace", "c", "x")
    with pytest.raises(DataProblem):
        utm_params("instagram", "!!", "x")
