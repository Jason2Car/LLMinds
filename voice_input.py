"""
Optional voice input for app.py, transcribed with OpenAI's Whisper API.

Enabled by setting VOICE_INPUT=true in config.env (see config.env.example).
When enabled, app.py calls record_and_transcribe() instead of input() to
get each turn's user message. How a turn is recorded depends on
VOICE_INPUT_MODE:

    hold    (default) push-to-talk: hold PUSH_TO_TALK_KEY (Shift by default)
            while speaking, release it to send. Needs `pip install pynput`
            and, on macOS, Accessibility / Input Monitoring permission for
            the app the terminal runs in. Falls back to "toggle" if either
            is missing.
    toggle  press Enter to start talking and Enter again to send. Works in
            any terminal with no extra permissions. Typing a message instead
            of pressing Enter sends the typed text (so `exit` still works).
    fixed   record a fixed VOICE_INPUT_DURATION seconds (the original mode).

Recordings stop automatically after VOICE_INPUT_MAX_SECONDS.

Requires: pip install sounddevice scipy   (plus pynput for "hold")
"""

import os
import sys
import tempfile
import threading
import time

import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write as write_wav

import config
import llm_client

_SAMPLE_RATE = 16000
_MIN_SECONDS = 0.3  # shorter than this is treated as an accidental tap
_SILENCE_PEAK = 500  # int16 peak below this = no speech (speech peaks in the thousands)
_hold_unavailable = False  # set once hold mode fails, so we warn only once


class _Recorder:
    """Records from the default microphone between start() and stop()."""

    def __init__(self):
        self._chunks = []
        self._stream = None
        self.started_at = None

    def _callback(self, indata, frames, time_info, status):
        self._chunks.append(indata.copy())

    def start(self):
        self._chunks = []
        self._stream = sd.InputStream(
            samplerate=_SAMPLE_RATE, channels=1, dtype="int16", callback=self._callback
        )
        self._stream.start()
        self.started_at = time.monotonic()

    @property
    def recording(self) -> bool:
        return self._stream is not None

    def elapsed(self) -> float:
        return time.monotonic() - self.started_at if self.started_at else 0.0

    def stop(self) -> np.ndarray:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        if not self._chunks:
            return np.zeros((0, 1), dtype=np.int16)
        return np.concatenate(self._chunks)


def _key_label(name: str) -> str:
    return name.capitalize() if len(name) > 1 else f"'{name}'"


def _record_hold():
    """Push-to-talk. Returns audio, or None if hold mode can't run here."""
    global _hold_unavailable
    try:
        from pynput import keyboard
    except ImportError:
        print("[push-to-talk needs `pip install pynput`; using Enter to start/stop instead]")
        _hold_unavailable = True
        return None

    target = config.PUSH_TO_TALK_KEY.lower()

    def matches(key) -> bool:
        name = (getattr(key, "name", None) or getattr(key, "char", None) or "").lower()
        # "shift" matches left and right Shift (Key.shift, Key.shift_r), etc.
        return name == target or name.startswith(target + "_")

    rec = _Recorder()
    done = threading.Event()

    def on_press(key):
        if matches(key) and not rec.recording and not done.is_set():
            rec.start()
            print("[recording... release to send]")

    def on_release(key):
        if matches(key) and rec.recording:
            done.set()
            return False  # stops the listener

    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()
    listener.wait()
    time.sleep(0.2)
    # Without macOS permission the listener either exits at once or stays
    # alive but never receives key events; IS_TRUSTED (macOS only) catches
    # the second case.
    if not listener.is_alive() or getattr(listener, "IS_TRUSTED", True) is False:
        listener.stop()
        if sys.platform == "darwin":
            print(
                "[push-to-talk is blocked by macOS. To enable it: System Settings > "
                "Privacy & Security > Accessibility > turn on the app this terminal "
                "runs in (Terminal, iTerm, VS Code, Claude...), then quit and reopen "
                "that app. Using Enter to start/stop for now.]"
            )
        else:
            print("[push-to-talk is unavailable here; using Enter to start/stop instead]")
        _hold_unavailable = True
        return None

    print(f"[hold {_key_label(target)} to talk, release to send]")
    try:
        while not done.wait(0.1):
            if rec.recording and rec.elapsed() >= config.VOICE_INPUT_MAX_SECONDS:
                print(f"[reached {config.VOICE_INPUT_MAX_SECONDS}s limit, sending]")
                break
    finally:
        listener.stop()
        audio = rec.stop()
    return audio


def _record_toggle():
    """Enter to start, Enter to stop. Returns audio, or typed text (str)."""
    typed = input("[press Enter to talk, or type a message] ").strip()
    if typed:
        return typed
    rec = _Recorder()
    rec.start()
    try:
        input(f"[recording... press Enter to send (max {config.VOICE_INPUT_MAX_SECONDS}s)]")
    finally:
        audio = rec.stop()
    return audio[: config.VOICE_INPUT_MAX_SECONDS * _SAMPLE_RATE]


def _record_fixed(duration: int):
    print(f"[recording for {duration}s, speak now...]")
    audio = sd.rec(int(duration * _SAMPLE_RATE), samplerate=_SAMPLE_RATE, channels=1, dtype="int16")
    sd.wait()
    return audio


def _transcribe(audio: np.ndarray) -> str:
    print("[transcribing...]")
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name
        write_wav(tmp_path, _SAMPLE_RATE, audio)
    try:
        return llm_client.transcribe(
            tmp_path, model=config.WHISPER_MODEL, language=config.WHISPER_LANGUAGE or None
        )
    finally:
        os.remove(tmp_path)


def record_and_transcribe(duration: int | None = None) -> str:
    """Record one turn from the default mic (see VOICE_INPUT_MODE) and
    return the Whisper transcript. Retries on accidental taps."""
    while True:
        mode = config.VOICE_INPUT_MODE
        if mode == "hold" and _hold_unavailable:
            mode = "toggle"

        if mode == "fixed":
            audio = _record_fixed(duration or config.VOICE_INPUT_DURATION)
        elif mode == "hold":
            audio = _record_hold()
            if audio is None:
                continue  # fall back to toggle on the next pass
        else:
            audio = _record_toggle()

        if isinstance(audio, str):  # typed instead of spoken (toggle mode)
            return audio
        if len(audio) < _MIN_SECONDS * _SAMPLE_RATE:
            print("[too short, try again]")
            continue
        if np.abs(audio).max() < _SILENCE_PEAK:
            # Whisper tends to invent sentences from silence, so don't send it.
            print("[didn't hear anything, try again]")
            continue
        return _transcribe(audio)
