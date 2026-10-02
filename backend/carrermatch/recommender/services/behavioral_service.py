"""BehavioralEventCollector — registra todo evento em `behavioral_events` (RN-10).

Regras:
- falha ao gravar evento NUNCA quebra a requisição do usuário (log e segue);
- payload sem texto livre do usuário: só ids, contagens e métricas (minimização, LGPD);
- pesos de engajamento (TRD §9) ficam aqui para alimentar `recommendation_feedback`
  quando a recomendação estiver persistida (usuário autenticado).
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from carrermatch.recommender.repositories.write_repo import BehavioralEvent, EventRepository

log = logging.getLogger("carrermatch.events")

ENGAGEMENT_WEIGHTS: dict[str, float] = {
    "recommendation_viewed": 0.1,
    "career_expanded": 0.3,
    "career_saved": 0.7,
    "mentor_contacted": 1.0,
    "rated_positive": 0.8,
    "rated_negative": -0.5,
    "dismissed": -0.3,
}
SERVER_EVENTS = {"recommendation_generated", "recommendation_failed", "mentor_contacted"}
# eventos que o frontend pode enviar por POST /events
CLIENT_EVENTS = set(ENGAGEMENT_WEIGHTS) - SERVER_EVENTS
_MAX_PAYLOAD_KEYS = 20


class BehavioralEventCollector:
    def __init__(self, repo: EventRepository) -> None:
        self._repo = repo

    async def log(
        self,
        event_type: str,
        *,
        session_id: UUID,
        user_auth_id: UUID | None = None,
        request_id: UUID | None = None,
        role_id: int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> bool:
        if event_type not in CLIENT_EVENTS | SERVER_EVENTS:
            raise ValueError(f"event_type desconhecido: {event_type}")
        clean = {k: v for k, v in (payload or {}).items() if isinstance(v, (int, float, bool)) or _is_id_list(v)}
        clean = dict(list(clean.items())[:_MAX_PAYLOAD_KEYS])
        try:
            await self._repo.insert(
                BehavioralEvent(event_type, session_id, user_auth_id, request_id, role_id, clean)
            )
            return True
        except Exception:  # noqa: BLE001 — telemetria nunca derruba a requisição
            log.exception("falha ao registrar evento %s", event_type)
            return False


def _is_id_list(value: Any) -> bool:
    return isinstance(value, list) and len(value) <= 50 and all(isinstance(x, int) for x in value)
