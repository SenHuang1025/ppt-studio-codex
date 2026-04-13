from __future__ import annotations

from app.parsers.base import BaseParser, ParseResult
from app.parsers.csv_parser import CSVParser
from app.parsers.excel_parser import ExcelParser
from app.parsers.image_parser import ImageParser
from app.parsers.pdf_parser import PDFParser
from app.parsers.pptx_parser import PPTXParser
from app.parsers.text_parser import TextParser
from app.parsers.word_parser import WordParser


class UnsupportedParserError(ValueError):
    def __init__(self, file_type: str):
        super().__init__(f"Unsupported parser for file type '{file_type}'.")
        self.file_type = file_type


class ParserRegistry:
    def __init__(self) -> None:
        self._parsers: dict[str, BaseParser] = {
            "xlsx": ExcelParser(),
            "csv": CSVParser(),
            "docx": WordParser(),
            "pdf": PDFParser(),
            "pptx": PPTXParser(),
            "png": ImageParser(),
            "jpg": ImageParser(),
            "jpeg": ImageParser(),
            "txt": TextParser(),
            "md": TextParser(),
            "json": TextParser(),
        }

    def get_parser(self, file_type: str) -> BaseParser:
        normalized_file_type = file_type.strip().lower().lstrip(".")
        parser = self._parsers.get(normalized_file_type)
        if parser is None:
            raise UnsupportedParserError(normalized_file_type)
        return parser

    async def parse(self, file_type: str, file_path: str) -> ParseResult:
        parser = self.get_parser(file_type)
        return await parser.parse(file_path)


parser_registry = ParserRegistry()


def get_parser(file_type: str) -> BaseParser:
    return parser_registry.get_parser(file_type)


async def parse(file_type: str, file_path: str) -> ParseResult:
    return await parser_registry.parse(file_type, file_path)
