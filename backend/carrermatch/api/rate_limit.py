"""Rate limiting por IP — janela deslizante em memória (seg. v2 §4.3, gate de go-live #1).

Escolha: implementação própria (~50 linhas) em vez de slowapi — sem dependência
extra e sem decorator que exige `request` na assinatura. Limitação conhecida: o
estado é por processo. Com mais de uma réplica, migrar para Redis/Postgres.

IP do cliente: `request.client.host`. Atrás de proxy (Railway/Fly), rodar o
uvicorn com `--proxy-headers --forwarded-allow-ips=<ip do proxy>` para que esse
valor venha do X-Forwarded-For confiável — nunca ler o header diretamente.
"""

from __future__ import annotations

import math
import re
import threading
import time
from collections import deque
from collections.abc import Callable

from fastapi import HTTPException, Request, status

_UNITS = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}
_MAX_KEYS = 50_000  # proteção de memória contra varredura de IPs


def parse_limits(spec: str) -> list[tuple[int, int]]:
    """"10/minute;50/hour" → [(10, 60), (50, 3600)]."""
    limits = []
    for part in filter(None, (p.strip() for p in spec.split(";"))):
        m = re.fullmatch(r"(\d+)\s*/\s*(second|minute|hour|day)", part)
        if not m:
            raise ValueError(f"limite inválido: {part!r}")
        limits.append((int(m.group(1)), _UNITS[m.group(2)]))
    return limits


class SlidingWindowLimiter:
    def __init__(self, spec: str, clock: Callable[[], float] = time.monotonic) -> None:
        self.limits = parse_limits(spec)
        self._window = max(w for _, w in self.limits)
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()
        self._clock = clock

    def hit(self, key: str) -> int | None:
        """Registra uma requisição. Retorna None se permitida, ou segundos até liberar."""
        now = self._clock()
        with self._lock:
            hits = self._hits.get(key)
            if hits is None:
                if len(self._hits) >= _MAX_KEYS:
                    self._evict(now)
                hits = self._hits[key] = deque()
            while hits and now - hits[0] >= self._window:
                hits.popleft()
            for count, window in self.limits:
                recent = [t for t in hits if now - t < window]
                if len(recent) >= count:
                    return max(1, math.ceil(window - (now - recent[0])))
            hits.append(now)
            return None

    def _evict(self, now: float) -> None:
        stale = [k for k, d in self._hits.items() if not d or now - d[-1] >= self._window]
        for k in stale:
            del self._hits[k]
        if len(self._hits) >= _MAX_KEYS:  # ainda cheio: descarta os mais antigos
            for k in sorted(self._hits, key=lambda k: self._hits[k][-1])[: _MAX_KEYS // 10]:
                del self._hits[k]


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "desconhecido"


def rate_limit(name: str) -> Callable[[Request], None]:
    """Dependency: `Depends(rate_limit("recommendations"))`. O limiter vive em app.state.limiters."""

    def dependency(request: Request) -> None:
        limiter: SlidingWindowLimiter = request.app.state.limiters[name]
        retry_after = limiter.hit(client_ip(request))
        if retry_after is not None:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Muitas solicitações em pouco tempo. Aguarde um instante e tente novamente.",
                headers={"Retry-After": str(retry_after)},
            )

    return dependency
