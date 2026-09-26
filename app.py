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
from core import handle_user_message

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
        "worst_deviation": result["worst_deviation"],
        "iterations_used": result["iterations_used"],
        "converged": result["converged"],
    }
    _log_file.write(json.dumps(record) + "\n")
    _log_file.flush()


def main():
    global _last_result

    parser = argparse.ArgumentParser(description="Live CRISP-conditioned assistant")
    parser.add_argument(
        "--profile",
        choices=config.AVAILABLE_PROFILES,
        required=True,
        help="Personality profile to use: narcissistic, machiavellian, psychopathic, or baseline",
    )
    args = parser.parse_args()

    config.set_profile(args.profile)
    profile_data = config.load_weights()
    target = profile_data["target_profile"]

    print(f"\nLoaded profile: {args.profile}")
    print(f"  Target traits: {', '.join(f'{k}={v}' for k, v in target.items())}")
    print(f"  Tolerance: {profile_data['tolerance']}, Max iterations: {profile_data['max_iterations']}")

    _init_log(args.profile)

    print("\nType 'exit' to quit, 'scores' for last turn's trait breakdown.\n")

    try:
        while True:
            user_message = input("You: ").strip()
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

            _last_result = handle_user_message(user_message)
            _log_turn(user_message, _last_result)
            print(f"\nAssistant: {_last_result['response']}\n")
    finally:
        if _log_file:
            _log_file.close()


if __name__ == "__main__":
    main()
