"""
Stage 2: holistic evaluation.

Equivalent to the paper's Motion Evaluator -- an LLM judge checks the whole
response against the target trait/intensity and naturalness, and if it's
not good enough, pinpoints the single step that most needs to change.
"""

import config
import llm_client
import prompts


def evaluate_response(trait: str, trait_def: str, level: int, scenario: str, steps: list) -> dict:
    prompt = prompts.judge_prompt(trait, trait_def, level, scenario, steps)
    return llm_client.call_json(config.JUDGE_MODEL, prompt)
