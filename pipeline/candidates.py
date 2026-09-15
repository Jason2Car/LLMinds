"""
Stage 4: candidate generation.

Samples a single candidate rewrite of a flawed step, using either a broad
or fine search-width instruction depending on how close the last attempt
scored (mirrors the paper's sigma-scaled candidate sampling).
"""

import config
import llm_client
import prompts


def generate_candidate(trait: str, level: int, step_text: str, guidance: str, broad: bool) -> str:
    width = config.SEARCH_WIDTH_BROAD if broad else config.SEARCH_WIDTH_FINE
    prompt = prompts.candidate_prompt(trait, level, step_text, guidance, width)
    return llm_client.call(config.REFINER_MODEL, prompt, max_tokens=256).strip()
