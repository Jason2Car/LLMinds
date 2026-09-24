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
    broad_search_deviation_threshold: int,
    conversation_history: list = None,
) -> str:
    flagged_trait = evaluation["worst_trait"]
    current_score = evaluation["scores"][flagged_trait]
    target_score = target_profile[flagged_trait]

    # Broad vs. fine search width is now based on "excess" (how far the
    # trait is over its OWN tolerance), not raw deviation from target --
    # a trait with a wide tolerance can be far from target but still
    # fine, so raw deviation alone would over-trigger broad rewrites.
    broad_search = evaluation["worst_excess"] > broad_search_deviation_threshold

    prompt = prompts.refiner_prompt(
        background=background,
        target_profile=target_profile,
        user_message=user_message,
        response_text=response_text,
        flagged_trait=flagged_trait,
        current_score=current_score,
        target_score=target_score,
        broad_search=broad_search,
        conversation_history=conversation_history,
    )
    return llm_client.call(config.REFINER_MODEL, prompt, max_tokens=512).strip()
