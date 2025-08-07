#!/usr/bin/env bash
set -euo pipefail
cd /Users/william.perez/Linkshell/stt_hotkey
if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi
if [[ ! -d .venv ]]; then
  echo "Virtualenv not found at .venv; please run setup in README." >&2
  exit 1
fi
source .venv/bin/activate
python /Users/william.perez/Linkshell/stt_hotkey/main.py 