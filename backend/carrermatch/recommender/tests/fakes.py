"""Dublês da Claude API para testes offline (nenhuma chamada real, nenhum custo)."""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any

WORDS_120 = " ".join(["palavra"] * 120)


def _response(text: str, stop_reason: str = "end_turn") -> SimpleNamespace:
    return SimpleNamespace(
        stop_reason=stop_reason,
        content=[SimpleNamespace(type="text", text=text)],
        _request_id="req_fake",
    )


@dataclass
class FakeMessages:
    mode: str = "ok"               # ok | refusal | invalid_json | short | error | slow | wrong_ids
    error: Exception | None = None
    delay_s: float = 0.0
    calls: list[dict[str, Any]] = field(default_factory=list)

    async def create(self, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(kwargs)
        if self.delay_s:
            await asyncio.sleep(self.delay_s)
        if self.mode == "error" and self.error is not None:
            raise self.error
        prompt = kwargs["messages"][0]["content"]
        ids = [int(i) for i in re.findall(r'"id": (\d+)', prompt)]
        if self.mode == "refusal":
            return _response("", stop_reason="refusal")
        if self.mode == "invalid_json":
            return _response("isto não é json")
        if self.mode == "wrong_ids":
            ids = [i + 100 for i in ids]
        text = "curta demais" if self.mode == "short" else f"<b>Você</b> combina experiências. {WORDS_120}"
        return _response(json.dumps({"paths": [{"id": i, "description": text} for i in ids]}, ensure_ascii=False))


class FakeAnthropic:
    def __init__(self, **kwargs: Any) -> None:
        self.messages = FakeMessages(**kwargs)

    async def close(self) -> None:
        pass
