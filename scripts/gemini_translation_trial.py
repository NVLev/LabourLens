#!/usr/bin/env python
"""
Пробный прогон перевода fi -> en/ru через Gemini API (Google AI Studio, бесплатный уровень).

Скрипт живёт вне приложения (ничего не импортирует из app/) и ничего не пишет в БД.
Тексты для теста берёт из scripts/trial_texts/*.txt, результаты пишет в
scripts/trial_results/gemini_<время>.md (вместе с сырым ответом модели).

Ключ: переменная окружения GEMINI_API_KEY (или GOOGLE_API_KEY).
Не называйте её с префиксом APP_: если переменной нет в Settings, pydantic
ругнётся при чтении .env.

Установка SDK (внутри контейнера app, для пробы достаточно):
  docker-compose exec app pip install google-genai

Лимиты бесплатного уровня (из AI Studio, проект Translation, на 22.11.2026; могут меняться):
  gemini-3.5-flash-lite / gemini-3.1-flash-lite: 15 RPM, 250K TPM, 500 RPD
  gemini-3.6-flash, 3.8-flash, 3-flash, 2.5-flash: 5 RPM, 250K TPM, 20 RPD
Поэтому для Flash-Lite хватает --delay 5, а для моделей Flash ставьте --delay 13
и --max-requests не больше 5.

Итоги проб (22.11.2026; клаузы 1743, 14484, 1793, 29131):
  gemini-3.5-flash-lite и gemini-3.1-flash-lite - выбраны, две параллельные «полосы»
  (независимость суточных квот проверить на практике);
  gemma-4-31b-it - не подходит: примерно в 6 раз медленнее, периодические 503;
  пачки клауз в одном запросе - не использовать (терялся русский или возвращался финский);
  один язык за запрос - не нужен (медленнее и не надёжнее).
Русские варианты терминов в GLOSSARIES, помеченные (?), - черновые, ждут согласования.
Номера страниц PDF (строки из одних цифр) модель выбрасывает, и валидатор видит это как
MISSING NUMBERS: в сервисе их нужно вырезать до отправки.

Глоссарий двухуровневый:
  core  - термины и названия законов, общие для всех TES (подключается всегда);
  kt    - термины, специфичные для договоров KT (подключается флагом --glossary kt).
Для других профсоюзов добавляйте свои наборы в GLOSSARIES и подключайте флагом.

Проверки результата: числа, циклы, иероглифы, длина, доля кириллицы, число строк у
секторов, согласованность названий законов EN/RU, НЕПЕРЕВЕДЁННЫЙ текст (финские
буквы и строки, совпавшие с источником дословно). Невидимые символы (U+200B и др.)
вырезаются из ответа до проверки; сколько вырезано, пишется в отчёт.

Ошибки: 429 по минутной квоте - одна повторная попытка после паузы из ответа
(или 60 с); 429 по суточной квоте - модель отключается; 500/503 - до двух
повторов с паузами 30 и 60 с.

Примеры (из корня проекта, внутри контейнера app):

  # 1) по одному тексту за запрос, оба языка в одном ответе
  docker-compose exec -T app python scripts/gemini_translation_trial.py

  # 2) клаузы KT с глоссарием KT
  docker-compose exec -T app python scripts/gemini_translation_trial.py \
      --glossary kt --files scripts/trial_texts/14484.txt

  # 3) самая длинная клауза (нужен больший лимит ответа)
  docker-compose exec -T app python scripts/gemini_translation_trial.py \
      --max-tokens 16000 --files scripts/trial_texts/29131.txt

  # 4) сравнение моделей на одних и тех же текстах
  docker-compose exec -T app python scripts/gemini_translation_trial.py \
      --models gemini-3.5-flash-lite gemini-3.1-flash-lite --files scripts/trial_texts/1743.txt

  # 5) несколько клауз в одном запросе
  docker-compose exec -T app python scripts/gemini_translation_trial.py --pack \
      --files scripts/trial_texts/1743.txt scripts/trial_texts/1729.txt

  # 6) один язык за запрос
  docker-compose exec -T app python scripts/gemini_translation_trial.py --mode ru \
      --files scripts/trial_texts/1793.txt

Для Gemma: --inline-system (системный промпт вклеивается в сообщение пользователя).
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

from google import genai
from google.genai import errors, types

try:  # необязательная проверка русских слов по словарю: pip install pymorphy3
    import pymorphy3

    _MORPH = pymorphy3.MorphAnalyzer()
except Exception:  # пакет не установлен - проверка просто отключена
    _MORPH = None

TEXTS_DIR = Path("scripts/trial_texts")
RESULTS_DIR = Path("scripts/trial_results")
DEFAULT_MODELS = ["gemini-3.5-flash-lite"]  # 500 запросов в сутки на бесплатном уровне
RETRY_WAITS_5XX = [30, 60]  # паузы перед повторами при 500/503, секунды

# ----------------------------------------------------------------------------
# Глоссарии. Русские варианты, отмеченные (?), предложены без согласования - поправьте.
# ----------------------------------------------------------------------------
GLOSSARIES: dict[str, str] = {
    # Общие для всех TES: устойчивая лексика трудового права и названия законов.
    "core": """\
ylityö = overtime / сверхурочная работа
lisätyö = additional work / дополнительная работа
työehtosopimus = collective agreement / коллективный договор
työsopimuslaki = Employment Contracts Act / Закон о трудовых договорах
työaikalaki = Working Hours Act / Закон о рабочем времени
vuosilomalaki = Annual Holidays Act / Закон о ежегодных отпусках
työturvallisuuslaki = Occupational Safety and Health Act / Закон об охране труда
vuosiloma = annual leave / ежегодный отпуск
keskituntiansio = average hourly earnings / средний часовой заработок
urakkatyö = piecework / сдельная работа
tasoittumisjakso = averaging period / период усреднения рабочего времени
tarkastelujakso = review period / учётный период (?)
pöytäkirjamerkintä = protocol note / протокольная запись
viikkolepopäivä = weekly rest day / день еженедельного отдыха
lomautus = furlough (temporary lay-off) / временное увольнение (?)
sairausajan palkka = sick pay / оплата за период болезни (?)
omailmoitus = self-notification of sick leave / самостоятельное уведомление о болезни (?)
työterveyshuolto = occupational health care / охрана здоровья на рабочем месте (?)
työterveyshuoltolaki = Occupational Health Care Act / Закон об охране здоровья на рабочем месте (?)
arkipäivä = working day (weekday) / будний день (?)
kalenteripäivä = calendar day / календарный день
korvaus (pay, compensation) = compensation / компенсация, выплата; never "ущерб" \
(that is vahinko, damage)
pykälä = section / параграф: in running text write "section N" / "параграф N", \
but a heading of the form "N §" keeps "N §" exactly as in the source
luku = chapter / глава
"N mom." (momentti) = subsection / абзац: write "N subsection" in English and \
"N абз." in Russian, keeping the number first as in the source.
The Finnish acts (työsopimuslaki, työaikalaki, vuosilomalaki, työturvallisuuslaki) \
are different laws: never replace one by another.""",
    # Специфичные для договоров KT (municipal / wellbeing services county employers).
    "kt": """\
hyvinvointialue = wellbeing services county / регион благополучия (?)
hyvinvointiala (as a sector name) = wellbeing services sector / сфера благополучия (?)
viranhaltija = office holder / должностное лицо
tasopalkka = flat-rate salary / фиксированная заработная плата (?); \
use the same Russian term every time
palkkaryhmä = salary group / группа оплаты труда
harjoittelija = trainee / стажёр (?)
kesätyöntekijä = summer employee / летний работник
luontoisetu = fringe benefit / натуральная льгота""",
}

SECTORS_HINT = (
    "The input is a list of names of industry sectors covered by Finnish collective "
    "agreements, one per line. Output exactly one translated line per input line, "
    "in the same order, with no numbering and no empty lines."
)


def build_glossary(extra: list[str]) -> str:
    names = ["core", *[n for n in extra if n != "core"]]
    return "\n".join(GLOSSARIES[n] for n in names)


# ----------------------------------------------------------------------------
# Промпт и разбор ответа
# ----------------------------------------------------------------------------
def build_system_prompt(mode: str, packed: bool, sectors: bool, glossary: str) -> str:
    langs = {"en": "English", "ru": "Russian", "both": "English and Russian"}[mode]
    parts = [
        f"You are a professional legal translator from Finnish into {langs}.",
        "You translate excerpts of Finnish collective labour agreements (työehtosopimus).",
        "Rules:",
        "1. Translate everything into the target language(s). Do not omit, summarize, "
        "merge or add anything, and never copy the Finnish text into the output.",
        "2. Keep every number, percentage, date, amount and § reference exactly "
        "as in the source; write numbers as digits and do not reformat dates "
        "(2.2.2017 stays 2.2.2017).",
        "3. Keep the line structure: headings stay on their own lines; keep "
        "Markdown tables as Markdown tables.",
        "4. Use this glossary where the term occurs; for terms not in the glossary "
        "choose the standard legal translation:\n" + glossary,
        "5. Give exactly one translation of each term: no alternatives, no "
        "explanations or comments in brackets.",
        "6. Output only the translation, with no comments.",
        "7. If the source breaks off mid-sentence or contains '...', keep it exactly "
        "so; never complete or smooth over a sentence that is incomplete in the source.",
        "8. Use only real words of the target language. If unsure how to render a "
        "term, use a plain descriptive phrase rather than inventing a word.",
    ]
    if sectors:
        parts.append(SECTORS_HINT)
    if packed:
        parts.append(
            "The input contains several clauses. Each clause starts with a marker "
            "line like <<<CLAUSE name>>>. Repeat every marker line exactly as it is "
            "in your output and translate each clause separately."
        )
    if mode == "both":
        if sectors:
            parts.append(
                "Output format: write the marker line ===EN=== exactly once, then all "
                "English lines, then the marker line ===RU=== exactly once, then all "
                "Russian lines. Do not repeat the markers for each line."
            )
        else:
            parts.append(
                "Output format for every text (or for every clause):\n"
                "===EN===\n<English translation>\n===RU===\n<Russian translation>\n"
                "Write each marker exactly once per text and always fill both sections."
            )
    return "\n".join(parts)


MARK_CLAUSE = re.compile(r"^<<<CLAUSE (.+?)>>>[ \t]*$", re.M)
MARK_LANG = re.compile(r"^===(EN|RU)===[ \t]*$", re.M)


def split_blocks(text: str, pattern: re.Pattern) -> list[tuple[str, str]]:
    """Режет текст по строкам-маркерам: [(метка, тело), ...]."""
    matches = list(pattern.finditer(text))
    blocks = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        blocks.append((m.group(1), text[m.end() : end].strip()))
    return blocks


def parse_response(text: str, mode: str, packed: bool, names: list[str]) -> dict:
    """{имя: {"en": ..., "ru": ..., "_warn": ...} или None, если блок не найден}.

    Ключи, начинающиеся с "_", служебные (не язык). Пустые блоки (например,
    «===RU===» два раза подряд) игнорируются.
    """
    by_name = dict(split_blocks(text, MARK_CLAUSE)) if packed else {names[0]: text}
    result = {}
    for name in names:
        body = by_name.get(name)
        if body is None:
            result[name] = None
        elif mode == "both":
            blocks = [(k, v) for k, v in split_blocks(body, MARK_LANG) if v]
            counts = Counter(k for k, _ in blocks)
            langs = {k.lower(): v for k, v in blocks}
            entry = {"en": langs.get("en"), "ru": langs.get("ru")}
            dups = {k: n for k, n in counts.items() if n > 1}
            if dups:
                entry["_warn"] = (
                    f"LANGUAGE MARKERS REPEATED WITH CONTENT {dups}: only the last "
                    "block of each language is kept above, see the raw response"
                )
            result[name] = entry
        else:
            result[name] = {mode: body.strip()}
    return result


# ----------------------------------------------------------------------------
# Очистка и проверки качества (упрощённый прототип будущего валидатора)
# ----------------------------------------------------------------------------
_INVISIBLE = re.compile("[\u200b\u200c\u200d\u2060\ufeff\u00ad]")
_DATE_FULL = re.compile(r"\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b")  # 31.1.2020 -> 31 2020
_DATE_SHORT = re.compile(r"\b(\d{1,2})\.(\d{1,2})\.")  # 1.5. -> 1
_WORD_LOOP = re.compile(r"\b([^\W\d_]{2,})\b(?:\s+\1\b){3,}", re.I)
_PHRASE_LOOP = re.compile(r"(.{12,80}?)(?:\s*\1){2,}")
_CJK = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af]")
_CYR = re.compile(r"[А-Яа-яЁё]")
_LETTER = re.compile(r"[^\W\d_]")
_FI_CHARS = re.compile(r"[äöåÄÖÅ]")

# Названия законов: сколько раз каждый встречается в EN и в RU должно совпадать.
LAW_NAMES: dict[str, tuple[re.Pattern, re.Pattern]] = {
    "Employment Contracts Act": (
        re.compile(r"Employment Contracts Act|Contracts of Employment Act", re.I),
        re.compile(r"Закон\w*\s+о\s+трудов\w+\s+договор\w*", re.I),
    ),
    "Working Hours Act": (
        re.compile(r"Working Hours Act", re.I),
        re.compile(r"Закон\w*\s+о\s+рабочем\s+времени", re.I),
    ),
    "Annual Holidays Act": (
        re.compile(r"Annual Holidays Act", re.I),
        re.compile(r"Закон\w*\s+о\s+ежегодных\s+отпусках", re.I),
    ),
    "Occupational Safety and Health Act": (
        re.compile(r"Occupational Safety and Health Act", re.I),
        re.compile(r"Закон\w*\s+об\s+охране\s+труда", re.I),
    ),
}


_SRC_WORKDAY = re.compile(r"(\d+)\s+(?:arkipäiv\w*|työpäiv\w*)", re.I)
_SRC_CALDAY = re.compile(r"(\d+)\s+kalenteripäiv\w*", re.I)
_OUT_WORKDAY = {
    "en": r"{n}\s+(?:\w+\s+)?(?:working\s+days?|workdays?|weekdays?|business\s+days?)",
    "ru": r"{n}\s+(?:\w+\s+)?(?:рабоч\w+|будн\w+)\s+дн\w*",
}
_OUT_CALDAY = {
    "en": r"{n}\s+(?:\w+\s+)?calendar\s+days?",
    "ru": r"{n}\s+(?:\w+\s+)?календарн\w+\s+дн\w*",
}
_RU_WORD = re.compile(r"[А-Яа-яЁё]{5,}")


def check_day_units(src: str, out: str, lang: str) -> list[str]:
    """«9 arkipäivää» должно остаться рабочими/будними днями, а не календарными."""
    if lang not in _OUT_WORKDAY:
        return []
    issues = []
    for rx, table, label in (
        (_SRC_WORKDAY, _OUT_WORKDAY, "working days/weekdays"),
        (_SRC_CALDAY, _OUT_CALDAY, "calendar days"),
    ):
        for n in sorted(set(rx.findall(src)), key=int):
            if not re.search(table[lang].format(n=re.escape(n)), out, re.I):
                issues.append(
                    f"DAY UNIT MISMATCH: source has {n} {label}, "
                    f"not found in {lang.upper()} output"
                )
    return issues


def check_ru_words(out: str) -> list[str]:
    """Слова, которых нет в словаре pymorphy3 (выдумки вроде «самоноселения»).
    Только предупреждение: имена и сокращения тоже могут попасть в список."""
    if _MORPH is None:
        return []
    unknown: Counter = Counter()
    for word in _RU_WORD.findall(out):
        low = word.lower()
        if not _MORPH.word_is_known(low):
            unknown[low] += 1
    if not unknown:
        return []
    top = ", ".join(f"{w}({n})" for w, n in unknown.most_common(15))
    return [f"UNKNOWN RUSSIAN WORDS (info): {top}"]


def clean_output(text: str) -> tuple[str, int]:
    """Вырезает невидимые символы (U+200B и др.), неразрывный пробел -> обычный.
    Возвращает (текст, сколько символов затронуто)."""
    n = len(_INVISIBLE.findall(text)) + text.count("\xa0")
    return _INVISIBLE.sub("", text).replace("\xa0", " "), n


def number_tokens(text: str) -> list[str]:
    """Все группы цифр. Даты dd.mm.yyyy и dd.mm. упрощаются (месяц словом в переводе)."""
    text = _DATE_FULL.sub(r"\1 \3", text)
    text = _DATE_SHORT.sub(r"\1 ", text)
    return re.findall(r"\d+", text)


def _letter_share(line: str) -> float:
    stripped = line.strip()
    return len(_LETTER.findall(stripped)) / len(stripped) if stripped else 0.0


def check_untranslated(src: str, out: str, lang: str) -> list[str]:
    """Финский текст под видом перевода: финские буквы и строки, совпавшие с
    источником дословно (строки из цифр/таблиц игнорируются)."""
    issues = []
    letters = len(_LETTER.findall(out)) or 1
    fi = len(_FI_CHARS.findall(out))
    if lang == "en" and fi / letters > 0.005:
        issues.append(f"FINNISH LETTERS IN EN OUTPUT ({fi})")
    if lang == "ru" and fi >= 3:
        issues.append(f"FINNISH LETTERS IN RU OUTPUT ({fi})")

    src_lines = {
        s.strip()
        for s in src.splitlines()
        if len(s.strip()) >= 20 and _letter_share(s) >= 0.6
    }
    if src_lines:
        out_lines = {s.strip() for s in out.splitlines()}
        share = len(src_lines & out_lines) / len(src_lines)
        if share > 0.2:
            issues.append(f"UNTRANSLATED LINES: {share:.0%} of source lines appear verbatim")
    return issues


def run_checks(src: str, out: str | None, lang: str, sectors: bool = False) -> list[str]:
    if not out:
        return ["EMPTY OR MISSING OUTPUT"]
    issues: list[str] = []

    missing = sorted(set(number_tokens(src)) - set(number_tokens(out)), key=int)
    if missing:
        issues.append(f"MISSING NUMBERS: {missing}")
    extra = sorted(set(number_tokens(out)) - set(number_tokens(src)), key=int)
    if extra:
        issues.append(f"extra numbers (info): {extra}")

    issues.extend(check_untranslated(src, out, lang))
    issues.extend(check_day_units(src, out, lang))
    if lang == "ru":
        issues.extend(check_ru_words(out))

    no_tables = "\n".join(
        line for line in out.splitlines() if not line.lstrip().startswith("|")
    )
    if _WORD_LOOP.search(out):
        issues.append("REPEATED WORD LOOP")
    elif _PHRASE_LOOP.search(no_tables):
        issues.append("REPEATED PHRASE LOOP")

    if _CJK.search(out):
        issues.append("CJK CHARACTERS IN OUTPUT")
    if "<think>" in out.lower():
        issues.append("THINK TAGS IN OUTPUT")

    ratio = len(out) / max(len(src), 1)
    if ratio < 0.65:
        issues.append(f"OUTPUT MUCH SHORTER ({ratio:.2f}) - possible omission")
    elif ratio > 1.7:
        issues.append(f"OUTPUT MUCH LONGER ({ratio:.2f})")

    if lang == "ru":
        letters = len(_LETTER.findall(out))
        share = len(_CYR.findall(out)) / letters if letters else 0
        if share < 0.7:
            issues.append(f"LOW CYRILLIC SHARE ({share:.2f})")

    if sectors:
        n_src = len([line for line in src.splitlines() if line.strip()])
        n_out = len([line for line in out.splitlines() if line.strip()])
        if n_src != n_out:
            issues.append(f"LINE COUNT MISMATCH: source {n_src}, output {n_out}")
    return issues


def check_cross_language(en: str | None, ru: str | None) -> list[str]:
    """Названия законов в EN и RU должны встречаться одинаковое число раз."""
    if not en or not ru:
        return []
    issues = []
    for law, (en_re, ru_re) in LAW_NAMES.items():
        n_en, n_ru = len(en_re.findall(en)), len(ru_re.findall(ru))
        if n_en != n_ru:
            issues.append(f"LAW NAME MISMATCH: {law} en={n_en} ru={n_ru}")
    return issues


# ----------------------------------------------------------------------------
# Вызов API
# ----------------------------------------------------------------------------
def load_api_key() -> str:
    for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        if os.environ.get(name):
            return os.environ[name]
    sys.exit("API key not found: set GEMINI_API_KEY (or GOOGLE_API_KEY).")


def parse_retry(exc: errors.APIError) -> tuple[float | None, bool]:
    """(через сколько секунд повторять или None, суточная ли это квота)."""
    text = f"{exc} {getattr(exc, 'details', '')}"
    compact = re.sub(r"[\s_]", "", text).lower()
    daily = "perday" in compact
    m = re.search(r"retry(?:Delay|\s+in)\D{0,8}(\d+(?:\.\d+)?)\s*s", text, re.I)
    return (float(m.group(1)) if m else None), daily


def call_model(
    client: genai.Client,
    model: str,
    system: str,
    user: str,
    max_tokens: int,
    thinking: dict,
    inline_system: bool,
) -> dict:
    """Один логический запрос с повторами: 429 (минутная квота) - один повтор,
    500/503 - до двух повторов с паузами RETRY_WAITS_5XX."""
    contents = f"{system}\n\n---\n\n{user}" if inline_system else user
    cfg: dict = {"temperature": 0, "max_output_tokens": max_tokens}
    if not inline_system:
        cfg["system_instruction"] = system
    if thinking:
        cfg["thinking_config"] = types.ThinkingConfig(**thinking)
    config = types.GenerateContentConfig(**cfg)

    result: dict = {"ok": False, "retries": 0}
    rate_retried = False
    server_retries = 0
    while True:
        t0 = time.time()
        try:
            resp = client.models.generate_content(
                model=model, contents=contents, config=config
            )
        except errors.APIError as exc:
            result["elapsed"] = round(time.time() - t0, 1)
            result["status"] = exc.code
            result["error"] = {
                "reason": exc.status,
                "message": str(exc.message)[:300],
            }
            if exc.code == 429:
                retry_after, daily = parse_retry(exc)
                if daily or (retry_after is not None and retry_after > 120):
                    result["stop_model"] = True  # закончилась суточная квота
                    return result
                if not rate_retried:
                    rate_retried = True
                    wait = (retry_after + 1) if retry_after is not None else 60
                    print(f"    429, waiting {wait:.0f}s and retrying once...")
                    time.sleep(wait)
                    result["retries"] += 1
                    continue
            elif (
                exc.code is not None
                and exc.code >= 500
                and server_retries < len(RETRY_WAITS_5XX)
            ):
                wait = RETRY_WAITS_5XX[server_retries]
                server_retries += 1
                print(f"    {exc.code} ({exc.status}), waiting {wait}s and retrying...")
                time.sleep(wait)
                result["retries"] += 1
                continue
            return result
        except Exception as exc:  # сеть, таймаут и т.п.
            result.update(
                status=None,
                elapsed=round(time.time() - t0, 1),
                error={"message": f"network: {exc!r}"[:300]},
            )
            return result

        result["elapsed"] = round(time.time() - t0, 1)
        result["status"] = 200
        result.pop("error", None)
        usage = resp.usage_metadata
        cand = resp.candidates[0] if resp.candidates else None
        fr = getattr(cand, "finish_reason", None)
        result.update(
            ok=True,
            content=resp.text or "",
            finish_reason=getattr(fr, "name", str(fr)) if fr else None,
            usage={
                "prompt": getattr(usage, "prompt_token_count", None),
                "output": getattr(usage, "candidates_token_count", None),
                "thoughts": getattr(usage, "thoughts_token_count", None),
            },
        )
        return result


# ----------------------------------------------------------------------------
# Основная логика
# ----------------------------------------------------------------------------
def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip("\n")


def make_jobs(files: list[Path], pack: bool) -> list[dict]:
    if pack:
        names = [p.stem for p in files]
        user = "\n".join(f"<<<CLAUSE {p.stem}>>>\n{read_text(p)}" for p in files)
        sources = {p.stem: read_text(p) for p in files}
        return [{"label": "+".join(names), "names": names, "user": user,
                 "sources": sources, "packed": True, "sectors": False}]
    jobs = []
    for p in files:
        text = read_text(p)
        jobs.append({"label": p.stem, "names": [p.stem], "user": text,
                     "sources": {p.stem: text}, "packed": False,
                     "sectors": p.stem.startswith("sectors")})
    return jobs


def run_trial(args: argparse.Namespace, client: genai.Client) -> None:
    files = [Path(f) for f in args.files] if args.files else sorted(TEXTS_DIR.glob("*.txt"))
    if not files:
        sys.exit(f"No test texts: put *.txt files into {TEXTS_DIR}/")
    jobs = make_jobs(files, args.pack)
    glossary = build_glossary(args.glossary)

    thinking: dict = {}
    if args.thinking_budget is not None:
        thinking["thinking_budget"] = args.thinking_budget
    if args.thinking_level:
        thinking["thinking_level"] = args.thinking_level

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    report = RESULTS_DIR / f"gemini_{datetime.now():%Y%m%d_%H%M%S}.md"
    summary: list[str] = []
    used = 0
    dead_models: set[str] = set()
    out_of_budget = False

    with report.open("w", encoding="utf-8") as fh:
        fh.write(f"# Gemini trial {datetime.now():%Y-%m-%d %H:%M}\n\n"
                 f"models: {args.models}, mode: {args.mode}, pack: {args.pack}, "
                 f"glossary: core+{args.glossary or '-'}, "
                 f"thinking: {thinking or 'default'}, max_tokens: {args.max_tokens}\n\n")
        for job in jobs:
            if out_of_budget:
                break
            for model in args.models:
                if used >= args.max_requests:
                    print("Request budget exhausted (--max-requests).")
                    out_of_budget = True
                    break
                if model in dead_models:
                    continue
                if used:
                    time.sleep(args.delay)
                used += 1
                system = build_system_prompt(args.mode, job["packed"], job["sectors"], glossary)
                print(f"[{used}/{args.max_requests}] {model} <- {job['label']} "
                      f"({len(job['user'])} chars)")
                res = call_model(client, model, system, job["user"], args.max_tokens,
                                 thinking, args.inline_system)

                fh.write(f"\n---\n## {job['label']} / {model}\n\n")
                fh.write(f"status: {res.get('status')}, elapsed: {res.get('elapsed')}s, "
                         f"retries: {res['retries']}\n\n")
                line = f"{model:28} {job['label'][:28]:28} status={res.get('status')}"
                if not res["ok"]:
                    err = res.get("error", {})
                    fh.write(f"ERROR: {err}\n")
                    line += f"  ERROR {err.get('reason') or err.get('message')}"
                    summary.append(line)
                    print("   ", line)
                    if res.get("stop_model"):
                        dead_models.add(model)
                    fh.flush()
                    continue

                raw = res["content"].strip()
                text, n_cleaned = clean_output(raw)
                usage = res["usage"]
                fh.write(f"finish_reason: {res['finish_reason']}, usage: {usage}\n\n")
                if n_cleaned:
                    fh.write(f"cleaned invisible/nbsp characters: {n_cleaned}\n\n")
                parsed = parse_response(text, args.mode, job["packed"], job["names"])
                total_issues = 0
                for name in job["names"]:
                    block = parsed[name]
                    fh.write(f"### {name}\n\n")
                    if block is None:
                        fh.write("MARKER NOT FOUND IN OUTPUT\n\n")
                        total_issues += 1
                        continue
                    if block.get("_warn"):
                        total_issues += 1
                        fh.write(f"WARNING: {block['_warn']}\n\n")
                    for lang, out in block.items():
                        if lang.startswith("_"):
                            continue
                        issues = run_checks(job["sources"][name], out, lang, job["sectors"])
                        hard = [i for i in issues if "(info)" not in i]
                        total_issues += len(hard)
                        fh.write(f"**{lang.upper()}** checks: {issues or 'OK'}\n\n{out}\n\n")
                    if args.mode == "both":
                        cross = check_cross_language(block.get("en"), block.get("ru"))
                        total_issues += len(cross)
                        fh.write(f"**EN/RU consistency**: {cross or 'OK'}\n\n")
                if res["finish_reason"] not in (None, "STOP"):
                    total_issues += 1
                    fh.write(f"WARNING: finish_reason={res['finish_reason']} "
                             "(output may be cut off or blocked)\n\n")
                fh.write(f"#### Raw response\n\n~~~~\n{raw}\n~~~~\n")
                line += (f" {res['elapsed']}s tokens(in/out/thoughts)="
                         f"{usage['prompt']}/{usage['output']}/{usage['thoughts']} "
                         f"finish={res['finish_reason']} cleaned={n_cleaned} "
                         f"issues={total_issues}")
                summary.append(line)
                print("   ", line)
                fh.flush()

    print("\n=== SUMMARY ===")
    print("\n".join(summary))
    print(f"\nRequests used: {used}. Report: {report}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models", nargs="+", default=DEFAULT_MODELS, help="id моделей Gemini API")
    ap.add_argument("--files", nargs="*", help="тексты для теста (по умолчанию scripts/trial_texts/*.txt)")
    ap.add_argument("--mode", choices=["en", "ru", "both"], default="both")
    ap.add_argument("--glossary", nargs="*", default=[],
                    choices=[k for k in GLOSSARIES if k != "core"],
                    help="дополнительные глоссарии поверх core (например: kt)")
    ap.add_argument("--pack", action="store_true", help="все файлы одним запросом")
    ap.add_argument("--max-requests", type=int, default=12, help="бюджет запросов за запуск")
    ap.add_argument("--delay", type=float, default=5.0,
                    help="пауза между запросами, с (Flash-Lite: 5; модели Flash с 5 RPM: 13)")
    ap.add_argument("--max-tokens", type=int, default=8000)
    ap.add_argument("--thinking-budget", type=int, default=None,
                    help="ThinkingConfig.thinking_budget (0 = выключить, если модель позволяет)")
    ap.add_argument("--thinking-level", default=None,
                    help="ThinkingConfig.thinking_level (например minimal/low), для новых моделей")
    ap.add_argument("--inline-system", action="store_true",
                    help="вклеить системный промпт в сообщение пользователя (для Gemma)")
    args = ap.parse_args()

    if args.delay < 4:
        print("Warning: --delay < 4 s may exceed 15 RPM.")

    client = genai.Client(
        api_key=load_api_key(),
        http_options=types.HttpOptions(timeout=240_000),  # миллисекунды
    )
    run_trial(args, client)


if __name__ == "__main__":
    main()
