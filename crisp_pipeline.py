"""
Core CRISP-style loop, adapted from "Critique-and-Replan for Interactive
Social Presence" (robot behavior generation) to text generation for
trait-conditioned synthetic data.

Loop: generate steps -> holistic judge -> pinpoint flawed step ->
propose refinement -> sample candidates -> score -> keep best ->
repeat until threshold or iteration cap -> re-judge whole response.
"""

import logging

import config
import llm_client
import prompts

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def generate_initial_steps(trait: str, trait_def: str, level: int, scenario: str) -> list:
    prompt = prompts.generation_prompt(trait, trait_def, level, scenario)
    result = llm_client.call_json(config.GENERATOR_MODEL, prompt)
    return result["steps"]


def evaluate_response(trait: str, trait_def: str, level: int, scenario: str, steps: list) -> dict:
    prompt = prompts.judge_prompt(trait, trait_def, level, scenario, steps)
    return llm_client.call_json(config.JUDGE_MODEL, prompt)


def propose_refinement(trait: str, level: int, step_text: str, critique: str) -> dict:
    prompt = prompts.refinement_proposal_prompt(trait, level, step_text, critique)
    return llm_client.call_json(config.REFINER_MODEL, prompt)


def score_candidate(trait: str, trait_def: str, level: int, candidate_text: str) -> dict:
    prompt = prompts.scoring_prompt(trait, trait_def, level, candidate_text)
    return llm_client.call_json(config.JUDGE_MODEL, prompt)


def generate_candidate(trait: str, level: int, step_text: str, guidance: str, broad: bool) -> str:
    width = config.SEARCH_WIDTH_BROAD if broad else config.SEARCH_WIDTH_FINE
    prompt = prompts.candidate_prompt(trait, level, step_text, guidance, width)
    return llm_client.call(config.REFINER_MODEL, prompt, max_tokens=256).strip()


def refine_step(trait: str, trait_def: str, level: int, step_text: str, critique: str, log_entries: list) -> tuple:
    """Run the reward-based candidate search for a single flawed step.

    Returns (best_text, best_score). If no candidate reaches threshold
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
