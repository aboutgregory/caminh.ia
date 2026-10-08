"""Serviços da aplicação, montados no lifespan e expostos às rotas via app.state."""

from __future__ import annotations

from dataclasses import dataclass, field

from fastapi import HTTPException, Request, status

from carrermatch.recommender.engines.hybrid import HybridPipeline
from carrermatch.recommender.engines.mentor_matcher import MentorMatcher
from carrermatch.recommender.repositories.account_repo import AccountStore
from carrermatch.recommender.repositories.write_repo import RecommendationStore
from carrermatch.recommender.services.account_services import (
    AuthAdmin,
    LoggingNotifier,
    MentorNotifier,
    NullAuthAdmin,
)
from carrermatch.recommender.services.behavioral_service import BehavioralEventCollector
from carrermatch.recommender.services.claude_service import ClaudeDescriptionService


@dataclass(slots=True)
class AppServices:
    pipeline: HybridPipeline | None
    claude: ClaudeDescriptionService | None
    events: BehavioralEventCollector
    store: RecommendationStore | None   # None = sem banco: nada é persistido
    # sprint 3 — mentoria e LGPD. `accounts` implementa MentorRepository + AccountRepository
    accounts: AccountStore | None = None
    mentor_matcher: MentorMatcher = field(default_factory=lambda: MentorMatcher({}))
    auth_admin: AuthAdmin = field(default_factory=NullAuthAdmin)
    notifier: MentorNotifier = field(default_factory=LoggingNotifier)


def get_services(request: Request) -> AppServices:
    services: AppServices | None = getattr(request.app.state, "services", None)
    if services is None or services.pipeline is None or services.claude is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Serviço temporariamente indisponível.")
    return services
