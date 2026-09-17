"""Evaluation dashboard and run management API routes."""

import asyncio
from typing import List
from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user, get_db, require_admin
from app.models.user import User
from app.schemas.evaluation import EvalRunResponse, EvalSummaryResponse
from app.services.evaluation_service import EvaluationService

router = APIRouter(prefix="/evaluation", tags=["Evaluation"])


@router.get("/latest", response_model=EvalSummaryResponse)
async def get_latest_evaluation_summary(db: AsyncSession = Depends(get_db)):
    """Fetch latest benchmark metrics, baseline comparisons, and judge agreement."""
    service = EvaluationService(db)
    return await service.get_latest_summary()


@router.get("/runs", response_model=List[EvalRunResponse])
async def list_evaluation_runs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """List historical evaluation runs (Admin only)."""
    service = EvaluationService(db)
    runs = await service.list_runs()
    return [EvalRunResponse.model_validate(r) for r in runs]


@router.post("/runs", status_code=status.HTTP_202_ACCEPTED)
async def trigger_evaluation_run(
    background_tasks: BackgroundTasks,
    smoke: bool = False,
    current_user: User = Depends(require_admin),
):
    """Trigger an asynchronous golden-set evaluation run (Admin only)."""
    from app.eval.run import run_evaluation

    background_tasks.add_task(run_evaluation, smoke_test=smoke)
    return {"message": "Evaluation run initiated in background.", "smoke_test": smoke}

