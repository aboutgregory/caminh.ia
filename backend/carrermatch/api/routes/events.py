"""POST /events — eventos comportamentais enviados pelo frontend (RN-10, TRD §9)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, status
from fastapi.responses import Response

from carrermatch.api.auth import AuthUser, get_current_user
from carrermatch.api.rate_limit import rate_limit
from carrermatch.api.schemas.recommendation_schema import EventIn
from carrermatch.recommender.services.behavioral_service import ENGAGEMENT_WEIGHTS

router = APIRouter(tags=["eventos"])


@router.post("/events", status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(rate_limit("events"))])
async def track_event(
    body: EventIn,
    request: Request,
    x_session_id: UUID = Header(),
    user: AuthUser | None = Depends(get_current_user),
) -> Response:
    payload: dict[str, int | float] = {"engagement_weight": ENGAGEMENT_WEIGHTS[body.event_type]}
    if body.rating is not None:
        payload["rating"] = body.rating
    if body.reading_time_ms is not None:
        payload["reading_time_ms"] = body.reading_time_ms
    await request.app.state.services.events.log(
        body.event_type, session_id=x_session_id, user_auth_id=user.id if user else None,
        request_id=body.request_id, role_id=body.role_id, payload=payload,
    )
    return Response(status_code=status.HTTP_202_ACCEPTED)
