"""
Stage 3: Trait Evaluator.

Scores the candidate response against T along each of the 8 trait
dimensions. Each trait has its own tolerance (some traits are allowed to
vary more than others), so "how bad" a deviation is depends on how far
it exceeds THAT trait's own tolerance, not raw distance from target.

We call (deviation - tolerance) the "excess": <=0 means the trait is
within its allowed range, >0 means it's over by that many points. The
flagged trait is whichever has the largest excess -- the one most
urgently violating its own allowed variance, not just the one with the
biggest raw gap (a loosely-toleranced trait can be way off but still
fine; a tightly-toleranced trait can be only slightly off but still the
most urgent problem).
"""

import config
import llm_client
import prompts
from config import TRAIT_DIMENSIONS


def evaluate_response(target_profile: dict, tolerances: dict, response_text: str) -> dict:
    prompt = prompts.evaluator_prompt(target_profile, response_text)
    result = llm_client.call_json(config.EVALUATOR_MODEL, prompt)
    scores = result["scores"]

    deviations = {trait: abs(scores[trait] - target_profile[trait]) for trait in TRAIT_DIMENSIONS}
    excess = {trait: deviations[trait] - tolerances[trait] for trait in TRAIT_DIMENSIONS}
    worst_trait = max(excess, key=excess.get)

    return {
        "scores": scores,
        "deviations": deviations,
        "excess": excess,
        "worst_trait": worst_trait,
        "worst_excess": excess[worst_trait],
    }


def within_tolerance(evaluation: dict) -> bool:
    return evaluation["worst_excess"] <= 0
