import hashlib
import secrets
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import ApiKey, SecurityEvent


def _hash_api_key(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


async def create_api_key(db: AsyncSession, name: str) -> tuple[str, ApiKey]:
    """Crea una API key y persiste solo su hash SHA-256."""
    plaintext = secrets.token_urlsafe(32)
    api_key = ApiKey(
        name=name,
        key_prefix=f"pif_{plaintext[:8]}",
        key_hash=_hash_api_key(plaintext),
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    return plaintext, api_key


async def revoke_api_key(db: AsyncSession, key_id: int) -> bool:
    """Marca una API key como revocada."""
    result = await db.execute(
        update(ApiKey)
        .where(ApiKey.id == key_id, ApiKey.revoked_at.is_(None))
        .values(revoked_at=datetime.now(timezone.utc))
    )
    await db.commit()
    return result.rowcount > 0


async def list_api_keys(db: AsyncSession, include_revoked: bool = False) -> list[ApiKey]:
    """Lista API keys, excluyendo revocadas por defecto."""
    stmt = select(ApiKey).order_by(ApiKey.created_at.desc(), ApiKey.id.desc())
    if not include_revoked:
        stmt = stmt.where(ApiKey.revoked_at.is_(None))
    return list((await db.execute(stmt)).scalars().all())


async def get_api_key_by_hash(db: AsyncSession, key_hash: str) -> ApiKey | None:
    """Busca una API key por hash."""
    return (await db.execute(select(ApiKey).where(ApiKey.key_hash == key_hash))).scalar_one_or_none()


async def touch_api_key_usage(db: AsyncSession, key_id: int) -> None:
    """Actualiza la fecha de ultimo uso de una API key."""
    await db.execute(
        update(ApiKey)
        .where(ApiKey.id == key_id)
        .values(last_used_at=datetime.now(timezone.utc))
    )
    await db.commit()


async def log_security_event(db: AsyncSession, **kwargs: Any) -> SecurityEvent:
    """Inserta un evento de seguridad auditable."""
    event = SecurityEvent(**kwargs)
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


async def list_recent_events(
    db: AsyncSession, limit: int = 100, offset: int = 0
) -> list[SecurityEvent]:
    """Devuelve eventos recientes con paginacion simple."""
    stmt = (
        select(SecurityEvent)
        .order_by(SecurityEvent.timestamp.desc(), SecurityEvent.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list((await db.execute(stmt)).scalars().all())


async def get_stats(db: AsyncSession) -> dict[str, Any]:
    """Calcula metricas agregadas del firewall."""
    total = await db.scalar(select(func.count(SecurityEvent.id)))
    blocked = await db.scalar(select(func.count(SecurityEvent.id)).where(SecurityEvent.blocked.is_(True)))
    flagged = await db.scalar(
        select(func.count(SecurityEvent.id)).where(SecurityEvent.decision == "flag")
    )
    avg_risk = await db.scalar(select(func.avg(SecurityEvent.risk_score)))
    return {
        "total_requests": total or 0,
        "blocked_count": blocked or 0,
        "flagged_count": flagged or 0,
        "avg_risk_score": float(avg_risk or 0.0),
    }
