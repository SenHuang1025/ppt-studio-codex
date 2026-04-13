from __future__ import annotations

import pytest

from app.parsers import UnsupportedParserError, get_parser, parser_registry
from tests.sample_files import (
    write_csv_file,
    write_docx_file,
    write_excel_file,
    write_image_file,
    write_json_file,
    write_pdf_file,
    write_pptx_file,
    write_text_file,
)


def test_parser_registry_selects_by_extension() -> None:
    assert get_parser("xlsx").__class__.__name__ == "ExcelParser"
    assert get_parser("csv").__class__.__name__ == "CSVParser"
    assert get_parser("docx").__class__.__name__ == "WordParser"
    assert get_parser("pdf").__class__.__name__ == "PDFParser"
    assert get_parser("pptx").__class__.__name__ == "PPTXParser"
    assert get_parser("png").__class__.__name__ == "ImageParser"
    assert get_parser("txt").__class__.__name__ == "TextParser"

    with pytest.raises(UnsupportedParserError):
        get_parser("exe")


@pytest.mark.asyncio
async def test_text_family_parsers_smoke(tmp_path) -> None:
    txt_path = write_text_file(tmp_path / "notes.txt", "Line one\nLine two\nLine three")
    md_path = write_text_file(tmp_path / "notes.md", "# Title\n\n- Bullet one\n- Bullet two")
    json_path = write_json_file(tmp_path / "data.json", {"title": "Q1", "metrics": {"revenue": 360}})

    txt_result = await parser_registry.parse("txt", str(txt_path))
    md_result = await parser_registry.parse("md", str(md_path))
    json_result = await parser_registry.parse("json", str(json_path))

    assert txt_result.summary.startswith("Text document")
    assert txt_result.text_content.startswith("Line one")
    assert md_result.structured_data["headings"] == ["Title"]
    assert "  \"title\": \"Q1\"" in json_result.text_content
    assert json_result.structured_data["top_level_keys"] == ["title", "metrics"]


@pytest.mark.asyncio
async def test_csv_and_excel_parsers_smoke(tmp_path) -> None:
    csv_path = write_csv_file(tmp_path / "data.csv")
    excel_path = write_excel_file(tmp_path / "data.xlsx")

    csv_result = await parser_registry.parse("csv", str(csv_path))
    excel_result = await parser_registry.parse("xlsx", str(excel_path))

    assert csv_result.structured_data["row_count"] == 3
    assert "Revenue" in csv_result.structured_data["numeric_statistics"]
    assert excel_result.structured_data["sheet_count"] == 2
    assert excel_result.structured_data["sheets"][0]["headers"] == ["Month", "Revenue", "Cost"]


@pytest.mark.asyncio
async def test_docx_pdf_pptx_and_image_parsers_smoke(tmp_path) -> None:
    docx_path = write_docx_file(tmp_path / "sample.docx")
    pdf_path = write_pdf_file(tmp_path / "sample.pdf")
    pptx_path = write_pptx_file(tmp_path / "sample.pptx")
    image_path = write_image_file(tmp_path / "sample.png")

    docx_result = await parser_registry.parse("docx", str(docx_path))
    pdf_result = await parser_registry.parse("pdf", str(pdf_path))
    pptx_result = await parser_registry.parse("pptx", str(pptx_path))
    image_result = await parser_registry.parse("png", str(image_path))

    assert docx_result.structured_data["heading_count"] == 1
    assert docx_result.structured_data["table_count"] == 1
    assert pdf_result.structured_data["page_count"] == 1
    assert pdf_result.text_content.startswith("Page 1")
    assert pptx_result.structured_data["slide_count"] == 1
    assert pptx_result.structured_data["slides"][0]["has_title"] is True
    assert image_result.structured_data["width"] == 320
    assert image_result.structured_data["description_source"] == "metadata_only"
