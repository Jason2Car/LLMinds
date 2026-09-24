"""
Loads the two separate config files:

    config/weights.json     -- target trait profile (Big-5 + Dark Triad,
                                0-100 each), tolerance, iteration limits
    config/background.json  -- persona backstory, kept separate from the
                                trait weights so you can swap either one
                                independently

Also holds which model plays each role in the CRISP loop.
"""

import json
import os

_CONFIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config")
_WEIGHTS_PATH = os.path.join(_CONFIG_DIR, "weights.json")
_BACKGROUND_PATH = os.path.join(_CONFIG_DIR, "background.json")

# The 8 trait dimensions every profile, score, and evaluation is defined over.
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

# Which model plays each role in the loop.
GENERATOR_MODEL = "gpt-4o"
EVALUATOR_MODEL = "gpt-4o"
REFINER_MODEL = "gpt-4o"


def load_weights(path: str = _WEIGHTS_PATH) -> dict:
    with open(path) as f:
        weights = json.load(f)

    missing_profile = set(TRAIT_DIMENSIONS) - set(weights["target_profile"])
    if missing_profile:
        raise ValueError(f"weights.json target_profile is missing traits: {missing_profile}")

    if not isinstance(weights.get("tolerance"), dict):
        raise ValueError(
            "weights.json 'tolerance' must be a per-trait object, e.g. "
            '{"openness": 20, ..., "psychopathy": 8}, not a single number.'
        )

    missing_tolerance = set(TRAIT_DIMENSIONS) - set(weights["tolerance"])
    if missing_tolerance:
        raise ValueError(f"weights.json tolerance is missing traits: {missing_tolerance}")

    return weights


def load_background(path: str = _BACKGROUND_PATH) -> dict:
    with open(path) as f:
        return json.load(f)
