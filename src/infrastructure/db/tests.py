import pytest
from infrastructure.db.session import SessionLocal
from infrastructure.db.repositories.postgres_repo import PostgresUserRepository


@pytest.mark.asyncio
async def test_user_creation():
    async with SessionLocal() as session:
        repo = PostgresUserRepository(session)

        user = await repo.get_or_create_user(123)

        assert user.tg_user_id == 123