import hashlib
import secrets

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.models import ApiKey
from app.database.repositories import create_api_key, get_api_key_by_hash, touch_api_key_usage
from app.database.session import get_db


async def generate_api_key(name: str, db: AsyncSession) -> dict:
    """Genera una API key interna y devuelve el secreto una sola vez."""
    plaintext, api_key = await create_api_key(db, name)
    return {"plaintext": plaintext, "prefix": api_key.key_prefix, "id": api_key.id}


def hash_api_key(plaintext: str) -> str:
    """Calcula SHA-256 hexadecimal para una API key."""
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


async def verify_api_key(plaintext: str, db: AsyncSession) -> ApiKey | None:
    """Verifica una API key y actualiza su ultimo uso si esta activa."""
    api_key = await get_api_key_by_hash(db, hash_api_key(plaintext))
    if api_key is None or api_key.revoked_at is not None:
        return None
    await touch_api_key_usage(db, api_key.id)
    await db.refresh(api_key)
    return api_key


async def require_api_key(
    request: Request, db: AsyncSession = Depends(get_db)
) -> ApiKey | None:
    """Dependencia que exige Authorization: Bearer cuando la auth esta activa."""
    if not settings.auth_enabled:
        request.state.api_key = None
        return None

    authorization = request.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Missing API key")

    api_key = await verify_api_key(token, db)
    if api_key is None:
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")

    request.state.api_key = api_key
    return api_key
