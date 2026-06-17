"""
Seed-данные для FAQ правил по финскому трудовому праву.

Структура правила:
    topic_key     — ключ темы из topic_map.py
    question_en   — вопрос (уникальный ключ для upsert)
    question_ru   — вопрос на русском
    conditions    — условия срабатывания (JSONB):
                    equality:         {"employment_type": "fixed"}
                    числовой диапазон: {"tenure_months": {"lt": 12}}
                    без условий:      {} — правило срабатывает всегда
    answer_en     — ответ на английском, юридический стиль со ссылками
    answer_ru     — ответ на русском
    priority      — чем выше, тем раньше проверяется (более специфичные — выше)
    section_refs  — ссылки на параграфы законов: act + chapter + section
"""

from typing import TypedDict


class SectionRefSeed(TypedDict):
    act: str
    chapter: int
    section: int


class FaqRuleSeed(TypedDict):
    topic_key: str
    question_en: str
    question_ru: str
    conditions: dict
    answer_en: str
    answer_ru: str
    answer_fi:str
    priority: int
    section_refs: list[SectionRefSeed]
    priority: int
    section_refs: list[SectionRefSeed]

FAQ_RULES: list[FaqRuleSeed] = [

    # ══════════════════════════════════════════════════════════════════════════
    # NOTICE PERIOD (notice_period)
    # Työsopimuslaki Chapter 6 § 3 — employer's notice periods by tenure
    # Työsopimuslaki Chapter 6 § 4 — employee's notice periods
    # ══════════════════════════════════════════════════════════════════════════

    {
        "topic_key": "notice_period",
        "question_en": "What is the employer's notice period? (tenure < 1 year)",
        "question_ru": "Каков срок уведомления от работодателя? (стаж < 1 года)",
        "conditions": {"tenure_months": {"lt": 12}},
        "answer_en": (
            "Under Työsopimuslaki Chapter 6 § 3, when the employment relationship "
            "has lasted less than 1 year, the employer must give a minimum notice "
            "period of 14 days before terminating the contract."
        ),
        "answer_ru": (
            "Согласно главе 6 § 3 Закона о трудовых договорах (Työsopimuslaki), "
            "если трудовые отношения длились менее 1 года, работодатель обязан "
            "уведомить работника об увольнении не менее чем за 14 дней."
        ),
        "answer_fi": (
            "Työsopimuslain 6 luvun 3 §:n mukaan, kun työsuhde on kestänyt alle "
            "vuoden, työnantajan on irtisanomisaikana noudatettava vähintään "
            "14 päivän irtisanomisaikaa ennen työsopimuksen päättämistä."
        ),
        "priority": 50,
        "section_refs": [
            {"act": "tyosopimuslaki", "chapter": 6, "section": 3},
        ],
    },
    {
        "topic_key": "notice_period",
        "question_en": "What is the employer's notice period? (tenure 1–4 years)",
        "question_ru": "Каков срок уведомления от работодателя? (стаж 1–4 года)",
        "conditions": {"tenure_months": {"gte": 12, "lt": 48}},
        "answer_en": (
            "Under Työsopimuslaki Chapter 6 § 3, when the employment relationship "
            "has lasted from 1 year to less than 4 years, the employer must give "
            "a minimum notice period of 1 month."
        ),
        "answer_ru": (
            "Согласно главе 6 § 3 Закона о трудовых договорах, "
            "при стаже от 1 года до 4 лет работодатель обязан уведомить "
            "об увольнении не менее чем за 1 месяц."
        ),
        "answer_fi": (
            "Työsopimuslain 6 luvun 3 §:n mukaan, kun työsuhde on kestänyt "
            "vähintään vuoden mutta alle 4 vuotta, työnantajan on noudatettava "
            "vähintään 1 kuukauden irtisanomisaikaa."
        ),
        "priority": 50,
        "section_refs": [
            {"act": "tyosopimuslaki", "chapter": 6, "section": 3},
        ],
    },
    {
        "topic_key": "notice_period",
        "question_en": "What is the employer's notice period? (tenure 4–8 years)",
        "question_ru": "Каков срок уведомления от работодателя? (стаж 4–8 лет)",
        "conditions": {"tenure_months": {"gte": 48, "lt": 96}},
        "answer_en": (
            "Under Työsopimuslaki Chapter 6 § 3, when the employment relationship "
            "has lasted from 4 years to less than 8 years, the employer must give "
            "a minimum notice period of 2 months."
        ),
        "answer_ru": (
            "Согласно главе 6 § 3 Закона о трудовых договорах, "
            "при стаже от 4 до 8 лет работодатель обязан уведомить "
            "об увольнении не менее чем за 2 месяца."
        ),
        "answer_fi": (
            "Työsopimuslain 6 luvun 3 §:n mukaan, kun työsuhde on kestänyt "
            "vähintään 4 vuotta mutta alle 8 vuotta, työnantajan on noudatettava "
            "vähintään 2 kuukauden irtisanomisaikaa."
        ),
        "priority": 50,
        "section_refs": [
            {"act": "tyosopimuslaki", "chapter": 6, "section": 3},
        ],
    },
    {
        "topic_key": "notice_period",
        "question_en": "What is the employer's notice period? (tenure 8–12 years)",
        "question_ru": "Каков срок уведомления от работодателя? (стаж 8–12 лет)",
        "conditions": {"tenure_months": {"gte": 96, "lt": 144}},
        "answer_en": (
            "Under Työsopimuslaki Chapter 6 § 3, when the employment relationship "
            "has lasted from 8 years to less than 12 years, the employer must give "
            "a minimum notice period of 4 months."
        ),
        "answer_ru": (
            "Согласно главе 6 § 3 Закона о трудовых договорах, "
            "при стаже от 8 до 12 лет работодатель обязан уведомить "
            "об увольнении не менее чем за 4 месяца."
        ),
        "answer_fi": (
            "Työsopimuslain 6 luvun 3 §:n mukaan, kun työsuhde on kestänyt "
            "vähintään 8 vuotta mutta alle 12 vuotta, työnantajan on noudatettava "
            "vähintään 4 kuukauden irtisanomisaikaa."
        ),
        "priority": 50,
        "section_refs": [
            {"act": "tyosopimuslaki", "chapter": 6, "section": 3},
        ],
    },
    {
        "topic_key": "notice_period",
        "question_en": "What is the employer's notice period? (tenure ≥ 12 years)",
        "question_ru": "Каков срок уведомления от работодателя? (стаж ≥ 12 лет)",
        "conditions": {"tenure_months": {"gte": 144}},
        "answer_en": (
            "Under Työsopimuslaki Chapter 6 § 3, when the employment relationship "
            "has lasted 12 years or more, the employer must give a minimum notice "
            "period of 6 months."
        ),
        "answer_ru": (
            "Согласно главе 6 § 3 Закона о трудовых договорах, "
            "при стаже 12 лет и более работодатель обязан уведомить "
            "об увольнении не менее чем за 6 месяцев."
        ),
        "answer_fi": (
            "Työsopimuslain 6 luvun 3 §:n mukaan, kun työsuhde on kestänyt "
            "vähintään 12 vuotta, työnantajan on noudatettava vähintään "
            "6 kuukauden irtisanomisaikaa."
        ),
        "priority": 50,
        "section_refs": [
            {"act": "tyosopimuslaki", "chapter": 6, "section": 3},
        ],
    },
    {
        "topic_key": "notice_period",
        "question_en": "What is the employee's notice period?",
        "question_ru": "Каков срок уведомления от работника?",
        "conditions": {},
        "answer_en": (
            "Under Työsopimuslaki Chapter 6 § 4, the employee's notice period is "
            "14 days if the employment has lasted less than 5 years, and 1 month "
            "if the employment has lasted 5 years or more. A collective agreement "
            "(TES) applicable to the sector may provide for different notice periods."
        ),
        "answer_ru": (
            "Согласно главе 6 § 4 Закона о трудовых договорах, "
            "работник обязан уведомить работодателя об увольнении за 14 дней, "
            "если стаж менее 5 лет, и за 1 месяц, если стаж 5 лет и более. "
            "Применимый коллективный договор (TES) может устанавливать иные сроки."
        ),
        "answer_fi": (
            "Työsopimuslain 6 luvun 4 §:n mukaan työntekijän irtisanomisaika on "
            "14 päivää, jos työsuhde on kestänyt alle 5 vuotta, ja 1 kuukausi, "
            "jos työsuhde on kestänyt vähintään 5 vuotta. Alalla sovellettava "
            "työehtosopimus (TES) voi määrätä toisin."
        ),
        "priority": 10,
        "section_refs": [
            {"act": "tyosopimuslaki", "chapter": 6, "section": 4},
        ],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # PROBATION PERIOD (probation_period)
    # Työsopimuslaki Chapter 1 § 4
    # ══════════════════════════════════════════════════════════════════════════

    {
        "topic_key": "probation_period",
        "question_en": "Can a probation period be agreed for a fixed-term contract?",
        "question_ru": "Можно ли установить испытательный срок при срочном договоре?",
        "conditions": {"employment_type": "fixed"},
        "answer_en": (
            "Under Työsopimuslaki Chapter 1 § 4, a probation period may be agreed "
            "in a fixed-term contract, but it may not exceed half the duration of "
            "the contract, and in any case no more than 6 months. If the fixed-term "
            "contract is less than 8 months, the maximum probation period is "
            "proportionally shorter."
        ),
        "answer_ru": (
            "Согласно главе 1 § 4 Закона о трудовых договорах, "
            "испытательный срок при срочном договоре не может превышать половину "
            "срока договора и в любом случае не более 6 месяцев. "
            "При договоре сроком менее 8 месяцев максимальный испытательный срок "
            "сокращается пропорционально."
        ),
        "answer_fi": (
            "Työsopimuslain 1 luvun 4 §:n mukaan määräaikaiseen työsopimukseen "
            "voidaan sopia koeajasta, joka saa olla enintään puolet sopimuksen "
            "kestosta, kuitenkin enintään 6 kuukautta. Jos määräaikainen sopimus "
            "on alle 8 kuukautta, koeaika on suhteellisesti lyhyempi."
        ),
        "priority": 20,
        "section_refs": [
            {"act": "tyosopimuslaki", "chapter": 1, "section": 4},
        ],
    },
    {
        "topic_key": "probation_period",
        "question_en": "What is the maximum probation period for a permanent contract?",
        "question_ru": "Каков максимальный испытательный срок при бессрочном договоре?",
        "conditions": {"employment_type": "permanent"},
        "answer_en": (
            "Under Työsopimuslaki Chapter 1 § 4, the maximum probation period for "
            "a permanent employment contract is 6 months. A collective agreement "
            "(TES) may extend this up to 8 months if the employer arranges "
            "vocational training lasting at least 4 months during the probation "
            "period. Either party may terminate the contract during probation "
            "without giving grounds (Työsopimuslaki Chapter 1 § 4(3))."
        ),
        "answer_ru": (
            "Согласно главе 1 § 4 Закона о трудовых договорах, максимальный "
            "испытательный срок при бессрочном трудовом договоре составляет "
            "6 месяцев. Коллективный договор (TES) может увеличить его до "
            "8 месяцев, если работодатель организует профессиональное обучение "
            "продолжительностью не менее 4 месяцев. В период испытательного срока "
            "любая из сторон вправе расторгнуть договор без указания причин "
            "(глава 1 § 4(3))."
        ),
        "answer_fi": (
            "Työsopimuslain 1 luvun 4 §:n mukaan toistaiseksi voimassa olevan "
            "työsopimuksen koeaika on enintään 6 kuukautta. Työehtosopimuksella "
            "(TES) voidaan pidentää koeaika enintään 8 kuukaudeksi, jos työnantaja "
            "järjestää koeajan aikana vähintään 4 kuukautta kestävää ammatillista "
            "koulutusta. Koeaikana kumpikin osapuoli voi purkaa työsopimuksen "
            "ilmoittamatta siihen erityistä syytä (Työsopimuslain 1 luvun 4 §:n "
            "3 momentti)."
        ),
        "priority": 20,
        "section_refs": [
            {"act": "tyosopimuslaki", "chapter": 1, "section": 4},
        ],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # SICK LEAVE (sick_leave)
    # Työsopimuslaki Chapter 2 § 11
    # ══════════════════════════════════════════════════════════════════════════

    {
        "topic_key": "sick_leave",
        "question_en": "How long is sick pay paid? (tenure < 1 month)",
        "question_ru": "Как долго выплачивается больничное пособие? (стаж < 1 месяца)",
        "conditions": {"tenure_months": {"lt": 1}},
        "answer_en": (
            "Under Työsopimuslaki Chapter 2 § 11, an employee whose employment "
            "has lasted less than 1 month is not entitled to full sick pay from "
            "the employer. The employer is obliged to pay 50% of the regular wage "
            "for the period of incapacity for work. After 10 working days, the "
            "employee may be entitled to Kela sickness allowance (sairauspäiväraha)."
        ),
        "answer_ru": (
            "Согласно главе 2 § 11 Закона о трудовых договорах, работник со "
            "стажем менее 1 месяца не имеет права на полное больничное пособие "
            "от работодателя. Работодатель выплачивает 50% от обычной зарплаты "
            "за период нетрудоспособности. По истечении 10 рабочих дней работник "
            "может иметь право на пособие по болезни Kela (sairauspäiväraha)."
        ),
        "answer_fi": (
            "Työsopimuslain 2 luvun 11 §:n mukaan työntekijällä, jonka työsuhde "
            "on kestänyt alle kuukauden, ei ole oikeutta täyteen palkkaan "
            "sairausajan palkkana. Työnantaja on velvollinen maksamaan 50 % "
            "tavanomaisesta palkasta työkyvyttömyyden ajalta. 10 työpäivän jälkeen "
            "työntekijällä voi olla oikeus Kelan sairauspäivärahaan."
        ),
        "priority": 40,
        "section_refs": [
            {"act": "tyosopimuslaki", "chapter": 2, "section": 11},
        ],
    },
    {
        "topic_key": "sick_leave",
        "question_en": "How long is sick pay paid? (tenure ≥ 1 month)",
        "question_ru": "Как долго выплачивается больничное пособие? (стаж ≥ 1 месяца)",
        "conditions": {"tenure_months": {"gte": 1}},
        "answer_en": (
            "Under Työsopimuslaki Chapter 2 § 11, when the employment has lasted "
            "at least 1 month, the employer must pay full wages during incapacity "
            "for work caused by illness or accident for a maximum of 9 working days "
            "(the day of incapacity plus 8 following working days). There is no "
            "statutory waiting day (karenssi) under Finnish law; however, some "
            "collective agreements (TES) may specify a waiting day. After 9 days, "
            "the employee may apply for Kela sickness allowance."
        ),
        "answer_ru": (
            "Согласно главе 2 § 11 Закона о трудовых договорах, при стаже не "
            "менее 1 месяца работодатель обязан выплачивать полную зарплату в "
            "период нетрудоспособности по болезни или травме максимум 9 рабочих "
            "дней (день нетрудоспособности и 8 следующих рабочих дней). "
            "Законодательством не предусмотрен карентный день (karenssi), однако "
            "некоторые коллективные договоры (TES) могут его устанавливать. "
            "После 9 дней работник может подать заявку на пособие по болезни Kela."
        ),
        "answer_fi": (
            "Työsopimuslain 2 luvun 11 §:n mukaan, kun työsuhde on kestänyt "
            "vähintään kuukauden, työnantajan on maksettava täysi palkka "
            "sairauden tai tapaturman aiheuttaman työkyvyttömyyden ajalta enintään "
            "9 työpäivältä (työkyvyttömyyspäivä ja 8 sitä seuraavaa työpäivää). "
            "Laissa ei ole säädetty omavastuupäivästä (karenssi), mutta jotkin "
            "työehtosopimukset (TES) voivat määrätä siitä. 9 päivän jälkeen "
            "työntekijä voi hakea Kelan sairauspäivärahaa."
        ),
        "priority": 30,
        "section_refs": [
            {"act": "tyosopimuslaki", "chapter": 2, "section": 11},
        ],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # ANNUAL LEAVE (annual_leave)
    # Vuosilomalaki Chapter 2 § 5, § 6
    # ══════════════════════════════════════════════════════════════════════════

    {
        "topic_key": "annual_leave",
        "question_en": "How many days of annual leave do I accrue? (tenure < 1 year)",
        "question_ru": "Сколько дней отпуска я накапливаю? (стаж < 1 года)",
        "conditions": {"tenure_months": {"lt": 12}},
        "answer_en": (
            "Under Vuosilomalaki Chapter 2 § 5, an employee who has been employed "
            "for less than 1 full year in the holiday credit year "
            "(1 April – 31 March) accrues 2 weekdays of annual leave per full "
            "month of employment, giving a maximum of 24 weekdays (4 weeks) for "
            "a full holiday credit year. Weekend days and public holidays are not "
            "counted as leave days."
        ),
        "answer_ru": (
            "Согласно главе 2 § 5 Закона об отпусках (Vuosilomalaki), работник "
            "со стажем менее 1 полного года в отпускном году (1 апреля – "
            "31 марта) накапливает 2 рабочих дня отпуска за каждый полный "
            "отработанный месяц, максимум 24 рабочих дня (4 недели) за полный "
            "отпускной год. Выходные и праздничные дни в дни отпуска не входят."
        ),
        "answer_fi": (
            "Vuosilomalain 2 luvun 5 §:n mukaan työntekijä, jonka työsuhde on "
            "kestänyt alle kokonaisen vuoden lomanmääräytymisvuoden "
            "(1.4. – 31.3.) aikana, kerryttää 2 arkipäivää vuosilomaa kutakin "
            "täyttä työssäolokuukautta kohden, enintään 24 arkipäivää (4 viikkoa) "
            "täydeltä lomanmääräytymisvuodelta. Viikonloppupäivät ja yleiset "
            "vapaapäivät eivät ole lomapäiviä."
        ),
        "priority": 30,
        "section_refs": [
            {"act": "vuosilomalaki", "chapter": 2, "section": 5},
            {"act": "vuosilomalaki", "chapter": 2, "section": 6},
        ],
    },
    {
        "topic_key": "annual_leave",
        "question_en": "How many days of annual leave do I accrue? (tenure ≥ 1 year)",
        "question_ru": "Сколько дней отпуска я накапливаю? (стаж ≥ 1 года)",
        "conditions": {"tenure_months": {"gte": 12}},
        "answer_en": (
            "Under Vuosilomalaki Chapter 2 § 5, an employee who has been employed "
            "for at least 1 full year before the end of the holiday credit year "
            "(1 April – 31 March) accrues 2.5 weekdays of annual leave per full "
            "month of employment, giving a maximum of 30 weekdays (5 weeks) for "
            "a full holiday credit year. Weekend days and public holidays are not "
            "counted as leave days. A collective agreement (TES) may provide for "
            "additional leave days."
        ),
        "answer_ru": (
            "Согласно главе 2 § 5 Закона об отпусках, работник со стажем не "
            "менее 1 полного года до окончания отпускного года (31 марта) "
            "накапливает 2,5 рабочих дня за каждый полный отработанный месяц, "
            "максимум 30 рабочих дней (5 недель) за полный отпускной год. "
            "Выходные и праздничные дни в дни отпуска не входят. "
            "Коллективный договор (TES) может предусматривать дополнительные дни."
        ),
        "answer_fi": (
            "Vuosilomalain 2 luvun 5 §:n mukaan työntekijä, jonka työsuhde on "
            "kestänyt vähintään kokonaisen vuoden lomanmääräytymisvuoden "
            "(31.3.) loppuun mennessä, kerryttää 2,5 arkipäivää vuosilomaa kutakin "
            "täyttä työssäolokuukautta kohden, enintään 30 arkipäivää (5 viikkoa) "
            "täydeltä lomanmääräytymisvuodelta. Viikonloppupäivät ja yleiset "
            "vapaapäivät eivät ole lomapäiviä. Työehtosopimus (TES) voi määrätä "
            "lisälomapäivistä."
        ),
        "priority": 30,
        "section_refs": [
            {"act": "vuosilomalaki", "chapter": 2, "section": 5},
            {"act": "vuosilomalaki", "chapter": 2, "section": 6},
        ],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # HOLIDAY PAY (holiday_pay)
    # Vuosilomalaki Chapter 3 § 9, § 10, § 11
    # ══════════════════════════════════════════════════════════════════════════

    {
        "topic_key": "holiday_pay",
        "question_en": "How is holiday pay calculated for a monthly salary employee?",
        "question_ru": "Как рассчитываются отпускные для работника с месячной зарплатой?",
        "conditions": {"salary_type": "monthly"},
        "answer_en": (
            "Under Vuosilomalaki Chapter 3 § 9, for an employee with a fixed "
            "monthly salary, holiday pay equals the regular monthly salary. The "
            "salary is not reduced during annual leave. Additionally, under § 16, "
            "the employee is entitled to a holiday bonus (lomaraha) of 50% of "
            "the holiday pay, if stipulated in the applicable collective agreement "
            "(TES). The holiday bonus is not required by statute."
        ),
        "answer_ru": (
            "Согласно главе 3 § 9 Закона об отпусках, работнику с фиксированной "
            "месячной зарплатой отпускные равны обычной месячной зарплате — "
            "зарплата не уменьшается в период отпуска. Кроме того, согласно § 16, "
            "работник имеет право на отпускную надбавку (lomaraha) в размере 50% "
            "от отпускных, если это предусмотрено применимым коллективным "
            "договором (TES). Закон не обязывает выплачивать lomaraha."
        ),
        "answer_fi": (
            "Vuosilomalain 3 luvun 9 §:n mukaan työntekijälle, jolla on kiinteä "
            "kuukausipalkka, lomapalkka on tavanomainen kuukausipalkka. Palkkaa "
            "ei alenneta vuosiloman aikana. Lisäksi 16 §:n mukaan työntekijällä "
            "on oikeus lomarahaan, joka on 50 % lomapalkasta, jos se on määrätty "
            "sovellettavassa työehtosopimuksessa (TES). Lomaraha ei ole laissa "
            "säädetty pakollinen."
        ),
        "priority": 20,
        "section_refs": [
            {"act": "vuosilomalaki", "chapter": 3, "section": 9},
        ],
    },
    {
        "topic_key": "holiday_pay",
        "question_en": "How is holiday pay calculated for an hourly wage employee?",
        "question_ru": "Как рассчитываются отпускные для работника с почасовой оплатой?",
        "conditions": {"salary_type": "hourly"},
        "answer_en": (
            "Under Vuosilomalaki Chapter 3 § 10, for an employee whose wage varies "
            "(hourly, piecework etc.), holiday pay is calculated as a percentage "
            "of the total wages earned during the holiday credit year "
            "(1 April – 31 March): 9% if the employment has lasted less than 1 year, "
            "or 11.5% if the employment has lasted at least 1 year. "
            "The calculation base includes all wages but excludes overtime "
            "compensation paid in addition to the basic rate."
        ),
        "answer_ru": (
            "Согласно главе 3 § 10 Закона об отпусках, работнику с переменной "
            "оплатой труда (почасовая, сдельная и т.п.) отпускные рассчитываются "
            "как процент от общего заработка за отпускной год (1 апреля – "
            "31 марта): 9% при стаже менее 1 года или 11,5% при стаже не менее "
            "1 года. В базу расчёта включается весь заработок, но не включается "
            "надбавка за сверхурочную работу сверх базовой ставки."
        ),
        "answer_fi": (
            "Vuosilomalain 3 luvun 10 §:n mukaan työntekijälle, jonka palkka "
            "vaihtelee (tuntipalkka, urakkapalkka jne.), lomapalkka lasketaan "
            "prosenttiosuutena lomanmääräytymisvuoden (1.4. – 31.3.) aikana "
            "ansaitusta kokonaispalkasta: 9 %, jos työsuhde on kestänyt alle "
            "vuoden, tai 11,5 %, jos työsuhde on kestänyt vähintään vuoden. "
            "Laskentaperusteeseen sisältyvät kaikki palkat, mutta ei ylityökorvauksia "
            "peruspalkan lisäksi."
        ),
        "priority": 20,
        "section_refs": [
            {"act": "vuosilomalaki", "chapter": 3, "section": 10},
        ],
    },
    {
        "topic_key": "holiday_pay",
        "question_en": "What is a holiday bonus (lomaraha) and is it mandatory?",
        "question_ru": "Что такое lomaraha и обязателен ли он?",
        "conditions": {},
        "answer_en": (
            "Holiday bonus (lomaraha or lomaltapaluuraha) is not required by "
            "statute under Finnish law. It is payable only if stipulated in the "
            "collective agreement (TES) applicable to the sector. In practice, "
            "most TES provide for a holiday bonus of 50% of holiday pay, typically "
            "paid upon commencement of leave or upon return from leave. "
            "If no TES applies and no individual agreement exists, the employer "
            "is not legally obliged to pay the bonus."
        ),
        "answer_ru": (
            "Отпускная надбавка (lomaraha или lomaltapaluuraha) законодательством "
            "Финляндии не предусмотрена в качестве обязательной выплаты. "
            "Она выплачивается только в том случае, если это закреплено в "
            "применимом коллективном договоре (TES). На практике большинство TES "
            "предусматривают надбавку в размере 50% от отпускных, как правило "
            "выплачиваемую при уходе в отпуск или при выходе из него. "
            "При отсутствии TES и индивидуального соглашения работодатель не "
            "обязан её выплачивать."
        ),
        "answer_fi": (
            "Lomaraha (tai lomaltapaluuraha) ei ole Suomessa laissa säädetty "
            "pakollinen etuus. Se maksetaan vain, jos se on määrätty alalla "
            "sovellettavassa työehtosopimuksessa (TES). Käytännössä useimmat TES "
            "määräävät lomarahaksi 50 % lomapalkasta, maksettavaksi yleensä loman "
            "alkaessa tai lomalta palattaessa. Jos TES ei ole sovellettavissa eikä "
            "yksilöllistä sopimusta ole, työnantaja ei ole velvollinen maksamaan "
            "lomarahaa."
        ),
        "priority": 10,
        "section_refs": [
            {"act": "vuosilomalaki", "chapter": 3, "section": 9},
            {"act": "vuosilomalaki", "chapter": 3, "section": 11},
        ],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # LAYOFF (layoff)
    # Työsopimuslaki Chapter 5 § 2, § 4
    # ══════════════════════════════════════════════════════════════════════════

    {
        "topic_key": "layoff",
        "question_en": "Can an employee on a fixed-term contract be laid off?",
        "question_ru": "Можно ли отправить в ломаутус работника со срочным договором?",
        "conditions": {"employment_type": "fixed"},
        "answer_en": (
            "Under Työsopimuslaki Chapter 5 § 2, an employee on a fixed-term "
            "contract may only be laid off (lomautus) if this right is expressly "
            "stipulated in the applicable collective agreement (TES). Without such "
            "a provision in the TES, a fixed-term employee cannot be laid off. "
            "This differs from permanent employees, who may be laid off under the "
            "general conditions of Chapter 5 § 2."
        ),
        "answer_ru": (
            "Согласно главе 5 § 2 Закона о трудовых договорах, работник со "
            "срочным договором может быть отправлен в ломаутус только в том "
            "случае, если такое право прямо предусмотрено применимым коллективным "
            "договором (TES). При отсутствии такого положения в TES срочный "
            "работник не может быть отправлен в ломаутус. Это отличает его от "
            "постоянных работников, которые могут быть ломаутированы на общих "
            "основаниях главы 5 § 2."
        ),
        "answer_fi": (
            "Työsopimuslain 5 luvun 2 §:n mukaan määräaikaisessa työsuhteessa "
            "oleva työntekijä voidaan lomauttaa ainoastaan, jos tästä oikeudesta "
            "on nimenomaisesti määrätty sovellettavassa työehtosopimuksessa (TES). "
            "Ilman tällaista TES:n määräystä määräaikaista työntekijää ei voida "
            "lomauttaa. Tämä eroaa toistaiseksi voimassa olevista työntekijöistä, "
            "jotka voidaan lomauttaa 5 luvun 2 §:n yleisten edellytysten mukaisesti."
        ),
        "priority": 30,
        "section_refs": [
            {"act": "tyosopimuslaki", "chapter": 5, "section": 2},
        ],
    },
    {
        "topic_key": "layoff",
        "question_en": "What are the conditions and notice period for laying off a permanent employee?",
        "question_ru": "Каковы условия и срок уведомления о ломаутусе постоянного работника?",
        "conditions": {"employment_type": "permanent"},
        "answer_en": (
            "Under Työsopimuslaki Chapter 5 § 2, a permanent employee may be "
            "temporarily laid off if the employer's need for work has diminished "
            "temporarily due to financial or production-related reasons and the "
            "employer cannot reasonably arrange other work or training. "
            "Under Chapter 5 § 4, the employer must give the employee at least "
            "5 calendar days' advance notice of the layoff. The employee retains "
            "the right to terminate the contract with 7 days' notice during a "
            "layoff exceeding 90 days (Chapter 5 § 7)."
        ),
        "answer_ru": (
            "Согласно главе 5 § 2 Закона о трудовых договорах, постоянный "
            "работник может быть временно ломаутирован, если потребность "
            "работодателя в труде временно снизилась по финансовым или "
            "производственным причинам и работодатель не может разумным образом "
            "предоставить другую работу или организовать обучение. "
            "Согласно главе 5 § 4, работодатель обязан уведомить работника о "
            "ломаутусе не менее чем за 5 календарных дней. При ломаутусе "
            "продолжительностью более 90 дней работник вправе расторгнуть договор "
            "с уведомлением за 7 дней (глава 5 § 7)."
        ),
        "answer_fi": (
            "Työsopimuslain 5 luvun 2 §:n mukaan toistaiseksi voimassa oleva "
            "työntekijä voidaan lomauttaa tilapäisesti, jos työnantajan työntarve "
            "on vähentynyt tilapäisesti taloudellisista tai tuotannollisista syistä "
            "eikä työnantaja voi kohtuudella järjestää muuta työtä tai koulutusta. "
            "5 luvun 4 §:n mukaan työnantajan on ilmoitettava lomautuksesta "
            "työntekijälle vähintään 5 kalenteripäivää ennen lomautuksen alkamista. "
            "Yli 90 päivää kestäneen lomautuksen aikana työntekijällä on oikeus "
            "irtisanoutua 7 päivän irtisanomisajalla (5 luvun 7 §)."
        ),
        "priority": 20,
        "section_refs": [
            {"act": "tyosopimuslaki", "chapter": 5, "section": 2},
            {"act": "tyosopimuslaki", "chapter": 5, "section": 4},
        ],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # DISMISSAL GROUNDS (dismissal_grounds)
    # Työsopimuslaki Chapter 7 § 1, § 2, § 3
    # ══════════════════════════════════════════════════════════════════════════

    {
        "topic_key": "dismissal_grounds",
        "question_en": "Can a fixed-term employee be dismissed before the contract ends?",
        "question_ru": "Можно ли уволить срочного работника до окончания договора?",
        "conditions": {"employment_type": "fixed"},
        "answer_en": (
            "Under Työsopimuslaki Chapter 7 § 1, a fixed-term employment contract "
            "may only be terminated before its expiry date if both parties agree, "
            "or on grounds of an extremely serious breach by the employee that "
            "would justify cancellation (purku) under Chapter 8 § 1. "
            "Ordinary notice (irtisanominen) on financial or production-related "
            "grounds is not permitted for fixed-term contracts unless the right "
            "is expressly provided in the applicable collective agreement (TES)."
        ),
        "answer_ru": (
            "Согласно главе 7 § 1 Закона о трудовых договорах, срочный трудовой "
            "договор может быть расторгнут до истечения срока только по соглашению "
            "сторон или на основании грубого нарушения работником, которое "
            "позволяет расторгнуть договор в соответствии с главой 8 § 1. "
            "Обычное увольнение (irtisanominen) по финансовым или "
            "производственным причинам не допускается для срочных договоров, "
            "если иное прямо не предусмотрено применимым коллективным "
            "договором (TES)."
        ),
        "answer_fi": (
            "Työsopimuslain 7 luvun 1 §:n mukaan määräaikainen työsopimus voidaan "
            "päättää ennen sen päättymispäivää ainoastaan osapuolten yhteisellä "
            "sopimuksella tai työntekijän erittäin vakavan rikkomuksen perusteella, "
            "joka oikeuttaisi sopimuksen purkamiseen 8 luvun 1 §:n mukaisesti. "
            "Tavallinen irtisanominen taloudellisilla tai tuotannollisilla "
            "perusteilla ei ole sallittu määräaikaisissa sopimuksissa, ellei "
            "oikeudesta ole nimenomaisesti määrätty sovellettavassa "
            "työehtosopimuksessa (TES)."
        ),
        "priority": 30,
        "section_refs": [
            {"act": "tyosopimuslaki", "chapter": 7, "section": 1},
        ],
    },
    {
        "topic_key": "dismissal_grounds",
        "question_en": "What constitutes valid grounds for dismissal on personal grounds?",
        "question_ru": "Каковы законные основания для увольнения по личным причинам?",
        "conditions": {"employment_type": "permanent"},
        "answer_en": (
            "Under Työsopimuslaki Chapter 7 § 2, the employer may terminate a "
            "permanent employment contract on personal grounds only if there is a "
            "proper and weighty reason (asiallinen ja painava syy). This includes "
            "serious or repeated breach of contractual obligations, persistent "
            "neglect of work duties after a written warning, or loss of the "
            "required professional qualifications. "
            "Grounds that are not valid include illness (unless it causes a "
            "permanent and substantial reduction in work ability), participation "
            "in an industrial action, expression of opinion, or exercising "
            "statutory rights (§ 2(2))."
        ),
        "answer_ru": (
            "Согласно главе 7 § 2 Закона о трудовых договорах, работодатель "
            "вправе расторгнуть бессрочный трудовой договор по личным причинам "
            "только при наличии надлежащего и веского основания (asiallinen ja "
            "painava syy). К ним относятся: грубое или повторное нарушение "
            "договорных обязательств, систематическое неисполнение трудовых "
            "обязанностей после письменного предупреждения, утрата необходимой "
            "профессиональной квалификации. "
            "Не являются основаниями: болезнь (если только она не вызывает "
            "постоянного и существенного снижения трудоспособности), участие в "
            "трудовых спорах, выражение мнения или реализация законных прав "
            "(§ 2(2))."
        ),
        "answer_fi": (
            "Työsopimuslain 7 luvun 2 §:n mukaan työnantaja voi irtisanoa "
            "toistaiseksi voimassa olevan työsopimuksen henkilökohtaisella "
            "perusteella ainoastaan, jos siihen on asiallinen ja painava syy. "
            "Tällaisia syitä ovat muun muassa työsopimusvelvoitteiden vakava tai "
            "toistuva rikkominen, työtehtävien jatkuva laiminlyönti kirjallisen "
            "varoituksen jälkeen tai vaaditun ammatillisen pätevyyden menettäminen. "
            "Päteviä syitä eivät ole sairaus (ellei se aiheuta pysyvää ja "
            "olennaista työkyvyn alentumista), osallistuminen työtaisteluun, "
            "mielipiteen ilmaisu tai lakisääteisten oikeuksien käyttö (2 §:n 2 mom.)."
        ),
        "priority": 20,
        "section_refs": [
            {"act": "tyosopimuslaki", "chapter": 7, "section": 2},
        ],
    },
    {
        "topic_key": "dismissal_grounds",
        "question_en": "What are the conditions for dismissal on financial or production-related grounds?",
        "question_ru": "Каковы условия увольнения по финансовым или производственным причинам?",
        "conditions": {},
        "answer_en": (
            "Under Työsopimuslaki Chapter 7 § 3, the employer may terminate an "
            "employment contract on financial, production-related or restructuring "
            "grounds if the available work has permanently and substantially "
            "diminished. Dismissal is not permitted if the employer has hired or "
            "intends to hire another employee for similar tasks, or if the "
            "reduction of work is only temporary. Under § 6, the employer must "
            "re-employ the dismissed employee within 9 months (4 months if the "
            "employment lasted less than 12 years) if a vacancy in the same or "
            "similar work arises."
        ),
        "answer_ru": (
            "Согласно главе 7 § 3 Закона о трудовых договорах, работодатель "
            "вправе расторгнуть трудовой договор по финансовым, "
            "производственным причинам или в связи с реструктуризацией, если "
            "объём работы постоянно и существенно сократился. Увольнение не "
            "допускается, если работодатель принял или намерен принять другого "
            "работника на аналогичные задачи, либо если сокращение работы носит "
            "временный характер. Согласно § 6, работодатель обязан повторно "
            "трудоустроить уволенного работника в течение 9 месяцев (4 месяца "
            "при стаже менее 12 лет), если откроется вакансия на аналогичную "
            "или схожую работу."
        ),
        "answer_fi": (
            "Työsopimuslain 7 luvun 3 §:n mukaan työnantaja voi irtisanoa "
            "työsopimuksen taloudellisilla, tuotannollisilla tai "
            "uudelleenjärjestelyperusteilla, jos tarjolla oleva työ on vähentynyt "
            "pysyvästi ja olennaisesti. Irtisanominen ei ole sallittua, jos "
            "työnantaja on palkannut tai aikoo palkata toisen työntekijän "
            "vastaaviin tehtäviin tai jos työn väheneminen on tilapäistä. "
            "6 §:n mukaan työnantajan on työsuhde-etuoikeuden perusteella "
            "tarjottava irtisanotulle työntekijälle uudelleen työtä 9 kuukauden "
            "kuluessa (4 kuukautta, jos työsuhde kesti alle 12 vuotta), jos "
            "samaa tai samankaltaista työtä koskeva tehtävä avautuu."
        ),
        "priority": 10,
        "section_refs": [
            {"act": "tyosopimuslaki", "chapter": 7, "section": 3},
        ],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # DISMISSAL PROTECTION (dismissal_protection)
    # Työsopimuslaki Chapter 7 § 9, § 10, § 11
    # ══════════════════════════════════════════════════════════════════════════

    {
        "topic_key": "dismissal_protection",
        "question_en": "Is an employee on parental leave protected from dismissal?",
        "question_ru": "Защищён ли работник в декретном отпуске от увольнения?",
        "conditions": {"on_parental_leave": True},
        "answer_en": (
            "Under Työsopimuslaki Chapter 7 § 9, the employer may not terminate "
            "the contract of an employee who is pregnant or on parental leave "
            "(raskausvapaa, vanhempainvapaa) on financial or production-related "
            "grounds. Termination on personal grounds is only permitted if the "
            "employer is unaware of the pregnancy or parental leave, or if the "
            "grounds are extremely serious (comparable to cancellation under "
            "Chapter 8). The burden of proof for lack of knowledge lies "
            "with the employer."
        ),
        "answer_ru": (
            "Согласно главе 7 § 9 Закона о трудовых договорах, работодатель не "
            "вправе расторгнуть договор с работником, находящимся в состоянии "
            "беременности или в декретном отпуске (raskausvapaa, vanhempainvapaa), "
            "по финансовым или производственным основаниям. Увольнение по личным "
            "причинам допустимо лишь в том случае, если работодатель не знал о "
            "беременности или отпуске, либо если основания крайне серьёзны "
            "(сравнимы с расторжением по главе 8). Бремя доказывания отсутствия "
            "осведомлённости лежит на работодателе."
        ),
        "answer_fi": (
            "Työsopimuslain 7 luvun 9 §:n mukaan työnantaja ei saa irtisanoa "
            "raskaus- tai vanhempainvapaalla olevan työntekijän sopimusta "
            "taloudellisilla tai tuotannollisilla perusteilla. Irtisanominen "
            "henkilökohtaisilla perusteilla on sallittua ainoastaan, jos "
            "työnantaja ei ole tiennyt raskaudesta tai vanhempainvapaasta tai jos "
            "perusteet ovat erittäin vakavat (verrattavissa 8 luvun mukaiseen "
            "purkamiseen). Todistustaakka siitä, ettei työnantaja ole tiennyt, "
            "on työnantajalla."
        ),
        "priority": 30,
        "section_refs": [
            {"act": "tyosopimuslaki", "chapter": 7, "section": 9},
        ],
    },
    {
        "topic_key": "dismissal_protection",
        "question_en": "Is a shop steward (luottamusmies) protected from dismissal?",
        "question_ru": "Защищён ли профсоюзный представитель (luottamusmies) от увольнения?",
        "conditions": {"is_shop_steward": True},
        "answer_en": (
            "Under Työsopimuslaki Chapter 7 § 10, a shop steward (luottamusmies) "
            "or an elected employee representative may only be dismissed on "
            "financial or production-related grounds if their work ceases entirely "
            "and the employer cannot offer them other suitable work or arrange "
            "retraining. On personal grounds, dismissal requires the consent of "
            "the majority of the employees the representative represents. "
            "This enhanced protection applies during the term of office and for "
            "6 months thereafter."
        ),
        "answer_ru": (
            "Согласно главе 7 § 10 Закона о трудовых договорах, профсоюзный "
            "представитель (luottamusmies) или избранный представитель работников "
            "может быть уволен по финансовым или производственным причинам только "
            "в случае полного прекращения его работы при невозможности "
            "предложить другую подходящую работу или организовать переобучение. "
            "Увольнение по личным причинам требует согласия большинства "
            "работников, которых он представляет. "
            "Усиленная защита действует в течение срока полномочий и "
            "6 месяцев после его окончания."
        ),
        "answer_fi": (
            "Työsopimuslain 7 luvun 10 §:n mukaan luottamusmies tai valittu "
            "työntekijäedustaja voidaan irtisanoa taloudellisilla tai "
            "tuotannollisilla perusteilla ainoastaan, jos hänen työnsä lakkaa "
            "kokonaan eikä työnantaja voi tarjota hänelle muuta sopivaa työtä tai "
            "järjestää uudelleenkoulutusta. Henkilökohtaisilla perusteilla "
            "irtisanominen edellyttää edustettavien työntekijöiden enemmistön "
            "suostumusta. Tämä korotettu suoja on voimassa luottamusmiehen "
            "toimikauden ajan ja 6 kuukautta sen päättymisen jälkeen."
        ),
        "priority": 30,
        "section_refs": [
            {"act": "tyosopimuslaki", "chapter": 7, "section": 10},
        ],
    },
    {
        "topic_key": "dismissal_protection",
        "question_en": "What remedies are available if dismissal is found unlawful?",
        "question_ru": "Каковы средства правовой защиты при незаконном увольнении?",
        "conditions": {},
        "answer_en": (
            "Under Työsopimuslaki Chapter 7 § 11, if the employer has terminated "
            "the contract without proper grounds, the employee is entitled to "
            "compensation of a minimum of 3 months' and a maximum of 24 months' "
            "salary, taking into account the circumstances. Reinstatement is not "
            "the primary remedy under Finnish law; instead, compensation is "
            "awarded. Claims must be brought within 2 years of the termination "
            "of the employment relationship (Chapter 13 § 9)."
        ),
        "answer_ru": (
            "Согласно главе 7 § 11 Закона о трудовых договорах, если работодатель "
            "расторг договор без надлежащих оснований, работник имеет право на "
            "компенсацию в размере от 3 до 24 месячных зарплат с учётом "
            "обстоятельств дела. Восстановление на работе не является основным "
            "средством защиты по финскому праву — вместо него присуждается "
            "денежная компенсация. Требования должны быть предъявлены в течение "
            "2 лет с момента прекращения трудовых отношений (глава 13 § 9)."
        ),
        "answer_fi": (
            "Työsopimuslain 7 luvun 11 §:n mukaan, jos työnantaja on irtisanonut "
            "työsopimuksen ilman asiallista ja painavaa syytä, työntekijällä on "
            "oikeus saada vähintään 3 kuukauden ja enintään 24 kuukauden palkkaa "
            "vastaava hyvitys ottaen huomioon olosuhteet. Takaisinpalaaminen "
            "työhön ei ole Suomen lain ensisijainen oikeuskeino, vaan sen sijaan "
            "myönnetään rahallinen korvaus. Vaateet on esitettävä 2 vuoden "
            "kuluessa työsuhteen päättymisestä (13 luvun 9 §)."
        ),
        "priority": 10,
        "section_refs": [
            {"act": "tyosopimuslaki", "chapter": 7, "section": 11},
        ],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # OVERTIME (overtime)
    # Työaikalaki Chapter 5 § 16, § 17, § 18, § 20
    # ══════════════════════════════════════════════════════════════════════════

    {
        "topic_key": "overtime",
        "question_en": "What are the statutory overtime compensation rates?",
        "question_ru": "Каковы установленные законом ставки компенсации сверхурочных?",
        "conditions": {},
        "answer_en": (
            "Under Työaikalaki Chapter 5 § 20, overtime compensation is as follows: "
            "for daily overtime, the first 2 hours are compensated at 150% of the "
            "regular hourly wage, and subsequent hours at 200%. "
            "For weekly overtime (hours exceeding the agreed weekly working time "
            "that do not constitute daily overtime), the first 8 hours are "
            "compensated at 150% and subsequent hours at 200%. "
            "Under § 16, overtime requires the employee's consent for each "
            "instance, unless otherwise agreed in a collective agreement (TES). "
            "The annual maximum for overtime is 138 hours, extendable to 250 hours "
            "by a collective agreement (§ 18)."
        ),
        "answer_ru": (
            "Согласно главе 5 § 20 Закона о рабочем времени (Työaikalaki), "
            "компенсация сверхурочных осуществляется следующим образом: "
            "за ежедневные сверхурочные — первые 2 часа оплачиваются по 150% "
            "от обычной почасовой ставки, последующие часы — по 200%. "
            "За еженедельные сверхурочные (часы сверх согласованного рабочего "
            "времени, не являющиеся ежедневными сверхурочными) — первые 8 часов "
            "по 150%, последующие — по 200%. "
            "Согласно § 16, каждый случай сверхурочной работы требует согласия "
            "работника, если иное не предусмотрено коллективным договором (TES). "
            "Годовой максимум сверхурочных составляет 138 часов, "
            "который может быть увеличен до 250 часов коллективным договором (§ 18)."
        ),
        "answer_fi": (
            "Työaikalain 5 luvun 20 §:n mukaan ylityökorvaukset ovat seuraavat: "
            "päivittäisestä ylityöstä ensimmäisiltä 2 tunnilta maksetaan 150 %:a "
            "tavanomaisesta tuntipalkasta ja seuraavilta tunneilta 200 %:a. "
            "Viikoittaisesta ylityöstä (sovittua viikoittaista työaikaa ylittävät "
            "tunnit, jotka eivät ole päivittäistä ylityötä) ensimmäisiltä "
            "8 tunnilta maksetaan 150 %:a ja seuraavilta tunneilta 200 %:a. "
            "16 §:n mukaan ylityö edellyttää työntekijän suostumusta jokaista "
            "ylitystapausta kohden, ellei työehtosopimuksessa (TES) ole toisin "
            "sovittu. Ylityön vuosimaksimi on 138 tuntia, joka voidaan "
            "työehtosopimuksella pidentää 250 tuntiin (18 §)."
        ),
        "priority": 10,
        "section_refs": [
            {"act": "tyoaikalaki", "chapter": 5, "section": 16},
            {"act": "tyoaikalaki", "chapter": 5, "section": 18},
            {"act": "tyoaikalaki", "chapter": 5, "section": 20},
        ],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # PARENTAL LEAVE (parental_leave)
    # Työsopimuslaki Chapter 4 § 1, § 2
    # ══════════════════════════════════════════════════════════════════════════

    {
        "topic_key": "parental_leave",
        "question_en": "What is the right to parental leave and job protection?",
        "question_ru": "Каково право на декретный отпуск и защита рабочего места?",
        "conditions": {},
        "answer_en": (
            "Under Työsopimuslaki Chapter 4 § 1, an employee has the right to "
            "take pregnancy leave (raskausvapaa), parental leave (vanhempainvapaa) "
            "and child care leave (hoitovapaa) as provided in the Sickness Insurance "
            "Act (Sairausvakuutuslaki). The employee must notify the employer of "
            "the intended leave at least 2 months before it begins. "
            "Under Chapter 4 § 2, the employee is entitled to return to their "
            "previous position after parental leave. If this is not possible, "
            "the employer must offer work that is comparable and corresponds to "
            "the employee's professional qualifications. "
            "Under Chapter 7 § 9, dismissal during parental leave on "
            "financial/production grounds is prohibited."
        ),
        "answer_ru": (
            "Согласно главе 4 § 1 Закона о трудовых договорах, работник имеет "
            "право на отпуск по беременности (raskausvapaa), родительский отпуск "
            "(vanhempainvapaa) и отпуск по уходу за ребёнком (hoitovapaa) в "
            "соответствии с Законом о страховании по болезни (Sairausvakuutuslaki). "
            "Работник обязан уведомить работодателя о предполагаемом отпуске не "
            "менее чем за 2 месяца до его начала. "
            "Согласно главе 4 § 2, по окончании декретного отпуска работник вправе "
            "вернуться на прежнюю должность. Если это невозможно, работодатель "
            "обязан предложить сравнимую работу, соответствующую квалификации "
            "работника. Согласно главе 7 § 9, увольнение в период декретного "
            "отпуска по финансовым или производственным основаниям запрещено."
        ),
        "answer_fi": (
            "Työsopimuslain 4 luvun 1 §:n mukaan työntekijällä on oikeus "
            "raskausvapaaseen, vanhempainvapaaseen ja hoitovapaaseen "
            "sairausvakuutuslain mukaisesti. Työntekijän on ilmoitettava "
            "työnantajalle suunnitellusta vapaasta vähintään 2 kuukautta ennen "
            "sen alkamista. "
            "4 luvun 2 §:n mukaan työntekijällä on oikeus palata aikaisempaan "
            "tehtäväänsä vanhempainvapaan jälkeen. Jos tämä ei ole mahdollista, "
            "työnantajan on tarjottava verrattavaa työtä, joka vastaa työntekijän "
            "ammatillista pätevyyttä. "
            "7 luvun 9 §:n mukaan irtisanominen vanhempainvapaan aikana "
            "taloudellisilla tai tuotannollisilla perusteilla on kielletty."
        ),
        "priority": 10,
        "section_refs": [
            {"act": "tyosopimuslaki", "chapter": 4, "section": 1},
            {"act": "tyosopimuslaki", "chapter": 4, "section": 2},
            {"act": "tyosopimuslaki", "chapter": 7, "section": 9},
        ],
    },
]