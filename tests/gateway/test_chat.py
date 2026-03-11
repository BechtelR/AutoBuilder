"""Integration tests for chat routes (real PostgreSQL + Redis)."""

import pytest
from httpx import AsyncClient

from tests.conftest import require_infra


@require_infra
class TestChatEndpoints:
    @pytest.mark.asyncio
    async def test_create_chat_returns_201(self, test_client: AsyncClient) -> None:
        response = await test_client.post("/chat", json={})
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert "session_id" in data
        assert data["type"] == "DIRECTOR"
        assert data["status"] == "ACTIVE"

    @pytest.mark.asyncio
    async def test_create_chat_with_title(self, test_client: AsyncClient) -> None:
        response = await test_client.post("/chat", json={"type": "DIRECTOR", "title": "Test Chat"})
        assert response.status_code == 201
        assert response.json()["title"] == "Test Chat"

    @pytest.mark.asyncio
    async def test_list_chats_empty(self, test_client: AsyncClient) -> None:
        response = await test_client.get("/chat")
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_chats_returns_created(self, test_client: AsyncClient) -> None:
        await test_client.post("/chat", json={"title": "Chat A"})
        await test_client.post("/chat", json={"title": "Chat B"})
        response = await test_client.get("/chat")
        assert response.status_code == 200
        chats = response.json()
        assert len(chats) == 2

    @pytest.mark.asyncio
    async def test_list_chats_filter_by_type(self, test_client: AsyncClient) -> None:
        await test_client.post("/chat", json={"type": "DIRECTOR"})
        await test_client.post("/chat", json={"type": "PROJECT"})
        response = await test_client.get("/chat", params={"type": "DIRECTOR"})
        assert response.status_code == 200
        chats = response.json()
        assert len(chats) == 1
        assert chats[0]["type"] == "DIRECTOR"

    @pytest.mark.asyncio
    async def test_get_chat_by_session_id(self, test_client: AsyncClient) -> None:
        create_resp = await test_client.post("/chat", json={"title": "Test"})
        session_id = create_resp.json()["session_id"]

        response = await test_client.get(f"/chat/{session_id}")
        assert response.status_code == 200
        assert response.json()["session_id"] == session_id

    @pytest.mark.asyncio
    async def test_get_chat_not_found(self, test_client: AsyncClient) -> None:
        response = await test_client.get("/chat/nonexistent-session")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_send_message_returns_201(self, test_client: AsyncClient) -> None:
        create_resp = await test_client.post("/chat", json={})
        session_id = create_resp.json()["session_id"]

        response = await test_client.post(
            f"/chat/{session_id}/messages",
            json={"content": "Hello, Director!"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["role"] == "USER"
        assert data["content"] == "Hello, Director!"

    @pytest.mark.asyncio
    async def test_send_message_empty_content_rejected(self, test_client: AsyncClient) -> None:
        create_resp = await test_client.post("/chat", json={})
        session_id = create_resp.json()["session_id"]

        response = await test_client.post(
            f"/chat/{session_id}/messages",
            json={"content": ""},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_messages_empty(self, test_client: AsyncClient) -> None:
        create_resp = await test_client.post("/chat", json={})
        session_id = create_resp.json()["session_id"]

        response = await test_client.get(f"/chat/{session_id}/messages")
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_get_messages_returns_sent(self, test_client: AsyncClient) -> None:
        create_resp = await test_client.post("/chat", json={})
        session_id = create_resp.json()["session_id"]

        await test_client.post(
            f"/chat/{session_id}/messages",
            json={"content": "First message"},
        )
        await test_client.post(
            f"/chat/{session_id}/messages",
            json={"content": "Second message"},
        )

        response = await test_client.get(f"/chat/{session_id}/messages")
        assert response.status_code == 200
        messages = response.json()
        assert len(messages) == 2
        assert messages[0]["content"] == "First message"
        assert messages[1]["content"] == "Second message"

    @pytest.mark.asyncio
    async def test_chat_stream_placeholder(self, test_client: AsyncClient) -> None:
        create_resp = await test_client.post("/chat", json={})
        session_id = create_resp.json()["session_id"]

        response = await test_client.get(f"/chat/{session_id}/stream")
        assert response.status_code == 200
        assert response.json()["session_id"] == session_id

    @pytest.mark.asyncio
    async def test_send_message_to_nonexistent_chat(self, test_client: AsyncClient) -> None:
        response = await test_client.post(
            "/chat/nonexistent/messages",
            json={"content": "Hello"},
        )
        assert response.status_code == 404

    # -----------------------------------------------------------------------
    # Well-known session auto-creation
    # -----------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_main_session_auto_created(self, test_client: AsyncClient) -> None:
        response = await test_client.get("/chat/main")
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "DIRECTOR"
        assert data["title"] == "Main"
        assert data["session_id"].startswith("main_")

    @pytest.mark.asyncio
    async def test_main_session_idempotent(self, test_client: AsyncClient) -> None:
        r1 = await test_client.get("/chat/main")
        r2 = await test_client.get("/chat/main")
        assert r1.json()["id"] == r2.json()["id"]

    @pytest.mark.asyncio
    async def test_settings_session_auto_created(self, test_client: AsyncClient) -> None:
        response = await test_client.get("/chat/settings")
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "SETTINGS"
        assert data["title"] == "Settings"
        assert data["session_id"].startswith("settings_")

    @pytest.mark.asyncio
    async def test_settings_session_idempotent(self, test_client: AsyncClient) -> None:
        r1 = await test_client.get("/chat/settings")
        r2 = await test_client.get("/chat/settings")
        assert r1.json()["id"] == r2.json()["id"]
