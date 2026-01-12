"""Database session management."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.bot.config import settings
from src.database.models import Base

engine = create_async_engine(
    settings.database_url,
    echo=False,
)

SessionMaker = async_sessionmaker[AsyncSession]


def create_session_maker(database_url: str) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        create_async_engine(
            database_url,
            echo=False,
        ),
        class_=AsyncSession,
        expire_on_commit=False,
    )


session_factory = create_session_maker(settings.database_url)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get a database session."""
    async with session_factory() as session:
        yield session


async def init_db() -> None:
    """Create all database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
