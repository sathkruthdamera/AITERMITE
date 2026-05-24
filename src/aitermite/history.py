from __future__ import annotations

import os
import re
from pathlib import Path

_SELF_PATTERNS = ("aitermite", "ai-fix", "python -m aitermite")


def history_paths() -> list[Path]:
    home = Path.home()
    paths = [home / ".zsh_history", home / ".bash_history", home / ".local/share/fish/fish_history"]
    appdata = os.getenv("APPDATA")
    if appdata:
        paths.append(Path(appdata) / "Microsoft/Windows/PowerShell/PSReadLine/ConsoleHost_history.txt")
    return paths


def _clean_zsh(line: str) -> str:
    if line.startswith(": ") and ";" in line:
        return line.split(";", 1)[1].strip()
    return line.strip()


def _clean_fish(lines: list[str]) -> list[str]:
    out: list[str] = []
    for line in lines:
        text = line.strip()
        if text.startswith("- cmd:"):
            out.append(text.split(":", 1)[1].strip())
    return out


def _is_self(command: str) -> bool:
    stripped = command.strip()
    base = Path(stripped.split()[0]).name if stripped.split() else ""
    return base in {"aitermite", "ai-fix"} or stripped.startswith("python -m aitermite")


def read_history(limit: int = 80) -> list[str]:
    commands: list[str] = []
    for path in history_paths():
        if not path.exists():
            continue
        try:
            lines = path.read_text(errors="ignore").splitlines()
        except OSError:
            continue
        parsed = _clean_fish(lines) if "fish_history" in str(path) else [_clean_zsh(x) for x in lines]
        for cmd in parsed:
            if cmd and not _is_self(cmd):
                commands.append(cmd)
    return commands[-limit:]


def last_command() -> str | None:
    hist = read_history(20)
    return hist[-1] if hist else None
