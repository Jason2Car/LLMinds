"""
Loads config files for a given personality profile.

Profiles live under config/profiles/<name>/, each containing:
    weights.json      -- target trait vector, tolerance, iteration limits
    background.json   -- persona backstory and tone notes

Falls back to config/weights.json and config/background.json if no
profile is selected (backwards compatible).

Also holds which model plays each role in the CRISP loop, and reads the
voice-input settings (VOICE_INPUT, WHISPER_MODEL, VOICE_INPUT_DURATION)
from config.env.
"""

import json
import os

_CONFIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config")
_PROFILES_DIR = os.path.join(_CONFIG_DIR, "profiles")
_ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.env")

AVAILABLE_PROFILES = ["narcissistic", "machiavellian", "psychopathic", "baseline"]

_active_profile = None


def _load_env(path: str = _ENV_FILE) -> dict:
    values = {}
    if not os.path.exists(path):
        return values
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


_env = _load_env()

# Voice input: when VOICE_INPUT=true in config.env, app.py records from the
# microphone and transcribes with OpenAI Whisper instead of reading typed
# text. See voice_input.py.
VOICE_INPUT_ENABLED = _env.get("VOICE_INPUT", "false").strip().lower() in ("1", "true", "yes")
WHISPER_MODEL = _env.get("WHISPER_MODEL", "whisper-1")
VOICE_INPUT_DURATION = int(_env.get("VOICE_INPUT_DURATION", "5"))

TRAIT_DIMENSIONS = [
    "openness",
    "conscientiousness",
    "extraversion",
    "agreeableness",
    "neuroticism",
    "narcissism",
    "machiavellianism",
    "psychopathy",
]

GENERATOR_MODEL = "gpt-4o"
EVALUATOR_MODEL = "gpt-4o"
REFINER_MODEL = "gpt-4o"


def set_profile(name: str) -> None:
    global _active_profile
    if name not in AVAILABLE_PROFILES:
        raise ValueError(
            f"Unknown profile '{name}'. Available: {AVAILABLE_PROFILES}"
        )
    profile_dir = os.path.join(_PROFILES_DIR, name)
    if not os.path.isdir(profile_dir):
        raise FileNotFoundError(f"Profile directory not found: {profile_dir}")
    _active_profile = name


def get_active_profile() -> str | None:
    return _active_profile


def _resolve_paths() -> tuple[str, str]:
    if _active_profile:
        profile_dir = os.path.join(_PROFILES_DIR, _active_profile)
        return (
            os.path.join(profile_dir, "weights.json"),
            os.path.join(profile_dir, "background.json"),
        )
    return (
        os.path.join(_CONFIG_DIR, "weights.json"),
        os.path.join(_CONFIG_DIR, "background.json"),
    )


def load_weights(path: str | None = None) -> dict:
    if path is None:
        path = _resolve_paths()[0]
    with open(path) as f:
        weights = json.load(f)

    missing = set(TRAIT_DIMENSIONS) - set(weights["target_profile"])
    if missing:
        raise ValueError(f"weights.json target_profile is missing traits: {missing}")

    return weights


def load_background(path: str | None = None) -> dict:
    if path is None:
        path = _resolve_paths()[1]
    with open(path) as f:
        return json.load(f)
