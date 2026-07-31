import pytest

from app.config import settings
from app.database.repositories import revoke_api_key
from app.security.authentication import generate_api_key, verify_api_key


@pytest.mark.asyncio
async def test_generate_verify_and_revoke_api_key(db_sessionmaker):
    async with db_sessionmaker() as session:
        created = await generate_api_key("test", session)
        assert created["plaintext"]
        assert created["prefix"].startswith("pif_")

        verified = await verify_api_key(created["plaintext"], session)
        assert verified is not None
        assert verified.last_used_at is not None

        await revoke_api_key(session, created["id"])
        revoked = await verify_api_key(created["plaintext"], session)
        assert revoked is None


@pytest.mark.asyncio
async def test_proxy_returns_401_without_api_key(client, monkeypatch):
    monkeypatch.setattr(settings, "auth_enabled", True)
    response = await client.post(
        "/v1/chat/completions",
        json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "hola"}]},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_proxy_returns_401_with_invalid_api_key(client, monkeypatch):
    monkeypatch.setattr(settings, "auth_enabled", True)
    response = await client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer invalid"},
        json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "hola"}]},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_proxy_returns_401_with_revoked_api_key(
    client, db_sessionmaker, monkeypatch
):
    monkeypatch.setattr(settings, "auth_enabled", True)
    async with db_sessionmaker() as session:
        created = await generate_api_key("revoked", session)
        await revoke_api_key(session, created["id"])

    response = await client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {created['plaintext']}"},
        json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "hola"}]},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_proxy_accepts_valid_api_key(
    client, db_sessionmaker, monkeypatch, mock_provider
):
    monkeypatch.setattr(settings, "auth_enabled", True)
    async with db_sessionmaker() as session:
        created = await generate_api_key("valid", session)

    response = await client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {created['plaintext']}"},
        json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "hola"}]},
    )
    assert response.status_code == 200
    assert response.headers["X-Request-ID"]
