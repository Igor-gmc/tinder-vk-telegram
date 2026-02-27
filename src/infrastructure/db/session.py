from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession


def create_session_factory(database_url: str) -> async_sessionmaker[AsyncSession]:
    """Создаёт фабрику асинхронных сессий SQLAlchemy."""
    engine = create_async_engine(database_url, echo=False)
    return async_sessionmaker(engine, expire_on_commit=False)
