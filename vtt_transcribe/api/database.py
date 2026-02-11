"""Database configuration and session management."""

import os
from collections.abc import AsyncGenerator

try:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from sqlalchemy.orm import DeclarativeBase

    # Database URL from environment or default to SQLite
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./vtt_transcribe.db")

    # Convert PostgreSQL URL to async version if needed
    if DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif DATABASE_URL.startswith("sqlite://"):
        DATABASE_URL = DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://", 1)

    # Base class for all models
    class Base(DeclarativeBase):
        """Base class for all SQLAlchemy models."""

    # Create async engine
    engine = create_async_engine(
        DATABASE_URL,
        echo=os.getenv("SQL_ECHO", "false").lower() == "true",
        future=True,
    )

    # Create async session factory
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    database_available = True

except ImportError:
    # Database dependencies not available
    Base = None  # type: ignore[assignment,misc]
    engine = None  # type: ignore[assignment]
    AsyncSessionLocal = None  # type: ignore[assignment]
    database_available = False


async def init_db() -> None:
    """Initialize database tables."""
    if not database_available or engine is None:
        return  # Skip if database dependencies not available

    try:
        # Import models here to ensure they're registered with Base.metadata
        from vtt_transcribe.api.models import APIKey, TranscriptionJob, User  # noqa: F401

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except ImportError:
        # Models not available, skip initialization
        pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async database sessions."""
    if not database_available or AsyncSessionLocal is None:
        msg = "Database dependencies not available"
        raise RuntimeError(msg)

    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
