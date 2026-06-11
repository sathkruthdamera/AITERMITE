from __future__ import annotations

import re
import shutil

from .precheck import precheck_command

# Words that strongly signal the line is a question/intent rather than a command.
_INTENT_WORDS = {
    "how", "what", "why", "when", "where", "who", "which", "whats", "whose",
    "can", "could", "should", "would", "will", "do", "does", "did", "is", "are",
    "please", "help", "explain", "show", "tell", "find", "list", "make", "create",
    "generate", "write", "convert", "i", "im", "my", "me", "want", "need", "want",
    "remove", "delete", "install", "setup", "fix", "give", "let", "got", "have",
}

# A line that begins with one of these is almost certainly a real command attempt
# (path, sudo, env assignment, redirection), not a thought.
_COMMAND_LEADERS = re.compile(r"^(?:[./~]|[A-Za-z]:[\\/]|sudo\b|[A-Za-z_][A-Za-z0-9_]*=)")


def _tokens(text: str) -> list[str]:
    return [t for t in re.split(r"\s+", text.strip()) if t]


def looks_like_thought(line: str) -> bool:
    """Heuristic: is this typed line a natural-language thought (route to the AI
    ask flow) rather than a mistyped real command (route to the typo fixer)?"""
    text = (line or "").strip()
    if not text:
        return False
    if text.endswith("?"):
        return True

    tokens = _tokens(text)
    if not tokens:
        return False

    first = tokens[0].strip("`'\"").lower()

    # A real, resolvable executable that failed is a runtime error, not a thought.
    if shutil.which(first):
        return False
    if _COMMAND_LEADERS.match(text):
        return False
    # Single token with no spaces: treat as a typo'd command, not a thought.
    if len(tokens) < 2:
        return False

    # A confident known-command typo (e.g. "gti status") belongs to the fixer.
    pre = precheck_command(text)
    if pre.suggestion and pre.confidence >= 0.9:
        return False

    lowered = [t.strip(".,!?;:").lower() for t in tokens]
    intent_hits = sum(1 for t in lowered if t in _INTENT_WORDS)

    # Natural language tends to be several words with at least one intent word,
    # or simply a longer prose-like line.
    if intent_hits >= 1 and len(tokens) >= 2:
        return True
    if len(tokens) >= 5 and intent_hits >= 1:
        return True
    return False
