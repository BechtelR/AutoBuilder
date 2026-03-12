"""Tests for skill management routes."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.gateway.deps import get_skill_library
from app.gateway.main import create_app
from app.skills.library import SkillEntry, SkillLibrary, TriggerSpec

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_mock_skill_library(entries: dict[str, SkillEntry] | None = None) -> MagicMock:
    """Create a mock SkillLibrary with optional index entries."""
    lib = MagicMock(spec=SkillLibrary)
    lib.get_index.return_value = entries or {}
    lib.invalidate_cache = AsyncMock()
    lib.save_to_cache = AsyncMock()
    lib.scan = MagicMock()
    return lib


@pytest_asyncio.fixture
async def skills_client() -> AsyncIterator[AsyncClient]:
    """AsyncClient with mocked SkillLibrary dependency (no infra required)."""
    app = create_app()
    mock_lib = _make_mock_skill_library()

    app.dependency_overrides[get_skill_library] = lambda: mock_lib

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        yield client


@pytest_asyncio.fixture
async def skills_client_with_entries() -> AsyncIterator[AsyncClient]:
    """AsyncClient with SkillLibrary containing sample entries."""
    app = create_app()

    from app.models.enums import TriggerType

    entries = {
        "api-endpoint": SkillEntry(
            name="api-endpoint",
            description="REST API endpoint conventions",
            triggers=[
                TriggerSpec(trigger_type=TriggerType.DELIVERABLE_TYPE, value="api_endpoint"),
            ],
            tags=["api", "http"],
            applies_to=["coder", "reviewer"],
            priority=10,
            has_references=True,
            has_assets=False,
            path=Path("/fake/api-endpoint/SKILL.md"),
        ),
        "governance": SkillEntry(
            name="governance",
            description="Director governance rules",
            triggers=[
                TriggerSpec(trigger_type=TriggerType.ALWAYS, value=""),
            ],
            tags=[],
            applies_to=["director"],
            priority=20,
            has_references=False,
            has_assets=False,
            path=Path("/fake/governance/SKILL.md"),
        ),
    }
    mock_lib = _make_mock_skill_library(entries)

    app.dependency_overrides[get_skill_library] = lambda: mock_lib

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        yield client


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestInvalidateSkillCache:
    @pytest.mark.asyncio
    async def test_returns_invalidated(self, skills_client: AsyncClient) -> None:
        response = await skills_client.post("/skills/cache/invalidate")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "invalidated"


class TestListSkills:
    @pytest.mark.asyncio
    async def test_empty_index_returns_empty_list(self, skills_client: AsyncClient) -> None:
        response = await skills_client.get("/skills")
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_returns_catalog_entries(self, skills_client_with_entries: AsyncClient) -> None:
        response = await skills_client_with_entries.get("/skills")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

        # Sorted by name: api-endpoint, governance
        assert data[0]["name"] == "api-endpoint"
        assert data[0]["description"] == "REST API endpoint conventions"
        assert data[0]["priority"] == 10
        assert data[0]["tags"] == ["api", "http"]
        assert data[0]["applies_to"] == ["coder", "reviewer"]
        assert data[0]["has_references"] is True
        assert data[0]["has_assets"] is False
        assert data[0]["has_scripts"] is False
        assert len(data[0]["triggers"]) == 1

        assert data[1]["name"] == "governance"
        assert data[1]["priority"] == 20
        assert data[1]["applies_to"] == ["director"]
        assert data[1]["has_scripts"] is False
