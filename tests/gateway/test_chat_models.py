"""Unit tests for chat Pydantic models."""

import uuid

import pytest
from pydantic import ValidationError

from app.gateway.models.chat import (
    ChatMessageResponse,
    ChatResponse,
    CreateChatRequest,
    SendChatMessageRequest,
)
from app.models.enums import ChatMessageRole, ChatStatus, ChatType


class TestCreateChatRequest:
    def test_defaults(self) -> None:
        req = CreateChatRequest()
        assert req.type == ChatType.DIRECTOR
        assert req.title is None
        assert req.project_id is None

    def test_explicit_values(self) -> None:
        """Test with dict input (simulates FastAPI JSON deserialization)."""
        req = CreateChatRequest.model_validate(
            {
                "type": "PROJECT",
                "title": "My project chat",
                "project_id": "550e8400-e29b-41d4-a716-446655440000",
            }
        )
        assert req.type == ChatType.PROJECT
        assert req.title == "My project chat"
        assert req.project_id == uuid.UUID("550e8400-e29b-41d4-a716-446655440000")


class TestSendChatMessageRequest:
    def test_valid_content(self) -> None:
        req = SendChatMessageRequest(content="Hello, Director!")
        assert req.content == "Hello, Director!"

    def test_empty_content_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SendChatMessageRequest(content="")

    def test_max_length_enforced(self) -> None:
        with pytest.raises(ValidationError):
            SendChatMessageRequest(content="x" * 100_001)


class TestChatResponse:
    def test_from_dict(self) -> None:
        data = {
            "id": "abc123",
            "session_id": "sess-1",
            "type": "DIRECTOR",
            "status": "ACTIVE",
            "title": None,
            "project_id": None,
            "created_at": "2026-02-28T12:00:00Z",
            "updated_at": "2026-02-28T12:00:00Z",
        }
        resp = ChatResponse.model_validate(data)
        assert resp.type == ChatType.DIRECTOR
        assert resp.status == ChatStatus.ACTIVE


class TestChatMessageResponse:
    def test_from_dict(self) -> None:
        data = {
            "id": "msg-1",
            "chat_id": "chat-1",
            "role": "USER",
            "content": "Hello",
            "created_at": "2026-02-28T12:00:00Z",
        }
        resp = ChatMessageResponse.model_validate(data)
        assert resp.role == ChatMessageRole.USER
        assert resp.content == "Hello"
