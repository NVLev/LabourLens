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
    OVERTIME_RATE_TIER1_PCT = "overtime_rate_tier1_pct" # первые N часов по одной ставке (%)
    OVERTIME_RATE_TIER2_PCT = "overtime_rate_tier2_pct" # следующие часы по другой ставке (%)

    # night_and_sunday_work — одна строка, режим (sunnuntai/lauantai/aatto/ilta/yo) через rate_type_context
    NIGHT_SUNDAY_RATE_PCT = "night_sunday_rate_pct"

    # manual: holiday_pay
    HOLIDAY_PAY_COMPENSATION_PCT = "holiday_pay_compensation_pct"

    # manual: wages
    WAGE_REDUCTION_MIN_PCT = "wage_reduction_min_pct"
    WAGE_REDUCTION_MAX_PCT = "wage_reduction_max_pct"

    # manual: working_hours
    CALLOUT_PAY_EUR = "callout_pay_eur"

    # expense_reimbursement
    DAILY_ALLOWANCE_FULL_EUR = "daily_allowance_full_eur"  # kokopäiväraha
    DAILY_ALLOWANCE_PART_EUR = "daily_allowance_part_eur"  # osapäiväraha
    MEAL_COMPENSATION_EUR = (
        "meal_compensation_eur"  # ateriakorvaus (два tier'а через context)
    )
    NIGHT_TRAVEL_ALLOWANCE_EUR = "night_travel_allowance_eur"  # yömatkaraha
    CLOTHING_MAINTENANCE_EUR = "clothing_maintenance_eur"  # vaatetuksen huolto

    # sick_leave
    SICK_PAY_TIER1_PCT = "sick_pay_tier1_pct"  # первые дни — всегда 100%, пишем явно для симметрии с tier2
    SICK_PAY_TIER1_DAYS = "sick_pay_tier1_days"  # Первые дни по одной ставке unit="days"
    SICK_PAY_TIER2_DAYS = "sick_pay_tier2_days"  # Последующие по другой unit="days"
    SICK_PAY_TIER2_PCT = "sick_pay_tier2_pct"  # доля оплаты после первых дней - unit="pct", ⅔ → 66.67
    # после tier2 может пойти ещё до 125 дней той же ⅔-ставки. Но слово harkinnan mukaan
    # ("по усмотрению работодателя") — ключевое: это не гарантированное право работника,
    # как tier1/tier2, а дискреционная возможность.
    SICK_PAY_TIER3_DISCRETIONARY_DAYS = "sick_pay_tier3_discretionary_days"  # unit="days"
    # альтернативный сценарий, который срабатывает вместо tier1/tier2, если стаж недостаточный
    SICK_PAY_SHORT_TENURE_DAYS = "sick_pay_short_tenure_days"  # unit="days", единственный tier, full pay
    SICK_PAY_SHORT_TENURE_PCT = "sick_pay_short_tenure_pct"  # тоже всегда 100%, пишем явно для консистентности
