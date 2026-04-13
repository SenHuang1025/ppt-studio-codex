from __future__ import annotations

import asyncio
import io
from pathlib import Path

import pandas as pd
from pandas.errors import EmptyDataError

from app.parsers.base import BaseParser, ParseResult
from app.parsers.utils import (
    dataframe_column_info,
    dataframe_numeric_statistics,
    dataframe_preview,
    dataframe_text_preview,
    decode_bytes,
    identify_chart_candidates,
    normalize_file_type,
    unique_strings,
)


class CSVParser(BaseParser):
    async def parse(self, file_path: str) -> ParseResult:
        return await asyncio.to_thread(self._parse_sync, file_path)

    def _parse_sync(self, file_path: str) -> ParseResult:
        raw_bytes = Path(file_path).read_bytes()
        decoded_text, encoding = decode_bytes(raw_bytes)

        try:
            dataframe = pd.read_csv(io.StringIO(decoded_text))
        except EmptyDataError:
            return ParseResult(
                file_type=normalize_file_type(file_path),
                summary="CSV file is empty.",
                text_content="",
                structured_data={
                    "encoding": encoding,
                    "row_count": 0,
                    "column_count": 0,
                    "columns": [],
                    "preview_rows": [],
                    "numeric_statistics": {},
                    "chart_candidates": [],
                },
                key_points=["CSV file is empty"],
            )

        dataframe.columns = [str(column_name) for column_name in dataframe.columns]
        row_count, column_count = dataframe.shape
        numeric_statistics = dataframe_numeric_statistics(dataframe)
        chart_candidates = identify_chart_candidates(dataframe)
        columns = dataframe_column_info(dataframe)
        key_points = unique_strings(
            [
                f"Columns: {', '.join(dataframe.columns[:5])}" if column_count else "",
                f"Numeric columns: {', '.join(list(numeric_statistics.keys())[:4])}" if numeric_statistics else "",
                f"Chart candidates: {', '.join([candidate['y'] for candidate in chart_candidates[:3]])}"
                if chart_candidates
                else "",
            ],
            max_items=5,
        )

        return ParseResult(
            file_type=normalize_file_type(file_path),
            summary=f"CSV file with {row_count} rows and {column_count} columns.",
            text_content="\n".join(
                [
                    f"Columns: {', '.join(dataframe.columns)}" if column_count else "No columns detected.",
                    dataframe_text_preview(dataframe),
                ]
            ),
            structured_data={
                "encoding": encoding,
                "row_count": int(row_count),
                "column_count": int(column_count),
                "columns": columns,
                "preview_rows": dataframe_preview(dataframe),
                "numeric_statistics": numeric_statistics,
                "chart_candidates": chart_candidates,
            },
            key_points=key_points,
        )
