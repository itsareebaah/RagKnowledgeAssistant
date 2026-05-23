import re
from pathlib import Path

from docx import Document as DocxDocument
from pypdf import PdfReader

from app.config import settings


def extract_text(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf(file_path)
    if suffix == ".docx":
        return _extract_docx(file_path)
    if suffix in {".txt", ".md", ".csv"}:
        return file_path.read_text(encoding="utf-8", errors="replace")
    raise ValueError(f"Unsupported file type: {suffix}")


def _extract_pdf(file_path: Path) -> str:
    reader = PdfReader(str(file_path))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(pages)


def _extract_docx(file_path: Path) -> str:
    doc = DocxDocument(str(file_path))
    return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())


def chunk_text(text: str, filename: str) -> list[dict]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []

    size = settings.chunk_size
    overlap = settings.chunk_overlap
    chunks: list[dict] = []
    start = 0
    index = 0

    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            boundary = text.rfind(" ", start, end)
            if boundary > start + size // 2:
                end = boundary

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(
                {
                    "text": chunk,
                    "metadata": {"filename": filename, "chunk_index": index},
                }
            )
            index += 1

        if end >= len(text):
            break
        start = max(end - overlap, start + 1)

    return chunks
