"""
Stage 2: Response Generator.

Given the conversational context and the target profile T, generates a
candidate response intended to express T.
"""

import config
import llm_client
import prompts


def generate_response(background: dict, target_profile: dict, user_message: str) -> str:
    prompt = prompts.generation_prompt(background, target_profile, user_message)
    return llm_client.call(config.GENERATOR_MODEL, prompt, max_tokens=512).strip()
