
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




class PamParser:
    """

    """

    def __init__(self, timeout: float = 30.0) -> None:
        self.timeout = timeout

    # обнаружение договоров

    async def discover(self) -> list[PamDiscoveredTes]:
        """
        Сканирует https://www.pam.fi/tyoehtosopimukset/.
        Проходит по ссылкам вида https://www.pam.fi/tes/...
        Возвращает список найденных версионированных договоров.
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
                seen.add(href)
                index_pages.append(href)

            logger.info("PAM index catalog: %d agreements", len(index_pages))

            results = []
            for index_page in index_pages:
                pam_tes = await self._fetch_index_page(client, index_page)
                results.append(pam_tes)
            # for slug, period in candidates:
            #     index_url = f"{PAM_BASE_URL}/sopimukset/{slug}/{period}"
            #     try:
            #         d = await self._fetch_index_page(client, slug, period, index_url)
            #         if d:
            #             results.append(d)
            #             logger.info(
            #                 "KT discovered: %s/%s — %s", slug, period, d.name_fi[:50]
            #             )
            #     except Exception as e:
            #         logger.error("KT: failed index %s/%s: %s", slug, period, e)

        return results

    def _is_tes_page_url(self, href: str) -> bool:
        """Проверяет что ссылка ведёт на страницу TES, а не на каталог."""
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
        """Конвертирует "1.2.2025" → "2025-02-01"."""
        try:
            parts = date_str.strip().split(".")
            return f"{parts[2]}-{int(parts[1]):02d}-{int(parts[0]):02d}"
        except (IndexError, ValueError):
            return None


    @staticmethod
    async def _fetch(client: httpx.AsyncClient, url: str) -> str:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.text

