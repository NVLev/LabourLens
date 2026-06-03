import logging
import re
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select

from app.database.models import Interpretation
from app.parsing.topic_keywords import detect_topic

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fi-FI,fi;q=0.9",
}

TEHY_BASE_URL = "https://www.tehy.fi"
TEHY_CATALOG_URL = "https://www.tehy.fi/fi/tyoelamaopas/tyoehtosopimukset"

TEHY_AGREEMENTS: dict[str, dict] = {
    "sote-sopimus": {
        "name_fi": "Sosiaali- ja terveydenhuollon henkilöstön työ- ja virkaehtosopimus",
        "sector_fi": "Sosiaali- ja terveydenhuolto",
    },
    "kvtes-kunta-alan-yleinen-virka-ja-tyoehtosopimus": {
        "name_fi": "Kunta-alan yleinen virka- ja työehtosopimus KVTES",
        "sector_fi": "Kunnallinen sektori",
    },
    "hyvtes-hyvinvointialan-yleinen-virka-ja-tyoehtosopimus": {
        "name_fi": "Hyvinvointialan yleinen virka- ja työehtosopimus HYVTES",
        "sector_fi": "Hyvinvointiala",
    },
    "tptes-terveyspalvelualan-tyoehtosopimus": {
        "name_fi": "Terveyspalvelualan työehtosopimus TPTES",
        "sector_fi": "Yksityinen terveyspalveluala",
    },
    "sostes-yksityisen-sosiaalipalvelualan-tyoehtosopimus": {
        "name_fi": "Yksityisen sosiaalipalvelualan työehtosopimus SOSTES",
        "sector_fi": "Yksityinen sosiaalipalveluala",
    },
    "vakates-yksityisen-varhaiskasvatusalan-tyoehtosopimus": {
        "name_fi": "Yksityisen varhaiskasvatusalan työehtosopimus VAKATES",
        "sector_fi": "Yksityinen varhaiskasvatus",
    },
    "ensihoitotes": {
        "name_fi": "Ensihoitoalan työehtosopimus",
        "sector_fi": "Ensihoito",
    },
    "finnhems-tes": {
        "name_fi": "FinnHEMS Oy:n työehtosopimus",
        "sector_fi": "Lentokuljetukset",
    },
    "hammastes-hammaslaakarien-tyonantajayhdistyksen-ja-tehyn-valinen-tyoehtosopimus": {
        "name_fi": "Hammaslääkärien työnantajayhdistyksen ja Tehyn välinen TES",
        "sector_fi": "Hammashoito",
    },
    "tyoterveyslaitoksen-tes": {
        "name_fi": "Työterveyslaitoksen työehtosopimus",
        "sector_fi": "Työterveyslaitos",
    },
}


@dataclass
class ParsedTehySection:
    title_fi: str
    text_fi: str
    topic_key: str | None
    source_url: str
    sector_fi: str
    agreement_name_fi: str


class TehyParser:
    """
    Парсит страницы интерпретаций TES на tehy.fi.

    Для каждого договора из TEHY_AGREEMENTS:
    - Загружает страницу
    - Разбивает по <h2> на секции
    - Маппит каждую секцию на топик по ключевым словам заголовка
    - Возвращает список ParsedTehySection
    """

    async def parse_all(self) -> list[ParsedTehySection]:
        results = []
        async with httpx.AsyncClient(
            headers=HEADERS, follow_redirects=True, timeout=20
        ) as client:
            for slug, meta in TEHY_AGREEMENTS.items():
                url = f"{TEHY_BASE_URL}/fi/tyoelamaopas/tyoehtosopimukset/{slug}"
                try:
                    sections = await self._parse_page(client, url, meta)
                    results.extend(sections)
                    logger.info("Tehy: parsed %d sections from %s", len(sections), slug)
                except Exception as e:
                    logger.error("Tehy: failed to parse %s: %s", slug, e)
        return results

    async def parse_one(self, slug: str) -> list[ParsedTehySection]:
        if slug not in TEHY_AGREEMENTS:
            raise ValueError(
                f"Unknown Tehy agreement slug: {slug}. "
                f"Available: {list(TEHY_AGREEMENTS.keys())}"
            )
        meta = TEHY_AGREEMENTS[slug]
        url = f"{TEHY_BASE_URL}/fi/tyoelamaopas/tyoehtosopimukset/{slug}"
        async with httpx.AsyncClient(
            headers=HEADERS, follow_redirects=True, timeout=20
        ) as client:
            return await self._parse_page(client, url, meta)

    async def _parse_page(
        self,
        client: httpx.AsyncClient,
        url: str,
        meta: dict,
    ) -> list[ParsedTehySection]:
        resp = await client.get(url)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        # Ищем основной контент — убираем футер и навигацию
        main = soup.find("main") or soup.find("article") or soup.body

        sections = []
        current_title: str | None = None
        current_paragraphs: list[str] = []

        for tag in main.descendants:
            if tag.name == "h2":
                # Сохраняем предыдущую секцию
                if current_title and current_paragraphs:
                    section = self._build_section(
                        current_title, current_paragraphs, url, meta
                    )
                    if section:
                        sections.append(section)
                current_title = tag.get_text(strip=True)
                current_paragraphs = []
            elif tag.name == "p" and current_title:
                text = tag.get_text(strip=True)
                if text:
                    current_paragraphs.append(text)

        # Последняя секция
        if current_title and current_paragraphs:
            section = self._build_section(current_title, current_paragraphs, url, meta)
            if section:
                sections.append(section)

        return sections

    def _build_section(
        self,
        title: str,
        paragraphs: list[str],
        url: str,
        meta: dict,
    ) -> ParsedTehySection | None:
        text = "\n\n".join(paragraphs)
        if len(text) < 50:
            return None
        topic_key = self._resolve_topic(title, text)
        if topic_key is None:
            logger.debug("Tehy: no topic for section '%s'", title[:60])
            return None
        return ParsedTehySection(
            title_fi=title,
            text_fi=text,
            topic_key=topic_key,
            source_url=url,
            sector_fi=meta["sector_fi"],
            agreement_name_fi=meta["name_fi"],
        )

    def _resolve_topic(self, title_fi: str, text_fi: str) -> str | None:
        # Фильтр мусорных заголовков
        if not self._is_noise_title(title_fi):
            title_topic = detect_topic(title_fi)
        else:
            title_topic = None

        snippet = text_fi[:1000]
        text_topic = detect_topic(snippet)

        if title_topic and text_topic:
            if title_topic == text_topic:
                return title_topic
            return title_topic  # приоритет заголовка

        return title_topic or text_topic

    def _is_noise_title(self, title: str) -> bool:
        title_l = title.lower().strip()
        return (
            len(title_l) < 8
            or title_l.endswith("?")
            or "liity" in title_l
            or title_l in {"tehy footer", "tehy footer bottom"}
            or (
                title_l.startswith(tuple(f"{i}." for i in range(1, 10)))
                and len(title_l) < 20
            )
        )
