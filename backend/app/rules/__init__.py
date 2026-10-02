"""Editable rule tables (minimum wage, visa work-hour caps) shipped as JSON."""

import json
from datetime import date
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel

RULES_DIR = Path(__file__).parent


class WageRates(BaseModel):
    effective_from: date
    age_21_plus: float
    age_18_20: float
    under_18: float
    apprentice: float

    @property
    def legal_floor(self) -> float:
        """The lowest hourly rate that can ever be legal (any age, apprentices included)."""
        return min(self.age_21_plus, self.age_18_20, self.under_18, self.apprentice)


class WageRules(BaseModel):
    source: str
    rates: list[WageRates]

    def on(self, day: date) -> WageRates:
        """Rates in force on ``day`` (the earliest known rates for dates before any entry)."""
        ordered = sorted(self.rates, key=lambda r: r.effective_from)
        in_force = [r for r in ordered if r.effective_from <= day]
        return in_force[-1] if in_force else ordered[0]


@lru_cache
def load_wage_rules(path: Path = RULES_DIR / "uk_wages.json") -> WageRules:
    return WageRules.model_validate(json.loads(path.read_text(encoding="utf-8")))
