"""
Stage 1: Trait Profile Specification.

Just loads and exposes the target vector T = {t1...t8} from weights.json,
plus tolerance and iteration settings -- separate from the persona
background, per your request to keep weights and background in
separate files.
"""

import config


def get_target_profile() -> dict:
    weights = config.load_weights()
    return weights["target_profile"]


def get_search_settings() -> dict:
    weights = config.load_weights()
    return {
        "tolerance": weights["tolerance"],
        "max_iterations": weights["max_iterations"],
        "broad_search_deviation_threshold": weights["broad_search_deviation_threshold"],
    }


def get_background() -> dict:
    return config.load_background()
