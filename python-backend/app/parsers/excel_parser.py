from __future__ import annotations

import asyncio

import pandas as pd

from app.parsers.base import BaseParser, ParseResult
from app.parsers.utils import (
    dataframe_column_info,
    dataframe_numeric_statistics,
    dataframe_preview,
    dataframe_text_preview,
    identify_chart_candidates,
    normalize_file_type,
    unique_strings,
)


class ExcelParser(BaseParser):
    async def parse(self, file_path: str) -> ParseResult:
        return await asyncio.to_thread(self._parse_sync, file_path)

    def _parse_sync(self, file_path: str) -> ParseResult:
        workbook = pd.read_excel(file_path, sheet_name=None, engine="openpyxl")
        sheet_summaries: list[dict[str, object]] = []
        text_sections: list[str] = []
        key_points: list[str] = []
        total_rows = 0

        for sheet_name, dataframe in workbook.items():
            dataframe.columns = [str(column_name) for column_name in dataframe.columns]
            row_count, column_count = dataframe.shape
            total_rows += int(row_count)
            numeric_statistics = dataframe_numeric_statistics(dataframe)
            chart_candidates = identify_chart_candidates(dataframe)
            sheet_summaries.append(
                {
                    "sheet_name": sheet_name,
                    "row_count": int(row_count),
                    "column_count": int(column_count),
                    "headers": [str(column_name) for column_name in dataframe.columns.tolist()],
                    "columns": dataframe_column_info(dataframe),
                    "preview_rows": dataframe_preview(dataframe),
                    "numeric_statistics": numeric_statistics,
                    "chart_candidates": chart_candidates,
                }
            )
            text_sections.append(
                "\n".join(
                    [
                        f"Sheet: {sheet_name}",
                        f"Columns: {', '.join(dataframe.columns)}" if column_count else "No columns detected.",
                        dataframe_text_preview(dataframe),
                    ]
                )
            )
            key_points.extend(
                [
                    f"{sheet_name}: {row_count} rows x {column_count} columns",
                    f"{sheet_name}: numeric columns {', '.join(list(numeric_statistics.keys())[:4])}"
                    if numeric_statistics
                    else "",
                ]
            )

        return ParseResult(
            file_type=normalize_file_type(file_path),
            summary=f"Excel workbook with {len(sheet_summaries)} sheets and {total_rows} total data rows.",
            text_content="\n\n".join(text_sections),
            structured_data={
                "sheet_count": len(sheet_summaries),
                "total_rows": total_rows,
                "sheets": sheet_summaries,
            },
            key_points=unique_strings(key_points, max_items=5),
        )
