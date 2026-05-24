#!/usr/bin/env bash
set -euo pipefail

aitermite --doctor
aitermite --precheck gti status
aitermite --provider heuristic --json git push
aitermite --shell-init zsh
