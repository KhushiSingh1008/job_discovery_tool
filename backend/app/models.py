"""Domain models shared by the scraper, repositories and API."""

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field, HttpUrl


class JobType(StrEnum):
    PART_TIME = "part-time"
    FULL_TIME = "full-time"
    INTERNSHIP = "internship"


class EligibilityTag(StrEnum):
    STUDENT_FRIENDLY = "student-friendly"
    SPONSORSHIP_AVAILABLE = "sponsorship-available"
    RIGHT_TO_WORK_REQUIRED = "right-to-work-required"
    UK_CITIZENS_ONLY = "uk-citizens-only"
    UNKNOWN = "unknown"


class ApplicationStatus(StrEnum):
    SAVED = "saved"
    APPLIED = "applied"
    INTERVIEWING = "interviewing"
    OFFERED = "offered"
    REJECTED = "rejected"


class ListingIn(BaseModel):
    """A normalised listing produced by the scraper, ready to be stored."""

    title: str = Field(min_length=1)
    employer: str = Field(min_length=1)
    location: str = ""
    pay_raw: str | None = None
    pay_hourly: float | None = Field(default=None, ge=0)
    job_type: JobType
    posted_date: date | None = None
    description: str = ""
    url: HttpUrl
    source: str = Field(min_length=1)


class Listing(BaseModel):
    """A stored listing, as returned by the API."""

    id: str
    title: str
    employer: str
    location: str
    pay_raw: str | None
    pay_hourly: float | None
    job_type: JobType
    posted_date: date
    description: str
    url: str
    source: str
    first_seen: datetime
    last_seen: datetime
    trust_score: int | None
    trust_flags: list[str]
    eligibility_tag: EligibilityTag
