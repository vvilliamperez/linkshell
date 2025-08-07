# Linkshell STT Hotkey (macOS)

A lightweight macOS background tool that lets you press-and-hold a hotkey to dictate anywhere on your Mac. While the hotkey is held, it records your microphone, sends the audio to OpenAI's transcription API, and then types the resulting text into the currently focused application.

- Default hotkey: Cmd+Shift+Space (hold to record; release to transcribe and type)
- Mode: push-to-talk by default; toggle mode available
- Output: types keystrokes into the active app

## Requirements
- macOS on Apple Silicon (M1/M2/M3/M4)
- Python 3.10+
- Homebrew (for PortAudio dependency)
- An OpenAI API key with access to `whisper-1` or `gpt-4o-mini-transcribe`

## Install

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

- On first microphone use, macOS will prompt for Microphone permission for `python`.
- On first keystroke injection, macOS will prompt for Accessibility permission for your terminal (e.g., Terminal or iTerm). Go to System Settings → Privacy & Security → Accessibility and enable your terminal app.

Once allowed, press and hold your hotkey, speak, and release. The recognized text should type into your current app.

## Run at login (optional)
You can use a LaunchAgent to auto-start the tool at login.

1) Edit the provided plist if needed and load it:

```bash
launchctl unload "$HOME/Library/LaunchAgents/com.linkshell.stt.plist" 2>/dev/null || true
cp ./com.linkshell.stt.plist "$HOME/Library/LaunchAgents/"
launchctl load "$HOME/Library/LaunchAgents/com.linkshell.stt.plist"
launchctl start com.linkshell.stt
```

Note: For Accessibility permissions when running as a LaunchAgent, macOS may attribute control to the Python interpreter inside the venv. If typing does not work, run `python main.py` once in the foreground from your terminal and re-grant Accessibility. 

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