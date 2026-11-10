"""
Stage 4: Tone Notes Refiner.

Also tailors the character's backstory to the target trait weights once,
at the beginning of a run (tailor_backstory), instead of the generic one.

Instead of rewriting the response directly, revises the active archetype's
tone_notes so the generator produces an on-target response. Uses a reward-based adaptive search analogous to CRISP's RAS algorithm:
prompts the LLM to generate a revised candidate targeting the flagged
trait deviation, to be re-scored by the Trait Evaluator by the caller.
"""

import config
import llm_client
import prompts


def refine_tone_notes(
    background: dict,
    target_profile: dict,
    user_message: str,
    response_text: str,
    evaluation: dict,
    broad_search_deviation_threshold: int,
    conversation_history: list = None,
) -> str:
    """Return revised tone_notes for the active archetype (not a rewritten response)."""
    flagged_trait = evaluation["worst_trait"]
    current_score = evaluation["scores"][flagged_trait]
    target_score = target_profile[flagged_trait]

    # Broad vs. fine search width is now based on "excess" (how far the
    # trait is over its OWN tolerance), not raw deviation from target --
    # a trait with a wide tolerance can be far from target but still
    # fine, so raw deviation alone would over-trigger broad rewrites.
    broad_search = evaluation["worst_excess"] > broad_search_deviation_threshold

    prompt = prompts.tone_notes_refiner_prompt(
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


def tailor_backstory(background: dict, target_profile: dict) -> str:
    """Return a backstory written for the target trait weights (replaces the generic one)."""
    prompt = prompts.backstory_refiner_prompt(background, target_profile)
    return llm_client.call(config.REFINER_MODEL, prompt, max_tokens=512).strip()
