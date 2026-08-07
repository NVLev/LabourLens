import logging
import re
from datetime import date
from decimal import Decimal

from app.database.models import TesRate

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
    r"(?:ylityö)?tunni(?:lta|sta).{0,60}?"
    r"(?P<tier1_pct>\d+(?:,\d+)?)\s*(?:%(?::lla)?|prosentilla)"
    r".{0,60}?seuraav\w*\s+(?:\w+\s+)?tunn\w*.{0,60}?"
    r"(?P<tier2_pct>\d+(?:,\d+)?)\s*(?:%(?::lla)?|prosentilla)",
    re.IGNORECASE,
)

_MOM_HEADER_RE = re.compile(r"\d+\s*mom\.\s*([^\n]*)")

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
    "yksi": 1, "yhden": 1, "yhdeltä": 1,
    "kaksi": 2, "kahden": 2, "kahdelta": 2,
    "kolme": 3, "kolmen": 3, "kolmelta": 3,
    "neljä": 4, "neljän": 4, "neljältä": 4,
    "viisi": 5, "viiden": 5, "viideltä": 5,
    "kuusi": 6, "kuuden": 6, "kuudelta": 6,
    "seitsemän": 7, "seitsemältä": 7,
    "kahdeksan": 8, "kahdeksalta": 8,
    "yhdeksän": 9, "yhdeksältä": 9,
    "kymmenen": 10, "kymmeneltä": 10,
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

        snippet = text_fi[max(0, start - 40): min(len(text_fi), end + 40)]
        source_text = " ".join(snippet.split())

        results.append({
            "wage_group": None,
            "rate_type_context": None,
            "rate_type": "min_wage",
            "value": value,
            "unit": "eur_month",
            "effective_from": effective_from,
            "source_text": source_text,
        })

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
    segments = find_segments_overtime(text_fi)

    for title_text, segment in segments:
        rate_type_context = _detect_mode(title_text)

        if rate_type_context is not None:
            results.extend(_extract_case1_tiers(segment, rate_type_context))
        else:
            results.extend(_extract_compact_segment(segment))

    return results


def _extract_case1_tiers(segment: str, rate_type_context: str) -> list[dict]:
    """Случай 1: заголовок уже назвал режим, ищем тройку (порог, tier1%, tier2%)."""
    results = []

    for match in KT_OVERTIME_AMOUNT_RE.finditer(segment):
        start = match.start()
        end = match.end()

        snippet = segment[max(0, start - 40): min(len(segment), end + 40)]
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


def _build_tiers_from_compact_match(match: re.Match, mode: str, full_text: str) -> list[dict]:
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
    snippet = full_text[max(0, start - 40): min(len(full_text), end + 40)]
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

    zone = segment[anchor.start():]

    tier1_match = _JAKSOTYO_TIER1_RE.search(zone)
    tier2_match = _JAKSOTYO_TIER2_RE.search(zone)
    period_matches = list(_JAKSOTYO_PERIOD_RE.finditer(zone))

    if not tier1_match or not tier2_match or not period_matches:
        logger.warning(
            "KT overtime: jaksotyö zone found but pattern incomplete "
            "(tier1=%s, tier2=%s, periods=%d): %.120s",
            bool(tier1_match), bool(tier2_match), len(period_matches), zone,
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
        snippet = zone[max(0, start - 40): min(len(zone), end + 40)]
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
    """"kahden" -> "2vk"; "neljän ja kuuden" -> "4-6vk"."""
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
    common = {"wage_group": None, "rate_type_context": rate_type_context, "source_text": source_text}
    return [
        {**common, "rate_type": "overtime_rate_tier1_hours", "value": threshold_hours, "unit": "hours"},
        {**common, "rate_type": "overtime_rate_tier1_pct", "value": tier1_pct, "unit": "pct"},
        {**common, "rate_type": "overtime_rate_tier2_pct", "value": tier2_pct, "unit": "pct"},
    ]


def _normalize_amount(amount_str: str) -> Decimal:
    normalized = (
        amount_str
        .replace("\xa0", "")
        .replace(" ", "")
        .replace(",", ".")
    )
    return Decimal(normalized.rstrip("."))


def _detect_mode(title_text: str) -> str | None:
    """Канонизирует заголовок сегмента в фиксированный ключ режима."""
    lowered = title_text.lower()
    if "vuorokautinen" in lowered or "vuorokautista" in lowered:
        return "vuorokautinen"
    if "viikoittainen" in lowered or "viikoittaista" in lowered:
        return "viikoittainen"
    return None


def find_segments_overtime(text_fi: str) -> list[tuple[str, str]]:
    """
    Разбивает текст клаузулы на сегменты по заголовкам "N mom. Title".
    Возвращает список (title_text, segment_text). Если заголовков нет
    вообще — возвращает весь текст одним сегментом с пустым title_text
    (тогда _detect_mode("") вернёт None, и extract_kt_overtime уйдёт
    в ветку "Случай 2").
    """
    matches = list(_MOM_HEADER_RE.finditer(text_fi))
    if not matches:
        return [("", text_fi)]

    segments = []
    for i, match in enumerate(matches):
        title_text = match.group(1).strip()
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text_fi)
        segments.append((title_text, text_fi[start:end].strip()))

    return segments
