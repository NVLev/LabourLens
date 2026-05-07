import logging
import re
from dataclasses import dataclass, field
from typing import Sized

import httpx
from pathlib import Path
import tempfile

import pdfplumber

logger = logging.getLogger(__name__)

# Маппинг ключевых слов параграфа → topic_key

SECTION_TOPIC_MAP: dict[str, str] = {
    "työsopimus":           "contract_types",
    "koeaika":              "probation_period",
    "työsuhteen päättyminen": "dismissal_grounds",
    "lomautus":             "layoff",
    "irtisanominen":        "dismissal_grounds",
    "yötyö":                "night_and_sunday_work",
    "sunnuntaityö":         "night_and_sunday_work",
    "lisä- ja ylityö":      "overtime",
    "ylityö":               "overtime",
    "työpalkat":            "min_wage",
    "palkat":               "min_wage",
    "vähimmäispalkka":      "min_wage",
    "sairastuminen":        "sick_leave",
    "sairausajan palkka":   "sick_leave",
    "vuosiloma":            "annual_leave",
    "lomaraha":             "holiday_pay",
    "lomapalkka":           "holiday_pay",
    "perhevapaat":          "parental_leave",
    "työaika":              "working_hours",
    "ilta- ja yölisä":      "night_and_sunday_work",
    "yölisä":               "night_and_sunday_work",
    "iltalisä":             "night_and_sunday_work",
    "lisät":                "night_and_sunday_work",
    "pyhätyö":              "night_and_sunday_work",
    "tilapäinen poissaolo": "sick_leave",
    "lääkärintarkastus":    "sick_leave",
    "lapsen syntymä":       "parental_leave",
    "matkakustannukset":    "working_hours",
    "määräaikainen sopimus":  "contract_types",
    "lepoajat":               "working_hours",
    "myyjät":                   "min_wage",
    "logistiikkatyöntekijät":   "min_wage",
    "toimihenkilöt":            "min_wage",
    "muut ammattiryhmät":       "min_wage",
    "lääkärintarkastukset":     "sick_leave",
    "sairauspoissaolo":         "sick_leave",
    "työsuhdeturva":            "dismissal_protection",
    "provisiopalkka":           "min_wage",
    "vaativuustasot":           "min_wage",
    "suorituspalkkaus":         "min_wage",
    "vuosivapaa":   "annual_leave",
    "työviikko":    "working_hours",
}


@dataclass
class ParsedTesClause:
    section_ref: str        # "§ 13"
    title_fi: str           # "Työpalkat"
    text_fi: str            # полный текст параграфа
    topic_key: str | None
    page_start: int         # номер страницы (1-based)
    @property
    def needs_manual_linking(self) -> bool:
        """True если клаузула не залинкована к теме и содержит существенный текст."""
        return self.topic_key is None and len(self.text_fi) > 300


@dataclass
class ParsedAgreement:
    union_key: str          # "pam"
    name_fi: str            # "Kaupan työehtosopimus"
    valid_from: str | None  # "2025-02-01"
    valid_until: str | None # "2028-01-31"
    source_url: str
    is_universally_binding: bool = True
    clauses: list[ParsedTesClause] = field(default_factory=list)


# Parser

# Паттерн заголовка параграфа: "13 § Työpalkat" или "1 § Sopimuksen ulottuvuus"
_SECTION_HEADER = re.compile(
    r"^(\d+)\s*§\s*(.+)$",
    re.MULTILINE,
)

# Паттерн периода действия: "1.2.2025–31.1.2028"
_VALIDITY_RE = re.compile(
    r"(\d{1,2}\.\d{1,2}\.\d{4})\s*[–-]\s*(\d{1,2}\.\d{1,2}\.\d{4})"
)


class TesPdfParser:
    """
    Парсит PDF-файлы финских коллективных договоров (TES/työehtosopimus).

    Стратегия:
    - Извлекает текст всех страниц через pdfplumber
    - Пропускает оглавление (первое вхождение параграфов без реального текста)
    - Разбивает текст на клаузуры по паттерну "N § Название"
    - Маппит каждую клаузуру к topic_key по ключевым словам заголовка
    - Сохраняет полный текст каждого параграфа для хранения в TesClause
    """

    async def parse_from_url(
            self,
            url: str,
            union_key: str,
            is_universally_binding: bool = True,
    ) -> ParsedAgreement:
        """Скачивает PDF по URL и парсит."""
        logger.info("Downloading TES PDF: %s", url)
        async with httpx.AsyncClient(follow_redirects=True, timeout=60) as client:
            resp = await client.get(url)
            resp.raise_for_status()

        # Сохраняем во временный файл — pdfplumber требует файл, не bytes
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(resp.content)
            tmp_path = Path(tmp.name)

        try:
            return self.parse(tmp_path, union_key, url, is_universally_binding)
        finally:
            tmp_path.unlink(missing_ok=True)

    def parse(
        self,
        pdf_path: str | Path,
        union_key: str,
        source_url: str,
        is_universally_binding: bool = True,
    ) -> ParsedAgreement:
        path = Path(pdf_path)
        logger.info("Parsing TES PDF: %s", path.name)

        pages = self._extract_pages(path)
        full_text, page_index = self._build_full_text(pages)

        name_fi, valid_from, valid_until = self._extract_metadata(full_text)
        start_pos = self._find_content_start(full_text)
        clauses = self._extract_clauses(full_text[start_pos:], page_index, start_pos)

        logger.info(
            "Parsed %s: %d clauses, valid %s–%s",
            path.name, len(clauses), valid_from, valid_until,
        )

        unlinked = [c for c in clauses
                    if c.topic_key is None and len(c.text_fi) > 300]
        if unlinked:
            logger.warning(
                "%s: %d clauses need manual topic linking: %s",
                name_fi,
                len(unlinked),
                [f"{c.section_ref} {c.title_fi[:30]}" for c in unlinked],
            )

        return ParsedAgreement(
            union_key=union_key,
            name_fi=name_fi,
            valid_from=valid_from,
            valid_until=valid_until,
            source_url=source_url,
            is_universally_binding=is_universally_binding,
            clauses=clauses,
        )

    # Text extraction

    def _extract_pages(self, path: Path) -> list[tuple[int, str]]:
        """Возвращает список (page_number_1based, text)."""
        pages = []
        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                pages.append((i + 1, text))
        return pages

    def _build_full_text(
        self, pages: list[tuple[int, str]]
    ) -> tuple[str, list[tuple[int, int]]]:
        """
        Склеивает текст всех страниц в одну строку.
        Возвращает (full_text, page_index) где page_index — список
        (char_offset, page_number) для восстановления номера страницы.
        """
        parts = []
        page_index: list[tuple[int, int]] = []
        offset = 0
        for page_num, text in pages:
            page_index.append((offset, page_num))
            parts.append(text)
            offset += len(text) + 1  # +1 за \n между страницами
        return "\n".join(p for _, p in pages), page_index

    def _find_content_start(self, full_text: str) -> int:
        """
        Пропускает оглавление — находит второе вхождение "1 §"
        (первое в оглавлении, второе — начало реального текста).
        """
        pattern = re.compile(r"^1\s*§\s+\S", re.MULTILINE)
        matches = list(pattern.finditer(full_text))
        if len(matches) >= 2:
            return matches[1].start()
        if matches:
            return matches[0].start()
        return 0

    # Metadata

    def _extract_metadata(
        self, full_text: str
    ) -> tuple[str | Sized, str | None, str | None]:
        """Извлекает название и период действия из первых страниц."""
        header = full_text[:3000]

        valid_from = valid_until = None
        m = _VALIDITY_RE.search(header)
        if m:
            valid_from = self._parse_fi_date(m.group(1))
            valid_until = self._parse_fi_date(m.group(2))

        # Название — ищем строки ДО первого §, исключая даты и мусор
        name_fi = ""
        lines = [l.strip() for l in header.split("\n") if l.strip()]
        candidates = []
        for line in lines:
            if "§" in line:
                break
            if (len(line) > 5
                    and not re.match(r"^\d", line)  # не начинается с цифры
                    and "....." not in line  # не оглавление
                    and "alkaen" not in line.lower()):  # не дата вступления
                candidates.append(line)

        # Берём самую длинную строку-кандидат
        if candidates:
            name_fi = max(candidates, key=len)

        return name_fi, valid_from, valid_until

    def _parse_fi_date(self, date_str: str) -> str | None:
        """Конвертирует "1.2.2025" → "2025-02-01"."""
        try:
            parts = date_str.strip().split(".")
            return f"{parts[2]}-{int(parts[1]):02d}-{int(parts[0]):02d}"
        except (IndexError, ValueError):
            return None

    # Clause extraction

    def _extract_clauses(
        self,
        text: str,
        page_index: list[tuple[int, int]],
        base_offset: int,
    ) -> list[ParsedTesClause]:
        """
        Разбивает текст на клаузуры по паттерну "N § Название".
        Каждая клаузура — текст от текущего заголовка до следующего.
        """
        matches = list(_SECTION_HEADER.finditer(text))
        if not matches:
            return []

        clauses = []
        for i, match in enumerate(matches):
            section_num = match.group(1)
            title_fi = match.group(2).strip()
            if self._is_toc_title(title_fi):
                continue

            # Текст до следующего параграфа
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            clause_text = text[start:end].strip()
            MAX_CLAUSE_CHARS = 30000
            if len(clause_text) > MAX_CLAUSE_CHARS:
                logger.warning("Clause %s '%s' truncated: %d chars",
                               section_num, title_fi, len(clause_text))
                clause_text = clause_text[:MAX_CLAUSE_CHARS]
            # Пропускаем слишком короткие (артефакты оглавления)
            if len(clause_text) < 100:
                continue

            # Номер страницы
            abs_offset = base_offset + start
            page_num = self._offset_to_page(abs_offset, page_index)

            topic_key = self._resolve_topic(title_fi)
            if title_fi.startswith(":") or title_fi.startswith(")"):
                continue
            clauses.append(ParsedTesClause(
                section_ref=f"§ {section_num}",
                title_fi=title_fi,
                text_fi=clause_text,
                topic_key=topic_key,
                page_start=page_num,
            ))

        return clauses

    def _is_toc_title(self, title_fi: str) -> bool:
        """True если заголовок содержит точки оглавления."""
        return bool(re.search(r"\.{3,}", title_fi))

    def _offset_to_page(
        self, offset: int, page_index: list[tuple[int, int]]
    ) -> int:
        """Возвращает номер страницы по символьному смещению."""
        page_num = 1
        for page_offset, pnum in page_index:
            if page_offset <= offset:
                page_num = pnum
            else:
                break
        return page_num

    def _resolve_topic(self, title_fi: str) -> str | None:
        """Маппит заголовок параграфа на topic_key по ключевым словам."""
        title_lower = title_fi.lower()
        for keyword, topic_key in SECTION_TOPIC_MAP.items():
            if keyword in title_lower:
                return topic_key
        return None


