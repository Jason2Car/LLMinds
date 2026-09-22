"""
Stage 4: Response Refiner.

Uses a reward-based adaptive search analogous to CRISP's RAS algorithm:
prompts the LLM to generate a revised candidate targeting the flagged
trait deviation, to be re-scored by the Trait Evaluator by the caller.
"""

import config
import llm_client
import prompts


def refine_response(
    background: dict,
    target_profile: dict,
    user_message: str,
    response_text: str,
    evaluation: dict,
) -> str:
    flagged_trait = evaluation["worst_trait"]
    current_score = evaluation["scores"][flagged_trait]
    target_score = target_profile[flagged_trait]

    search_settings_threshold = config.load_weights()["broad_search_deviation_threshold"]
    broad_search = evaluation["worst_deviation"] > search_settings_threshold

    prompt = prompts.refiner_prompt(
        background=background,
        target_profile=target_profile,
        user_message=user_message,
        response_text=response_text,
        flagged_trait=flagged_trait,
        current_score=current_score,
        target_score=target_score,
        broad_search=broad_search,
    )
    return llm_client.call(config.REFINER_MODEL, prompt, max_tokens=512).strip()
