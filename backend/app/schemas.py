"""Request and response bodies of the HTTP API (the domain models live in ``models``)."""

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

from app.models import ApplicationStatus, EligibilityTag, JobType


class SortOrder(StrEnum):
    NEWEST = "newest"
    PAY = "pay"
    TRUST = "trust"


class ListingSummary(BaseModel):
    """A listing without its (long) description, for result lists."""

    id: str
    title: str
    employer: str
    location: str
    pay_raw: str | None
    pay_hourly: float | None
    job_type: JobType
    posted_date: date
    url: str
    source: str
    trust_score: int | None
    eligibility_tag: EligibilityTag


class ListingPage(BaseModel):
    items: list[ListingSummary]
    total: int
    page: int
    page_size: int


class FacetCount(BaseModel):
    value: str
    count: int


class FilterFacets(BaseModel):
    job_types: list[FacetCount]
    sources: list[FacetCount]
    locations: list[FacetCount]
    eligibility: list[FacetCount]
    max_pay_hourly: float | None


class ApplicationCreate(BaseModel):
    listing_id: str
    status: ApplicationStatus = ApplicationStatus.SAVED
    weekly_hours: float = Field(default=0, ge=0, le=168)
    notes: str = ""


class ApplicationUpdate(BaseModel):
    """Partial update: only the fields that are sent are changed."""

    status: ApplicationStatus | None = None
    weekly_hours: float | None = Field(default=None, ge=0, le=168)
    notes: str | None = None
    last_contact_at: datetime | None = None


class HoursStatus(StrEnum):
    OK = "ok"
    NEAR_LIMIT = "near_limit"
    OVER_LIMIT = "over_limit"
    NO_LIMIT = "no_limit"


class CapSource(StrEnum):
    VISA_RULE = "visa_rule"
    USER_OVERRIDE = "user_override"
    FALLBACK = "fallback"


class HoursSummary(BaseModel):
    cap_hours: float | None
    cap_source: CapSource
    rule_label: str
    vacation_note: str
    source_url: str | None
    committed_hours: float  # jobs you hold (offered)
    potential_hours: float  # committed + interviewing: what you'd work if all came through
    remaining_hours: float | None
    status: HoursStatus
    message: str


class Reminder(BaseModel):
    application_id: int
    title: str
    employer: str
    status: ApplicationStatus
    days_silent: int
    draft_message: str


class MatchEngine(StrEnum):
    CLAUDE = "claude"
    KEYWORD = "keyword"


class ResumeJobRequest(BaseModel):
    """Resume text plus either a stored listing or a pasted job description."""

    resume_text: str = Field(min_length=50, max_length=20_000)
    listing_id: str | None = None
    job_description: str | None = Field(default=None, min_length=50, max_length=20_000)

    @model_validator(mode="after")
    def _exactly_one_job(self) -> "ResumeJobRequest":
        if (self.listing_id is None) == (self.job_description is None):
            raise ValueError("Provide exactly one of listing_id or job_description")
        return self


class MatchRequest(ResumeJobRequest):
    pass


class EnhanceRequest(ResumeJobRequest):
    pass


class MatchResult(BaseModel):
    score: int = Field(ge=0, le=100)
    summary: str
    matched_skills: list[str]
    missing_skills: list[str]
    suggestions: list[str]
    engine: MatchEngine
    notice: str | None = None  # e.g. why the offline matcher was used


class EnhanceEngine(StrEnum):
    CLAUDE = "claude"
    RULES = "rules"


class SuggestionKind(StrEnum):
    REWRITE = "rewrite"  # replace ``original`` (verbatim resume text) with ``replacement``
    ADD = "add"  # insert ``replacement`` as a new line after the line containing ``original``


class SuggestionDraft(BaseModel):
    """One proposed resume edit, before it is checked against the resume."""

    kind: SuggestionKind
    section: str = Field(description="Resume section the edit belongs to, e.g. 'Experience'")
    original: str = Field(description="Rewrite: text to replace. Add: anchor line ('' = top)")
    replacement: str
    reason: str


class ResumeSuggestion(SuggestionDraft):
    id: str


class EnhanceResult(BaseModel):
    suggestions: list[ResumeSuggestion]
    engine: EnhanceEngine
    notice: str | None = None


class ResumeText(BaseModel):
    text: str


class ScrapeRunStatus(StrEnum):
    OK = "ok"
    PARTIAL = "partial"  # some pages failed or discovery had gaps
    EMPTY = "empty"  # pages fetched but nothing parsed: the site layout probably changed
    FAILED = "failed"  # the source could not be scraped at all


class ScrapeRun(BaseModel):
    """One scrape of one source, as recorded for monitoring."""

    source: str
    started_at: datetime
    finished_at: datetime
    status: ScrapeRunStatus
    pages: int = 0
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    skipped: int = 0
    failed_pages: int = 0
    closed: int = 0
    errors: list[str] = Field(default_factory=list)
    #: Share (0-1) of this run's listings that had each field, e.g. {"pay_hourly": 0.42}.
    quality: dict[str, float] = Field(default_factory=dict)


class SourceHealth(BaseModel):
    name: str
    label: str
    open_listings: int
    last_run: ScrapeRun | None
