"""Custom agent implementations — register all in CLASS_REGISTRY on import."""

from __future__ import annotations

from app.agents._registry import register_custom_agent
from app.agents.custom.dependency_resolver import DependencyResolverAgent
from app.agents.custom.diagnostics import DiagnosticsAgent
from app.agents.custom.formatter import FormatterAgent
from app.agents.custom.linter import LinterAgent
from app.agents.custom.memory_loader import MemoryLoaderAgent
from app.agents.custom.regression_tester import RegressionTestAgent
from app.agents.custom.review_cycle import ReviewCycleAgent
from app.agents.custom.skill_loader import SkillLoaderAgent
from app.agents.custom.test_runner import TestRunnerAgent

register_custom_agent("SkillLoaderAgent", SkillLoaderAgent)
register_custom_agent("MemoryLoaderAgent", MemoryLoaderAgent)
register_custom_agent("LinterAgent", LinterAgent)
register_custom_agent("TestRunnerAgent", TestRunnerAgent)
register_custom_agent("FormatterAgent", FormatterAgent)
register_custom_agent("RegressionTestAgent", RegressionTestAgent)
register_custom_agent("DependencyResolverAgent", DependencyResolverAgent)
register_custom_agent("DiagnosticsAgent", DiagnosticsAgent)
register_custom_agent("ReviewCycleAgent", ReviewCycleAgent)

__all__ = [
    "DependencyResolverAgent",
    "DiagnosticsAgent",
    "FormatterAgent",
    "LinterAgent",
    "MemoryLoaderAgent",
    "RegressionTestAgent",
    "ReviewCycleAgent",
    "SkillLoaderAgent",
    "TestRunnerAgent",
]
