"""Mentoria (PRD §6.4): matching por user-based CF + solicitação de contato. Exige login (RN-08)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status

from carrermatch.api.auth import AuthUser, require_auth
from carrermatch.api.deps import AppServices, get_services
from carrermatch.api.rate_limit import rate_limit
from carrermatch.api.schemas.mentor_schema import (
    MentorContactRequest,
    MentorContactResponse,
    MentorMatchRequest,
    MentorMatchResponse,
    MentorOut,
)
from carrermatch.recommender.engines.vectors import user_vector
from carrermatch.recommender.repositories.account_repo import (
    DuplicateRequestError,
    MentorRequest,
    MentorUnavailableError,
)

router = APIRouter(tags=["mentoria"])

NO_PROFILE_MSG = (
    "Para encontrar mentores, precisamos das suas experiências: gere seus caminhos com o consentimento "
    "de salvamento ativado ou envie as experiências junto com a busca."
)


def _require_accounts(services: AppServices) -> None:
    if services.accounts is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Mentoria temporariamente indisponível.")


@router.post("/mentor-matches", response_model=MentorMatchResponse, dependencies=[Depends(rate_limit("mentor_search"))])
async def find_mentors(
    body: MentorMatchRequest,
    user: AuthUser = Depends(require_auth),
    services: AppServices = Depends(get_services),
) -> MentorMatchResponse:
    _require_accounts(services)
    pipeline = services.pipeline
    assert pipeline is not None and services.accounts is not None
    role = pipeline.role(body.role_id)
    if role is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Caminho de carreira não encontrado.")

    if body.experiences:
        mentee = user_vector(pipeline.build_profile(body.experiences))
    else:
        mentee = await services.accounts.user_skills(user.id) or {}
    if not mentee:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=NO_PROFILE_MSG)

    mentors = await services.accounts.list_available_mentors()
    matches = services.mentor_matcher.match(mentee, role, mentors)
    return MentorMatchResponse(
        role_id=role.id,
        mentors=[
            MentorOut(
                mentor_id=m.mentor.id,
                display_name=m.mentor.display_name,
                headline=m.mentor.headline,
                similarity_score=m.similarity_score,
                match_reasons=[pipeline.skill_names.get(s, "") for s in m.reason_skill_ids],
            )
            for m in matches
        ],
    )


@router.post(
    "/mentor-matches/{mentor_id}/requests",
    response_model=MentorContactResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("mentor_requests"))],
)
async def request_mentoring(
    mentor_id: UUID,
    body: MentorContactRequest,
    user: AuthUser = Depends(require_auth),
    services: AppServices = Depends(get_services),
    x_session_id: UUID | None = Header(default=None),
) -> MentorContactResponse:
    _require_accounts(services)
    pipeline = services.pipeline
    assert pipeline is not None and services.accounts is not None
    role = pipeline.role(body.role_id)
    if role is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Caminho de carreira não encontrado.")

    # a pontuação gravada é a do matching atual — não confiamos em score vindo do cliente
    mentee = await services.accounts.user_skills(user.id) or {}
    mentors = await services.accounts.list_available_mentors()
    match = next((m for m in services.mentor_matcher.match(mentee, role, mentors, k=len(mentors) or 1)
                  if m.mentor.id == mentor_id), None)
    if match is None and not any(m.id == mentor_id for m in mentors):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Mentor(a) indisponível no momento.")

    try:
        match_id = await services.accounts.create_request(
            MentorRequest(
                mentee_auth_id=user.id,
                mentee_email=user.email,
                mentor_id=mentor_id,
                role_id=role.id,
                similarity_score=match.similarity_score if match else 0.0,
                message=body.message,
            )
        )
    except MentorUnavailableError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Mentor(a) indisponível no momento.") from None
    except DuplicateRequestError:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="Você já tem uma solicitação pendente com essa pessoa. Aguarde a resposta."
        ) from None

    await services.notifier.notify_mentor_request(match_id)
    if x_session_id is not None:
        await services.events.log(
            "mentor_contacted", session_id=x_session_id, user_auth_id=user.id, role_id=role.id,
            payload={"engagement_weight": 1.0},
        )
    return MentorContactResponse(match_id=match_id)
