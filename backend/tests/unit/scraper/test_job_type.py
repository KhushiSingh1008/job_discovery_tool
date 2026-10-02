import pytest

from app.models import JobType
from app.scraper.normalize.job_type import normalize_job_type


@pytest.mark.parametrize(
    ("employment_type", "title", "description", "expected"),
    [
        ("PART_TIME", "Barista", "", JobType.PART_TIME),
        ("FULL_TIME", "Store Manager", "", JobType.FULL_TIME),
        ("INTERN", "Marketing Assistant", "", JobType.INTERNSHIP),
        ("Part-time, Internship", "", "", JobType.INTERNSHIP),
        ("Zero hours contract", "Delivery Rider", "", JobType.PART_TIME),
        (None, "Summer Internship 2027", "", JobType.INTERNSHIP),
        (None, "Industrial Placement - Engineering", "", JobType.INTERNSHIP),
        (None, "Weekend Team Member", "", JobType.PART_TIME),
        (None, "Casual Bar Staff", "", JobType.PART_TIME),
        (None, "Software Engineer", "This is a permanent role.", JobType.FULL_TIME),
        # explicit type beats a noisy title or description
        ("FULL_TIME", "Weekend Supervisor", "", JobType.FULL_TIME),
    ],
)
def test_normalize_job_type(
    employment_type: str | None, title: str, description: str, expected: JobType
) -> None:
    assert normalize_job_type(employment_type, title, description) == expected


def test_international_is_not_an_internship() -> None:
    assert normalize_job_type(None, "International Sales Executive") == JobType.FULL_TIME


def test_falls_back_to_adapter_default() -> None:
    assert (
        normalize_job_type(None, "Barista", "Make great coffee.", default=JobType.PART_TIME)
        == JobType.PART_TIME
    )
