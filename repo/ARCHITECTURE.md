vk_tg_dating_bot/   # корень локального проекта
│
├── repo/
│   ├── README.md               # быстрый старт (локально), зависимости, запуск, сценарии  
│   ├── ARCHITECTURE.md         # архитектура, слои, потоки данных, FSM, кнопки, фильтры, БД  
│   ├── WORKPLAN.md             # план работ и распределение задач для 2 разработчиков (локально)  
│  
├── .env.example                # пример переменных окружения (TG/DB), без секретов  
├── requirements.txt            # зависимости (локально)  
├── .gitignore                  # исключаем .env, data/, кэши, логи, venv и пр.  
│  
├── docker-compose.yml          # (опционально) локальный Postgres через Docker (не деплой!)  
│                               # можно удалить, если Postgres установлен системно  
│  
├── scripts/                    # скрипты для локальной БД и служебные SQL  
│   ├── init_db.sql             # создание таблиц (преподаватель/проверка без кода)  
│   ├── reset_db.sql            # снести и пересоздать таблицы (опционально)  
│   └── seed.sql                # тестовые данные (опционально)  
│  
├── data/                       # локальные данные проекта (НЕ коммитить)  
│   ├── photos/                 # скачанные фото кандидатов (JPEG/PNG)  
│   │   └── <vk_user_id>/       # по папкам на каждого кандидата  
│   ├── models/                 # ONNX-модели InsightFace (buffalo_l), НЕ коммитить  
│   ├── cache/                  # кэш ответов/временные файлы  
│   └── logs/                   # локальные логи приложения (rotating)  
│  
├── src/                        # исходный код  
│   ├── main.py                 # точка входа: запускает Telegram-бота локально  
│   │  
│   ├── core/                   # конфиг, логирование, константы, исключения  
│   │   ├── config.py           # загрузка .env, валидация конфигурации, единый доступ к настройкам  
│   │   ├── logging.py          # настройка логов (ротация, путь ./data/logs)  
│   │   ├── constants.py        # константы: лимиты, имена кнопок, VK API version  
│   │   └── exceptions.py       # VkApiError, DbError, ValidationError и т.п.  
│   │
│   ├── domain/                 # доменные модели (не завязаны на Telegram/VK/SQLAlchemy)  
│   │   ├── models.py           # Candidate, Photo, SearchFilters, UserSessionState...  
│   │   └── enums.py            # Gender, UiState, CallbackAction...  
│   │  
│   ├── infrastructure/         # интеграции (VK/DB)  
│   │   ├── vk/                 # всё взаимодействие с VK API  
│   │   │   ├── client.py       # HTTP-клиент VK (token per user, retry/backoff)  
│   │   │   ├── methods.py      # users.search, photos.get, users.get, utils.resolveScreenName...  
│   │   │   └── attachments.py  # сборка attachment: photo{owner_id}_{photo_id}  
│   │   │  
│   │   ├── db/                 # всё взаимодействие с PostgreSQL  
│   │   │   ├── session.py      # engine/sessionmaker  
│   │   │   ├── models.py       # SQLAlchemy модели таблиц  
│   │   │   └── repositories.py # репозитории CRUD  
│   │   │
│   │   └── vision/                 # обработка фото — InsightFace (ONNXRuntime, CPU)  
│   │       ├── detector.py         # SCRFD: detect_faces(image) → list[Face]  
│   │       ├── embedder.py         # ArcFace: get_embedding(image, face) → ndarray(512)  
│   │       ├── blur_check.py       # variance of Laplacian: calc_blur_score → float  
│   │       └── photo_selector.py   # оркестратор: detect → filter → blur → embed → топ-3  
│   │  
│   ├── application/                        # бизнес-логика / use-cases  
│   │   ├── services/  
│   │   │   ├── auth_service.py             # сохранить токен, протестировать VK соединение  
│   │   │   ├── filters_service.py          # “настроить фильтры” (город/пол/возраст)  
│   │   │   ├── dating_service.py           # предыдущий/следующий кандидат + показать карточку  
│   │   │   ├── favorites_service.py        # избранное: добавить/удалить/список  
│   │   │   ├── blacklist_service.py        # чёрный список: добавить/проверка  
│   │   │   └── photo_processing_service.py # фоновый воркер: скачивание + InsightFace пайплайн  
│   │   │  
│   │   └── strategies/  
│   │       ├── search_pagination.py        # обход лимита 1000 (сегментация)  
│   │       └── filters.py                  # фильтры кандидатов (seen/blacklist/валидность)  
│   │  
│   ├── presentation/               # внешний интерфейс приложения  
│   │   └── tg/                     # Telegram-бот (aiogram)  
│   │       ├── bot.py              # Bot/Dispatcher, регистрация роутеров  
│   │       ├── handlers.py         # обработчики: /start, токен, фильтры, навигация, избранное  
│   │       ├── keyboards.py        # клавиатуры согласно новой архитектуре кнопок  
│   │       ├── states.py           # FSM: ввод токена, настройка фильтров (4 вопроса)  
│   │       └── formatters.py       # формат карточки кандидата + списки  
│   │  
│   └── tests/                      # тесты (локально)  
│       ├── test_filters.py         # тесты валидации фильтров  
│       ├── test_repositories.py    # тесты репозиториев  
│       └── conftest.py             # фикстуры pytest  
│
└── docs/                           # документация (локальная)  
    ├── user_manual.md              # мануал: сценарии, кнопки, настройка фильтров, избранное/чс  
    ├── db_schema.md                # таблицы, поля, индексы, уникальности  
    └── vk_api_notes.md             # методы VK, параметры поиска, attachments, лимит 1000  
  

  
---

## ARCHITECTURE.md (целиком)

```md
# VK Dating Telegram Bot — Архитектура (локальный проект)

## 1. Назначение
Telegram-бот на Python для локального запуска, который подбирает анкеты VK для знакомств:
- Пользователь вводит VK токен (бот работает “от имени пользователя” для чтения данных).
- Бот тестирует соединение с VK перед началом работы.
- Пользователь настраивает фильтры поиска через 4 вопроса:
  1) город
  2) пол
  3) возраст от
  4) возраст до
- Фотографии кандидатов отбираются через InsightFace (ONNXRuntime, CPU):
  - SCRFD — детекция лиц, отсев фото без лица / с несколькими лицами / размытых.
  - ArcFace (512-d) — эмбеддинги для проверки, что на топ-3 фото один и тот же человек.
  - Файлы хранятся на диске (`data/photos/`), метаданные и эмбеддинги — в PostgreSQL.
- Бот показывает кандидатов карточками:
  - Имя Фамилия
  - ссылка на профиль VK
  - 3 лучшие фото (отобраны через InsightFace)
- Управление через кнопки (без лайков):
  - Предыдущий
  - Далее
  - Дополнительно → Избранное / Чёрный список / Показать избранное → Удалить из избранного

> Проект НЕ деплоится. Запуск и работа выполняются только локально.

---

## 2. Архитектурный подход
Слои:
1) Presentation (Telegram) — UI и FSM.
2) Application (Use-cases) — бизнес-логика, сценарии, фоновый воркер обработки фото.
3) Infrastructure — VK API + PostgreSQL + Vision (InsightFace).
4) Domain — модели данных, не завязанные на конкретные реализации.

Принципы:
- Telegram handlers не выполняют "тяжёлую" логику поиска и не пишут SQL.
- VK API инкапсулирован в infrastructure/vk.
- Все запросы к БД через repositories.
- Application services склеивают VK + DB и возвращают DTO для отображения.
- Обработка фото (скачивание, детекция лиц, эмбеддинги) выполняется фоновым воркером малыми пачками, опережая курсор пользователя.

---

## 3. Компоненты

### 3.1 Presentation layer (Telegram)
Папка: `src/presentation/tg/`

#### FSM состояния (states.py)
Рекомендуемые состояния:
- `WAIT_VK_TOKEN` — бот ждёт токен VK после “Старт”.
- `FILTER_CITY` — вопрос 1: город.
- `FILTER_GENDER` — вопрос 2: пол.
- `FILTER_AGE_FROM` — вопрос 3: возраст от.
- `FILTER_AGE_TO` — вопрос 4: возраст до.
- `MAIN_SCREEN` — главный экран: навигация по кандидатам.

#### Обработчики (handlers.py)
Сценарии:
- /start или кнопка “Старт” → сообщение “Введите токен vk”, переход в WAIT_VK_TOKEN.
- При вводе токена:
  - вызвать AuthService.test_vk_token(...)
  - если ok → сохранить токен, показать “Настроить фильтры поиска”.
  - если ошибка → попросить ввести токен снова.
- Кнопка “Настроить фильтры поиска” → запустить опрос 4 вопросов (FSM).
- Кнопки “Предыдущий/Далее” → DatingService.get_prev/get_next.
- “Дополнительно” → показать вложенное меню.
- “Добавить в избранное” → FavoritesService.add.
- “В чёрный список” → BlacklistService.add.
- “Показать избранное” → FavoritesService.list.
- “Удалить из избранного” → FavoritesService.remove.

#### Клавиатуры (keyboards.py)
- Стартовая клавиатура: [Старт]
- После токена: [Настроить фильтры поиска]
- Главный экран: [Предыдущий] [Далее] [Дополнительно]
- Меню “Дополнительно”: [Добавить в избранное] [В чёрный список] [Показать избранное] [Назад]
- В “Избранном” для каждого элемента: [Удалить из избранного] + (опционально) навигация по списку

---

### 3.2 Application layer (Use Cases / Services)
Папка: `src/application/services/`

#### AuthService (auth_service.py)
Задачи:
- принять токен пользователя,
- протестировать соединение с VK:
  - сделать простой запрос (например users.get),
  - убедиться что токен валиден,
- сохранить токен в БД (tg_user.vk_access_token + vk_user_id).

#### FiltersService (filters_service.py)
Задачи:
- сохранить фильтры (город/пол/возраст от/до) в БД для tg_user,
- валидировать ввод:
  - возраст — числа,
  - возраст_from <= возраст_to,
  - пол — из допустимых значений,
  - город — корректно преобразовать в VK city_id (см. VK notes).

#### DatingService (dating_service.py)
Задачи:
- получить следующего кандидата по текущим фильтрам,
- получить предыдущего кандидата по истории показов,
- исключать кандидатов:
  - уже показанных (seen),
  - из чёрного списка,
- фиксировать показ кандидата (seen + history cursor).
- формировать карточку кандидата (DTO) с 3 фото (уже отобранными через InsightFace).

#### PhotoProcessingService (photo_processing_service.py)
Фоновый воркер, обрабатывает кандидатов из `search_queue` малыми пачками (по 5):
1) Берёт следующих кандидатов со статусом `new` (исключая seen/blacklist).
2) Скачивает фото через VK photos.get (сортировка по лайкам) → сохраняет в `data/photos/`.
3) Прогоняет каждое фото через пайплайн InsightFace:
   - SCRFD: детекция лиц → `faces_count`, `det_score`, `bbox`.
   - Фильтрация: ровно 1 лицо, `det_score` выше порога, лицо не слишком мелкое.
   - Blur-check: variance of Laplacian → `blur_score`, отсев размытых.
   - ArcFace: вычисление эмбеддинга (512 float32) → `embedding`.
4) Проверка консистентности: cosine similarity между эмбеддингами топ-фото — один и тот же человек.
5) Выбор топ-3 фото (status = `selected`), остальные — `rejected` с `reject_reason`.
6) Обновление `vk_profiles.status` → `ready`.
7) Воркер поддерживает буфер ~5 готовых кандидатов впереди курсора пользователя.

#### FavoritesService / BlacklistService
- add/remove/list favorites
- add blacklist profiling (и исключение из выдачи)

---

### 3.3 Infrastructure layer

#### VK API
Папка: `src/infrastructure/vk/`
- `client.py` — отправка HTTP запросов в VK, обработка ошибок, retry/backoff.
- `methods.py` — конкретные методы:
  - users.get (проверка токена)
  - users.search (по фильтрам)
  - photos.get (получить фото с лайками)
  - database.getCities или utils.resolveScreenName (в зависимости от выбранного способа определения города)
- `attachments.py` — сборка attachment строк: photo{owner_id}_{photo_id}

Важно: VK токен хранится в БД и подставляется в вызовы по tg_user.

#### DB
Папка: `src/infrastructure/db/`
- `session.py` — engine/sessionmaker
- `models.py` — таблицы
- `repositories.py` — CRUD и запросы

#### Vision (InsightFace)
Папка: `src/infrastructure/vision/`
Стек: InsightFace через ONNXRuntime (CPU), модель buffalo_l.

- `detector.py` — инициализация SCRFD-детектора, метод `detect_faces(image) → list[Face]`.
  Каждый Face содержит: bbox, det_score, landmark.
- `embedder.py` — извлечение ArcFace эмбеддинга (512 float32) из кропа лица.
  Метод `get_embedding(image, face) → np.ndarray`.
- `blur_check.py` — оценка резкости кропа лица через variance of Laplacian.
  Метод `calc_blur_score(image, bbox) → float`.
- `photo_selector.py` — оркестратор пайплайна для одного кандидата:
  1) Для каждого фото: detect → filter (1 лицо, score, size) → blur → embed.
  2) Cosine similarity между эмбеддингами — проверка "один человек".
  3) Ранжирование accepted-фото по лайкам → топ-3 (status = `selected`).
  Метод `select_top_photos(photos: list[VkPhoto]) → list[VkPhoto]`.

---

## 4. База данных (PostgreSQL) — что и зачем хранить

| Таблица | Назначение |
|---------|-----------|
| `tg_users` | Telegram user + vk_token + vk_id + фильтры + history_cursor |
| `vk_profiles` | Данные кандидатов (имя, фамилия, ссылка, статус: new/processing/ready/error) |
| `vk_photos` | Метаданные фото, результаты детекции лиц, blur_score, эмбеддинги ArcFace, статус (raw/accepted/rejected/selected) |
| `search_queue` | Очередь кандидатов из users.search per user (с позицией) |
| `seen_profiles` | Показанные кандидаты (исключение повторов при поиске) |
| `view_history` | Упорядоченная история просмотров (для "Предыдущий/Далее") |
| `favorite_profiles` | Избранное |
| `blacklist_profiles` | Чёрный список |

Файлы фотографий (JPEG/PNG) хранятся на диске в `data/photos/`, в БД — только пути и метаданные.

Подробно: `docs/db_schema.md`

---

## 5. Потоки данных (Data Flow)

### 5.1 Старт и авторизация токеном
1) /start → “Введите токен vk”
2) Пользователь отправляет токен
3) Затем бот запрашивает VK_APP_ID → “Введите ваш vk id” и пользователь отправляет ID
4) AuthService:
   - вызывает VK users.get с этим токеном
   - если ok → сохраняет токен и vk_user_id, показывает кнопку “Настроить фильтры поиска”
   - если fail → просит повторить

### 5.2 Настройка фильтров (4 вопроса)
1) Нажатие “Настроить фильтры”
2) По очереди сохраняются:
   - город (и преобразование в city_id),
   - пол,
   - возраст от,
   - возраст до
3) После завершения сохраняем фильтры в tg_user и открываем главный экран.

### 5.3 Гибридный поиск и обработка кандидатов
Поиск разделён на два этапа для экономии памяти и мгновенного отклика:

**Этап 1 — Сбор ID (дешёвый):**
1) `users.search` по фильтрам → список VK ID + имя/фамилия.
2) Upsert в `vk_profiles` (status = `new`).
3) Запись в `search_queue` (per user, с позицией).

**Этап 2 — Фоновая обработка малыми пачками (по 5):**
1) PhotoProcessingService берёт следующих 5 кандидатов из `search_queue` (status = `new`, не в seen/blacklist).
2) Для каждого: `photos.get` → скачивание → InsightFace пайплайн → топ-3 фото.
3) `vk_profiles.status` = `ready`.
4) Воркер поддерживает буфер ~5 готовых кандидатов впереди курсора.

**Показ пользователю:**
- Далее: DatingService.get_next_candidate
  - берёт следующего `ready`-кандидата из очереди
  - запись в history + seen
  - если буфер < 5 — воркер подгружает ещё пачку
- Предыдущий: DatingService.get_prev_candidate
  - берём из локальной истории показов
  - показываем карточку без нового поиска

---

## 6. Ограничение VK users.search (1000) и обход
Стратегия сегментации по возрасту:
- дробим возрастной диапазон на интервалы,
- перебираем интервалы,
- при переполнении — дробим интервал ещё.

Реализация: `src/application/strategies/search_pagination.py`

---

## 7. Локальный запуск
1) `.env`
Переменные окружения (.env)
- `TG_BOT_TOKEN=...`
- `DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/vkbot`
- `INSIGHTFACE_MODEL=buffalo_l` — модель InsightFace (SCRFD + ArcFace)
- `PHOTO_DIR=./data/photos` — путь для скачанных фото
- `PHOTO_BATCH_SIZE=5` — размер пачки фонового воркера
- `PHOTO_BUFFER_AHEAD=5` — сколько ready-кандидатов держать впереди курсора

2) Postgres локально
3) `scripts/init_db.sql`
4) `python -m src.main`
