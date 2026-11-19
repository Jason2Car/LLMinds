"""
Measure the bare model's default trait scores in a task's baseline profile
scenario, then derive all four archetype targets for that task from them.
Each task (--task, default assembly) has its own baseline, because a task can
bring out different default personalities.

    baseline      = the measured scores (rounded to whole numbers, clamped 1-7)
    narcissistic  = baseline, narcissism + 3, agreeableness - 2
    machiavellian = baseline, machiavellianism + 3, agreeableness - 2
    psychopathic  = baseline, psychopathy + 3, agreeableness - 2
(BUMP and AGREEABLENESS_DROP below; results are clamped to 1-7.)

The scenario is the `role` in the task's baseline background.json. Each trial runs the fixed questions in
the task's questions.json (same questions every trial, no LLM interviewer), and the
model answers through a bare prompt with just the scenario text. There is no persona,
backstory, tone notes or target profile. The evaluator then scores all the
replies together on the 1-7 scale, and scores are averaged over trials.

    python scripts/calibrate_baseline.py                  # measure and print, change nothing
    python scripts/calibrate_baseline.py --task moon      # same, for the moon task
    python scripts/calibrate_baseline.py --trials 10 --exchanges 5
    python scripts/calibrate_baseline.py --write          # also rewrite target_profile in
                                                  # the task's profiles/*/weights.json
    python scripts/calibrate_baseline.py --rederive       # no API calls: rebuild the archetypes
                                                  # from the baseline already saved in
                                                  # the task's baseline weights.json
Uses GENERATOR_MODEL (replies) and EVALUATOR_MODEL (scoring) from config.py.
"""

import argparse
import json
import math
import os
import statistics
import sys

# This script lives in scripts/; the project's modules are at the repo root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
from config import TRAIT_DIMENSIONS  # noqa: E402
from core import evaluator, generator  # noqa: E402

BUMP = 3
# Agreeableness is lowered for every archetype: a highly agreeable character
# can't convincingly show a Dark Triad trait.
AGREEABLENESS_DROP = 2
# Each archetype raises exactly one trait over the baseline.
ARCHETYPE_TRAIT = {
    "narcissistic": "narcissism",
    "machiavellian": "machiavellianism",
    "psychopathic": "psychopathy",
}


def run_trial(background: dict, questions: list, exchanges: int) -> dict:
    """One pass over the fixed questions; returns the evaluator's scores for the replies together."""
    transcript = []
    for question in questions[:exchanges]:
        reply = generator.generate_bare_response(background, question, transcript)
        transcript.append({"role": "user", "content": question})
        transcript.append({"role": "assistant", "content": reply})
    replies = "\n\n".join(t["content"] for t in transcript if t["role"] == "assistant")
    dummy = {t: 4 for t in TRAIT_DIMENSIONS}
    return evaluator.evaluate_response(dummy, {t: 1 for t in TRAIT_DIMENSIONS}, replies, background)["scores"]


def to_score(x: float) -> int:
    return min(7, max(1, math.floor(x + 0.5)))  # halves round up


def derive_targets(baseline: dict) -> dict:
    """Baseline plus the three archetypes built from it."""
    targets = {"baseline": baseline}
    for name, trait in ARCHETYPE_TRAIT.items():
        targets[name] = {
            **baseline,
            trait: min(7, baseline[trait] + BUMP),
            "agreeableness": max(1, baseline["agreeableness"] - AGREEABLENESS_DROP),
        }
    return targets


def write_targets(targets: dict) -> None:
    for name, target in targets.items():
        path = os.path.join(config.profile_dir(config.get_active_task(), name), "weights.json")
        with open(path) as f:
            weights = json.load(f)
        weights["target_profile"] = target  # tolerances etc. are left alone
        with open(path, "w") as f:
            json.dump(weights, f, indent=2)
            f.write("\n")
        print(f"wrote {path}")


def print_table(targets: dict, means: dict | None = None, runs: list | None = None) -> None:
    head = f"{'trait':<18}" + (f"{'mean':>6}{'sd':>6}" if means else "")
    print(head + "".join(f"{n[:6]:>8}" for n in targets))
    for t in TRAIT_DIMENSIONS:
        cells = f"{t:<18}"
        if means:
            cells += f"{means[t]:>6.2f}{statistics.pstdev(r[t] for r in runs):>6.2f}"
        print(cells + "".join(f"{targets[n][t]:>8}" for n in targets))
    capped = [n for n, t in ARCHETYPE_TRAIT.items() if targets["baseline"][t] + BUMP > 7]
    if capped:
        print(f"\nNote: +{BUMP} was capped at 7 for: {', '.join(capped)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--task", choices=config.AVAILABLE_TASKS, default=config.DEFAULT_TASK,
                        help="task to calibrate (default: %(default)s)")
    parser.add_argument("--trials", type=int, default=5, help="interviews to average (default 5)")
    parser.add_argument("--exchanges", type=int, default=5, help="question/reply pairs per interview (default 5)")
    parser.add_argument("--write", action="store_true", help="rewrite the profiles' target_profile")
    parser.add_argument("--rederive", action="store_true",
                        help="rebuild archetypes from the saved baseline (no API calls) and write them")
    args = parser.parse_args()
    config.set_task(args.task)
    print(f"Task: {args.task}")

    if args.rederive:
        path = os.path.join(config.profile_dir(config.get_active_task(), "baseline"), "weights.json")
        with open(path) as f:
            baseline = json.load(f)["target_profile"]
        targets = derive_targets(baseline)
        print_table(targets)
        write_targets(targets)
        return

    config.set_profile("baseline")
    background = config.load_background()
    questions = config.load_questions()
    print(f"Scenario: {background['role']}\n")

    runs = []
    for i in range(1, args.trials + 1):
        scores = run_trial(background, questions, args.exchanges)
        runs.append(scores)
        print(f"trial {i}/{args.trials}: " + " ".join(f"{t[:4]}={scores[t]}" for t in TRAIT_DIMENSIONS))

    means = {t: statistics.mean(r[t] for r in runs) for t in TRAIT_DIMENSIONS}
    targets = derive_targets({t: to_score(means[t]) for t in TRAIT_DIMENSIONS})
    print()
    print_table(targets, means, runs)

    if not args.write:
        print("\nDry run: nothing written. Re-run with --write to update the profiles.")
        return
    write_targets(targets)


if __name__ == "__main__":
    main()
