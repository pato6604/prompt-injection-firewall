import pytest

from app.config import settings


@pytest.mark.asyncio
async def test_admin_returns_503_without_master_key(client, monkeypatch):
    monkeypatch.setattr(settings, "auth_master_key", "")
    response = await client.get("/admin/stats", headers={"X-Master-Key": "test-master"})
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_admin_returns_401_with_wrong_master_key(client):
    response = await client.get("/admin/stats", headers={"X-Master-Key": "wrong"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_admin_key_lifecycle_and_stats(client):
    create_response = await client.post(
        "/admin/keys",
        headers={"X-Master-Key": "test-master"},
        json={"name": "admin-test"},
    )
    assert create_response.status_code == 200
    created = create_response.json()
    assert created["plaintext"]
    assert created["prefix"].startswith("pif_")

    list_response = await client.get(
        "/admin/keys", headers={"X-Master-Key": "test-master"}
    )
    assert list_response.status_code == 200
    keys = list_response.json()
    assert keys[0]["name"] == "admin-test"
    assert "key_hash" not in keys[0]

    revoke_response = await client.delete(
        f"/admin/keys/{created['id']}", headers={"X-Master-Key": "test-master"}
    )
    assert revoke_response.status_code == 200
    assert revoke_response.json()["revoked"] is True

    events_response = await client.get(
        "/admin/events", headers={"X-Master-Key": "test-master"}
    )
    assert events_response.status_code == 200

    stats_response = await client.get(
        "/admin/stats", headers={"X-Master-Key": "test-master"}
    )
    assert stats_response.status_code == 200
    assert stats_response.json()["total_requests"] == 0
