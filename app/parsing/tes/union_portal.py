import logging
import re
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
    "collective-agreement",
    "korotukset",       # таблицы повышений зарплат
    "tyosopimusmalli",  # шаблон трудового договора
    "työsopimus_",      # шаблон (имя файла)
    "tutustu",          # программа для школьников
    "korvaava",         # инструкция по замещающей работе
    "silmatapaturmat",  # инструкция по травмам глаз
    "yhteenveto",       # summary (Finnish)
    "tiivistys",        # summary of changes
    "sammandrag",       # summary (Swedish)
    "yrityskohtainen",  # company-specific agreement
    "harjoittelij",     # trainee wage tables
]

_FINNISH_REPLACEMENTS = {
    "tyoehtosopimus": "työehtosopimus",
    "tyontekijoiden": "työntekijöiden",
    "esihenkiloiden": "esihenkilöiden",
    "vahittaiskaupan": "vähittäiskaupan",
    "palveluautomaattialan": "palveluautomaattialan",
    "kiinteisto": "kiinteistö",
    "tyontekijat": "työntekijät",
    "paallystys": "päällystys",
    "lattianpaallyst": "lattianpäällyst",
    "jarjestot": "järjestöt",
    "jarjestojen": "järjestöjen",
    "vahittais":         "vähittäis",
    "kenka":             "kenkä",
    "ymparisto":         "ympäristö",
    "oljy":              "öljy",
}


def _extract_sector_fi(name_fi: str) -> str:
    """
    Извлекает короткое название сектора из полного имени договора.
    'Kaupan alan työehtosopimus' → 'Kaupan ala'
    'Suunnittelu- ja konsulttialan ylempien toimihenkilöiden TES' → 'Suunnittelu- ja konsulttiala'
    'Talonrakennusala' → 'Talonrakennusala'
    """
    suffixes = [
        r"\s+virka-\s*ja\s+työehtosopimus.*",
        r"\s+työ-\s*ja\s+virkaehtosopimus.*",
        r"\s+työehtosopimus.*",
        r"\s+tyoehtosopimus.*",
        r"\s+TES\b.*",
    ]
    person_qualifiers = [
        r"\s+ylempien\s+toimihenkilöiden$",
        r"\s+toimihenkilöiden$",
        r"\s+työntekijöiden$",
        r"\s+esihenkilöiden$",
        r"\s+henkilöstön$",
        r"\s+koskeva$",
    ]
    result = name_fi
    for pattern in suffixes + person_qualifiers:
        result = re.sub(pattern, "", result, flags=re.IGNORECASE).strip()
    return result or name_fi  # fallback: если всё срезали — вернуть оригинал

class PdfStrategy(str, Enum):
    FIRST_PDF = "first_pdf"        # PAM: первый PDF без стоп-слов
    LINK_TEXT = "link_text"        # Rakennusliitto: по тексту ссылки
    ALL_PDFS_ON_PAGE = "all_pdfs_on_page"  # NEW: все PDF прямо с каталога

@dataclass
class DiscoveredTes:
    name_fi: str
    sector_fi: str
    tes_page_url: str
    pdf_url: str
    key_source: str | None = None
    link_text: str | None = None


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
    "kirkonalat": UnionPortalConfig(
    catalog_url="https://kirkonalat.fi/tyoehtosopimukset/",
    tes_url_marker="/tyoehtosopimukset/",
    domain="kirkonalat.fi",
    pdf_strategy=PdfStrategy.LINK_TEXT,
    path_depth=2,
    ),
    "konepaallystoliitto": UnionPortalConfig(
        catalog_url="https://www.konepaallystoliitto.fi/tyoehtosopimukset/",
        tes_url_marker="/tyoehtosopimukset/",
        domain="konepaallystoliitto.fi",
        pdf_strategy=PdfStrategy.LINK_TEXT,
        path_depth=2,
        path_exclude=["merenkulku", "julkinen"],
    ),
    "mvl": UnionPortalConfig(
        catalog_url="https://mvl.fi/palvelut-ja-edut/tyoehtosopimus/",
        tes_url_marker="/tyoehtosopimus/",
        domain="mvl.fi",
        pdf_strategy=PdfStrategy.ALL_PDFS_ON_PAGE,
    ),
    "ria": UnionPortalConfig(
        catalog_url="https://ria.fi/tyoelama/rialaisia-koskevat-tyoehtosopimukset/",
        tes_url_marker="/tyoehtosopimus/",
        domain="ria.fi",
        pdf_strategy=PdfStrategy.ALL_PDFS_ON_PAGE,
    ),
    "jyty": UnionPortalConfig(
    catalog_url="https://jytyliitto.fi/tyoelama/tyoehtosopimukset/yksityinen/",
    tes_url_marker="/tyoehtosopimukset/yksityinen/",
    domain="jytyliitto.fi",
    pdf_strategy=PdfStrategy.LINK_TEXT,
    path_depth=4,
    path_exclude=["ytes"],
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
        if self.config.pdf_strategy == PdfStrategy.ALL_PDFS_ON_PAGE:
            return await self._discover_all_pdfs_on_catalog()
        tes_page_urls = await self._fetch_catalog()
        if not tes_page_urls:
            logger.warning(
                "No TES pages found in %s catalog. "
                "Consider using PdfStrategy.ALL_PDFS_ON_PAGE for this portal.",
                self.union_key,
            )
            return []
        logger.info(
            "Found %d TES pages in %s catalog",
            len(tes_page_urls), self.union_key,
        )

        results = []
        async with httpx.AsyncClient(
                headers=HEADERS, follow_redirects=True, timeout=20
        ) as client:
            for url, link_text in tes_page_urls:
                try:
                    pdf_url = await self._fetch_pdf_url(client, url)
                    if pdf_url:
                        raw_name = link_text if link_text else self._slug_to_name(url)
                        results.append(DiscoveredTes(
                            name_fi=raw_name,
                            sector_fi=_extract_sector_fi(raw_name),
                            tes_page_url=url,
                            pdf_url=pdf_url,
                            link_text=link_text,
                        ))
                        logger.info("Discovered: %s → %s",
                                    raw_name[:50], pdf_url.split("/")[-1])
                    else:
                        logger.warning("No PDF found on page: %s", url)
                except Exception as e:
                    logger.error("Failed to fetch TES page %s: %s", url, e)
        return results

    async def _fetch_pdf_from_page(
            self, client: httpx.AsyncClient, page_url: str
    ) -> tuple[str | None, str | None]:
        """
        Загружает страницу и находит на ней PDF с учётом стратегии.

        Returns:
            tuple[str | None, str | None]: (pdf_url, link_text) или (None, None)
        """
        resp = await client.get(page_url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Выбираем стратегию поиска PDF
        if self.config.pdf_strategy == PdfStrategy.LINK_TEXT:
            pdf_url = self._find_pdf_by_link_text(soup)
        elif self.config.pdf_strategy == PdfStrategy.ALL_PDFS_ON_PAGE:
            # Для ALL_PDFS_ON_PAGE эта логика будет в другом месте
            pdf_url = self._find_first_pdf(soup)
        else:  # FIRST_PDF
            pdf_url = self._find_first_pdf(soup)

        if not pdf_url:
            return None, None

        # Нормализуем URL
        if pdf_url.startswith("/"):
            pdf_url = f"https://{self.config.domain}{pdf_url}"

        # Ищем текст ссылки для этого PDF
        link_text = None
        pdf_filename = pdf_url.split("/")[-1]
        for a in soup.find_all("a", href=True):
            href = str(a["href"])
            if href.endswith(pdf_filename):
                link_text = a.get_text(strip=True)
                break

        return pdf_url, link_text

    async def _fetch_catalog(self) -> list[tuple[str, str]]:
        """Возвращает список (url, link_text)."""
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
                link_text = a.get_text(strip=True)
                urls.append((href, link_text))
        return urls

    def _is_tes_page_url(self, href: str) -> bool:
        """Проверяет что ссылка ведёт на страницу TES, а не на каталог."""
        marker = self.config.tes_url_marker
        domain = self.config.domain
        if marker not in href or domain not in href:
            return False
        if href.rstrip("/").endswith(marker.rstrip("/")):
            return False
        # Исключаемые подстроки — проверяем ДО глубины
        for exclude in self.config.path_exclude:
            if exclude in href:
                return False
        # Проверка глубины пути
        if self.config.path_depth is not None:
            path = href.split(domain)[-1].rstrip("/")
            segments = [s for s in path.split("/") if s]
            if len(segments) != self.config.path_depth:
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

    async def _discover_all_pdfs_on_catalog(self) -> list[DiscoveredTes]:
        """Собирает все PDF прямо со страницы каталога — для порталов без подстраниц."""
        async with httpx.AsyncClient(
                headers=HEADERS, follow_redirects=True, timeout=20
        ) as client:
            resp = await client.get(self.config.catalog_url)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        seen = set()

        for a in soup.find_all("a", href=True):
            href = str(a["href"])
            if not href.endswith(".pdf"):
                continue
            filename = href.split("/")[-1].lower()
            if any(kw in filename for kw in _PDF_SKIP_KEYWORDS):
                continue
            if href in seen:
                continue
            seen.add(href)

            if href.startswith("/"):
                href = f"https://{self.config.domain}{href}"

            link_text = a.get_text(strip=True)
            name_fi = link_text if link_text else self._slug_to_name(href)
            results.append(DiscoveredTes(
                name_fi=name_fi,
                sector_fi=_extract_sector_fi(name_fi),
                tes_page_url=self.config.catalog_url,
                pdf_url=href,
                key_source=href,
            ))
            logger.info("Discovered PDF on catalog: %s → %s", name_fi[:50], filename)

        logger.info("Found %d PDFs on catalog page for %s", len(results), self.union_key)
        return results

    @staticmethod
    def _slug_to_name(url: str) -> str:
        slug = url.rstrip("/").split("/")[-1]
        name = slug.replace("-", " ").capitalize()
        for ascii_form, finnish in _FINNISH_REPLACEMENTS.items():
            name = name.replace(ascii_form, finnish)
        return name