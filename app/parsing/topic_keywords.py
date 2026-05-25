import re


TOPIC_KEYWORDS: dict[str, list[str]] = {
    # ТРУДОВОЙ ДОГОВОР
    "contract_types": [
    "työsopimus", "määräaikainen sopimus", "toistaiseksi voimassa",
    "työsuhteen ehto", "määräaikais",
    ],
    "probation_period": [
        "koeaika",
    ],

    # РАБОЧЕЕ ВРЕМЯ
    "working_hours": [
        "työaika", "säännöllinen työaika", "työvuorolista", "lepoajat",
        "vuorokausilepo", "viikoittainen vapaa", "tauko", "jaksotyö",
        "työvuorokausi", "työviikko", "hälytysluontoinen",
    ],
    "working_hours_reduction": [
        "työajan lyhennys", "pekkaspäivät", "vuosityöajan lyhentäminen",
        "työajantasaaminen",
    ],
    "overtime": [
        "ylityö", "lisä- ja ylityö", "ylityökorvaus", "hätätyö",
        "ylityöraja",
    ],
    "night_and_sunday_work": [
        "yötyö", "sunnuntaityö", "ilta- ja yölisä", "yölisä", "iltalisä",
        "pyhätyö", "sunnuntaikorotus", "arkipyhäkorvaus", "arkipyhä",
    ],

    # ОТПУСК
    "annual_leave": [
        "vuosiloma", "vuosivapaa", "lomakausi", "lomanmääräytymisvuosi",
        "lomapäivä", "loma",
    ],
    "holiday_pay": [
        "lomaraha", "lomapalkka", "lomaltapaluuraha", "lomakorvaus",
    ],

    # БОЛЬНИЧНЫЙ
    "sick_leave": [
    "sairausajan palkka", "sairastuminen", "sairauspoissaolo",
    "työkyvyttömyys", "työkyvyttömyy",   # ← добавлено
    "lääkärintarkastus", "tilapäinen poissaolo",
    "sairaan lapsen", "karenssi", "hedelmöityshoito",
    ],

    # СЕМЬЯ / ДЕКРЕТ
    "parental_leave": [
        "perhevapaa", "vanhempainvapaa", "raskausvapaa", "hoitovapaa",
        "lapsen syntymä", "imetys", "opintovapaa", "hautajaispäivä",
    ],

    # УВОЛЬНЕНИЕ
    "dismissal_grounds": [
        "irtisanominen", "työsopimuksen päättäminen", "työsuhteen päättyminen",
        "irtisanomisperuste", "purkaminen",
    ],
    "notice_period": [
        "irtisanomisaika", "irtisanomisajat",
    ],
    "dismissal_protection": [
        "työsuhdeturva", "rekrytointikielto", "irtisanomissuoja",
    ],
    "layoff": [
        "lomautus", "lomauttaminen", "lomautusilmoitus",
    ],

    # ЗАРПЛАТА
    "wages": [
    "palkanmaksu", "palkanmaksupäivä", "tuntipalkka", "kuukausipalkka",
    "palkkaryhmä", "henkilökohtainen palkka", "tehtäväkohtainen palkka",
    "palkkausjärjestelmä", "keskituntiansio", "palvelusvuosilisä",
    "palvelusaikalisä", "urakkatyö", "provisiopalkka",
    "suorituspalkkaus", "tasopalkkajärjestelmä", "palkankorotus",
    "palkka", "palkkaus",
    "sopimuskorotus", "palkallisuus", "tasolisä", "palkkahinnoittelu",  
    ],
    "min_wage": [
        "vähimmäispalkka", "taulukkopalkat", "palkkataulukko",
        "vaativuustasot", "työpalkat", "palkat",
        "myyjät", "logistiikkatyöntekijät", "toimihenkilöt",
        "muut ammattiryhmät",
    ],

    # ПРОФСОЮЗЫ
    "shop_steward": [
    "luottamusmies", "pääluottamusmies", "luottamusmiessopimus",
    "luottamushenkilö", "luottamusedustaja",
    "luottamustehtä",
    ],
    "safety_representative": [
        "työsuojeluvaltuutettu", "työsuojelupäällikkö", "työsuojeluasiamies",
        "työsuojeluyhteistoiminta",
    ],
    "local_agreement": [
        "paikallinen sopiminen", "paikallisesti sopimalla",
        "työpaikkakohtainen sopiminen",
    ],


    # БЕЗОПАСНОСТЬ
    "workplace_safety": [
        "työturvallisuus", "tapaturma", "ammattitauti", "työsuojelu",
    ],


    # ДОКУМЕНТЫ / САНКЦИИ
    "warning": [
        "varoitus",
    ],
    "work_certificate": [
        "työtodistus", "palkkatodistus",
    ],


    # КОМПЕНСАЦИИ
    "expense_reimbursement": [
        "matkakustannukset", "päiväraha", "työkalukorvaus", "puhelinkorvaus",
        "suojavaatetus", "työasut", "työvälineet", "matkustaminen",
        "matkakorvaus", "siirto",
    ],


    # ДИСКРИМИНАЦИЯ
    "discrimination": [
        "tasa-arvo", "syrjintä", "yhdenvertaisuus", "tasapuolinen kohtelu",
    ],

    # ОБЯЗАННОСТИ
    "employer_obligations": [
        "työnantajan velvollisuus", "työnjohtooikeus",
    ],
    "employee_obligations": [
        "työntekijän velvollisuus", "kilpaileva toiminta", "salassapito",
    ],
}



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
    if len(keyword) < 6:
        pattern = r'(?<!\w)' + re.escape(keyword) + r'(?!\w)'
        return bool(re.search(pattern, text, re.IGNORECASE))
    return keyword in text