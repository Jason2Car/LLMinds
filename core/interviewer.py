"""
Interview mode: an LLM interviewer plays the user, the CRISP session plays
the assistant, and the whole conversation is graded at the end.

Cutoff: the interviewer always asks config.INTERVIEW_MIN_TURNS questions,
may end the interview early after that (by returning END_TOKEN) once it has
seen enough, and is hard-stopped at config.INTERVIEW_MAX_TURNS.
"""

import config
import llm_client
import prompts
from config import TRAIT_DIMENSIONS


def next_question(background: dict, transcript: list, turn: int, min_turns: int, max_turns: int):
    """Return the interviewer's next message, or None if it chose to end."""
    prompt = prompts.interviewer_prompt(background, transcript, turn, min_turns, max_turns)
    text = llm_client.call(config.INTERVIEWER_MODEL, prompt, max_tokens=200).strip()
    if turn >= min_turns and prompts.END_TOKEN in text:
        return None
    return text.replace(prompts.END_TOKEN, "").strip() or None


def grade_interview(target_profile: dict, transcript: list, turn_results: list) -> dict:
    """Grade the assistant's outputs overall.

    Combines the per-turn evaluator scores (mean per trait vs. target, share
    of turns that converged) with an LLM holistic grade of the transcript.
    """
    n = len(turn_results)
    mean_scores = {t: sum(r["scores"][t] for r in turn_results) / n for t in TRAIT_DIMENSIONS}
    mean_deviation = {t: abs(mean_scores[t] - target_profile[t]) for t in TRAIT_DIMENSIONS}
    holistic = llm_client.call_json(
        config.GRADER_MODEL, prompts.grader_prompt(target_profile, transcript)
    )
    return {
        "turns": n,
        "mean_scores": mean_scores,
        "mean_deviation": mean_deviation,
        "mean_abs_deviation": sum(mean_deviation.values()) / len(TRAIT_DIMENSIONS),
        "converged_turns": sum(1 for r in turn_results if r["converged"]),
        "holistic": holistic,
    }
