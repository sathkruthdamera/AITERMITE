from __future__ import annotations

import argparse
import difflib
import json
import os
import platform
import shutil
import sys

from . import __version__
from .history import last_command
from .precheck import precheck_command
from .providers import suggest
from .safety import assess_command
from .shell_integration import animation_text, detect_shell, find_executable, install_shell, profile_path, scripts_dirs, shell_init

CYAN = "\033[96m"
RESET = "\033[0m"

AITERMITE_COMMANDS = {
    "doctor": "--doctor",
    "version": "--version",
    "precheck": "--precheck",
    "install-shell": "--install-shell",
    "shell-init": "--shell-init",
    "help": "--help",
}

AITERMITE_COMMAND_ALIASES = {
    "doc": "doctor",
    "check": "doctor",
    "health": "doctor",
    "docter": "doctor",
    "dotcor": "doctor",
    "docotr": "doctor",
    "doctro": "doctor",
    "verison": "version",
    "versoin": "version",
    "instal-shell": "install-shell",
    "install-shel": "install-shell",
    "shellinit": "shell-init",
}


def cyan(text: str, enabled: bool = True) -> str:
    return f"{CYAN}{text}{RESET}" if enabled else text


def print_doctor(provider: str, no_color: bool = False) -> None:
    print(cyan("AITERMITE doctor", not no_color))
    print(f"version: {__version__}")
    print(f"python: {sys.version.split()[0]}")
    print(f"platform: {platform.platform()}")
    print(f"provider: {provider}")

    on_path = shutil.which("aitermite")
    print(f"aitermite on PATH: {'yes (' + on_path + ')' if on_path else 'NO'}")
    if not on_path:
        exe = find_executable()
        if exe:
            print(f"  found at: {exe}")
            print(f"  hint: add this dir to PATH so 'aitermite'/'ait'/'af' work directly: {os.path.dirname(exe)}")
            print("        (the shell hook and aliases already fall back to 'python -m aitermite', so auto-fix works either way.)")
        else:
            print(f"  hint: add your Scripts dir to PATH (one of: {', '.join(scripts_dirs())}); shell hooks fall back to 'python -m aitermite'.")

    shell = detect_shell()
    prof = profile_path(shell)
    installed = prof.exists() and ("AITERMITE" in prof.read_text(encoding="utf-8", errors="replace"))
    print(f"shell: {shell}")
    print(f"profile: {prof} ({'hook installed' if installed else 'no hook'})")
    if not installed:
        print("  hint: run 'aitermite --install-shell auto' then restart your terminal.")


def print_suggestion(s, typed: str, *, postfail: bool = False, no_color: bool = False) -> None:
    title = "AITERMITE suggestion after failed command" if postfail else "AITERMITE suggestion"
    print(cyan(title, not no_color))
    print(f"Typed: {typed}")
    print(f"Fix: {s.command}")
    print(f"Why: {s.explanation}")
    print(f"Confidence: {s.confidence_label()} ({s.confidence:.2f})")
    print(f"Risk: {s.risk}")
    print(f"Provider: {s.provider}")
    print(f"Run manually: {s.command}")


def maybe_handle_aitermite_builtin_typo(args: argparse.Namespace) -> int | None:
    if not args.command:
        return None
    first = args.command[0].strip().lower().lstrip("-")
    if not first:
        return None
    canonical = AITERMITE_COMMAND_ALIASES.get(first)
    if canonical is None and first not in AITERMITE_COMMANDS:
        match = difflib.get_close_matches(first, list(AITERMITE_COMMANDS), n=1, cutoff=0.72)
        canonical = match[0] if match else None
    elif first in AITERMITE_COMMANDS:
        canonical = first
    if canonical is None:
        return None
    if canonical == "doctor":
        if first != canonical:
            print(cyan("AITERMITE suggestion", not args.no_color))
            print(f"Typed: aitermite {args.command[0]}")
            print("Fix: aitermite doctor")
            print("Why: AITERMITE command typo detected.")
            print("Confidence: high (0.96)")
            print()
        print_doctor(args.provider, args.no_color)
        return 0
    if canonical == "version":
        if first != canonical:
            print("Fix: aitermite version")
        print(__version__)
        return 0
    if canonical == "help":
        print("Run: aitermite --help")
        return 0
    if canonical in {"install-shell", "shell-init", "precheck"} and first != canonical:
        print(cyan("AITERMITE suggestion", not args.no_color))
        print(f"Typed: aitermite {args.command[0]}")
        print(f"Fix: aitermite {canonical}")
        print("Why: AITERMITE command typo detected.")
        return 0
    return None


def _harden_stdio() -> None:
    """Avoid UnicodeEncodeError on legacy Windows consoles (cp1252) when output
    contains non-ASCII characters (animation glyphs, provider suggestions)."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


def main(argv: list[str] | None = None) -> int:
    _harden_stdio()
    parser = argparse.ArgumentParser(prog="aitermite", description="AI-powered terminal error fixer")
    parser.add_argument("command", nargs="*", help="Command to fix. If empty, uses shell history.")
    parser.add_argument("--version", action="store_true")
    parser.add_argument("--doctor", action="store_true")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--provider", default=os.getenv("AITERMITE_PROVIDER", "auto"), choices=["auto", "heuristic", "ollama", "openai"])
    parser.add_argument("--error", default="")
    parser.add_argument("--precheck", action="store_true")
    parser.add_argument("--postfail", type=int, default=None)
    parser.add_argument("--install-shell", choices=["auto", "zsh", "bash", "fish", "powershell", "pwsh", "cmd", "clink", "universal"])
    parser.add_argument("--shell-init", choices=["auto", "zsh", "bash", "fish", "powershell", "pwsh", "cmd", "clink", "universal"])
    parser.add_argument("--no-color", action="store_true")
    args = parser.parse_args(argv)

    if args.version:
        print(__version__)
        return 0
    if args.doctor:
        print_doctor(args.provider, args.no_color)
        return 0
    if args.shell_init:
        print(shell_init(args.shell_init))
        return 0
    if args.install_shell:
        print(animation_text(color=not args.no_color))
        result = install_shell(args.install_shell)
        print(cyan(f"Installed AITERMITE shell integration for {result.shell}", not args.no_color))
        for path in result.paths:
            print(f"Updated: {path}")
        for message in result.messages:
            print(message)
        print("Restart your terminal, then test with: gti status")
        return 0

    builtin_result = maybe_handle_aitermite_builtin_typo(args)
    if builtin_result is not None:
        return builtin_result

    command = " ".join(args.command).strip()
    if command.startswith("-- "):
        command = command[3:]
    if not command:
        command = last_command() or ""
    if not command:
        print("No command supplied and no shell history found.", file=sys.stderr)
        return 2

    if args.precheck:
        result = precheck_command(command)
        payload = {"original": result.original, "suggestion": result.suggestion, "confidence": result.confidence, "reason": result.reason}
        print(json.dumps(payload, indent=2) if args.as_json else (result.suggestion or result.reason))
        return 0

    timeout = float(os.getenv("AITERMITE_POSTFAIL_TIMEOUT_MS", "900")) / 1000 if args.postfail is not None else None
    provider = os.getenv("AITERMITE_POSTFAIL_PROVIDER", args.provider) if args.postfail is not None else args.provider
    s = suggest(command, args.error, provider=provider, timeout=timeout)
    verdict = assess_command(s.command)
    payload = {"typed": command, "suggested_command": s.command, "explanation": s.explanation, "confidence": s.confidence, "confidence_label": s.confidence_label(), "risk": s.risk, "provider": s.provider, "safety_allowed": verdict.allowed, "safety_reason": verdict.reason}
    if args.as_json:
        print(json.dumps(payload, indent=2))
    else:
        print_suggestion(s, command, postfail=args.postfail is not None, no_color=args.no_color)
        if not verdict.allowed:
            print(f"Safety: blocked - {verdict.reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
