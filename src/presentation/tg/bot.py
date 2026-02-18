# Bot/Dispatcher, регистрация роутеров

from src.application.services.auth_service import AuthService
from src.infrastructure.db.repositories import InMemoryUserRepo
from src.infrastructure.vk.client import VkClient
from src.infrastructure.vk.methods import VkMethods
from src.presentation.tg.handlers import setup_handlers
from src.core.config import TG_TOKEN

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

def setup_bot(token: str) -> tuple[Dispatcher, Bot]:
    """
    Собирает бота и диспетчер так, чтобы можно было тестить другим token.
    Возвращает (dp, bot).
    """
    # FSM память
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # routers
    user_repo = InMemoryUserRepo()

    # VK слой (не содержит токен — токен передаём параметром в методы)
    vk_client = VkClient()
    vk_methods = VkMethods(client=vk_client)

    # Сервис авторизации: валидирует и сохраняет
    auth_service = AuthService(vk=vk_methods, user_repo=user_repo)

    router = setup_handlers(user_repo=user_repo, auth_service=auth_service)
    dp.include_router(router=router)

    bot = Bot(token=token, default=DefaultBotProperties(parse_mode="HTML"))
    return dp, bot


async def start_bot() -> None:
    # получаем Dispatcher, Bot
    dp, bot = setup_bot(token=TG_TOKEN)
    
    # запуск бота    
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close() # закрытие сессии бота

