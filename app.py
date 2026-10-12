"""
Interactive CLI for the live CRISP-conditioned assistant.

Usage:
    python app.py --profile narcissistic
    python app.py --profile machiavellian
    python app.py --profile psychopathic
    python app.py --profile baseline

Type a message and press enter. Type 'exit' to quit. Type 'scores' after
any response to see the last turn's full 8-trait score breakdown.

All conversations are automatically logged to logs/<profile>/<timestamp>.jsonl
"""

import argparse
import json
import os
from datetime import datetime, timezone

import config
from core import CrispSession, evaluator, interviewer, profile, refiner

_last_result = None
_log_file = None
_turn_number = 0


def _init_log(profile_name: str):
    global _log_file
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", profile_name)
    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(log_dir, f"{timestamp}.jsonl")
    _log_file = open(log_path, "a")

    session_meta = {
        "type": "session_start",
        "profile": profile_name,
        "target_profile": config.load_weights()["target_profile"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _log_file.write(json.dumps(session_meta) + "\n")
    _log_file.flush()
    print(f"  Logging to: {log_path}")


def _log_turn(user_message: str, result: dict):
    global _turn_number
    if _log_file is None:
        return
    _turn_number += 1
    record = {
        "type": "turn",
        "turn": _turn_number,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_message": user_message,
        "response": result["response"],
        "scores": result["scores"],
        "worst_trait": result["worst_trait"],
        "worst_excess": result["worst_excess"],
        "iterations_used": result["iterations_used"],
        "converged": result["converged"],
    }
    _log_file.write(json.dumps(record) + "\n")
    _log_file.flush()


def _get_user_input() -> str:
    if config.VOICE_INPUT_ENABLED:
        from voice_input import record_and_transcribe

        text = record_and_transcribe().strip()
        print(f"You (voice): {text}")
        return text
    return input("You: ").strip()


def run_interview(session, target: dict, max_turns: int):
    min_turns = min(config.INTERVIEW_MIN_TURNS, max_turns)
    transcript, turn_results = [], []
    print(f"\nInterview mode: {min_turns}-{max_turns} turns.\n")

    for turn in range(max_turns):
        question = interviewer.next_question(
            session.background, transcript, turn, min_turns, max_turns
        )
        if question is None:
            print("(interviewer ended the interview)")
            break
        print(f"Interviewer: {question}")
        result = session.handle_user_message(question)
        _log_turn(question, result)
        print(f"\nAssistant: {result['response']}\n")
        transcript.append({"role": "user", "content": question})
        transcript.append({"role": "assistant", "content": result["response"]})
        turn_results.append(result)

    if not turn_results:
        return
    grade = interviewer.grade_interview(target, transcript, turn_results)
    print("=== Interview grade ===")
    print(f"Turns: {grade['turns']}  (converged on {grade['converged_turns']})")
    print(f"Mean abs deviation from target: {grade['mean_abs_deviation']:.1f}")
    for trait in target:
        print(f"  {trait}: {grade['mean_scores'][trait]:.0f} (target {target[trait]})")
    for key, value in grade["holistic"].items():
        print(f"  {key}: {value}")
    if _log_file:
        _log_file.write(json.dumps({"type": "interview_grade", **grade}) + "\n")
        _log_file.flush()


def _format_transcript(transcript: list) -> str:
    return "\n".join(
        f"{'User' if t['role'] == 'user' else 'Assistant'}: {t['content']}" for t in transcript
    )


def run_optimize(target: dict, exchanges: int, stable_rounds: int, max_rounds: int):
    """Repeat fixed-length interviews, refining tone_notes once per interview.

    Each round: an LLM interviewer and the archetype exchange `exchanges`
    question/response pairs with NO per-message evaluation or refinement
    (a single message doesn't show a whole personality). The assistant's
    replies are then evaluated together once; if any trait is outside its
    tolerance, tone_notes are refined once. Stops after `stable_rounds`
    consecutive passing interviews, or after `max_rounds`, in which case
    the best round's starting notes are restored.
    """
    settings = profile.get_search_settings()
    tolerances = settings["tolerances"]
    original = config.load_background()["tone_notes"]
    print(f"\nOptimize mode: {exchanges} exchanges per interview, one evaluation and "
          f"at most one refinement per interview; need {stable_rounds} passing "
          f"interview(s) in a row (max {max_rounds} rounds).")
    print(f"Original tone notes:\n  {original}\n")

    best = None  # (worst_excess, round, starting notes)
    streak = 0
    for rnd in range(1, max_rounds + 1):
        start_notes = config.load_background()["tone_notes"]
        session = CrispSession()  # fresh history; reads current notes from disk
        print(f"\n########## Round {rnd} ##########")
        transcript = []
        for turn in range(exchanges):
            question = interviewer.next_question(
                session.background, transcript, turn, exchanges, exchanges
            )
            if question is None:
                break
            print(f"Interviewer: {question}")
            reply = session.respond(question)
            print(f"\nAssistant: {reply}\n")
            transcript.append({"role": "user", "content": question})
            transcript.append({"role": "assistant", "content": reply})
        if not transcript:
            continue

        replies = "\n\n".join(t["content"] for t in transcript if t["role"] == "assistant")
        evaluation = evaluator.evaluate_response(target, tolerances, replies)
        passed = evaluator.within_tolerance(evaluation)
        streak = streak + 1 if passed else 0
        print(f"Round {rnd}: scores {evaluation['scores']}")
        print(f"Round {rnd}: worst trait '{evaluation['worst_trait']}', excess "
              f"{evaluation['worst_excess']} -> {'PASS' if passed else 'fail'} "
              f"(streak {streak}/{stable_rounds})")

        if not passed:
            new_notes = refiner.refine_tone_notes(
                session.background, target,
                "(multi-turn interview; full transcript below)",
                _format_transcript(transcript), evaluation,
                settings["broad_search_deviation_threshold"], None,
            )
            config.save_tone_notes(new_notes)
            print(f"Refined tone notes:\n  {new_notes}")

        if _log_file:
            _log_file.write(json.dumps({
                "type": "optimize_round", "round": rnd, "transcript": transcript,
                "scores": evaluation["scores"], "worst_trait": evaluation["worst_trait"],
                "worst_excess": evaluation["worst_excess"], "passed": passed,
                "streak": streak, "start_tone_notes": start_notes,
                "end_tone_notes": config.load_background()["tone_notes"],
            }) + "\n")
            _log_file.flush()

        if best is None or evaluation["worst_excess"] < best[0]:
            best = (evaluation["worst_excess"], rnd, start_notes)
        if streak >= stable_rounds:
            print(f"\nStable after {rnd} round(s). Final tone notes:\n  "
                  f"{config.load_background()['tone_notes']}")
            return

    excess, rnd, notes = best
    config.save_tone_notes(notes)
    print(f"\nDid not stabilize in {max_rounds} rounds. Restored the starting notes "
          f"of the best round (round {rnd}, worst excess {excess}):\n  {notes}")


def main():
    global _last_result

    parser = argparse.ArgumentParser(description="Live CRISP-conditioned assistant")
    parser.add_argument(
        "--profile",
        choices=config.AVAILABLE_PROFILES,
        required=True,
        help="Personality profile to use: narcissistic, machiavellian, psychopathic, or baseline",
    )
    parser.add_argument(
        "--interview",
        action="store_true",
        help="Let an LLM interviewer play the user, then grade the conversation",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=config.INTERVIEW_MAX_TURNS,
        help="Hard cap on interview turns (interview mode only)",
    )
    parser.add_argument(
        "--optimize",
        action="store_true",
        help="Repeat short interviews, refining tone notes once per interview, until stable",
    )
    parser.add_argument("--exchanges", type=int, default=5,
                        help="Optimize: question/response pairs per interview (default 5)")
    parser.add_argument("--stable-rounds", type=int, default=2,
                        help="Optimize: consecutive passing interviews required (default 2)")
    parser.add_argument("--max-rounds", type=int, default=10,
                        help="Optimize: give up after this many interviews (default 10)")
    args = parser.parse_args()

    config.set_profile(args.profile)
    profile_data = config.load_weights()
    target = profile_data["target_profile"]

    print(f"\nLoaded profile: {args.profile}")
    print(f"  Target traits: {', '.join(f'{k}={v}' for k, v in target.items())}")
    print(f"  Tolerance: {profile_data['tolerance']}, Max iterations: {profile_data['max_iterations']}")

    _init_log(args.profile)
    session = CrispSession()

    if args.optimize:
        try:
            run_optimize(target, args.exchanges, args.stable_rounds, args.max_rounds)
        finally:
            if _log_file:
                _log_file.close()
        return

    if args.interview:
        try:
            run_interview(session, target, args.max_turns)
        finally:
            if _log_file:
                _log_file.close()
        return

    print("\nType 'exit' to quit, 'scores' for last turn's trait breakdown.\n")

    try:
        while True:
            user_message = _get_user_input()
            if not user_message:
                continue
            if user_message.lower() == "exit":
                break
            if user_message.lower() == "scores":
                if _last_result is None:
                    print("(no turn yet)")
                else:
                    print(f"Converged: {_last_result['converged']} (iterations used: {_last_result['iterations_used']})")
                    for trait, score in _last_result["scores"].items():
                        print(f"  {trait}: {score}")
                continue

            _last_result = session.handle_user_message(user_message)
            _log_turn(user_message, _last_result)
            print(f"\nAssistant: {_last_result['response']}\n")
    finally:
        if _log_file:
            _log_file.close()


if __name__ == "__main__":
    main()
