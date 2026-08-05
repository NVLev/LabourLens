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

KT_OVERTIME_AMOUNT_RE = re.compile(
    r"(?P<threshold_hours>\d+)\s+ensimm(?:äi|ai)selt[äa]\s+"
    r"(?:ylityö)?tunni(?:lta|sta).{0,60}?"
    r"(?P<tier1_pct>\d+(?:,\d+)?)\s*(?:%(?::lla)?|prosentilla)"
    r".{0,60}?seuraav\w*\s+(?:\w+\s+)?tunn\w*.{0,60}?"
    r"(?P<tier2_pct>\d+(?:,\d+)?)\s*(?:%(?::lla)?|prosentilla)",
    re.IGNORECASE,
)

_MOM_HEADER_RE = re.compile(r"\d+\s*mom\.\s*([^\n]*)")

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

        normalized = (
            amount_str
            .replace("\xa0", "")
            .replace(" ", "")
            .replace(",", ".")
        )
        value = Decimal(normalized.rstrip(","))

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
   results = []
   segments = find_segments_overtime(text_fi)
   for type_context, segment in segments:
       rate_type_context = _detect_mode(type_context)
       for match in KT_OVERTIME_AMOUNT_RE.finditer(segment):
           start = match.start()
           end = match.end()

           snippet = segment[max(0, start - 40): min(len(segment), end + 40)]
           source_text = " ".join(snippet.split())
           if match.group("threshold_hours"):
                rate_type = "overtime_rate_tier1_hours"
                unit = "hours"
                amount_str = match.group("threshold_hours")
                value = _normalize_amount(amount_str)
                results.append(
                    {
                        "wage_group": None,
                        "rate_type": rate_type,
                        "rate_type_context": rate_type_context,
                        "value": value,
                        "unit": unit,
                        "source_text": source_text,
                    }
                )
           if match.group("tier1_pct"):
                rate_type = "overtime_rate_tier1_pct"
                unit = "pct"
                amount_str = match.group("tier1_pct")
                value = _normalize_amount(amount_str)
                results.append(
                {
                    "wage_group": None,
                    "rate_type": rate_type,
                    "rate_type_context": rate_type_context,
                    "value": value,
                    "unit": unit,
                    "source_text": source_text,
                }
                )
           if match.group("tier2_pct"):
               rate_type = "overtime_rate_tier2_pct"
               unit = "pct"
               amount_str = match.group("tier2_pct")
               value = _normalize_amount(amount_str)
               results.append(
                   {
                       "wage_group": None,
                       "rate_type": rate_type,
                       "rate_type_context": rate_type_context,
                       "value": value,
                       "unit": unit,
                       "source_text": source_text,
                   }
            )
   return results

def _normalize_amount(amount_str) -> Decimal:
    normalized = (
        amount_str
        .replace(" ", "")
        .replace(",", ".")
    )
    value = Decimal(normalized.rstrip(","))
    return value


def _detect_mode(title_text: str) -> str | None:
    """Переформатирует заголовок сегмента в фиксированный ключ режима."""
    lowered = title_text.lower()
    if "vuorokautinen" in lowered or "vuorokautista" in lowered:
        return "vuorokautinen"
    if "viikoittainen" in lowered or "viikoittaista" in lowered:
        return "viikoittainen"
    return None


def find_segments_overtime(text_fi: str) -> list[tuple[str, str]]:
    """
    Разбивает текст клаузулы на сегменты по заголовкам "N mom. Title".
    Возвращает список (title_text, segment_text).
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







