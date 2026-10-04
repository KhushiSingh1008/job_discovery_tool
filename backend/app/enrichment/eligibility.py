"""Eligibility tags: what a listing says about who may apply.

For an international student the key questions are "can I do this on a Student visa?"
and, for graduate roles, "will they sponsor me?". Rules are checked in priority order:
an explicit restriction outranks a positive signal elsewhere in the same text.
"""

import re

from app.models import EligibilityTag

_RULES: tuple[tuple[EligibilityTag, re.Pattern[str]], ...] = (
    (
        EligibilityTag.UK_CITIZENS_ONLY,
        re.compile(
            r"(british|uk) (citizens?|nationals?) only|must be a (british|uk) "
            r"(citizen|national)|\b(sc|dv) clearance|security clearance|sole uk national",
            re.I,
        ),
    ),
    (
        # Student visa holders may not be self-employed, whatever else the advert says.
        EligibilityTag.SELF_EMPLOYED,
        re.compile(
            r"\bas a freelancer\b|freelance (basis|role|position|contract|work)|"
            r"self[- ]employ(ed|ment)|independent contractor|contractor basis",
            re.I,
        ),
    ),
    (
        # Explicit "no sponsorship" beats any generic mention of sponsorship.
        EligibilityTag.RIGHT_TO_WORK_REQUIRED,
        re.compile(
            r"(cannot|can't|unable to|not able to|do not|don't|will not|won't|does not) "
            r"(offer |provide |currently )?(visa )?sponsor|"
            r"no (company |visa )?sponsorship|"
            r"without (the need for )?(visa )?sponsorship|"
            r"sponsorship (is )?not (available|offered|provided|possible)",
            re.I,
        ),
    ),
    (
        EligibilityTag.SPONSORSHIP_AVAILABLE,
        re.compile(
            r"visa sponsorship (is )?(available|provided|offered|possible)|"
            r"(we|can|will|able to) (can |will )?sponsor|skilled worker (visa|sponsorship)|"
            r"certificate of sponsorship",
            re.I,
        ),
    ),
    (
        EligibilityTag.STUDENT_FRIENDLY,
        re.compile(
            r"students? (welcome|friendly)|ideal for students|suitable for students|"
            r"around (your )?(studies|lectures|university|classes)|term[- ]time|"
            r"international students|flexible (hours|shifts)|\bstudent jobs?\b|"
            r"(current|university|undergraduate) students?\b|"
            r"(starting point|opportunity|perfect) for students|students and graduates",
            re.I,
        ),
    ),
    (
        EligibilityTag.RIGHT_TO_WORK_REQUIRED,
        re.compile(
            r"right to work in the (uk|u\.k\.|united kingdom)|"
            r"(eligible|eligibility|authori[sz]ed|permitted) to work in the (uk|u\.k\.|"
            r"united kingdom)|right to work (documents|information|checks?)",
            re.I,
        ),
    ),
)


def tag_eligibility(title: str, description: str) -> EligibilityTag:
    text = f"{title}\n{description}"
    for tag, pattern in _RULES:
        if pattern.search(text):
            return tag
    return EligibilityTag.UNKNOWN
