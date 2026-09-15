"""
Stage 5: candidate scoring.

Equivalent to the paper's VLM reward assignment (1-10) -- scores a single
candidate rewrite against the target trait/intensity.
"""

import config
import llm_client
import prompts


def score_candidate(trait: str, trait_def: str, level: int, candidate_text: str) -> dict:
    prompt = prompts.scoring_prompt(trait, trait_def, level, candidate_text)
    return llm_client.call_json(config.JUDGE_MODEL, prompt)
