"""MCP server: Claude Code -> Antigravity (Gemini).

Envolve a CLI `agentapi` do Antigravity. A CLI exige ANTIGRAVITY_LS_ADDRESS e um
token CSRF, que só existem nos terminais do Antigravity aberto. Handshake:
o agente do Antigravity grava as variáveis ANTIGRAVITY_* em
.collab/antigravity_env.json ao iniciar a sessão (ver .collab/PROTOCOL.md).

Registrado em .mcp.json na raiz do repositório.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from mcp.server.mcpserver import MCPServer

REPO = Path(__file__).resolve().parents[2]
COLLAB = REPO / ".collab"
ADDRESS_FILE = COLLAB / "antigravity_ls_address"   # legado
ENV_FILE = COLLAB / "antigravity_env.json"
AGENTAPI = Path(os.environ.get("ANTIGRAVITY_AGENTAPI", Path.home() / ".gemini/antigravity/bin/agentapi.bat"))
TIMEOUT_S = 300

mcp = MCPServer("antigravity")


def _antigravity_env() -> dict[str, str]:
    """Variáveis ANTIGRAVITY_* do terminal do Antigravity (endereço do language server, token CSRF...).

    Ordem: ambiente atual > .collab/antigravity_env.json (handshake novo) > antigravity_ls_address (legado).
    O arquivo é local e ignorado pelo git; o token CSRF vale só para a sessão aberta do Antigravity.
    """
    env = {k: v for k, v in os.environ.items() if k.startswith("ANTIGRAVITY_")}
    if "ANTIGRAVITY_LS_ADDRESS" not in env and ENV_FILE.exists():
        data = json.loads(ENV_FILE.read_text(encoding="utf-8-sig"))
        env.update({k: str(v) for k, v in data.items() if k.startswith("ANTIGRAVITY_")})
    if "ANTIGRAVITY_LS_ADDRESS" not in env and ADDRESS_FILE.exists():
        env["ANTIGRAVITY_LS_ADDRESS"] = ADDRESS_FILE.read_text(encoding="utf-8-sig").strip()
    if not env.get("ANTIGRAVITY_LS_ADDRESS"):
        raise RuntimeError(
            "Antigravity indisponível: abra o Antigravity no repositório e peça ao agente para rodar o "
            "handshake de .collab/PROTOCOL.md (grava .collab/antigravity_env.json)."
        )
    return env


def _one_line(text: str) -> str:
    """O agentapi é um .bat: o cmd corta argumentos na primeira quebra de linha (e trata % e " de
    forma especial). Achata o texto numa linha só, com " | " no lugar das quebras."""
    return " | ".join(part.strip() for part in text.splitlines() if part.strip()).replace('"', "'").replace("%", " por cento")


def _agentapi(*args: str) -> str:
    if not AGENTAPI.exists():
        raise RuntimeError(f"agentapi não encontrado em {AGENTAPI}")
    env = {**os.environ, **_antigravity_env()}
    proc = subprocess.run(
        [str(AGENTAPI), *(_one_line(a) for a in args)],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=TIMEOUT_S,
        env=env,
        cwd=REPO,
    )
    out = (proc.stdout or "").strip()
    if proc.returncode != 0:
        raise RuntimeError(f"agentapi falhou ({proc.returncode}): {out or proc.stderr.strip()}")
    return out


@mcp.tool()
def antigravity_new_conversation(prompt: str, model: str = "pro", title: str = "") -> str:
    """Abre uma conversa nova com o agente do Antigravity (Gemini) e envia `prompt`.

    model: flash_lite | flash | pro. Use pro para revisão de código e decisões de produto.
    Retorna a saída do agentapi (inclui o id da conversa para acompanhar depois).
    """
    if model not in {"flash_lite", "flash", "pro"}:
        raise ValueError("model deve ser flash_lite, flash ou pro")
    args = ["new-conversation", f"--model={model}"]
    if title:
        args.append(f"--title={title}")
    return _agentapi(*args, prompt)


@mcp.tool()
def antigravity_send_message(conversation_id: str, content: str) -> str:
    """Envia uma mensagem de continuação para uma conversa existente do Antigravity."""
    return _agentapi("send-message", conversation_id, content)


@mcp.tool()
def antigravity_conversation_status(conversation_id: str) -> str:
    """Metadados/estado de uma conversa do Antigravity (para saber se terminou)."""
    return _agentapi("get-conversation-metadata", conversation_id)


@mcp.tool()
def collab_read_reviews(limit: int = 5) -> str:
    """Lê as revisões mais recentes que o Antigravity gravou em .collab/reviews/."""
    reviews = sorted((COLLAB / "reviews").glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]
    if not reviews:
        return "nenhuma revisão em .collab/reviews/"
    return "\n\n---\n\n".join(f"# {p.name}\n\n{p.read_text(encoding='utf-8')}" for p in reviews)


if __name__ == "__main__":
    mcp.run()
