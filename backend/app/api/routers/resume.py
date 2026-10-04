"""Resume tools: read an uploaded resume, and suggest edits tailored to one job."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from starlette.concurrency import run_in_threadpool

from app.api.deps import DbConn
from app.api.job_target import resolve_job
from app.config import get_settings
from app.schemas import EnhanceRequest, EnhanceResult, ResumeText
from app.services.enhancement.base import Enhancer
from app.services.enhancement.factory import build_enhancer
from app.services.resume_files import MAX_UPLOAD_BYTES, ResumeFileError, extract_resume_text

router = APIRouter(prefix="/api/resume", tags=["resume"])

_TOO_LARGE = f"Files must be {MAX_UPLOAD_BYTES // (1024 * 1024)} MB or smaller."


def get_enhancer() -> Enhancer:
    return build_enhancer(get_settings())


async def _read_body(request: Request) -> bytes:
    """The request body, refusing anything over the limit *while* it streams in.

    Reading the raw body (rather than a multipart form) keeps the file in memory only:
    multipart parsing would spool large uploads to a temporary file on disk.
    """
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, _TOO_LARGE)
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > MAX_UPLOAD_BYTES:
            raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, _TOO_LARGE)
    return bytes(body)


@router.post(
    "/extract",
    response_model=ResumeText,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/octet-stream": {"schema": {"type": "string", "format": "binary"}}
            },
        }
    },
)
async def extract_resume(request: Request) -> ResumeText:
    """Text of a PDF, Word (.docx) or plain-text resume, sent as the raw request body.

    The file is parsed in memory and discarded; it is never stored or logged.
    """
    data = await _read_body(request)
    try:
        # Parsing is CPU-bound, so keep it off the event loop.
        text = await run_in_threadpool(extract_resume_text, data)
    except ResumeFileError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    return ResumeText(text=text)


@router.post("/enhance", response_model=EnhanceResult)
def enhance_resume(
    data: EnhanceRequest, db: DbConn, enhancer: Annotated[Enhancer, Depends(get_enhancer)]
) -> EnhanceResult:
    title, job_text = resolve_job(db, data)
    return enhancer.enhance(data.resume_text, title, job_text)
