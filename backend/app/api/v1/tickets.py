"""Support Ticket and Feedback API routes."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.ticket import (
    FeedbackCreate,
    FeedbackResponse,
    TicketCreate,
    TicketListResponse,
    TicketResponse,
)
from app.services.feedback_service import FeedbackService
from app.services.ticket_service import TicketService

router = APIRouter(prefix="/tickets", tags=["Tickets"])


@router.get("", response_model=TicketListResponse)
async def list_tickets(
    status: Optional[str] = Query(None, description="Filter by status: open, drafted, resolved, escalated"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List support tickets with pagination and status filtering."""
    service = TicketService(db)
    items, total = await service.list_tickets(status=status, page=page, size=size)
    return TicketListResponse(
        items=[TicketResponse.model_validate(t) for t in items],
        total=total,
        page=page,
        size=size,
    )


@router.post("", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    data: TicketCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new incoming customer support ticket."""
    service = TicketService(db)
    ticket = await service.create_ticket(data)
    await db.commit()
    await db.refresh(ticket)
    return TicketResponse.model_validate(ticket)


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve details for a specific ticket."""
    service = TicketService(db)
    ticket = await service.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket '{ticket_id}' not found.")
    return TicketResponse.model_validate(ticket)


@router.post("/{ticket_id}/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    ticket_id: str,
    data: FeedbackCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Record human support agent feedback (Approve, Edit & Send, Escalate, Reject)."""
    service = FeedbackService(db)
    try:
        feedback = await service.record_feedback(
            ticket_id=ticket_id,
            data=data,
            user_id=current_user.id,
        )
        return FeedbackResponse.model_validate(feedback)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

