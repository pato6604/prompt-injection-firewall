import asyncio
import time
from collections import defaultdict, deque
from typing import Deque

from app.config import settings


class RateLimiter:
    """Rate limiter con Redis opcional y fallback en memoria."""

    def __init__(self) -> None:
        self.redis = None
        self._memory: dict[str, Deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Inicializa Redis si esta configurado."""
        if settings.redis_url:
            import redis.asyncio as redis

            self.redis = redis.from_url(settings.redis_url, decode_responses=True)

    async def close(self) -> None:
        """Cierra el cliente Redis si existe."""
        if self.redis is not None:
            await self.redis.aclose()
            self.redis = None

    async def check(self, key: str) -> bool:
        """Devuelve True si la clave esta dentro del limite configurado."""
        if not settings.rate_limit_enabled:
            return True
        if self.redis is not None:
            return await self._check_redis(key)
        return await self._check_memory(key)

    async def _check_redis(self, key: str) -> bool:
        redis_key = f"rate_limit:{key}"
        count = await self.redis.incr(redis_key)
        if count == 1:
            await self.redis.expire(redis_key, settings.rate_limit_window_seconds)
        return int(count) <= settings.rate_limit_requests

    async def _check_memory(self, key: str) -> bool:
        now = time.monotonic()
        window_start = now - settings.rate_limit_window_seconds
        async with self._lock:
            entries = self._memory[key]
            while entries and entries[0] <= window_start:
                entries.popleft()
            if len(entries) >= settings.rate_limit_requests:
                return False
            entries.append(now)
            return True


_rate_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    """Devuelve el singleton de rate limiting."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def reset_rate_limiter() -> None:
    """Resetea el singleton para tests."""
    global _rate_limiter
    _rate_limiter = None
