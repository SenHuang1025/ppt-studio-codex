from __future__ import annotations

import math
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd
from pandas.api.types import is_numeric_dtype

DEFAULT_TEXT_ENCODINGS: tuple[str, ...] = ("utf-8-sig", "utf-8", "gb18030", "latin-1")
DATE_LIKE_PATTERN = re.compile(r"^\d{1,4}([-/\.]\d{1,2}){1,2}$")
MONTH_LIKE_PATTERN = re.compile(r"^(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*$", re.IGNORECASE)


def normalize_file_type(file_path: str) -> str:
    return Path(file_path).suffix.strip().lower().lstrip(".")


def truncate_text(text: str, limit: int = 400) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: max(limit - 3, 0)].rstrip()}..."


def non_empty_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def unique_strings(items: list[str], *, max_items: int = 5, max_length: int = 180) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()

    for item in items:
        normalized = truncate_text(item.strip(), max_length)
        if not normalized or normalized in seen:
            continue
        result.append(normalized)
        seen.add(normalized)
        if len(result) >= max_items:
            break

    return result


def summarize_text(
    text: str,
    *,
    prefix: str | None = None,
    max_lines: int = 3,
    max_chars: int = 280,
) -> str:
    lines = non_empty_lines(text)
    if not lines:
        return prefix or "No readable text extracted."

    summary_body = truncate_text(" ".join(lines[:max_lines]), max_chars)
    if not prefix:
        return summary_body
    return f"{prefix} {summary_body}".strip()


def extract_key_points(text: str, *, max_items: int = 5) -> list[str]:
    lines = non_empty_lines(text)
    prioritized = [
        line
        for line in lines
        if line.startswith(("#", "-", "*", "•")) or line[:2].isdigit()
    ]
    return unique_strings(prioritized + lines, max_items=max_items)


def decode_bytes(raw_bytes: bytes, encodings: tuple[str, ...] = DEFAULT_TEXT_ENCODINGS) -> tuple[str, str]:
    for encoding in encodings:
        try:
            return raw_bytes.decode(encoding), encoding
        except UnicodeDecodeError:
            continue

    return raw_bytes.decode("utf-8", errors="replace"), "utf-8-replace"


def to_jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value

    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [to_jsonable(item) for item in value]

    item_method = getattr(value, "item", None)
    if callable(item_method):
        try:
            return to_jsonable(item_method())
        except (TypeError, ValueError):
            pass

    return str(value)


def dataframe_preview(dataframe: pd.DataFrame, *, limit: int = 5) -> list[dict[str, Any]]:
    if dataframe.empty:
        return []

    preview_frame = dataframe.head(limit).copy()
    preview_frame = preview_frame.where(pd.notna(preview_frame), None)
    preview_rows = preview_frame.to_dict(orient="records")
    return [to_jsonable(row) for row in preview_rows]


def dataframe_text_preview(dataframe: pd.DataFrame, *, limit: int = 5) -> str:
    if dataframe.empty:
        return "No data rows."

    preview_frame = dataframe.head(limit).copy()
    preview_frame = preview_frame.where(pd.notna(preview_frame), "")
    return truncate_text(preview_frame.to_string(index=False), limit=800)


def dataframe_column_info(dataframe: pd.DataFrame, *, sample_limit: int = 3) -> list[dict[str, Any]]:
    column_info: list[dict[str, Any]] = []

    for column_name in dataframe.columns:
        series = dataframe[column_name]
        non_null = series.dropna()
        sample_values = [
            truncate_text(str(value), 120)
            for value in non_null.head(sample_limit).tolist()
        ]
        column_info.append(
            {
                "name": str(column_name),
                "dtype": str(series.dtype),
                "non_null_count": int(non_null.shape[0]),
                "unique_count": int(non_null.astype(str).nunique()) if not non_null.empty else 0,
                "sample_values": unique_strings(sample_values, max_items=sample_limit, max_length=120),
            }
        )

    return column_info


def dataframe_numeric_statistics(dataframe: pd.DataFrame) -> dict[str, dict[str, Any]]:
    statistics: dict[str, dict[str, Any]] = {}

    for column_name in dataframe.columns:
        series = dataframe[column_name]
        if not is_numeric_dtype(series):
            continue

        numeric_series = series.dropna()
        if numeric_series.empty:
            continue

        statistics[str(column_name)] = {
            "count": int(numeric_series.count()),
            "sum": to_jsonable(numeric_series.sum()),
            "mean": to_jsonable(numeric_series.mean()),
            "min": to_jsonable(numeric_series.min()),
            "max": to_jsonable(numeric_series.max()),
        }

    return statistics


def identify_chart_candidates(dataframe: pd.DataFrame, *, max_items: int = 8) -> list[dict[str, str]]:
    if dataframe.empty:
        return []

    numeric_columns = [str(column_name) for column_name in dataframe.columns if is_numeric_dtype(dataframe[column_name])]
    if not numeric_columns:
        return []

    category_columns: list[tuple[str, str]] = []
    total_rows = max(len(dataframe.index), 1)

    for column_name in dataframe.columns:
        column_key = str(column_name)
        if column_key in numeric_columns:
            continue

        series = dataframe[column_name].dropna()
        if series.empty:
            continue

        sample = series.head(20).astype(str)
        date_like_count = sum(
            1
            for value in sample
            if DATE_LIKE_PATTERN.match(value.strip()) or MONTH_LIKE_PATTERN.match(value.strip())
        )
        if date_like_count >= max(2, min(3, len(sample))):
            category_columns.append((column_key, "datetime"))
            continue

        unique_count = int(series.astype(str).nunique())
        if 1 < unique_count <= min(max(total_rows // 2, 2), 20):
            category_columns.append((column_key, "category"))

    candidates: list[dict[str, str]] = []
    for column_name, axis_kind in category_columns[:3]:
        for numeric_column in numeric_columns[:4]:
            candidates.append(
                {
                    "x": column_name,
                    "y": numeric_column,
                    "kind": axis_kind,
                    "reason": f"{axis_kind} field paired with numeric series",
                }
            )
            if len(candidates) >= max_items:
                return candidates

    if candidates:
        return candidates

    if len(numeric_columns) >= 2:
        baseline = numeric_columns[0]
        for numeric_column in numeric_columns[1:]:
            candidates.append(
                {
                    "x": baseline,
                    "y": numeric_column,
                    "kind": "numeric-comparison",
                    "reason": "compare two numeric series directly",
                }
            )
            if len(candidates) >= max_items:
                break

    return candidates


def describe_json_structure(value: Any, *, depth: int = 0, max_depth: int = 3, max_items: int = 5) -> dict[str, Any]:
    if depth >= max_depth:
        return {"type": type(value).__name__}

    if isinstance(value, dict):
        children = {
            str(key): describe_json_structure(item, depth=depth + 1, max_depth=max_depth, max_items=max_items)
            for key, item in list(value.items())[:max_items]
        }
        return {
            "type": "object",
            "size": len(value),
            "children": children,
        }

    if isinstance(value, list):
        return {
            "type": "array",
            "size": len(value),
            "sample": [
                describe_json_structure(item, depth=depth + 1, max_depth=max_depth, max_items=max_items)
                for item in value[:max_items]
            ],
        }

    return {
        "type": type(value).__name__,
        "example": truncate_text(str(to_jsonable(value)), 120),
    }
