import re
from datetime import date
from decimal import Decimal

from app.database.models import TesRate

KT_DATE_AMOUNT_RE = re.compile(
    r"(\d{1,2}\.\d{1,2}\.\d{4})"
    r"\s+(?:alkaen|lukien)\s+"
    r"(\d[\d\s\xa0]*(?:,\d{2})?)"     
    r"(?:\s*(?:€/kk|euroa|€))?",
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

