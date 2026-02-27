# Bot/Dispatcher, регистрация роутеров

import logging
import os

from src.application.services.auth_service import AuthService
from src.application.services.dating_service import DatingService
from src.application.services.photo_processing_service import PhotoProcessingService
from src.infrastructure.db.repositories import InMemoryUserRepo
from src.infrastructure.vk.client import VkClient
from src.infrastructure.vk.methods import VkMethods
from src.presentation.tg.handlers import setup_handlers
from src.core.config import TG_TOKEN, CLEAN_DB_ON_START

logger = logging.getLogger(__name__)

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

def setup_bot(token: str) -> tuple[Dispatcher, Bot, PhotoProcessingService]:
    """
    Собирает бота и диспетчер так, чтобы можно было тестить другим token.
    Возвращает (dp, bot, photo_service).
    """
    # FSM память
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Выбор репозитория: PostgreSQL (если DATABASE_URL задан) или InMemory
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        from src.infrastructure.db.session import create_session_factory
        from src.infrastructure.db.postgres_repo import PostgresUserRepo
        session_factory = create_session_factory(database_url)
        user_repo = PostgresUserRepo(session_factory)
    else:
        user_repo = InMemoryUserRepo()

    # VK слой (не содержит токен — токен передаём параметром в методы)
    vk_client = VkClient()
    vk_methods = VkMethods(client=vk_client)

    # Сервис авторизации: валидирует и сохраняет
    auth_service = AuthService(vk=vk_methods, user_repo=user_repo)

    # Сервис обработки фото: скачивание + (позже) InsightFace
    photo_service = PhotoProcessingService(vk=vk_methods, user_repo=user_repo)

    # Сервис знакомств: поиск кандидатов, навигация по очереди
    dating_service = DatingService(vk=vk_methods, user_repo=user_repo, _photo_service=photo_service)

    router = setup_handlers(
        user_repo=user_repo,
        auth_service=auth_service,
        dating_service=dating_service,
        photo_service=photo_service,
    )
    dp.include_router(router=router)

    bot = Bot(token=token, default=DefaultBotProperties(parse_mode="HTML"))
    return dp, bot, photo_service


async def _clean_db() -> None:
    """Очистка всех таблиц БД (если CLEAN_DB_ON_START=true)."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return

    from src.infrastructure.db.session import create_session_factory
    from src.infrastructure.db.models import User, QueueItem, FavoriteProfile, Blacklist, Profile, Photo

    sf = create_session_factory(database_url)
    async with sf() as s:
        for table in (Photo, QueueItem, FavoriteProfile, Blacklist, Profile, User):
            from sqlalchemy import delete
            await s.execute(delete(table))
        await s.commit()
    logger.info('БД очищена (CLEAN_DB_ON_START=true)')


async def start_bot() -> None:
    # очистка БД при старте (если включена)
    if CLEAN_DB_ON_START:
        await _clean_db()

    # получаем Dispatcher, Bot, PhotoProcessingService
    dp, bot, photo_service = setup_bot(token=TG_TOKEN)

    # прогрев InsightFace детектора (в thread pool, не блокирует)
    await photo_service.warm_up_detector()

    # запуск бота
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close() # закрытие сессии бота

