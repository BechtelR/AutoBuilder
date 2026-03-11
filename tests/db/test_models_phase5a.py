"""Tests for Phase 5a database models: CeoQueueItem, DirectorQueueItem, ProjectConfig."""

import uuid

from sqlalchemy import inspect as sa_inspect

from app.db.models import CeoQueueItem, DirectorQueueItem, ProjectConfig
from app.models.enums import (
    CeoItemType,
    CeoQueueStatus,
    DirectorQueueStatus,
    EscalationPriority,
    EscalationRequestType,
)


def _column_default(model: type, attr_name: str) -> object:
    """Get the Python-side default for a mapped column by attribute name."""
    mapper = sa_inspect(model)  # type: ignore[type-var]
    prop = mapper.attrs[attr_name]  # type: ignore[union-attr]
    col = prop.columns[0]  # type: ignore[union-attr]
    if col.default is not None:  # type: ignore[union-attr]
        return col.default.arg  # type: ignore[union-attr]
    return None


class TestCeoQueueItem:
    def test_instantiate_with_required_fields(self) -> None:
        item = CeoQueueItem(
            type=CeoItemType.ESCALATION,
            title="Test escalation",
        )
        assert item.type == CeoItemType.ESCALATION
        assert item.title == "Test escalation"

    def test_default_priority(self) -> None:
        assert _column_default(CeoQueueItem, "priority") == EscalationPriority.NORMAL

    def test_default_status(self) -> None:
        assert _column_default(CeoQueueItem, "status") == CeoQueueStatus.PENDING

    def test_default_metadata(self) -> None:
        default = _column_default(CeoQueueItem, "metadata_")
        assert callable(default) and default(None) == {}

    def test_optional_fields_default_none(self) -> None:
        item = CeoQueueItem(
            type=CeoItemType.NOTIFICATION,
            title="Test",
        )
        assert item.source_project_id is None
        assert item.source_agent is None
        assert item.session_id is None
        assert item.resolved_at is None
        assert item.resolved_by is None

    def test_with_source_project_id(self) -> None:
        pid = uuid.uuid4()
        item = CeoQueueItem(
            type=CeoItemType.ESCALATION,
            title="Test",
            source_project_id=pid,
        )
        assert item.source_project_id == pid

    def test_tablename(self) -> None:
        assert CeoQueueItem.__tablename__ == "ceo_queue"


class TestDirectorQueueItem:
    def test_instantiate_with_required_fields(self) -> None:
        item = DirectorQueueItem(
            type=EscalationRequestType.ESCALATION,
            title="Test escalation",
            context="Worker needs help",
        )
        assert item.type == EscalationRequestType.ESCALATION
        assert item.title == "Test escalation"
        assert item.context == "Worker needs help"

    def test_default_priority(self) -> None:
        assert _column_default(DirectorQueueItem, "priority") == EscalationPriority.NORMAL

    def test_default_status(self) -> None:
        assert _column_default(DirectorQueueItem, "status") == DirectorQueueStatus.PENDING

    def test_default_metadata(self) -> None:
        default = _column_default(DirectorQueueItem, "metadata_")
        assert callable(default) and default(None) == {}

    def test_tablename(self) -> None:
        assert DirectorQueueItem.__tablename__ == "director_queue"


class TestProjectConfig:
    def test_instantiate_with_required_fields(self) -> None:
        cfg = ProjectConfig(project_name="my-project")
        assert cfg.project_name == "my-project"

    def test_default_active(self) -> None:
        assert _column_default(ProjectConfig, "active") is True

    def test_default_config(self) -> None:
        default = _column_default(ProjectConfig, "config")
        assert callable(default) and default(None) == {}

    def test_custom_config(self) -> None:
        cfg = ProjectConfig(
            project_name="my-project",
            config={"key": "value"},
        )
        assert cfg.config == {"key": "value"}

    def test_tablename(self) -> None:
        assert ProjectConfig.__tablename__ == "project_configs"


class TestCeoQueueStatusEnum:
    def test_has_all_values(self) -> None:
        expected = {"PENDING", "SEEN", "RESOLVED", "DISMISSED"}
        actual = {s.value for s in CeoQueueStatus}
        assert actual == expected

    def test_values_match_names(self) -> None:
        for member in CeoQueueStatus:
            assert member.name == member.value
