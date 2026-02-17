# Bot/Dispatcher, регистрация роутеров

from src.infrastructure.db.repositories import InMemoryUserRepo
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
    router = setup_handlers(user_repo)
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

