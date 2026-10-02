"""Curated skills that student, graduate and everyday UK jobs ask for, with common aliases.

Each canonical skill maps to regex alternatives matched on word boundaries. The list
favours what part-time, graduate and internship adverts actually mention rather than an
exhaustive tech taxonomy.
"""

import re

SKILL_ALIASES: dict[str, tuple[str, ...]] = {
    # Customer-facing, hospitality and retail
    "customer service": (r"customer service", r"customer[- ]facing", r"customer care",
                         r"customer experience", r"(serv|help|assist)(ed|ing) customers"),
    "cash handling": (r"cash handling", r"handling cash", r"\btills?\b", r"\bepos\b",
                      r"cash register"),
    "barista": (r"barista", r"coffee making", r"espresso"),
    "food hygiene": (r"food hygiene", r"food safety", r"food handling"),
    "stock management": (r"stock (management|control|replenishment)", r"merchandising",
                         r"stocktak(e|ing)", r"inventory"),
    "sales": (r"\bsales\b", r"selling", r"upsell(ing)?"),
    "hospitality": (r"hospitality", r"front of house", r"waiting staff", r"bar work"),
    # Logistics and driving
    "driving licence": (r"driving licen[cs]e", r"full uk licen[cs]e", r"\bdriver\b"),
    "delivery": (r"deliver(y|ies)", r"courier"),
    "warehouse": (r"warehouse", r"picking and packing", r"forklift"),
    # Education and care
    "tutoring": (r"tutor(ing)?", r"mentor(ing)?"),
    "teaching": (r"teaching", r"classroom", r"lesson planning"),
    "childcare": (r"childcare", r"early years", r"nursery"),
    "safeguarding": (r"safeguarding", r"\bdbs\b"),
    # Office and admin
    "administration": (r"administrat(ion|ive)", r"\badmin\b", r"data entry", r"filing"),
    "microsoft office": (r"microsoft office", r"ms office", r"microsoft word", r"powerpoint",
                         r"outlook"),
    "excel": (r"excel", r"spreadsheets?"),
    "scheduling": (r"scheduling", r"diary management", r"\brotas?\b"),
    "crm": (r"\bcrm\b", r"salesforce", r"hubspot"),
    # Transferable skills
    "communication": (r"communication", r"communicat(e|ing)", r"interpersonal"),
    "teamwork": (r"team ?work", r"team player", r"collaborat(e|ion|ive)",
                 r"(in|as part of|within) a team"),
    "leadership": (r"leadership", r"supervis(e|ing|or)", r"team lead(er)?"),
    "time management": (r"time management", r"prioriti[sz](e|ing|ation)",
                        r"meet(ing)? deadlines"),
    "problem solving": (r"problem[- ]solving", r"troubleshoot(ing)?"),
    "attention to detail": (r"attention to detail", r"detail[- ]oriented", r"accuracy"),
    "project management": (r"project management", r"managing projects", r"\bagile\b",
                           r"\bscrum\b"),
    "research": (r"\bresearch\b", r"literature review"),
    "presentation": (r"presentations?", r"public speaking"),
    "languages": (r"bilingual", r"multilingual", r"fluent in", r"mandarin", r"cantonese",
                  r"hindi", r"arabic", r"spanish", r"french", r"german", r"urdu", r"bengali"),
    # Marketing and business
    "marketing": (r"marketing", r"campaigns?"),
    "social media": (r"social media", r"instagram", r"tiktok", r"linkedin"),
    "content writing": (r"copywriting", r"content (writing|creation)", r"blog(ging)?"),
    "data analysis": (r"data analy(sis|tics|st)", r"analy[sz](e|ing) data", r"insights"),
    "financial analysis": (r"financial (analysis|modell?ing)", r"forecasting", r"budgeting"),
    "accounting": (r"accounting", r"bookkeeping", r"accounts payable", r"reconciliation"),
    # Technical
    "python": (r"python",),
    "sql": (r"\bsql\b", r"postgres(ql)?", r"mysql"),
    "javascript": (r"javascript", r"\bjs\b", r"typescript", r"node\.?js"),
    "react": (r"\breact\b",),
    "java": (r"\bjava\b",),
    "c++": (r"c\+\+",),
    "git": (r"\bgit\b", r"github", r"version control"),
    "cloud": (r"\baws\b", r"azure", r"google cloud", r"\bgcp\b"),
    "machine learning": (r"machine learning", r"\bml\b", r"deep learning", r"\bai\b"),
    "statistics": (r"statistic(s|al)", r"\br\b programming", r"regression"),
    "power bi": (r"power ?bi", r"tableau", r"dashboards?"),
}  # fmt: skip

_COMPILED: dict[str, re.Pattern[str]] = {
    skill: re.compile("|".join(f"(?:{alias})" for alias in aliases), re.I)
    for skill, aliases in SKILL_ALIASES.items()
}


def skills_in_order(text: str) -> list[str]:
    """Canonical skills in ``text``, ordered by first mention.

    Adverts tend to lead with what matters most, so order is a cheap importance signal.
    """
    positions = {
        skill: match.start()
        for skill, pattern in _COMPILED.items()
        if (match := pattern.search(text))
    }
    return sorted(positions, key=lambda skill: (positions[skill], skill))


def find_skills(text: str) -> set[str]:
    """Canonical skills mentioned anywhere in ``text``."""
    return set(skills_in_order(text))
