from __future__ import annotations

import json
import os
import subprocess
import urllib.request
from .models import FixSuggestion
from .precheck import precheck_command
from .redaction import redact

SYSTEM_PROMPT = "Return JSON with command, explanation, confidence, risk. Suggest one safe corrected command."

def heuristic_suggest(command: str, error: str = "") -> FixSuggestion:
    pre = precheck_command(command)
    if pre.suggestion:
        return FixSuggestion(pre.suggestion, pre.reason, pre.confidence, "low", "heuristic")
    text = f"{command}\n{error}".lower()
    if "module not found" in text or "modulenotfounderror" in text:
        parts = command.split()
        module = "requests"
        if "no module named" in text:
            module = text.split("no module named")[-1].strip().strip("'\" .") or module
        return FixSuggestion(f"python -m pip install {module}", "Missing Python module detected.", 0.72, "low", "heuristic")
    if command.strip().startswith("git push"):
        return FixSuggestion("git push --set-upstream origin HEAD", "Git push may need an upstream branch.", 0.70, "medium", "heuristic")
    return FixSuggestion(command, "No confident fix found; review the command manually.", 0.25, "low", "heuristic")

def ollama_suggest(command: str, error: str = "", model: str | None = None, timeout: float = 8.0) -> FixSuggestion:
    model = model or os.getenv("AITERMITE_OLLAMA_MODEL", "gemma3:latest")
    payload = {"model": model, "prompt": f"{SYSTEM_PROMPT}\nCommand: {redact(command)}\nError: {redact(error)}", "stream": False, "format": "json"}
    data = json.dumps(payload).encode()
    req = urllib.request.Request("http://127.0.0.1:11434/api/generate", data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        outer = json.loads(resp.read().decode())
    body = json.loads(outer.get("response", "{}"))
    return FixSuggestion(body.get("command", command), body.get("explanation", "Ollama suggestion."), float(body.get("confidence", 0.5)), body.get("risk", "medium"), "ollama")

def openai_suggest(command: str, error: str = "", timeout: float = 10.0) -> FixSuggestion:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    payload = {"model": os.getenv("AITERMITE_OPENAI_MODEL", "gpt-4.1-mini"), "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": f"Command: {redact(command)}\nError: {redact(error)}"}], "response_format": {"type": "json_object"}}
    req = urllib.request.Request("https://api.openai.com/v1/chat/completions", data=json.dumps(payload).encode(), headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        outer = json.loads(resp.read().decode())
    body = json.loads(outer["choices"][0]["message"]["content"])
    return FixSuggestion(body.get("command", command), body.get("explanation", "OpenAI suggestion."), float(body.get("confidence", 0.5)), body.get("risk", "medium"), "openai")

def suggest(command: str, error: str = "", provider: str = "auto", timeout: float | None = None) -> FixSuggestion:
    provider = provider or os.getenv("AITERMITE_PROVIDER", "auto")
    timeout = timeout or float(os.getenv("AITERMITE_TIMEOUT", "8"))
    if provider == "heuristic":
        return heuristic_suggest(command, error)
    if provider == "ollama":
        return ollama_suggest(command, error, timeout=timeout)
    if provider == "openai":
        return openai_suggest(command, error, timeout=timeout)
    first = heuristic_suggest(command, error)
    if first.confidence >= 0.80:
        return first
    for fn in (ollama_suggest, openai_suggest):
        try:
            return fn(command, error, timeout=timeout)
        except Exception:
            continue
    return first
