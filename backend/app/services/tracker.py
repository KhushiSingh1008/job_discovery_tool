"""Application tracker: creating, updating and moving applications through the pipeline."""

import sqlite3
from datetime import datetime
from typing import Any

from app.models import Application, ApplicationStatus
from app.repositories.applications import DEFAULT_OWNER, ApplicationRepository
from app.repositories.listings import ListingRepository
from app.schemas import ApplicationCreate, ApplicationUpdate
from app.services.errors import ConflictError, InvalidTransitionError, NotFoundError

S = ApplicationStatus

# saved -> applied -> interviewing -> offered, with rejected reachable from anywhere active.
ALLOWED_TRANSITIONS: dict[ApplicationStatus, frozenset[ApplicationStatus]] = {
    S.SAVED: frozenset({S.APPLIED, S.REJECTED}),
    S.APPLIED: frozenset({S.INTERVIEWING, S.OFFERED, S.REJECTED}),
    S.INTERVIEWING: frozenset({S.OFFERED, S.REJECTED}),
    S.OFFERED: frozenset({S.REJECTED}),  # offer withdrawn or declined
    S.REJECTED: frozenset(),
}

# Statuses that mean the employer got back to the student.
_EMPLOYER_RESPONSES = frozenset({S.INTERVIEWING, S.OFFERED, S.REJECTED})


def can_transition(current: ApplicationStatus, new: ApplicationStatus) -> bool:
    return new == current or new in ALLOWED_TRANSITIONS[current]


class TrackerService:
    def __init__(self, conn: sqlite3.Connection, owner: str = DEFAULT_OWNER) -> None:
        self._applications = ApplicationRepository(conn, owner)
        self._listings = ListingRepository(conn)

    def list(self) -> list[Application]:
        return self._applications.list()

    def get(self, application_id: int) -> Application:
        application = self._applications.get(application_id)
        if application is None:
            raise NotFoundError(f"Application {application_id} not found")
        return application

    def create(self, data: ApplicationCreate, now: datetime) -> Application:
        if self._listings.get(data.listing_id) is None:
            raise NotFoundError(f"Listing {data.listing_id} not found")
        if self._applications.get_by_listing(data.listing_id) is not None:
            raise ConflictError("This listing is already in your tracker")

        # Students often add a job they have already applied for elsewhere.
        applied_at = now if data.status != S.SAVED else None
        application_id = self._applications.create(
            data.listing_id, data.status, data.weekly_hours, data.notes, now, applied_at
        )
        return self.get(application_id)

    def update(self, application_id: int, data: ApplicationUpdate, now: datetime) -> Application:
        current = self.get(application_id)
        changes: dict[str, Any] = data.model_dump(exclude_unset=True, exclude_none=True)

        new_status = changes.get("status")
        if new_status is not None and new_status != current.status:
            if not can_transition(current.status, new_status):
                raise InvalidTransitionError(
                    f"Cannot move an application from '{current.status}' to '{new_status}'"
                )
            if new_status == S.APPLIED and current.applied_at is None:
                changes["applied_at"] = now
            if new_status == S.APPLIED or new_status in _EMPLOYER_RESPONSES:
                changes.setdefault("last_contact_at", now)

        if changes:
            self._applications.update(application_id, changes, now)
        return self.get(application_id)

    def delete(self, application_id: int) -> None:
        if not self._applications.delete(application_id):
            raise NotFoundError(f"Application {application_id} not found")
