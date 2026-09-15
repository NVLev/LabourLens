import re

TOPIC_KEYWORDS: dict[str, list[str]] = {
    # ТРУДОВОЙ ДОГОВОР
    "contract_types": [
        "työsopimus",
        "määräaikainen sopimus",
        "toistaiseksi voimassa",
        "työsuhteen ehto",
        "määräaikais",
    ],
    "probation_period": [
        "koeaika",
    ],
    # РАБОЧЕЕ ВРЕМЯ
    "working_hours": [
        "työaika",
        "säännöllinen työaika",
        "työvuorolista",
        "lepoajat",
        "vuorokausilepo",
        "viikoittainen vapaa",
        "tauko",
        "jaksotyö",
        "työvuorokausi",
        "työviikko",
        "hälytysluontoinen",
        "lisätyö",  # additional work (below contract hours)
        "kolmivuorotyö",  # continuous 3-shift work
        "varallaolo",  # on-call duty
        "joustovapaa",  # flex leave earned from overtime
        "työvuoroluettelo",
        "viikkolepo",
        "kolmivuorotyö",
        "keskeytymätön työ",
    ],
    "working_hours_reduction": [
        "työajan lyhennys",
        "pekkaspäivät",
        "vuosityöajan lyhentäminen",
        "työajantasaaminen",
        "joustovapaa",
    ],
    "overtime": [
        "ylityö",
        "lisä- ja ylityö",
        "ylityökorvaus",
        "hätätyö",
        "ylityöraja",
        "lisätyö",
    ],
    "night_and_sunday_work": [
        "yötyö",
        "sunnuntaityö",
        "ilta- ja yölisä",
        "yölisä",
        "iltalisä",
        "pyhätyö",
        "sunnuntaikorotus",
        "arkipyhäkorvaus",
        "arkipyhä",
    ],
    # ОТПУСК
    "annual_leave": [
        "vuosiloma",
        "vuosivapaa",
        "lomakausi",
        "lomanmääräytymisvuosi",
        "lomapäivä",
        "loma",
    ],
    "holiday_pay": [
        "lomaraha",
        "lomapalkka",
        "lomaltapaluuraha",
        "lomakorvaus",
    ],
    # БОЛЬНИЧНЫЙ
    "sick_leave": [
        "sairausajan palkka",
        "sairastuminen",
        "sairauspoissaolo",
        "työkyvyttömyys",
        "lääkärintarkastukset",
        "työkyvyttömyy",
        "lääkärintarkastus",
        "tilapäinen poissaolo",
        "sairaan lapsen",
        "karenssi",
        "hedelmöityshoito",
        "terveystarkastukset",
    ],
    # СЕМЬЯ / ДЕКРЕТ
    "parental_leave": [
        "perhevapaa",
        "vanhempainvapaa",
        "raskausvapaa",
        "hoitovapaa",
        "lapsen syntymä",
        "imetys",
        "opintovapaa",
        "hautajaispäivä",
        "synnytysloma",
        "raskaus",
    ],
    # УВОЛЬНЕНИЕ
    "dismissal_grounds": [
        "irtisanominen",
        "työsopimuksen päättäminen",
        "työsuhteen päättyminen",
        "irtisanomisperuste",
        "purkaminen",
        "takaisinottaminen",  # rehiring obligation after economic dismissal
        "perusteettomasta irtisanomisesta",  # wrongful dismissal compensation
    ],
    "notice_period": [
        "irtisanomisaika",
        "irtisanomisajat",
    ],
    "dismissal_protection": [
        "työsuhdeturva",
        "rekrytointikielto",
        "irtisanomissuoja",
    ],
    "layoff": [
        "lomautus",
        "lomauttaminen",
        "lomautusilmoitus",
    ],
    # ЗАРПЛАТА
    "wages": [
        "palkanmaksu",
        "palkanmaksupäivä",
        "tuntipalkka",
        "kuukausipalkka",
        "palkkaryhmä",
        "henkilökohtainen palkka",
        "tehtäväkohtainen palkka",
        "palkkausjärjestelmä",
        "keskituntiansio",
        "palvelusvuosilisä",
        "palvelusaikalisä",
        "urakkatyö",
        "provisiopalkka",
        "suorituspalkkaus",
        "tasopalkkajärjestelmä",
        "palkankorotus",
        "palkka",
        "palkkaus",
        "sopimuskorotus",
        "palkallisuus",
        "tasolisä",
        "palkkahinnoittelu",
        "työnopastus",
        "likainen työ",
        "palkan käsite",
        "osa-ajan palkka",
    ],
    "min_wage": [
        "vähimmäispalkka",
        "vähimmäistuntipalkka",
        "vähimmäispalkat",
        "taulukkopalkat",
        "taulukkopalkka",
        "palkkataulukko",
        "ohjetuntipalkka",
        "ohjetuntipalkat",
        "työpalkat",
        "vaativuustasot",
    ],
    # ПРОФСОЮЗЫ
    "shop_steward": [
        "luottamusmies",
        "pääluottamusmies",
        "luottamusmiessopimus",
        "luottamushenkilö",
        "luottamusedustaja",
        "luottamustehtä",
        "ay-koulutus",  # union training rights
        "kokoontumis",  # assembly right of employees
    ],
    "safety_representative": [
        "työsuojeluvaltuutettu",
        "työsuojelupäällikkö",
        "työsuojeluasiamies",
        "työsuojeluyhteistoiminta",
    ],
    "local_agreement": [
        "paikallinen sopiminen",
        "paikallisesti sopimalla",
        "työpaikkakohtainen sopiminen",
    ],
    # БЕЗОПАСНОСТЬ
    "workplace_safety": [
        "työturvallisuus",
        "tapaturma",
        "ammattitauti",
        "työsuojelu",
    ],
    # ДОКУМЕНТЫ / САНКЦИИ
    "warning": [
        "varoitus",
    ],
    "work_certificate": [
        "työtodistus",
        "palkkatodistus",
    ],
    # КОМПЕНСАЦИИ
    "expense_reimbursement": [
        "matkakustannukset",
        "päiväraha",
        "työkalukorvaus",
        "puhelinkorvaus",
        "suojavaatetus",
        "työasut",
        "työvälineet",
        "matkustaminen",
        "matkakorvaus",
        "matkakorvaukset",
        "siirto",
        "suojavaatteet",
    ],
    # ДИСКРИМИНАЦИЯ
    "discrimination": [
        "tasa-arvo",
        "syrjintä",
        "yhdenvertaisuus",
        "tasapuolinen kohtelu",
    ],
    # ОБЯЗАННОСТИ
    "employer_obligations": [
        "työnantajan velvollisuus",
        "työnjohtooikeus",
    ],
    "employee_obligations": [
        "työntekijän velvollisuus",
        "kilpaileva toiminta",
        "salassapito",
    ],
}


# Кэш скомпилированных regex — только для коротких ключевых слов (< 6 символов),
# которым нужна граница слова.
#
# ВАЖНО: универсальная граница слова для ВСЕХ ключевых слов (более ранняя
# версия этого файла) была ошибкой и откатена. Она чинила одну конкретную
# коллизию ("palkat" внутри "palkata"/"palkaton"), но ломала легитимные
# совпадения для длинных составных слов, к которым в финском падежные
# окончания приклеиваются без разделителя — например:
#   "suojavaatetus" не совпадает с "suojavaatetusta" (партитив)
#   "päiväraha"     не совпадает с "päivärahaan" (иллатив)
#   "luottamusedustaja" не совпадает с "luottamusedustajalle" (аллатив)
# Реальной причиной исходного бага был не regex, а само наличие "palkat"
# в списке min_wage — оно удалено выше. Точечное удаление проблемного
# ключа решает задачу без риска для остальных тем.
_COMPILED_PATTERNS: dict[str, re.Pattern] = {}


def _get_pattern(keyword: str) -> re.Pattern:
    if keyword not in _COMPILED_PATTERNS:
        pattern = r"(?<!\w)" + re.escape(keyword) + r"(?!\w)"
        _COMPILED_PATTERNS[keyword] = re.compile(pattern, re.IGNORECASE)
    return _COMPILED_PATTERNS[keyword]


def detect_topic(text: str) -> str | None:
    """
    Определяет topic_key по тексту (клауза TES или заголовок секции).
    Возвращает первый совпавший топик или None.
    Длинные ключевые слова имеют приоритет над короткими.
    """
    text_lower = text.lower()
    # Сортируем по убыванию длины — длинные фразы имеют приоритет
    candidates = []
    for topic_key, keywords in TOPIC_KEYWORDS.items():
        for keyword in keywords:
            if _keyword_matches(keyword, text_lower):
                candidates.append((len(keyword), topic_key))
    if not candidates:
        return None
    # Берём топик с самым длинным совпавшим ключевым словом
    candidates.sort(reverse=True)
    return candidates[0][1]


def _keyword_matches(keyword: str, text: str) -> bool:
    """
    Проверяет вхождение ключевого слова в текст.

    Короткие слова (< 6 символов) проверяются с учётом границ слова —
    иначе они слишком часто совпадают как подстрока внутри случайных
    других слов (пример из истории: "loma" внутри "lomautus").

    Более длинные слова (составные термины вроде "vähimmäispalkka",
    "luottamusedustaja") проверяются простым вхождением подстроки —
    без границы на конце, потому что в финском падежные окончания
    приклеиваются к корню напрямую, и строгая граница отсекла бы
    легитимные словоформы. Риск ложной коллизии для таких длинных
    специфичных терминов на практике намного ниже, чем для коротких.
    """
    if len(keyword) < 6:
        return bool(_get_pattern(keyword).search(text))
    return keyword in text
