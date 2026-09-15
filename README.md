# LabourLens

Агрегатор финского трудового права для русскоязычной аудитории в Финляндии.
Парсит законы (Finlex), официальные разъяснения (Työsuojelu, профсоюзы), коллективные
договоры (TES/työehtosopimus). Переводит fi→en и fi→ru. Отвечает на ситуационные вопросы
через rule-based FAQ движок и рассчитывает ставки TES через калькулятор.

**Состояние на 5 августа 2026.**

Интерфейсы: Telegram-бот (aiogram 3.x) + REST API (FastAPI).

---

## Стек

| Слой | Технология |
|---|---|
| Backend | FastAPI + uvicorn |
| Database | PostgreSQL 16 + SQLAlchemy 2.0 async |
| Migrations | Alembic |
| Validation | Pydantic v2 + pydantic-settings |
| HTTP client | httpx (async) + requests (fallback для PDF за WAF) |
| HTML parsing | BeautifulSoup4 |
| PDF parsing | pdfplumber |
| XML parsing | lxml (Akoma Ntoso, Finlex) |
| Translation | NLLB-200-distilled-600M (fi→en, fi→ru), Helsinki-NLP не используется |
| Bot | aiogram 3.x + MemoryStorage FSM |
| Infrastructure | Docker Compose |

---

## Структура проекта

```
LabourLens/
├── config.py                        — Pydantic BaseSettings, префикс APP_
├── docker-compose.yml
├── Dockerfile
├── alembic.ini
├── pyproject.toml
│
├── alembic/
│   └── versions/                    — миграции (17 ревизий на сегодня)
│
├── app/
│   ├── app_main.py                  — FastAPI, подключение роутеров, lifespan (прогрев NLLB)
│   │
│   ├── database/
│   │   ├── db_helper.py             — AsyncEngine, session factory (autoflush=False)
│   │   ├── models.py                — все SQLAlchemy ORM модели
│   │   └── schemas/                 — Pydantic-схемы
│   │
│   ├── parsing/                     — слой парсинга источников
│   │   ├── finlex.py                — законы, httpx + lxml (Akoma Ntoso XML)
│   │   ├── tyosuojelu.py            — разъяснения tyosuojelu.fi → Interpretation
│   │   ├── tehy.py                  — разъяснения Tehy → Interpretation
│   │   ├── ilry.py                  — FAQ по трудовому праву для инженеров → Interpretation
│   │   ├── topic_keywords.py        — detect_topic(): маппинг текста клаузулы на topic_key
│   │   └── tes/
│   │       ├── union_portal.py      — универсальный 2-шаговый парсер каталогов профсоюзов
│   │       ├── pam.py               — TesPdfParser: общий парсер PDF-договоров (pdfplumber)
│   │       ├── pam_html.py          — PamParser: HTML-парсер договоров pam.fi (с 2 июля)
│   │       └── kt.py                — KtParser: HTML-парсер договоров kt.fi (3-уровневая структура)
│   │
│   ├── calculator/                  — TES-калькулятор ставок (в разработке)
│   │   ├── enums.py                 — RateType: min_wage, overtime_threshold_hours,
│   │   │                               overtime_rate_tier1_pct, night_bonus, sunday_bonus_pct
│   │   ├── service.py               — TesRateService: extract → upsert в TesRate
│   │   └── extractors/
│   │       └── kt_rate.py           — regex-экстракторы для KT (min_wage готов,
│   │                                   extract_kt_overtime() в проектировании)
│   │
│   ├── services/                    — слой бизнес-логики
│   │   ├── analyze_service.py       — сборка ответа: law + interpretations + FAQ по topic_key
│   │   ├── faq_service.py           — matching условий FaqRule
│   │   ├── faq_seed_service.py
│   │   ├── interpretation_service.py
│   │   ├── law_service.py
│   │   ├── tes_discovery_service.py — discover() + parse() пайплайн для порталов профсоюзов
│   │   ├── tes_service.py           — upsert клауз, relink_topics()
│   │   ├── topic_service.py
│   │   ├── translation_service.py
│   │   └── union_seed_service.py
│   │
│   ├── translation/
│   │   ├── nllb.py                  — основная модель перевода, прогревается на старте
│   │   ├── helsinki_nlp.py          — не используется (оставлен для истории)
│   │   └── cache.py                 — хэш-кэш, не переводим одно дважды
│   │
│   ├── application/
│   │   ├── sector_mapping.py        — SECTOR_GROUPS: группировка секторов для бота/фильтров
│   │   └── seeds/
│   │       ├── topic_map.py         — стартовый маппинг тем на параграфы законов
│   │       └── faq_rules.py         — seed-данные FAQ (10+ тем)
│   │
│   ├── repositories/                — слой доступа к данным
│   │   ├── faq.py
│   │   ├── laws.py
│   │   ├── topics.py
│   │   ├── tes.py                   — Union / Agreement / TesClause запросы
│   │   ├── tes_rate.py              — TesRate запросы (get_by_unique_key, add)
│   │   └── interpretations.py
│   │
│   └── routers/                     — REST API
│       ├── analyze.py               — POST /analyze/
│       ├── laws.py                  — GET /laws/...
│       ├── topics.py                — GET/POST /topics/...
│       ├── tes.py                   — GET /tes/..., POST /tes/relink-topics
│       ├── translate.py             — POST /translate/...
│       ├── calculator.py            — POST /calculator/extract/kt-min-wage
│       └── parse.py                 — POST /parse/... (finlex, tyosuojelu, tehy, ilry, tes, faq)
│
├── bot/
│   ├── bot_main.py                  — Dispatcher (HTML parse mode, MemoryStorage), логирование
│   ├── keyboards.py                 — Reply + Inline клавиатуры
│   ├── states.py                    — FSM SituationStates
│   └── routers/
│       ├── start.py                 — /start, выбор языка и профсоюза
│       ├── situation.py             — FSM визард: группа → сектор → тема → детали → результат
│       ├── laws.py                  — просмотр параграфов
│       ├── calculator.py            — TES-калькулятор (файл создан, логика не начата)
│       └── faq.py
│
└── scripts/, audit_keywords.py, review_mapping_quality.py, merge_verdicts.py
    — вспомогательные скрипты для аудита качества привязки топиков к клаузулам
```

---

## Модель данных

```
Act (закон)
 └─ Chapter (глава)
     └─ Section (§)
         └─ SectionParagraph — text_fi / text_en / text_ru

Topic (тема: "min_wage", "overtime", "dismissal"...) — центр графа
 ├─ TopicSection M2M → Section (relevance 1..3)
 ├─ Interpretation (tyosuojelu / tehy / ilry, опционально sector_fi)
 ├─ TesClause
 ├─ FaqRule (conditions: JSONB + answer_en/ru/fi)
 └─ TesRate

Union → UnionPortal → Agreement → TesClause
                                 → TesRate (rate_type, wage_group, value, unit,
                                             effective_from/until, rate_type_context,
                                             source_text, is_verified)

User → UserQuery
```

`TesRate` — таблица калькулятора. Уникальность:
`(agreement_id, rate_type, wage_group, effective_from)`.
Поле `rate_type_context` дополнительно разбивает ставки внутри одного `rate_type`
(например режим сверхурочных: `vuorokautinen` / `viikoittainen` / `jaksotyö`).

---

## API — основные группы эндпоинтов

```
POST /parse/finlex[/{act_key}]                парсинг законов
POST /parse/tyosuojelu[/{topic_key}]           разъяснения tyosuojelu.fi
POST /parse/tehy[/{slug}], /parse/ilry[/{slug}] разъяснения профсоюзов
POST /parse/unions/seed                        сид профсоюзов и порталов
POST /tes/discover/{union_key}                 обнаружение договоров на портале (без парсинга)
POST /parse/tes[/{key}]                        парсинг клауз одного/всех договоров
POST /tes/relink-topics                        пересчёт topic_id по актуальному topic_keywords
POST /parse/faq/seed                           сид FAQ-правил

GET  /laws/acts/{act_key}/{chapter}/{section}  текст параграфа fi/en/ru
GET  /topics/, GET /topics/{key}
GET  /tes/unions, GET /tes/agreements[?union_key=&sector_fi=]
GET  /tes/agreements/{key}                     договор со всеми клаузулами
GET  /tes/agreements/{key}/unlinked            клаузулы без topic_id (админ)
GET  /tes/topic/{topic_key}[?union_key=&sector_fi=&agreement_key=]
                                                основной endpoint для AnalyzeService и бота

POST /translate/laws/{en|ru}[/{act_key}]
POST /translate/interpretations/{en|ru}
POST /translate/tes/... (agreement / union_key)

POST /analyze/                                 {topic, employment_type, tenure_months, ...}
                                                → law + interpretations + FAQ-ответ

POST /calculator/extract/kt-min-wage           запуск экстрактора min_wage по клаузулам KT
```

---

## TES-калькулятор — текущее состояние

**Готово:**
- `TesRate` модель + Alembic-миграция, поля `wage_group` и `rate_type_context`
  для разграничения режимов переработки
- Экстрактор `extract_kt_min_wage()` в `kt_rate.py` — полный цикл: extractor → service →
  repository → router, идемпотентный upsert
- `TesRateService.extract_rates_for_kt()` — извлекает и апсертит ставки по клаузулам
  темы `min_wage` для союза `kt`

**В работе:** `extract_kt_overtime()` — тарифная сетка сверхурочных (50%/100%),
зависящая от режима работы (`vuorokautinen` / `viikoittainen` / `jaksotyö`).
Открытые вопросы дизайна: структура `rate_type` для порогов/часов, место периода
(`rate_type_context` vs отдельный rate_type), обработка клауз с несколькими режимами
подряд, форма возврата функции, нужен ли отдельный `_detect_mode()`.

**На горизонте (Category B — простые rate/percentage экстракторы):**
ночные и воскресные надбавки, holiday pay, `epäpätevyysalennus` (снижение за
неполную квалификацию), `hälytysraha` (плата за вызов).

**Отдельная нерешённая проблема — зарплатные таблицы (palkkataulukko):**
данные физически есть в PDF/HTML части договоров, но не унифицированы — у Fiskars
это повторяющийся блок "дата + список", у Hirsitaloteollisuus — настоящая
многоколоночная таблица, расплющенная в текст. Табличные форматы отличаются
у каждого профсоюза; нужен отдельный путь извлечения через `pdfplumber.extract_tables()`
вместо текущего `_rebuild_lines()` на словах.

---

## Известные технические решения и проблемы

- `datetime.now(timezone.utc)` везде, не `utcnow()`; колонки — `TIMESTAMPTZ`
- `autoflush=False` в session factory → после `session.add()` нужен явный `flush()`,
  иначе `MultipleResultsFound`
- Дубли строк TesRate возникают, когда несколько клауз одного договора содержат
  одинаковое значение ставки — дедупликация на уровне апсерта по unique key
- `**dict` в функцию с уже заданными keyword-аргументами → `TypeError`, распаковывать
  аккуратно
- Топики цепляются за слово `palkka/palkat` без проверки контекста → шумные клаузулы
  без чисел (обязанности, отпуск без содержания, перекрёстные ссылки). Аудит — через
  SQL по подзапросам topic key, отсечение по regex-фильтру "похоже на реальную ставку"
  перед структурированием
- Дата действия договора (`valid_from/until`) иногда доступна только как диапазон лет
  (`2025–2028`) — есть резервный `YEAR_RANGE_RE`
- Название договора (`name_fi`) чистится через STOPWORDS-фильтр, ограничение длины
  строки/числа строк, обрезка по первому вхождению "ehtosopimus", схлопывание дублей

---

## Docker

```
PostgreSQL — localhost:5434
Adminer    — localhost:8085
App        — localhost:8003
```

Запуск: `docker-compose up`. При старте `app` применяет `alembic upgrade head`,
прогревает модель NLLB и поднимает uvicorn. `bot` стартует после `app`.

---

## Дальнейшие шаги

1. Regex-паттерны и реализация `extract_kt_overtime()` (нужны реальные `text_fi`
   из Lääkärit, Henkilöstövuokrausala, MaRa jaksotyö)
2. Category B экстракторы (ночные/воскресные надбавки, holiday pay, epäpätevyysalennus,
   hälytysraha)
3. Решение по зарплатным таблицам — `pdfplumber.extract_tables()` для табличных клауз
4. `bot/routers/calculator.py` — FSM для ввода часов/зарплаты и вывода расчёта
5. Параллельно — ручной анализ клауз `working_hours` (отдельная методология,
   независимый поток работы)
