
import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import date
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from app.parsing.topic_keywords import detect_topic

logger = logging.getLogger(__name__)

PAM_BASE_URL = "https://www.pam.fi"
PAM_DOMAIN = "pam.fi"
PAM_CATALOG_URL = "https://www.pam.fi/tyoehtosopimukset/"
PAM_URL_MARKER = "/tes/"

VALIDITY_RE = re.compile(
    r"(\d{1,2}\.\d{1,2}\.\d{4})\s*[–-]\s*(\d{1,2}\.\d{1,2}\.\d{4})"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fi-FI,fi;q=0.9",
}

@dataclass
class PamDiscoveredTes:
    """Найденный договор — до загрузки полного текста."""
    key: str
    index_url: str
    links: list
    name_fi: str
    valid_from: str | None
    valid_until: str | None
    sector_fi: str

@dataclass
class PamParsedClause:
    """Одна клаузура (§) договора."""

    section_ref: str  # "§ 22"
    title_fi: str  # "Työaika"
    text_fi: str
    topic_key: str | None

@dataclass
class PamParsedAgreement:
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
    clauses: list[PamParsedClause] = field(default_factory=list)

class PamParser:
    """
    Парсер коллективных договоров (TES) с сайта pam.fi.

    PAM = Palvelualojen ammattiliitto — профсоюз работников сферы услуг.
    Договоры на pam.fi опубликованы в HTML, не PDF. Структура трёхуровневая:

      1. Каталог    https://www.pam.fi/tyoehtosopimukset/
           ссылки вида /tes/{slug}/

      2. Индексная страница   https://www.pam.fi/tes/{slug}/
           <h1> = название договора
           ссылки /taysi/{chapter}/ = главы договора
           текст с датами вида "1.2.2025–31.1.2028"

      3. Страница главы   .../taysi/{chapter}/
           div.pam-tes-official__content
           <h2>N § Название</h2> + следующие теги — клаузулы

    Данные сохраняются в модель Agreement + TesClause (не Interpretation).
    """

    def __init__(self, timeout: float = 30.0) -> None:
        self.timeout = timeout

    # обнаружение договоров

    async def discover(self) -> list[PamDiscoveredTes]:
        """
         Шаг 1: сканирует каталог pam.fi, возвращает список найденных договоров.

        Для каждого договора извлекает метаданные (название, даты, ссылки на главы)
        с его индексной страницы. Клаузулы не парсит.
        """
        async with httpx.AsyncClient(
            headers=HEADERS, follow_redirects=True, timeout=self.timeout
        ) as client:
            html = await self._fetch(client, PAM_CATALOG_URL)
            soup = BeautifulSoup(html, "html.parser")

            seen: set[str] = set()
            index_pages = []
            for a in soup.find_all("a", href=True):
                href = str(a["href"])
                if not self._is_tes_page_url(href):
                    continue
                # Нормализуем относительные ссылки
                if href.startswith("/"):
                    href = f"https://{PAM_DOMAIN}{href}"
                if href not in seen:
                    seen.add(href)
                    index_pages.append(href)

            logger.info("PAM index catalog: %d agreements", len(index_pages))

            results = []
            for index_page in index_pages:
                pam_tes = await self._fetch_index_page(client, index_page)
                if pam_tes:
                    results.append(pam_tes)

        return results

    def _is_tes_page_url(self, href: str) -> bool:
        """
        Проверяет что ссылка ведёт на индексную страницу договора (/tes/{slug}/),
        а не на сам каталог или внешний ресурс.
        """
        marker = PAM_URL_MARKER
        domain = PAM_DOMAIN
        if marker not in href or domain not in href:
            return False
        if href.rstrip("/").endswith(marker.rstrip("/")):
            return False
        return True

    async def _fetch_index_page(
            self, client: httpx.AsyncClient, index_url: str
    ) -> PamDiscoveredTes | None:
        """
        Загружает индексную страницу договора и извлекает метаданные.

        Возвращает PamDiscoveredTes с name_fi, key, датами и списком глав.
        Возвращает None если на странице не найдены ссылки на главы.
        """
        html = await self._fetch(client, index_url)
        soup = BeautifulSoup(html, "html.parser")

        h1 = soup.find("h1")
        name_fi = h1.get_text(strip=True) if h1 else ""
        key = index_url.rstrip("/").split("/")[-1]
        valid_from = None
        valid_until = None
        text = soup.get_text()
        m = VALIDITY_RE.search(text)
        if m:
            valid_from = self._parse_fi_date(m.group(1))
            valid_until = self._parse_fi_date(m.group(2))

        chapter_links = self._find_chapter_links(html, PAM_BASE_URL)
        if not chapter_links:
            logger.warning("PAM: no chapter links found for %s", index_url)
            return None

        return PamDiscoveredTes(
            key=key,
            index_url=index_url,
            links=chapter_links,
            name_fi=name_fi,
            valid_from=valid_from,
            valid_until=valid_until,
            sector_fi="",
        )

    def _find_chapter_links(self, html: str, base_url: str) -> list[str]:
        """
        Извлекает список абсолютных URL глав договора из HTML индексной страницы.
        Ищет ссылки содержащие /taysi/ в пути.
        """
        soup = BeautifulSoup(html, "html.parser")
        links = []
        seen = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if isinstance(href, list):
                href = href[0] if href else ""
            href = str(href).strip()
            absolute_url = urljoin(base_url, href)
            if "/taysi/" in href:
                if href not in seen:
                    seen.add(href)
                    links.append(absolute_url)
        return links
    
    def _parse_fi_date(self, date_str: str) -> str | None:
        """Конвертирует финскую дату "1.2.2025" в ISO формат "2025-02-01"."""
        try:
            parts = date_str.strip().split(".")
            return f"{parts[2]}-{int(parts[1]):02d}-{int(parts[0]):02d}"
        except (IndexError, ValueError):
            return None

    async def parse_tes(self, discovered: PamDiscoveredTes) -> PamParsedAgreement:
        """
        Парсит все главы одного договора и собирает PamParsedAgreement.

        Обходит все URL из discovered.links, накапливает клаузулы,
        вычисляет content_hash. Используется в parse_all_tes().
        """

        links = discovered.links
        clauses = []
        for link in links:
            part_clauses = await self.fetch_and_parse(link)
            clauses.extend(part_clauses)
        content_hash = hashlib.sha256(
            "\n".join(c.text_fi for c in clauses).encode()
        ).hexdigest()

        return PamParsedAgreement(
            union_key="pam",
            key=discovered.key,
            name_fi=discovered.name_fi,
            valid_from=discovered.valid_from,
            valid_until=discovered.valid_until,
            source_url=discovered.index_url,
            content_hash=content_hash,
            sector_fi=discovered.sector_fi,
            is_universally_binding=True,
            clauses=clauses,
        )

    async def parse_all_tes(self) -> list[PamParsedAgreement]:
        """
        Удобный метод для ручного запуска полного цикла: discover() + parse_tes()
        для каждого найденного договора. В production-флоу не используется —
        там discovery и парсинг клаузул разделены через TesDiscoveryService.
        """
        discovered = await self.discover()
        results = []
        for d in discovered:
            try:
                agreement = await self.parse_tes(d)
                results.append(agreement)
                logger.info(
                    "PAM: parsed %-40s — %d clauses", d.name_fi[:40], len(agreement.clauses)
                )
            except Exception as e:
                logger.error("PAM: failed %s: %s", d.index_url, e)
        return results

    def _extract_clauses(self, html: str) -> list[PamParsedClause]:
        """
        Разбивает HTML страницы главы на клаузулы по тегу <h2> с символом §.

        Контент ищется внутри div.pam-tes-official__content.
        Текст каждой клаузулы — всё между текущим и следующим <h2>.
        Клаузулы короче 80 символов пропускаются как артефакты.
        """
        soup = BeautifulSoup(html, "html.parser")

        # Все h2 с § в документе
        content = soup.find("div", class_="pam-tes-official__content")
        if not content:
            logger.warning("PAM: content container not found")
            return []
        section_headers = [h for h in content.find_all("h2") if "§" in h.get_text()]
        if not section_headers:
            # fallback: h1 вне content — вся страница = одна клаузула
            h1 = soup.find("h1")
            if h1 and "§" in h1.get_text():
                title_text = h1.get_text(strip=True)
                m = re.match(r"^(\d+)\s*§\s*(.*)$", title_text)
                section_ref = f"§ {m.group(1)}" if m else "§ ?"
                title_fi = m.group(2).strip() if m else title_text
                clause_text = content.get_text(separator="\n", strip=True)
                if len(clause_text) >= 80:
                    topic_key = self._resolve_topic(title_fi, clause_text)
                    return [PamParsedClause(
                        section_ref=section_ref,
                        title_fi=title_fi,
                        text_fi=clause_text,
                        topic_key=topic_key,
                    )]
            logger.warning("PAM: no § headers found in page")
            return []

        clauses: list[PamParsedClause] = []
        for i, header in enumerate(section_headers):
            title_text = header.get_text(strip=True)
            m = re.match(r"^(\d+)\s*§\s*(.*)$", title_text)
            section_ref = f"§ {m.group(1)}" if m else "§ ?"
            title_fi = m.group(2).strip() if m else title_text

            # Текст: все siblings до следующего h2 с §
            text_parts: list[str] = []
            next_header = (
                section_headers[i + 1] if i + 1 < len(section_headers) else None
            )
            for sib in header.find_next_siblings():
                if sib == next_header:
                    break
                if sib.name == "h2" and "§" in sib.get_text():
                    break
                if sib.name == "table":
                    text = self._table_to_markdown(sib)
                elif sib.find("table"):
                    text = self._table_to_markdown(sib.find("table"))
                else:
                    text = sib.get_text(separator=" ", strip=True)
                if text:
                    text_parts.append(text)

            clause_text = "\n\n".join(text_parts).strip()
            if len(clause_text) < 80:
                continue

            topic_key = self._resolve_topic(title_fi, clause_text)
            clause_text = clause_text.replace("← Takaisin sisällysluetteloon", "").strip()
            clauses.append(
                PamParsedClause(
                    section_ref=section_ref,
                    title_fi=title_fi,
                    text_fi=clause_text,
                    topic_key=topic_key,
                )
            )
        logger.debug("Pam: extracted %d clauses", len(clauses))
        return clauses

    def _resolve_topic(self, title_fi: str, text_fi: str = "") -> str | None:
        """
        Определяет topic_key клаузулы через detect_topic().
        Сначала проверяет заголовок, затем первые 500 символов текста как fallback.
        """
        topic = detect_topic(title_fi)
        if topic:
            return topic
        if text_fi:
            return detect_topic(text_fi[:500])
        return None

    async def fetch_and_parse(self, url: str) -> list[PamParsedClause]:
        """
        Загружает одну страницу главы и возвращает список клаузул.
        Используется в TesDiscoveryService._parse_agreement().
        """
        async with httpx.AsyncClient(
            headers=HEADERS, follow_redirects=True, timeout=self.timeout
        ) as client:
            html = await self._fetch(client, url)
        return self._extract_clauses(html)

    async def get_chapter_links(self, index_url: str) -> list[str]:
        """
        Загружает индексную страницу и возвращает список URL глав.
        Используется в TesDiscoveryService._parse_agreement() при парсинге клаузур.
        """
        async with httpx.AsyncClient(
                headers=HEADERS, follow_redirects=True, timeout=self.timeout
        ) as client:
            html = await self._fetch(client, index_url)
        return self._find_chapter_links(html, PAM_BASE_URL)

    def _table_to_markdown(self, table) -> str:
        """Конвертирует HTML <table> в Markdown."""
        rows = []
        for tr in table.find_all("tr"):
            cells = [td.get_text(strip=True) for td in tr.find_all(["th", "td"])]
            if cells:
                rows.append(cells)

        if not rows:
            return ""
        headers = rows[0]
        header_line = "| " + " | ".join(headers) + " |"
        separator_line = "| " + " | ".join(["---"] * len(headers)) + " |"
        data_lines = []
        for row in rows[1:]:
            if len(row) < len(headers):
                row += [""] * (len(headers) - len(row))
            row = row[:len(headers)]

            data_lines.append("| " + " | ".join(row) + " |")
        return "\n".join([header_line, separator_line] + data_lines)

    @staticmethod
    async def _fetch(client: httpx.AsyncClient, url: str) -> str:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.text



