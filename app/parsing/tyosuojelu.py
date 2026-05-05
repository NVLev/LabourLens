import asyncio
import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import httpx
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)

TYOSUOJELU_PAGES = {
    # Трудовой договор
    "contract_types": "https://tyosuojelu.fi/tyosuhde/tyosopimus",
    "probation_period": "https://tyosuojelu.fi/tyosuhde/tyosopimus/koeaika",

    # Рабочее время
    "working_hours": "https://tyosuojelu.fi/tyosuhde/tyoaika/saannollinen",
    "overtime": "https://tyosuojelu.fi/tyosuhde/tyoaika/lisa-jaylityot",

    # Зарплата
    "sick_leave": "https://tyosuojelu.fi/tyosuhde/palkka/sairausajan-palkka",

    # Отпуск
    "annual_leave": "https://tyosuojelu.fi/tyosuhde/vuosiloma/lomapaivien-maara",
    "holiday_pay": "https://tyosuojelu.fi/tyosuhde/vuosiloma/lomapalkka-ja-korvaus",

    # Семья
    "parental_leave": "https://tyosuojelu.fi/tyosuhde/muut-vapaat-tyosta/perhevapaat",

    # Ломаутус
    "layoff": "https://tyosuojelu.fi/tyosuhde/lomautus",

    # Увольнение
    "dismissal_grounds": "https://tyosuojelu.fi/tyosuhde/tyosuhteen-paattyminen/sopimuksen-irtisanominen",
    "notice_period": "https://tyosuojelu.fi/tyosuhde/tyosuhteen-paattyminen/sopimuksen-irtisanominen/irtisanomisajat",
    "dismissal_protection": "https://tyosuojelu.fi/tyosuhde/tyosuhteen-paattyminen/erityistilanteet",

    # Дискриминация
    "discrimination": "https://tyosuojelu.fi/tyosuhde/yhdenvertaisuus/syrjinta",

    # Безопасность
    "workplace_safety": "https://tyosuojelu.fi/tyosuojelu-tyopaikalla/vaarojen-arviointi",
}



BASE_URL = "https://tyosuojelu.fi"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fi-FI,fi;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Connection": "keep-alive",
}



@dataclass
class ParsedFinlexRef:
    act_code: str
    chapter: Optional[int]
    section: int
    raw_text: str = ""



@dataclass
class ParsedInterpretation:
    topic_key: str
    source: str = "tyosuojelu"
    source_url: str = ""
    title_fi: str = ""

    # Секции контента
    general_fi: str = ""       # "Yleistä aiheesta"
    employee_fi: str = ""      # "Työntekijälle"
    employer_fi: str = ""      # "Työnantajalle"

    finlex_refs: list[ParsedFinlexRef] = field(default_factory=list)
    content_hash: str = ""
    parsed_at: datetime = field(default_factory=datetime.utcnow)

    def compute_hash(self) -> None:
        raw = self.general_fi + self.employee_fi + self.employer_fi
        self.content_hash = hashlib.sha256(raw.encode()).hexdigest()

    @property
    def full_text_fi(self) -> str:
        """Полный текст для перевода и хранения."""
        parts = []
        if self.general_fi:
            parts.append(self.general_fi)
        if self.employee_fi:
            parts.append(self.employee_fi)
        if self.employer_fi:
            parts.append(self.employer_fi)
        return "\n\n".join(parts)


class TyosuojeluParser:
    """
    Парсит тематические страницы tyosuojelu.fi.
    Использует httpx + BS4 — сайт на Liferay, рендерит на сервере.
    """
    SECTION_PATTERNS = {
        "general": ["yleistä aiheesta", "yleistä"],
        "employee": ["ohjeita työntekijälle", "työntekijälle"],
        "employer": ["ohjeita työnantajalle", "työnantajalle"],
    }

    def __init__(self, request_delay: float = 2.0, timeout: float = 30.0) -> None:
        self.request_delay = request_delay
        self.timeout = timeout

    # Публичные методы

    async def parse_all(self) -> list[ParsedInterpretation]:
        results = []
        for i, (topic_key, url) in enumerate(TYOSUOJELU_PAGES.items()):
            if i > 0:
                await asyncio.sleep(self.request_delay)
            try:
                result = await self.parse_page(topic_key, url)
                results.append(result)
                logger.info(
                    "Parsed %s: %d chars, %d finlex refs",
                    topic_key,
                    len(result.full_text_fi),
                    len(result.finlex_refs),
                )
            except Exception as e:
                logger.error("Failed to parse %s (%s): %s", topic_key, url, e)
        return results

    async def parse_page(self, topic_key: str, url: str) -> ParsedInterpretation:
        html = await self._fetch(url)
        soup = BeautifulSoup(html, "html.parser")

        result = ParsedInterpretation(
            topic_key=topic_key,
            source_url=url,
        )

        main = soup.find(id="main-content")
        if not main:
            logger.warning("No #main-content found at %s", url)
            return result

        h1 = main.find("h1", id="page-main-title")
        if h1:
            result.title_fi = h1.get_text(strip=True)

        result.general_fi = self._extract_section(main, "general")
        result.employee_fi = self._extract_section(main, "employee")
        result.employer_fi = self._extract_section(main, "employer")

        # Если все три секции пустые — страница имеет нестандартную структуру.
        # Собираем весь основной контент в general_fi.
        if not result.full_text_fi:
            result.general_fi = self._extract_full_content(main)

        result.finlex_refs = self._extract_finlex_refs(main)
        result.compute_hash()
        return result

    def _extract_full_content(self, main: Tag) -> str:
        """
        Fallback для страниц без стандартных секций.
        Собирает весь текст из #main-content, исключая
        служебные блоки (метаданные, навигация, SDG-пalkki).
        """
        SKIP_HEADINGS = {
            "sivun päivityspäivämäärä ja metatiedot",
            "sdg-palkki",
            "muualla tyosuojelu.fissä",
            "muualla verkossa",
            "lomakkeet",
            "sanasto",
            "usein kysytyt kysymykset",
            "ankkurilinkit",
            "tällä sivulla",
        }

        texts = []
        skip = False

        for el in main.find_all(["h2", "h3", "p", "ul", "ol"]):
            if el.name == "h2":
                heading_text = el.get_text(strip=True).lower()
                clean = re.sub(r"^.+\s*[-–]\s*", "", heading_text).strip()
                skip = clean in SKIP_HEADINGS
                continue

            if skip:
                continue

            # Пропускаем пустые и навигационные элементы
            t = " ".join(el.get_text().split())
            if t and len(t) > 20:  # игнорируем совсем короткие фрагменты
                texts.append(t)

        return "\n\n".join(texts)

    def _extract_section(self, main: Tag, section_name: str) -> str:
        """
        Ищет секцию по паттернам заголовков.
        Liferay дублирует заголовки — берём последний (реальный контент).
        """
        patterns = self.SECTION_PATTERNS.get(section_name, [section_name.lower()])

        matches = []
        for heading in main.find_all("h2"):
            text = heading.get_text(strip=True).lower()
            clean = re.sub(r"^.+\s*[-–]\s*", "", text).strip()
            if any(p == clean or p in text for p in patterns):
                matches.append(heading)

        if not matches:
            return ""
        heading = matches[-1]
        # Контент может быть:
        # 1. siblings самого h2 (если h2 и <p> на одном уровне)
        # 2. siblings родителя h2 (если h2 обёрнут в <div>/<section>)
        anchor = heading
        for _ in range(3):  # максимум 3 уровня вверх
            parent = anchor.parent
            if parent is None or parent == main:
                break
            siblings = list(parent.find_next_siblings())
            if siblings:
                anchor = parent
                break
            anchor = parent

        texts = []
        for sib in anchor.find_next_siblings():
            if sib.find("h2"):  # следующая секция
                break
            t = " ".join(sib.get_text().split())
            if t:
                texts.append(t)

        return "\n\n".join(texts)

    # Извлечение ссылок на законы

    def _extract_finlex_refs(self, main: Tag) -> list[ParsedFinlexRef]:
        """
        Извлекает ссылки на параграфы законов.
        Два источника:
        1. <a href="finlex.fi/..."> — ссылка на закон
        2. <li>N § текст</li> — список параграфов после ссылки на закон
        """
        refs = []
        seen_with_chapter = set()  # (act_code, chapter, section) — полный ключ
        seen_sections = set()  # (act_code, section) — для отсева дублей без главы

        current_act_code = None

        for el in main.find_all(["a", "li"]):
            if el.name == "a":
                href = el.get("href", "")
                if "finlex.fi" in href:
                    code = self._parse_act_code_from_url(href)
                    if code:
                        current_act_code = code

            elif el.name == "li" and current_act_code:
                text = el.get_text(strip=True)

                chap_m = re.search(r"(\d+)\s*luku", text, re.IGNORECASE)
                chapter = int(chap_m.group(1)) if chap_m else self._find_chapter_context(el)

                for sect_m in re.finditer(r"(\d+)\s*§", text):
                    section = int(sect_m.group(1))
                    section_key = (current_act_code, section)
                    full_key = (current_act_code, chapter, section)

                    # Если уже есть этот параграф с главой — пропускаем
                    if section_key in seen_sections and chapter is None:
                        continue
                    # Если уже есть точно такой же — пропускаем
                    if full_key in seen_with_chapter:
                        continue

                    seen_with_chapter.add(full_key)
                    seen_sections.add(section_key)
                    refs.append(ParsedFinlexRef(
                        act_code=current_act_code,
                        chapter=chapter,
                        section=section,
                        raw_text=text[:100],
                    ))

        return refs
    def _parse_act_code_from_url(self, url: str) -> str | None:
        """
        finlex.fi/fi/laki/ajantasa/2001/20010055 → "2001/55"
        """
        m = re.search(r"/(\d{4})/(\d{4,8})$", url)
        if not m:
            return None
        year = m.group(1)
        raw_num = m.group(2)
        # 20010055 → убираем год-префикс → "55"
        num = str(int(raw_num[len(year):]))
        return f"{year}/{num}"

    def _find_chapter_context(self, li: Tag) -> int | None:
        text = li.get_text(strip=True)
        m = re.search(r"(\d+)\s*luku", text, re.IGNORECASE)
        if m:
            return int(m.group(1))
        for sibling in li.find_previous_siblings("li"):
            t = sibling.get_text(strip=True)
            m = re.match(r"(\d+)\s+luku", t, re.IGNORECASE)
            if m:
                return int(m.group(1))
        return None

    # HTTP

    async def _fetch(self, url: str) -> str:
        async with httpx.AsyncClient(
            headers=HEADERS,
            follow_redirects=True,
            timeout=self.timeout,
        ) as client:
            for attempt in range(3):
                try:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    return resp.text
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429:
                        wait = 2 ** (attempt + 1)
                        logger.warning("Rate limited, waiting %ds", wait)
                        await asyncio.sleep(wait)
                    else:
                        raise
                except httpx.RequestError as e:
                    if attempt == 2:
                        raise
                    logger.warning("Request error %s, retry %d/3", e, attempt + 1)
                    await asyncio.sleep(2)
        raise RuntimeError(f"Failed to fetch {url} after 3 attempts")