"""MCP server: Antigravity (Gemini) -> Claude Code.

Expõe o Claude Code em modo headless (`claude -p`) como ferramentas para o
agente do Antigravity. Por padrão o Claude roda SOMENTE LEITURA (Read, Grep,
Glob) — revisa e opina, não edita. Edição continua com quem é Responsible pelo
arquivo segundo o RACI do roadmap.

Registrado no mcp_config.json do Antigravity.
"""

from __future__ import annotations

import glob
import os
import shutil
import subprocess
from pathlib import Path

from mcp.server.mcpserver import MCPServer

REPO = Path(__file__).resolve().parents[2]
TIMEOUT_S = 600
READ_ONLY_TOOLS = "Read,Grep,Glob"

mcp = MCPServer("claude-code")


def _claude_bin() -> str:
    """CLAUDE_BIN > `claude` no PATH > versão mais recente instalada pelo app desktop."""
    if env := os.environ.get("CLAUDE_BIN"):
        return env
    if found := shutil.which("claude"):
        return found
    candidates = glob.glob(os.path.expandvars(r"%APPDATA%\Claude\claude-code\*\*\claude.exe"))
    if not candidates:
        raise RuntimeError("Claude Code CLI não encontrado; defina CLAUDE_BIN")
    return max(candidates, key=os.path.getmtime)


def _run_claude(prompt: str) -> str:
    proc = subprocess.run(
        [_claude_bin(), "-p", prompt, "--allowedTools", READ_ONLY_TOOLS, "--output-format", "text"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=TIMEOUT_S,
        cwd=REPO,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"claude falhou ({proc.returncode}): {proc.stderr.strip() or proc.stdout.strip()}")
    return proc.stdout.strip()


@mcp.tool()
def claude_review(paths: list[str], focus: str = "") -> str:
    """Pede ao Claude uma revisão crítica de arquivos do repositório caminh.ia.

    paths: caminhos relativos à raiz do repo. focus: o que priorizar (ex.: "corretude do
    algoritmo", "regras RN-01..RN-10", "acessibilidade"). Retorna achados ordenados por
    severidade, cada um com arquivo:linha, problema e correção sugerida.
    """
    missing = [p for p in paths if not (REPO / p).exists()]
    if missing:
        raise ValueError(f"arquivos inexistentes: {missing}")
    prompt = (
        "Você é o revisor técnico do caminh.ia (veja CLAUDE.md e .collab/PROTOCOL.md). "
        f"Revise criticamente: {', '.join(paths)}. "
        + (f"Foco: {focus}. " if focus else "")
        + "Responda em pt-BR com achados ordenados por severidade (bloqueante/importante/sugestão), "
        "cada um com arquivo:linha, problema, cenário de falha e correção sugerida. "
        "Se não houver problemas reais, diga isso — não invente achados."
    )
    return _run_claude(prompt)


@mcp.tool()
def ask_claude(question: str) -> str:
    """Pergunta livre ao Claude sobre a arquitetura, algoritmos ou código do caminh.ia
    (somente leitura do repositório)."""
    return _run_claude(question)


if __name__ == "__main__":
    mcp.run()
