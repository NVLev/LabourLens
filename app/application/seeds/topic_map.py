from typing import TypedDict


class SectionRef(TypedDict):
    act: str
    chapter: int
    section: int
    relevance: int  # 1=упоминает, 2=основной, 3=ключевой


class TopicSeed(TypedDict):
    key: str
    name_en: str
    name_ru: str
    description: str
    section_refs: list[SectionRef]


TOPICS: list[TopicSeed] = [
    # ── ТРУДОВОЙ ДОГОВОР ─────────────────────────────────────
    {
        "key": "contract_types",
        "name_en": "Employment contract types",
        "name_ru": "Виды трудовых договоров",
        "description": "Permanent vs fixed-term contracts, form and duration",
        "section_refs": [
            {"act": "tyosopimuslaki", "chapter": 1, "section": 3, "relevance": 3},
            {"act": "tyosopimuslaki", "chapter": 1, "section": 4, "relevance": 2},
        ],
    },
    {
        "key": "probation_period",
        "name_en": "Probation period",
        "name_ru": "Испытательный срок",
        "description": "Trial period conditions, maximum duration, termination during trial",
        "section_refs": [
            {"act": "tyosopimuslaki", "chapter": 1, "section": 4, "relevance": 3},
        ],
    },
    {
        "key": "employer_obligations",
        "name_en": "Employer obligations",
        "name_ru": "Обязанности работодателя",
        "description": "General obligations: pay, safe working conditions, information duty",
        "section_refs": [
            {"act": "tyosopimuslaki", "chapter": 2, "section": 1, "relevance": 3},
            {"act": "tyosopimuslaki", "chapter": 2, "section": 2, "relevance": 2},
            {"act": "tyosopimuslaki", "chapter": 2, "section": 3, "relevance": 2},
        ],
    },
    {
        "key": "employee_obligations",
        "name_en": "Employee obligations",
        "name_ru": "Обязанности работника",
        "description": "Duty to work, loyalty, non-compete during employment",
        "section_refs": [
            {"act": "tyosopimuslaki", "chapter": 3, "section": 1, "relevance": 3},
            {"act": "tyosopimuslaki", "chapter": 3, "section": 2, "relevance": 2},
            {"act": "tyosopimuslaki", "chapter": 3, "section": 3, "relevance": 2},
        ],
    },
    # ── РАБОЧЕЕ ВРЕМЯ ────────────────────────────────────────
    {
        "key": "working_hours",
        "name_en": "Working hours",
        "name_ru": "Рабочее время",
        "description": "Regular working hours, maximum limits, flexible arrangements",
        "section_refs": [
            {"act": "tyoaikalaki", "chapter": 2, "section": 3, "relevance": 3},
            {"act": "tyoaikalaki", "chapter": 2, "section": 4, "relevance": 2},
        ],
    },
    {
        "key": "overtime",
        "name_en": "Overtime work and compensation",
        "name_ru": "Сверхурочная работа",
        "description": "Overtime limits, required consent, compensation rates",
        "section_refs": [
            {"act": "tyoaikalaki", "chapter": 5, "section": 16, "relevance": 3},
            {"act": "tyoaikalaki", "chapter": 5, "section": 17, "relevance": 2},
            {"act": "tyoaikalaki", "chapter": 5, "section": 18, "relevance": 2},
            {"act": "tyoaikalaki", "chapter": 5, "section": 20, "relevance": 3},
        ],
    },
    {
        "key": "night_and_sunday_work",
        "name_en": "Night work and Sunday work",
        "name_ru": "Ночная работа и работа в воскресенье",
        "description": "Conditions for night shifts, Sunday premium pay",
        "section_refs": [
            {"act": "tyoaikalaki", "chapter": 3, "section": 8, "relevance": 3},
            {"act": "tyoaikalaki", "chapter": 5, "section": 20, "relevance": 3},
            {"act": "tyoaikalaki", "chapter": 5, "section": 21, "relevance": 2},
        ],
    },
    {
        "key": "working_hours_reduction",
        "name_en": "Working hours reduction (Pekkas)",
        "name_ru": "Сокращение рабочего времени (пеккасы)",
        "description": "Statutory and TES-based annual working hours reduction days",
        "section_refs": [
            {"act": "tyoaikalaki", "chapter": 2, "section": 3, "relevance": 2},
        ],
    },
    # ── ОТПУСК ───────────────────────────────────────────────
    {
        "key": "annual_leave",
        "name_en": "Annual leave",
        "name_ru": "Ежегодный отпуск",
        "description": "Leave accrual, minimum entitlement, timing of leave",
        "section_refs": [
            {"act": "vuosilomalaki", "chapter": 1, "section": 2, "relevance": 2},
            {"act": "vuosilomalaki", "chapter": 2, "section": 5, "relevance": 3},
            {"act": "vuosilomalaki", "chapter": 2, "section": 6, "relevance": 3},
        ],
    },
    {
        "key": "holiday_pay",
        "name_en": "Holiday pay calculation",
        "name_ru": "Расчёт отпускных",
        "description": "How holiday pay is calculated based on salary type",
        "section_refs": [
            {"act": "vuosilomalaki", "chapter": 3, "section": 9, "relevance": 3},
            {"act": "vuosilomalaki", "chapter": 3, "section": 10, "relevance": 3},
            {"act": "vuosilomalaki", "chapter": 3, "section": 11, "relevance": 2},
        ],
    },
    # ── БОЛЬНИЧНЫЙ ───────────────────────────────────────────
    {
        "key": "sick_leave",
        "name_en": "Sick leave and pay",
        "name_ru": "Больничный",
        "description": "Sick pay obligation, waiting day (karenssi), notification duty",
        "section_refs": [
            {"act": "tyosopimuslaki", "chapter": 2, "section": 11, "relevance": 3},
        ],
    },
    # ── УВОЛЬНЕНИЕ ───────────────────────────────────────────
    {
        "key": "dismissal_grounds",
        "name_en": "Grounds for dismissal",
        "name_ru": "Основания для увольнения",
        "description": "Valid grounds for termination: personal reasons vs financial/production",
        "section_refs": [
            {"act": "tyosopimuslaki", "chapter": 7, "section": 1, "relevance": 3},
            {"act": "tyosopimuslaki", "chapter": 7, "section": 2, "relevance": 3},
            {"act": "tyosopimuslaki", "chapter": 7, "section": 3, "relevance": 2},
        ],
    },
    {
        "key": "notice_period",
        "name_en": "Notice period",
        "name_ru": "Срок уведомления об увольнении",
        "description": "Notice periods by length of employment, both employer and employee",
        "section_refs": [
            {"act": "tyosopimuslaki", "chapter": 6, "section": 3, "relevance": 3},
            {"act": "tyosopimuslaki", "chapter": 6, "section": 4, "relevance": 2},
        ],
    },
    {
        "key": "dismissal_protection",
        "name_en": "Dismissal protection",
        "name_ru": "Защита от увольнения",
        "description": "Protected employees: pregnant, parental leave, union representatives",
        "section_refs": [
            {"act": "tyosopimuslaki", "chapter": 7, "section": 9, "relevance": 3},
            {"act": "tyosopimuslaki", "chapter": 7, "section": 10, "relevance": 3},
            {"act": "tyosopimuslaki", "chapter": 7, "section": 11, "relevance": 2},
        ],
    },
    {
        "key": "layoff",
        "name_en": "Temporary layoff (lomautus)",
        "name_ru": "Временное увольнение (ломаутус)",
        "description": "Employer right to temporarily lay off, notice, duration",
        "section_refs": [
            {"act": "tyosopimuslaki", "chapter": 5, "section": 1, "relevance": 2},
            {"act": "tyosopimuslaki", "chapter": 5, "section": 2, "relevance": 3},
            {"act": "tyosopimuslaki", "chapter": 5, "section": 4, "relevance": 3},
        ],
    },
    # ── ЗАРПЛАТА И КОМПЕНСАЦИИ──────────────────────────────────────
    {
        "key": "min_wage",
        "name_en": "Minimum wage by sector",
        "name_ru": "Минимальная зарплата по отрасли",
        "description": "Sector-specific minimum wages set by collective agreements (TES). "
        "Finland has no statutory national minimum wage.",
        "section_refs": [],
    },
    {
        "key": "wages",
        "name_en": "Wages and salary",
        "name_ru": "Заработная плата",
        "description": "Wage payment rules, pay periods, salary structure in TES",
        "section_refs": [
            {"act": "tyosopimuslaki", "chapter": 2, "section": 1, "relevance": 2},
        ],
    },
    {
        "key": "expense_reimbursement",
        "name_en": "Expense reimbursement",
        "name_ru": "Компенсация расходов",
        "description": "Travel expenses, daily allowances, tools, phone, work clothing provided or reimbursed by employer",
        "section_refs": [],
    },
    # ── ОСОБЫЕ СИТУАЦИИ ──────────────────────────────────────
    {
        "key": "parental_leave",
        "name_en": "Parental and family leave",
        "name_ru": "Декретный и семейный отпуск",
        "description": "Maternity, paternity, parental leave rights and job protection",
        "section_refs": [
            {"act": "tyosopimuslaki", "chapter": 4, "section": 1, "relevance": 3},
            {"act": "tyosopimuslaki", "chapter": 4, "section": 2, "relevance": 2},
            {"act": "tyosopimuslaki", "chapter": 7, "section": 9, "relevance": 2},
        ],
    },
    {
        "key": "discrimination",
        "name_en": "Discrimination at work",
        "name_ru": "Дискриминация на работе",
        "description": "Prohibited grounds for discrimination, equal treatment obligation",
        "section_refs": [
            {"act": "tyosopimuslaki", "chapter": 2, "section": 2, "relevance": 3},
            {"act": "tyoturvallisuuslaki", "chapter": 2, "section": 8, "relevance": 2},
        ],
    },
    {
        "key": "workplace_safety",
        "name_en": "Workplace safety",
        "name_ru": "Безопасность на рабочем месте",
        "description": "Employer duty to ensure safe working conditions",
        "section_refs": [
            {"act": "tyoturvallisuuslaki", "chapter": 2, "section": 8, "relevance": 3},
            {"act": "tyoturvallisuuslaki", "chapter": 2, "section": 10, "relevance": 2},
            {"act": "tyoturvallisuuslaki", "chapter": 2, "section": 14, "relevance": 2},
        ],
    },
    {
        "key": "warning",
        "name_en": "Written warning",
        "name_ru": "Письменное предупреждение",
        "description": "Conditions and procedure for issuing a formal warning",
        "section_refs": [
            {"act": "tyosopimuslaki", "chapter": 7, "section": 2, "relevance": 2},
        ],
    },
    {
        "key": "work_certificate",
        "name_en": "Work certificate",
        "name_ru": "Трудовая справка",
        "description": "Employer obligation to provide work certificate upon request",
        "section_refs": [
            {"act": "tyosopimuslaki", "chapter": 6, "section": 7, "relevance": 3},
        ],
    },
    # ── РАБОТА С ПРОФСОЮЗОМ, ДРУГИЕ ДОГОВОРЫ ──────────────────────────────────────
    {
        "key": "shop_steward",
        "name_en": "Shop steward (luottamusmies)",
        "name_ru": "Профсоюзный представитель",
        "description": "Election, rights, duties and protection of workplace union representatives",
        "section_refs": [
            {"act": "tyosopimuslaki", "chapter": 7, "section": 10, "relevance": 2},
        ],
    },
    {
        "key": "safety_representative",
        "name_en": "Workplace safety representative",
        "name_ru": "Уполномоченный по охране труда",
        "description": "Election and rights of työsuojeluvaltuutettu",
        "section_refs": [
            {"act": "tyoturvallisuuslaki", "chapter": 2, "section": 10, "relevance": 2},
        ],
    },
    {
        "key": "local_agreement",
        "name_en": "Local agreement",
        "name_ru": "Местное соглашение",
        "description": "Workplace-level agreements that deviate from TES defaults",
        "section_refs": [],
    },
]

TOPIC_LABELS: dict[str, str] = {
    # Contract & basics
    "contract_types": "Contract types",
    "probation_period": "Probation period",
    "employer_obligations": "Employer obligations",
    "employee_obligations": "Employee obligations",
    # Work hours
    "working_hours": "Working hours",
    "overtime": "Overtime",
    "night_and_sunday_work": "Night & Sunday work",
    "working_hours_reduction": "Hours reduction (Pekkas)",
    # Leave
    "annual_leave": "Annual leave",
    "holiday_pay": "Holiday pay",
    "parental_leave": "Parental & family leave",
    # Pay
    "wages": "Wages & salary",
    "min_wage": "Minimum wage",
    "expense_reimbursement": "Expense reimbursement",
    # Dismissal
    "dismissal_grounds": "Grounds for dismissal",
    "notice_period": "Notice period",
    "dismissal_protection": "Dismissal protection",
    "layoff": "Temporary layoff",
    # Workplace
    "sick_leave": "Sick leave & pay",
    "workplace_safety": "Workplace safety",
    "discrimination": "Discrimination",
    "warning": "Written warning",
    "work_certificate": "Work certificate",
    # Union & agreements
    "shop_steward": "Shop steward",
    "safety_representative": "Safety representative",
    "local_agreement": "Local agreement",
}

TOPIC_CATEGORIES: list[tuple[str, list[str]]] = [
    ("📄 Contract & basics", [
        "contract_types",
        "probation_period",
        "employer_obligations",
        "employee_obligations",
    ]),
    ("⏰ Work hours", [
        "working_hours",
        "overtime",
        "night_and_sunday_work",
        "working_hours_reduction",
    ]),
    ("🏖️ Leave", [
        "annual_leave",
        "holiday_pay",
        "parental_leave",
    ]),
    ("💰 Pay", [
        "wages",
        "min_wage",
        "expense_reimbursement",
    ]),
    ("⚖️ Dismissal", [
        "dismissal_grounds",
        "notice_period",
        "dismissal_protection",
        "layoff",
    ]),
    ("🏢 Workplace", [
        "sick_leave",
        "workplace_safety",
        "discrimination",
        "warning",
        "work_certificate",
    ]),
    ("🤝 Union & agreements", [
        "shop_steward",
        "safety_representative",
        "local_agreement",
    ]),
]
