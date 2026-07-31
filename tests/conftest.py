import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.cache.decision_cache import reset_decision_cache
from app.config import settings
from app.database.models import Base
from app.database.session import get_db, reset_session_state
from app.main import app
from app.security.rate_limit import reset_rate_limiter


@pytest_asyncio.fixture
async def db_sessionmaker(monkeypatch):
    monkeypatch.setattr(settings, "database_url", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setattr(settings, "redis_url", "")
    monkeypatch.setattr(settings, "auth_enabled", False)
    monkeypatch.setattr(settings, "auth_master_key", "test-master")
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_requests", 1000)
    monkeypatch.setattr(settings, "rate_limit_window_seconds", 60)
    monkeypatch.setattr(settings, "decision_cache_ttl_seconds", 60)
    reset_session_state()
    reset_rate_limiter()
    reset_decision_cache()

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield sessionmaker

    await engine.dispose()
    app.dependency_overrides.clear()
    reset_session_state()
    reset_rate_limiter()
    reset_decision_cache()


@pytest.fixture
def mock_provider(monkeypatch):
    from app.api.schemas import ChatCompletionResponse, ChatMessage, Choice, Usage
    import app.api.proxy_routes as proxy_routes

    class DummyProvider:
        async def chat(self, request):
            return ChatCompletionResponse(
                id="chatcmpl-test",
                created=0,
                model=request.model,
                choices=[
                    Choice(
                        message=ChatMessage(role="assistant", content="ok"),
                    )
                ],
                usage=Usage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
            )

        async def stream(self, request):
            yield 'data: {"choices":[]}\n\n'

    monkeypatch.setattr(proxy_routes, "get_provider", lambda: DummyProvider())


@pytest_asyncio.fixture
async def client(db_sessionmaker):
    async def override_get_db():
        async with db_sessionmaker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
