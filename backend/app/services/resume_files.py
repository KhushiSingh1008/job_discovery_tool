"""Turn an uploaded resume (PDF, DOCX or plain text) into text, safely.

Uploads are handled entirely in memory and never written to disk or logged. Every input is
treated as hostile:

- the format is detected from the file's bytes, never from its name or declared type;
- size, page count and unzipped size are capped before any parsing work is done, which
  defuses oversized PDFs and zip bombs;
- encrypted PDFs are refused rather than decrypted.
"""

import io
import re
import zipfile

import docx
from pypdf import PdfReader
from pypdf.errors import PdfReadError

MAX_UPLOAD_BYTES = 2 * 1024 * 1024
MAX_PDF_PAGES = 10
MAX_UNZIPPED_BYTES = 20 * 1024 * 1024
MIN_TEXT_CHARS = 50
MAX_TEXT_CHARS = 20_000

_PDF_MAGIC = b"%PDF-"
_ZIP_MAGIC = b"PK\x03\x04"


class ResumeFileError(Exception):
    """The file cannot be used; the message is safe to show to the student."""


# What malformed files make the parsers raise (they are not consistent about it).
_PARSER_ERRORS = (PdfReadError, zipfile.BadZipFile, ValueError, KeyError, TypeError, OSError)
_UNREADABLE_PDF = "We couldn't read this PDF. Try another copy or paste the text."
_UNREADABLE_DOCX = "We couldn't read this Word document. Try saving it again."


def _pdf_text(data: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(data))
        encrypted = reader.is_encrypted
        page_count = 0 if encrypted else len(reader.pages)
    except _PARSER_ERRORS as exc:
        raise ResumeFileError(_UNREADABLE_PDF) from exc
    if encrypted:
        raise ResumeFileError("This PDF is password-protected. Remove the password or paste it.")
    if page_count > MAX_PDF_PAGES:
        raise ResumeFileError(f"Resumes longer than {MAX_PDF_PAGES} pages are not supported.")
    try:
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except _PARSER_ERRORS as exc:
        raise ResumeFileError(_UNREADABLE_PDF) from exc


def _docx_text(data: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            unzipped_size = sum(info.file_size for info in archive.infolist())
            is_word = "word/document.xml" in archive.namelist()
    except _PARSER_ERRORS as exc:
        raise ResumeFileError(_UNREADABLE_DOCX) from exc
    # Checked before parsing, from the zip directory alone, so a zip bomb is never inflated.
    if unzipped_size > MAX_UNZIPPED_BYTES:
        raise ResumeFileError("This document is too large to read.")
    if not is_word:
        raise ResumeFileError("Upload a PDF, Word (.docx) or plain-text file.")
    try:
        document = docx.Document(io.BytesIO(data))
    except _PARSER_ERRORS as exc:
        raise ResumeFileError(_UNREADABLE_DOCX) from exc

    lines = [paragraph.text for paragraph in document.paragraphs]
    for table in document.tables:  # many resume templates lay out sections in tables
        for row in table.rows:
            lines.append("  ".join(cell.text.strip() for cell in row.cells if cell.text.strip()))
    return "\n".join(lines)


def _plain_text(data: bytes) -> str:
    if b"\x00" in data:
        raise ResumeFileError("Upload a PDF, Word (.docx) or plain-text file.")
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp1252", errors="replace")  # older Windows text files


def _tidy(text: str) -> str:
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def extract_resume_text(data: bytes) -> str:
    """Plain text of a resume file; raises ``ResumeFileError`` with a friendly reason."""
    if len(data) > MAX_UPLOAD_BYTES:
        raise ResumeFileError(f"Files must be {MAX_UPLOAD_BYTES // (1024 * 1024)} MB or smaller.")

    if data.startswith(_PDF_MAGIC):
        text = _pdf_text(data)
    elif data.startswith(_ZIP_MAGIC):
        text = _docx_text(data)
    else:
        text = _plain_text(data)

    text = _tidy(text)
    if len(text) < MIN_TEXT_CHARS:
        raise ResumeFileError(
            "We couldn't find enough text in this file. If it is a scanned image, paste the "
            "text instead."
        )
    if len(text) > MAX_TEXT_CHARS:
        raise ResumeFileError("This resume is too long. Keep it under 20,000 characters.")
    return text
