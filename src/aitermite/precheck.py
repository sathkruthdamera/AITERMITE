from __future__ import annotations

import difflib
import shutil
from dataclasses import dataclass

@dataclass(frozen=True)
class PrecheckResult:
    original: str
    suggestion: str | None
    confidence: float
    reason: str

KNOWN_COMMAND_TYPOS = {
    "gti": "git", "gi": "git", "gitg": "git", "pyhton": "python", "pythn": "python", "python3.13": "python",
    "pip3.13": "pip", "dockre": "docker", "docer": "docker", "kubctl": "kubectl", "kubeclt": "kubectl",
    "npm": "npm", "npx": "npx", "yarn": "yarn", "pnpm": "pnpm", "cd..": "cd .."
}
SUBCOMMAND_TYPOS = {
    "git": {"sttaus": "status", "statsu": "status", "chekcout": "checkout", "comit": "commit", "pus": "push", "pul": "pull", "brnch": "branch"},
    "npm": {"isntall": "install", "isntal": "install", "rn": "run", "startt": "start"},
    "docker": {"pss": "ps", "bulid": "build", "runn": "run"},
    "kubectl": {"gett": "get", "aply": "apply", "decribe": "describe"},
}

def _tokens(command: str) -> list[str]:
    return [x for x in command.strip().split() if x]

def _best(word: str, choices: list[str]) -> tuple[str | None, float]:
    matches = difflib.get_close_matches(word, choices, n=1, cutoff=0.74)
    if not matches:
        return None, 0.0
    return matches[0], difflib.SequenceMatcher(None, word, matches[0]).ratio()

def precheck_command(command: str) -> PrecheckResult:
    parts = _tokens(command)
    if not parts:
        return PrecheckResult(command, None, 0.0, "empty command")
    changed = False
    first = parts[0]
    if first in KNOWN_COMMAND_TYPOS and KNOWN_COMMAND_TYPOS[first] != first:
        parts[0] = KNOWN_COMMAND_TYPOS[first]
        changed = True
    elif shutil.which(first) is None:
        choices = ["git", "python", "pip", "npm", "npx", "node", "docker", "kubectl", "terraform", "aws", "az", "java", "mvn"]
        match, score = _best(first, choices)
        if match and score >= 0.78:
            parts[0] = match
            changed = True
    if len(parts) > 1 and parts[0] in SUBCOMMAND_TYPOS:
        sub = parts[1]
        replacement = SUBCOMMAND_TYPOS[parts[0]].get(sub)
        if replacement:
            parts[1] = replacement
            changed = True
    if not changed:
        return PrecheckResult(command, None, 0.0, "no obvious typo detected")
    return PrecheckResult(command, " ".join(parts), 0.94, "Known command/subcommand typo detected")
