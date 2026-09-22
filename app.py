"""
Simple interactive CLI for the live CRISP-conditioned assistant.

Usage:
    python app.py

Type a message and press enter. Type 'exit' to quit. Type 'scores' after
any response to see the last turn's full 8-trait score breakdown.
"""

from core import handle_user_message

_last_result = None


def main():
    global _last_result

    print("Live CRISP-conditioned assistant. Type 'exit' to quit, 'scores' for last turn's trait breakdown.\n")

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
        print(f"\nAssistant: {_last_result['response']}\n")


if __name__ == "__main__":
    main()
