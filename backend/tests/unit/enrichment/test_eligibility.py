import pytest

from app.enrichment.eligibility import tag_eligibility
from app.models import EligibilityTag


@pytest.mark.parametrize(
    ("description", "expected"),
    [
        ("Applicants must be British citizens only.", EligibilityTag.UK_CITIZENS_ONLY),
        ("This role requires SC clearance.", EligibilityTag.UK_CITIZENS_ONLY),
        ("We are unable to offer visa sponsorship.", EligibilityTag.RIGHT_TO_WORK_REQUIRED),
        ("No sponsorship is available for this role.", EligibilityTag.RIGHT_TO_WORK_REQUIRED),
        ("You must have the right to work in the UK.", EligibilityTag.RIGHT_TO_WORK_REQUIRED),
        ("Visa sponsorship is available.", EligibilityTag.SPONSORSHIP_AVAILABLE),
        ("We can sponsor a Skilled Worker visa.", EligibilityTag.SPONSORSHIP_AVAILABLE),
        ("Flexible shifts around your studies.", EligibilityTag.STUDENT_FRIENDLY),
        ("International students welcome!", EligibilityTag.STUDENT_FRIENDLY),
        ("Serve great coffee.", EligibilityTag.UNKNOWN),
    ],
)
def test_tag_eligibility(description: str, expected: EligibilityTag) -> None:
    assert tag_eligibility("Barista", description) == expected


def test_explicit_no_sponsorship_outranks_student_friendly() -> None:
    text = "Students welcome. Please note we cannot sponsor visas."
    assert tag_eligibility("Graduate Analyst", text) == EligibilityTag.RIGHT_TO_WORK_REQUIRED


def test_student_friendly_outranks_generic_right_to_work() -> None:
    # A Student visa gives the right to work part-time, so this is still a good match.
    text = "Ideal for students. You must be eligible to work in the UK."
    assert tag_eligibility("Weekend Barista", text) == EligibilityTag.STUDENT_FRIENDLY
