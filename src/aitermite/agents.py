from __future__ import annotations

import json
import os
import shutil
import subprocess
import urllib.request
from dataclasses import dataclass

from .redaction import redact

# Keep answers short and force runnable commands into fenced blocks so the
# extractor can find them. Targeting info is filled in per call.
ASK_SYSTEM_PROMPT = (
    "You are AITERMITE, a terminal copilot. The user types a plain thought at "
    "their shell prompt. Answer briefly and practically. When you propose shell "
    "commands the user can run, put EACH runnable command on its own line inside "
    "a single fenced code block (```bash or ```powershell). Do not put prose, "
    "prompts ($, >, PS>), or comments inside the code block. Prefer the shell and "
    "OS named below."
)


@dataclass(frozen=True)
class AskResult:
    answer: str
    provider: str
    ok: bool = True
    error: str = ""


def _claude_available() -> bool:
    return shutil.which("claude") is not None


def _codex_available() -> bool:
    return shutil.which("codex") is not None


def _ollama_available() -> bool:
    if shutil.which("ollama") is not None:
        return True
    try:
        urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=0.4)
        return True
    except Exception:
        return False


def available_providers() -> list[str]:
    out = []
    if _claude_available():
        out.append("claude")
    if _codex_available():
        out.append("codex")
    if _ollama_available():
        out.append("ollama")
    return out


def _build_prompt(thought: str, shell: str, os_name: str) -> str:
    return (
        f"{ASK_SYSTEM_PROMPT}\nShell: {shell}\nOS: {os_name}\n\n"
        f"User thought: {redact(thought)}"
    )


def claude_ask(thought: str, shell: str, os_name: str, timeout: float = 60.0) -> AskResult:
    prompt = _build_prompt(thought, shell, os_name)
    proc = subprocess.run(
        ["claude", "-p", prompt],
        capture_output=True,
        text=True,
        timeout=timeout,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        return AskResult("", "claude", ok=False, error=(proc.stderr or "claude exited non-zero").strip())
    return AskResult(proc.stdout.strip(), "claude")


def codex_ask(thought: str, shell: str, os_name: str, timeout: float = 60.0) -> AskResult:
    prompt = _build_prompt(thought, shell, os_name)
    # `codex exec` runs a single non-interactive turn and prints to stdout.
    proc = subprocess.run(
        ["codex", "exec", prompt],
        capture_output=True,
        text=True,
        timeout=timeout,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        return AskResult("", "codex", ok=False, error=(proc.stderr or "codex exited non-zero").strip())
    return AskResult(proc.stdout.strip(), "codex")


def ollama_ask(thought: str, shell: str, os_name: str, timeout: float = 60.0, model: str | None = None) -> AskResult:
    model = model or os.getenv("AITERMITE_OLLAMA_MODEL", "gemma3:latest")
    payload = {"model": model, "prompt": _build_prompt(thought, shell, os_name), "stream": False}
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        "http://127.0.0.1:11434/api/generate",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = json.loads(resp.read().decode("utf-8", "replace"))
    return AskResult((body.get("response") or "").strip(), "ollama")


_PROVIDER_FNS = {"claude": "claude_ask", "codex": "codex_ask", "ollama": "ollama_ask"}


def _provider_fn(name: str):
    """Resolve the provider function by name at call time so tests can monkeypatch
    e.g. ``agents.ollama_ask`` and have the dispatch honor the patched version."""
    attr = _PROVIDER_FNS.get(name)
    return globals().get(attr) if attr else None


def ask(thought: str, *, provider: str = "auto", shell: str = "", os_name: str = "", timeout: float | None = None) -> AskResult:
    """Send a natural-language thought to an LLM and return its answer.

    provider "auto" tries the installed CLI agents first (claude, then codex),
    then falls back to a local ollama daemon.
    """
    provider = (provider or os.getenv("AITERMITE_ASK_PROVIDER", "auto")).lower()
    timeout = timeout if timeout is not None else float(os.getenv("AITERMITE_ASK_TIMEOUT", "60"))
    thought = (thought or "").strip()
    if not thought:
        return AskResult("", provider, ok=False, error="Empty thought.")

    if provider != "auto":
        fn = _provider_fn(provider)
        if fn is None:
            return AskResult("", provider, ok=False, error=f"Unknown ask provider: {provider}")
        try:
            return fn(thought, shell, os_name, timeout=timeout)
        except Exception as exc:  # noqa: BLE001 - surface a clean message to the user
            return AskResult("", provider, ok=False, error=str(exc))

    order = available_providers()
    if not order:
        return AskResult(
            "", "auto", ok=False,
            error="No AI backend found. Install the 'claude' or 'codex' CLI, or run a local ollama.",
        )
    last_error = ""
    for name in order:
        try:
            result = _provider_fn(name)(thought, shell, os_name, timeout=timeout)
            if result.ok and result.answer:
                return result
            last_error = result.error or "empty answer"
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            continue
    return AskResult("", "auto", ok=False, error=last_error or "All providers failed.")
