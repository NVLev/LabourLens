import logging
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

ILRY_BASE_URL = "https://www.ilry.fi/tyoelaman-lakitieto"

# ILRY структурирован по темам
# тема определяется URL страницы, а не содержимым.
ILRY_PAGES: dict[str, tuple[str, str]] = {
    # slug (для API) → (путь относительно BASE_URL, topic_key)

    # Прямые дочерние страницы
    "tyoaika":               ("tyoaika",               "working_hours"),
    "vuosiloma":             ("vuosiloma",              "annual_leave"),
    "matkustaminen":         ("matkustaminen",          "expense_reimbursement"),
    "lomauttaminen":         ("lomauttaminen",          "layoff"),

    # Раздел: tyosopimuksen-tekeminen-ja-muuttaminen
    "palkka":                        ("tyosopimuksen-tekeminen-ja-muuttaminen/palkka",                         "wages"),
    "tyosopimuksen-ehtojen-muuttaminen": ("tyosopimuksen-tekeminen-ja-muuttaminen/tyosopimuksen-ehtojen-muuttaminen", "contract_types"),

    # Раздел: perhevapaat-ja-muut-poissaolot
    "sairastuminen":         ("perhevapaat-ja-muut-poissaolot/sairastuminen",         "sick_leave"),
    "perhevapaat":           ("perhevapaat-ja-muut-poissaolot/perhevapaat",           "parental_leave"),
    "opinto-ja-palkaton-vapaa": ("perhevapaat-ja-muut-poissaolot/opinto-ja-palkaton-vapaa", "parental_leave"),

    # Раздел: tyosuhteen-paattaminen-tai-paattyminen
    "irtisanominen":         ("tyosuhteen-paattaminen-tai-paattyminen/irtisanominen",                            "dismissal_grounds"),
    "irtisanoutuminen":      ("tyosuhteen-paattaminen-tai-paattyminen/irtisanoutuminen-ja-tyopaikan-vaihtaminen", "notice_period"),
    "purkaminen":            ("tyosuhteen-paattaminen-tai-paattyminen/purkaminen",                               "dismissal_grounds"),
    "koeaika":               ("tyosuhteen-paattaminen-tai-paattyminen/koeaika",                                  "probation_period"),
    "maaraaikainen":         ("tyosuhteen-paattaminen-tai-paattyminen/maaraaikaisen-sopimus-ja-sen-paattyminen", "contract_types"),
    "paattosopimus":         ("tyosuhteen-paattaminen-tai-paattyminen/paattosopimus-tai-irtisanomispaketti",     "dismissal_grounds"),
    "yhteistoiminta":        ("tyosuhteen-paattaminen-tai-paattyminen/yhteistoiminta-ja-muutosneuvottelut",      "local_agreement"),

    # Раздел: tyohyvinvointi-ja-turvallisuus
    "tyoturvallisuus":       ("tyohyvinvointi-ja-turvallisuus/tyoturvallisuus-tyosuojelu-tyoterveys", "workplace_safety"),
    "tasa-arvo":             ("tyohyvinvointi-ja-turvallisuus/tasa-arvo-yhdenvertaisuus-ja-hairinta", "discrimination"),
}


@dataclass
class ParsedIlryEntry:
    """Одна FAQ-запись: вопрос + развёрнутый ответ."""
    question_fi: str   # текст <summary>
    answer_fi: str     # текст <details> без <summary>
    topic_key: str
    source_url: str


class IlryParser:
    """
    Парсит FAQ-страницы раздела «Työelämän lakitieto» на ilry.fi.

    Каждая страница содержит аккордеон из элементов <details>/<summary>:
    - <summary> — вопрос (заголовок записи)
    - остальное содержимое <details> — развёрнутый ответ

    Тема определяется из ILRY_PAGES по slug URL, без detect_topic.
    Каждый <details> → одна Interpretation с source="ilry".
    """

    async def parse_all(self) -> list[ParsedIlryEntry]:
        results = []
        async with httpx.AsyncClient(
            headers=HEADERS, follow_redirects=True, timeout=20
        ) as client:
            for slug, (path, topic_key) in ILRY_PAGES.items():
                url = f"{ILRY_BASE_URL}/{path}/"
                entries = await self._parse_page(client, url, topic_key)
                try:
                    entries = await self._parse_page(client, url, topic_key)
                    results.extend(entries)
                    logger.info(
                        "ILRY: parsed %d entries from %s", len(entries), slug
                    )
                except Exception as e:
                    logger.error("ILRY: failed to parse %s: %s", slug, e)
        return results

    async def parse_one(self, slug: str) -> list[ParsedIlryEntry]:
        if slug not in ILRY_PAGES:
            raise ValueError(
                f"Unknown ILRY slug: '{slug}'. "
                f"Available: {list(ILRY_PAGES.keys())}"
            )
        path, topic_key = ILRY_PAGES[slug]
        url = f"{ILRY_BASE_URL}/{path}/"
        async with httpx.AsyncClient(
            headers=HEADERS, follow_redirects=True, timeout=20
        ) as client:
            return await self._parse_page(client, url, topic_key)

    async def _parse_page(
        self,
        client: httpx.AsyncClient,
        url: str,
        topic_key: str,
    ) -> list[ParsedIlryEntry]:
        resp = await client.get(url)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        entries = []

        for details in soup.find_all("details"):
            summary = details.find("summary")
            if not summary:
                continue

            question = summary.get_text(strip=True)
            if not question:
                continue

            # Извлекаем summary из дерева, чтобы он не попал в текст ответа
            summary.extract()
            answer = details.get_text(separator="\n", strip=True)

            if len(answer) < 50:
                logger.debug("ILRY: skipping short entry '%s'", question[:60])
                continue

            entries.append(ParsedIlryEntry(
                question_fi=question,
                answer_fi=answer,
                topic_key=topic_key,
                source_url=url,
            ))

        return entries
