<p align="center">
  <img src="assets/aitermite-logo.svg" alt="AITERMITE logo" width="900">
</p>

# AITERMITE

**AITERMITE** is an AI-powered terminal error fixer for Windows, macOS, and Linux. It gives command-fix suggestions manually, before Enter where the shell supports it, and automatically after a command fails through shell hooks.

## Current packaged release

Latest local build prepared in this chat: **v0.4.1 Clink Bootstrap**.

Main features:

- Manual command fixing with `aitermite`.
- Inline fixing with `aitermite <command>`.
- Automatic post-failure suggestion hooks.
- Pre-enter typo detection where supported.
- Ollama local provider support.
- OpenAI fallback support.
- Heuristic offline fallback.
- Windows PowerShell / Windows Terminal support.
- macOS/Linux zsh, bash, and fish support.
- cmd.exe helper macros.
- Clink bootstrap integration for true cmd.exe auto-hooks.
- Secret redaction before provider calls.
- Dangerous command blocking and safety checks.

## Install from wheel

```bash
python -m pip install aitermite-0.4.1-py3-none-any.whl
aitermite --doctor
```

## Install from source

```bash
git clone https://github.com/sathkruthdamera/AITERMITE.git
cd AITERMITE
python -m pip install -e .
aitermite --doctor
```

## Shell integration

```bash
aitermite --install-shell auto
```

Supported shell targets:

```bash
aitermite --install-shell zsh
aitermite --install-shell bash
aitermite --install-shell fish
aitermite --install-shell powershell
aitermite --install-shell cmd
aitermite --install-shell clink
aitermite --install-shell universal
```

## Automatic post-failure behavior

Target behavior:

```text
Wrong command entered -> command fails -> AITERMITE automatically prints suggestion
```

Example:

```bash
gti status
```

Output:

```text
command not found: gti

AITERMITE suggestion after failed command
Typed: gti status
Fix: git status
Why: Known command typo detected.
Confidence: high (0.94)
Run manually: git status
```

## Provider settings

```bash
export AITERMITE_PROVIDER=auto
export AITERMITE_POSTFAIL_PROVIDER=auto
export AITERMITE_POSTFAIL_TIMEOUT_MS=900
```

For Ollama:

```bash
ollama pull gemma3:latest
export AITERMITE_PROVIDER=ollama
export AITERMITE_OLLAMA_MODEL=gemma3:latest
```

For OpenAI:

```bash
export OPENAI_API_KEY="your_api_key"
export AITERMITE_PROVIDER=openai
```

## Common commands

```bash
aitermite --doctor
aitermite git push
aitermite --json git push
aitermite --precheck gti status
aitermite --postfail 127 gti status
aitermite --install-shell auto
```

## Safety

AITERMITE blocks or avoids risky commands such as destructive delete patterns, `curl | sh`, fork bombs, device writes, shutdown/reboot patterns, and unsupported shell control operators in auto-apply flows.

## Validation from local build

```text
CLI tests: 9/9 passed
History tests: 5/5 passed
Precheck tests: 7/7 passed
Redaction tests: 2/2 passed
Safety tests: 7/7 passed
Shell integration tests: 9/9 passed
Total targeted tests: 39/39 passed
Pentest checks: 11/11 passed
Wheel build: passed
Clean virtualenv install: passed
CLI smoke test: passed
Clink hook generation: passed
Version: 0.4.1
```

## Repository import status

This repository has been initialized from ChatGPT. The full v0.4.1 source ZIP and wheel were generated in the workspace. Source import should include:

```text
src/aitermite/
tests/
security/
examples/
assets/
README.md
pyproject.toml
LICENSE
FULL_DOCUMENTATION.md
CROSS_PLATFORM_SHELL_INTEGRATION.md
POSTFAIL_AUTOMATION.md
SHELL_AND_ANIMATION.md
VALIDATION_REPORT.md
```
