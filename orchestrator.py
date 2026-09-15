"""
Orchestrator: ties generate -> evaluate -> propose -> search into the
full CRISP-style loop for one (trait, level, scenario) combination.
"""

import logging

import config
from .evaluate import evaluate_response
from .generate import generate_initial_steps
from .search import refine_step

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def run_pipeline(trait: str, level: int, scenario: str) -> dict:
    """Run the full CRISP loop for one (trait, level, scenario) combination.

    Returns a dict with the final text, a full audit log, and metadata,
    suitable for writing straight to a JSONL training file.
    """
    trait_def = config.TRAITS[trait]
    log_entries = []

    steps = generate_initial_steps(trait, trait_def, level, scenario)
    log_entries.append({"stage": "initial_generation", "steps": steps})

    for pass_num in range(config.MAX_TOTAL_PASSES):
        evaluation = evaluate_response(trait, trait_def, level, scenario, steps)
        log_entries.append({"stage": "holistic_evaluation", "pass": pass_num, "evaluation": evaluation})

        if evaluation["status"] == "appropriate":
            break

        flagged_id = evaluation["flagged_step_id"]
        critique = evaluation["critique"]
        flagged_step = next((s for s in steps if s["id"] == flagged_id), None)

        if flagged_step is None:
            log.warning("Judge flagged a step id not found in the response; stopping.")
            break

        new_text, new_score = refine_step(trait, trait_def, level, flagged_step["text"], critique, log_entries)

        if new_text is None:
            steps = [s for s in steps if s["id"] != flagged_id]
        else:
            flagged_step["text"] = new_text

        log_entries.append(
            {"stage": "step_updated", "step_id": flagged_id, "new_text": new_text, "reward": new_score}
        )
    else:
        log.info("Reached MAX_TOTAL_PASSES without full convergence; using best available response.")

    final_text = " ".join(s["text"] for s in steps)

    return {
        "trait": trait,
        "level": level,
        "scenario": scenario,
        "final_text": final_text,
        "steps": steps,
        "log": log_entries,
    }
