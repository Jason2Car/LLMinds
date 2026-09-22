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

    missing = set(TRAIT_DIMENSIONS) - set(weights["target_profile"])
    if missing:
        raise ValueError(f"weights.json target_profile is missing traits: {missing}")

    return weights


def load_background(path: str = _BACKGROUND_PATH) -> dict:
    with open(path) as f:
        return json.load(f)
