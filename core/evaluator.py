"""
Stage 3: Trait Evaluator.

Scores the candidate response against T along each of the 8 trait
dimensions and identifies the trait with the largest deviation from
target.
"""

import config
import llm_client
import prompts
from config import TRAIT_DIMENSIONS


def evaluate_response(target_profile: dict, response_text: str) -> dict:
    prompt = prompts.evaluator_prompt(target_profile, response_text)
    result = llm_client.call_json(config.EVALUATOR_MODEL, prompt)
    scores = result["scores"]

    deviations = {trait: abs(scores[trait] - target_profile[trait]) for trait in TRAIT_DIMENSIONS}
    worst_trait = max(deviations, key=deviations.get)

    return {
        "scores": scores,
        "deviations": deviations,
        "worst_trait": worst_trait,
        "worst_deviation": deviations[worst_trait],
    }


def within_tolerance(evaluation: dict, tolerance: int) -> bool:
    return evaluation["worst_deviation"] <= tolerance
