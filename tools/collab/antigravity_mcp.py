"""MCP server: Claude Code -> Antigravity (Gemini).

Envolve a CLI `agentapi` do Antigravity. A CLI exige ANTIGRAVITY_LS_ADDRESS,
que só existe dentro dos terminais do Antigravity aberto. Handshake:

    1. variável de ambiente ANTIGRAVITY_LS_ADDRESS, se definida; senão
    2. arquivo .collab/antigravity_ls_address, gravado pelo agente do
       Antigravity ao iniciar a sessão (ver .collab/PROTOCOL.md).

Registrado em .mcp.json na raiz do repositório.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from mcp.server.mcpserver import MCPServer

REPO = Path(__file__).resolve().parents[2]
COLLAB = REPO / ".collab"
ADDRESS_FILE = COLLAB / "antigravity_ls_address"
AGENTAPI = Path(os.environ.get("ANTIGRAVITY_AGENTAPI", Path.home() / ".gemini/antigravity/bin/agentapi.bat"))
TIMEOUT_S = 300

mcp = MCPServer("antigravity")


def _ls_address() -> str:
    addr = os.environ.get("ANTIGRAVITY_LS_ADDRESS", "").strip()
    if not addr and ADDRESS_FILE.exists():
        addr = ADDRESS_FILE.read_text(encoding="utf-8-sig").strip()
    if not addr:
        raise RuntimeError(
            "Antigravity indisponível: abra o Antigravity no repositório e peça ao agente para rodar o "
            "handshake de .collab/PROTOCOL.md (grava .collab/antigravity_ls_address)."
        )
    return addr


def _agentapi(*args: str) -> str:
    if not AGENTAPI.exists():
        raise RuntimeError(f"agentapi não encontrado em {AGENTAPI}")
    env = {**os.environ, "ANTIGRAVITY_LS_ADDRESS": _ls_address()}
    proc = subprocess.run(
        [str(AGENTAPI), *args],
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
