from __future__ import annotations

import argparse
import json
import os
import platform
import sys

from . import __version__
from .history import last_command
from .precheck import precheck_command
from .providers import suggest
from .safety import assess_command
from .shell_integration import animation_text, shell_init

CYAN = "\033[96m"
RESET = "\033[0m"


def cyan(text: str, enabled: bool = True) -> str:
    return f"{CYAN}{text}{RESET}" if enabled else text


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


def main(argv: list[str] | None = None) -> int:
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
        print(cyan("AITERMITE doctor", not args.no_color))
        print(f"version: {__version__}")
        print(f"python: {sys.version.split()[0]}")
        print(f"platform: {platform.platform()}")
        print(f"provider: {args.provider}")
        return 0
    if args.shell_init:
        print(shell_init(args.shell_init))
        return 0
    if args.install_shell:
        print(animation_text(color=not args.no_color))
        print(shell_init(args.install_shell))
        print(cyan("Copy the shell init block above into your shell profile, or use the packaged installer scripts from the generated ZIP.", not args.no_color))
        return 0

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
