"""Pluggable text extraction for the supported file types.

Each extractor takes a Django file field and returns (text, metadata). New
formats (audio transcription, video, HTML) slot in by registering here.
"""
from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass, field
from typing import Callable

logger = logging.getLogger("neuraforge")


@dataclass
class ExtractionResult:
    text: str
    page_count: int = 0
    metadata: dict = field(default_factory=dict)


def _extract_pdf(fileobj) -> ExtractionResult:
    from pypdf import PdfReader

    reader = PdfReader(fileobj)
    pages = [page.extract_text() or "" for page in reader.pages]
    text = "\n\n".join(pages)
    return ExtractionResult(text=text, page_count=len(pages))


def _extract_docx(fileobj) -> ExtractionResult:
    import docx

    document = docx.Document(fileobj)
    text = "\n".join(p.text for p in document.paragraphs)
    return ExtractionResult(text=text, page_count=0)


def _extract_txt(fileobj) -> ExtractionResult:
    raw = fileobj.read()
    text = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
    return ExtractionResult(text=text)


def _extract_csv(fileobj) -> ExtractionResult:
    raw = fileobj.read()
    text_io = io.StringIO(raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw)
    rows = list(csv.reader(text_io))
    # Flatten to a readable, embedding-friendly representation.
    lines = [" | ".join(cell for cell in row) for row in rows]
    return ExtractionResult(text="\n".join(lines), metadata={"rows": len(rows)})


def _extract_xlsx(fileobj) -> ExtractionResult:
    from openpyxl import load_workbook

    wb = load_workbook(fileobj, read_only=True, data_only=True)
    chunks: list[str] = []
    for ws in wb.worksheets:
        chunks.append(f"# Sheet: {ws.title}")
        for row in ws.iter_rows(values_only=True):
            chunks.append(" | ".join("" if c is None else str(c) for c in row))
    return ExtractionResult(text="\n".join(chunks), metadata={"sheets": len(wb.worksheets)})


def _extract_image(fileobj) -> ExtractionResult:
    """OCR via Tesseract. Degrades gracefully if the binary is unavailable."""
    try:
        import pytesseract
        from PIL import Image

        image = Image.open(fileobj)
        text = pytesseract.image_to_string(image)
        return ExtractionResult(text=text, metadata={"ocr": True, "size": image.size})
    except Exception as exc:  # pragma: no cover - depends on system tesseract
        logger.warning("OCR unavailable/failed: %s", exc)
        return ExtractionResult(text="", metadata={"ocr": False, "error": str(exc)})


# file_type (documents.Document.FileType) -> extractor
EXTRACTORS: dict[str, Callable] = {
    "pdf": _extract_pdf,
    "docx": _extract_docx,
    "txt": _extract_txt,
    "csv": _extract_csv,
    "xlsx": _extract_xlsx,
    "image": _extract_image,
}


def detect_file_type(filename: str, mime_type: str = "") -> str:
    name = filename.lower()
    if name.endswith(".pdf"):
        return "pdf"
    if name.endswith((".docx", ".doc")):
        return "docx"
    if name.endswith(".txt") or name.endswith(".md"):
        return "txt"
    if name.endswith(".csv"):
        return "csv"
    if name.endswith((".xlsx", ".xls")):
        return "xlsx"
    if name.endswith((".png", ".jpg", ".jpeg", ".webp", ".tiff", ".gif")):
        return "image"
    if mime_type.startswith("image/"):
        return "image"
    return "other"


def extract(file_type: str, fileobj) -> ExtractionResult:
    extractor = EXTRACTORS.get(file_type)
    if not extractor:
        raise ValueError(f"No extractor for file type '{file_type}'")
    fileobj.seek(0)
    return extractor(fileobj)
