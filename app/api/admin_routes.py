import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.models import ApiKey, SecurityEvent
from app.database.repositories import (
    get_stats,
    list_api_keys,
    list_recent_events,
    revoke_api_key,
)
from app.database.session import get_db
from app.security.authentication import generate_api_key

router = APIRouter(prefix="/admin")


class CreateKeyRequest(BaseModel):
    name: str


def require_master_key(x_master_key: str | None = Header(default=None)) -> None:
    """Protege endpoints administrativos con una clave maestra."""
    if not settings.auth_master_key:
        raise HTTPException(status_code=503, detail="AUTH_MASTER_KEY is not configured")
    if not hmac.compare_digest(x_master_key or "", settings.auth_master_key):
        raise HTTPException(status_code=401, detail="Invalid master key")


def serialize_api_key(api_key: ApiKey) -> dict:
    """Serializa una API key sin exponer su hash."""
    return {
        "id": api_key.id,
        "name": api_key.name,
        "prefix": api_key.key_prefix,
        "created_at": api_key.created_at,
        "revoked_at": api_key.revoked_at,
        "last_used_at": api_key.last_used_at,
    }


def serialize_event(event: SecurityEvent) -> dict:
    """Serializa eventos recientes para administracion."""
    return {
        "id": event.id,
        "timestamp": event.timestamp,
        "request_id": event.request_id,
        "api_key_id": event.api_key_id,
        "model": event.model,
        "messages_count": event.messages_count,
        "risk_score": event.risk_score,
        "decision": event.decision,
        "triggered_rules": event.triggered_rules,
        "normalized_text_preview": event.normalized_text_preview,
        "blocked": event.blocked,
        "ip_address": event.ip_address,
        "user_agent": event.user_agent,
    }


@router.post("/keys", dependencies=[Depends(require_master_key)])
async def create_key(payload: CreateKeyRequest, db: AsyncSession = Depends(get_db)):
    result = await generate_api_key(payload.name, db)
    return result


@router.get("/keys", dependencies=[Depends(require_master_key)])
async def get_keys(db: AsyncSession = Depends(get_db)):
    keys = await list_api_keys(db, include_revoked=True)
    return [serialize_api_key(key) for key in keys]


@router.delete("/keys/{key_id}", dependencies=[Depends(require_master_key)])
async def delete_key(key_id: int, db: AsyncSession = Depends(get_db)):
    revoked = await revoke_api_key(db, key_id)
    if not revoked:
        raise HTTPException(status_code=404, detail="API key not found or already revoked")
    return {"revoked": True}


@router.get("/events", dependencies=[Depends(require_master_key)])
async def get_events(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    events = await list_recent_events(db, limit=limit, offset=offset)
    return [serialize_event(event) for event in events]


@router.get("/stats", dependencies=[Depends(require_master_key)])
async def admin_stats(db: AsyncSession = Depends(get_db)):
    return await get_stats(db)
