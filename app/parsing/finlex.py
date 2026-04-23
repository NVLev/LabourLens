import asyncio
import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime

import httpx
from lxml import etree

logger = logging.getLogger(__name__)

# XML namespace
AKN_NS = "http://docs.oasis-open.org/legaldocml/ns/akn/3.0"
NS = {"akn": AKN_NS}

def akn(tag: str) -> str:
    """Возвращает тег с namespace: akn('chapter') → '{http://...}chapter'"""
    return f"{{{AKN_NS}}}{tag}"


# Конфигурация законов

ACTS_CONFIG = {
    "tyosopimuslaki": {
        "name_fi": "Työsopimuslaki",
        "code": "2001/55",
        "api_url": "https://opendata.finlex.fi/finlex/avoindata/v1/akn/fi/act/statute/2001/55/fin@",
        "web_url": "https://www.finlex.fi/fi/lainsaadanto/2001/55",
        "priority_chapters": [1, 2, 6, 7],
    },
    "vuosilomalaki": {
        "name_fi": "Vuosilomalaki",
        "code": "2005/162",
        "api_url": "https://opendata.finlex.fi/finlex/avoindata/v1/akn/fi/act/statute/2005/162/fin@",
        "web_url": "https://www.finlex.fi/fi/lainsaadanto/2005/162",
        "priority_chapters": [],
    },
    "tyoaikalaki": {
        "name_fi": "Työaikalaki",
        "code": "2019/872",
        "api_url": "https://opendata.finlex.fi/finlex/avoindata/v1/akn/fi/act/statute/2019/872/fin@",
        "web_url": "https://www.finlex.fi/fi/lainsaadanto/2019/872",
        "priority_chapters": [2, 3],
    },
    "tyoturvallisuuslaki": {
        "name_fi": "Työturvallisuuslaki",
        "code": "2002/738",
        "api_url": "https://opendata.finlex.fi/finlex/avoindata/v1/akn/fi/act/statute/2002/738/fin@",
        "web_url": "https://www.finlex.fi/fi/lainsaadanto/2002/738",
        "priority_chapters": [],
    },
}


# Датаклассы

@dataclass
class ParsedParagraph:
    order_index: int
    text_fi: str


@dataclass
class ParsedSection:
    chapter_number: int
    number: int
    title_fi: str
    anchor: str           # "chp_1__sec_1"
    url: str
    paragraphs: list[ParsedParagraph] = field(default_factory=list)
    content_hash: str = ""

    def compute_hash(self) -> None:
        raw = "".join(p.text_fi for p in self.paragraphs)
        self.content_hash = hashlib.sha256(raw.encode()).hexdigest()


@dataclass
class ParsedChapter:
    number: int
    title_fi: str
    sections: list[ParsedSection] = field(default_factory=list)


@dataclass
class ParsedAct:
    key: str
    name_fi: str
    code: str
    url: str
    parsed_at: datetime
    chapters: list[ParsedChapter] = field(default_factory=list)


# Парсер

class FinlexParser:
    """
    Получает законы через официальный Finlex Open Data API.
    Формат ответа — Akoma Ntoso XML.
    Авторизация не требуется.
    """

    def __init__(self, request_delay: float = 1.5, timeout: float = 30.0) -> None:
        self.request_delay = request_delay
        self.timeout = timeout

    # Публичные методы
    async def parse_act(self, act_key: str) -> ParsedAct:
        config = ACTS_CONFIG[act_key]
        logger.info("Fetching act: %s from %s", act_key, config["api_url"])

        xml_bytes = await self._fetch(config["api_url"])
        root = etree.fromstring(xml_bytes)

        act = ParsedAct(
            key=act_key,
            name_fi=config["name_fi"],
            code=config["code"],
            url=config["web_url"],
            parsed_at=datetime.utcnow(),
            chapters=self._parse_chapters(root, config["web_url"]),
        )

        logger.info(
            "Parsed %s: %d chapters, %d sections",
            act_key,
            len(act.chapters),
            sum(len(ch.sections) for ch in act.chapters),
        )
        return act

    async def parse_all(self) -> list[ParsedAct]:
        results = []
        for i, act_key in enumerate(ACTS_CONFIG):
            if i > 0:
                await asyncio.sleep(self.request_delay)
            results.append(await self.parse_act(act_key))
        return results

    # Парсинг XML
    def _parse_chapters(self, root: etree._Element, web_url: str) -> list[ParsedChapter]:
        chapters = []

        # Все chapter внутри body → hcontainer
        for chp_el in root.findall(
            f".//{akn('chapter')}"
        ):
            chp_num = self._parse_chapter_number(chp_el)
            if chp_num is None:
                continue

            title_fi = self._text(chp_el.find(akn("heading"))) or f"Luku {chp_num}"

            chapter = ParsedChapter(number=chp_num, title_fi=title_fi)

            for sec_el in chp_el.findall(akn("section")):
                section = self._parse_section(sec_el, chp_num, web_url)
                if section:
                    chapter.sections.append(section)

            chapters.append(chapter)

        return chapters

    def _parse_section(
        self,
        sec_el: etree._Element,
        chapter_num: int,
        web_url: str,
    ) -> ParsedSection | None:
        eid = sec_el.get("eId", "")
        # "chp_1__sec_3" → section_num = 3
        m = re.search(r"__sec_(\d+)$", eid)
        if not m:
            return None
        section_num = int(m.group(1))

        title_fi = self._text(sec_el.find(akn("heading"))) or ""
        # Убираем номер параграфа из заголовка если он туда попал
        title_fi = re.sub(r"^\d+\s*§\s*", "", title_fi).strip()

        section = ParsedSection(
            chapter_number=chapter_num,
            number=section_num,
            title_fi=title_fi,
            anchor=eid,
            url=f"{web_url}#{eid}",
        )

        # Собираем пункты
        paragraphs = self._collect_paragraphs(sec_el)
        section.paragraphs = [
            ParsedParagraph(order_index=i, text_fi=text)
            for i, text in enumerate(paragraphs)
        ]
        section.compute_hash()
        return section

    def _collect_paragraphs(self, sec_el: etree._Element) -> list[str]:
        """
        Собирает текст всех subsection в плоский список строк.
        Обрабатывает три структуры которые встречаются в AKN:

        1. Простой пункт:
           subsection → content → p

        2. Пункт с вводной фразой и подпунктами:
           subsection → intro → p
                      → paragraph[1)] → content → p
                      → paragraph[2)] → content → p

        3. Пункт с несколькими content:
           subsection → content → p (несколько)
        """
        texts = []

        for subsec in sec_el.findall(akn("subsection")):
            parts = []

            # intro — вводная фраза ("Tätä lakia ei sovelleta:")
            intro = subsec.find(akn("intro"))
            if intro is not None:
                t = self._extract_text(intro)
                if t:
                    parts.append(t)

            # вложенные нумерованные подпункты paragraph 1), 2)...
            sub_paragraphs = subsec.findall(akn("paragraph"))
            if sub_paragraphs:
                for para in sub_paragraphs:
                    num_el = para.find(akn("num"))
                    num = (self._text(num_el) or "").strip()
                    content_text = self._extract_text(para.find(akn("content")))
                    if content_text:
                        parts.append(f"{num} {content_text}".strip())
            else:
                # простой content без подпунктов
                content = subsec.find(akn("content"))
                if content is not None:
                    t = self._extract_text(content)
                    if t:
                        parts.append(t)

            if parts:
                # Весь subsection — одна запись в paragraphs
                texts.append(" ".join(parts))

        return texts

    # Вспомогательные
    def _parse_chapter_number(self, chp_el: etree._Element) -> int | None:
        """'1 luku' → 1"""
        num_el = chp_el.find(akn("num"))
        if num_el is None:
            return None
        m = re.match(r"(\d+)", self._text(num_el) or "")
        return int(m.group(1)) if m else None

    def _extract_text(self, el: etree._Element | None) -> str:
        """Рекурсивно собирает текст из элемента включая дочерние теги (i, b, ref...)."""
        if el is None:
            return ""
        # itertext() обходит весь поддерев включая tail
        return " ".join(
            t.strip() for t in el.itertext() if t.strip()
        )

    def _text(self, el: etree._Element | None) -> str | None:
        """Текст одного элемента, None если элемент отсутствует."""
        if el is None:
            return None
        return (el.text or "").strip() or None

    # HTTP

    async def _fetch(self, url: str) -> bytes:
        headers = {
            "User-Agent": "LabourLens/1.0",
            "Accept": "application/xml",
            "Accept-Encoding": "gzip",
        }
        async with httpx.AsyncClient(
            headers=headers,
            follow_redirects=True,
            timeout=self.timeout,
        ) as client:
            for attempt in range(3):
                try:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    return resp.content
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