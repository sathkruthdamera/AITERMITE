from __future__ import annotations

import re
import shlex
import subprocess
from dataclasses import dataclass
from typing import List, Sequence

DANGEROUS_PATTERNS = [
    re.compile(r"\brm\s+-[A-Za-z]*r[A-Za-z]*f[A-Za-z]*\s+(?:--no-preserve-root\s+)?/(?:\s|$)"),
    re.compile(r"\brm\s+-[A-Za-z]*f[A-Za-z]*r[A-Za-z]*\s+(?:~|\$HOME)(?:\s|/|$)"),
    re.compile(r"\bdd\s+.*\bof=/dev/(?:sd|nvme|hd)"),
    re.compile(r"\bmkfs(?:\.[a-z0-9]+)?\b"),
    re.compile(r"\bshutdown\b|\breboot\b|\bhalt\b"),
    re.compile(r":\(\)\s*\{\s*:\|:&\s*\}\s*;:"),
    re.compile(r"\b(?:curl|wget)\b.*\|\s*(?:sudo\s+)?(?:sh|bash)\b"),
    re.compile(r">\s*/dev/(?:sd|nvme|hd)[a-z0-9]+"),
]
SHELL_OPERATOR_TOKENS = {"|", "||", "&&", ";", "<", ">", ">>", "2>", "2>>", "&"}
MEDIUM_RISK_PATTERNS = [re.compile(r"\bsudo\b"), re.compile(r"\brm\b"), re.compile(r"\bchmod\b|\bchown\b"), re.compile(r"\bgit\s+reset\b|\bgit\s+clean\b"), re.compile(r"\bkubectl\s+delete\b")]

@dataclass(frozen=True)
class SafetyVerdict:
    allowed: bool
    risk: str
    reason: str

def command_to_argv(command: str) -> List[str]:
    return shlex.split(command, posix=True)

def assess_command(command: str) -> SafetyVerdict:
    normalized = " ".join((command or "").strip().split())
    if not normalized:
        return SafetyVerdict(False, "invalid", "Empty command.")
    for pattern in DANGEROUS_PATTERNS:
        if pattern.search(normalized):
            return SafetyVerdict(False, "dangerous", "Blocked by AITERMITE safety rules.")
    try:
        argv = command_to_argv(normalized)
    except ValueError as exc:
        return SafetyVerdict(False, "invalid", f"Invalid shell quoting: {exc}")
    if any(token in SHELL_OPERATOR_TOKENS for token in argv):
        return SafetyVerdict(False, "unsupported", "Shell control operators are blocked in auto-apply mode.")
    for pattern in MEDIUM_RISK_PATTERNS:
        if pattern.search(normalized):
            return SafetyVerdict(True, "medium", "Command needs explicit confirmation.")
    return SafetyVerdict(True, "low", "No high-risk shell pattern detected.")

def run_command(command: str, *, cwd: str | None = None, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    verdict = assess_command(command)
    if not verdict.allowed:
        raise ValueError(verdict.reason)
    argv: Sequence[str] = command_to_argv(command)
    if not argv:
        raise ValueError("Empty command.")
    return subprocess.run(argv, cwd=cwd, timeout=timeout, check=False, text=True, capture_output=True, shell=False)
