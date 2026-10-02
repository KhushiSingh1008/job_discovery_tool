"""Builders for domain objects used across tests."""

from datetime import UTC, date, datetime

from app.models import EligibilityTag, JobType, Listing

TODAY = date(2026, 10, 2)
NOW = datetime(2026, 10, 2, 9, 0, tzinfo=UTC)


def make_listing(**overrides: object) -> Listing:
    data: dict[str, object] = {
        "id": "abc123",
        "title": "Barista",
        "employer": "Bean & Leaf",
        "location": "Manchester",
        "pay_raw": "£12.80 per hour",
        "pay_hourly": 12.8,
        "job_type": JobType.PART_TIME,
        "posted_date": date(2026, 9, 20),
        "description": "Serve great coffee to our customers.",
        "url": "https://www.beanandleaf.co.uk/careers/barista",
        "source": "test",
        "first_seen": NOW,
        "last_seen": NOW,
        "trust_score": None,
        "trust_flags": [],
        "eligibility_tag": EligibilityTag.UNKNOWN,
    }
    data.update(overrides)
    return Listing.model_validate(data)
