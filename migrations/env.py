# type: ignore

import asyncio
import os
from logging.config import fileConfig

import sqlalchemy
from alembic import context
from dotenv import load_dotenv
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

# 모델 import
from src.config.database import Base, database_models

load_dotenv()

config = context.config

# user = os.environ.get("DB_USER")
# password = os.environ.get("DB_PASSWORD")
# host = os.environ.get("DB_HOST")
# database = os.environ.get("DB_NAME")
# port = int(os.environ.get("DB_PORT", "5432"))
#
# database_url = sqlalchemy.engine.URL.create(
#     drivername="postgresql+asyncpg",
#     username=user,
#     password=password,
#     host=host,
#     port=port,
#     database=database,
# )

database_url = os.environ.get("PG_DATABASE_URL")
config.set_main_option("sqlalchemy.url", database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()