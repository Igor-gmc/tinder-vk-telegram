from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

import sys
import os
from pathlib import Path
from dotenv import load_dotenv


# --------------------------------------------------
# PATH НАСТРОЙКА (чтобы Alembic видел src)
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent  # корень проекта

# Добавляем корень проекта в sys.path, чтобы работали импорты from src.*
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


# --------------------------------------------------
# ЗАГРУЗКА .env
# --------------------------------------------------

load_dotenv(BASE_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

# Alembic работает с sync драйвером.
# +asyncpg — async-only, заменяем на +psycopg (sync-совместимый).
# +psycopg — уже sync-совместимый, оставляем как есть.
SYNC_DATABASE_URL = DATABASE_URL.replace("+asyncpg", "+psycopg")


# --------------------------------------------------
# ALEMBIC CONFIG
# --------------------------------------------------

config = context.config
config.set_main_option("sqlalchemy.url", SYNC_DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# --------------------------------------------------
# ИМПОРТ МОДЕЛЕЙ
# --------------------------------------------------

from src.infrastructure.db.models import Base

target_metadata = Base.metadata


# --------------------------------------------------
# OFFLINE MODE
# --------------------------------------------------

def run_migrations_offline():
    context.configure(
        url=SYNC_DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


# --------------------------------------------------
# ONLINE MODE
# --------------------------------------------------

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


# --------------------------------------------------
# RUN
# --------------------------------------------------

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
