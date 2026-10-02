"""Map schema.org ``employmentType`` values and free text to our three job types."""

import re

from app.models import JobType

# Checked in this order: "Part-time internship" is an internship,
# "Graduate (part time)" is part-time.
_RULES: tuple[tuple[JobType, re.Pattern[str]], ...] = (
    (
        JobType.INTERNSHIP,
        re.compile(
            r"\bintern(ship)?s?\b|placement|work experience|summer analyst|insight (day|week)",
            re.I,
        ),
    ),
    (
        JobType.PART_TIME,
        re.compile(
            r"part[\s_-]?time|\bcasual\b|zero[\s-]?hours?|\bseasonal\b|\bweekend\b|"
            r"\bevening\b|flexible hours|\bper_diem\b|\bhourly\b|\bsaturday\b",
            re.I,
        ),
    ),
    (
        JobType.FULL_TIME,
        re.compile(r"full[\s_-]?time|\bpermanent\b|\bgraduate scheme\b", re.I),
    ),
)


def classify(text: str | None) -> JobType | None:
    """Classify a single piece of text, or ``None`` if it carries no job-type signal."""
    if not text:
        return None
    for job_type, pattern in _RULES:
        if pattern.search(text):
            return job_type
    return None


def normalize_job_type(
    employment_type: str | None,
    title: str = "",
    description: str = "",
    default: JobType = JobType.FULL_TIME,
) -> JobType:
    """Use the most authoritative signal available: explicit type, then title, then description.

    The description is noisy ("this is not a part-time role"), so it is only a last resort
    before the adapter's ``default``.
    """
    for text in (employment_type, title, description):
        job_type = classify(text)
        if job_type is not None:
            return job_type
    return default
