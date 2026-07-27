import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from app.api.health_routes import router as health_router
from app.api.proxy_routes import router as proxy_router
from app.proxy.request_parser import parse_request
from app.proxy.provider_router import get_provider, close_provider
from app.proxy.stream_handler import stream_response

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Prompt Injection Firewall")
    yield
    logger.info("Shutting down...")
    await close_provider()


app = FastAPI(title="Prompt Injection Firewall", version="0.1.0", lifespan=lifespan)
app.include_router(health_router)
app.include_router(proxy_router)
