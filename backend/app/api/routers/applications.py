"""Application tracker with the visa work-hour guard and follow-up reminders."""

from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from app.api.deps import AppSettings, DbConn, Now, Owner
from app.models import Application
from app.rules import load_visa_rules
from app.schemas import ApplicationCreate, ApplicationUpdate, HoursSummary, Reminder
from app.services.hours_guard import summarize_hours
from app.services.reminders import due_reminders
from app.services.tracker import TrackerService

router = APIRouter(prefix="/api/applications", tags=["applications"])


@router.get("", response_model=list[Application])
def list_applications(db: DbConn, owner: Owner) -> list[Application]:
    return TrackerService(db, owner).list()


@router.post("", response_model=Application, status_code=status.HTTP_201_CREATED)
def create_application(data: ApplicationCreate, db: DbConn, owner: Owner, now: Now) -> Application:
    return TrackerService(db, owner).create(data, now)


# Static paths are declared before "/{application_id}" so they are matched first.
@router.get("/hours-summary", response_model=HoursSummary)
def hours_summary(
    db: DbConn,
    owner: Owner,
    country: Annotated[str, Query(max_length=10)] = "UK",
    visa_type: Annotated[str, Query(max_length=40)] = "student",
    cap_override: Annotated[float | None, Query(ge=0, le=168)] = None,
) -> HoursSummary:
    return summarize_hours(
        TrackerService(db, owner).list(), load_visa_rules(), country, visa_type, cap_override
    )


@router.get("/reminders", response_model=list[Reminder])
def reminders(db: DbConn, owner: Owner, now: Now, settings: AppSettings) -> list[Reminder]:
    return due_reminders(TrackerService(db, owner).list(), now, settings.reminder_silence_days)


@router.get("/{application_id}", response_model=Application)
def get_application(application_id: int, db: DbConn, owner: Owner) -> Application:
    return TrackerService(db, owner).get(application_id)


@router.patch("/{application_id}", response_model=Application)
def update_application(
    application_id: int, data: ApplicationUpdate, db: DbConn, owner: Owner, now: Now
) -> Application:
    return TrackerService(db, owner).update(application_id, data, now)


@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_application(application_id: int, db: DbConn, owner: Owner) -> Response:
    TrackerService(db, owner).delete(application_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
