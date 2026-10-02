from datetime import date
from pathlib import Path

import pytest

from app.db import open_db
from app.enrichment.service import enrich_all
from app.models import JobType, ListingIn
from app.repositories.listings import ListingRepository, make_listing_id
from app.rules import load_wage_rules
from tests.factories import NOW, TODAY

SEED = [
    {
        "title": "Weekend Barista",
        "employer": "Bean & Leaf",
        "location": "Manchester",
        "pay_raw": "£12.80 per hour",
        "pay_hourly": 12.8,
        "job_type": JobType.PART_TIME,
        "posted_date": date(2026, 9, 30),
        "description": "Flexible shifts around your studies. 100% fun.",
        "url": "https://www.beanandleaf.co.uk/careers/barista",
        "source": "studentjob",
    },
    {
        "title": "Summer Software Intern",
        "employer": "Monzo",
        "location": "London",
        "pay_raw": "£25 per hour",
        "pay_hourly": 25.0,
        "job_type": JobType.INTERNSHIP,
        "posted_date": date(2026, 9, 25),
        "description": "Build banking features.",
        "url": "https://job-boards.greenhouse.io/monzo/jobs/1",
        "source": "greenhouse",
    },
    {
        "title": "Graduate Analyst",
        "employer": "Acme",
        "location": "London",
        "pay_raw": "Competitive",
        "pay_hourly": None,
        "job_type": JobType.FULL_TIME,
        "posted_date": date(2026, 8, 1),
        "description": "We cannot sponsor visas for this role.",
        "url": "https://www.studentjob.co.uk/vacancies/2",
        "source": "studentjob",
    },
    {
        "title": "Earn money with surveys",
        "employer": "Panel Co",
        "location": "Remote",
        "pay_raw": "£5 per hour",
        "pay_hourly": 5.0,
        "job_type": JobType.PART_TIME,
        "posted_date": date(2026, 9, 28),
        "description": "Get paid to share your opinion.",
        "url": "https://www.studentjob.co.uk/vacancies/3",
        "source": "studentjob",
    },
    {
        "title": "Delivery Rider",
        "employer": "Deliveroo",
        "location": "Leeds",
        "pay_raw": "£13.50 per hour",
        "pay_hourly": 13.5,
        "job_type": JobType.PART_TIME,
        "posted_date": date(2026, 10, 1),
        "description": "Deliver food on your own schedule.",
        "url": "https://job-boards.greenhouse.io/deliveroo/jobs/4",
        "source": "greenhouse",
    },
]


@pytest.fixture
def listing_ids(db_path: Path) -> dict[str, str]:
    """Seed the API database with enriched listings; returns ids keyed by title."""
    ids: dict[str, str] = {}
    with open_db(db_path) as conn:
        repo = ListingRepository(conn)
        for data in SEED:
            listing = ListingIn.model_validate(data)
            repo.upsert(listing, NOW)
            ids[listing.title] = make_listing_id(listing.title, listing.employer, listing.location)
        conn.commit()
        enrich_all(conn, TODAY, load_wage_rules())
    return ids
