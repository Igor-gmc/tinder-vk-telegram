vk_tg_dating_bot/                                # корень локального проекта
│
├── repo/
│   ├── README.md               # быстрый старт (локально), зависимости, запуск, сценарии
│   ├── ARCHITECTURE.md         # архитектура, слои, потоки данных, FSM, кнопки, фильтры, БД
│   ├── WORKPLAN.md             # план работ и распределение задач для 2 разработчиков (локально)
│
├── .env.example                                 # пример переменных окружения (TG/DB), без секретов
├── requirements.txt                             # зависимости (локально)
├── .gitignore                                   # исключаем .env, data/, кэши, логи, venv и пр.
│
├── docker-compose.yml                            # (опционально) локальный Postgres через Docker (не деплой!)
│                                                 # можно удалить, если Postgres установлен системно
│
├── scripts/                                      # скрипты для локальной БД и служебные SQL
│   ├── init_db.sql                               # создание таблиц (преподаватель/проверка без кода)
│   ├── reset_db.sql                              # снести и пересоздать таблицы (опционально)
│   └── seed.sql                                  # тестовые данные (опционально)
│
├── data/                                         # локальные данные проекта (НЕ коммитить)
│   ├── photos/                                   # локально сохранённые фото для проверок (если качаешь)
│   ├── cache/                                    # кэш ответов/временные файлы
│   └── logs/                                     # локальные логи приложения (rotating)
│
├── src/                                          # исходный код
│   ├── main.py                                   # точка входа: запускает Telegram-бота локально
│   │
│   ├── core/                                     # конфиг, логирование, константы, исключения
│   │   ├── config.py                              # загрузка .env, валидация конфигурации, единый доступ к настройкам
│   │   ├── logging.py                             # настройка логов (ротация, путь ./data/logs)
│   │   ├── constants.py                           # константы: лимиты, имена кнопок, VK API version
│   │   └── exceptions.py                          # VkApiError, DbError, ValidationError и т.п.
│   │
│   ├── domain/                                   # доменные модели (не завязаны на Telegram/VK/SQLAlchemy)
│   │   ├── models.py                              # Candidate, Photo, SearchFilters, UserSessionState...
│   │   └── enums.py                               # Gender, UiState, CallbackAction...
│   │
│   ├── infrastructure/                            # интеграции (VK/DB)
│   │   ├── vk/                                    # всё взаимодействие с VK API
│   │   │   ├── client.py                          # HTTP-клиент VK (token per user, retry/backoff)
│   │   │   ├── methods.py                         # users.search, photos.get, users.get, utils.resolveScreenName...
│   │   │   └── attachments.py                     # сборка attachment: photo{owner_id}_{photo_id}
│   │   │
│   │   ├── db/                                    # всё взаимодействие с PostgreSQL
│   │   │   ├── session.py                         # engine/sessionmaker
│   │   │   ├── models.py                          # SQLAlchemy модели таблиц
│   │   │   └── repositories.py                    # репозитории CRUD
│   │   │
│   │   └── vision/                                # (опционально) локальная обработка фото
│   │       ├── blur_check.py                      # blur-check на CPU (если используешь)
│   │       ├── face_check.py                      # “одно лицо/много лиц” (если используешь)
│   │       └── photo_selector.py                  # выбор топ-3 фото (если используешь)
│   │
│   ├── application/                               # бизнес-логика / use-cases
│   │   ├── services/
│   │   │   ├── auth_service.py                    # сохранить токен, протестировать VK соединение
│   │   │   ├── filters_service.py                 # “настроить фильтры” (город/пол/возраст)
│   │   │   ├── dating_service.py                  # предыдущий/следующий кандидат + показать карточку
│   │   │   ├── favorites_service.py               # избранное: добавить/удалить/список
│   │   │   └── blacklist_service.py               # чёрный список: добавить/проверка
│   │   │
│   │   └── strategies/
│   │       ├── search_pagination.py               # обход лимита 1000 (сегментация)
│   │       └── filters.py                         # фильтры кандидатов (seen/blacklist/валидность)
│   │
│   ├── presentation/                              # внешний интерфейс приложения
│   │   └── tg/                                    # Telegram-бот (aiogram)
│   │       ├── bot.py                             # Bot/Dispatcher, регистрация роутеров
│   │       ├── handlers.py                        # обработчики: /start, токен, фильтры, навигация, избранное
│   │       ├── keyboards.py                       # клавиатуры согласно новой архитектуре кнопок
│   │       ├── states.py                          # FSM: ввод токена, настройка фильтров (4 вопроса)
│   │       └── formatters.py                      # формат карточки кандидата + списки
│   │
│   └── tests/                                     # тесты (локально)
│       ├── test_filters.py                        # тесты валидации фильтров
│       ├── test_repositories.py                   # тесты репозиториев
│       └── conftest.py                            # фикстуры pytest
│
└── docs/                                          # документация (локальная)
    ├── user_manual.md                             # мануал: сценарии, кнопки, настройка фильтров, избранное/чс
    ├── db_schema.md                               # таблицы, поля, индексы, уникальности
    └── vk_api_notes.md                            # методы VK, параметры поиска, attachments, лимит 1000



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
- Бот показывает кандидатов карточками:
  - Имя Фамилия
  - ссылка на профиль VK
  - 3 фото attachments
- Управление через кнопки (без лайков):
  - Предыдущий
  - Далее
  - Дополнительно → Избранное / Чёрный список / Показать избранное → Удалить из избранного

> Проект НЕ деплоится. Запуск и работа выполняются только локально.

---

## 2. Архитектурный подход
Слои:
1) Presentation (Telegram) — UI и FSM.
2) Application (Use-cases) — бизнес-логика и сценарии.
3) Infrastructure — VK API + PostgreSQL + (опционально) vision.
4) Domain — модели данных, не завязанные на конкретные реализации.

Принципы:
- Telegram handlers не выполняют “тяжёлую” логику поиска и не пишут SQL.
- VK API инкапсулирован в infrastructure/vk.
- Все запросы к БД через repositories.
- Application services склеивают VK + DB и возвращают DTO для отображения.

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
- формировать карточку кандидата (DTO) с 3 фото attachments.

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

#### Vision (опционально)
Папка: `src/infrastructure/vision/`
Если ты используешь правила “одно лицо / blur-check / один и тот же человек”, то:
- фото прогоняются через photo_selector.
Если решишь упростить, можно оставить только сортировку по лайкам.

---

## 4. База данных (PostgreSQL) — что и зачем хранить
Нужно хранить:
- tg_user (Telegram user + vk_token + vk_id+ фильтры)
- seen_profile (кого показывали)
- favorites (избранное)
- blacklist (чёрный список)
- history_cursor (позиция для “Предыдущий/Далее”)

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

### 5.3 Далее / Предыдущий
- Далее: DatingService.get_next_candidate
  - поиск по сегментам (обход 1000)
  - исключение seen/blacklist
  - выбор фото
  - запись в history + seen
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

2) Postgres локально
3) `scripts/init_db.sql`
4) `python -m src.main`
