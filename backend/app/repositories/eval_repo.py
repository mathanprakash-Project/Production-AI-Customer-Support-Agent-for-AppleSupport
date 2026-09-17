"""Evaluation Repository for benchmark runs and metric history."""

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.eval_run import EvalRun
from app.repositories.base import BaseRepository


class EvalRepository(BaseRepository[EvalRun]):
    def __init__(self, db: AsyncSession):
        super().__init__(EvalRun, db)

    async def get_latest_run(self) -> Optional[EvalRun]:
        stmt = select(EvalRun).order_by(EvalRun.started_at.desc()).limit(1)
        return (await self.db.execute(stmt)).scalars().first()

    async def list_runs(self, limit: int = 20) -> List[EvalRun]:
        stmt = select(EvalRun).order_by(EvalRun.started_at.desc()).limit(limit)
        return list((await self.db.execute(stmt)).scalars().all())

