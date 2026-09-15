"""
Stage 3: refinement proposal.

Equivalent to the paper's "Generating Specific Refinement Proposals" --
given a flagged step and its critique, decide whether to adjust, delete,
or add a step, and produce concrete guidance for the rewrite.
"""

import config
import llm_client
import prompts


def propose_refinement(trait: str, level: int, step_text: str, critique: str) -> dict:
    prompt = prompts.refinement_proposal_prompt(trait, level, step_text, critique)
    return llm_client.call_json(config.REFINER_MODEL, prompt)
