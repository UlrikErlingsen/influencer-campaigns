"""CSV/XLSX input with validation, and formula-injection-safe tabular output."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
import re
import zipfile

import defusedxml
import pandas as pd

from .errors import DataProblem
from .metrics import RESULT_COLUMNS
from .utm import PLATFORMS

defusedxml.defuse_stdlib()

MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_EXPANDED_WORKBOOK_BYTES = 100 * 1024 * 1024
MAX_TABLE_ROWS = 50_000
MAX_TABLE_COLUMNS = 100
_ILLEGAL_XML = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_HANDLE = re.compile(r"^[A-Za-z0-9._-]{1,60}$")
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Norway's 15 counties (fylker) from 1 January 2024.
FYLKER = (
    "Agder",
    "Akershus",
    "Buskerud",
    "Finnmark",
    "Innlandet",
    "Møre og Romsdal",
    "Nordland",
    "Oslo",
    "Rogaland",
    "Telemark",
    "Troms",
    "Trøndelag",
    "Vestfold",
    "Vestland",
    "Østfold",
)

CREATOR_COLUMNS = (
    "name",
    *PLATFORMS,
    "followers",
    "engagement_rate",
    "niche_tags",
    "region",
    "contact_email",
    "contact_phone",
    "rate_card",
    "notes",
)
RESULT_IMPORT_COLUMNS = ("deliverable_id", *RESULT_COLUMNS)


def _safe_cell(value: object) -> object:
    if isinstance(value, str):
        cleaned = _ILLEGAL_XML.sub("", value)
        if cleaned.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")):
            return "'" + cleaned
        return cleaned
    return value


def safe_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Neutralize spreadsheet formulas in text cells and column headers."""
    result = frame.copy()
    for column in result.select_dtypes(include=["object", "string"]).columns:
        result[column] = result[column].map(_safe_cell)
    result.columns = [_safe_cell(str(column)) for column in result.columns]
    return result


def dataframe_csv_bytes(frame: pd.DataFrame) -> bytes:
    # utf-8-sig so Excel opens æ, ø and å correctly.
    return safe_frame(frame).to_csv(index=False).encode("utf-8-sig")


def read_table(filename: str, payload: bytes) -> pd.DataFrame:
    """Read an uploaded CSV (comma or semicolon) or XLSX with size limits."""
    suffix = Path(filename).suffix.lower()
    if not payload:
        raise DataProblem("This file is empty.")
    if len(payload) > MAX_UPLOAD_BYTES:
        raise DataProblem("Uploads are limited to 20 MB.")
    try:
        if suffix == ".csv":
            text = payload.decode("utf-8-sig", errors="replace")
            first_line = text.splitlines()[0] if text else ""
            separator = ";" if first_line.count(";") > first_line.count(",") else ","
            frame = pd.read_csv(BytesIO(text.encode("utf-8")), sep=separator, dtype=str, keep_default_na=False)
        elif suffix == ".xlsx":
            with zipfile.ZipFile(BytesIO(payload)) as workbook_zip:
                expanded = sum(member.file_size for member in workbook_zip.infolist())
            if expanded > MAX_EXPANDED_WORKBOOK_BYTES:
                raise DataProblem("This workbook expands beyond 100 MB. Remove unrelated sheets before upload.")
            frame = pd.read_excel(BytesIO(payload), sheet_name=0, dtype=str).fillna("")
        else:
            raise DataProblem("Upload a CSV or XLSX file.")
    except DataProblem:
        raise
    except Exception as exc:  # pragma: no cover - parser messages differ by dependency version
        raise DataProblem(f"Could not read {filename}: {exc}") from exc
    if len(frame) > MAX_TABLE_ROWS:
        raise DataProblem(f"The table exceeds the {MAX_TABLE_ROWS:,}-row safety limit.")
    if len(frame.columns) > MAX_TABLE_COLUMNS:
        raise DataProblem(f"The table exceeds the {MAX_TABLE_COLUMNS}-column safety limit.")
    frame.columns = [str(column).strip().lower().replace(" ", "_") for column in frame.columns]
    return frame


def _parse_number(raw: object) -> float | None:
    """Accept '12 500', '12,5', '4.2%', 'NOK 3 000'; return None for blank."""
    text = str(raw if raw is not None else "").strip()
    if not text or text.lower() in ("nan", "none"):
        return None
    text = text.replace(" ", "").replace(" ", "").replace("%", "")
    text = re.sub(r"(?i)^(nok|kr)\.?", "", text)
    if "," in text and "." not in text:
        text = text.replace(",", ".")
    else:
        text = text.replace(",", "")
    return float(text)


def _clean_text(raw: object) -> str:
    text = "" if raw is None else str(raw)
    return "" if text.strip().lower() == "nan" else text.strip()


def validate_creators(frame: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Validate a creator roster table. Returns cleaned rows and non-blocking warnings.

    Raises DataProblem listing every blocking problem with its spreadsheet row number.
    """
    if frame.empty:
        raise DataProblem("The creator file has no rows.")
    columns = [str(column).strip().lower().replace(" ", "_") for column in frame.columns]
    frame = frame.copy()
    frame.columns = columns
    if "name" not in columns:
        raise DataProblem("The creator file needs a 'name' column. Download the template to see every column.")
    warnings = []
    unknown = [column for column in columns if column not in CREATOR_COLUMNS]
    if unknown:
        warnings.append("Ignored unknown columns: " + ", ".join(unknown))

    fylke_lookup = {fylke.casefold(): fylke for fylke in FYLKER}
    problems: list[str] = []
    rows = []
    for position, raw in enumerate(frame.to_dict("records")):
        line = position + 2  # header is line 1
        row = {column: _clean_text(raw.get(column)) for column in CREATOR_COLUMNS}
        if not row["name"]:
            problems.append(f"Row {line}: name is required.")
        for platform in PLATFORMS:
            handle = row[platform].lstrip("@").strip()
            if handle and not _HANDLE.match(handle):
                problems.append(f"Row {line}: {platform} handle '{row[platform]}' has characters a handle cannot have.")
            row[platform] = handle
        try:
            followers = _parse_number(row["followers"])
        except ValueError:
            problems.append(f"Row {line}: followers '{row['followers']}' is not a number.")
            followers = None
        if followers is not None and (followers < 0 or followers != int(followers)):
            problems.append(f"Row {line}: followers must be a whole number of zero or more.")
        row["followers"] = int(followers) if followers is not None and followers >= 0 else None
        try:
            rate = _parse_number(row["engagement_rate"])
        except ValueError:
            problems.append(f"Row {line}: engagement_rate '{row['engagement_rate']}' is not a number.")
            rate = None
        if rate is not None and not 0 <= rate <= 100:
            problems.append(f"Row {line}: engagement_rate is a percentage and must be between 0 and 100.")
        row["engagement_rate"] = rate
        if row["region"]:
            match = fylke_lookup.get(row["region"].casefold())
            if match is None:
                problems.append(
                    f"Row {line}: region '{row['region']}' is not one of Norway's 15 counties (from 2024): "
                    + ", ".join(FYLKER)
                    + "."
                )
            row["region"] = match or row["region"]
        if row["contact_email"] and not _EMAIL.match(row["contact_email"]):
            problems.append(f"Row {line}: contact_email '{row['contact_email']}' does not look like an e-mail address.")
        row["niche_tags"] = ", ".join(tag.strip().lower() for tag in row["niche_tags"].split(",") if tag.strip())
        if not any(row[platform] for platform in PLATFORMS) and row["name"]:
            warnings.append(f"Row {line}: {row['name']} has no platform handle; tracked links will use the name.")
        rows.append(row)

    clean = pd.DataFrame(rows, columns=list(CREATOR_COLUMNS))
    names = clean["name"].str.casefold()
    for name in sorted(set(names[names.duplicated() & names.ne("")])):
        problems.append(f"Name '{name}' appears more than once in the file.")
    for platform in PLATFORMS:
        handles = clean[platform].str.casefold()
        for handle in sorted(set(handles[handles.duplicated() & handles.ne("")])):
            problems.append(f"{platform} handle '{handle}' appears more than once in the file.")
    if problems:
        shown = problems[:25]
        more = f" …and {len(problems) - 25} more." if len(problems) > 25 else ""
        raise DataProblem("The creator file was not imported:\n- " + "\n- ".join(shown) + more)
    return clean, warnings


def validate_results(frame: pd.DataFrame, known_ids: set[int]) -> pd.DataFrame:
    """Validate a results table keyed by deliverable_id. Blank cells stay blank (not reported)."""
    if frame.empty:
        raise DataProblem("The results file has no rows.")
    frame = frame.copy()
    frame.columns = [str(column).strip().lower().replace(" ", "_") for column in frame.columns]
    if "deliverable_id" not in frame.columns:
        raise DataProblem("The results file needs a 'deliverable_id' column. Download the template from this page.")
    present = [column for column in RESULT_COLUMNS if column in frame.columns]
    if not present:
        raise DataProblem("The results file needs at least one of: " + ", ".join(RESULT_COLUMNS) + ".")
    problems = []
    rows = []
    for position, raw in enumerate(frame.to_dict("records")):
        line = position + 2
        try:
            deliverable_id = int(_parse_number(raw.get("deliverable_id")) or -1)
        except ValueError:
            deliverable_id = -1
        if deliverable_id not in known_ids:
            problems.append(f"Row {line}: deliverable_id '{raw.get('deliverable_id')}' is not a deliverable in this campaign.")
            continue
        row: dict[str, object] = {"deliverable_id": deliverable_id}
        for column in present:
            try:
                value = _parse_number(raw.get(column))
            except ValueError:
                problems.append(f"Row {line}: {column} '{raw.get(column)}' is not a number.")
                continue
            if value is not None and value < 0:
                problems.append(f"Row {line}: {column} cannot be negative.")
            row[column] = value
        rows.append(row)
    ids = [row["deliverable_id"] for row in rows]
    duplicated = sorted({value for value in ids if ids.count(value) > 1})
    if duplicated:
        problems.append("These deliverable_ids appear more than once: " + ", ".join(map(str, duplicated)))
    if problems:
        raise DataProblem("The results file was not imported:\n- " + "\n- ".join(problems[:25]))
    return pd.DataFrame(rows)


def creator_template() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "name": "Eksempel Skaper",
                "instagram": "demo_eksempel",
                "tiktok": "",
                "youtube": "",
                "snapchat": "",
                "followers": 12000,
                "engagement_rate": 3.4,
                "niche_tags": "trening, friluft",
                "region": "Vestland",
                "contact_email": "skaper@example.com",
                "contact_phone": "",
                "rate_card": "Reel 5 000 NOK; story 2 000 NOK",
                "notes": "Fictional example row — replace it.",
            }
        ],
        columns=list(CREATOR_COLUMNS),
    )
