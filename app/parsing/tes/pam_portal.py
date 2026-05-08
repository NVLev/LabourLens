import logging
import re
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fi-FI,fi;q=0.9",
}

PAM_CATALOG_URL = (
    "https://www.pam.fi/tyoehtosopimukset/"
    "pamin-alojen-tyoehtosopimukset-aakkosjarjestyksessa/"
)

# Слова в имени PDF которые означают не основной договор
_PDF_SKIP_KEYWORDS = ["tasku", "taskutes", "palkkataulukko", "tiivistelma", "lyhyt"]


@dataclass
class DiscoveredTes:
    name_fi: str        # название из slug URL промежуточной страницы
    sector_fi: str      # то же, чуть почище
    tes_page_url: str   # промежуточная страница pam.fi/tes/*/
    pdf_url: str        # прямая ссылка на PDF


class PamPortalParser:
    """
    Двухшаговый парсер каталога TES на pam.fi.

    Шаг 1: сканирует каталог → находит ссылки на промежуточные страницы /tes/*/
    Шаг 2: заходит на каждую промежуточную страницу → находит основной PDF

    Название сектора извлекается из URL slug промежуточной страницы.
    """

    async def discover(self) -> list[DiscoveredTes]:
        """Возвращает список всех TES с PDF ссылками."""
        tes_page_urls = await self._fetch_catalog()
        logger.info("Found %d TES pages in PAM catalog", len(tes_page_urls))

        results = []
        async with httpx.AsyncClient(
            headers=HEADERS, follow_redirects=True, timeout=20
        ) as client:
            for url in tes_page_urls:
                try:
                    pdf_url = await self._fetch_pdf_url(client, url)
                    if pdf_url:
                        name_fi = self._slug_to_name(url)
                        results.append(DiscoveredTes(
                            name_fi=name_fi,
                            sector_fi=name_fi,
                            tes_page_url=url,
                            pdf_url=pdf_url,
                        ))
                        logger.info("Discovered: %s → %s", name_fi, pdf_url.split("/")[-1])
                    else:
                        logger.warning("No PDF found on page: %s", url)
                except Exception as e:
                    logger.error("Failed to fetch TES page %s: %s", url, e)

        logger.info("Discovered %d TES with PDFs", len(results))
        return results

    async def _fetch_catalog(self) -> list[str]:
        """Шаг 1: возвращает уникальные URL промежуточных страниц из каталога."""
        async with httpx.AsyncClient(
            headers=HEADERS, follow_redirects=True, timeout=20
        ) as client:
            resp = await client.get(PAM_CATALOG_URL)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        seen = set()
        urls = []
        for a in soup.find_all("a", href=True):
            href = str(a["href"])  # явное приведение к str
            if (
                    "/tes/" in href
                    and "pam.fi" in href
                    and href not in seen
            ):
                seen.add(href)
                urls.append(href)
        return urls

    async def _fetch_pdf_url(
        self, client: httpx.AsyncClient, tes_page_url: str
    ) -> str | None:
        """Шаг 2: находит основной PDF на промежуточной странице."""
        resp = await client.get(tes_page_url)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = str(a["href"])
            if not (href.endswith(".pdf") and "wp-content/uploads" in href):
                continue
            filename = href.split("/")[-1].lower()
            if any(kw in filename for kw in _PDF_SKIP_KEYWORDS):
                continue
            return href
        return None

    @staticmethod
    def _slug_to_name(url: str) -> str:
        """
        Извлекает название из URL slug.
        'pam.fi/tes/kaupan-alan-tyoehtosopimus/' → 'Kaupan alan työehtosopimus'
        """
        slug = url.rstrip("/").split("/")[-1]
        # Заменяем дефисы на пробелы, капитализируем
        name = slug.replace("-", " ").capitalize()
        # Исправляем финские слова
        name = name.replace("tyoehtosopimus", "työehtosopimus")
        name = name.replace("tyontekijoiden", "työntekijöiden")
        name = name.replace("esihenkiloiden", "esihenkilöiden")
        name = name.replace("vahittaiskaupan", "vähittäiskaupan")
        name = name.replace("palveluautomaattialan", "palveluautomaattialan")
        return name