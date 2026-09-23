import logging
import re
from datetime import date
from decimal import Decimal
from typing import Any

from app.calculator.enums import RateType

logger = logging.getLogger(__name__)

KT_DATE_AMOUNT_RE = re.compile(
    r"(\d{1,2}\.\d{1,2}\.\d{4})"
    r"\s+(?:alkaen|lukien)\s+"
    r"(\d[\d\s\xa0]*(?:,\d{2})?)"
    r"(?:\s*(?:€/kk|euroa|€))?",
    re.IGNORECASE,
)

# Случай 1: явные "N mom. Title" заголовки, режим назван прямо в заголовке.
KT_OVERTIME_AMOUNT_RE = re.compile(
    r"(?P<threshold_hours>\d+)\s+ensimm(?:äi|ai)selt[äa]\s+"
    r"(?:ylityö)?tunni(?:lta|sta).{0,80}?"
    r"(?P<tier1_pct>\d+(?:,\d+)?)\s*(?:%(?::lla)?|prosentilla)"
    r".{0,80}?"
    r"(?P<tier2_pct>\d+(?:,\d+)?)\s*(?:%(?::lla)?|prosentilla)",
    re.IGNORECASE,
)

_MOM_HEADER_BEFORE_RE = re.compile(r"\d+\s*mom\.[ \t]*([^\n]*)")
_MOM_HEADER_AFTER_RE = re.compile(r"([^\n]*?)[ \t]+\d+\s*mom\.")

# Случай 2 ("слитный" формат — mom.-заголовок пуст или не назван по режиму,
_VUOROKAUTINEN_COMPACT_RE = re.compile(
    r"(?P<tier1_pct>\d+(?:,\d+)?)\s*%:lla\s+korotettu\s+\w+\s+"
    r"(?P<threshold>[a-zäöA-ZÄÖ]+|\d+)\s+ensimm(?:äi|ai)selt[äa]\s+vuorokautis\w*"
    r".{0,80}?"
    r"(?P<tier2_pct>\d+(?:,\d+)?)\s*%:lla",
    re.IGNORECASE,
)

# "50 %:lla korotettu tuntipalkka viikoittaisen ylityön 5 ensimmäiseltä tunnilta
#  ja 100 %:lla korotettu palkka kultakin seuraavalta viikoittaiselta..."
_VIIKOITTAINEN_COMPACT_RE = re.compile(
    r"(?P<tier1_pct>\d+(?:,\d+)?)\s*%:lla\s+korotettu\s+\w+\s+"
    r"viikoittais\w*\s+ylityön\s+"
    r"(?P<threshold>[a-zäöA-ZÄÖ]+|\d+)\s+ensimm(?:äi|ai)selt[äa]"
    r".{0,80}?"
    r"(?P<tier2_pct>\d+(?:,\d+)?)\s*%:lla",
    re.IGNORECASE,
)

# Якорь начала jaksotyö-зоны внутри mom.-блока — дальше от него режем зону вручную.
_JAKSOTYO_ANCHOR_RE = re.compile(r"jaksoty\w*", re.IGNORECASE)

# Первая ставка jaksotyö-зоны: "jaksotyössä 50 %:lla korotettu tuntipalkka ..."
_JAKSOTYO_TIER1_RE = re.compile(
    r"jaksoty\w*.{0,40}?(?P<tier1_pct>\d+(?:,\d+)?)\s*%:lla",
    re.IGNORECASE,
)

# Вторая ставка jaksotyö-зоны — привязана к завершающей фразе
# "... %:lla korotettu tuntipalkka kultakin seuraavalta ylityötunnilta"
_JAKSOTYO_TIER2_RE = re.compile(
    r"(?P<tier2_pct>\d+(?:,\d+)?)\s*%:lla.{0,40}?kultakin\s+seuraavalta",
    re.IGNORECASE,
)

# Финские числительные, встречающиеся как словоформы порогов/периодов
_FI_NUMBER_WORDS = {
    "yksi": 1,
    "yhden": 1,
    "yhdeltä": 1,
    "kaksi": 2,
    "kahden": 2,
    "kahdelta": 2,
    "kolme": 3,
    "kolmen": 3,
    "kolmelta": 3,
    "neljä": 4,
    "neljän": 4,
    "neljältä": 4,
    "viisi": 5,
    "viiden": 5,
    "viideltä": 5,
    "kuusi": 6,
    "kuuden": 6,
    "kuudelta": 6,
    "seitsemän": 7,
    "seitsemältä": 7,
    "kahdeksan": 8,
    "kahdeksalta": 8,
    "yhdeksän": 9,
    "yhdeksältä": 9,
    "kymmenen": 10,
    "kymmeneltä": 10,
}

# Альтернативный паттерн из ключей словаря — используется в _JAKSOTYO_PERIOD_RE,
# чтобы период матчился ТОЛЬКО по известным числительным
_NUMBER_WORD_ALT = "|".join(sorted(_FI_NUMBER_WORDS.keys(), key=len, reverse=True))

# Повторяющиеся пары (период, порог часов) внутри jaksotyö-зоны
_JAKSOTYO_PERIOD_RE = re.compile(
    rf"(?P<period>(?:{_NUMBER_WORD_ALT})(?:\s+ja\s+(?:{_NUMBER_WORD_ALT}))?)"
    r"\s+viikon\s+työaikajakson\s+(?P<hours>\d+)\s+ensimm(?:äi|ai)selt[äa]",
    re.IGNORECASE,
)

# паттерн - явный процент
_NIGHT_SUNDAY_PCT_RE = re.compile(
    r"(?P<pct>\d+(?:,\d+)?)\s*(?:%(?::n)?|prosentin)",
    re.IGNORECASE,
)

# паттерн - фиксированная фраза = 100%: "korottamaton tuntipalkka"
_FULL_RATE_PHRASE_RE = re.compile(r"\bkorottamaton\s+tuntipalkka\b", re.IGNORECASE)

# паттерн - фиксированная фраза = 100%: "kaksinkertaisena"
_DOUBLE_RATE_PHRASE_RE = re.compile(r"kaksinkertais\w*", re.IGNORECASE)

#-----------------------topic - expense_reimbursement---------------------
# паттерн - Kokopäiväraha + osapäiväraha
KT_DAILY_ALLOWANCE_RE = re.compile(
    r"Kokopäiväraha\s+on\s+(?P<full>\d+(?:,\d+)?)\s*(?:euroa|€)"
    r"\s+ja\s+osapäiväraha\s+(?P<part>\d+(?:,\d+)?)\s*(?:euroa|€)",
    re.IGNORECASE,
)

KT_MEAL_COMPENSATION_RE = re.compile(
    r"ateriakorvaus(?:ta)?\s+(?P<amt_tier1>\d+(?:,\d+)?)\s*(?:euroa|€)"
    r"|(?P<amt_tier2>\d+(?:,\d+)?)\s*euron\s+suuruinen\s+ateriakorvaus",
    re.IGNORECASE,
)

KT_NIGHT_TRAVEL_ALLOWANCE_RE = re.compile(
    r"(?P<amt>\d+(?:,\d+)?)\s*euron\s+yömatkaraha",
    re.IGNORECASE,
)

KT_CLOTHING_MAINTENANCE_RE = re.compile(
    r"huollosta\s+aiheutuvista\s+kustannuksista\s+korvataan\s+"
    r"(?P<amt>\d+(?:,\d+)?)\s*euroa\s+kuukaudessa",
    re.IGNORECASE,
)
#--------------------topic - sick_leave----------------------
KT_SICK_PAY_TIER_RE = re.compile(
    r"varsinainen(?:\s+palkkansa|en\s+palkkansa)\s+enintään\s+(?P<tier1_days>\d+)\s*"
    r"kalenteripäivän ajalta\s+ja\s+sen\s+jälkeen\s+kaksi\s+kolmasosaa\s*"
    r"\(?⅔\)?\s*varsinaisesta\s+palkastaan\s+enintään\s+(?P<tier2_days>\d+)\s*"
    r"kalenteripäivän ajalta",
    re.IGNORECASE,
)

KT_SICK_PAY_SHORT_TENURE_RE = re.compile(
    r"saada\s+sairauspoissaolon\s+ajalta\s+varsinainen\s+palkkansa\s+"
    r"(?P<days>\d+)\s*kalenteripäivän\s+ajalta,\s*jonka\s+jälkeen\s+ei\s+suoriteta\s+mitään\s+palkkaetuja",
    re.IGNORECASE,
)

KT_SICK_PAY_DISCRETIONARY_TIER_RE = re.compile(
    r"Lisäksi\s+voidaan\s+harkinnan\s+mukaan\s+maksaa\s+kaksi\s+kolmasosaa\s+"
    r"varsinaisesta\s+palkasta\s+enintään\s+(?P<days>\d+)\s*kalenteripäivän\s+ajalta",
    re.IGNORECASE,
)

#паттерн для различения обычного больничного и больничного "по производственной травме"
KT_SICK_LEAVE_ACCIDENT_KEYWORDS_RE = re.compile(
    r"työtapaturma|ammattitauti|tapaturmavakuutuslainsäädännössä|"
    r"työtehtävistä\s+johtuneesta\s+väkivallasta",
    re.IGNORECASE,
)

def extract_kt_min_wage(text_fi: str) -> list[dict]:
    """
    Возвращает список {"value": ..., "unit": "eur_month", "effective_from": ..., "source_text": ...}
    По одной записи на каждое найденное совпадение "дата + сумма" в тексте.
    """
    results = []

    for match in KT_DATE_AMOUNT_RE.finditer(text_fi):
        date_str = match.group(1)  # "1.6.2023"
        amount_str = match.group(2)  # "1 746,00"

        day, month, year = map(int, date_str.split("."))
        effective_from = date(year, month, day)

        value = _normalize_amount(amount_str)

        start = match.start()
        end = match.end()

        snippet = text_fi[max(0, start - 40) : min(len(text_fi), end + 40)]
        source_text = " ".join(snippet.split())

        results.append(
            {
                "wage_group": None,
                "rate_type_context": None,
                "rate_type": RateType.MIN_WAGE.value,
                "value": value,
                "unit": "eur_month",
                "effective_from": effective_from,
                "source_text": source_text,
            }
        )

    return results


def _build_expense_row(
    rate_type: str,
    value: Decimal,
    source_text: str,
    unit: str,
    rate_type_context: str | None = None,
) -> dict:
    """Единая точка сборки rate-словаря для extractor'ов group A (expense_reimbursement)."""
    return {
        "wage_group": None,
        "rate_type_context": rate_type_context,
        "rate_type": rate_type,
        "value": value,
        "unit": unit,
        "source_text": source_text,
    }


def _extract_daily_allowance(text_fi: str) -> list[dict]:
    """
    Kokopäiväraha + osapäiväraha — одно предложение, две обязательные
    именованные группы (full/part): заполняются всегда вместе, либо
    весь regex не совпадает вовсе (альтернации тут нет).

    Пример: "Kokopäiväraha on 54 euroa ja osapäiväraha 25 euroa
    jokaiselta ao. päivärahaan oikeuttavalta matkavuorokaudelta."
    """
    results = []

    for match in KT_DAILY_ALLOWANCE_RE.finditer(text_fi):
        start, end = match.start(), match.end()
        snippet = text_fi[max(0, start - 40) : min(len(text_fi), end + 40)]
        source_text = " ".join(snippet.split())

        try:
            full_value = _normalize_amount(match.group("full"))
            part_value = _normalize_amount(match.group("part"))
        except Exception:
            logger.warning(
                "KT expense_reimbursement: failed to parse daily allowance amounts: %.120s",
                source_text,
            )
            continue

        results.append(
            _build_expense_row(
                RateType.DAILY_ALLOWANCE_FULL_EUR.value,
                full_value,
                source_text,
                "eur",
            )
        )
        results.append(
            _build_expense_row(
                RateType.DAILY_ALLOWANCE_PART_EUR.value,
                part_value,
                source_text,
                "eur",
            )
        )

    if not results:
        logger.debug(
            "KT expense_reimbursement: no daily allowance (kokopäiväraha) match found"
        )

    return results


def _extract_night_travel_allowance(text_fi: str) -> list[dict]:
    """
    Yömatkaraha — одна именованная группа (amt): "maksetaan 16 euron
    yömatkaraha" / "16,00 euron yömatkaraha".
    """
    results = []

    for match in KT_NIGHT_TRAVEL_ALLOWANCE_RE.finditer(text_fi):
        start, end = match.start(), match.end()
        snippet = text_fi[max(0, start - 40) : min(len(text_fi), end + 40)]
        source_text = " ".join(snippet.split())

        try:
            value = _normalize_amount(match.group("amt"))
        except Exception:
            logger.warning(
                "KT expense_reimbursement: failed to parse night travel allowance amount: %.120s",
                source_text,
            )
            continue

        results.append(
            _build_expense_row(
                RateType.NIGHT_TRAVEL_ALLOWANCE_EUR.value,
                value,
                source_text,
                "eur",
            )
        )

    if not results:
        logger.debug(
            "KT expense_reimbursement: no night travel allowance (yömatkaraha) match found"
        )

    return results


def _extract_meal_compensation(text_fi: str) -> list[dict]:
    """
    Ateriakorvaus — два разных tier'а (13,50 € базовый, 2,02 € усечённый
    случай hyvtes), выраженные разным порядком слов в одном regex через
    альтернацию. В каждом match заполнена ровно одна из двух именованных
    групп (amt_tier1 / amt_tier2) — вторая всегда None.
    """
    results = []

    for match in KT_MEAL_COMPENSATION_RE.finditer(text_fi):
        start, end = match.start(), match.end()
        snippet = text_fi[max(0, start - 40) : min(len(text_fi), end + 40)]
        source_text = " ".join(snippet.split())

        tier1_amount_str = match.group("amt_tier1")
        tier2_amount_str = match.group("amt_tier2")

        if tier1_amount_str:
            try:
                value = _normalize_amount(tier1_amount_str)
            except Exception:
                logger.warning(
                    "KT expense_reimbursement: failed to parse meal compensation (tier1) amount: %.120s",
                    source_text,
                )
                continue
            results.append(
                _build_expense_row(
                    RateType.MEAL_COMPENSATION_EUR.value,
                    value,
                    source_text,
                    "eur",
                    "tier1",
                )
            )
        elif tier2_amount_str:
            try:
                value = _normalize_amount(tier2_amount_str)
            except Exception:
                logger.warning(
                    "KT expense_reimbursement: failed to parse meal compensation (tier2) amount: %.120s",
                    source_text,
                )
                continue
            results.append(
                _build_expense_row(
                    RateType.MEAL_COMPENSATION_EUR.value,
                    value,
                    source_text,
                    "eur",
                    "tier2",
                )
            )
        else:
            logger.warning(
                "KT expense_reimbursement: meal compensation match with neither tier group filled: %.120s",
                source_text,
            )

    if not results:
        logger.debug(
            "KT expense_reimbursement: no meal compensation (ateriakorvaus) match found"
        )

    return results


def _extract_clothing_maintenance(text_fi: str) -> list[dict]:
    """
    Vaatetuksen/suojavaatetuksen huolto — фиксированная ежемесячная
    компенсация: "korvataan 5 euroa kuukaudessa". Unit "eur_month"
    (не разовая, а помесячная выплата — по аналогии с min_wage).
    """
    results = []

    for match in KT_CLOTHING_MAINTENANCE_RE.finditer(text_fi):
        start, end = match.start(), match.end()
        snippet = text_fi[max(0, start - 40) : min(len(text_fi), end + 40)]
        source_text = " ".join(snippet.split())

        try:
            value = _normalize_amount(match.group("amt"))
        except Exception:
            logger.warning(
                "KT expense_reimbursement: failed to parse clothing maintenance amount: %.120s",
                source_text,
            )
            continue

        results.append(
            _build_expense_row(
                RateType.CLOTHING_MAINTENANCE_EUR.value,
                value,
                source_text,
                "eur_month",
            )
        )

    if not results:
        logger.debug("KT expense_reimbursement: no clothing maintenance match found")

    return results


def extract_kt_expense_reimbursement(text_fi: str) -> list[dict]:
    """
    Возвращает список rate-словарей для компенсаций расходов KT (group A):
    kokopäiväraha/osapäiväraha, ateriakorvaus (2 tier'а), yömatkaraha,
    vaatetuksen huolto.

    В отличие от overtime/night_sunday, сегментация по mom.-заголовкам
    не нужна — каждая сумма распознаётся по собственной устойчивой
    фразе-якорю независимо от остального текста клаузулы, поэтому все
    четыре под-функции сканируют text_fi целиком.
    """
    results = []
    results.extend(_extract_daily_allowance(text_fi))
    results.extend(_extract_meal_compensation(text_fi))
    results.extend(_extract_night_travel_allowance(text_fi))
    results.extend(_extract_clothing_maintenance(text_fi))

    return results


def extract_kt_overtime(text_fi: str) -> list[dict]:
    """
    Возвращает список rate-словарей для сверхурочных ставок KT.

    Сегментирует клаузуру по "N mom." заголовкам (find_segments_overtime).
    Если заголовок явно называет режим (vuorokautinen/viikoittainen) —
    извлекает через "Случай 1" (KT_OVERTIME_AMOUNT_RE). Если заголовок
    пуст или не распознан — пробует "Случай 2": слитный текст без
    заголовков режима, с обратным порядком слов и, для jaksotyö,
    несколькими порогами (по длине периода) внутри одного блока.
    """
    results = []
    segments = find_segments_by_mom_header(text_fi)

    for title_text, segment in segments:
        rate_type_context = _detect_mode(title_text)

        if rate_type_context is not None:
            results.extend(_extract_case1_tiers(segment, rate_type_context))
        else:
            results.extend(_extract_compact_segment(segment))

    return results


def extract_kt_night_sunday(text_fi: str) -> list[dict]:
    """
    Возвращает список rate-словарей для ставок KT при работе в ночную смену и в выходные.
    :param text_fi:
    :return:
    """
    results = []
    segments = find_segments_by_mom_header(text_fi)
    for title_text, segment in segments:
        rate_type_context = _detect_night_sunday_mode(title_text)

        if rate_type_context is not None:
            results.extend(_extract_night_sunday_rate(segment, rate_type_context))

        else:
            logger.warning(
                "KT night/sunday: could not detect mode from header '%s': %.120s",
                title_text,
                segment,
            )

    return results

SICK_PAY_TIER2_FRACTION_PCT = Decimal("66.67")  # kaksi kolmasosaa (⅔) — нормализовано в pct


def _build_sick_leave_row(
    rate_type: str,
    value: Decimal,
    source_text: str,
    unit: str,
    rate_type_context: str,
) -> dict:
    """
    Единая точка сборки rate-словаря для extractor'ов topic sick_leave.
    rate_type_context обязателен (не Optional, как в _build_expense_row) —
    для sick_leave не бывает строки без контекста general/work_accident.
    """
    return {
        "wage_group": None,
        "rate_type_context": rate_type_context,
        "rate_type": rate_type,
        "value": value,
        "unit": unit,
        "source_text": source_text,
    }


def _extract_sick_pay_tiers(text_fi: str, context: str) -> list[dict]:
    """
    Основная лестница: tier1 (N дней, всегда 100% — varsinainen palkkansa)
    + tier2 (M дней, ⅔ от зарплаты). Один match даёт четыре rate-строки
    сразу: обе группы (tier1_days/tier2_days) обязательны в самом regex
    (альтернации нет), поэтому извлекаем их безусловно.
    """
    results = []

    for match in KT_SICK_PAY_TIER_RE.finditer(text_fi):
        start, end = match.start(), match.end()
        snippet = text_fi[max(0, start - 40) : min(len(text_fi), end + 40)]
        source_text = " ".join(snippet.split())

        try:
            tier1_days = _normalize_amount(match.group("tier1_days"))
            tier2_days = _normalize_amount(match.group("tier2_days"))
        except Exception:
            logger.warning(
                "KT sick_leave: failed to parse sick_pay_tiers days: %.120s",
                source_text,
            )
            continue

        results.append(
            _build_sick_leave_row(
                RateType.SICK_PAY_TIER1_DAYS.value,
                tier1_days,
                source_text,
                "days",
                context,
            )
        )
        results.append(
            _build_sick_leave_row(
                RateType.SICK_PAY_TIER1_PCT.value,
                Decimal(100),
                source_text,
                "pct",
                context,
            )
        )
        results.append(
            _build_sick_leave_row(
                RateType.SICK_PAY_TIER2_DAYS.value,
                tier2_days,
                source_text,
                "days",
                context,
            )
        )
        results.append(
            _build_sick_leave_row(
                RateType.SICK_PAY_TIER2_PCT.value,
                SICK_PAY_TIER2_FRACTION_PCT,
                source_text,
                "pct",
                context,
            )
        )

    if not results:
        logger.debug(
            "KT sick_leave: no sick pay tier match found (context=%s)", context
        )

    return results


def _extract_short_tenure(text_fi, context) -> list[dict]:
    results = []

    for match in KT_SICK_PAY_SHORT_TENURE_RE.finditer(text_fi):
        start, end = match.start(), match.end()
        snippet = text_fi[max(0, start - 40): min(len(text_fi), end + 40)]
        source_text = " ".join(snippet.split())
        try:
            value = _normalize_amount(match.group("days"))
        except Exception:
            logger.warning(
                "KT sick_leave: failed to parse sick_pay_short_tenure: %.120s",
                source_text,
            )
            continue
        results.append(
            _build_sick_leave_row(
                RateType.SICK_PAY_SHORT_TENURE_DAYS.value,
                value,
                source_text,
                "days",
                context,
            )
        )
        results.append(
            _build_sick_leave_row(
                RateType.SICK_PAY_SHORT_TENURE_PCT.value,
                Decimal(100),
                source_text,
                "pct",
                context,
            )
        )
    return results



def _extract_discretionary_tier(text_fi, context) -> list[dict]:
    results = []

    for match in KT_SICK_PAY_DISCRETIONARY_TIER_RE.finditer(text_fi):
        start, end = match.start(), match.end()
        snippet = text_fi[max(0, start - 40): min(len(text_fi), end + 40)]
        source_text = " ".join(snippet.split())
        try:
            value = _normalize_amount(match.group("days"))
        except Exception:
            logger.warning(
                "KT sick_leave: failed to parse sick_pay_discretionary_tier: %.120s",
                source_text,
            )
            continue
        results.append(
            _build_sick_leave_row(
                RateType.SICK_PAY_TIER3_DISCRETIONARY_DAYS.value,
                value,
                source_text,
                "days",
                context,
            )
        )
    return results


def extract_kt_sick_leave(text_fi: str) -> list[dict]:
    """
    Возвращает список rate-словарей для больничных KT: основная лестница
    (tier1 дней full pay + tier2 дней ⅔), короткий стаж (единственный
    tier, вместо лестницы), дискреционный tier3 (только work_accident,
    только hyvtes). rate_type_context (general/work_accident) вычисляется
    один раз на клаузулу и передаётся во все под-функции.
    """
    context = _detect_sick_leave_context(text_fi)

    results = []
    results.extend(_extract_sick_pay_tiers(text_fi, context))
    results.extend(_extract_short_tenure(text_fi, context))
    results.extend(_extract_discretionary_tier(text_fi, context))
    return results



def _detect_sick_leave_context(text_fi: str) -> str:
    """
    Определяет, обычный это больничный или больничный по производственной
    травме — по ключевым словам в начале клаузулы (первый mom., где
    указывается основание). Смотрим только на первые ~200 символов,
    чтобы не словить упоминание травмы из перекрёстной ссылки на другой §
    (пример: kt-ytes §89 ссылается на §90 по ходу текста).
    """
    lowered = text_fi.lower()
    if KT_SICK_LEAVE_ACCIDENT_KEYWORDS_RE.search(lowered[:200]):
        return "work_accident"
    else:
        return "general"


def _detect_night_sunday_mode(title_text):
    lowered = title_text.lower()
    if "sunnuntai" in lowered:
        return "sunnuntai"
    if "lauantai" in lowered:
        return "lauantai"
    if "aatto" in lowered:
        return "aatto"
    if "ilta" in lowered:
        return "ilta"
    if "yötyö" in lowered or "yölisä" in lowered or "yökorvaus" in lowered:
        return "yo"
    return None


def _build_night_sunday_row(
    rate_type_context: str, value: Decimal, source_text: str
) -> dict:
    return {
        "wage_group": None,
        "rate_type": RateType.NIGHT_SUNDAY_RATE_PCT.value,
        "rate_type_context": rate_type_context,
        "value": value,
        "unit": "pct",
        "source_text": source_text,
    }


def _extract_night_sunday_rate(segment: str, rate_type_context: str) -> list[dict]:
    """Пробует явный процент, потом обе фиксированные фразы (=100%) по очереди."""
    for pattern, fixed_value in (
        (_NIGHT_SUNDAY_PCT_RE, None),
        (_FULL_RATE_PHRASE_RE, Decimal(100)),
        (_DOUBLE_RATE_PHRASE_RE, Decimal(100)),
    ):
        m = pattern.search(segment)
        if not m:
            continue
        value = (
            fixed_value
            if fixed_value is not None
            else _normalize_amount(m.group("pct"))
        )
        start, end = m.start(), m.end()
        snippet = segment[max(0, start - 40) : min(len(segment), end + 40)]
        source_text = " ".join(snippet.split())
        return [_build_night_sunday_row(rate_type_context, value, source_text)]

    logger.warning(
        "KT night/sunday: no rate found for mode '%s': %.120s",
        rate_type_context,
        segment,
    )
    return []

# overtime
def _extract_case1_tiers(segment: str, rate_type_context: str) -> list[dict]:
    """Случай 1: заголовок уже назвал режим, ищем тройку (порог, tier1%, tier2%)."""
    results = []

    for match in KT_OVERTIME_AMOUNT_RE.finditer(segment):
        start = match.start()
        end = match.end()

        snippet = segment[max(0, start - 40) : min(len(segment), end + 40)]
        source_text = " ".join(snippet.split())

        results.extend(
            _build_tier_rows(
                rate_type_context=rate_type_context,
                threshold_hours=_normalize_amount(match.group("threshold_hours")),
                tier1_pct=_normalize_amount(match.group("tier1_pct")),
                tier2_pct=_normalize_amount(match.group("tier2_pct")),
                source_text=source_text,
            )
        )

    return results


def _extract_compact_segment(segment: str) -> list[dict]:
    """
    Случай 2: mom.-заголовок пуст/не распознан — весь режим текстово
    "слит" внутри одного блока. Пробуем три известных под-паттерна
    (vuorokautinen / viikoittainen / jaksotyö) независимо друг от друга,
    т.к. они не имеют общей структуры (порядок слов у каждого свой).
    """
    results = []

    m = _VUOROKAUTINEN_COMPACT_RE.search(segment)
    if m:
        results.extend(_build_tiers_from_compact_match(m, "vuorokautinen", segment))

    m = _VIIKOITTAINEN_COMPACT_RE.search(segment)
    if m:
        results.extend(_build_tiers_from_compact_match(m, "viikoittainen", segment))

    results.extend(_extract_jaksotyo(segment))

    if not results:
        logger.warning(
            "KT overtime: no known pattern (Case 1 or Case 2) matched segment: %.120s",
            segment,
        )

    return results


def _build_tiers_from_compact_match(
    match: re.Match, mode: str, full_text: str
) -> list[dict]:
    threshold = _word_to_number(match.group("threshold"))
    if threshold is None:
        logger.warning(
            "KT overtime: unrecognized threshold word '%s' for mode '%s'",
            match.group("threshold"),
            mode,
        )
        return []

    start = match.start()
    end = match.end()
    snippet = full_text[max(0, start - 40) : min(len(full_text), end + 40)]
    source_text = " ".join(snippet.split())

    return _build_tier_rows(
        rate_type_context=mode,
        threshold_hours=Decimal(threshold),
        tier1_pct=_normalize_amount(match.group("tier1_pct")),
        tier2_pct=_normalize_amount(match.group("tier2_pct")),
        source_text=source_text,
    )


def _extract_jaksotyo(segment: str) -> list[dict]:
    """
    jaksotyö — особый случай: одна пара ставок (tier1/tier2 %), но
    НЕСКОЛЬКО порогов часов, по одному на каждую длину периода
    (2 недели / 3 недели / 4 и 6 недель ...). Каждая пара
    (период, порог) даёт свой rate_type_context вида "jaksotyo_2vk".
    """
    anchor = _JAKSOTYO_ANCHOR_RE.search(segment)
    if not anchor:
        return []

    zone = segment[anchor.start() :]

    tier1_match = _JAKSOTYO_TIER1_RE.search(zone)
    tier2_match = _JAKSOTYO_TIER2_RE.search(zone)
    period_matches = list(_JAKSOTYO_PERIOD_RE.finditer(zone))

    if not tier1_match or not tier2_match or not period_matches:
        logger.warning(
            "KT overtime: jaksotyö zone found but pattern incomplete "
            "(tier1=%s, tier2=%s, periods=%d): %.120s",
            bool(tier1_match),
            bool(tier2_match),
            len(period_matches),
            zone,
        )
        return []

    tier1_pct = _normalize_amount(tier1_match.group("tier1_pct"))
    tier2_pct = _normalize_amount(tier2_match.group("tier2_pct"))

    results = []
    for m in period_matches:
        period_suffix = _period_words_to_suffix(m.group("period"))
        if period_suffix is None:
            logger.warning(
                "KT overtime: unrecognized jaksotyö period words '%s'",
                m.group("period"),
            )
            continue

        start = m.start()
        end = m.end()
        snippet = zone[max(0, start - 40) : min(len(zone), end + 40)]
        source_text = " ".join(snippet.split())

        results.extend(
            _build_tier_rows(
                rate_type_context=f"jaksotyo_{period_suffix}",
                threshold_hours=_normalize_amount(m.group("hours")),
                tier1_pct=tier1_pct,
                tier2_pct=tier2_pct,
                source_text=source_text,
            )
        )

    return results


def _period_words_to_suffix(period_text: str) -> str | None:
    """ "kahden" -> "2vk"; "neljän ja kuuden" -> "4-6vk"."""
    numbers = []
    for word in period_text.split(" ja "):
        n = _word_to_number(word.strip())
        if n is None:
            return None
        numbers.append(str(n))
    return "-".join(numbers) + "vk"


def _word_to_number(word: str) -> int | None:
    word = word.strip().lower()
    if word.isdigit():
        return int(word)
    return _FI_NUMBER_WORDS.get(word)


def _build_tier_rows(
    rate_type_context: str,
    threshold_hours: Decimal,
    tier1_pct: Decimal,
    tier2_pct: Decimal,
    source_text: str,
) -> list[dict]:
    """Три rate-строки (порог часов, tier1%, tier2%) для одного режима/контекста."""
    common = {
        "wage_group": None,
        "rate_type_context": rate_type_context,
        "source_text": source_text,
    }
    return [
        {
            **common,
            "rate_type": RateType.OVERTIME_RATE_TIER1_HOURS.value,
            "value": threshold_hours,
            "unit": "hours",
        },
        {
            **common,
            "rate_type": RateType.OVERTIME_RATE_TIER1_PCT.value,
            "value": tier1_pct,
            "unit": "pct",
        },
        {
            **common,
            "rate_type": RateType.OVERTIME_RATE_TIER2_PCT.value,
            "value": tier2_pct,
            "unit": "pct",
        },
    ]


def _normalize_amount(amount_str: str) -> Decimal:
    normalized = amount_str.replace("\xa0", "").replace(" ", "").replace(",", ".")
    return Decimal(normalized.rstrip("."))


def _detect_mode(title_text: str) -> str | None:
    """Канонизирует заголовок сегмента в фиксированный ключ режима."""
    lowered = title_text.lower()
    if "vuorokautinen" in lowered or "vuorokautista" in lowered:
        return "vuorokautinen"
    if "viikoittainen" in lowered or "viikoittaista" in lowered:
        return "viikoittainen"
    return None


def find_segments_by_mom_header(text_fi: str) -> list[tuple[str, str]]:
    """
    Разбивает текст клаузулы на сегменты по заголовкам "N mom. Title".
    Возвращает список (title_text, segment_text). Если заголовков нет
    вообще — возвращает весь текст одним сегментом с пустым title_text
    (тогда _detect_mode("") вернёт None, и extract_kt_overtime уйдёт
    в ветку "Случай 2").
    """
    matches_before = list(_MOM_HEADER_BEFORE_RE.finditer(text_fi))
    matches_after = list(_MOM_HEADER_AFTER_RE.finditer(text_fi))
    matches = (
        matches_before if len(matches_before) >= len(matches_after) else matches_after
    )

    def nonempty_count(matches):
        return sum(1 for m in matches if m.group(1).strip())

    matches = (
        matches_before
        if nonempty_count(matches_before) >= nonempty_count(matches_after)
        else matches_after
    )

    if not matches:
        return [("", text_fi)]

    segments = []
    for i, match in enumerate(matches):
        title_text = match.group(1).strip()
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text_fi)
        segments.append((title_text, text_fi[start:end].strip()))

    return segments
