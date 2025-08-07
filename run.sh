#!/usr/bin/env bash
set -euo pipefail
# Resolve repo root as the directory containing this script
SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
cd "$SCRIPT_DIR"

# Load env if present
if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi

# Require virtualenv
if [[ ! -d .venv ]]; then
  echo "Virtualenv not found at .venv; please run setup in README." >&2
  exit 1
fi
source .venv/bin/activate

# Run
python main.py 