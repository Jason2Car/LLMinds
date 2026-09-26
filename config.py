"""
Loads config files for a given personality profile.

Profiles live under config/profiles/<name>/, each containing:
    weights.json      -- target trait vector, tolerance, iteration limits
    background.json   -- persona backstory and tone notes

Falls back to config/weights.json and config/background.json if no
profile is selected (backwards compatible).

Also holds which model plays each role in the CRISP loop.
"""

import json
import os

_CONFIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config")
_PROFILES_DIR = os.path.join(_CONFIG_DIR, "profiles")

AVAILABLE_PROFILES = ["narcissistic", "machiavellian", "psychopathic", "baseline"]

_active_profile = None

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
