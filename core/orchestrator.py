"""
Orchestrator: runs the full live CRISP loop for a single user message.

    generate -> evaluate -> (if outside tolerance) refine -> re-evaluate
    -> repeat until within tolerance or max_iterations reached.

This is meant to be called once per conversational turn, at inference
time, with no model weight updates -- matching the proposal's design.
"""

import logging

from . import evaluator, generator, profile, refiner

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def handle_user_message(user_message: str, verbose: bool = True) -> dict:
    """Run the live CRISP loop on one user message.

    Returns a dict with the final response text, the final trait scores,
    the number of refinement iterations used, and whether it converged
    within tolerance (vs. hit the iteration cap and returned its best
    attempt).
    """
    target_profile = profile.get_target_profile()
    background = profile.get_background()
    settings = profile.get_search_settings()

    response_text = generator.generate_response(background, target_profile, user_message)
    evaluation = evaluator.evaluate_response(target_profile, response_text)

    best_response, best_evaluation = response_text, evaluation
    converged = evaluator.within_tolerance(evaluation, settings["tolerance"])

    iteration = 0
    while not converged and iteration < settings["max_iterations"]:
        if verbose:
            log.info(
                f"Iteration {iteration}: worst trait '{evaluation['worst_trait']}' "
                f"off by {evaluation['worst_deviation']} points -- refining."
            )

        response_text = refiner.refine_response(
            background, target_profile, user_message, response_text, evaluation
        )
        evaluation = evaluator.evaluate_response(target_profile, response_text)

        # Keep the best-so-far in case we hit max_iterations without converging.
        if evaluation["worst_deviation"] < best_evaluation["worst_deviation"]:
            best_response, best_evaluation = response_text, evaluation

        converged = evaluator.within_tolerance(evaluation, settings["tolerance"])
        iteration += 1

    if verbose and not converged:
        log.info(
            f"Reached max_iterations ({settings['max_iterations']}) without full "
            f"convergence; returning best attempt (worst deviation="
            f"{best_evaluation['worst_deviation']})."
        )

    return {
        "response": best_response,
        "scores": best_evaluation["scores"],
        "worst_trait": best_evaluation["worst_trait"],
        "worst_deviation": best_evaluation["worst_deviation"],
        "iterations_used": iteration,
        "converged": converged,
    }
