"""Tests for error handling middleware."""

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

import pytest
from fastapi import APIRouter
from httpx import ASGITransport, AsyncClient

from app.gateway.deps import get_db_session, get_redis
from app.gateway.main import create_app
from app.lib import ConflictError, NotFoundError
from app.lib.exceptions import ConfigurationError, ValidationError, WorkerError
from app.models.enums import ErrorCode

# Test routes that raise specific exceptions
_test_router = APIRouter(prefix="/test-errors")


@_test_router.get("/not-found")
async def raise_not_found() -> None:
    raise NotFoundError("thing not found")


@_test_router.get("/conflict")
async def raise_conflict() -> None:
    raise ConflictError("already exists")


@_test_router.get("/validation")
async def raise_validation() -> None:
    raise ValidationError("bad input")


@_test_router.get("/configuration")
async def raise_configuration() -> None:
    raise ConfigurationError("missing config")


@_test_router.get("/worker")
async def raise_worker() -> None:
    raise WorkerError("worker failed")


@_test_router.get("/unhandled")
async def raise_unhandled() -> None:
    raise RuntimeError("unexpected boom")


@pytest.fixture
async def error_test_client(
    mock_db_session: AsyncMock,
    mock_redis: AsyncMock,
) -> AsyncIterator[AsyncClient]:
    """AsyncClient with error-raising test routes added."""
    app = create_app()
    app.include_router(_test_router)

    async def override_db_session() -> AsyncIterator[AsyncMock]:
        yield mock_db_session

    async def override_redis() -> AsyncMock:
        return mock_redis

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_redis] = override_redis

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        yield client


class TestErrorMiddleware:
    @pytest.mark.asyncio
    async def test_not_found_returns_404(self, error_test_client: AsyncClient) -> None:
        response = await error_test_client.get("/test-errors/not-found")
        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == ErrorCode.NOT_FOUND
        assert data["error"]["message"] == "thing not found"

    @pytest.mark.asyncio
    async def test_conflict_returns_409(self, error_test_client: AsyncClient) -> None:
        response = await error_test_client.get("/test-errors/conflict")
        assert response.status_code == 409
        data = response.json()
        assert data["error"]["code"] == ErrorCode.CONFLICT
        assert data["error"]["message"] == "already exists"

    @pytest.mark.asyncio
    async def test_validation_returns_422(self, error_test_client: AsyncClient) -> None:
        response = await error_test_client.get("/test-errors/validation")
        assert response.status_code == 422
        data = response.json()
        assert data["error"]["code"] == ErrorCode.VALIDATION_ERROR
        assert data["error"]["message"] == "bad input"

    @pytest.mark.asyncio
    async def test_configuration_returns_500(self, error_test_client: AsyncClient) -> None:
        response = await error_test_client.get("/test-errors/configuration")
        assert response.status_code == 500
        data = response.json()
        assert data["error"]["code"] == ErrorCode.CONFIGURATION_ERROR
        assert data["error"]["message"] == "missing config"

    @pytest.mark.asyncio
    async def test_worker_returns_500(self, error_test_client: AsyncClient) -> None:
        response = await error_test_client.get("/test-errors/worker")
        assert response.status_code == 500
        data = response.json()
        assert data["error"]["code"] == ErrorCode.WORKER_ERROR
        assert data["error"]["message"] == "worker failed"

    @pytest.mark.asyncio
    async def test_unhandled_returns_500(self, error_test_client: AsyncClient) -> None:
        response = await error_test_client.get("/test-errors/unhandled")
        assert response.status_code == 500
        data = response.json()
        assert data["error"]["code"] == ErrorCode.INTERNAL_ERROR
        assert data["error"]["message"] == "An internal error occurred"

    @pytest.mark.asyncio
    async def test_error_response_has_details_field(self, error_test_client: AsyncClient) -> None:
        response = await error_test_client.get("/test-errors/not-found")
        data = response.json()
        assert "details" in data["error"]
        assert data["error"]["details"] == {}
