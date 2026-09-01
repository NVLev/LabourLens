from enum import StrEnum


class RateType(StrEnum):
    """
    Единственное легальное место для завода новых rate_type.
    Строки здесь должны совпадать 1:1 с тем, что реально пишется в tes_rates.rate_type —
    как через extractor'ы (используют .value), так и через ручные SQL-вставки
    (сверяться с этим enum перед тем, как придумывать новое имя).
    """

    # min_wage
    MIN_WAGE = "min_wage"

    # overtime — три строки на каждый (rate_type_context: vuorokautinen / viikoittainen / jaksotyo_Nvk)
    OVERTIME_RATE_TIER1_HOURS = "overtime_rate_tier1_hours"
    OVERTIME_RATE_TIER1_PCT = "overtime_rate_tier1_pct"
    OVERTIME_RATE_TIER2_PCT = "overtime_rate_tier2_pct"

    # night_and_sunday_work — одна строка, режим (sunnuntai/lauantai/aatto/ilta/yo) через rate_type_context
    NIGHT_SUNDAY_RATE_PCT = "night_sunday_rate_pct"

    # manual: holiday_pay
    HOLIDAY_PAY_COMPENSATION_PCT = "holiday_pay_compensation_pct"

    # manual: wages
    WAGE_REDUCTION_MIN_PCT = "wage_reduction_min_pct"
    WAGE_REDUCTION_MAX_PCT = "wage_reduction_max_pct"

    # manual: working_hours
    CALLOUT_PAY_EUR = "callout_pay_eur"
