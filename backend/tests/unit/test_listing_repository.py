import sqlite3
from datetime import UTC, date, datetime, timedelta

from app.models import JobType, ListingIn
from app.repositories.listings import ListingRepository, UpsertOutcome, make_listing_id

T0 = datetime(2026, 9, 1, 9, 0, tzinfo=UTC)
T1 = T0 + timedelta(days=3)


def _listing(**overrides: object) -> ListingIn:
    data: dict[str, object] = {
        "title": "Barista",
        "employer": "Bean & Leaf",
        "location": "Manchester",
        "pay_raw": "£12.21 per hour",
        "pay_hourly": 12.21,
        "job_type": JobType.PART_TIME,
        "posted_date": None,
        "url": "https://beanandleaf.example/jobs/1",
        "source": "test",
    }
    data.update(overrides)
    return ListingIn.model_validate(data)


def test_listing_id_ignores_case_and_whitespace() -> None:
    assert make_listing_id("Barista ", "BEAN & LEAF", "Manchester") == make_listing_id(
        "barista", "Bean  &  Leaf", " manchester"
    )
    assert make_listing_id("Barista", "Bean & Leaf", "Leeds") != make_listing_id(
        "Barista", "Bean & Leaf", "Manchester"
    )


def test_insert_sets_first_and_last_seen_and_falls_back_to_today(db: sqlite3.Connection) -> None:
    repo = ListingRepository(db)

    assert repo.upsert(_listing(), T0) is UpsertOutcome.INSERTED

    stored = repo.get(make_listing_id("Barista", "Bean & Leaf", "Manchester"))
    assert stored is not None
    assert stored.first_seen == stored.last_seen == T0
    assert stored.posted_date == T0.date()
    assert stored.trust_flags == []


def test_rescrape_updates_without_losing_history(db: sqlite3.Connection) -> None:
    repo = ListingRepository(db)
    repo.upsert(_listing(posted_date=date(2026, 8, 30)), T0)

    outcome = repo.upsert(_listing(pay_raw="£12.50 per hour", pay_hourly=12.5), T1)

    stored = repo.get(make_listing_id("Barista", "Bean & Leaf", "Manchester"))
    assert outcome is UpsertOutcome.UPDATED
    assert repo.count() == 1
    assert stored is not None
    assert stored.first_seen == T0
    assert stored.last_seen == T1
    assert stored.pay_hourly == 12.5
    assert stored.posted_date == date(2026, 8, 30)  # page dropped its date: keep the known one


def test_get_unknown_id_returns_none(db: sqlite3.Connection) -> None:
    assert ListingRepository(db).get("missing") is None
