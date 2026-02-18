# VK Dating Telegram Bot — Архитектура (локальный проект)

## 1. Назначение
Telegram-бот на Python для локального запуска, который подбирает анкеты VK для знакомств:
- Пользователь вводит VK токен (бот работает "от имени пользователя" для чтения данных).
- Бот тестирует соединение с VK перед началом работы.
- Пользователь настраивает фильтры поиска через 4 вопроса:
  1) город
  2) пол
  3) возраст от
  4) возраст до
- Фотографии кандидатов отбираются через InsightFace (ONNXRuntime, CPU) или по лайкам:
  - Переключается переменной `USE_INSIGHTFACE` в `.env` (true/false).
  - SCRFD — детекция лиц, отсев фото без лица / с несколькими лицами / размытых.
  - ArcFace (512-d) — эмбеддинги для проверки, что на топ-3 фото один и тот же человек.
  - Файлы хранятся на диске (`data/photos/`).
- Бот показывает кандидатов карточками:
  - Имя Фамилия
  - ссылка на профиль VK
  - 3 лучшие фото (отобраны через InsightFace или по лайкам)
- Управление через кнопки (без лайков):
  - Предыдущий
  - Далее
  - Дополнительно
    - В избранное
    - В черный список
    - Назад
    - Показать избранное
      - Удалить из избранного
      - Назад
    - Настроить фильтры

> Проект НЕ деплоится. Запуск и работа выполняются только локально.

---

## 2. Архитектурный подход
Слои:
1) **Presentation** (Telegram) — UI и FSM.
2) **Application** (Use-cases) — бизнес-логика, сценарии, обработка фото.
3) **Infrastructure** — VK API + хранилище данных + Vision (InsightFace).
4) **Core** — конфигурация, логирование, константы, исключения.

Принципы:
- Telegram handlers не выполняют "тяжёлую" логику поиска и не работают напрямую с хранилищем.
- VK API инкапсулирован в infrastructure/vk.
- Все запросы к данным через repositories (Protocol `UserRepo`).
- Application services склеивают VK + repo и возвращают DTO для отображения.
- Обработка фото (скачивание, детекция лиц, эмбеддинги) выполняется с предзагрузкой, опережая курсор пользователя.
- CPU-тяжёлые операции InsightFace выполняются в thread pool executor (не блокируют event loop).

---

## 3. Структура проекта

```
vk_tg_dating_bot/                  # корень проекта
│
├── repo/
│   ├── README.md                  # описание, сценарии, установка, задание для SQL-специалиста
│   ├── ARCHITECTURE.md            # архитектура, слои, потоки данных, FSM
│   └── WORKPLAN.md                # план работ для 2 разработчиков
│
├── .env.example                   # пример переменных окружения (без секретов)
├── requirements.txt               # зависимости
├── .gitignore                     # исключаем .env, data/, кэши, venv и пр.
│
├── data/                          # локальные данные (НЕ коммитить)
│   ├── photos/                    # скачанные фото кандидатов (JPEG)
│   │   └── <vk_user_id>/         # по папкам на каждого кандидата
│   └── logs/                      # логи приложения (rotating)
│
├── src/                           # исходный код
│   ├── main.py                    # точка входа: python -m src.main
│   │
│   ├── core/                      # конфиг, логирование, константы, исключения
│   │   ├── config.py              # загрузка .env, USE_INSIGHTFACE, пути
│   │   ├── log_setup.py           # настройка логов (ротация, путь data/logs)
│   │   ├── constants.py           # константы: имена кнопок, callback-данные
│   │   ├── exceptions.py          # VkApiError
│   │   └── init_data_dirs.py      # создание data/photos, data/logs при старте
│   │
│   ├── infrastructure/            # интеграции (VK / хранилище / распознавание)
│   │   ├── vk/                    # всё взаимодействие с VK API
│   │   │   ├── client.py          # HTTP-клиент VK (aiohttp, retry/backoff)
│   │   │   ├── methods.py         # users.get, users.search, photos.get, database.getCities
│   │   │   └── attachments.py     # сборка attachment: photo{owner_id}_{photo_id}
│   │   │
│   │   ├── db/                    # хранение данных
│   │   │   └── repositories.py    # Protocol UserRepo + InMemoryUserRepo (заглушка)
│   │   │
│   │   └── vision/                # обработка фото — InsightFace (ONNXRuntime, CPU)
│   │       ├── detector.py        # FaceDetector: SCRFD детекция лиц
│   │       ├── embedder.py        # ArcFace: get_embedding → ndarray(512), cosine_similarity
│   │       ├── blur_check.py      # calc_blur_score (variance of Laplacian)
│   │       └── photo_selector.py  # select_top_photos: detect → filter → blur → embed → топ-3
│   │
│   ├── application/               # бизнес-логика / use-cases
│   │   └── services/
│   │       ├── auth_service.py            # авторизация: проверка токена VK, сохранение
│   │       ├── filters_service.py         # валидация фильтров (город/пол/возраст)
│   │       ├── dating_service.py          # навигация: next/prev кандидат, ensure_queue, preload_ahead
│   │       ├── favorites_service.py       # избранное: добавить/удалить/список
│   │       ├── blacklist_service.py       # чёрный список: добавить
│   │       └── photo_processing_service.py # скачивание фото + InsightFace пайплайн
│   │
│   └── presentation/              # внешний интерфейс
│       └── tg/                    # Telegram-бот (aiogram)
│           ├── bot.py             # Bot/Dispatcher, сборка зависимостей, запуск
│           ├── handlers.py        # обработчики: /start, токен, фильтры, навигация, избранное
│           ├── keyboards.py       # клавиатуры (reply + inline)
│           ├── states.py          # FSM: AuthState, FilterState, MenuState
│           └── formatters.py      # формат карточки кандидата
│
└── venv/                          # виртуальное окружение (НЕ коммитить)
```

---

## 4. Компоненты

### 4.1 Presentation layer (Telegram)
Папка: `src/presentation/tg/`

#### FSM состояния (states.py)
- `AuthState.WAIT_VK_TOKEN` — бот ждёт токен VK после "Старт".
- `AuthState.WAIT_VK_ID` — бот ждёт VK ID пользователя.
- `FilterState.CITY` — вопрос 1: город.
- `FilterState.GENDER` — вопрос 2: пол.
- `FilterState.AGE_FROM` — вопрос 3: возраст от.
- `FilterState.AGE_TO` — вопрос 4: возраст до.
- `MenuState.MAIN` — главный экран: навигация по кандидатам.
- `MenuState.MORE` — вложенное меню "Дополнительно".
- `MenuState.FAVORITES` — просмотр избранного.

#### Обработчики (handlers.py)
- `/start` → приветствие + "Введите токен vk", переход в WAIT_VK_TOKEN.
- Ввод токена → ввод VK ID → AuthService.authorize → "Настроить фильтры".
- "Настроить фильтры" → 4 вопроса (FSM).
- "Далее" → DatingService.next_candidate + show_candidate_card + preload_ahead.
- "Предыдущий" → DatingService.prev_candidate.
- "Дополнительно" → вложенное меню.
- "В избранное" / "В чёрный список" → user_repo.add_favorite / add_blacklist.
- "Показать избранное" → inline-кнопки с VK ID.

При загрузке фото показывается сообщение "Ищу фото кандидата..." (удаляется после загрузки).

#### Клавиатуры (keyboards.py)
- Стартовая: [Старт]
- После авторизации: [Настроить фильтры поиска]
- Главный экран: [Предыдущий] [Далее] [Дополнительно]
- "Дополнительно": [В избранное] [В чёрный список] [Показать избранное] [Настроить фильтры] [Назад]
- "Показать избранное": inline-кнопки с VK ID + [Назад]

---

### 4.2 Application layer (Services)
Папка: `src/application/services/`

#### AuthService (auth_service.py)
- Проверка токена VK через `users.get` (без user_ids → возвращает владельца токена).
- Сверка введённого VK ID с реальным владельцем токена.
- Сохранение токена + vk_user_id через `user_repo.upsert_user_token_and_vk_id`.

#### DatingService (dating_service.py)
- `resolve_city_id(access_token, city_name)` — резолвит город в city_id через VK database.getCities.
- `ensure_queue(tg_user_id)` — если очередь пуста, делает users.search и сохраняет профили + очередь.
- `next_candidate(tg_user_id)` / `prev_candidate(tg_user_id)` — навигация по очереди.
- `get_candidate_card(tg_user_id)` — возвращает (ProfileDTO, [PhotoDTO]) текущего кандидата.
- `preload_ahead(tg_user_id)` — предзагрузка фото для 5 кандидатов впереди курсора (фоново).

#### PhotoProcessingService (photo_processing_service.py)
Полный пайплайн обработки фото кандидата:
1) `photos.get` из VK → список фото с лайками.
2) Сортировка по лайкам, параллельное скачивание top-10 на диск (asyncio.gather + aiohttp.ClientSession).
3) Если `USE_INSIGHTFACE=true` и >= 3 фото:
   - InsightFace пайплайн в thread pool executor:
     detect → filter (1 лицо, score, size) → blur → embed → cosine similarity → top-3.
4) Если InsightFace отключён или < 3 фото — fallback по лайкам.
5) Сохранение результата в repo.

Оптимизации:
- `warm_up_detector()` — прогрев InsightFace детектора при старте (не блокирует первый запрос).
- Параллельное скачивание фото через `asyncio.gather`.
- InsightFace в `run_in_executor` (не блокирует event loop aiogram).

#### FavoritesService / BlacklistService
- add/remove/list favorites.
- add blacklist (и исключение из очереди).

---

### 4.3 Infrastructure layer

#### VK API
Папка: `src/infrastructure/vk/`
- `client.py` — HTTP-клиент (aiohttp), отправка запросов в VK, обработка ошибок VkApiError.
- `methods.py` — конкретные методы VK:
  - `users_get_me` — users.get без user_ids (проверка токена + получение vk_user_id)
  - `users_search` — поиск кандидатов по фильтрам (city_id, sex, age_from, age_to)
  - `photos_get` — получить фото пользователя (album_id=profile, extended=1 для лайков)
  - `database_get_cities` — резолвит название города в city_id
- `attachments.py` — сборка attachment строк: `photo{owner_id}_{photo_id}`

VK токен хранится в repo и подставляется в вызовы per user.

#### Хранение данных (DB)
Папка: `src/infrastructure/db/`
- `repositories.py` — содержит:
  - **DTO**: `UserDTO`, `ProfileDTO`, `PhotoDTO`
  - **Protocol** `UserRepo` — интерфейс с 18 async-методами (описание в README раздел 8)
  - **InMemoryUserRepo** — текущая реализация (заглушка в памяти)

Для production: создать `PostgresUserRepo` реализующий тот же Protocol.

#### Vision (InsightFace)
Папка: `src/infrastructure/vision/`
Стек: InsightFace через ONNXRuntime (CPU), модель buffalo_l (~280 МБ).
Импортируется условно: только если `USE_INSIGHTFACE=true` в конфиге.

- `detector.py` — класс `FaceDetector`, инициализирует SCRFD (buffalo_l).
  Метод `detect(image_path) → list[dict]` — детекция лиц, возвращает bbox, det_score, embedding.
- `embedder.py` — `get_embedding(face) → np.ndarray(512)` и `cosine_similarity(emb1, emb2) → float`.
- `blur_check.py` — `calc_blur_score(image, bbox) → float` через variance of Laplacian.
- `photo_selector.py` — оркестратор `select_top_photos(detector, photos, top_n)`:
  1) Для каждого фото: detect → filter (1 лицо, score >= порог, size >= порог) → blur → embed.
  2) Cosine similarity между эмбеддингами — группировка "один человек".
  3) Ранжирование → top-N (status = `selected`).

---

## 5. Потоки данных (Data Flow)

### 5.1 Старт и авторизация
1) `/start` → "Введите токен vk"
2) Пользователь отправляет токен
3) "Введите ваш vk id" → пользователь отправляет ID
4) AuthService:
   - вызывает VK `users.get` с токеном
   - сверяет vk_id владельца с введённым
   - если ok → сохраняет токен и vk_user_id, показывает "Настроить фильтры"
   - если fail → просит повторить

### 5.2 Настройка фильтров (4 вопроса)
1) Нажатие "Настроить фильтры"
2) По очереди: город → пол → возраст от → возраст до
3) Сохранение фильтров → сброс очереди и курсора → главный экран

### 5.3 Поиск и обработка кандидатов
1) Нажатие "Далее" → `DatingService.next_candidate`
2) Если очередь пуста → `ensure_queue`:
   - `database.getCities` (резолв города в city_id)
   - `users.search` по фильтрам → список VK ID + имя/фамилия
   - Сохранение профилей и очереди в repo
3) Сдвиг курсора → показ карточки кандидата
4) Если фото не загружены → `PhotoProcessingService.fetch_and_save_photos`:
   - `photos.get` → скачивание → (опционально) InsightFace → сохранение
   - Пока фото загружаются, пользователь видит "Ищу фото кандидата..."
5) `preload_ahead` — фоновая предзагрузка фото для 5 следующих кандидатов

### 5.4 Навигация
- **Далее** → move_next + показ карточки + preload_ahead
- **Предыдущий** → move_prev + показ карточки (фото уже в кэше)

---

## 6. Конфигурация (.env)
Пример: `.env.example`

| Переменная | Описание | Пример |
|-----------|----------|--------|
| `TG_TOKEN` | Токен Telegram бота | `123456:ABC-DEF...` |
| `VK_API_VERSION` | Версия VK API | `5.131` |
| `USE_INSIGHTFACE` | Распознавание лиц (true/false) | `true` |
| `INSIGHTFACE_MODEL` | Модель InsightFace | `buffalo_l` |
| `PHOTO_DIR` | Путь для скачанных фото | `./data/photos` |

---

## 7. Локальный запуск
1) Скопировать `.env.example` → `.env`, заполнить токены
2) `pip install -r requirements.txt`
3) `python -m src.main`

При `USE_INSIGHTFACE=true`:
- Первый запуск: модель buffalo_l скачивается автоматически (~280 МБ)
- Детектор прогревается при старте (лог "FaceDetector прогрет и готов к работе")
