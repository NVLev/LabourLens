"""
Парсер коллективных договоров (TES) с сайта kt.fi.

KT = Kunta- ja hyvinvointialuetyönantajat — работодательская организация
муниципального и социально-здравоохранительного секторов Финляндии.

Договоры на kt.fi — это HTML. Структура трёхуровневая:

  1. Каталог    https://www.kt.fi/sopimukset
       ссылки вида /sopimukset/{slug}/{YYYY-YYYY}

  2. Страница договора  https://www.kt.fi/sopimukset/{slug}/{YYYY-YYYY}
       og:title = название
       ссылка «Avaa koko sopimus» → /sopimukset/{slug}/{YYYY-YYYY}/kokoteksti

  3. Полный текст  .../kokoteksti
       div.contract-content > div.field-item
       <h3>N § Название</h3> + следующие теги — клаузулы

Данные сохраняются в модель Agreement + TesClause (не Interpretation).
"""

import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import date

import httpx
from bs4 import BeautifulSoup

from app.parsing.topic_keywords import detect_topic

logger = logging.getLogger(__name__)

KT_BASE_URL = "https://www.kt.fi"
KT_CATALOG_URL = "https://www.kt.fi/sopimukset"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fi-FI,fi;q=0.9",
}

# Паттерн ссылок на версионированные договоры: /sopimukset/{slug}/{YYYY-YYYY}
_VERSION_URL_RE = re.compile(
    r"^(?:https://www\.kt\.fi)?/sopimukset/([^/]+)/(20\d{2}-20\d{2})$"
)

_VOIMASSA_RE = re.compile(r"voimassa\s+(\d{1,2})\.(\d{1,2})\.(\d{4})", re.IGNORECASE)

_SLUG_SECTOR: dict[str, str] = {
    "kvtes": "Kunta-ala, yleinen",
    "hyvtes": "Hyvinvointiala, yleinen",
    "sote": "Sosiaali- ja terveydenhuolto",
    "otes": "Opetusala, tuntipalkkaiset",
    "ovtes": "Opetusala",
    "ytes": "Yliopistoala",
    "tekniset": "Tekniset",
    "tuntipalkkaiset": "Tuntipalkkaiset",
    "laakarit": "Lääkärit",
    "vuokra-tes": "Henkilöstövuokrausala",
}


@dataclass
class KtDiscoveredTes:
    """Найденный договор — до загрузки полного текста."""

    slug: str
    period: str
    index_url: str
    full_url: str  # URL kokoteksti
    name_fi: str
    valid_from: str | None
    valid_until: str | None
    sector_fi: str


@dataclass
class KtParsedClause:
    """Одна клаузура (§) договора."""

    section_ref: str  # "§ 22"
    title_fi: str  # "Työaika"
    text_fi: str
    topic_key: str | None


@dataclass
class KtParsedAgreement:
    """Полностью распарсенный договор, готовый к сохранению."""

    union_key: str  # "kt"
    key: str  # "kt-kvtes-2025-2028"
    name_fi: str
    valid_from: str | None
    valid_until: str | None
    source_url: str
    content_hash: str
    sector_fi: str
    is_universally_binding: bool = True
    clauses: list[KtParsedClause] = field(default_factory=list)


class KtParser:
    """
    Трёхшаговый парсер kt.fi:
      1. discover()   — каталог → список KtDiscoveredTes
      2. parse_one()  — kokoteksti → KtParsedAgreement
      3. parse_all()  — discover() + parse_one() для каждого
    """

    def __init__(self, timeout: float = 30.0) -> None:
        self.timeout = timeout

    # обнаружение договоров

    async def discover(self) -> list[KtDiscoveredTes]:
        """
        Сканирует https://www.kt.fi/sopimukset.
        Возвращает список найденных версионированных договоров.
        """
        async with httpx.AsyncClient(
            headers=HEADERS, follow_redirects=True, timeout=self.timeout
        ) as client:
            html = await self._fetch(client, KT_CATALOG_URL)
            soup = BeautifulSoup(html, "html.parser")

            seen: set[str] = set()
            candidates: list[tuple[str, str]] = []
            for a in soup.find_all("a", href=True):
                href = str(a["href"])
                m = _VERSION_URL_RE.match(href)
                if not m:
                    continue
                slug, period = m.group(1), m.group(2)
                key = f"{slug}/{period}"
                # if key in seen or slug in _SLUG_IGNORE:
                #     continue
                seen.add(key)
                candidates.append((slug, period))

            logger.info("KT catalog: %d candidate agreements", len(candidates))

            results = []
            for slug, period in candidates:
                index_url = f"{KT_BASE_URL}/sopimukset/{slug}/{period}"
                try:
                    d = await self._fetch_index_page(client, slug, period, index_url)
                    if d:
                        results.append(d)
                        logger.info(
                            "KT discovered: %s/%s — %s", slug, period, d.name_fi[:50]
                        )
                except Exception as e:
                    logger.error("KT: failed index %s/%s: %s", slug, period, e)

        logger.info("KT: discovered %d agreements total", len(results))
        return results

    async def _fetch_index_page(
        self,
        client: httpx.AsyncClient,
        slug: str,
        period: str,
        index_url: str,
    ) -> KtDiscoveredTes | None:
        html = await self._fetch(client, index_url)
        soup = BeautifulSoup(html, "html.parser")

        # Название из og:title
        og = soup.find("meta", property="og:title")
        name_fi = og.get("content", "").strip() if og else slug.upper()
        # Убираем мусорный суффикс
        name_fi = re.sub(
            r"\s*[-–]\s*sähköinen sopimuskirja\s*[>»]?\s*$",
            "",
            name_fi,
            flags=re.IGNORECASE,
        ).strip()
        name_fi = (
            name_fi.replace("–", "-")
            .replace("—", "-")
            .replace("?", "-")
            .replace("−", "-")
        )
        # Ссылка «Avaa koko sopimus» → kokoteksti
        full_url = None
        for a in soup.find_all("a", href=True):
            href = str(a["href"])
            if href.endswith("/kokoteksti"):
                full_url = f"{KT_BASE_URL}{href}" if href.startswith("/") else href
                break

        if not full_url:
            logger.warning("KT: no kokoteksti link for %s/%s", slug, period)
            return None

        name_from, _ = self._extract_dates_from_name(name_fi)

        name_from, name_until = self._extract_dates_from_name(name_fi)

        logger.debug(
            "KT DATE PARSE: raw='%s' → from=%s until=%s",
            name_fi,
            name_from,
            name_until,
        )
        period_from, period_until = self._parse_period(period)

        valid_from = name_from or period_from
        valid_until = name_until or period_until

        sector_fi = _SLUG_SECTOR.get(slug, slug.replace("-", " ").capitalize())

        return KtDiscoveredTes(
            slug=slug,
            period=period,
            index_url=index_url,
            full_url=full_url,
            name_fi=name_fi,
            valid_from=valid_from,
            valid_until=valid_until,
            sector_fi=sector_fi,
        )

    # парсинг клаузур

    async def parse_one(self, discovered: KtDiscoveredTes) -> KtParsedAgreement:
        """Загружает kokoteksti и извлекает все клаузулы."""
        clauses = await self.fetch_and_parse(discovered.full_url)
        content_hash = hashlib.sha256(
            "\n".join(c.text_fi for c in clauses).encode()
        ).hexdigest()

        return KtParsedAgreement(
            union_key="kt",
            key=f"kt-{discovered.slug}-{discovered.period}",
            name_fi=discovered.name_fi,
            valid_from=discovered.valid_from,
            valid_until=discovered.valid_until,
            source_url=discovered.full_url,
            content_hash=content_hash,
            sector_fi=discovered.sector_fi,
            is_universally_binding=True,
            clauses=clauses,
        )

    async def parse_all(self) -> list[KtParsedAgreement]:
        """Обнаруживает и парсит все договоры с kt.fi."""
        discovered = await self.discover()
        results = []
        async with httpx.AsyncClient(
            headers=HEADERS, follow_redirects=True, timeout=self.timeout
        ) as client:
            for d in discovered:
                try:
                    html = await self._fetch(client, d.full_url)
                    clauses = self._extract_clauses(html)
                    content_hash = hashlib.sha256(
                        "\n".join(c.text_fi for c in clauses).encode()
                    ).hexdigest()
                    results.append(
                        KtParsedAgreement(
                            union_key="kt",
                            key=f"kt-{d.slug}-{d.period}",
                            name_fi=d.name_fi,
                            valid_from=d.valid_from,
                            valid_until=d.valid_until,
                            source_url=d.full_url,
                            content_hash=content_hash,
                            sector_fi=d.sector_fi,
                            is_universally_binding=True,
                            clauses=clauses,
                        )
                    )
                    logger.info(
                        "KT: parsed %-40s — %d clauses", d.name_fi[:40], len(clauses)
                    )
                except Exception as e:
                    logger.error("KT: failed %s: %s", d.full_url, e)
        return results

    # Извлечение клаузур

    def _extract_clauses(self, html: str) -> list[KtParsedClause]:
        """
        Разбивает kokoteksti на клаузулы по <h3>N § Название</h3>.

        Структура страницы:
          div.contract-content
            div.field-item          ← основной контент
              <h3>1 § ...</h3>
              <p>текст</p>
              <h4>момент</h4>
              <p>текст</p>
              ...
              <h3>2 § ...</h3>
              ...

        Важно: h3 с § находятся в div.field-item, но не в article —
        ищем их по всему документу.
        """
        soup = BeautifulSoup(html, "html.parser")

        # Все h3 с § в документе
        section_headers = [h for h in soup.find_all("h3") if "§" in h.get_text()]
        if not section_headers:
            logger.warning("KT: no § h3 headers found in page")
            return []

        clauses: list[KtParsedClause] = []
        for i, header in enumerate(section_headers):
            title_text = header.get_text(strip=True)
            m = re.match(r"^(\d+)\s*§\s*(.*)$", title_text)
            section_ref = f"§ {m.group(1)}" if m else "§ ?"
            title_fi = m.group(2).strip() if m else title_text

            # Текст: все siblings до следующего h3 с §
            text_parts: list[str] = []
            next_header = (
                section_headers[i + 1] if i + 1 < len(section_headers) else None
            )
            for sib in header.find_next_siblings():
                if sib == next_header:
                    break
                if sib.name == "h3" and "§" in sib.get_text():
                    break
                text = sib.get_text(separator=" ", strip=True)
                if text:
                    text_parts.append(text)

            clause_text = "\n\n".join(text_parts).strip()
            if len(clause_text) < 80:
                continue  # слишком короткие — артефакты

            topic_key = self._resolve_topic(title_fi, clause_text)
            clauses.append(
                KtParsedClause(
                    section_ref=section_ref,
                    title_fi=title_fi,
                    text_fi=clause_text,
                    topic_key=topic_key,
                )
            )

        logger.debug("KT: extracted %d clauses", len(clauses))
        return clauses

    # Утилиты
    def _extract_dates_from_name(self, name: str) -> tuple[date | None, date | None]:
        """
        Парсит даты из строки типа:
        'YTES 2025–2028, voimassa 1.5.2025 lukien'
        """

        # 1. voimassa 1.5.2025
        m = re.search(r"voimassa\s+(\d{1,2})\.(\d{1,2})\.(\d{4})", name, re.IGNORECASE)
        if m:
            d, mth, y = map(int, m.groups())
            return date(y, mth, d), None

        # 2. диапазон 2025–2028 или 2025-2028
        m = re.search(r"(20\d{2})\s*[–-]\s*(20\d{2})", name)
        if m:
            y1, y2 = map(int, m.groups())
            return date(y1, 1, 1), date(y2, 12, 31)

        return None, None

    def _parse_valid_until(self, name: str, period: str) -> date | None:
        """
        Пока просто fallback на period
        """
        _, until = self._parse_period(period)
        return until

    async def fetch_and_parse(self, url: str) -> list[KtParsedClause]:
        async with httpx.AsyncClient(
            headers=HEADERS, follow_redirects=True, timeout=self.timeout
        ) as client:
            html = await self._fetch(client, url)
        return self._extract_clauses(html)

    def _resolve_topic(self, title_fi: str, text_fi: str = "") -> str | None:
        topic = detect_topic(title_fi)
        if topic:
            return topic
        if text_fi:
            return detect_topic(text_fi[:500])
        return None

    def _parse_period(self, period: str) -> tuple[date | None, date | None]:
        """
        '2025-2028' → (2025-01-01, 2028-12-31)
        """
        try:
            y1, y2 = map(int, period.split("-"))
            return date(y1, 1, 1), date(y2, 12, 31)
        except Exception:
            return None, None

    @staticmethod
    async def _fetch(client: httpx.AsyncClient, url: str) -> str:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.text
