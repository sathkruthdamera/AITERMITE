from __future__ import annotations

import os
import subprocess
import sys
from typing import Callable, Iterable

from .extract import Candidate
from .safety import assess_command

CYAN = "\033[96m"
DIM = "\033[2m"
BOLD = "\033[1m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
INVERT = "\033[7m"
RESET = "\033[0m"

_RISK_COLOR = {"low": GREEN, "medium": YELLOW, "dangerous": RED}


# --------------------------------------------------------------------------- #
# Key reading (cross-platform)
# --------------------------------------------------------------------------- #
# Logical keys returned by read_key(): "up", "down", "enter", "cancel",
# "top", "bottom", a single character, or "" on EOF.

def _read_key_windows() -> str:
    import msvcrt

    ch = msvcrt.getwch()
    if ch in ("\x00", "\xe0"):  # arrow / function-key prefix
        code = msvcrt.getwch()
        return {"H": "up", "P": "down", "G": "top", "O": "bottom"}.get(code, "")
    if ch in ("\r", "\n"):
        return "enter"
    if ch == "\x03":  # Ctrl-C
        raise KeyboardInterrupt
    if ch in ("\x1b", "\x04", "\x07"):  # Esc, Ctrl-D, Ctrl-G
        return "cancel"
    return ch


def _read_key_posix() -> str:
    import termios
    import tty

    fd = os.open("/dev/tty", os.O_RDONLY)
    try:
        old = termios.tcgetattr(fd)
        tty.setraw(fd)
        try:
            ch = os.read(fd, 1).decode("utf-8", "replace")
            if ch == "\x1b":
                seq = os.read(fd, 2).decode("utf-8", "replace")
                return {"[A": "up", "[B": "down", "[H": "top", "[F": "bottom"}.get(seq, "cancel")
            if ch in ("\r", "\n"):
                return "enter"
            if ch == "\x03":
                raise KeyboardInterrupt
            if ch in ("\x04", "\x07"):
                return "cancel"
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
    finally:
        os.close(fd)


def read_key() -> str:
    return _read_key_windows() if os.name == "nt" else _read_key_posix()


def _enable_windows_vt() -> None:
    """Best-effort: turn on ANSI/VT processing so the in-place menu redraw
    (cursor-movement escapes) renders correctly on legacy Windows consoles."""
    if os.name != "nt":
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
    except Exception:
        pass


def interactive_supported() -> bool:
    """True when we can host an arrow-key menu attached to a real terminal."""
    try:
        if not sys.stdout.isatty():
            return False
    except Exception:
        return False
    if os.name == "nt":
        try:
            import msvcrt  # noqa: F401
            return True
        except ImportError:
            return False
    try:
        fd = os.open("/dev/tty", os.O_RDONLY)
        os.close(fd)
        return True
    except OSError:
        return False


# --------------------------------------------------------------------------- #
# Menu
# --------------------------------------------------------------------------- #
def _badge(risk: str, color: bool) -> str:
    label = f"[{risk}]"
    if not color:
        return label
    return f"{_RISK_COLOR.get(risk, '')}{label}{RESET}"


def _render(cands: list[Candidate], index: int, color: bool, out) -> int:
    lines = []
    lines.append(f"{CYAN if color else ''}AITERMITE — pick a command to run{RESET if color else ''}")
    for i, c in enumerate(cands):
        cursor = "›" if i == index else " "
        cmd = c.command
        if color and i == index:
            cmd = f"{BOLD}{cmd}{RESET}"
        disabled = "" if c.allowed else f" {DIM if color else ''}(blocked: dangerous){RESET if color else ''}"
        marker = INVERT if (color and i == index) else ""
        reset = RESET if (color and i == index) else ""
        lines.append(f" {marker}{cursor}{reset} {_badge(c.risk, color)} {cmd}{disabled}")
    hint = "↑/↓ move · Enter run · e edit · q cancel"
    lines.append(f"{DIM if color else ''}{hint}{RESET if color else ''}")
    text = "\n".join(lines)
    out.write(text + "\n")
    out.flush()
    return len(lines)


def _clear(n: int, out) -> None:
    # Move cursor up n lines and clear each, so the menu redraws in place.
    out.write(f"\033[{n}A")
    out.write("\033[J")
    out.flush()


def select_command(
    cands: list[Candidate],
    *,
    color: bool = True,
    out=None,
    key_reader: Callable[[], str] | None = None,
) -> Candidate | None:
    """Show an arrow-key menu and return the chosen Candidate, or None if the
    user cancels. An 'edit' selection returns a Candidate with the edited text."""
    out = out or sys.stdout
    key_reader = key_reader or read_key
    if not cands:
        return None
    _enable_windows_vt()
    index = 0
    rendered = _render(cands, index, color, out)
    while True:
        try:
            key = key_reader()
        except KeyboardInterrupt:
            _clear(rendered, out)
            return None
        if key == "":
            return None
        if key == "up":
            index = (index - 1) % len(cands)
        elif key == "down":
            index = (index + 1) % len(cands)
        elif key == "top":
            index = 0
        elif key == "bottom":
            index = len(cands) - 1
        elif key.isdigit() and key != "0" and int(key) <= len(cands):
            index = int(key) - 1
            _clear(rendered, out)
            return cands[index] if cands[index].allowed else None
        elif key in ("q", "Q", "cancel"):
            _clear(rendered, out)
            return None
        elif key in ("e", "E"):
            _clear(rendered, out)
            edited = _edit(cands[index].command, out)
            if not edited:
                return None
            verdict = assess_command(edited)
            risk = "dangerous" if verdict.risk == "dangerous" else ("low" if verdict.risk == "low" else "medium")
            return Candidate(edited, risk, risk != "dangerous")
        elif key == "enter":
            _clear(rendered, out)
            chosen = cands[index]
            return chosen if chosen.allowed else None
        else:
            continue
        _clear(rendered, out)
        rendered = _render(cands, index, color, out)


def _edit(prefill: str, out) -> str:
    """Let the user edit a command before running. Uses a plain line read so
    the cursor and backspace behave normally."""
    out.write(f"Edit command, then Enter:\n  {prefill}\n> ")
    out.flush()
    try:
        return input().strip() or prefill
    except (EOFError, KeyboardInterrupt):
        return ""


# --------------------------------------------------------------------------- #
# Running
# --------------------------------------------------------------------------- #
def run_shell() -> list[str]:
    """The shell command vector used to execute a confirmed command."""
    override = os.getenv("AITERMITE_RUN_SHELL")
    if override:
        import shlex
        return shlex.split(override, posix=os.name != "nt")
    if os.name == "nt":
        return ["powershell", "-NoProfile", "-Command"]
    return [os.environ.get("SHELL", "/bin/sh"), "-c"]


def run_command(command: str, *, color: bool = True, out=None) -> int:
    """Execute a confirmed command through the user's shell, streaming output.
    Refuses commands matching dangerous safety patterns even after selection."""
    out = out or sys.stdout
    verdict = assess_command(command)
    if verdict.risk == "dangerous":
        out.write(f"{RED if color else ''}Refused: {verdict.reason}{RESET if color else ''}\n")
        return 126
    out.write(f"{DIM if color else ''}$ {command}{RESET if color else ''}\n")
    out.flush()
    argv = run_shell() + [command]
    try:
        proc = subprocess.run(argv)
        return proc.returncode
    except FileNotFoundError as exc:
        out.write(f"{RED if color else ''}Could not run: {exc}{RESET if color else ''}\n")
        return 127
