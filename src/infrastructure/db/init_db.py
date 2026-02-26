from sqlalchemy.ext.asyncio import AsyncEngine
from infrastructure.db.models import Base


async def init_db(engine: AsyncEngine) -> None:
    """
    Создаёт все таблицы в базе данных.

    Используется:
    - для локальной разработки
    - в тестах
    - при первом запуске проекта
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)