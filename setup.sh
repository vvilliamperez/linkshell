#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
cd "$SCRIPT_DIR"

say_step() { printf "\n==> %s\n" "$*"; }
say_info() { printf "  - %s\n" "$*"; }
say_warn() { printf "[warn] %s\n" "$*"; }
say_err() { printf "[err] %s\n" "$*" >&2; }

say_step "Linkshell STT Hotkey setup"

# 1) OS check
if [[ "$(uname -s)" != "Darwin" ]]; then
  say_warn "This setup is intended for macOS. Continuing anyway."
fi

# 2) PortAudio via Homebrew
if command -v brew >/dev/null 2>&1; then
  if ! brew list portaudio >/dev/null 2>&1; then
    say_step "Installing PortAudio via Homebrew"
    brew install portaudio
  else
    say_info "PortAudio already installed"
  fi
else
  say_warn "Homebrew not found. Please install Homebrew and run: brew install portaudio"
fi

# 3) Python venv
if ! command -v python3 >/dev/null 2>&1; then
  say_err "python3 not found. Please install Python 3.10+ and re-run."
  exit 1
fi

if [[ ! -d .venv ]]; then
  say_step "Creating Python virtual environment (.venv)"
  python3 -m venv .venv
else
  say_info ".venv already exists"
fi

# shellcheck disable=SC1091
source .venv/bin/activate

say_step "Upgrading pip and installing Python dependencies"
python -m pip install -U pip
pip install -r requirements.txt

# 4) Env file
if [[ ! -f .env ]]; then
  if [[ -f example.env ]]; then
    cp example.env .env
    say_info "Created .env from example.env. Please edit and set OPENAI_API_KEY=..."
  else
    cat > .env <<'EOF'
OPENAI_API_KEY=
OPENAI_TRANSCRIBE_MODEL=whisper-1
MODE=push_to_talk
HOTKEY_MODIFIERS=
HOTKEY_KEY=home
SAMPLE_RATE_HZ=16000
MIN_RECORD_MS=200
OUTPUT_MODE=paste
TYPE_CHAR_DELAY_MS=0
EOF
    say_info "Created .env. Please edit and set OPENAI_API_KEY=..."
  fi
else
  say_info ".env already exists (will not overwrite)"
fi

# 5) Make run.sh executable
chmod +x run.sh || true

# 6) Optional: Install LaunchAgent with actual path
if [[ "${1:-}" == "--install-launchagent" ]]; then
  say_step "Installing LaunchAgent to run at login"
  LA_DIR="$HOME/Library/LaunchAgents"
  LA_PLIST="$LA_DIR/com.linkshell.stt.plist"
  mkdir -p "$LA_DIR"
  cat > "$LA_PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.linkshell.stt</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>-lc</string>
    <string>cd "${SCRIPT_DIR}"; ./run.sh</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>StandardOutPath</key>
  <string>/tmp/linkshell-stt.out.log</string>
  <key>StandardErrorPath</key>
  <string>/tmp/linkshell-stt.err.log</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
  </dict>
</dict>
</plist>
EOF
  launchctl unload "$LA_PLIST" 2>/dev/null || true
  launchctl load "$LA_PLIST"
  say_info "LaunchAgent installed. Start it now with: launchctl start com.linkshell.stt"
fi

say_step "Setup complete"
say_info "Next steps:"
say_info "1) Edit .env and set OPENAI_API_KEY=..."
say_info "2) Run: source .venv/bin/activate && python main.py (or ./run.sh)"
say_info "Optional: ./setup.sh --install-launchagent to run at login" 