"""Load and validate the editable compliance rules (``rules/no.yaml``)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re

import yaml

from .errors import DataProblem

DEFAULT_RULES_PATH = Path(__file__).resolve().parent / "rules" / "no.yaml"
APPLIES_WHEN = ("always", "shows_person", "format_story", "restricted_category")
CHECK_TYPES = ("yes_no", "acknowledge")
_ID = re.compile(r"^[a-z][a-z0-9_]*$")


@dataclass(frozen=True)
class Source:
    title: str
    url: str
    quote: str = ""  # original wording, verbatim from the source
    fetched: str = ""
    quote_en: str = ""  # unofficial English translation shown first


@dataclass(frozen=True)
class Category:
    key: str
    label: str
    url: str
    quote: str = ""
    note: str = ""
    quote_en: str = ""


@dataclass(frozen=True)
class Rule:
    id: str
    label_no: str
    label_en: str
    question_no: str
    question_en: str
    applies_when: str
    check: str
    allow_not_applicable: bool
    legal_basis: str
    sources: tuple[Source, ...]
    help_en: str = ""
    not_applicable_label_en: str = "Not applicable"
    not_applicable_label_no: str = ""  # optional; the app shows English only
    categories: tuple[Category, ...] = field(default_factory=tuple)

    @property
    def primary_url(self) -> str:
        return self.sources[0].url if self.sources else ""


@dataclass(frozen=True)
class RuleSet:
    version: int
    jurisdiction: str
    fetched: str
    disclaimer_en: str
    disclaimer_no: str
    rules: tuple[Rule, ...]

    def by_id(self, rule_id: str) -> Rule:
        for rule in self.rules:
            if rule.id == rule_id:
                return rule
        raise KeyError(rule_id)

    @property
    def restricted_categories(self) -> dict[str, Category]:
        categories: dict[str, Category] = {}
        for rule in self.rules:
            if rule.applies_when == "restricted_category":
                categories.update({category.key: category for category in rule.categories})
        return categories


def _text(mapping: object, key: str, where: str, *, required: bool = True) -> str:
    if not isinstance(mapping, dict):
        raise DataProblem(f"{where} must be a mapping with '{key}'.")
    value = mapping.get(key, "")
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise DataProblem(f"{where}.{key} must be text.")
    if required and not value.strip():
        raise DataProblem(f"{where}.{key} is required.")
    return value.strip()


def _parse_rule(raw: object, position: int) -> Rule:
    where = f"rules[{position}]"
    if not isinstance(raw, dict):
        raise DataProblem(f"{where} must be a mapping.")
    rule_id = _text(raw, "id", where)
    if not _ID.match(rule_id):
        raise DataProblem(f"{where}.id '{rule_id}' must be snake_case (a-z, 0-9, underscore).")
    where = f"rule '{rule_id}'"
    applies_when = _text(raw, "applies_when", where)
    if applies_when not in APPLIES_WHEN:
        raise DataProblem(f"{where}: applies_when must be one of {', '.join(APPLIES_WHEN)}.")
    check = _text(raw, "check", where)
    if check not in CHECK_TYPES:
        raise DataProblem(f"{where}: check must be one of {', '.join(CHECK_TYPES)}.")

    raw_sources = raw.get("sources") or []
    if not isinstance(raw_sources, list):
        raise DataProblem(f"{where}: sources must be a list.")
    sources = []
    for index, source in enumerate(raw_sources):
        url = _text(source, "url", f"{where}.sources[{index}]")
        if not url.startswith("https://"):
            raise DataProblem(f"{where}.sources[{index}].url must be an https:// URL.")
        sources.append(
            Source(
                title=_text(source, "title", f"{where}.sources[{index}]"),
                url=url,
                quote=_text(source, "quote", f"{where}.sources[{index}]", required=False),
                fetched=str(source.get("fetched", "") or ""),
                quote_en=_text(source, "quote_en", f"{where}.sources[{index}]", required=False),
            )
        )

    categories = []
    raw_categories = raw.get("categories") or {}
    if applies_when == "restricted_category":
        if not isinstance(raw_categories, dict) or not raw_categories:
            raise DataProblem(f"{where}: a restricted_category rule needs a 'categories' mapping.")
        for key, category in raw_categories.items():
            url = _text(category, "url", f"{where}.categories.{key}")
            if not url.startswith("https://"):
                raise DataProblem(f"{where}.categories.{key}.url must be an https:// URL.")
            categories.append(
                Category(
                    key=str(key),
                    label=_text(category, "label", f"{where}.categories.{key}"),
                    url=url,
                    quote=_text(category, "quote", f"{where}.categories.{key}", required=False),
                    note=_text(category, "note", f"{where}.categories.{key}", required=False),
                    quote_en=_text(category, "quote_en", f"{where}.categories.{key}", required=False),
                )
            )
    if not sources and not categories:
        raise DataProblem(f"{where}: every rule needs at least one source URL.")

    not_applicable = raw.get("not_applicable_label") or {}
    return Rule(
        id=rule_id,
        label_no=_text(raw.get("label"), "no", f"{where}.label", required=False),
        label_en=_text(raw.get("label"), "en", f"{where}.label"),
        question_no=_text(raw.get("question"), "no", f"{where}.question", required=False),
        question_en=_text(raw.get("question"), "en", f"{where}.question"),
        applies_when=applies_when,
        check=check,
        allow_not_applicable=bool(raw.get("allow_not_applicable", False)),
        legal_basis=_text(raw, "legal_basis", where, required=False),
        sources=tuple(sources),
        help_en=_text(raw.get("help") or {}, "en", f"{where}.help", required=False),
        not_applicable_label_en=not_applicable.get("en", "Not applicable") if isinstance(not_applicable, dict) else "Not applicable",
        not_applicable_label_no=not_applicable.get("no", "") if isinstance(not_applicable, dict) else "",
        categories=tuple(categories),
    )


def parse_rules(document: object) -> RuleSet:
    """Validate a parsed YAML document and return an immutable rule set."""
    if not isinstance(document, dict):
        raise DataProblem("The rules file must be a YAML mapping with a 'rules' list.")
    raw_rules = document.get("rules")
    if not isinstance(raw_rules, list) or not raw_rules:
        raise DataProblem("The rules file needs a non-empty 'rules' list.")
    rules = tuple(_parse_rule(raw, position) for position, raw in enumerate(raw_rules))
    ids = [rule.id for rule in rules]
    duplicates = sorted({rule_id for rule_id in ids if ids.count(rule_id) > 1})
    if duplicates:
        raise DataProblem("Rule ids must be unique; duplicated: " + ", ".join(duplicates))
    disclaimer = document.get("disclaimer") or {}
    disclaimer_en = disclaimer.get("en", "") if isinstance(disclaimer, dict) else ""
    if "not legal advice" not in disclaimer_en.lower():
        raise DataProblem("The rules file must keep an English disclaimer stating it is not legal advice.")
    return RuleSet(
        version=int(document.get("version", 1)),
        jurisdiction=str(document.get("jurisdiction", "")),
        fetched=str(document.get("fetched", "")),
        disclaimer_en=disclaimer_en,
        disclaimer_no=disclaimer.get("no", "") if isinstance(disclaimer, dict) else "",
        rules=rules,
    )


def load_rules(path: str | Path | None = None) -> RuleSet:
    """Load the rules YAML (default: the bundled Norwegian rules)."""
    rules_path = Path(path) if path else DEFAULT_RULES_PATH
    try:
        document = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DataProblem(f"Rules file not found: {rules_path}") from exc
    except yaml.YAMLError as exc:
        raise DataProblem(f"The rules file is not valid YAML: {exc}") from exc
    return parse_rules(document)
