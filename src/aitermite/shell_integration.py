from __future__ import annotations

import os
import shutil
import sys
import sysconfig
from pathlib import Path
from dataclasses import dataclass

CYAN = "\033[96m"
RESET = "\033[0m"
START_MARKER = "# >>> AITERMITE shell integration >>>"
END_MARKER = "# <<< AITERMITE shell integration <<<"

INSTALL_ANIMATION = [
    "AITERMITE  [>_       ]  scanning shell",
    "AITERMITE  [ >_      ]  wiring hooks",
    "AITERMITE  [  >_     ]  enabling post-failure AI",
    "AITERMITE  [   >_    ]  ready",
]

@dataclass
class InstallResult:
    shell: str
    paths: list[Path]
    messages: list[str]

    @property
    def primary_path(self) -> Path:
        return self.paths[0]


def animation_text(color: bool = True) -> str:
    return "\n".join((CYAN + x + RESET) if color else x for x in INSTALL_ANIMATION)


def detect_shell() -> str:
    if os.name == "nt":
        return "powershell"
    shell = os.environ.get("SHELL", "").lower()
    if "zsh" in shell:
        return "zsh"
    if "fish" in shell:
        return "fish"
    if "bash" in shell:
        return "bash"
    return "bash"


def scripts_dirs() -> list[str]:
    """Directories where pip may have placed the ``aitermite`` console script.

    A ``pip install --user`` on Windows drops the script in the *user-site*
    Scripts dir (e.g. ``%APPDATA%\\Python\\Python3xx\\Scripts``), NOT next to
    ``python.exe`` — so we have to consult both install schemes, not just the
    interpreter directory.
    """
    dirs: list[str] = []
    user_scheme = "nt_user" if os.name == "nt" else "posix_user"
    for scheme in (None, user_scheme):
        try:
            dirs.append(sysconfig.get_path("scripts") if scheme is None
                        else sysconfig.get_path("scripts", scheme=scheme))
        except (KeyError, ValueError):
            pass
    base = os.path.dirname(sys.executable)
    dirs.append(os.path.join(base, "Scripts") if os.name == "nt" else base)
    seen: set[str] = set()
    out: list[str] = []
    for d in dirs:
        if d and d not in seen:
            seen.add(d)
            out.append(d)
    return out


def find_executable() -> str | None:
    """Locate the installed ``aitermite`` launcher, even when its Scripts dir is
    not on PATH (the common pip ``--user`` gotcha on Windows)."""
    found = shutil.which("aitermite")
    if found:
        return found
    name = "aitermite.exe" if os.name == "nt" else "aitermite"
    for d in scripts_dirs():
        candidate = os.path.join(d, name)
        if os.path.exists(candidate):
            return candidate
    return None


def launcher_command() -> str:
    """Resolve a launcher that works even when the Scripts dir is not on PATH.

    The shell hooks must invoke AITERMITE without relying on ``aitermite`` being
    on PATH (a common pip ``--user`` install gotcha on Windows). ``python -m
    aitermite`` via the current interpreter always resolves the package.
    """
    exe = find_executable()
    if exe:
        return f'"{exe}"'
    return f'"{sys.executable}" -m aitermite'


def powershell_profile_paths() -> list[Path]:
    """All profile paths PowerShell may load, so the hook works regardless of
    whether the user runs Windows PowerShell 5.1 or PowerShell 7+."""
    home = Path.home()
    if os.name == "nt":
        docs = home / "Documents"
        return [
            docs / "WindowsPowerShell" / "Microsoft.PowerShell_profile.ps1",  # Windows PowerShell 5.1
            docs / "PowerShell" / "Microsoft.PowerShell_profile.ps1",         # PowerShell 7+
        ]
    return [home / ".config" / "powershell" / "Microsoft.PowerShell_profile.ps1"]


def profile_path(shell: str) -> Path:
    home = Path.home()
    shell = shell.lower()
    if shell == "zsh":
        return home / ".zshrc"
    if shell == "bash":
        return home / ".bashrc"
    if shell == "fish":
        return home / ".config" / "fish" / "conf.d" / "aitermite.fish"
    if shell in {"powershell", "pwsh"}:
        return powershell_profile_paths()[0]
    if shell == "cmd":
        return home / ".aitermite" / "aitermite-cmd-init.bat"
    if shell == "clink":
        local = os.getenv("LOCALAPPDATA")
        if local:
            return Path(local) / "clink" / "aitermite.lua"
        return home / ".aitermite" / "aitermite-clink.lua"
    return home / ".profile"


def _write_profile_block(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    block = f"{START_MARKER}\n{content.strip()}\n{END_MARKER}\n"
    if START_MARKER in existing and END_MARKER in existing:
        before = existing.split(START_MARKER, 1)[0].rstrip()
        after = existing.split(END_MARKER, 1)[1].lstrip()
        updated = before + "\n\n" + block + after
    else:
        updated = (existing.rstrip() + "\n\n" + block) if existing.strip() else block
    path.write_text(updated, encoding="utf-8")


def install_shell(shell: str) -> InstallResult:
    shell = detect_shell() if shell == "auto" else shell.lower()
    if shell == "cmd":
        path = profile_path("cmd")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(cmd_init(), encoding="utf-8")
        clink_path = profile_path("clink")
        clink_path.parent.mkdir(parents=True, exist_ok=True)
        clink_path.write_text(clink_lua(), encoding="utf-8")
        return InstallResult("cmd", [path, clink_path], ["Wrote cmd.exe aliases and Clink hook. Run the BAT once or use Clink for auto post-failure suggestions."])
    if shell == "clink":
        path = profile_path("clink")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(clink_lua(), encoding="utf-8")
        return InstallResult("clink", [path], ["Wrote Clink Lua hook."])
    if shell in {"powershell", "pwsh"}:
        content = shell_init("powershell")
        paths = powershell_profile_paths()
        for path in paths:
            _write_profile_block(path, content)
        messages = ["Installed PowerShell integration for Windows PowerShell 5.1 and PowerShell 7+."]
        if shutil.which("aitermite") is None:
            exe = find_executable()
            where = exe if exe else "python -m aitermite"
            messages.append(f"Note: 'aitermite' is not on PATH; the hook and the 'ait'/'af' aliases call {where} directly, so they still work.")
        return InstallResult("powershell", paths, messages)
    path = profile_path(shell)
    _write_profile_block(path, shell_init(shell))
    return InstallResult(shell, [path], [f"Installed {shell} integration. Restart terminal or source the profile."])


def zsh_init() -> str:
    return r'''
# AITERMITE zsh integration
_aitermite_preexec(){ export AITERMITE_LAST_COMMAND="$1"; }
_aitermite_precmd(){ local code=$?; if [ "$code" -ne 0 ] && [ -n "$AITERMITE_LAST_COMMAND" ]; then aitermite --postfail "$code" -- "$AITERMITE_LAST_COMMAND" 2>/dev/null || true; fi }
autoload -Uz add-zsh-hook
add-zsh-hook preexec _aitermite_preexec
add-zsh-hook precmd _aitermite_precmd
alias ait='aitermite'
alias af='aitermite'
alias ai='aitermite ask'
alias aicheck='aitermite --precheck'
'''


def bash_init() -> str:
    return r'''
# AITERMITE bash integration
__aitermite_last_command=""
__aitermite_preexec(){ local cmd="$BASH_COMMAND"; case "$cmd" in __aitermite_*|aitermite*|ait\ *|af\ *|aicheck\ *|history\ *) return ;; esac; __aitermite_last_command="$cmd"; }
__aitermite_postfail(){ local code=$?; if [ "$code" -ne 0 ] && [ -n "$__aitermite_last_command" ]; then aitermite --postfail "$code" -- "$__aitermite_last_command" 2>/dev/null || true; fi; return $code; }
trap '__aitermite_preexec' DEBUG
if [ -n "${PROMPT_COMMAND:-}" ]; then PROMPT_COMMAND="__aitermite_postfail; $PROMPT_COMMAND"; else PROMPT_COMMAND="__aitermite_postfail"; fi
alias ait='aitermite'
alias af='aitermite'
alias ai='aitermite ask'
alias aicheck='aitermite --precheck'
'''


def fish_init() -> str:
    return r'''
# AITERMITE fish integration
function __aitermite_postfail --on-event fish_postexec
    set -l code $status
    if test $code -ne 0
        set -l line (string join " " $argv)
        if test -n "$line"
            aitermite --postfail $code -- "$line" 2>/dev/null
        end
    end
end
alias ait aitermite
alias af aitermite
alias ai "aitermite ask"
alias aicheck "aitermite --precheck"
'''


def powershell_init(launcher: str | None = None) -> str:
    launcher = launcher or launcher_command()
    template = r'''
# AITERMITE PowerShell integration
if (-not $global:__AITERMITE_ORIGINAL_PROMPT) { $global:__AITERMITE_ORIGINAL_PROMPT = (Get-Command prompt).ScriptBlock }
$global:__AITERMITE_LAST_HISTORY_ID = 0
function global:prompt {
    $ok = $?
    $native = $global:LASTEXITCODE
    # Prefer $? : PowerShell-native failures (e.g. command-not-found typos) do
    # NOT update $LASTEXITCODE, so a stale 0 would otherwise hide the failure.
    $code = if (-not $ok) { if (($native -is [int]) -and ($native -ne 0)) { [int]$native } else { 1 } } else { 0 }
    try {
        $hist = Get-History -Count 1 -ErrorAction SilentlyContinue
        if ($hist -and $hist.Id -ne $global:__AITERMITE_LAST_HISTORY_ID -and $code -ne 0) {
            $global:__AITERMITE_LAST_HISTORY_ID = $hist.Id
            $cmd = [string]$hist.CommandLine
            if ($cmd -and -not $cmd.TrimStart().StartsWith("aitermite")) { __LAUNCHER__ --postfail $code -- $cmd 2>$null }
        }
    } catch {}
    $global:LASTEXITCODE = $native  # restore so the hook is transparent to the user
    & $global:__AITERMITE_ORIGINAL_PROMPT
}
# Functions (not Set-Alias) so 'ait'/'af' work even when aitermite is not on PATH.
function global:ait { __LAUNCHER__ @args }
function global:af { __LAUNCHER__ @args }
function global:ai { __LAUNCHER__ ask @args }
function global:aicheck { __LAUNCHER__ --precheck @args }
'''
    # PowerShell needs the call operator (&) when the launcher is a quoted path.
    invoke = launcher if launcher.lstrip().startswith("&") else (f"& {launcher}" if launcher.startswith('"') else launcher)
    return template.replace("__LAUNCHER__", invoke)


def cmd_init() -> str:
    return r'''
@echo off
REM AITERMITE cmd.exe helpers. For automatic cmd.exe hooks, install Clink and use aitermite --install-shell clink.
doskey ait=aitermite $*
doskey af=aitermite $*
doskey ai=aitermite ask $*
doskey aicheck=aitermite --precheck $*
where clink >nul 2>nul
if %ERRORLEVEL% EQU 0 clink inject --quiet >nul 2>nul
'''


def clink_lua() -> str:
    return r'''
-- AITERMITE Clink integration for cmd.exe
local last_line = ""
local busy = false
clink.onendedit(function(line) if line and line ~= "" then last_line = line end end)
clink.prompt.register_filter(function(prompt)
    if busy or last_line == "" then return prompt end
    local code = os.geterrorlevel and os.geterrorlevel() or 0
    if code and code ~= 0 then
        busy = true
        os.execute('aitermite --postfail ' .. tostring(code) .. ' -- ' .. string.format('%q', last_line))
        last_line = ""
        busy = false
    end
    return prompt
end, 50)
'''


def universal_init() -> str:
    return r'''
# AITERMITE universal helper
alias ait='aitermite'
alias af='aitermite'
alias ai='aitermite ask'
alias aicheck='aitermite --precheck'
arun(){ "$@"; code=$?; if [ "$code" -ne 0 ]; then aitermite --postfail "$code" -- "$*" 2>/dev/null || true; fi; return "$code"; }
'''


def shell_init(shell: str) -> str:
    shell = (shell or "auto").lower()
    if shell == "auto": shell = detect_shell()
    if shell == "zsh": return zsh_init()
    if shell == "bash": return bash_init()
    if shell == "fish": return fish_init()
    if shell in {"powershell", "pwsh"}: return powershell_init()
    if shell == "cmd": return cmd_init()
    if shell == "clink": return clink_lua()
    if shell == "universal": return universal_init()
    raise ValueError(f"Unsupported shell: {shell}")
