"""
Optional voice input for app.py, transcribed with OpenAI's Whisper API.

Enabled by setting VOICE_INPUT=true in config.env (see config.env.example).
When enabled, app.py calls record_and_transcribe() instead of input() to
get each turn's user message: it records a fixed-length clip from the
default microphone, sends it to Whisper, and returns the transcript text.

Requires: pip install sounddevice scipy
"""

import os
import tempfile

import sounddevice as sd
from scipy.io.wavfile import write as write_wav

import config
import llm_client

_SAMPLE_RATE = 16000


def record_and_transcribe(duration: int | None = None) -> str:
    """Record `duration` seconds of audio from the default mic and
    transcribe it with OpenAI Whisper. Uses config.VOICE_INPUT_DURATION
    and config.WHISPER_MODEL when not overridden."""
    duration = duration or config.VOICE_INPUT_DURATION

    print(f"[recording for {duration}s, speak now...]")
    audio = sd.rec(int(duration * _SAMPLE_RATE), samplerate=_SAMPLE_RATE, channels=1, dtype="int16")
    sd.wait()
    print("[transcribing...]")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name
        write_wav(tmp_path, _SAMPLE_RATE, audio)

    try:
        return llm_client.transcribe(tmp_path, model=config.WHISPER_MODEL)
    finally:
        os.remove(tmp_path)
