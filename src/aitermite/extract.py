from __future__ import annotations

import re
from dataclasses import dataclass

from .safety import assess_command

# Languages we treat as runnable shell. Anything else (python, json, yaml, ...)
# is shown as context but never offered as a runnable command.
_SHELL_LANGS = {
    "", "sh", "bash", "zsh", "shell", "console", "terminal",
    "powershell", "ps", "ps1", "pwsh", "cmd", "bat", "batch",
}

_FENCE_RE = re.compile(r"```([^\n`]*)\n(.*?)```", re.DOTALL)
# Interactive-prompt prefixes a model may echo before a command. '#' is left out
# on purpose — it collides with comment lines, which are far more common in a
# code block than a literal root-shell prompt.
_PROMPT_PREFIX_RE = re.compile(r"^\s*(?:\$|>|PS[^>]*>|[A-Za-z]:\\[^>]*>)\s+")
_LINE_COMMENT_RE = re.compile(r"^(?:#|//|::|rem\b)", re.IGNORECASE)


@dataclass(frozen=True)
class Candidate:
    command: str
    risk: str  # low | medium | dangerous
    allowed: bool  # False only for dangerous patterns we refuse to run


def _clean_line(raw_line: str) -> str:
    stripped = raw_line.strip()
    if not stripped or _LINE_COMMENT_RE.match(stripped):
        return ""
    return _PROMPT_PREFIX_RE.sub("", stripped).strip()


def extract_commands(answer: str) -> list[str]:
    """Return the ordered, de-duplicated list of runnable shell commands found
    in fenced code blocks of an LLM answer."""
    commands: list[str] = []
    seen: set[str] = set()
    for raw_lang, block in _FENCE_RE.findall(answer or ""):
        lang = raw_lang.strip().lower().split()[0] if raw_lang.strip() else ""
        if lang not in _SHELL_LANGS:
            continue
        for raw_line in block.splitlines():
            line = _clean_line(raw_line)
            if line and line not in seen:
                seen.add(line)
                commands.append(line)
    return commands


def candidates(answer: str) -> list[Candidate]:
    """Extracted commands annotated with a safety verdict for the menu."""
    out: list[Candidate] = []
    for cmd in extract_commands(answer):
        verdict = assess_command(cmd)
        # assess_command blocks shell operators (pipes/&&) for its own argv-only
        # auto-apply path; here the user runs through a real shell after an
        # explicit confirmation, so only the truly dangerous patterns disqualify.
        if verdict.risk == "dangerous":
            out.append(Candidate(cmd, "dangerous", False))
        elif verdict.risk in {"low"}:
            out.append(Candidate(cmd, "low", True))
        else:  # medium, unsupported (operators), invalid quoting -> needs eyes
            out.append(Candidate(cmd, "medium", True))
    return out
