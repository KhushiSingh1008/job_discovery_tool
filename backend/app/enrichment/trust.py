"""Job trust score: 0-100 with plain-language reasons, from data the scraper already has.

International students are frequent targets of job scams and waste scarce time on dead
listings. Every signal here is explainable to the student ("pay is below the legal
minimum"), and the score is simply a neutral baseline plus each signal's impact.
"""

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date
from urllib.parse import urlsplit

from app.models import Listing, TrustFlag
from app.rules import WageRules

BASELINE = 60
RECENT_DAYS = 7
STALE_DAYS = 7

# Hosted applicant-tracking systems: a company's board lives under its own path.
ATS_HOSTS = ("greenhouse.io", "lever.co", "workable.com", "teamtailor.com", "ashbyhq.com")
_GENERIC_NAME_WORDS = frozenset(
    {"the", "and", "ltd", "limited", "plc", "inc", "llc", "llp", "group", "company", "co",
     "university", "of", "uk", "services", "gmbh", "holdings", "international"}
)  # fmt: skip
_GENERIC_HOST_LABELS = frozenset(
    {"www", "com", "org", "net", "gov", "jobs", "job", "careers", "apply", "boards"}
)

# Asking the applicant for money, or moving the conversation off-platform.
_SCAM_PHRASES = re.compile(
    r"registration fee|training fee|pay for (your )?training|upfront (payment|fee)|"
    r"investment required|deposit required|pay to apply|application fee|"
    r"send (us )?your bank details|whats\s?app|telegram|crypto(currency)?|"
    r"starter kit|no interview",
    re.I,
)
# Income claims typical of survey panels and get-rich offers rather than employment.
_HYPE_PHRASES = re.compile(
    r"earn (up to )?£\s?\d|earn (extra )?(money|cash)|get paid to|unlimited earning|"
    r"be your own boss|cash daily|passive income",
    re.I,
)

Signal = Callable[[Listing, date, WageRules, int], Iterable[TrustFlag]]


@dataclass(frozen=True, slots=True)
class TrustResult:
    score: int
    flags: list[TrustFlag]


def _name_tokens(employer: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", employer.casefold())
    return [w for w in words if len(w) >= 3 and w not in _GENERIC_NAME_WORDS]


def _host_matches_employer(host: str, tokens: list[str]) -> bool:
    labels = [label for label in host.split(".") if len(label) >= 3]
    labels = [label for label in labels if label not in _GENERIC_HOST_LABELS]
    # "cam.ac.uk" matches "Cambridge": a host label may be an abbreviation of the name.
    return any(t in host or any(t.startswith(label) for label in labels) for t in tokens)


def employer_site_signal(listing: Listing, *_: object) -> Iterable[TrustFlag]:
    parts = urlsplit(listing.url)
    host = (parts.hostname or "").casefold()
    tokens = _name_tokens(listing.employer)

    if not listing.employer.strip():
        yield TrustFlag(code="employer_unnamed", message="The employer is not named.", impact=-15)
    elif any(host.endswith(ats) for ats in ATS_HOSTS):
        if any(t in parts.path.casefold() for t in tokens):
            yield TrustFlag(
                code="employer_careers_board",
                message="Posted on the employer's own careers board.",
                impact=10,
            )
    elif tokens and _host_matches_employer(host, tokens):
        yield TrustFlag(
            code="employer_own_site",
            message="Posted on the employer's own website.",
            impact=15,
        )
    else:
        yield TrustFlag(
            code="third_party_board",
            message="Listed on a third-party job board; check the employer independently.",
            impact=0,
        )


def pay_disclosure_signal(listing: Listing, *_: object) -> Iterable[TrustFlag]:
    if listing.pay_hourly is not None:
        yield TrustFlag(code="pay_disclosed", message="Pay is stated clearly.", impact=10)
    else:
        yield TrustFlag(
            code="pay_vague",
            message="Pay is not stated or is vague (e.g. 'To be determined').",
            impact=-10,
        )


def minimum_wage_signal(
    listing: Listing, today: date, wages: WageRules, _: int
) -> Iterable[TrustFlag]:
    if listing.pay_hourly is None:
        return
    rates = wages.on(listing.posted_date)
    pay = listing.pay_hourly
    if pay < rates.legal_floor:
        yield TrustFlag(
            code="pay_below_legal_minimum",
            message=(
                f"Pay of £{pay:.2f}/hour is below the legal minimum for any worker "
                f"(£{rates.legal_floor:.2f}/hour)."
            ),
            impact=-35,
        )
    elif pay < rates.age_21_plus and "apprentic" not in listing.title.casefold():
        yield TrustFlag(
            code="pay_below_living_wage",
            message=(
                f"Pay of £{pay:.2f}/hour is below the National Living Wage for 21+ "
                f"(£{rates.age_21_plus:.2f}/hour); only legal for under-21s or apprentices."
            ),
            impact=-15,
        )


def phrase_signal(listing: Listing, *_: object) -> Iterable[TrustFlag]:
    text = f"{listing.title}\n{listing.description}"
    scam = sorted({m.group(0).lower() for m in _SCAM_PHRASES.finditer(text)})
    if scam:
        yield TrustFlag(
            code="scam_phrases",
            message=f"Contains phrases common in job scams: {', '.join(scam)}.",
            impact=-20 * min(len(scam), 2),
        )
    if _HYPE_PHRASES.search(text):
        yield TrustFlag(
            code="income_claims",
            message="Advertises earnings ('earn money', 'get paid to') rather than a job.",
            impact=-10,
        )


def freshness_signal(
    listing: Listing, today: date, _: WageRules, ghost_days: int
) -> Iterable[TrustFlag]:
    age = (today - listing.posted_date).days
    if age >= ghost_days:
        yield TrustFlag(
            code="ghost_job",
            message=f"Advertised for {age} days; roles open this long are often already filled.",
            impact=-15,
        )
    elif age <= RECENT_DAYS:
        yield TrustFlag(code="recently_posted", message="Posted in the last week.", impact=5)

    unseen = (today - listing.last_seen.date()).days
    if unseen >= STALE_DAYS:
        yield TrustFlag(
            code="no_longer_listed",
            message=f"Not seen on the source for {unseen} days; it may have closed.",
            impact=-10,
        )


SIGNALS: tuple[Signal, ...] = (
    employer_site_signal,
    pay_disclosure_signal,
    minimum_wage_signal,
    phrase_signal,
    freshness_signal,
)


def score_listing(
    listing: Listing, today: date, wages: WageRules, ghost_days: int = 45
) -> TrustResult:
    flags = [flag for signal in SIGNALS for flag in signal(listing, today, wages, ghost_days)]
    score = BASELINE + sum(flag.impact for flag in flags)
    return TrustResult(score=max(0, min(100, score)), flags=flags)
