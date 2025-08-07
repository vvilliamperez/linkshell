![Linkshell STT Hotkey](./cid.png)

# Linkshell STT Hotkey (macOS)

A lightweight macOS background tool that lets you press-and-hold a hotkey to dictate anywhere on your Mac. While the hotkey is held, it records your microphone, sends the audio to OpenAI's transcription API, and then types the resulting text into the currently focused application.

- Default hotkey: Cmd+Shift+Space (hold to record; release to transcribe and type)
- Mode: push-to-talk by default; toggle mode available
- Output: types keystrokes into the active app

## Quick setup (recommended)

```bash
# 1) Install PortAudio (for mic capture)
brew list portaudio >/dev/null 2>&1 || brew install portaudio

# 2) From the repo root
git clone https://github.com/vvilliamperez/linkshell.git
cd linkshell

# 3) One-shot setup
./setup.sh

# 4) Add your API key
# Edit .env and set OPENAI_API_KEY=...

# 5) Run (first time in foreground to grant permissions)
./run.sh
```

- On first run, macOS will prompt for Microphone and Accessibility permissions.
- Hold your hotkey, speak, release. Text should paste/type into the active app.

## Requirements
- macOS on Apple Silicon (M1/M2/M3/M4)
- Python 3.10+
- Homebrew (for PortAudio dependency)
- An OpenAI API key with access to `whisper-1` or `gpt-4o-mini-transcribe`

## Manual install

1) Install PortAudio (needed for microphone recording):

```bash
brew list portaudio >/dev/null 2>&1 || brew install portaudio
```

2) Create a virtual environment and install dependencies:

```bash
cd /path/to/linkshell   # repo root (this folder)
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

3) Set your OpenAI API key:

```bash
cp example.env .env
# then edit .env and set OPENAI_API_KEY=... (or export OPENAI_API_KEY in your shell)
```

4) First run (foreground) to grant permissions:

```bash
source .venv/bin/activate
python main.py
```

## Run at login

- Preferred: let the setup script install a LaunchAgent with the correct absolute path for your clone location.

```bash
./setup.sh --install-launchagent
# then start it (or log out and back in)
launchctl start com.linkshell.stt
```

- Alternate (manual): copy the provided plist (generic) into your LaunchAgents. If you cloned the repo to a non-standard folder, prefer the setup script instead.

```bash
launchctl unload "$HOME/Library/LaunchAgents/com.linkshell.stt.plist" 2>/dev/null || true
cp ./com.linkshell.stt.plist "$HOME/Library/LaunchAgents/"
launchctl load "$HOME/Library/LaunchAgents/com.linkshell.stt.plist"
launchctl start com.linkshell.stt
```

## Configuration
Configure via environment variables (in `.env` or exported in your shell):

- `OPENAI_API_KEY`: Your API key (required)
- `OPENAI_TRANSCRIBE_MODEL`:
  - `whisper-1` (classic Whisper API)
  - `gpt-4o-mini-transcribe` (fast/light transcription)
  - default: `whisper-1`
- `HOTKEY_MODIFIERS`: Comma-separated list of modifiers. Options: `cmd`, `shift`, `alt`, `ctrl`.
  - default: `cmd,shift`
- `HOTKEY_KEY`: The trigger key to hold. Examples: `space`, `home`, `grave`, `caps_lock` (caps lock requires Karabiner remap), `f18` (if available).
  - default: `space`
- `MODE`: `push_to_talk` or `toggle`.
  - default: `push_to_talk`
- `SAMPLE_RATE_HZ`: Recording sample rate. Default `16000`.
- `TYPE_CHAR_DELAY_MS`: Delay between typed characters (for very slow apps). Default `0`.

### Use the Home key only
Set no modifiers and use the Home key as the trigger:

```bash
HOTKEY_MODIFIERS=
HOTKEY_KEY=home
MODE=push_to_talk
```

## Caps Lock or other special triggers
Capturing Caps Lock reliably across macOS apps is tricky. A common pattern is to remap Caps Lock to `F18` via Karabiner-Elements, and set `HOTKEY_KEY=f18`.

1) Install Karabiner-Elements (optional):
- Download from: https://karabiner-elements.pqrs.org/
- Remap Caps Lock to `F18` globally.
- Then set `HOTKEY_KEY=f18` and optionally remove modifiers (`HOTKEY_MODIFIERS=`).

## Uninstall

```bash
launchctl unload "$HOME/Library/LaunchAgents/com.linkshell.stt.plist" 2>/dev/null || true
rm -f "$HOME/Library/LaunchAgents/com.linkshell.stt.plist"
rm -rf .venv
```

## Troubleshooting
- If no text types: ensure your terminal or the Python interpreter has Accessibility permission. Try running `python main.py` manually once and approve prompts.
- If recording fails: ensure Microphone permission is granted to your terminal (or the Python binary in the venv if using LaunchAgent).
- If you see PortAudio errors: ensure `brew install portaudio` is complete before `pip install -r requirements.txt`.
- For better accuracy/latency, try switching models via `OPENAI_TRANSCRIBE_MODEL`. 