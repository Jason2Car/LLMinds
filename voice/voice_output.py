"""
Optional voice output for app.py, using OpenAI text-to-speech.

Enabled by setting VOICE_OUTPUT=true in config.env (see config.env.example).
When enabled, app.py calls speak() after printing each assistant reply, so
the participant can keep their eyes and hands on the LEGO build.

Playback uses the operating system's built-in player, so there are no extra
Python dependencies: afplay on macOS, aplay/paplay on Linux, winsound on
Windows. speak() blocks until the audio finishes, which also keeps voice
input (VOICE_INPUT=true) from recording the assistant's own voice.

A text-to-speech failure never ends the session: the reply has already been
printed, so speak() prints a warning and returns.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import time

import config
import llm_client


def _play_wav(path: str) -> None:
    if sys.platform == "darwin":
        subprocess.run(["afplay", path], check=True)
    elif sys.platform.startswith("win"):
        import winsound

        winsound.PlaySound(path, winsound.SND_FILENAME)
    else:
        player = shutil.which("aplay") or shutil.which("paplay")
        if not player:
            raise RuntimeError("no audio player found (install alsa-utils or pulseaudio-utils)")
        subprocess.run([player, path], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def speak(text: str) -> float | None:
    """Read `text` aloud. Returns seconds spent generating the audio (for
    logging), or None if text-to-speech failed or there was nothing to say."""
    text = (text or "").strip()
    if not text:
        return None

    start = time.monotonic()
    try:
        audio = llm_client.synthesize_speech(
            text,
            model=config.TTS_MODEL,
            voice=config.TTS_VOICE,
            instructions=config.TTS_INSTRUCTIONS,
        )
    except Exception as e:  # noqa: BLE001 - never crash the session over audio
        print(f"[voice output failed: {e}]")
        return None
    synth_seconds = time.monotonic() - start

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio)
        tmp_path = tmp.name
    try:
        _play_wav(tmp_path)
    except Exception as e:  # noqa: BLE001
        print(f"[could not play audio: {e}]")
    finally:
        os.remove(tmp_path)
    return synth_seconds
