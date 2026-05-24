from __future__ import annotations

import re
from typing import Iterable

_SECRET_PATTERNS: Iterable[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(?i)\b(api[_-]?key|token|password|passwd|secret|client_secret)\s*=\s*([^\s'\"]+)"), r"\1=<REDACTED>"),
    (re.compile(r"(?i)(--(?:api-key|token|password|secret)\s+)([^\s'\"]+)"), r"\1<REDACTED>"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"), "<OPENAI_KEY_REDACTED>"),
    (re.compile(r"\bghp_[A-Za-z0-9_]{20,}\b"), "<GITHUB_TOKEN_REDACTED>"),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"), "<GITHUB_PAT_REDACTED>"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "<AWS_ACCESS_KEY_REDACTED>"),
    (re.compile(r"(?i)(authorization:\s*bearer\s+)[A-Za-z0-9._~+/=-]+"), r"\1<REDACTED>"),
]


def redact(text: str) -> str:
    redacted = text or ""
    for pattern, replacement in _SECRET_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted
