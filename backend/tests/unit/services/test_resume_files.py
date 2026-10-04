import io
import zipfile

import pytest

from app.services.resume_files import (
    MAX_PDF_PAGES,
    MAX_UNZIPPED_BYTES,
    MAX_UPLOAD_BYTES,
    ResumeFileError,
    extract_resume_text,
)
from tests.documents import encrypt_pdf, make_docx, make_pdf, make_zip_bomb

LINES = [
    "Priya Sharma",
    "Retail Assistant, Boots (2025-2026)",
    "- Responsible for handling cash on the till",
    "- Served customers at busy times",
]


def test_reads_text_from_a_pdf() -> None:
    text = extract_resume_text(make_pdf(LINES))

    assert "Priya Sharma" in text
    assert "Responsible for handling cash on the till" in text


def test_reads_paragraphs_and_tables_from_a_word_document() -> None:
    data = make_docx(LINES, table=[["Skills", "Excel, teamwork and customer service"]])

    text = extract_resume_text(data)

    assert text.splitlines()[:2] == ["Priya Sharma", "Retail Assistant, Boots (2025-2026)"]
    assert "Skills  Excel, teamwork and customer service" in text


@pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig", "cp1252"])
def test_reads_plain_text_in_common_encodings(encoding: str) -> None:
    resume = "\r\n".join([*LINES, "Café supervisor \u2013 weekends"])

    text = extract_resume_text(resume.encode(encoding))

    assert text.endswith("Café supervisor \u2013 weekends")
    assert "\r" not in text


def test_tidies_whitespace() -> None:
    text = extract_resume_text(("  \n" + "\n\n\n\n".join(LINES) + "   \n\n").encode())
    assert text == "\n\n".join(LINES)


def test_format_comes_from_the_bytes_not_the_name() -> None:
    # A PDF is a PDF whatever it is called; there is no filename to trust at all.
    assert "Priya Sharma" in extract_resume_text(make_pdf(LINES))


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (encrypt_pdf(make_pdf(LINES)), "password-protected"),
        (make_pdf(LINES, pages=MAX_PDF_PAGES + 1), "longer than"),
        (b"%PDF-1.7\nthis is not really a pdf", "couldn't read this PDF"),
        (make_zip_bomb(MAX_UNZIPPED_BYTES + 1), "too large"),
        (b"PK\x03\x04 not a zip", "couldn't read this Word document"),
        (b"\x00\x01\x02binary" * 20, "Upload a PDF"),
        (make_pdf([]), "couldn't find enough text"),
        (b"x" * (MAX_UPLOAD_BYTES + 1), "2 MB or smaller"),
        (("word " * 4_100).encode(), "too long"),
    ],
    ids=[
        "encrypted-pdf",
        "too-many-pages",
        "corrupt-pdf",
        "zip-bomb",
        "corrupt-zip",
        "binary",
        "scanned-or-empty",
        "too-big",
        "too-much-text",
    ],
)
def test_unusable_files_get_a_friendly_reason(data: bytes, message: str) -> None:
    with pytest.raises(ResumeFileError, match=message):
        extract_resume_text(data)


def test_zip_that_is_not_a_word_document_is_refused() -> None:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as archive:
        archive.writestr("payload.exe", b"MZ" + b"0" * 100)
    with pytest.raises(ResumeFileError, match="Upload a PDF"):
        extract_resume_text(out.getvalue())
