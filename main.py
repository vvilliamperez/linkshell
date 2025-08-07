import os
import sys
import time
import threading
import tempfile
import wave
import queue
from dataclasses import dataclass

import numpy as np
import sounddevice as sd
from pynput import keyboard
from pynput.keyboard import Key, KeyCode, Controller as KeyController
import pyperclip
from dotenv import load_dotenv

try:
    from openai import OpenAI
except ImportError:
    print("The 'openai' package is required. Run: pip install -r requirements.txt", file=sys.stderr)
    sys.exit(1)


@dataclass
class Config:
    api_key: str
    model: str = "whisper-1"
    mode: str = "push_to_talk"  # or "toggle"
    hotkey_modifiers: list = None
    hotkey_key: str = "space"
    sample_rate_hz: int = 16000
    min_record_ms: int = 200
    output_mode: str = "paste"  # or "type"
    type_char_delay_ms: int = 0

    @staticmethod
    def from_env() -> "Config":
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            print("OPENAI_API_KEY is not set. Put it in .env or export it.", file=sys.stderr)
        model = os.getenv("OPENAI_TRANSCRIBE_MODEL", "whisper-1").strip() or "whisper-1"
        mode = os.getenv("MODE", "push_to_talk").strip() or "push_to_talk"
        modifiers_raw = os.getenv("HOTKEY_MODIFIERS", "cmd,shift").strip()
        hotkey_key = os.getenv("HOTKEY_KEY", "space").strip()
        sample_rate_hz = int(os.getenv("SAMPLE_RATE_HZ", "16000"))
        min_record_ms = int(os.getenv("MIN_RECORD_MS", "200"))
        output_mode = os.getenv("OUTPUT_MODE", "paste").strip()
        type_char_delay_ms = int(os.getenv("TYPE_CHAR_DELAY_MS", "0"))

        modifiers = [m.strip().lower() for m in modifiers_raw.split(",") if m.strip()] if modifiers_raw else []

        return Config(
            api_key=api_key,
            model=model,
            mode=mode,
            hotkey_modifiers=modifiers,
            hotkey_key=hotkey_key.lower(),
            sample_rate_hz=sample_rate_hz,
            min_record_ms=min_record_ms,
            output_mode=output_mode,
            type_char_delay_ms=type_char_delay_ms,
        )


class AudioRecorder:
    def __init__(self, sample_rate_hz: int = 16000):
        self.sample_rate_hz = sample_rate_hz
        self.stream = None
        self.frames_queue: queue.Queue[np.ndarray] = queue.Queue()
        self.started_at_ms = 0
        self.is_recording = False

    def _callback(self, indata, frames, time_info, status):  # noqa: ARG002
        if self.is_recording:
            # indata is float32 [-1, 1]
            self.frames_queue.put(indata.copy())

    def start(self):
        if self.is_recording:
            return
        self.frames_queue = queue.Queue()
        self.stream = sd.InputStream(
            channels=1,
            samplerate=self.sample_rate_hz,
            callback=self._callback,
            dtype="float32",
        )
        self.stream.start()
        self.started_at_ms = int(time.time() * 1000)
        self.is_recording = True
        print("[stt] Recording started")

    def stop_and_save_wav(self, path: str) -> int:
        if not self.is_recording:
            return 0
        self.is_recording = False
        try:
            if self.stream is not None:
                self.stream.stop()
                self.stream.close()
        finally:
            self.stream = None
        # drain queue
        frames = []
        while not self.frames_queue.empty():
            frames.append(self.frames_queue.get())
        if not frames:
            return 0
        # concatenate to single array
        audio = np.concatenate(frames, axis=0)
        # convert to int16 PCM
        audio_int16 = np.clip(audio, -1.0, 1.0)
        audio_int16 = (audio_int16 * 32767.0).astype(np.int16)
        with wave.open(path, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.sample_rate_hz)
            wf.writeframes(audio_int16.tobytes())
        duration_ms = int(1000 * audio_int16.shape[0] / self.sample_rate_hz)
        print(f"[stt] Saved WAV: {path} ({duration_ms} ms)")
        return duration_ms


class Transcriber:
    def __init__(self, api_key: str, model: str):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def transcribe_file(self, wav_path: str) -> str:
        try:
            with open(wav_path, "rb") as f:
                resp = self.client.audio.transcriptions.create(
                    model=self.model,
                    file=f,
                )
            text = getattr(resp, "text", None)
            if not text:
                text = str(resp)
            return text.strip()
        except Exception as e:
            print(f"[stt] Transcription error: {e}", file=sys.stderr)
            return ""


class Typer:
    def __init__(self, mode: str = "paste", char_delay_ms: int = 0):
        self.mode = mode
        self.char_delay = max(0, char_delay_ms) / 1000.0
        self.ctrl = KeyController()

    def _paste(self, text: str):
        if not text:
            return
        pyperclip.copy(text)
        # simulate Cmd+V
        with self.ctrl.pressed(Key.cmd):
            self.ctrl.press('v')
            self.ctrl.release('v')

    def _type(self, text: str):
        if not text:
            return
        for ch in text:
            self.ctrl.type(ch)
            if self.char_delay > 0:
                time.sleep(self.char_delay)

    def send(self, text: str):
        if not text:
            return
        if self.mode == "paste":
            self._paste(text)
        else:
            self._type(text)


def key_from_string(key_name: str):
    name = key_name.lower()
    special = {
        "space": Key.space,
        "enter": Key.enter,
        "return": Key.enter,
        "tab": Key.tab,
        "esc": Key.esc,
        "escape": Key.esc,
        "caps_lock": Key.caps_lock,
        "shift": Key.shift,
        "cmd": Key.cmd,
        "alt": Key.alt,
        "option": Key.alt,
        "ctrl": Key.ctrl,
        "control": Key.ctrl,
        "backspace": Key.backspace,
        "delete": Key.delete,
        "f18": Key.f18,
        "home": Key.home,
        "grave": KeyCode.from_char('`'),
    }
    if name in special:
        return special[name]
    if len(name) == 1:
        return KeyCode.from_char(name)
    # fallback: try function keys dynamically like f1..f24
    if name.startswith('f') and name[1:].isdigit():
        idx = int(name[1:])
        try:
            return getattr(Key, f'f{idx}')
        except AttributeError:
            return KeyCode.from_char(name)
    return KeyCode.from_char(name)


def build_modifier_set(modifiers: list[str]) -> set:
    mapping = {
        "cmd": Key.cmd,
        "shift": Key.shift,
        "alt": Key.alt,
        "ctrl": Key.ctrl,
    }
    return {mapping[m] for m in modifiers if m in mapping}


class HotkeyEngine:
    def __init__(self, config: Config, recorder: AudioRecorder, transcriber: Transcriber, typer: Typer):
        self.config = config
        self.recorder = recorder
        self.transcriber = transcriber
        self.typer = typer

        self.required_mods = build_modifier_set(config.hotkey_modifiers)
        self.trigger_key = key_from_string(config.hotkey_key)

        self.current_mods: set = set()
        self.is_trigger_down = False
        self.recording_active = False
        self.toggle_state = False
        self.listener = None

    def _should_start(self, key_pressed):
        return (
            key_pressed == self.trigger_key
            and self.required_mods.issubset(self.current_mods)
            and not self.recording_active
        )

    def _should_stop(self, key_released):
        # stop when trigger released or any required mod released
        return self.recording_active and (
            key_released == self.trigger_key or not self.required_mods.issubset(self.current_mods)
        )

    def _start_recording(self):
        if self.recording_active:
            return
        self.recorder.start()
        self.recording_active = True

    def _stop_and_transcribe_async(self):
        def worker():
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                wav_path = tmp.name
            duration_ms = self.recorder.stop_and_save_wav(wav_path)
            self.recording_active = False
            if duration_ms < self.config.min_record_ms:
                print(f"[stt] Recording too short ({duration_ms} ms); ignoring")
                try:
                    os.remove(wav_path)
                except OSError:
                    pass
                return
            text = self.transcriber.transcribe_file(wav_path)
            try:
                os.remove(wav_path)
            except OSError:
                pass
            if text:
                print(f"[stt] Transcribed: {text}")
                self.typer.send(text)
            else:
                print("[stt] No text returned")
        threading.Thread(target=worker, daemon=True).start()

    def on_press(self, key):
        # track modifiers
        if key in {Key.shift, Key.shift_r}:
            self.current_mods.add(Key.shift)
        elif key in {Key.ctrl, Key.ctrl_r}:
            self.current_mods.add(Key.ctrl)
        elif key in {Key.alt, Key.alt_r}:
            self.current_mods.add(Key.alt)
        elif key in {Key.cmd}:
            self.current_mods.add(Key.cmd)

        if self.config.mode == "toggle":
            if key == self.trigger_key and self.required_mods.issubset(self.current_mods) and not self.is_trigger_down:
                self.is_trigger_down = True
                self.toggle_state = not self.toggle_state
                if self.toggle_state:
                    self._start_recording()
                else:
                    self._stop_and_transcribe_async()
            return

        # push-to-talk
        if self._should_start(key):
            self.is_trigger_down = True
            self._start_recording()

    def on_release(self, key):
        # track modifiers up
        if key in {Key.shift, Key.shift_r}:
            self.current_mods.discard(Key.shift)
        elif key in {Key.ctrl, Key.ctrl_r}:
            self.current_mods.discard(Key.ctrl)
        elif key in {Key.alt, Key.alt_r}:
            self.current_mods.discard(Key.alt)
        elif key in {Key.cmd}:
            self.current_mods.discard(Key.cmd)

        if self.config.mode == "toggle":
            if key == self.trigger_key:
                self.is_trigger_down = False
            return

        # push-to-talk
        if key == self.trigger_key and self.is_trigger_down:
            self.is_trigger_down = False
            if self.recording_active:
                self._stop_and_transcribe_async()
        elif self._should_stop(key):
            if self.recording_active:
                self._stop_and_transcribe_async()

    def run(self):
        print("[stt] Hotkey engine running.")
        mods = "+".join(self.config.hotkey_modifiers) if self.config.hotkey_modifiers else "(none)"
        print(f"[stt] Hold {mods}+{self.config.hotkey_key} to dictate (mode={self.config.mode}).")
        with keyboard.Listener(on_press=self.on_press, on_release=self.on_release) as listener:
            self.listener = listener
            listener.join()


def main():
    config = Config.from_env()
    if not config.api_key:
        print("Set OPENAI_API_KEY before running.")
        sys.exit(1)

    recorder = AudioRecorder(sample_rate_hz=config.sample_rate_hz)
    transcriber = Transcriber(api_key=config.api_key, model=config.model)
    typer = Typer(mode=config.output_mode, char_delay_ms=config.type_char_delay_ms)
    engine = HotkeyEngine(config, recorder, transcriber, typer)

    try:
        engine.run()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main() 