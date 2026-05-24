from __future__ import annotations

CYAN = "\033[96m"
RESET = "\033[0m"

INSTALL_ANIMATION = [
    "AITERMITE  ◖>_       ◗  scanning shell",
    "AITERMITE  ◖ >_      ◗  wiring hooks",
    "AITERMITE  ◖  >_     ◗  enabling pre-enter guard",
    "AITERMITE  ◖   >_    ◗  enabling post-failure AI",
    "AITERMITE  ◖    >_   ◗  setting latency budget",
    "AITERMITE  ◖     >_  ◗  loading cyan terminal skin",
    "AITERMITE  ◖      >_ ◗  ready",
]

def animation_text(color: bool = True) -> str:
    return "\n".join((CYAN + x + RESET) if color else x for x in INSTALL_ANIMATION)

def zsh_init() -> str:
    return r'''
# AITERMITE zsh integration
_aitermite_preexec(){ export AITERMITE_LAST_COMMAND="$1"; }
_aitermite_precmd(){ local code=$?; if [ "$code" -ne 0 ] && [ -n "$AITERMITE_LAST_COMMAND" ]; then aitermite --postfail "$code" -- "$AITERMITE_LAST_COMMAND" 2>/dev/null; fi }
autoload -Uz add-zsh-hook
add-zsh-hook preexec _aitermite_preexec
add-zsh-hook precmd _aitermite_precmd
'''

def bash_init() -> str:
    return r'''
# AITERMITE bash integration
_aitermite_prompt(){ local code=$?; local cmd=$(history 1 | sed 's/^ *[0-9]* *//'); if [ "$code" -ne 0 ] && [ -n "$cmd" ]; then aitermite --postfail "$code" -- "$cmd" 2>/dev/null; fi }
PROMPT_COMMAND="_aitermite_prompt${PROMPT_COMMAND:+;$PROMPT_COMMAND}"
alias ait='aitermite'
'''

def fish_init() -> str:
    return r'''
# AITERMITE fish integration
function __aitermite_postfail --on-event fish_postexec
    set -l code $status
    if test $code -ne 0
        aitermite --postfail $code -- $argv 2>/dev/null
    end
end
alias ait aitermite
'''

def powershell_init() -> str:
    return r'''
# AITERMITE PowerShell integration
function Invoke-AitermitePostFail {
  if ($LASTEXITCODE -ne 0) {
    $cmd = (Get-History -Count 1).CommandLine
    if ($cmd) { aitermite --postfail $LASTEXITCODE -- $cmd }
  }
}
$global:__AitermitePrompt = $function:prompt
function prompt { Invoke-AitermitePostFail; if ($global:__AitermitePrompt) { & $global:__AitermitePrompt } else { "PS> " } }
Set-Alias ait aitermite
'''

def cmd_init() -> str:
    return r'''
@echo off
DOSKEY ait=aitermite $*
DOSKEY af=aitermite $*
DOSKEY aicheck=aitermite --precheck $*
where clink >nul 2>nul && clink inject --quiet
'''

def clink_lua() -> str:
    return r'''
-- AITERMITE Clink cmd.exe auto post-failure hook
local last_cmd = ""
local function aitermite_filter(line) last_cmd = line; return line end
clink.onfilterinput(aitermite_filter)
clink.onendedit(function(line) last_cmd = line end)
clink.onbeginedit(function() end)
clink.prompt.register_filter(function(prompt)
  local code = os.getenv("ERRORLEVEL") or "0"
  if last_cmd ~= "" and code ~= "0" then
    os.execute("aitermite --postfail " .. code .. " -- " .. string.format("%q", last_cmd))
    last_cmd = ""
  end
  return prompt
end, 90)
'''

def universal_init() -> str:
    return r'''
# AITERMITE universal POSIX helper
alias ait='aitermite'
arun(){ "$@"; local code=$?; if [ $code -ne 0 ]; then aitermite --postfail $code -- "$*"; fi; return $code; }
'''

def shell_init(shell: str) -> str:
    shell = (shell or "auto").lower()
    if shell in {"zsh", "auto"}: return zsh_init()
    if shell == "bash": return bash_init()
    if shell == "fish": return fish_init()
    if shell in {"powershell", "pwsh"}: return powershell_init()
    if shell == "cmd": return cmd_init()
    if shell == "clink": return clink_lua()
    if shell == "universal": return universal_init()
    raise ValueError(f"Unsupported shell: {shell}")
