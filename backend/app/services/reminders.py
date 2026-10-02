"""Follow-up reminders for applications that have gone quiet, with a ready-to-edit draft."""

from collections.abc import Iterable
from datetime import datetime

from app.models import Application, ApplicationStatus
from app.schemas import Reminder

_AWAITING_REPLY = frozenset({ApplicationStatus.APPLIED, ApplicationStatus.INTERVIEWING})

_APPLIED_DRAFT = """Subject: Following up on my application for {title}

Dear {employer} hiring team,

I applied for the {title} role on {since} and wanted to ask whether there is any update on \
my application. I am still very interested in the position and happy to share anything else \
you need, including my availability around my studies.

Thank you for your time.

Kind regards,
[Your name]"""

_INTERVIEW_DRAFT = """Subject: Thank you, and next steps for {title}

Dear {employer} hiring team,

Thank you again for the opportunity to interview for the {title} role. I enjoyed learning \
more about the team and wanted to ask whether there is an update on next steps.

I remain very interested in the role and look forward to hearing from you.

Kind regards,
[Your name]"""


def _last_activity(application: Application) -> datetime:
    return application.last_contact_at or application.applied_at or application.updated_at


def draft_follow_up(application: Application) -> str:
    template = (
        _INTERVIEW_DRAFT if application.status == ApplicationStatus.INTERVIEWING else _APPLIED_DRAFT
    )
    since = (application.applied_at or application.created_at).strftime("%d %B %Y")
    return template.format(title=application.title, employer=application.employer, since=since)


def due_reminders(
    applications: Iterable[Application], now: datetime, silence_days: int = 7
) -> list[Reminder]:
    """Applications awaiting a reply with no contact for ``silence_days`` or more."""
    reminders = []
    for application in applications:
        if application.status not in _AWAITING_REPLY:
            continue
        days_silent = (now - _last_activity(application)).days
        if days_silent >= silence_days:
            reminders.append(
                Reminder(
                    application_id=application.id,
                    title=application.title,
                    employer=application.employer,
                    status=application.status,
                    days_silent=days_silent,
                    draft_message=draft_follow_up(application),
                )
            )
    return sorted(reminders, key=lambda r: r.days_silent, reverse=True)
