import sqlite3
from datetime import date

from app.enrichment.service import enrich_all
from app.models import EligibilityTag, JobType, ListingIn
from app.repositories.listings import ListingRepository, make_listing_id
from app.rules import load_wage_rules
from tests.factories import NOW, TODAY


def _store(db: sqlite3.Connection, **overrides: object) -> str:
    data: dict[str, object] = {
        "title": "Weekend Barista",
        "employer": "Bean & Leaf",
        "location": "Leeds",
        "pay_raw": "£7.00 per hour",
        "pay_hourly": 7.0,
        "job_type": JobType.PART_TIME,
        "posted_date": date(2026, 9, 30),
        "description": "Flexible shifts around your studies.",
        "url": "https://www.studentjob.co.uk/vacancies/1",
        "source": "test",
    }
    data.update(overrides)
    listing = ListingIn.model_validate(data)
    ListingRepository(db).upsert(listing, NOW)
    return make_listing_id(listing.title, listing.employer, listing.location)


def test_enrich_all_persists_score_flags_and_tag(db: sqlite3.Connection) -> None:
    listing_id = _store(db)

    assert enrich_all(db, TODAY, load_wage_rules()) == 1

    stored = ListingRepository(db).get(listing_id)
    assert stored is not None
    assert stored.trust_score is not None and stored.trust_score < 50
    assert "pay_below_legal_minimum" in {flag.code for flag in stored.trust_flags}
    assert stored.eligibility_tag is EligibilityTag.STUDENT_FRIENDLY


def test_rescoring_ages_listings(db: sqlite3.Connection) -> None:
    listing_id = _store(db, pay_raw="£13 per hour", pay_hourly=13.0)
    wages = load_wage_rules()

    enrich_all(db, TODAY, wages)
    fresh = ListingRepository(db).get(listing_id)
    enrich_all(db, date(2026, 12, 1), wages)  # two months later, never re-scraped
    aged = ListingRepository(db).get(listing_id)

    assert fresh is not None and aged is not None
    assert aged.trust_score is not None and fresh.trust_score is not None
    assert aged.trust_score < fresh.trust_score
    assert {"ghost_job", "no_longer_listed"} <= {flag.code for flag in aged.trust_flags}
