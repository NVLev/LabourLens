import hashlib
import logging
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sized

import httpx
import pdfplumber
import requests

from app.parsing.topic_keywords import detect_topic

logger = logging.getLogger(__name__)


@dataclass
class ParsedTesClause:
    section_ref: str  # "§ 13"
    title_fi: str  # "Työpalkat"
    text_fi: str  # полный текст параграфа
    topic_key: str | None
    page_start: int  # номер страницы (1-based)

    @property
    def needs_manual_linking(self) -> bool:
        """True если клаузула не залинкована к теме и содержит существенный текст."""
        return self.topic_key is None and len(self.text_fi) > 300


@dataclass
class ParsedAgreement:
    union_key: str  # "pam"
    key: str
    name_fi: str  # "Kaupan työehtosopimus"
    valid_from: str | None  # "2025-02-01"
    valid_until: str | None  # "2028-01-31"
    source_url: str
    content_hash: str
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

YEAR_RANGE_RE = re.compile(r"(20\d{2})\s*[–—-]\s*(20\d{2})")


def build_key(union_key: str, name_fi: str) -> str:
    import re

    slug = name_fi.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")

    return f"{union_key}-{slug}"


def build_content_hash(clauses: list[ParsedTesClause]) -> str:
    raw = "\n".join(c.text_fi.strip() for c in clauses if c.text_fi)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


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
        """
        Скачивает PDF по URL с защитой от WAF и парсит.

        Защиты:
        - Browser headers
        - Проверка Content-Type
        - Проверка сигнатуры PDF (%PDF)
        - Детект HTML/WAF
        - fallback на requests
        """

        HEADERS = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0 Safari/537.36"
            ),
            "Accept": "application/pdf,application/octet-stream;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        def is_valid_pdf(content: bytes) -> bool:
            return content.startswith(b"%PDF")

        def looks_like_html(content: bytes) -> bool:
            snippet = content[:500].lower()
            return b"<html" in snippet or b"<!doctype html" in snippet

        def download_with_requests(url: str) -> bytes:

            resp = requests.get(url, headers=HEADERS, timeout=60)
            resp.raise_for_status()
            return resp.content

        logger.info("Downloading TES PDF: %s", url)

        content: bytes | None = None

        # httpx
        try:
            async with httpx.AsyncClient(
                headers=HEADERS,
                follow_redirects=True,
                timeout=60,
            ) as client:
                resp = await client.get(url)
                resp.raise_for_status()

                content_type = resp.headers.get("content-type", "")
                content = resp.content

                # Проверка: не PDF → fallback
                if "pdf" not in content_type.lower():
                    logger.warning(
                        "Unexpected content-type '%s' for %s",
                        content_type,
                        url,
                    )

                if looks_like_html(content):
                    raise ValueError("Got HTML instead of PDF (likely WAF)")

                if not is_valid_pdf(content):
                    raise ValueError("Invalid PDF signature")

        except Exception as e:
            logger.warning(
                "httpx failed for %s (%s), retrying with requests",
                url,
                str(e),
            )

            try:
                content = download_with_requests(url)

                if looks_like_html(content):
                    raise ValueError("Requests fallback also returned HTML")

                if not is_valid_pdf(content):
                    raise ValueError("Invalid PDF in fallback")

            except Exception as e2:
                logger.error(
                    "Failed to download PDF via both httpx and requests: %s (%s)",
                    url,
                    str(e2),
                )
                raise

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)

        try:
            return self.parse(
                tmp_path,
                union_key,
                url,
                is_universally_binding,
            )
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
        key = build_key(union_key, name_fi)
        content_hash = build_content_hash(clauses)
        logger.info(
            "Parsed %s: %d clauses, valid %s–%s",
            path.name,
            len(clauses),
            valid_from,
            valid_until,
        )

        unlinked = [c for c in clauses if c.topic_key is None and len(c.text_fi) > 300]
        if unlinked:
            logger.warning(
                "%s: %d clauses need manual topic linking: %s",
                name_fi,
                len(unlinked),
                [f"{c.section_ref} {c.title_fi[:30]}" for c in unlinked],
            )

        return ParsedAgreement(
            union_key=union_key,
            key=key,
            name_fi=name_fi,
            valid_from=valid_from,
            valid_until=valid_until,
            source_url=source_url,
            content_hash=content_hash,
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
                text = self._clean_text(text)
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

    def _extract_metadata(self, full_text: str) -> tuple[str, str | None, str | None]:
        """Извлекает название и период действия из первых страниц TES."""

        logger.warning("=== METADATA DEBUG START ===")

        header = full_text[:4000]
        logger.warning(
            "HEADER (first 500 chars): %s",
            header[:500].replace("\n", " | "),
        )

        # validity (даты)

        valid_from = None
        valid_until = None

        matches = list(_VALIDITY_RE.finditer(header))
        if not matches:
            matches = list(_VALIDITY_RE.finditer(full_text[:20000]))

        if matches:
            logger.warning("VALIDITY MATCHES FOUND: %d", len(matches))
            for m in matches[:5]:
                logger.warning("MATCH: %s", m.group(0))

            def duration_days(m):
                try:
                    start = self._parse_fi_date(m.group(1))
                    end = self._parse_fi_date(m.group(2))
                    if not start or not end:
                        return 0
                    return abs(int(end[:4]) - int(start[:4])) * 365
                except Exception:
                    return 0

            best = max(matches, key=duration_days)

            valid_from = self._parse_fi_date(best.group(1))
            valid_until = self._parse_fi_date(best.group(2))

        # fallback: только годы
        if not valid_from or not valid_until:
            year_matches = list(YEAR_RANGE_RE.finditer(header))
            if year_matches:
                logger.warning(
                    "YEAR RANGE MATCHES: %s",
                    [m.group(0) for m in year_matches],
                )
                y1, y2 = year_matches[0].groups()
                valid_from = f"{y1}-01-01"
                valid_until = f"{y2}-12-31"

        # name_fi (название)

        lines = [l.strip() for l in header.split("\n") if l.strip()]

        STOPWORDS = {
            "isbn",
            "kustantaja",
            "paino",
            "taitto",
            "sisältö",
            "sisällys",
        }

        filtered = []
        for line in lines:
            if "§" in line:
                break

            l = line.lower()

            if (
                len(line) > 3
                and not re.match(r"^\d", line)
                and "....." not in line
                and "alkaen" not in l
                and not _VALIDITY_RE.search(line)
                and l not in {"työntekijät", "palkkaliite", "liite"}
            ):
                filtered.append(line)

        logger.warning("FILTERED LINES: %s", filtered[:10])

        # --- берём только верхний блок до мусора ---
        name_lines = []

        for line in filtered:
            l = line.lower()
            # мусор
            if any(word in l for word in STOPWORDS):
                break

            # слишком длинная строка
            if len(line) > 80:
                break

            name_lines.append(line)

            if len(name_lines) >= 6:
                break

        # склейка
        name_fi = " ".join(name_lines).strip()

        # --- нормализация ---
        name_fi = re.sub(r"\s+", " ", name_fi)

        # удалим дубли подряд (частая проблема PDF)
        parts = name_fi.split()
        deduped = []
        for p in parts:
            if not deduped or deduped[-1] != p:
                deduped.append(p)
        name_fi = " ".join(deduped)

        # fallback
        if not name_fi and lines:
            name_fi = lines[0]

        words = name_fi.split()
        half = len(words) // 2
        if len(words) > 4 and words[:half] == words[half:]:
            name_fi = " ".join(words[:half])

        if name_fi:
            name_fi = self._clean_agreement_name(name_fi)

        logger.warning("SELECTED NAME: %s", name_fi)
        logger.warning("VALID FROM: %s | VALID UNTIL: %s", valid_from, valid_until)
        logger.warning("=== METADATA DEBUG END ===")

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
            clause_text = self._clean_text(clause_text)
            MAX_CLAUSE_CHARS = 30000
            if len(clause_text) > MAX_CLAUSE_CHARS:
                logger.warning(
                    "Clause %s '%s' truncated: %d chars",
                    section_num,
                    title_fi,
                    len(clause_text),
                )
                clause_text = clause_text[:MAX_CLAUSE_CHARS]
            # Пропускаем слишком короткие (артефакты оглавления)
            if len(clause_text) < 100:
                continue

            # Номер страницы
            abs_offset = base_offset + start
            page_num = self._offset_to_page(abs_offset, page_index)

            topic_key = self._resolve_topic(title_fi, clause_text)
            if title_fi.startswith(":") or title_fi.startswith(")"):
                continue
            clauses.append(
                ParsedTesClause(
                    section_ref=f"§ {section_num}",
                    title_fi=title_fi,
                    text_fi=clause_text,
                    topic_key=topic_key,
                    page_start=page_num,
                )
            )

        return clauses

    def _is_toc_title(self, title_fi: str) -> bool:
        """True если заголовок содержит точки оглавления."""
        return bool(re.search(r"\.{3,}", title_fi))

    def _offset_to_page(self, offset: int, page_index: list[tuple[int, int]]) -> int:
        """Возвращает номер страницы по символьному смещению."""
        page_num = 1
        for page_offset, pnum in page_index:
            if page_offset <= offset:
                page_num = pnum
            else:
                break
        return page_num

    def _clean_agreement_name(self, name: str) -> str:
        """Обрезает name_fi до первого 'ehtosopimus', убирает PDF-артефакты."""
        name = re.sub(
            r"-\s+", "-", name
        )  # "RAKENNUSTUOTE- TEOLLISUUDEN" → "RAKENNUSTUOTE-TEOLLISUUDEN"
        lower = name.lower()
        idx = lower.find("ehtosopimus")
        if idx != -1:
            name = name[: idx + len("ehtosopimus")]
        return name.strip()

    def _clean_text(self, text: str) -> str:
        if not text:
            return text

        text = text.replace("\x00", "")

        text = re.sub(r"[\x00-\x08\x0B-\x1F\x7F]", "", text)

        return text

    def _resolve_topic(self, title_fi: str, text_fi: str = "") -> str | None:
        """Маппит заголовок параграфа на topic_key через общий реестр."""
        title_topic = detect_topic(title_fi)
        if title_topic:
            return title_topic
        # Fallback: проверяем тело клаузы (первые 500 символов достаточно)
        if text_fi:
            return detect_topic(text_fi[:500])
        return None
