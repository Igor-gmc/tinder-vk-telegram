import os
import pytest
from dotenv import load_dotenv

from src.infrastructure.db.session import create_session_factory
from src.infrastructure.db.postgres_repo import PostgresUserRepo


@pytest.mark.asyncio
async def test_user_creation():
    """Требует запущенный PostgreSQL и DATABASE_URL в .env."""
    load_dotenv()

    database_url = os.getenv("DATABASE_URL")
    assert database_url, "DATABASE_URL не задан в .env"

    session_factory = create_session_factory(database_url)
    repo = PostgresUserRepo(session_factory)

    user = await repo.get_or_create_user(123)
    assert user.tg_user_id == 123
