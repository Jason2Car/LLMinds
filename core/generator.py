"""
Stage 2: Response Generator.

Given the conversational context and the target profile T, generates a
candidate response intended to express T.
"""

import config
import llm_client
import prompts


def generate_bare_response(
    background: dict, user_message: str, conversation_history: list = None
) -> str:
    """Plain OpenAI reply: no character, tone notes or target profile."""
    prompt = prompts.bare_prompt(background, user_message, conversation_history)
    return llm_client.call(config.GENERATOR_MODEL, prompt, max_tokens=512).strip()


def generate_response(
    background: dict, target_profile: dict, user_message: str, conversation_history: list = None
) -> str:
    if config.uses_bare_model():
        return generate_bare_response(background, user_message, conversation_history)
    prompt = prompts.generation_prompt(background, target_profile, user_message, conversation_history)
    return llm_client.call(config.GENERATOR_MODEL, prompt, max_tokens=512).strip()
