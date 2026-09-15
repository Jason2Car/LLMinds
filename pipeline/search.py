"""
Stage 6: reward-based adaptive search.

Equivalent to the paper's Behavior Refiner / Reward-based Adaptive Search
(RAS) algorithm -- repeatedly samples candidates for one flawed step,
scores them, keeps the best, and narrows or widens the search based on
how close the best score is to the threshold.
"""

import config
from .candidates import generate_candidate
from ..propose import propose_refinement
from .score import score_candidate


def refine_step(trait: str, trait_def: str, level: int, step_text: str, critique: str, log_entries: list) -> tuple:
    """Run the reward-based candidate search for a single flawed step.

    Returns (best_text, best_score). best_text is None if the proposal
    was to delete the step entirely. If no candidate reaches threshold
    within MAX_ITERATIONS_PER_STEP, returns the best one found so far.
    """
    proposal = propose_refinement(trait, level, step_text, critique)
    log_entries.append({"stage": "refinement_proposal", "proposal": proposal})

    if proposal["action"] == "delete":
        return None, 10  # signal deletion to the caller

    best_text, best_score = step_text, 0
    broad_search = True  # start broad, narrow once we're close

    for iteration in range(config.MAX_ITERATIONS_PER_STEP):
        candidates = [
            generate_candidate(trait, level, best_text, proposal["guidance"], broad_search)
            for _ in range(config.CANDIDATES_PER_ITERATION)
        ]
        scored = []
        for cand in candidates:
            result = score_candidate(trait, trait_def, level, cand)
            scored.append((cand, result["score"], result.get("reason", "")))

        scored.sort(key=lambda x: x[1], reverse=True)
        top_text, top_score, top_reason = scored[0]

        log_entries.append(
            {
                "stage": "candidate_search",
                "iteration": iteration,
                "candidates": [{"text": c, "score": s, "reason": r} for c, s, r in scored],
            }
        )

        if top_score > best_score:
            best_text, best_score = top_text, top_score

        if best_score >= config.REWARD_THRESHOLD:
            break

        # adaptive search width: narrow in once we're in the right
        # direction, stay broad if we're still far off
        broad_search = best_score < 5

    return best_text, best_score
