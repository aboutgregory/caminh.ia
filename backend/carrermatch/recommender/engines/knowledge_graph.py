"""KnowledgeGraphEngine — caminhos validados por transições reais de carreira.

1. âncoras: os cargos com que o perfil do usuário JÁ se parece (cosseno direto,
   sem expansão), acima de um piso.
2. a partir das âncoras, percorre `career_transitions` até MAX_HOPS saltos.
   força de um caminho = afinidade com a âncora × Π força das arestas × decaimento.
3. força da aresta = confidence ajustada pelo suporte (observed_count) e pela
   fração das habilidades-ponte que o usuário já tem.

O grafo é carregado em memória (ADR-03 prevê CTE recursiva; com ~300 arestas a
travessia em Python é mais simples e igualmente rápida. Rever acima de ~50k).
"""

from __future__ import annotations

import heapq
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from carrermatch.recommender.models.domain import CareerTransition

MAX_HOPS = 2
HOP_DECAY = 0.75          # cada salto extra vale menos
ANCHOR_FLOOR = 0.15       # afinidade mínima para um cargo virar âncora
MAX_ANCHORS = 6
BRIDGE_BONUS = 0.3        # até +30% na aresta se o usuário tem todas as habilidades-ponte


@dataclass(frozen=True, slots=True)
class GraphPath:
    target_role_id: int
    strength: float
    role_ids: tuple[int, ...]   # âncora → ... → alvo
    bridge_skill_ids: tuple[int, ...]


class KnowledgeGraphEngine:
    def __init__(self, transitions: Sequence[CareerTransition]) -> None:
        self._out: dict[int, list[CareerTransition]] = {}
        for t in transitions:
            self._out.setdefault(t.from_role_id, []).append(t)
        self._max_log_count = math.log1p(max((t.observed_count for t in transitions), default=1))

    def edge_strength(self, t: CareerTransition, user_skills: Mapping[int, float]) -> float:
        support = math.log1p(t.observed_count) / self._max_log_count if self._max_log_count else 0.0
        strength = t.confidence * (0.7 + 0.3 * support)
        if t.bridge_skill_ids:
            owned = sum(1 for s in t.bridge_skill_ids if s in user_skills) / len(t.bridge_skill_ids)
            strength *= 1 + BRIDGE_BONUS * owned
        return min(1.0, strength)

    def anchors(self, affinity: Mapping[int, float]) -> list[tuple[int, float]]:
        ranked = sorted(((r, a) for r, a in affinity.items() if a >= ANCHOR_FLOOR), key=lambda x: -x[1])
        return ranked[:MAX_ANCHORS]

    def explore(self, affinity: Mapping[int, float], user_skills: Mapping[int, float]) -> dict[int, GraphPath]:
        """Melhor caminho até cada cargo alcançável a partir das âncoras.

        affinity: role_id -> cosseno direto perfil×cargo (do ItemBasedRecommender, sem expansão).
        """
        best: dict[int, GraphPath] = {}
        # busca do melhor caminho (max-produto) com heap; forças em [0,1] só decrescem
        heap: list[tuple[float, int, tuple[int, ...], tuple[int, ...]]] = []
        for role_id, aff in self.anchors(affinity):
            heapq.heappush(heap, (-aff, role_id, (role_id,), ()))

        settled: set[tuple[int, int]] = set()  # (role, hops) já expandidos
        while heap:
            neg, role_id, path, bridges = heapq.heappop(heap)
            strength = -neg
            hops = len(path) - 1
            if (role_id, hops) in settled:
                continue
            settled.add((role_id, hops))
            if hops > 0 and (role_id not in best or strength > best[role_id].strength):
                best[role_id] = GraphPath(role_id, strength, path, bridges)
            if hops >= MAX_HOPS:
                continue
            for t in self._out.get(role_id, ()):
                if t.to_role_id in path:
                    continue
                decay = 1.0 if hops == 0 else HOP_DECAY
                nxt = strength * self.edge_strength(t, user_skills) * decay
                heapq.heappush(heap, (-nxt, t.to_role_id, (*path, t.to_role_id), t.bridge_skill_ids))
        return best
