# VK Dating Telegram Bot (локальный проект)

## 1. Описание
Telegram-бот на Python, который подбирает людей для знакомств во ВКонтакте (vk.com) по критериям пользователя.
Проект запускается и работает только локально.

Ключевые особенности:
- При старте бот просит у пользователя VK токен: сообщение "Введите токен vk".
- Бот тестирует соединение с VK (валидирует токен).
- После успешной проверки появляется кнопка "Настроить фильтры поиска".
- Фильтры настраиваются через 4 вопроса:
  1) Укажите город для поиска
  2) Укажите пол для поиска кандидатов
  3) Укажите интересующий начальный возраст кандидатов
  4) Укажите интересующий максимальный возраст кандидатов
- Фотографии кандидатов отбираются с помощью распознавания лиц (InsightFace / ONNXRuntime, CPU) **или** по количеству лайков (если InsightFace отключён):
  - Детектор SCRFD — поиск лиц, фильтрация (ровно одно лицо, без размытия).
  - Эмбеддинги ArcFace (512-d) — проверка, что на топ-3 фото один и тот же человек.
  - Режим переключается переменной `USE_INSIGHTFACE` в `.env` (true/false).
  - Файлы (JPEG/PNG) хранятся на диске (`data/photos/`).
- После настройки фильтров доступен главный экран с навигацией по кандидатам и дополнительными действиями:
  - Предыдущий
  - Далее
  - Дополнительно → В избранное / В чёрный список / Показать избранное → Удалить из избранного / Настроить фильтры
- Кнопок лайка нет.

---

## 2. Архитектура кнопок (по ТЗ пользователя)
|- Старт
|- Настроить фильтры
|- Кнопки главного экрана
   |- Предыдущий
   |- Далее
   |- Дополнительно
      |- В избранное
      |- В черный список
      |- Назад
      |- Показать избранное
         |- Удалить из избранного
         |- Назад
      |- Настроить фильтры

Примечания:
- "Старт" — это стартовая точка диалога (/start) и стартовая кнопка/экран.
- "Настроить фильтры" открывает режим опроса (4 шага).
- "Дополнительно" — вложенное меню.

---

## 3. Основные сценарии работы

### 3.1 Старт и ввод токена
1) Пользователь нажимает "Старт" или вводит `/start`.
2) Бот отвечает: "Введите токен vk".
3) Пользователь отправляет токен текстом.
4) Затем бот запрашивает VK ID → "Введите ваш vk id" и пользователь отправляет ID.
5) Бот тестирует соединение с VK:
   - если токен валиден → "Токен принят. Соединение с VK успешно." и показывает кнопку "Настроить фильтры поиска".
   - если токен невалиден → "Ошибка токена. Повторите ввод." и снова ждёт токен.

### 3.2 Настройка фильтров
1) Пользователь нажимает "Настроить фильтры поиска".
2) Бот задаёт вопросы по очереди:
   1) "Укажите город для поиска"
   2) "Укажите пол для поиска кандидатов"
   3) "Укажите интересующий начальный возраст кандидатов"
   4) "Укажите интересующий максимальный возраст кандидатов"
3) После ввода всех 4 параметров:
   - бот сохраняет фильтры в хранилище,
   - показывает главный экран (кнопки навигации "Предыдущий/Далее/Дополнительно").

### 3.3 Просмотр кандидатов
- "Далее" → показать следующего кандидата.
- "Предыдущий" → показать предыдущего кандидата (по локальной истории показов).
Карточка кандидата содержит:
- Имя Фамилия
- Ссылка на профиль VK
- 3 лучшие фотографии (отобраны через InsightFace или по лайкам)

### 3.4 Обработка фотографий
Фотографии обрабатываются с предзагрузкой на 5 кандидатов вперёд, опережая курсор пользователя:
1) Скачивание фото кандидата с VK (photos.get, сортировка по лайкам, параллельное скачивание).
2) Если `USE_INSIGHTFACE=true` и скачано >= 3 фото:
   - Детекция лиц (SCRFD) — отсев фото без лица или с несколькими лицами.
   - Оценка резкости (variance of Laplacian) — отсев размытых фото.
   - Вычисление эмбеддингов (ArcFace 512-d) — проверка, что на фото один и тот же человек.
   - Выбор топ-3 фото (status = selected) для показа в карточке.
   - InsightFace выполняется в thread pool executor (не блокирует event loop).
3) Если `USE_INSIGHTFACE=false` или фото < 3:
   - Берутся топ-3 фото по количеству лайков.
4) Файлы сохраняются в `data/photos/<vk_user_id>/`.
5) При старте бота детектор InsightFace прогревается (warm-up), чтобы первый запрос не ждал загрузки модели.

### 3.5 Дополнительные действия
- "В избранное" → сохраняет текущего кандидата в избранное.
- "В чёрный список" → добавляет текущего кандидата в чёрный список, чтобы больше не показывался.
- "Показать избранное" → выводит список избранных; для каждого доступно "Удалить из избранного".

---

## 4. Хранение состояния

### Текущая реализация (InMemoryUserRepo — заглушка)
Сейчас все данные хранятся в оперативной памяти (`src/infrastructure/db/repositories.py`).
При перезапуске бота данные сбрасываются. Это MVP-заглушка для быстрой разработки бота.

Данные в памяти:
- `_users: Dict[int, UserDTO]` — пользователи Telegram (токен VK, фильтры, курсор)
- `_favorites: Dict[int, set[int]]` — избранное (tg_user_id → set vk_id)
- `_black_list: Dict[int, set[int]]` — чёрный список
- `_queue: Dict[int, list[int]]` — очередь кандидатов из users.search
- `_profiles: Dict[int, ProfileDTO]` — профили кандидатов VK
- `_photos: Dict[int, list[PhotoDTO]]` — фото кандидатов VK (кэшируются после обработки)

### Целевая реализация (PostgreSQL)
Для production нужно реализовать `UserRepo` Protocol с PostgreSQL (см. раздел 8 "Задание для SQL-специалиста").

Файлы фотографий (JPEG/PNG) хранятся на диске в `data/photos/`, в БД — только пути и метаданные.

---

## 5. Ограничение VK users.search (1000 результатов)
VK ограничивает выдачу поиска 1000 анкет.
Планируется обход через стратегию сегментации по возрасту:
- дробим возрастной диапазон на интервалы,
- перебираем интервалы, пока не найдём подходящих кандидатов, которых нет в seen/blacklist,
- при переполнении сегмента — дробим интервал ещё.

> **Статус:** пока не реализовано. Текущий поиск возвращает до 50 кандидатов за один запрос.

---

## 6. Требования
- Python 3.11+
- Telegram Bot Token (в `.env`)
- VK user token + VK ID (пользователь вводит в чат бота)
- VK приложение (APP_ID + APP_URL для получения токена пользователем)

Опционально (для режима распознавания лиц, `USE_INSIGHTFACE=true`):
- InsightFace + ONNXRuntime (CPU) — модель buffalo_l (SCRFD + ArcFace, ~280 МБ)
- OpenCV (cv2) — предобработка фото, оценка резкости
- NumPy — работа с массивами и эмбеддингами

---

## 7. Установка и запуск

### 7.1 Базовая установка (без распознавания лиц)
```bash
# Создать виртуальное окружение
python -m venv venv

# Активировать (Windows):
venv\Scripts\activate
# Активировать (Linux/macOS):
source venv/bin/activate

# Установить зависимости
pip install -r requirements.txt
```

Создать файл `.env` по образцу `.env.example`:
```
TG_TOKEN=ваш_токен_телеграм_бота
VK_API_VERSION=5.131
USE_INSIGHTFACE=false
```

Запуск:
```bash
python -m src.main
```

### 7.2 Установка с распознаванием лиц (InsightFace)

Установить дополнительные пакеты:
```bash
pip install numpy opencv-python onnxruntime insightface
```

**Windows без Visual Studio Build Tools:**
InsightFace требует компиляции C-расширений (mesh_core_cython).
Если Visual Studio Build Tools не установлены, можно установить InsightFace без Cython-расширений:
1) Скачать tarball: `pip download insightface --no-binary insightface --no-deps -d ./tmp_pkg`
2) Распаковать архив
3) В `setup.py` удалить или закомментировать секцию `ext_modules` (Cython расширения)
4) Установить из изменённого каталога: `pip install ./tmp_pkg/insightface-X.X.X/ --no-deps --no-build-isolation`
5) Пропатчить `venv/.../insightface/thirdparty/face3d/mesh/__init__.py` — обернуть import mesh_core_cython в try/except
6) Пропатчить `venv/.../insightface/app/__init__.py` — обернуть `from .mask_renderer import *` в try/except

В `.env` установить:
```
USE_INSIGHTFACE=true
INSIGHTFACE_MODEL=buffalo_l
```

При первом запуске модель buffalo_l (~280 МБ) будет скачана автоматически.

Запуск:
```bash
python -m src.main
```

---

## 8. Задание для SQL-специалиста (реализация PostgreSQL)

### Описание задачи
Текущая реализация хранения данных — `InMemoryUserRepo` (заглушка в памяти).
Для production необходимо создать реализацию интерфейса `UserRepo` (Protocol) с использованием PostgreSQL.

Интерфейс определён в `src/infrastructure/db/repositories.py` и содержит все необходимые методы.
Новая реализация должна быть **drop-in заменой** `InMemoryUserRepo` — реализовать все те же методы с теми же сигнатурами.

### DTO (Data Transfer Objects)
Определены в `src/infrastructure/db/repositories.py`:

| DTO | Поля | Описание |
|-----|------|----------|
| `UserDTO` | `tg_user_id`, `vk_access_token`, `vk_user_id`, `filter_city_name`, `filter_city_id`, `filter_gender`, `filter_age_from`, `filter_age_to`, `history_cursor` | Пользователь Telegram |
| `ProfileDTO` | `vk_user_id`, `first_name`, `last_name`, `domain` | Профиль кандидата VK |
| `PhotoDTO` | `photo_id`, `owner_id`, `url`, `likes_count`, `local_path`, `status` | Фото кандидата VK |

### Методы UserRepo Protocol (для реализации SQL-запросов)

#### Пользователи (tg_users)

| Метод | Сигнатура | SQL-логика |
|-------|-----------|------------|
| `get_or_create_user` | `(tg_user_id: int) → UserDTO` | `SELECT ... WHERE tg_user_id = ?`, если нет — `INSERT` и вернуть |
| `upsert_user_token_and_vk_id` | `(tg_user_id, vk_access_token, vk_user_id) → None` | `INSERT ... ON CONFLICT UPDATE SET vk_access_token=?, vk_user_id=?` |
| `update_filters` | `(tg_user_id, city, gender, age_from, age_to, city_id=None) → None` | `UPDATE tg_users SET filter_city_name=?, filter_city_id=?, filter_gender=?, filter_age_from=?, filter_age_to=?, history_cursor=0 WHERE tg_user_id=?`. Также удалить очередь кандидатов при смене фильтров |

#### Курсор навигации

| Метод | Сигнатура | SQL-логика |
|-------|-----------|------------|
| `get_cursor` | `(tg_user_id) → int` | `SELECT history_cursor FROM tg_users WHERE tg_user_id=?`, дефолт 0 |
| `set_cursor` | `(tg_user_id, cursor) → None` | `UPDATE tg_users SET history_cursor=? WHERE tg_user_id=?` |

#### Избранное и чёрный список

| Метод | Сигнатура | SQL-логика |
|-------|-----------|------------|
| `add_favorite` | `(tg_user_id, vk_profile_id) → None` | `INSERT INTO favorites (tg_user_id, vk_profile_id) ON CONFLICT DO NOTHING` |
| `remove_favorite` | `(tg_user_id, vk_profile_id) → None` | `DELETE FROM favorites WHERE tg_user_id=? AND vk_profile_id=?` |
| `list_favorites` | `(tg_user_id) → list[int]` | `SELECT vk_profile_id FROM favorites WHERE tg_user_id=? ORDER BY vk_profile_id` |
| `add_blacklist` | `(tg_user_id, vk_profile_id) → None` | `INSERT INTO blacklist (tg_user_id, vk_profile_id) ON CONFLICT DO NOTHING`. Также удалить из очереди и скорректировать курсор |

#### Очередь кандидатов (search_queue)

| Метод | Сигнатура | SQL-логика |
|-------|-----------|------------|
| `set_queue` | `(tg_user_id, vk_ids: list[int]) → None` | `DELETE FROM search_queue WHERE tg_user_id=?` + `INSERT` всех vk_ids с позициями + сбросить cursor=0 |
| `get_queue` | `(tg_user_id) → list[int]` | `SELECT vk_id FROM search_queue WHERE tg_user_id=? ORDER BY position` |
| `get_current_vk_id` | `(tg_user_id) → int｜None` | Получить `history_cursor`, затем `SELECT vk_id FROM search_queue WHERE tg_user_id=? AND position=?` |
| `move_next` | `(tg_user_id) → int｜None` | Инкремент cursor (если не конец очереди), вернуть vk_id на новой позиции |
| `move_prev` | `(tg_user_id) → int｜None` | Декремент cursor (если не начало), вернуть vk_id. None если cursor=0 |

#### Профили кандидатов VK

| Метод | Сигнатура | SQL-логика |
|-------|-----------|------------|
| `upsert_profile` | `(profile: ProfileDTO) → None` | `INSERT INTO vk_profiles (...) ON CONFLICT (vk_user_id) DO UPDATE SET ...` |
| `get_profile` | `(vk_user_id) → ProfileDTO｜None` | `SELECT ... FROM vk_profiles WHERE vk_user_id=?` |

#### Фото кандидатов VK

| Метод | Сигнатура | SQL-логика |
|-------|-----------|------------|
| `set_photos` | `(vk_user_id, photos: list[PhotoDTO]) → None` | `DELETE FROM vk_photos WHERE owner_id=?` + `INSERT` всех фото |
| `get_photos` | `(vk_user_id) → list[PhotoDTO]` | `SELECT ... FROM vk_photos WHERE owner_id=?` |

### Рекомендуемая схема таблиц PostgreSQL

```sql
CREATE TABLE tg_users (
    tg_user_id       BIGINT PRIMARY KEY,
    vk_access_token  TEXT,
    vk_user_id       BIGINT,
    filter_city_name TEXT,
    filter_city_id   INTEGER,
    filter_gender    INTEGER,
    filter_age_from  INTEGER,
    filter_age_to    INTEGER,
    history_cursor   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE vk_profiles (
    vk_user_id  BIGINT PRIMARY KEY,
    first_name  TEXT NOT NULL DEFAULT '',
    last_name   TEXT NOT NULL DEFAULT '',
    domain      TEXT NOT NULL DEFAULT ''
);

CREATE TABLE vk_photos (
    photo_id    BIGINT,
    owner_id    BIGINT NOT NULL,
    url         TEXT NOT NULL,
    likes_count INTEGER NOT NULL DEFAULT 0,
    local_path  TEXT,
    status      TEXT NOT NULL DEFAULT 'raw',
    PRIMARY KEY (photo_id, owner_id)
);

CREATE TABLE search_queue (
    tg_user_id BIGINT NOT NULL,
    position   INTEGER NOT NULL,
    vk_id      BIGINT NOT NULL,
    PRIMARY KEY (tg_user_id, position)
);

CREATE TABLE favorites (
    tg_user_id    BIGINT NOT NULL,
    vk_profile_id BIGINT NOT NULL,
    PRIMARY KEY (tg_user_id, vk_profile_id)
);

CREATE TABLE blacklist (
    tg_user_id    BIGINT NOT NULL,
    vk_profile_id BIGINT NOT NULL,
    PRIMARY KEY (tg_user_id, vk_profile_id)
);
```

### Как подключить новую реализацию
1) Создать класс `PostgresUserRepo` в `src/infrastructure/db/` (реализует все методы `UserRepo` Protocol).
2) В `src/presentation/tg/bot.py` заменить `InMemoryUserRepo()` на `PostgresUserRepo(session)`.
3) Добавить `DATABASE_URL` в `.env`.

Пример подключения (в `bot.py`):
```python
# было:
user_repo = InMemoryUserRepo()
# стало:
user_repo = PostgresUserRepo(session=async_session)
```
