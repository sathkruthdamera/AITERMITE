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
    "terrafom": "terraform", "terform": "terraform", "awscli": "aws", "azcli": "az",
    "npm": "npm", "npx": "npx", "yarn": "yarn", "pnpm": "pnpm", "cd..": "cd .."
}

SUBCOMMAND_TYPOS = {
    "git": {
        "sttaus": "status", "statsu": "status", "chekcout": "checkout", "chekout": "checkout",
        "comit": "commit", "cmmit": "commit", "pus": "push", "pul": "pull", "brnch": "branch",
        "rest": "reset", "mrege": "merge", "reabse": "rebase", "swtich": "switch", "swich": "switch",
    },
    "npm": {"isntall": "install", "isntal": "install", "instal": "install", "rn": "run", "runn": "run", "startt": "start"},
    "docker": {"pss": "ps", "bulid": "build", "buid": "build", "runn": "run", "imgaes": "images", "iamges": "images", "comopse": "compose"},
    "kubectl": {"gett": "get", "aply": "apply", "appy": "apply", "decribe": "describe", "descrbe": "describe", "delte": "delete", "log": "logs"},
    "terraform": {"paln": "plan", "plna": "plan", "appy": "apply", "aply": "apply", "destory": "destroy", "destro": "destroy", "innit": "init"},
    "aws": {"s33": "s3", "ec22": "ec2", "iamn": "iam", "cloudwatchh": "cloudwatch", "lambd": "lambda"},
    "az": {"logn": "login", "grop": "group", "aksx": "aks", "webap": "webapp"},
}

TOKEN_TYPOS = {
    "--buld": "--build", "--bulid": "--build", "--buid": "--build",
    "--no-cahe": "--no-cache", "--no-cahce": "--no-cache",
    "--detatch": "--detach", "--deatch": "--detach",
    "--varfile": "--var-file", "--var-fiel": "--var-file",
    "--namesapce": "--namespace", "--namspace": "--namespace",
}

def _tokens(command: str) -> list[str]:
    return [x for x in command.strip().split() if x]

def _best(word: str, choices: list[str]) -> tuple[str | None, float]:
    matches = difflib.get_close_matches(word, choices, n=1, cutoff=0.74)
    if not matches:
        return None, 0.0
    return matches[0], difflib.SequenceMatcher(None, word, matches[0]).ratio()

def _fix_any_token(parts: list[str]) -> bool:
    changed = False
    for i, token in enumerate(parts):
        replacement = TOKEN_TYPOS.get(token)
        if replacement:
            parts[i] = replacement
            changed = True
    return changed

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
    if _fix_any_token(parts):
        changed = True
    if not changed:
        return PrecheckResult(command, None, 0.0, "no obvious typo detected")
    return PrecheckResult(command, " ".join(parts), 0.94, "Known command/subcommand/flag typo detected")
