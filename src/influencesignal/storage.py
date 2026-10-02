"""Local SQLite persistence. One file per workspace; nothing leaves the machine.

``Store(":memory:")`` keeps the workspace in one private in-memory database instead (Signal Hub uses this, one
per browser session, so nothing is written to disk).

The Paid gate is enforced here, not only in the UI: ``move_engagement`` refuses to move a creator to *Paid*
or *Reported* unless every deliverable passes ``compliance.paid_gate``.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3
import threading
from typing import Iterator

import pandas as pd

from .compliance import GATED_STAGES, checklist_status, paid_gate
from .errors import DataProblem, GateBlocked
from .io import CREATOR_COLUMNS
from .metrics import RESULT_COLUMNS
from .rules import RuleSet
from .utm import PLATFORMS, build_tracked_url, creator_token, slugify

STAGES = (
    "Shortlist",
    "Contacted",
    "Negotiating",
    "Contracted",
    "Content in review",
    "Published",
    "Paid",
    "Reported",
)
GOALS = ("awareness", "traffic", "sales")
FORMATS = ("reel", "story", "post", "video")
CATEGORIES = ("general", "alcohol", "gambling", "tobacco_nicotine")
DEFAULT_DATA_DIR = Path("data")
DB_NAME = "influencesignal.db"
MEMORY = ":memory:"

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS creators (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    instagram TEXT DEFAULT '', tiktok TEXT DEFAULT '', youtube TEXT DEFAULT '', snapchat TEXT DEFAULT '',
    followers INTEGER, engagement_rate REAL,
    niche_tags TEXT DEFAULT '', region TEXT DEFAULT '',
    contact_email TEXT DEFAULT '', contact_phone TEXT DEFAULT '',
    rate_card TEXT DEFAULT '', notes TEXT DEFAULT '',
    is_demo INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS campaigns (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    brand TEXT NOT NULL DEFAULT '',
    goal TEXT NOT NULL DEFAULT 'awareness',
    category TEXT NOT NULL DEFAULT 'general',
    targets_children INTEGER NOT NULL DEFAULT 0,
    budget_nok REAL,
    start_date TEXT DEFAULT '', end_date TEXT DEFAULT '',
    landing_url TEXT DEFAULT '',
    brief TEXT DEFAULT '', deliverables_template TEXT DEFAULT '',
    is_demo INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS engagements (
    id INTEGER PRIMARY KEY,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    creator_id INTEGER NOT NULL REFERENCES creators(id) ON DELETE CASCADE,
    stage TEXT NOT NULL DEFAULT 'Shortlist',
    notes TEXT DEFAULT '',
    UNIQUE (campaign_id, creator_id)
);
CREATE TABLE IF NOT EXISTS deliverables (
    id INTEGER PRIMARY KEY,
    engagement_id INTEGER NOT NULL REFERENCES engagements(id) ON DELETE CASCADE,
    platform TEXT NOT NULL,
    format TEXT NOT NULL,
    due_date TEXT DEFAULT '',
    fee_nok REAL,
    discount_code TEXT DEFAULT '',
    tracked_url TEXT DEFAULT '',
    published_date TEXT DEFAULT '',
    post_url TEXT DEFAULT '',
    shows_person INTEGER NOT NULL DEFAULT 1,
    override_reason TEXT DEFAULT '',
    reach REAL, views REAL, clicks REAL, redemptions REAL, revenue_nok REAL
);
CREATE TABLE IF NOT EXISTS checks (
    deliverable_id INTEGER NOT NULL REFERENCES deliverables(id) ON DELETE CASCADE,
    rule_id TEXT NOT NULL,
    answer TEXT NOT NULL,
    note TEXT DEFAULT '',
    checked_at TEXT NOT NULL,
    PRIMARY KEY (deliverable_id, rule_id)
);
CREATE TABLE IF NOT EXISTS stage_log (
    id INTEGER PRIMARY KEY,
    engagement_id INTEGER NOT NULL REFERENCES engagements(id) ON DELETE CASCADE,
    from_stage TEXT, to_stage TEXT NOT NULL,
    at TEXT NOT NULL, note TEXT DEFAULT ''
);
"""

CAMPAIGN_FIELDS = (
    "name", "brand", "goal", "category", "targets_children", "budget_nok", "start_date", "end_date",
    "landing_url", "brief", "deliverables_template",
)
DELIVERABLE_FIELDS = (
    "platform", "format", "due_date", "fee_nok", "discount_code", "published_date", "post_url", "shows_person",
    "override_reason",
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def default_db_path() -> Path:
    folder = os.environ.get("INFLUENCESIGNAL_DATA_DIR", "").strip()
    return (Path(folder) if folder else DEFAULT_DATA_DIR) / DB_NAME


def _clean_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    return str(value).strip()


def _clean_number(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise DataProblem(f"'{value}' is not a number.") from exc
    if pd.isna(number):
        return None
    if number < 0:
        raise DataProblem("Amounts and counts cannot be negative.")
    return number


class Store:
    """Thin data-access layer over one SQLite file (or one private in-memory database)."""

    def __init__(self, path: str | Path) -> None:
        self.in_memory = str(path) == MEMORY
        self.path = Path(path)
        self._memory: sqlite3.Connection | None = None
        self._lock = threading.RLock()
        if self.in_memory:
            # One connection for the store's lifetime: an in-memory database lives only as long as its connection.
            self._memory = sqlite3.connect(MEMORY, check_same_thread=False)
            self._memory.row_factory = sqlite3.Row
            self._memory.execute("PRAGMA foreign_keys = ON")
        else:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        if self._memory is not None:
            with self._lock:
                try:
                    yield self._memory
                    self._memory.commit()
                except Exception:
                    self._memory.rollback()
                    raise
            return
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _frame(self, query: str, params: tuple = ()) -> pd.DataFrame:
        with self._connect() as connection:
            return pd.read_sql_query(query, connection, params=params)

    def _row(self, query: str, params: tuple = ()) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(query, params).fetchone()
        return dict(row) if row else None

    # ── workspace ────────────────────────────────────────────────────────────────────────────────
    def is_empty(self) -> bool:
        with self._connect() as connection:
            return all(
                connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
                for table in ("creators", "campaigns")
            )

    def has_demo_data(self) -> bool:
        with self._connect() as connection:
            return any(
                connection.execute(f"SELECT 1 FROM {table} WHERE is_demo = 1 LIMIT 1").fetchone()
                for table in ("creators", "campaigns")
            )

    def clear(self) -> None:
        with self._connect() as connection:
            for table in ("stage_log", "checks", "deliverables", "engagements", "campaigns", "creators"):
                connection.execute(f"DELETE FROM {table}")

    # ── creators ─────────────────────────────────────────────────────────────────────────────────
    def creators(self) -> pd.DataFrame:
        return self._frame("SELECT * FROM creators ORDER BY name COLLATE NOCASE")

    def creator(self, creator_id: int) -> dict:
        row = self._row("SELECT * FROM creators WHERE id = ?", (creator_id,))
        if row is None:
            raise DataProblem("That creator no longer exists.")
        return row

    def _creator_values(self, data: dict) -> dict:
        values = {column: _clean_text(data.get(column)) for column in CREATOR_COLUMNS}
        if not values["name"]:
            raise DataProblem("A creator needs a name.")
        for platform in PLATFORMS:
            values[platform] = values[platform].lstrip("@")
        followers = _clean_number(data.get("followers"))
        values["followers"] = int(followers) if followers is not None else None
        rate = _clean_number(data.get("engagement_rate"))
        if rate is not None and rate > 100:
            raise DataProblem("Engagement rate is a percentage between 0 and 100.")
        values["engagement_rate"] = rate
        return values

    def add_creator(self, data: dict, *, is_demo: bool = False) -> int:
        values = self._creator_values(data)
        values["is_demo"] = int(is_demo)
        columns = ", ".join(values)
        marks = ", ".join("?" for _ in values)
        with self._connect() as connection:
            cursor = connection.execute(f"INSERT INTO creators ({columns}) VALUES ({marks})", tuple(values.values()))
            return int(cursor.lastrowid)

    def update_creator(self, creator_id: int, data: dict) -> None:
        values = self._creator_values(data)
        assignments = ", ".join(f"{column} = ?" for column in values)
        with self._connect() as connection:
            connection.execute(f"UPDATE creators SET {assignments} WHERE id = ?", (*values.values(), creator_id))

    def delete_creator(self, creator_id: int) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM creators WHERE id = ?", (creator_id,))

    def import_creators(self, frame: pd.DataFrame) -> tuple[int, int]:
        """Insert validated creators; rows whose name already exists update that creator. Returns (added, updated)."""
        existing = {str(name).casefold(): int(cid) for cid, name in self.creators()[["id", "name"]].itertuples(index=False)}
        added = updated = 0
        for row in frame.to_dict("records"):
            match = existing.get(str(row["name"]).casefold())
            if match is None:
                existing[str(row["name"]).casefold()] = self.add_creator(row)
                added += 1
            else:
                self.update_creator(match, row)
                updated += 1
        return added, updated

    # ── campaigns ────────────────────────────────────────────────────────────────────────────────
    def campaigns(self) -> pd.DataFrame:
        return self._frame("SELECT * FROM campaigns ORDER BY start_date DESC, name COLLATE NOCASE")

    def campaign(self, campaign_id: int) -> dict:
        row = self._row("SELECT * FROM campaigns WHERE id = ?", (campaign_id,))
        if row is None:
            raise DataProblem("That campaign no longer exists.")
        return row

    def _campaign_values(self, data: dict) -> dict:
        values = {field: _clean_text(data.get(field)) for field in CAMPAIGN_FIELDS}
        if not values["name"]:
            raise DataProblem("A campaign needs a name.")
        if values["goal"] not in GOALS:
            raise DataProblem(f"Goal must be one of: {', '.join(GOALS)}.")
        values["category"] = values["category"] or "general"
        if values["category"] not in CATEGORIES:
            raise DataProblem(f"Category must be one of: {', '.join(CATEGORIES)}.")
        values["targets_children"] = int(bool(data.get("targets_children")))
        values["budget_nok"] = _clean_number(data.get("budget_nok"))
        if values["start_date"] and values["end_date"] and values["end_date"] < values["start_date"]:
            raise DataProblem("The campaign end date is before its start date.")
        return values

    def add_campaign(self, data: dict, *, is_demo: bool = False) -> int:
        values = self._campaign_values(data)
        base = slugify(data.get("slug") or values["name"]) or "campaign"
        slugs = set(self.campaigns()["slug"].tolist())
        slug, counter = base, 2
        while slug in slugs:
            slug, counter = f"{base}-{counter}", counter + 1
        values.update(slug=slug, is_demo=int(is_demo))
        columns = ", ".join(values)
        marks = ", ".join("?" for _ in values)
        with self._connect() as connection:
            cursor = connection.execute(f"INSERT INTO campaigns ({columns}) VALUES ({marks})", tuple(values.values()))
            return int(cursor.lastrowid)

    def update_campaign(self, campaign_id: int, data: dict) -> None:
        values = self._campaign_values(data)
        assignments = ", ".join(f"{column} = ?" for column in values)
        with self._connect() as connection:
            connection.execute(f"UPDATE campaigns SET {assignments} WHERE id = ?", (*values.values(), campaign_id))

    def delete_campaign(self, campaign_id: int) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM campaigns WHERE id = ?", (campaign_id,))

    # ── pipeline ─────────────────────────────────────────────────────────────────────────────────
    def engagements(self, campaign_id: int) -> pd.DataFrame:
        return self._frame(
            """
            SELECT e.id, e.campaign_id, e.creator_id, e.stage, e.notes, c.name AS creator_name,
                   c.instagram, c.tiktok, c.youtube, c.snapchat, c.followers, c.engagement_rate, c.region
            FROM engagements e JOIN creators c ON c.id = e.creator_id
            WHERE e.campaign_id = ?
            ORDER BY c.name COLLATE NOCASE
            """,
            (campaign_id,),
        )

    def add_to_shortlist(self, campaign_id: int, creator_ids: list[int]) -> int:
        added = 0
        with self._connect() as connection:
            for creator_id in creator_ids:
                cursor = connection.execute(
                    "INSERT OR IGNORE INTO engagements (campaign_id, creator_id, stage) VALUES (?, ?, 'Shortlist')",
                    (campaign_id, int(creator_id)),
                )
                if cursor.rowcount:
                    connection.execute(
                        "INSERT INTO stage_log (engagement_id, from_stage, to_stage, at) VALUES (?, NULL, 'Shortlist', ?)",
                        (cursor.lastrowid, _now()),
                    )
                    added += 1
        return added

    def remove_engagement(self, engagement_id: int) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM engagements WHERE id = ?", (engagement_id,))

    def engagement_gate(self, engagement_id: int, rules: RuleSet) -> tuple[bool, list[str]]:
        """Would every deliverable of this engagement pass the Paid gate?"""
        engagement = self._row("SELECT * FROM engagements WHERE id = ?", (engagement_id,))
        if engagement is None:
            raise DataProblem("That pipeline card no longer exists.")
        campaign = self.campaign(int(engagement["campaign_id"]))
        deliverables = self._frame("SELECT * FROM deliverables WHERE engagement_id = ? ORDER BY id", (engagement_id,))
        if deliverables.empty:
            return False, ["No deliverables recorded yet. Add the deliverable(s) before marking the creator Paid."]
        reasons: list[str] = []
        allowed = True
        for deliverable in deliverables.to_dict("records"):
            status = checklist_status(deliverable, campaign, self.answers(int(deliverable["id"])), rules)
            label = f"#{deliverable['id']} {deliverable['platform']} {deliverable['format']}"
            gate = paid_gate(status, rules, label)
            allowed = allowed and gate.allowed
            if not gate.allowed:
                reasons.extend(gate.reasons)
        return allowed, reasons

    def move_engagement(self, engagement_id: int, stage: str, rules: RuleSet, note: str = "") -> None:
        if stage not in STAGES:
            raise DataProblem(f"Unknown stage '{stage}'.")
        engagement = self._row("SELECT * FROM engagements WHERE id = ?", (engagement_id,))
        if engagement is None:
            raise DataProblem("That pipeline card no longer exists.")
        if engagement["stage"] == stage:
            return
        if stage in GATED_STAGES:
            allowed, reasons = self.engagement_gate(engagement_id, rules)
            if not allowed:
                raise GateBlocked(
                    f"Cannot move to {stage}: the compliance checklist is not complete and no override reason is "
                    "written.",
                    reasons,
                )
        with self._connect() as connection:
            connection.execute("UPDATE engagements SET stage = ? WHERE id = ?", (stage, engagement_id))
            connection.execute(
                "INSERT INTO stage_log (engagement_id, from_stage, to_stage, at, note) VALUES (?, ?, ?, ?, ?)",
                (engagement_id, engagement["stage"], stage, _now(), note),
            )

    def stage_log(self, campaign_id: int) -> pd.DataFrame:
        return self._frame(
            """
            SELECT l.at, c.name AS creator_name, l.from_stage, l.to_stage, l.note
            FROM stage_log l JOIN engagements e ON e.id = l.engagement_id JOIN creators c ON c.id = e.creator_id
            WHERE e.campaign_id = ? ORDER BY l.at DESC, l.id DESC
            """,
            (campaign_id,),
        )

    # ── deliverables ─────────────────────────────────────────────────────────────────────────────
    def deliverables(self, campaign_id: int) -> pd.DataFrame:
        return self._frame(
            """
            SELECT d.*, e.creator_id, e.stage, c.name AS creator_name,
                   c.instagram, c.tiktok, c.youtube, c.snapchat
            FROM deliverables d
            JOIN engagements e ON e.id = d.engagement_id
            JOIN creators c ON c.id = e.creator_id
            WHERE e.campaign_id = ?
            ORDER BY c.name COLLATE NOCASE, d.due_date, d.id
            """,
            (campaign_id,),
        )

    def deliverable(self, deliverable_id: int) -> dict:
        row = self._row("SELECT * FROM deliverables WHERE id = ?", (deliverable_id,))
        if row is None:
            raise DataProblem("That deliverable no longer exists.")
        return row

    def _deliverable_values(self, data: dict) -> dict:
        values = {field: _clean_text(data.get(field)) for field in DELIVERABLE_FIELDS}
        values["platform"] = values["platform"].lower()
        values["format"] = values["format"].lower()
        if values["platform"] not in PLATFORMS:
            raise DataProblem(f"Platform must be one of: {', '.join(PLATFORMS)}.")
        if values["format"] not in FORMATS:
            raise DataProblem(f"Format must be one of: {', '.join(FORMATS)}.")
        values["fee_nok"] = _clean_number(data.get("fee_nok"))
        values["shows_person"] = int(bool(data.get("shows_person", True)))
        return values

    def tracked_url_for(self, engagement_id: int, platform: str) -> str:
        """Build the tracked link for a creator in a campaign; empty if the campaign has no landing page."""
        row = self._row(
            """
            SELECT k.slug, k.landing_url, c.name, c.instagram, c.tiktok, c.youtube, c.snapchat
            FROM engagements e JOIN campaigns k ON k.id = e.campaign_id JOIN creators c ON c.id = e.creator_id
            WHERE e.id = ?
            """,
            (engagement_id,),
        )
        if row is None:
            raise DataProblem("That pipeline card no longer exists.")
        if not row["landing_url"]:
            return ""
        handle = row.get(platform) or next((row[p] for p in PLATFORMS if row.get(p)), "")
        return build_tracked_url(row["landing_url"], platform, row["slug"], creator_token(handle, row["name"]))

    def add_deliverable(self, engagement_id: int, data: dict) -> int:
        values = self._deliverable_values(data)
        values["engagement_id"] = int(engagement_id)
        values["tracked_url"] = self.tracked_url_for(int(engagement_id), values["platform"])
        for column in RESULT_COLUMNS:
            values[column] = _clean_number(data.get(column))
        columns = ", ".join(values)
        marks = ", ".join("?" for _ in values)
        with self._connect() as connection:
            cursor = connection.execute(f"INSERT INTO deliverables ({columns}) VALUES ({marks})", tuple(values.values()))
            return int(cursor.lastrowid)

    def update_deliverable(self, deliverable_id: int, data: dict) -> None:
        current = self.deliverable(deliverable_id)
        values = self._deliverable_values({**current, **data})
        assignments = ", ".join(f"{column} = ?" for column in values)
        with self._connect() as connection:
            connection.execute(f"UPDATE deliverables SET {assignments} WHERE id = ?", (*values.values(), deliverable_id))

    def regenerate_tracked_url(self, deliverable_id: int) -> str:
        current = self.deliverable(deliverable_id)
        url = self.tracked_url_for(int(current["engagement_id"]), current["platform"])
        with self._connect() as connection:
            connection.execute("UPDATE deliverables SET tracked_url = ? WHERE id = ?", (url, deliverable_id))
        return url

    def delete_deliverable(self, deliverable_id: int) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM deliverables WHERE id = ?", (deliverable_id,))

    def set_results(self, deliverable_id: int, results: dict) -> None:
        values = {column: _clean_number(results.get(column)) for column in RESULT_COLUMNS if column in results}
        if not values:
            return
        assignments = ", ".join(f"{column} = ?" for column in values)
        with self._connect() as connection:
            connection.execute(f"UPDATE deliverables SET {assignments} WHERE id = ?", (*values.values(), deliverable_id))

    # ── checklist ────────────────────────────────────────────────────────────────────────────────
    def answers(self, deliverable_id: int) -> dict[str, str]:
        with self._connect() as connection:
            rows = connection.execute("SELECT rule_id, answer FROM checks WHERE deliverable_id = ?", (deliverable_id,))
            return {row["rule_id"]: row["answer"] for row in rows}

    def checks(self, campaign_id: int) -> pd.DataFrame:
        return self._frame(
            """
            SELECT k.deliverable_id, k.rule_id, k.answer, k.note, k.checked_at
            FROM checks k JOIN deliverables d ON d.id = k.deliverable_id JOIN engagements e ON e.id = d.engagement_id
            WHERE e.campaign_id = ? ORDER BY k.deliverable_id, k.rule_id
            """,
            (campaign_id,),
        )

    def set_answer(self, deliverable_id: int, rule_id: str, answer: str | None, note: str = "") -> None:
        with self._connect() as connection:
            if not answer:
                connection.execute("DELETE FROM checks WHERE deliverable_id = ? AND rule_id = ?", (deliverable_id, rule_id))
                return
            if answer not in ("yes", "no", "na"):
                raise DataProblem("Checklist answers are yes, no or na.")
            connection.execute(
                """
                INSERT INTO checks (deliverable_id, rule_id, answer, note, checked_at) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (deliverable_id, rule_id) DO UPDATE SET answer = excluded.answer, note = excluded.note,
                    checked_at = excluded.checked_at
                """,
                (deliverable_id, rule_id, answer, note, _now()),
            )

    def set_override(self, deliverable_id: int, reason: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE deliverables SET override_reason = ? WHERE id = ?", (_clean_text(reason), deliverable_id)
            )
