"""CSV/XLSX input with validation, and formula-injection-safe tabular output."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
import re
from typing import Callable
import zipfile

import defusedxml
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc

from .errors import DataProblem
from .metrics import RESULT_COLUMNS
from .utm import PLATFORMS

defusedxml.defuse_stdlib()

# Influence Signal is in the suite's data-heavy tier: the local upload cap is 1000 MB (``.streamlit/config.toml``,
# ``INFLUENCESIGNAL_MAX_UPLOAD_MB`` in the launchers, ``STREAMLIT_SERVER_MAX_UPLOAD_SIZE`` in Docker). The in-code
# limits below must never undercut it. Validation and import are vectorized, so post-level files with millions of
# rows stay practical; the screens show a preview of large tables instead of sending every row to the browser.
MAX_UPLOAD_MB = 1000
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
# Zip-bomb guard for XLSX: the old 5x ratio between expanded size and upload size, kept at the new cap.
MAX_EXPANDED_WORKBOOK_BYTES = 5 * MAX_UPLOAD_BYTES
MAX_TABLE_ROWS = 5_000_000
MAX_TABLE_COLUMNS = 100
MAX_PROBLEMS_SHOWN = 25
TEXT = pd.StringDtype("pyarrow")  # compact Arrow-backed text for uploaded cells
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


def _separator(payload: bytes) -> str:
    """Comma or semicolon, judged from the header line (without decoding the whole file)."""
    newline = payload.find(b"\n", 0, 1_000_000)
    first_line = payload[: newline if newline >= 0 else 1_000_000]
    return ";" if first_line.count(b";") > first_line.count(b",") else ","


def read_table(filename: str, payload: bytes) -> pd.DataFrame:
    """Read an uploaded CSV (comma or semicolon) or XLSX with size limits.

    Cells are read as text into Arrow-backed strings (a fraction of the memory of Python string objects), straight from
    the uploaded bytes without a decoded copy of the whole file.
    """
    suffix = Path(filename).suffix.lower()
    if not payload:
        raise DataProblem("This file is empty.")
    if len(payload) > MAX_UPLOAD_BYTES:
        raise DataProblem(f"Uploads are limited to {MAX_UPLOAD_MB:,} MB.")
    try:
        if suffix == ".csv":
            frame = pd.read_csv(
                BytesIO(payload),
                sep=_separator(payload),
                dtype=TEXT,
                keep_default_na=False,
                encoding="utf-8-sig",
                encoding_errors="replace",
            )
        elif suffix == ".xlsx":
            with zipfile.ZipFile(BytesIO(payload)) as workbook_zip:
                expanded = sum(member.file_size for member in workbook_zip.infolist())
            if expanded > MAX_EXPANDED_WORKBOOK_BYTES:
                raise DataProblem(
                    f"This workbook expands beyond {MAX_EXPANDED_WORKBOOK_BYTES // (1024 * 1024):,} MB. "
                    "Remove unrelated sheets, or save the sheet as CSV (much faster for large files)."
                )
            frame = pd.read_excel(BytesIO(payload), sheet_name=0, dtype=str).fillna("").astype(TEXT)
        else:
            raise DataProblem("Upload a CSV or XLSX file.")
    except DataProblem:
        raise
    except Exception as exc:  # pragma: no cover - parser messages differ by dependency version
        raise DataProblem(f"Could not read {filename}: {exc}") from exc
    if len(frame) > MAX_TABLE_ROWS:
        raise DataProblem(
            f"The table has {len(frame):,} rows, above the {MAX_TABLE_ROWS:,}-row limit. "
            "Split the file and import it in parts."
        )
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


def _text_column(frame: pd.DataFrame, column: str) -> pd.Series:
    """One column as stripped Arrow text; a missing column, NaN and the text 'nan' all become ''."""
    if column not in frame.columns:
        return pd.Series("", index=frame.index, dtype=TEXT)
    series = frame[column].astype(TEXT).fillna("").str.strip()
    return series.mask(series.str.lower() == "nan", "")


def _cast_floats(text: pd.Series) -> pd.Series | None:
    """Arrow casts a whole text column (null = blank) to floats at once; None when any cell is not a plain number."""
    try:
        cast = pc.cast(pa.array(text), pa.float64())
    except (pa.ArrowInvalid, pa.ArrowNotImplementedError):
        return None
    return pd.Series(cast.to_numpy(zero_copy_only=False), index=text.index, dtype="float64")


def _parse_numbers(text: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Vectorized ``_parse_number``: returns (float values with NaN for blank or bad, mask of bad non-blank cells).

    Plain numbers take one Arrow cast; only columns with Norwegian formatting (spaces, decimal commas, %, NOK/kr)
    go through the clean-up steps, and only unparseable leftovers fall back to Python objects.
    """
    text = text.astype(TEXT).fillna("").str.strip()
    blank = text.eq("") | text.str.lower().isin(["nan", "none"])
    values = _cast_floats(text.mask(blank, None))
    if values is None:
        cleaned = text.str.replace("[\u00a0 %]", "", regex=True).str.replace(r"(?i)^(?:nok|kr)\.?", "", regex=True)
        decimal_comma = cleaned.str.contains(",", regex=False) & ~cleaned.str.contains(".", regex=False)
        cleaned = cleaned.where(~decimal_comma, cleaned.str.replace(",", ".", regex=False))
        cleaned = cleaned.where(decimal_comma, cleaned.str.replace(",", "", regex=False))
        values = _cast_floats(cleaned.mask(blank, None))
        if values is None:
            values = pd.to_numeric(cleaned.mask(blank, "").astype(object), errors="coerce").astype("float64")
    bad = values.isna() & ~blank
    return values.where(~blank), bad


class _Problems:
    """Collects blocking problems with spreadsheet row numbers, keeping only the first few per check."""

    def __init__(self) -> None:
        self.items: list[tuple[int, int, str]] = []
        self.total = 0

    def rows(self, mask: pd.Series, message: Callable[[int, int], str]) -> None:
        """Add one problem per True row in ``mask``; ``message(line, position)`` formats it."""
        positions = np.flatnonzero(np.asarray(mask, dtype=bool))
        self.total += len(positions)
        for position in positions[:MAX_PROBLEMS_SHOWN]:
            line = int(position) + 2  # header is line 1
            self.items.append((line, len(self.items), message(line, int(position))))

    def add(self, message: str) -> None:
        self.total += 1
        self.items.append((10**12, len(self.items), message))  # file-level problems after row problems

    def raise_if_any(self, title: str) -> None:
        if not self.total:
            return
        shown = [message for _, _, message in sorted(self.items)[:MAX_PROBLEMS_SHOWN]]
        more = f" …and {self.total - len(shown):,} more." if self.total > len(shown) else ""
        raise DataProblem(title + "\n- " + "\n- ".join(shown) + more)


def _relabel(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Normalized column names and a 0..n-1 index without copying the cell data (uploads can be huge)."""
    frame = frame.copy(deep=False)
    frame.columns = columns
    if not isinstance(frame.index, pd.RangeIndex) or frame.index.start != 0 or frame.index.step != 1:
        frame.index = pd.RangeIndex(len(frame))
    return frame


def casefold_text(values: pd.Series) -> pd.Series:
    """``str.casefold`` for a text column without turning every cell into a Python string.

    ASCII cells are lower-cased in Arrow; only non-ASCII cells (æ, ø, å, ß …) take the exact Python casefold.
    """
    text = values.astype(TEXT).fillna("")
    folded = text.str.lower()
    special = text.str.contains(r"[^\x00-\x7f]", regex=True)
    if special.any():
        folded = folded.mask(special, text[special].astype(object).str.casefold().astype(TEXT))
    return folded


def _duplicates(values: pd.Series) -> list[str]:
    folded = casefold_text(values)
    return sorted(set(folded[folded.duplicated() & folded.ne("")]))


def validate_creators(frame: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Validate a creator roster table. Returns cleaned rows and non-blocking warnings.

    Raises DataProblem listing every blocking problem with its spreadsheet row number. Checks run column by column
    (vectorized), so rosters with millions of rows validate in seconds.
    """
    if frame.empty:
        raise DataProblem("The creator file has no rows.")
    columns = [str(column).strip().lower().replace(" ", "_") for column in frame.columns]
    frame = _relabel(frame, columns)
    if "name" not in columns:
        raise DataProblem("The creator file needs a 'name' column. Download the template to see every column.")
    warnings = []
    unknown = [column for column in columns if column not in CREATOR_COLUMNS]
    if unknown:
        warnings.append("Ignored unknown columns: " + ", ".join(unknown))

    problems = _Problems()
    clean = pd.DataFrame(index=frame.index)
    for column in CREATOR_COLUMNS:
        clean[column] = _text_column(frame, column)
    problems.rows(clean["name"].eq(""), lambda line, _: f"Row {line}: name is required.")
    for platform in PLATFORMS:
        original = clean[platform]
        handles = original.str.lstrip("@").str.strip()
        bad = handles.ne("") & ~handles.str.fullmatch(_HANDLE.pattern.strip("^$"))
        problems.rows(
            bad,
            lambda line, position, platform=platform, original=original: (
                f"Row {line}: {platform} handle '{original.iat[position]}' has characters a handle cannot have."
            ),
        )
        clean[platform] = handles

    raw_followers = clean["followers"]
    followers, bad = _parse_numbers(raw_followers)
    problems.rows(bad, lambda line, position: f"Row {line}: followers '{raw_followers.iat[position]}' is not a number.")
    wrong = followers.notna() & ((followers < 0) | (followers != np.floor(followers)))
    problems.rows(wrong, lambda line, _: f"Row {line}: followers must be a whole number of zero or more.")
    clean["followers"] = np.floor(followers.where(followers >= 0))

    raw_rate = clean["engagement_rate"]
    rate, bad = _parse_numbers(raw_rate)
    problems.rows(bad, lambda line, position: f"Row {line}: engagement_rate '{raw_rate.iat[position]}' is not a number.")
    problems.rows(
        rate.notna() & ~rate.between(0, 100),
        lambda line, _: f"Row {line}: engagement_rate is a percentage and must be between 0 and 100.",
    )
    clean["engagement_rate"] = rate

    region = clean["region"]
    if region.ne("").any():
        fylke_lookup = {fylke.casefold(): fylke for fylke in FYLKER}
        codes, uniques = pd.factorize(region)  # a handful of distinct regions, however many rows
        canonical = np.array([fylke_lookup.get(str(value).casefold()) for value in uniques] + [None], dtype=object)
        matched = pd.Series(canonical[codes], index=region.index)
        problems.rows(
            region.ne("") & matched.isna(),
            lambda line, position: (
                f"Row {line}: region '{region.iat[position]}' is not one of Norway's 15 counties (from 2024): "
                + ", ".join(FYLKER)
                + "."
            ),
        )
        clean["region"] = matched.fillna(region.astype(object)).astype(TEXT)

    email = clean["contact_email"]
    problems.rows(
        email.ne("") & ~email.str.fullmatch(_EMAIL.pattern.strip("^$")),
        lambda line, position: f"Row {line}: contact_email '{email.iat[position]}' does not look like an e-mail address.",
    )
    clean["niche_tags"] = clean["niche_tags"].str.lower().str.replace(r"\s*,[\s,]*", ", ", regex=True).str.strip(", \t")
    no_handle = clean["name"].ne("")
    for platform in PLATFORMS:
        no_handle &= clean[platform].eq("")
    missing = np.flatnonzero(no_handle.to_numpy(dtype=bool))
    for position in missing[:MAX_PROBLEMS_SHOWN]:
        name = clean["name"].iat[position]
        warnings.append(f"Row {position + 2}: {name} has no platform handle; tracked links will use the name.")
    if len(missing) > MAX_PROBLEMS_SHOWN:
        warnings.append(f"…and {len(missing) - MAX_PROBLEMS_SHOWN:,} more rows have no platform handle.")

    for name in _duplicates(clean["name"]):
        problems.add(f"Name '{name}' appears more than once in the file.")
    for platform in PLATFORMS:
        for handle in _duplicates(clean[platform]):
            problems.add(f"{platform} handle '{handle}' appears more than once in the file.")
    problems.raise_if_any("The creator file was not imported:")
    return clean, warnings


def validate_results(frame: pd.DataFrame, known_ids: set[int]) -> pd.DataFrame:
    """Validate a results table keyed by deliverable_id. Blank cells stay blank (not reported)."""
    if frame.empty:
        raise DataProblem("The results file has no rows.")
    columns = [str(column).strip().lower().replace(" ", "_") for column in frame.columns]
    frame = _relabel(frame, columns)
    if "deliverable_id" not in frame.columns:
        raise DataProblem("The results file needs a 'deliverable_id' column. Download the template from this page.")
    present = [column for column in RESULT_COLUMNS if column in frame.columns]
    if not present:
        raise DataProblem("The results file needs at least one of: " + ", ".join(RESULT_COLUMNS) + ".")
    problems = _Problems()
    raw_ids = _text_column(frame, "deliverable_id")
    parsed_ids, _ = _parse_numbers(raw_ids)
    ids = np.trunc(parsed_ids.where(parsed_ids.notna() & parsed_ids.ne(0), -1)).astype("int64")
    known = ids.isin(list(known_ids))
    problems.rows(
        ~known,
        lambda line, position: f"Row {line}: deliverable_id '{raw_ids.iat[position]}' is not a deliverable in this campaign.",
    )
    clean = pd.DataFrame({"deliverable_id": ids})
    for column in present:
        raw = _text_column(frame, column)
        values, bad = _parse_numbers(raw)
        problems.rows(
            bad & known,
            lambda line, position, column=column, raw=raw: f"Row {line}: {column} '{raw.iat[position]}' is not a number.",
        )
        problems.rows(values.lt(0) & known, lambda line, _, column=column: f"Row {line}: {column} cannot be negative.")
        clean[column] = values
    clean = clean[known.to_numpy()].reset_index(drop=True)
    duplicated = sorted(set(clean.loc[clean["deliverable_id"].duplicated(), "deliverable_id"].tolist()))
    if duplicated:
        listed = ", ".join(map(str, duplicated[:MAX_PROBLEMS_SHOWN]))
        more = f" …and {len(duplicated) - MAX_PROBLEMS_SHOWN:,} more" if len(duplicated) > MAX_PROBLEMS_SHOWN else ""
        problems.add("These deliverable_ids appear more than once: " + listed + more)
    problems.raise_if_any("The results file was not imported:")
    return clean


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
