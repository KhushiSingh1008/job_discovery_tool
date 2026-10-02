from datetime import date

from app.rules import load_wage_rules


def test_rates_in_force_on_a_date() -> None:
    rules = load_wage_rules()

    assert rules.on(date(2026, 3, 31)).age_21_plus == 12.21
    assert rules.on(date(2026, 4, 1)).age_21_plus == 12.71
    assert rules.on(date(2020, 1, 1)).effective_from == date(2025, 4, 1)  # earliest known


def test_legal_floor_is_lowest_rate() -> None:
    assert load_wage_rules().on(date(2026, 10, 2)).legal_floor == 8.00
