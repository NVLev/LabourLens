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

# Явный маппинг slug → topic_key.
# ILRY структурирован по темам
# тема определяется URL страницы, а не содержимым.
ILRY_PAGES: dict[str, str] = {
    "palkka":                                   "wages",
    "tyoaika":                                  "working_hours",
    "vuosiloma":                                "annual_leave",
    "sairastuminen":                            "sick_leave",
    "perhevapaat":                              "parental_leave",
    "opinto-ja-palkaton-vapaa":                 "parental_leave",
    "lomauttaminen":                            "layoff",
    "irtisanominen":                            "dismissal_grounds",
    "purkaminen":                               "dismissal_grounds",
    "koeaika":                                  "probation_period",
    "maaraaikaisen-sopimus-ja-sen-paattyminen": "contract_types",
    "tyosopimuksen-ehtojen-muuttaminen":        "contract_types",
    "tasa-arvo-yhdenvertaisuus-ja-hairinta":    "discrimination",
    "tyoturvallisuus-tyosuojelu-tyoterveys":    "workplace_safety",
    "matkustaminen":                            "expense_reimbursement",
    "yhteistoiminta-ja-muutosneuvottelut":      "local_agreement",
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
            for slug, topic_key in ILRY_PAGES.items():
                url = f"{ILRY_BASE_URL}/{slug}/"
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
        topic_key = ILRY_PAGES[slug]
        url = f"{ILRY_BASE_URL}/{slug}/"
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
