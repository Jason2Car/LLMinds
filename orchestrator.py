"""
Orchestrator: runs the full live CRISP loop for a conversation.

CrispSession holds the target profile, background, search settings, and
conversation history for one ongoing conversation. Call
session.handle_user_message(text) once per turn; it remembers everything
said before within that session, so multi-turn conversations don't lose
context between messages.

Each turn still runs the same per-message loop with no model weight
updates: generate -> evaluate -> (if outside tolerance) refine ->
re-evaluate -> repeat until within tolerance or max_iterations reached.
"""

import logging

from . import evaluator, generator, profile, refiner

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


class CrispSession:
    def __init__(self):
        self.target_profile = profile.get_target_profile()
        self.background = profile.get_background()
        self.settings = profile.get_search_settings()
        self.history = []  # list of {"role": "user"/"assistant", "content": str}

    def handle_user_message(self, user_message: str, verbose: bool = True) -> dict:
        """Run the live CRISP loop on one user message, with the full
        conversation so far as context.

        Returns a dict with the final response text, the final trait
        scores/excess, the number of refinement iterations used, and
        whether it converged within tolerance (vs. hit the iteration cap
        and returned its best attempt). Also appends this turn (user
        message + final response) to self.history for future turns.
        """
        tolerances = self.settings["tolerances"]

        response_text = generator.generate_response(
            self.background, self.target_profile, user_message, self.history
        )
        evaluation = evaluator.evaluate_response(self.target_profile, tolerances, response_text)

        best_response, best_evaluation = response_text, evaluation
        converged = evaluator.within_tolerance(evaluation)

        iteration = 0
        while not converged and iteration < self.settings["max_iterations"]:
            if verbose:
                log.info(
                    f"Iteration {iteration}: worst trait '{evaluation['worst_trait']}' "
                    f"exceeds its tolerance by {evaluation['worst_excess']} points -- refining."
                )

            response_text = refiner.refine_response(
                self.background,
                self.target_profile,
                user_message,
                response_text,
                evaluation,
                self.settings["broad_search_deviation_threshold"],
                self.history,
            )
            evaluation = evaluator.evaluate_response(self.target_profile, tolerances, response_text)

            # Keep the best-so-far in case we hit max_iterations without converging.
            if evaluation["worst_excess"] < best_evaluation["worst_excess"]:
                best_response, best_evaluation = response_text, evaluation

            converged = evaluator.within_tolerance(evaluation)
            iteration += 1

        if verbose and not converged:
            log.info(
                f"Reached max_iterations ({self.settings['max_iterations']}) without full "
                f"convergence; returning best attempt (worst excess="
                f"{best_evaluation['worst_excess']})."
            )

        self.history.append({"role": "user", "content": user_message})
        self.history.append({"role": "assistant", "content": best_response})

        return {
            "response": best_response,
            "scores": best_evaluation["scores"],
            "excess": best_evaluation["excess"],
            "worst_trait": best_evaluation["worst_trait"],
            "worst_excess": best_evaluation["worst_excess"],
            "iterations_used": iteration,
            "converged": converged,
        }
