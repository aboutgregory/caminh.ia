"""POST /recommendations — fluxo principal (TRD §5).

experiências → HybridPipeline (seleção, 6–21) → Claude (descrições) → resposta.
Sem login: resultado imediato (RN-06). Com login + consentimento: persiste (RN-07).
"""

from __future__ import annotations

import logging
import time
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, status

from carrermatch.api.auth import AuthUser, get_current_user
from carrermatch.api.deps import AppServices, get_services
from carrermatch.api.rate_limit import rate_limit
from carrermatch.api.schemas.recommendation_schema import CareerPathOut, RecommendationRequest, RecommendationResponse
from carrermatch.recommender.engines.hybrid import InsufficientPathsError, NoSkillsDetectedError
from carrermatch.recommender.repositories.write_repo import build_saved

log = logging.getLogger("carrermatch.recommendations")
router = APIRouter(tags=["recomendações"])

PIPELINE_VERSION = "hybrid-v1"
NO_SKILLS_MSG = (
    "Não conseguimos identificar habilidades nas suas experiências. Conte com mais detalhes o que você fez "
    "e o que isso te ensinou — por exemplo, ferramentas, responsabilidades ou desafios."
)
TOO_FEW_MSG = (
    "Ainda não encontramos caminhos suficientes para o seu perfil. Tente detalhar mais suas experiências "
    "ou incluir outras vivências, inclusive pessoais."
)


@router.post(
    "/recommendations",
    response_model=RecommendationResponse,
    dependencies=[Depends(rate_limit("recommendations"))],
)
async def create_recommendations(
    body: RecommendationRequest,
    services: AppServices = Depends(get_services),
    user: AuthUser | None = Depends(get_current_user),
    x_session_id: UUID | None = Header(default=None),
) -> RecommendationResponse:
    started = time.perf_counter()
    session_id = x_session_id or uuid4()
    request_id = uuid4()
    pipeline, claude = services.pipeline, services.claude
    assert pipeline is not None and claude is not None  # garantido por get_services

    profile = pipeline.build_profile(body.experiences, body.risk_tolerance)
    try:
        paths = pipeline.recommend(profile)
    except InsufficientPathsError as exc:  # RN-05 (inclui NoSkillsDetectedError)
        await services.events.log(
            "recommendation_failed", session_id=session_id, user_auth_id=user.id if user else None,
            request_id=request_id, payload={"found": exc.found},
        )
        msg = NO_SKILLS_MSG if isinstance(exc, NoSkillsDetectedError) else TOO_FEW_MSG
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=msg) from None

    described = await claude.describe(body.experiences, paths)
    model_version = f"{PIPELINE_VERSION}+{claude.model_version}"

    saved = False
    if user is not None and body.consent_data and services.store is not None:
        try:
            await services.store.save(build_saved(
                user_auth_id=user.id, email=user.email, request_id=request_id, profile=profile,
                paths=paths, descriptions=described.descriptions, model_version=model_version,
            ))
            saved = True
        except Exception:  # noqa: BLE001 — o usuário recebe o resultado mesmo se o salvamento falhar
            log.exception("falha ao salvar recomendações (request_id=%s)", request_id)

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    await services.events.log(
        "recommendation_generated", session_id=session_id, user_auth_id=user.id if user else None,
        request_id=request_id,
        payload={
            "n_paths": len(paths), "role_ids": [p.role.id for p in paths], "latency_ms": elapsed_ms,
            "fallback_descriptions": described.fallback_count, "saved": saved,
        },
    )

    return RecommendationResponse(
        request_id=request_id,
        model_version=model_version,
        generated_in_ms=elapsed_ms,
        saved=saved,
        paths=[
            CareerPathOut(
                id=rank,
                role_slug=p.role.slug,
                title=p.role.title,
                description=described.descriptions[rank],
                description_source=described.sources[rank],
                key_skills=[pipeline.skill_names.get(s, "") for s in p.key_skill_ids],
                relevance=p.relevance_stars,
                confidence_score=p.confidence_score,
                market_trend=p.role.market_trend.label,
                industries=[pipeline.sector_names.get(s, "") for s in p.industry_ids],
                is_hybrid=p.role.is_hybrid,
                source=p.source.value,
            )
            for rank, p in enumerate(paths, 1)
        ],
    )
