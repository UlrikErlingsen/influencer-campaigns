import copy

import pytest
import yaml

from influencesignal.errors import DataProblem
from influencesignal.rules import DEFAULT_RULES_PATH, load_rules, parse_rules


def _document() -> dict:
    return yaml.safe_load(DEFAULT_RULES_PATH.read_text(encoding="utf-8"))


def test_bundled_rules_load_with_the_seeded_ids(rules) -> None:
    ids = [rule.id for rule in rules.rules]
    for required in ("ad_identified", "label_wording", "retouch_label", "restricted_category"):
        assert required in ids
    assert rules.jurisdiction == "NO"
    assert "not legal advice" in rules.disclaimer_en.lower()


def test_every_rule_quotes_an_official_https_source(rules) -> None:
    official = ("https://www.forbrukertilsynet.no/", "https://lovdata.no/")
    for rule in rules.rules:
        assert rule.label_no and rule.label_en and rule.question_no and rule.question_en
        if rule.applies_when == "restricted_category":
            assert {"alcohol", "gambling", "tobacco_nicotine", "children"} <= set(rule.categories_dict() if hasattr(rule, "categories_dict") else {c.key for c in rule.categories})
            continue
        assert rule.sources, rule.id
        assert any(source.url.startswith(official) and source.quote for source in rule.sources), rule.id


def test_label_wording_rule_quotes_forbrukertilsynet_recommendation(rules) -> None:
    rule = rules.by_id("label_wording")
    quotes = " ".join(source.quote for source in rule.sources)
    assert "«sponset»" in quotes and "«i samarbeid med»" in quotes
    assert "reklame" in rule.question_no and "annonse" in rule.question_no
    assert rule.primary_url == "https://www.forbrukertilsynet.no/lov-og-rett/veiledninger-og-retningslinjer/someveiledning"


def test_retouch_rule_allows_not_applicable_and_cites_section_2(rules) -> None:
    rule = rules.by_id("retouch_label")
    assert rule.allow_not_applicable
    assert rule.applies_when == "shows_person"
    assert "§ 2" in rule.legal_basis and "1 July 2022" in rule.legal_basis


def test_unresolved_legal_details_are_marked_todo_verify() -> None:
    assert "TODO(verify)" in DEFAULT_RULES_PATH.read_text(encoding="utf-8")


def test_custom_rules_file_loads(tmp_path) -> None:
    path = tmp_path / "rules.yaml"
    path.write_text(yaml.safe_dump(_document(), allow_unicode=True), encoding="utf-8")
    assert len(load_rules(path).rules) == len(load_rules().rules)


@pytest.mark.parametrize(
    "mutate, message",
    [
        (lambda d: d.update(rules=[]), "non-empty"),
        (lambda d: d["rules"].append(copy.deepcopy(d["rules"][0])), "unique"),
        (lambda d: d["rules"][0].update(applies_when="sometimes"), "applies_when"),
        (lambda d: d["rules"][0].update(check="maybe"), "check"),
        (lambda d: d["rules"][0].update(id="Bad Id"), "snake_case"),
        (lambda d: d["rules"][0]["sources"][0].update(url="http://insecure.example"), "https"),
        (lambda d: d["rules"][0].update(sources=[]), "source"),
        (lambda d: d["rules"][0]["label"].pop("en"), "label.en"),
        (lambda d: d.update(disclaimer={"en": "All good."}), "not legal advice"),
    ],
)
def test_invalid_rules_are_rejected_with_a_clear_message(mutate, message: str) -> None:
    document = _document()
    mutate(document)
    with pytest.raises(DataProblem, match=message):
        parse_rules(document)


def test_missing_and_malformed_files(tmp_path) -> None:
    with pytest.raises(DataProblem, match="not found"):
        load_rules(tmp_path / "nope.yaml")
    bad = tmp_path / "bad.yaml"
    bad.write_text("rules: [unclosed", encoding="utf-8")
    with pytest.raises(DataProblem, match="YAML"):
        load_rules(bad)
