from enum import StrEnum


class RateType(StrEnum):
    MIN_WAGE = "min_wage"
    OVERTIME_THRESHOLD_HOURS = "overtime_threshold_hours"
    OVERTIME_RATE_TIER1_PCT = "overtime_rate_tier1_pct"
    NIGHT_BONUS = "night_bonus"
    SUNDAY_BONUS_PCT = "sunday_bonus_pct"
