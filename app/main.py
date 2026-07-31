import logging
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from app.api.admin_routes import router as admin_router
from app.api.health_routes import router as health_router
from app.api.proxy_routes import router as proxy_router
from app.cache.decision_cache import get_decision_cache
from app.config import settings
from app.database.models import Base
from app.database.session import close_database, get_engine
from app.proxy.provider_router import close_provider
from app.security.rate_limit import get_rate_limiter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Prompt Injection Firewall")
    engine = get_engine()
    if settings.database_url.startswith("sqlite"):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    await get_rate_limiter().initialize()
    await get_decision_cache().initialize()
    yield
    logger.info("Shutting down...")
    await close_provider()
    await get_rate_limiter().close()
    await get_decision_cache().close()
    await close_database()


app = FastAPI(title="Prompt Injection Firewall", version="0.1.0", lifespan=lifespan)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Propaga o genera un request_id para trazabilidad."""
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


app.include_router(health_router)
app.include_router(proxy_router)
app.include_router(admin_router)
