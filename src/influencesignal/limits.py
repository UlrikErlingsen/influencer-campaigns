"""Data limits: none when the app runs on your own computer; hard caps only in a public demo (``SIGNAL_PUBLIC=1``).

Signal suite contract (Signal Hub ``docs/APP_CONTRACT.md`` § 9): run locally — standalone, a local Signal Hub or an
internal company deployment — Influence Signal imposes no limit on file size, rows or columns; the computer's memory
is the limit, and running out of memory is reported as a plain message. A public demo server sets
``SIGNAL_PUBLIC=1`` (Signal Hub's public Docker image does), and then the caps below protect the shared server.
Every cap lives in this module, and the environment is read at call time.
"""

from __future__ import annotations

import os

from .errors import DataProblem

DEMO_MAX_UPLOAD_MB = 20
DEMO_MAX_EXPANDED_WORKBOOK_MB = 100
DEMO_MAX_TABLE_ROWS = 50_000
DEMO_MAX_TABLE_COLUMNS = 100
DEMO_NOTE = "This is a limit of the public demo; the downloaded app has no built-in limit."
OUT_OF_MEMORY = (
    "There is not enough memory on this computer for this file or step. Close other programs, or split the file "
    "and import it in parts."
)


def public_demo() -> bool:
    """True on a public demo server (``SIGNAL_PUBLIC=1``); independent of Signal Hub mode (``SIGNAL_HUB``)."""
    return os.environ.get("SIGNAL_PUBLIC") == "1"


def check_upload_bytes(size: int) -> None:
    if public_demo() and size > DEMO_MAX_UPLOAD_MB * 1024 * 1024:
        raise DataProblem(f"Uploads are limited to {DEMO_MAX_UPLOAD_MB} MB. {DEMO_NOTE}")


def check_workbook_expansion(expanded_bytes: int) -> None:
    if public_demo() and expanded_bytes > DEMO_MAX_EXPANDED_WORKBOOK_MB * 1024 * 1024:
        raise DataProblem(
            f"This workbook expands beyond {DEMO_MAX_EXPANDED_WORKBOOK_MB} MB. Remove unrelated sheets. {DEMO_NOTE}"
        )


def check_table_shape(rows: int, columns: int) -> None:
    if not public_demo():
        return
    if rows > DEMO_MAX_TABLE_ROWS:
        raise DataProblem(f"The table has {rows:,} rows, above the {DEMO_MAX_TABLE_ROWS:,}-row limit. {DEMO_NOTE}")
    if columns > DEMO_MAX_TABLE_COLUMNS:
        raise DataProblem(f"The table has {columns} columns, above the {DEMO_MAX_TABLE_COLUMNS}-column limit. {DEMO_NOTE}")
