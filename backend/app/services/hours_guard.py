"""Work-hour guard: compare the hours of jobs a student holds or may hold to their visa cap.

A normal tracker ignores this, but going over the term-time cap can cost an international
student their visa. We warn on what is committed (offers) and on what *would* be committed
if every interview came through, so the student can decide before accepting.
"""

from collections.abc import Iterable

from app.models import Application, ApplicationStatus
from app.rules import VisaRules
from app.schemas import CapSource, HoursStatus, HoursSummary

NEAR_LIMIT_RATIO = 0.8


def summarize_hours(
    applications: Iterable[Application],
    rules: VisaRules,
    country: str = "UK",
    visa_type: str = "student",
    cap_override: float | None = None,
) -> HoursSummary:
    applications = list(applications)
    committed = sum(a.weekly_hours for a in applications if a.status == ApplicationStatus.OFFERED)
    interviewing = sum(
        a.weekly_hours for a in applications if a.status == ApplicationStatus.INTERVIEWING
    )
    potential = committed + interviewing

    rule = rules.find(country, visa_type)
    vacation_note = rule.vacation_note if rule else ""
    source_url = rule.source_url if rule else None
    cap: float | None
    if cap_override is not None:
        cap, cap_source = cap_override, CapSource.USER_OVERRIDE
        label = f"Your own limit ({cap_override:g} hours/week)"
    elif rule is not None:
        cap, cap_source, label = rule.hours_per_week, CapSource.VISA_RULE, rule.label
    else:
        cap, cap_source = rules.fallback_hours_per_week, CapSource.FALLBACK
        label = f"Unknown visa: using a {cap:g}-hour default. Check your official rules."

    if cap is None:
        status, message = HoursStatus.NO_LIMIT, "Your visa has no weekly limit on work hours."
        remaining = None
    else:
        remaining = round(cap - committed, 2)
        if committed > cap:
            status = HoursStatus.OVER_LIMIT
            message = (
                f"Your jobs add up to {committed:g} hours a week, over your {cap:g}-hour limit. "
                "Working over the limit can breach your visa conditions."
            )
        elif potential > cap:
            status = HoursStatus.NEAR_LIMIT
            message = (
                f"If your interviews turn into offers you would work {potential:g} hours a week, "
                f"over your {cap:g}-hour limit. Plan which offers to accept."
            )
        elif committed >= NEAR_LIMIT_RATIO * cap:
            status = HoursStatus.NEAR_LIMIT
            message = f"You are close to your limit: {remaining:g} of {cap:g} hours left a week."
        else:
            status = HoursStatus.OK
            message = f"You have {remaining:g} of {cap:g} hours a week left."

    return HoursSummary(
        cap_hours=cap,
        cap_source=cap_source,
        rule_label=label,
        vacation_note=vacation_note,
        source_url=source_url,
        committed_hours=committed,
        potential_hours=potential,
        remaining_hours=remaining,
        status=status,
        message=message,
    )
