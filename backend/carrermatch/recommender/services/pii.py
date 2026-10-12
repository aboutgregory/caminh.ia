"""Higienização de texto: entrada do usuário e payload enviado à Claude API.

- `clean_user_text`: remove HTML/script e caracteres de controle do texto livre
  (aplicado na borda da API, antes de qualquer processamento).
- `redact_pii`: remove identificadores diretos antes de enviar à Anthropic
  (seg. v2 §3.2/§4.4). Nomes próprios não são detectáveis com regex de forma
  confiável — o prompt instrui o usuário a não incluir dados pessoais, e o
  payload nunca carrega nome/e-mail/user_id/IP vindos do perfil.
"""

from __future__ import annotations

import re
import unicodedata

REDACTED = "[REMOVIDO]"

_TAGS = re.compile(r"<\s*(script|style)[^>]*>.*?<\s*/\s*\1\s*>|<[^>]{0,500}>", re.IGNORECASE | re.DOTALL)
_CONTROL = re.compile(r"[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f​-‏ -‮⁦-⁩]")

# ordem importa: padrões mais específicos primeiro
_PII_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("email", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("url", re.compile(r"\b(?:https?://|www\.)\S+", re.IGNORECASE)),
    ("cnpj", re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b")),
    ("cpf", re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")),
    ("telefone", re.compile(r"(?:\+?55[\s.-]?)?\(?\b\d{2}\)?[\s.-]?9?\d{4}[\s.-]?\d{4}\b")),
    ("cep", re.compile(r"\b\d{5}-\d{3}\b")),
)


def clean_user_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = _TAGS.sub(" ", text)
    text = _CONTROL.sub("", text)
    return re.sub(r"[ \t]+", " ", text).strip()


def redact_pii(text: str) -> str:
    for _, pattern in _PII_PATTERNS:
        text = pattern.sub(REDACTED, text)
    return text


def contains_pii(text: str) -> bool:
    return any(p.search(text) for _, p in _PII_PATTERNS)
