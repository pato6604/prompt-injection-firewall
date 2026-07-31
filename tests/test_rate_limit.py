import pytest

from app.config import settings
from app.security.rate_limit import reset_rate_limiter


@pytest.mark.asyncio
async def test_rate_limit_returns_429_on_fourth_request(client, monkeypatch, mock_provider):
    monkeypatch.setattr(settings, "auth_enabled", False)
    monkeypatch.setattr(settings, "rate_limit_requests", 3)
    monkeypatch.setattr(settings, "rate_limit_window_seconds", 60)
    reset_rate_limiter()

    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": "hola"}],
    }
    for _ in range(3):
        response = await client.post("/v1/chat/completions", json=payload)
        assert response.status_code == 200

    response = await client.post("/v1/chat/completions", json=payload)
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "60"
