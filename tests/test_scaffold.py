"""Smoke tests verifying the project scaffold is correctly set up."""


def test_models_importable() -> None:
    """Verify shared domain models are importable."""
    from app.models import AgentRole, DeliverableStatus, WorkflowStatus

    assert WorkflowStatus.RUNNING.value == "RUNNING"
    assert DeliverableStatus.IN_PROGRESS.value == "IN_PROGRESS"
    assert AgentRole.CODER.value == "CODER"


def test_config_importable() -> None:
    """Verify configuration module is importable and returns defaults."""
    from app.config import get_settings

    settings = get_settings()
    assert "autobuilder" in settings.db_url
    assert settings.redis_url == "redis://localhost:6379"
    assert settings.log_level == "INFO"


def test_base_model() -> None:
    """Verify BaseModel has from_attributes enabled."""
    from app.models.base import BaseModel

    assert BaseModel.model_config.get("from_attributes") is True
