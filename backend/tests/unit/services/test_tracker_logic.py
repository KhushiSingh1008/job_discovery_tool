from datetime import timedelta

import pytest

from app.models import Application, ApplicationStatus, JobType
from app.rules import load_visa_rules
from app.schemas import HoursStatus
from app.services.hours_guard import summarize_hours
from app.services.reminders import due_reminders
from app.services.tracker import ALLOWED_TRANSITIONS, can_transition
from tests.factories import NOW

S = ApplicationStatus


def _application(app_id: int = 1, **overrides: object) -> Application:
    data: dict[str, object] = {
        "id": app_id,
        "listing_id": f"listing-{app_id}",
        "status": S.APPLIED,
        "weekly_hours": 0,
        "applied_at": NOW,
        "last_contact_at": None,
        "notes": "",
        "created_at": NOW,
        "updated_at": NOW,
        "title": "Weekend Barista",
        "employer": "Bean & Leaf",
        "location": "Leeds",
        "url": "https://example.com/1",
        "job_type": JobType.PART_TIME,
        "pay_hourly": 12.8,
    }
    data.update(overrides)
    return Application.model_validate(data)


@pytest.mark.parametrize(
    ("current", "new", "allowed"),
    [
        (S.SAVED, S.APPLIED, True),
        (S.SAVED, S.SAVED, True),  # no-op
        (S.SAVED, S.INTERVIEWING, False),
        (S.APPLIED, S.OFFERED, True),  # straight offer after applying happens
        (S.INTERVIEWING, S.APPLIED, False),
        (S.OFFERED, S.REJECTED, True),
        (S.REJECTED, S.SAVED, False),
    ],
)
def test_can_transition(current: S, new: S, allowed: bool) -> None:
    assert can_transition(current, new) is allowed


def test_every_status_has_a_transition_entry() -> None:
    assert set(ALLOWED_TRANSITIONS) == set(S)


class TestHoursGuard:
    rules = load_visa_rules()

    def test_only_offers_count_as_committed(self) -> None:
        apps = [
            _application(1, status=S.OFFERED, weekly_hours=8),
            _application(2, status=S.INTERVIEWING, weekly_hours=6),
            _application(3, status=S.APPLIED, weekly_hours=30),
            _application(4, status=S.REJECTED, weekly_hours=30),
        ]

        summary = summarize_hours(apps, self.rules)

        assert (summary.committed_hours, summary.potential_hours) == (8, 14)
        assert summary.remaining_hours == 12
        assert summary.status is HoursStatus.OK

    @pytest.mark.parametrize(
        ("hours", "status"),
        [(15, HoursStatus.OK), (16, HoursStatus.NEAR_LIMIT), (20, HoursStatus.NEAR_LIMIT),
         (20.5, HoursStatus.OVER_LIMIT)],
    )  # fmt: skip
    def test_status_thresholds_against_20_hours(self, hours: float, status: HoursStatus) -> None:
        apps = [_application(status=S.OFFERED, weekly_hours=hours)]
        assert summarize_hours(apps, self.rules).status is status

    def test_rule_lookup_is_case_insensitive(self) -> None:
        summary = summarize_hours([], self.rules, country="uk", visa_type="Student-Below-Degree")
        assert summary.cap_hours == 10


class TestReminders:
    def test_uses_last_contact_over_applied_date(self) -> None:
        app = _application(
            applied_at=NOW - timedelta(days=20), last_contact_at=NOW - timedelta(days=3)
        )
        assert due_reminders([app], NOW) == []

    def test_interviewing_gets_a_thank_you_draft_and_order_is_longest_silence_first(
        self,
    ) -> None:
        apps = [
            _application(1, applied_at=NOW - timedelta(days=9)),
            _application(2, status=S.INTERVIEWING, last_contact_at=NOW - timedelta(days=14)),
        ]

        reminders = due_reminders(apps, NOW)

        assert [r.application_id for r in reminders] == [2, 1]
        assert reminders[0].draft_message.startswith("Subject: Thank you")
        assert reminders[1].draft_message.startswith("Subject: Following up")

    @pytest.mark.parametrize("status", [S.SAVED, S.OFFERED, S.REJECTED])
    def test_statuses_not_awaiting_a_reply_are_ignored(self, status: S) -> None:
        app = _application(status=status, applied_at=NOW - timedelta(days=30))
        assert due_reminders([app], NOW) == []
