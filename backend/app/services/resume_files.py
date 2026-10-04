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
from pdfminer.high_level import extract_text as pdfminer_extract_text
from pdfminer.layout import LAParams
from pdfminer.psexceptions import PSException
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
        # pdfminer places words by character position, so styled runs keep their spaces
        # ("for 10+ events", where simpler extractors give "for10+events").
        text = pdfminer_extract_text(io.BytesIO(data), maxpages=MAX_PDF_PAGES, laparams=LAParams())
    except (PSException, *_PARSER_ERRORS) as exc:
        raise ResumeFileError(_UNREADABLE_PDF) from exc
    return clean_pdf_text(text)


# PDF layout artefacts: icon glyphs with no text equivalent, blank lines between every line,
# and lines that only end because the page was too narrow.
_CID_GLYPH = re.compile(r"\(cid:\d+\)\s?")
_BULLET_START = re.compile(r"^\s*(?:[-*•\u2013·▪●◦]|\d+[.)])\s+")
# Icon-font glyphs left on their own (contact-line phone, mail, LinkedIn icons).
_ICON_GLYPH = re.compile(r"(?:^|(?<=\s))[#\u00a7\u00b6\ue000-\uf8ff](?=\s)\s?")
_SENTENCE_END = re.compile(r"[.!?)\]”\"]$")
_HEADING = re.compile(r"^[A-Z][A-Za-z&]*(?: [A-Za-z&]+){0,2}$")
WRAPPED_LINE_MIN_CHARS = 70  # shorter lines ended on purpose; longer ones probably wrapped


def _wraps_onto_next(line: str) -> bool:
    if len(line) < WRAPPED_LINE_MIN_CHARS:
        return False
    return line.endswith(",") or (
        bool(_BULLET_START.match(line)) and not _SENTENCE_END.search(line)
    )


def _is_continuation(previous: str, line: str) -> bool:
    if _BULLET_START.match(line):
        return False
    # After a trailing comma even a heading-like line ("GitHub Copilot") is the same list.
    return previous.endswith(",") or not _HEADING.match(line)


def clean_pdf_text(text: str) -> str:
    """Rejoin wrapped bullets, drop layout blank lines and keep a gap before each heading."""
    lines = [_ICON_GLYPH.sub("", _CID_GLYPH.sub("", line)).strip() for line in text.splitlines()]
    joined: list[str] = []
    for line in filter(None, lines):
        if joined and _wraps_onto_next(joined[-1]) and _is_continuation(joined[-1], line):
            joined[-1] = f"{joined[-1]} {line}"
        elif joined and _HEADING.match(line):
            joined.extend(["", line])
        else:
            joined.append(line)
    return "\n".join(joined)


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
