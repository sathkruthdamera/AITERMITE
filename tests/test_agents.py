import subprocess

import aitermite.agents as agents


class _Proc:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_claude_ask_returns_stdout(monkeypatch):
    monkeypatch.setattr(agents.subprocess, "run", lambda *a, **k: _Proc(0, "use ls -la\n"))
    result = agents.claude_ask("how to list", "bash", "linux")
    assert result.ok
    assert result.provider == "claude"
    assert result.answer == "use ls -la"


def test_claude_ask_nonzero_is_error(monkeypatch):
    monkeypatch.setattr(agents.subprocess, "run", lambda *a, **k: _Proc(1, "", "boom"))
    result = agents.claude_ask("x", "bash", "linux")
    assert not result.ok
    assert "boom" in result.error


def test_auto_prefers_available_and_falls_back(monkeypatch):
    # Only ollama "available"; claude/codex absent.
    monkeypatch.setattr(agents, "_claude_available", lambda: False)
    monkeypatch.setattr(agents, "_codex_available", lambda: False)
    monkeypatch.setattr(agents, "_ollama_available", lambda: True)
    monkeypatch.setattr(agents, "ollama_ask", lambda *a, **k: agents.AskResult("hi", "ollama"))
    result = agents.ask("question here", provider="auto")
    assert result.provider == "ollama"
    assert result.answer == "hi"


def test_auto_no_backend_errors(monkeypatch):
    monkeypatch.setattr(agents, "_claude_available", lambda: False)
    monkeypatch.setattr(agents, "_codex_available", lambda: False)
    monkeypatch.setattr(agents, "_ollama_available", lambda: False)
    result = agents.ask("some thought", provider="auto")
    assert not result.ok
    assert "No AI backend" in result.error


def test_empty_thought_is_rejected():
    assert not agents.ask("   ").ok
