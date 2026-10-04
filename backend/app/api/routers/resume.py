"""Resume enhancement: line-level edits tailored to one job, accepted or rejected by the user."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import DbConn
from app.api.job_target import resolve_job
from app.config import get_settings
from app.schemas import EnhanceRequest, EnhanceResult
from app.services.enhancement.base import Enhancer
from app.services.enhancement.factory import build_enhancer

router = APIRouter(prefix="/api/resume", tags=["resume"])


def get_enhancer() -> Enhancer:
    return build_enhancer(get_settings())


@router.post("/enhance", response_model=EnhanceResult)
def enhance_resume(
    data: EnhanceRequest, db: DbConn, enhancer: Annotated[Enhancer, Depends(get_enhancer)]
) -> EnhanceResult:
    title, job_text = resolve_job(db, data)
    return enhancer.enhance(data.resume_text, title, job_text)
