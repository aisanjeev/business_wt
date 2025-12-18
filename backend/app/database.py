"""Database connection and session management."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool

from app.config import settings


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""
    pass


def get_engine_kwargs() -> dict:
    """Get engine configuration based on database type.
    
    Returns:
        Dictionary of engine kwargs appropriate for the database type.
    """
    kwargs: dict = {
        "echo": settings.db_echo,
    }
    
    if settings.is_sqlite:
        # SQLite-specific settings
        # Use StaticPool for SQLite to enable sharing connection across threads
        kwargs["poolclass"] = StaticPool
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        # MySQL-specific connection pool settings
        kwargs["pool_size"] = settings.db_pool_size
        kwargs["max_overflow"] = settings.db_max_overflow
        kwargs["pool_recycle"] = settings.db_pool_recycle
        kwargs["pool_pre_ping"] = True  # Check connections before use
    
    return kwargs


# Create async engine with appropriate settings
engine = create_async_engine(
    settings.get_database_url(async_mode=True),
    **get_engine_kwargs()
)


# Create async session factory
async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Async context manager for database sessions.
    
    Usage:
        async with get_db_context() as db:
            # use db session
    """
    session = async_session_maker()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions.
    
    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            # use db session
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Initialize database by creating all tables.
    
    Should be called on application startup.
    """
    async with engine.begin() as conn:
        # Import models to ensure they are registered with Base
        from app import models  # noqa: F401
        
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections.
    
    Should be called on application shutdown.
    """
    await engine.dispose()


# SQLite-specific: Enable foreign key support
if settings.is_sqlite:
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        """Enable foreign key constraints for SQLite."""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
