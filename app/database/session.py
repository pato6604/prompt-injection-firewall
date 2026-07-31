from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Devuelve el engine async global, inicializandolo bajo demanda."""
    global _engine, _sessionmaker
    if _engine is None:
        _engine = create_async_engine(settings.database_url, future=True)
        _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Devuelve el factory de sesiones asociado al engine global."""
    global _sessionmaker
    if _sessionmaker is None:
        get_engine()
    assert _sessionmaker is not None
    return _sessionmaker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependencia FastAPI para sesiones async."""
    async with get_sessionmaker()() as session:
        yield session


async def close_database() -> None:
    """Cierra el pool de conexiones de SQLAlchemy."""
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _sessionmaker = None


def reset_session_state() -> None:
    """Resetea singletons para tests que cambian DATABASE_URL."""
    global _engine, _sessionmaker
    _engine = None
    _sessionmaker = None
