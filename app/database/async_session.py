from collections.abc import AsyncGenerator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config.settings import Settings, get_settings


@lru_cache(maxsize=8)
def get_async_engine(database_url: str, echo: bool = False) -> AsyncEngine:
    return create_async_engine(
        database_url,
        echo=echo,
        pool_pre_ping=True,
    )


@lru_cache(maxsize=8)
def get_async_session_factory(
    database_url: str,
    echo: bool = False,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=get_async_engine(database_url, echo),
        class_=AsyncSession,
        autoflush=False,
        expire_on_commit=False,
    )


async def get_async_db(
    settings: Annotated[Settings, Depends(get_settings)],
) -> AsyncGenerator[AsyncSession, None]:
    factory = get_async_session_factory(
        settings.resolved_async_database_url,
        settings.database_echo,
    )
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
