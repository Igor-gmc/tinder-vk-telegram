# План работ VK Dating Telegram Bot (локальный запуск, 2 разработчика)

## Входные требования (обновлённые)
1) Кнопка “Старт”: при старте бот показывает сообщение “Введите токен vk”.
2) Потом "Введите ваш VK_ID"
3) Бот тестирует соединение (валидирует токен).
4) После успешной проверки доступна кнопка “Настроить фильтры поиска”.
5) После нажатия бот задаёт 4 вопроса:
   1) Укажите город для поиска
   2) Укажите пол для поиска кандидатов
   3) Укажите интересующий начальный возраст кандидатов
   4) Укажите интересующий максимальный возраст кандидатов
6) Главный экран:
   - Предыдущий
   - Далее
   - Дополнительно → Добавить в избранное / В чёрный список / Показать избранное → Удалить из избранного / Настроить фильтры
7) Кнопки лайк отсутствуют.

---

## Участники
- Участник A — VK API + Telegram Bot + обработка фото (InsightFace) + финальная сборка проекта
- Участник B — БД (PostgreSQL/ORM) + интеграция bot↔db + документация

---

## Этап 1: Подготовка проекта

### Участник A
1) Создать репозиторий GitHub и добавить Участника B (Admin).
2) Создать каркас проекта:
   - `src/`, `scripts/`, `docs/`, `data/`
3) Добавить базовые файлы:
   - `.env.example`
   - `requirements.txt`
   - `.gitignore`
   - `README.md` (локальный запуск)
4) Подготовить структуру Telegram UI:
   - клавиатуры согласно архитектуре кнопок
   - FSM-стейты (WAIT_VK_TOKEN + 4 фильтра + MAIN_SCREEN)

Артефакты:
- Репозиторий + доступы
- Каркас + первичная структура UI

### Участник B
1) Спроектировать БД с учётом новых требований:
   - хранение vk_token и vk_id per tg_user
   - хранение фильтров per tg_user
   - история показов для "Предыдущий/Далее"
   - favorites/blacklist/seen
   - `vk_profiles` — центральная таблица кандидатов (статус обработки)
   - `vk_photos` — метаданные фото, результаты InsightFace, эмбеддинги
   - `search_queue` — очередь кандидатов per user
2) Подготовить `scripts/init_db.sql` (создание таблиц).
3) Описать таблицы в `docs/db_schema.md`.

Артефакты:
- SQL скрипт
- Документация по БД

---

## Этап 2: Реализация модулей

### Участник A — VK интеграция, токен-тест и обработка фото
1) VK client + методы:
   - users.get (проверка токена)
   - users.search
   - photos.get
   - city resolve (получение city_id по названию)
2) Реализовать AuthService.test_vk_token:
   - проверить токен с vk_id
   - вернуть vk_user_id
3) Реализовать модуль Vision (InsightFace):
   - `detector.py` — SCRFD: детекция лиц, bbox, det_score
   - `embedder.py` — ArcFace: эмбеддинг 512-d
   - `blur_check.py` — variance of Laplacian
   - `photo_selector.py` — оркестратор: detect → filter → blur → embed → cosine similarity → топ-3
4) Реализовать PhotoProcessingService (фоновый воркер):
   - скачивание фото кандидатов малыми пачками (по 5)
   - прогон через InsightFace пайплайн
   - сохранение метаданных и эмбеддингов в `vk_photos`
   - поддержание буфера ~5 готовых кандидатов впереди курсора

Артефакты:
- `src/infrastructure/vk/*`
- `src/infrastructure/vision/*`
- `src/application/services/auth_service.py`
- `src/application/services/photo_processing_service.py`

### Участник B — DB + репозитории + история
1) Реализовать таблицы (8 таблиц):
   - `tg_users` (vk_token + vk_id + фильтры + history_cursor)
   - `vk_profiles` (данные кандидатов + статус обработки)
   - `vk_photos` (метаданные фото, faces_count, det_score, bbox, blur_score, embedding, status, reject_reason)
   - `search_queue` (очередь кандидатов per user)
   - `seen_profiles`
   - `view_history`
   - `favorite_profiles`
   - `blacklist_profiles`
2) Реализовать репозитории:
   - upsert tg_user + обновление токена
   - update filters
   - CRUD vk_profiles (upsert, update status)
   - CRUD vk_photos (insert, update после обработки, выбор топ-3 selected)
   - push/pop search_queue
   - push history / prev/next
   - CRUD favorites/blacklist/seen

Артефакты:
- `src/infrastructure/db/models.py`
- `src/infrastructure/db/repositories.py`
- обновлённый `scripts/init_db.sql`

---

## Этап 3: Telegram сценарии и интеграция

### Участник A — Telegram UI и FSM
1) /start → “Введите токен vk” → WAIT_VK_TOKEN
2) “Введите vk ID” → WAIT_VK_ID
3) При получении токена и ID:
   - вызвать AuthService.test_vk_token
   - показать “Настроить фильтры поиска”
4) “Настроить фильтры”:
   - 4 вопроса (FSM)
   - по завершению — MAIN_SCREEN
5) MAIN_SCREEN:
   - Предыдущий/Далее/Дополнительно
6) Дополнительно:
   - Добавить в избранное
   - В чёрный список
   - Показать избранное → Удалить

Артефакты:
- `src/presentation/tg/*`

### Участник B — Интеграция и документация
1) Связать Telegram сценарии с БД:
   - сохранить токен c vk_id
   - сохранить фильтры
   - history prev/next
   - favorites/blacklist/seen
2) Обновить/дописать документы:
   - `ARCHITECTURE.md`
   - `docs/user_manual.md`
   - `docs/db_schema.md`
   - `docs/vk_api_notes.md`
3) Финальные фиксы.

---

## Definition of Done (готово)
1) /start просит VK токен и vk_id.
2) Токен и id проверяется через VK API.
3) После проверки доступны "Настроить фильтры" и 4 вопроса.
4) Главный экран: Предыдущий/Далее/Дополнительно.
5) Избранное/ЧС работают и хранятся в БД.
6) Предыдущий/Далее работают через локальную историю показов.
7) Фото кандидатов отбираются через InsightFace (SCRFD + ArcFace): одно лицо, без размытия, один человек на топ-3.
8) Фоновый воркер обрабатывает кандидатов малыми пачками, пользователь не ждёт обработки.
9) Метаданные фото и эмбеддинги хранятся в `vk_photos`, файлы — в `data/photos/`.
10) Таблицы (8 шт.) создаются через `scripts/init_db.sql`.
11) Документации достаточно для проверки.
