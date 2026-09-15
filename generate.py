"""
Stage 1: initial generation.

Equivalent to the paper's Robot Behavior Generator -- produces a response
broken into discrete, sentence-level steps so later stages can refine one
step at a time instead of regenerating the whole response.
"""

import config
import llm_client
import prompts


def generate_initial_steps(trait: str, trait_def: str, level: int, scenario: str) -> list:
    prompt = prompts.generation_prompt(trait, trait_def, level, scenario)
    result = llm_client.call_json(config.GENERATOR_MODEL, prompt)
    return result["steps"]
