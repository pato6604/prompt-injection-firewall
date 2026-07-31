import pytest

from app.cache.decision_cache import DecisionCache


@pytest.mark.asyncio
async def test_decision_cache_memory_get_set_expiry(monkeypatch):
    monkeypatch.setattr("app.config.settings.redis_url", "")
    cache = DecisionCache()
    value = {
        "risk_score": 0.4,
        "decision": "flag",
        "triggered_rules": ["test"],
        "max_severity": "medium",
    }

    await cache.set("abc", value, ttl=1)
    assert await cache.get("abc") == value

    await cache.set("expired", value, ttl=0)
    assert await cache.get("expired") is None
