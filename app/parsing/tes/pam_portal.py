import logging
from dataclasses import dataclass, field
from enum import Enum
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

_PDF_SKIP_KEYWORDS = [
    "tasku", "taskutes", "palkkataulukko", "tiivistelma", "lyhyt",
    "yhdistetty",
    "kollektivavtal",   # шведская версия
    "korotukset",       # таблицы повышений зарплат
    "tyosopimusmalli",  # шаблон трудового договора
    "työsopimus_",      # шаблон (имя файла)
    "tutustu",          # программа для школьников
    "korvaava",         # инструкция по замещающей работе
    "silmatapaturmat",  # инструкция по травмам глаз
]

_FINNISH_REPLACEMENTS = {
    "tyoehtosopimus": "työehtosopimus",
    "tyontekijoiden": "työntekijöiden",
    "esihenkiloiden": "esihenkilöiden",
    "vahittaiskaupan": "vähittäiskaupan",
    "palveluautomaattialan": "palveluautomaattialan",
}

class PdfStrategy(str, Enum):
    FIRST_PDF = "first_pdf"        # PAM: первый PDF без стоп-слов
    LINK_TEXT = "link_text"        # Rakennusliitto: по тексту ссылки

@dataclass
class DiscoveredTes:
    name_fi: str
    sector_fi: str
    tes_page_url: str
    pdf_url: str


@dataclass
class UnionPortalConfig:
    """
    Конфиг для одного профсоюза.

    catalog_url     — страница со списком TES
    tes_url_marker  — подстрока, которая отличает ссылки на страницы TES
                      от всех остальных ссылок на каталоге
                      PAM:          "/tes/"
                      Rakennusliitto: "/tyoehtosopimukset/" + не сам каталог
    domain          — домен союза, для фильтрации внешних ссылок
    """
    catalog_url: str
    tes_url_marker: str
    domain: str
    pdf_strategy: PdfStrategy = PdfStrategy.FIRST_PDF
    path_depth: int | None = None  # если задан — требуем ровно N сегментов
    path_exclude: list[str] = field(default_factory=list)  # исключаемые подстроки


UNION_CONFIGS: dict[str, UnionPortalConfig] = {
    "pam": UnionPortalConfig(
        catalog_url=(
            "https://www.pam.fi/tyoehtosopimukset/"
            "pamin-alojen-tyoehtosopimukset-aakkosjarjestyksessa/"
        ),
        tes_url_marker="/tes/",
        domain="pam.fi",
        pdf_strategy=PdfStrategy.FIRST_PDF,
    ),
    "rakennusliitto": UnionPortalConfig(
        catalog_url="https://rakennusliitto.fi/tyoehtosopimukset/",
        tes_url_marker="/tyoehtosopimukset/",
        domain="rakennusliitto.fi",
        pdf_strategy=PdfStrategy.LINK_TEXT,
    ),
    "teollisuusliitto": UnionPortalConfig(
        catalog_url="https://www.teollisuusliitto.fi/tyoelama/tyoehtosopimukset/",
        tes_url_marker="/tyoehtosopimukset/",
        domain="teollisuusliitto.fi",
        pdf_strategy=PdfStrategy.LINK_TEXT,
    ),
}


class UnionPortalParser:
    """
    Универсальный двухшаговый парсер каталогов TES.

    Шаг 1: сканирует catalog_url → находит ссылки на страницы TES
            по tes_url_marker и domain из конфига
    Шаг 2: заходит на каждую страницу → находит основной PDF
    """

    def __init__(self, union_key: str) -> None:
        if union_key not in UNION_CONFIGS:
            raise ValueError(
                f"Unknown union key: {union_key}. "
                f"Available: {list(UNION_CONFIGS.keys())}"
            )
        self.union_key = union_key
        self.config = UNION_CONFIGS[union_key]

    async def discover(self) -> list[DiscoveredTes]:
        tes_page_urls = await self._fetch_catalog()
        logger.info(
            "Found %d TES pages in %s catalog",
            len(tes_page_urls), self.union_key,
        )

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
                        logger.info(
                            "Discovered: %s → %s",
                            name_fi, pdf_url.split("/")[-1],
                        )
                    else:
                        logger.warning("No PDF found on page: %s", url)
                except Exception as e:
                    logger.error("Failed to fetch TES page %s: %s", url, e)

        logger.info(
            "Discovered %d TES with PDFs for %s",
            len(results), self.union_key,
        )
        return results

    async def _fetch_catalog(self) -> list[str]:
        async with httpx.AsyncClient(
            headers=HEADERS, follow_redirects=True, timeout=20
        ) as client:
            resp = await client.get(self.config.catalog_url)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        seen = set()
        urls = []
        for a in soup.find_all("a", href=True):
            href = str(a["href"])
            if not self._is_tes_page_url(href):
                continue
            # Нормализуем относительные ссылки
            if href.startswith("/"):
                href = f"https://{self.config.domain}{href}"
            if href not in seen:
                seen.add(href)
                urls.append(href)
        return urls

    def _is_tes_page_url(self, href: str) -> bool:
        """Проверяет что ссылка ведёт на страницу TES, а не на каталог."""
        marker = self.config.tes_url_marker
        domain = self.config.domain
        if marker not in href or domain not in href:
            return False
        if href.rstrip("/").endswith(marker.rstrip("/")):
            return False
        # Проверка глубины пути
        if self.config.path_depth is not None:
            path = href.split(domain)[-1].rstrip("/")
            segments = [s for s in path.split("/") if s]
            if len(segments) != self.config.path_depth:
                return False
        # Исключаемые подстроки
        for exclude in self.config.path_exclude:
            if exclude in href:
                return False
        return True

    async def _fetch_pdf_url(
            self, client: httpx.AsyncClient, tes_page_url: str
    ) -> str | None:
        resp = await client.get(tes_page_url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        if self.config.pdf_strategy == PdfStrategy.LINK_TEXT:
            return self._find_pdf_by_link_text(soup)
        return self._find_first_pdf(soup)

    def _find_first_pdf(self, soup: BeautifulSoup) -> str | None:
        for a in soup.find_all("a", href=True):
            href = str(a["href"])
            if not href.endswith(".pdf"):
                continue
            filename = href.split("/")[-1].lower()
            if any(kw in filename for kw in _PDF_SKIP_KEYWORDS):
                continue
            return href
        return None

    def _find_pdf_by_link_text(self, soup: BeautifulSoup) -> str | None:
        for a in soup.find_all("a", href=True):
            href = str(a["href"])
            if not href.endswith(".pdf"):
                continue
            filename = href.split("/")[-1].lower()
            if any(kw in filename for kw in _PDF_SKIP_KEYWORDS):
                continue
            link_text = a.get_text(strip=True).lower()
            if "työehtosopimus" in link_text or "tyoehtosopimus" in link_text:
                return href
        return None

    @staticmethod
    def _slug_to_name(url: str) -> str:
        slug = url.rstrip("/").split("/")[-1]
        name = slug.replace("-", " ").capitalize()
        for ascii_form, finnish in _FINNISH_REPLACEMENTS.items():
            name = name.replace(ascii_form, finnish)
        return name