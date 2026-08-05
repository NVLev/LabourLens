# LabourLens — Project Structure

```
LabourLens/
├── config.py                        — Pydantic BaseSettings, префикс APP_
├── docker-compose.yml
├── pyproject.toml
├── .env
│
├── app/
│   ├── app_main.py                  — FastAPI, подключение роутеров
│   │
│   ├── database/
│   │   ├── db_helper.py             — AsyncEngine, get_session
│   │   ├── models.py                — SQLAlchemy ORM models
│   │   └── schemas/
│   │       ├── law.py               — Act, Chapter, Section, Paragraph
│   │       ├── topic.py             — Topic, TopicSection
│   │       ├── interpretation.py    — Interpretation
│   │       ├── tes.py               — Union, Agreement, TesClause
│   │       ├── faq.py               — FaqRule, FaqSectionRef
│   │       └── user.py              — User, UserQuery
│   │
│   ├── parsing/                     — Слой парсинга
│   │   ├── finlex.py                — httpx + BS4, статика
│   │   ├── tyosuojelu.py            — общие рекомендации, сохранение в модель Interpretations
│   │   ├── tehy.py                  — сохранение в модель Interpretations
│   │   ├── ilry.py                  — сохранение в модель Interpretations
│   │   ├── scheduler.py             — APScheduler, периодический запуск
│   │   └── tes/
│   │       ├── pam.py               — универсальный парсер pdf
│   │       ├── kt.py                — парсер HTML с сохранением в модель 
│   │       └── union_portal.py      — универсальный парсер порталов профсоюзов, поиск договоров
│   │
│   ├── services/                     — Слой бизнес-логики
│   │   ├── analyze_service.py        
│   │   ├── faq_service.py              
│   │   ├── interpretation_service.py          
│   │   ├── law_service.py
│   │   ├── tes_discovery_service.py
│   │   ├── tes_service.py
│   │   ├── topic_service.py
│   │   ├── translation_service.py
│   │   └── union_seed_service
│   │
│   ├── translation/                 — Слой перевода fi → en
│   │   ├── helsinki_nlp.py          — локальная модель (Helsinki-NLP)
│   │   ├── nllb.py                 — fallback, Free API 500k/мес
│   │   └── cache.py                 — не переводим одно дважды (хэш)
│   │
│   ├── application/                 — Бизнес-логика
│   │   ├── tes_calculator.py        — расчёт ставок (сверхурочные, праздники)
│   │   ├── situation_resolver.py    — topic → sections + interpretations + TES
│   │   └── seeds/
│   │       ├── topic_map.py         — ручной маппинг тем на старте
│   │       └── faq_rules.py         - Seed-данные для FAQ правил
│   │
│   ├── repositories/                — Слой доступа к данным
│   │   ├── faq.py
│   │   ├── laws.py
│   │   ├── topics.py
│   │   ├── tes.py
│   │   └── faq.py
│   │
│   └── routers/                     — REST API
│       ├── laws.py                  — GET /laws/{act}/{chapter}/{section}
│       ├── topics.py                — GET /topics/, GET /topics/{key}
│       ├── tes.py                   — GET /tes/{union}
│       ├── faq.py                   — GET /faq/?topic=&union=
│       └── parse.py                 — POST /parse/{source}
│
├── bot/
│   ├── bot_main.py                  — Dispatcher, подключение роутеров
│   ├── keyboards.py                 — Reply + Inline клавиатуры
│   ├── states.py                    — FSM состояния визарда
│   └── routers/
│       ├── start.py                 — /start, выбор языка и профсоюза
│       ├── situation.py             — FSM визард: отрасль → ситуация → ответ
│       ├── laws.py                  — просмотр параграфов, пагинация
│       ├── calculator.py            — TES-калькулятор ставок
│       └── faq.py                   — FAQ по темам
│
└── migrations/
    └── versions/
```

## Слои и технологии

| Слой | Файлы                                | Технология                           |
|---|--------------------------------------|--------------------------------------|
| Parsing / статика | `finlex.py`                          | httpx + BeautifulSoup4               |
| Parsing / динамика | `tyosuojelu.py`                      | Playwright (async)                   |
| Parsing / PDF | `tes/rakennusliitto.py`              | pdfplumber                           |
| Translation | `helsinki_nlp.py`                    | Helsinki-NLP fi→en                   |
| Translation | `nllb.py`                            | NLLB-600 API                         |
| Database | `models.py`, `db_helper.py`          | SQLAlchemy 2.0 async + PostgreSQL 16 |
| Migrations | `migrations/`                        | Alembic                              |
| Application | `faq_engine.py`, `tes_calculator.py` | rule-based, без LLM                  |
| REST API | `routers/`                           | FastAPI + uvicorn                    |
| Bot | `bot/`                               | aiogram 3.x                          |
| Scheduler | `scheduler.py`                       | APScheduler                          |
| Infrastructure | `docker-compose.yml`                 | Docker Compose                       |

## Приоритеты реализации

```
Фаза 1 — база
  finlex.py          парсим TSL главы 1,2,6,7 + Vuosilomalaki + Tyoaikalaki
  models.py          Act → Chapter → Section → Paragraph
  nllb.py    перевод fi→en
  topic_map.py       10 тем вручную (dismissal, overtime, sick_leave, ...)

Фаза 2 — обогащение
  tyosuojelu.py      тематические страницы → привязка к topics
  tes/pam.py         PAM TES (торговля, HTML)
  tes/rakennusliitto.py  Rakennusliitto (PDF)
  faq_engine.py      rule-based FAQ по 15 ситуациям

Фаза 3 — калькулятор и бот
  tes_calculator.py  ставки: сверхурочные, праздники, ночные
  bot/               FSM визард + калькулятор
  scheduler.py       APScheduler, обновление каждые 24ч
```