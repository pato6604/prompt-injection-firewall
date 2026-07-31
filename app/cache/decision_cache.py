import time
from typing import Any

from app.config import settings


class DecisionCache:
    """Cache de decisiones con Redis opcional y fallback en memoria."""

    def __init__(self) -> None:
        self.redis = None
        self._memory: dict[str, tuple[float, dict[str, Any]]] = {}

    async def initialize(self) -> None:
        """Inicializa Redis si esta configurado."""
        if settings.redis_url:
            import redis.asyncio as redis

            self.redis = redis.from_url(settings.redis_url, decode_responses=True)

    async def close(self) -> None:
        """Cierra Redis si fue inicializado."""
        if self.redis is not None:
            await self.redis.aclose()
            self.redis = None

    async def get(self, key: str) -> dict[str, Any] | None:
        """Obtiene una decision cacheada si no expiro."""
        if self.redis is not None:
            import json

            raw = await self.redis.get(f"decision:{key}")
            return json.loads(raw) if raw else None

        item = self._memory.get(key)
        if item is None:
            return None
        expires_at, value = item
        if expires_at <= time.monotonic():
            self._memory.pop(key, None)
            return None
        return value

    async def set(self, key: str, value: dict[str, Any], ttl: int | None = None) -> None:
        """Guarda una decision por ttl segundos."""
        ttl_seconds = ttl if ttl is not None else settings.decision_cache_ttl_seconds
        if self.redis is not None:
            import json

            await self.redis.setex(f"decision:{key}", ttl_seconds, json.dumps(value))
            return
        self._memory[key] = (time.monotonic() + ttl_seconds, value)


_decision_cache: DecisionCache | None = None


def get_decision_cache() -> DecisionCache:
    """Devuelve el singleton de cache de decisiones."""
    global _decision_cache
    if _decision_cache is None:
        _decision_cache = DecisionCache()
    return _decision_cache


def reset_decision_cache() -> None:
    """Resetea el singleton para tests."""
    global _decision_cache
    _decision_cache = None
