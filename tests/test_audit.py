import pytest
from sqlalchemy import select

from app.database.models import SecurityEvent


@pytest.mark.asyncio
async def test_proxy_logs_security_event(client, db_sessionmaker, mock_provider):
    response = await client.post(
        "/v1/chat/completions",
        json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "hola"}]},
    )
    assert response.status_code == 200

    async with db_sessionmaker() as session:
        event = (await session.execute(select(SecurityEvent))).scalar_one()
        assert event.decision == "allow"
        assert event.risk_score == 0.0
        assert event.request_id == response.headers["X-Request-ID"]
