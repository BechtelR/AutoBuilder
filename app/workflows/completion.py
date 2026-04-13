"""Three-layer completion report generation backed by DB validator evidence.

Reports are generated at TaskGroup and Stage boundaries.  Each layer collects
machine evidence from persisted ValidatorResult rows — assertion without evidence
is marked unverified, not passing.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import select

from app.db.models import (
    StageExecution,
    TaskGroupExecution,
)
from app.db.models import (
    ValidatorResult as ValidatorResultModel,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# ---------------------------------------------------------------------------
# Layer status constants (avoid magic strings per common-errors.md)
# ---------------------------------------------------------------------------

LAYER_PASS = "pass"
LAYER_FAIL = "fail"
LAYER_UNVERIFIED = "unverified"

# ---------------------------------------------------------------------------
# Layer-to-validator-name mapping (mirrors DEFAULT_VERIFICATION_LAYERS)
# ---------------------------------------------------------------------------

_FUNCTIONAL_VALIDATORS: frozenset[str] = frozenset(
    {"lint_check", "test_suite", "regression_tests", "integration_tests"}
)
_ARCHITECTURAL_VALIDATORS: frozenset[str] = frozenset({"code_review", "architecture_conformance"})
_CONTRACT_VALIDATORS: frozenset[str] = frozenset(
    {"deliverable_status_check", "dependency_validation"}
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _layer_status(rows: list[ValidatorResultModel]) -> str:
    """Return LAYER_PASS, LAYER_FAIL, or LAYER_UNVERIFIED for a set of validator rows."""
    if not rows:
        return LAYER_UNVERIFIED
    return LAYER_PASS if all(r.passed for r in rows) else LAYER_FAIL


def _layer_evidence(rows: list[ValidatorResultModel]) -> list[dict[str, object]]:
    return [
        {
            "validator": r.validator_name,
            "passed": r.passed,
            "message": r.message or "",
            "evidence": r.evidence or {},
            "evaluated_at": r.evaluated_at.isoformat() if r.evaluated_at else None,
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# CompletionReportBuilder
# ---------------------------------------------------------------------------


class CompletionReportBuilder:
    """Builds three-layer completion reports from DB-persisted validator evidence."""

    def __init__(self, db_session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._db_session_factory = db_session_factory

    async def build_taskgroup_report(
        self,
        taskgroup_execution_id: uuid.UUID,
        workflow_id: uuid.UUID,
        stage_execution_id: uuid.UUID,
        *,
        cost: Decimal = Decimal("0"),
        duration_seconds: float = 0.0,
    ) -> dict[str, object]:
        """Generate a TaskGroup completion report with three verification layers.

        Each layer contains machine evidence from ValidatorResult rows scoped to
        the workflow and stage_execution.  Layers without evidence are marked
        'unverified' — assertion without evidence never passes.

        Returns a plain dict for direct storage in the JSONB column.
        """
        async with self._db_session_factory() as db:
            functional = await self._build_functional_layer(db, workflow_id, stage_execution_id)
            architectural = await self._build_architectural_layer(
                db, workflow_id, stage_execution_id
            )
            contract = await self._build_contract_layer(db, workflow_id, stage_execution_id)

        all_layers_pass = (
            functional["status"] == LAYER_PASS
            and architectural["status"] == LAYER_PASS
            and contract["status"] == LAYER_PASS
        )

        return {
            "type": "taskgroup",
            "taskgroup_execution_id": str(taskgroup_execution_id),
            "stage_execution_id": str(stage_execution_id),
            "workflow_id": str(workflow_id),
            "generated_at": datetime.now(UTC).isoformat(),
            "layers": {
                "functional_correctness": functional,
                "architectural_conformance": architectural,
                "contract_completion": contract,
            },
            "metrics": {
                "cost": str(cost),
                "duration_seconds": duration_seconds,
            },
            "all_layers_pass": all_layers_pass,
        }

    async def build_stage_report(
        self,
        stage_execution_id: uuid.UUID,
        workflow_id: uuid.UUID,
        *,
        cost: Decimal = Decimal("0"),
        duration_seconds: float = 0.0,
    ) -> dict[str, object]:
        """Generate a Stage completion report aggregating all TaskGroup reports.

        Reads completion_report JSONB from every TaskGroupExecution in the stage.
        If any TaskGroup is missing a report or has a failing report, the stage
        is marked as not passing.
        """
        async with self._db_session_factory() as db:
            stmt = select(TaskGroupExecution).where(
                TaskGroupExecution.stage_execution_id == stage_execution_id
            )
            taskgroups: list[TaskGroupExecution] = list((await db.execute(stmt)).scalars().all())

        tg_reports: list[dict[str, object]] = []
        all_pass = True

        for tg in taskgroups:
            if tg.completion_report:
                report = tg.completion_report
                tg_reports.append(report)
                if not report.get("all_layers_pass", False):
                    all_pass = False
            else:
                all_pass = False
                tg_reports.append(
                    {
                        "status": "missing",
                        "taskgroup_execution_id": str(tg.id),
                    }
                )

        return {
            "type": "stage",
            "stage_execution_id": str(stage_execution_id),
            "workflow_id": str(workflow_id),
            "generated_at": datetime.now(UTC).isoformat(),
            "taskgroup_reports": tg_reports,
            "all_layers_pass": all_pass,
            "metrics": {
                "cost": str(cost),
                "duration_seconds": duration_seconds,
                "taskgroup_count": len(tg_reports),
            },
        }

    # ------------------------------------------------------------------
    # Private layer builders
    # ------------------------------------------------------------------

    async def _load_validator_rows(
        self,
        db: AsyncSession,
        workflow_id: uuid.UUID,
        stage_execution_id: uuid.UUID,
        names: frozenset[str],
    ) -> list[ValidatorResultModel]:
        stmt = select(ValidatorResultModel).where(
            ValidatorResultModel.workflow_id == workflow_id,
            ValidatorResultModel.stage_execution_id == stage_execution_id,
            ValidatorResultModel.validator_name.in_(list(names)),
        )
        return list((await db.execute(stmt)).scalars().all())

    async def _build_functional_layer(
        self,
        db: AsyncSession,
        workflow_id: uuid.UUID,
        stage_execution_id: uuid.UUID,
    ) -> dict[str, object]:
        """Layer 1: Functional correctness — lint, tests, integration."""
        rows = await self._load_validator_rows(
            db, workflow_id, stage_execution_id, _FUNCTIONAL_VALIDATORS
        )
        status = _layer_status(rows)
        result: dict[str, object] = {"status": status, "evidence": _layer_evidence(rows)}
        if status == LAYER_UNVERIFIED:
            result["message"] = "No functional validator results found"
        return result

    async def _build_architectural_layer(
        self,
        db: AsyncSession,
        workflow_id: uuid.UUID,
        stage_execution_id: uuid.UUID,
    ) -> dict[str, object]:
        """Layer 2: Architectural conformance — code review, architecture check."""
        rows = await self._load_validator_rows(
            db, workflow_id, stage_execution_id, _ARCHITECTURAL_VALIDATORS
        )
        status = _layer_status(rows)
        result: dict[str, object] = {"status": status, "evidence": _layer_evidence(rows)}
        if status == LAYER_UNVERIFIED:
            result["message"] = "No architectural validator results found"
        return result

    async def _build_contract_layer(
        self,
        db: AsyncSession,
        workflow_id: uuid.UUID,
        stage_execution_id: uuid.UUID,
    ) -> dict[str, object]:
        """Layer 3: Contract completion — deliverable status check, dependency validation."""
        rows = await self._load_validator_rows(
            db, workflow_id, stage_execution_id, _CONTRACT_VALIDATORS
        )
        status = _layer_status(rows)
        result: dict[str, object] = {"status": status, "evidence": _layer_evidence(rows)}
        if status == LAYER_UNVERIFIED:
            result["message"] = "No contract validator results found"
        return result


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------


async def store_taskgroup_report(
    db_session_factory: async_sessionmaker[AsyncSession],
    taskgroup_execution_id: uuid.UUID,
    report: dict[str, object],
) -> None:
    """Persist a completion report into TaskGroupExecution.completion_report JSONB.

    Raises ``ValueError`` if the TaskGroupExecution row does not exist — pipeline
    state is inconsistent and the caller must handle it.
    """
    async with db_session_factory() as db:
        stmt = select(TaskGroupExecution).where(TaskGroupExecution.id == taskgroup_execution_id)
        tge = (await db.execute(stmt)).scalar_one_or_none()
        if tge is None:
            msg = f"TaskGroupExecution {taskgroup_execution_id} not found"
            raise ValueError(msg)
        tge.completion_report = report
        await db.commit()


async def store_stage_report(
    db_session_factory: async_sessionmaker[AsyncSession],
    stage_execution_id: uuid.UUID,
    report: dict[str, object],
) -> None:
    """Persist a completion report into StageExecution.completion_report JSONB.

    Raises ``ValueError`` if the StageExecution row does not exist — pipeline
    state is inconsistent and the caller must handle it.
    """
    async with db_session_factory() as db:
        stmt = select(StageExecution).where(StageExecution.id == stage_execution_id)
        se = (await db.execute(stmt)).scalar_one_or_none()
        if se is None:
            msg = f"StageExecution {stage_execution_id} not found"
            raise ValueError(msg)
        se.completion_report = report
        await db.commit()
