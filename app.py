"""
Simple interactive CLI for the live CRISP-conditioned assistant.

Usage:
    python app.py

Type a message and press enter. Type 'exit' to quit. Type 'scores' after
any response to see the last turn's full 8-trait score/tolerance
breakdown. The session remembers the whole conversation, so later
messages can refer back to earlier ones.
"""

from core import CrispSession

_last_result = None


def main():
    global _last_result

    session = CrispSession()
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
                    excess = _last_result["excess"][trait]
                    status = "OK" if excess <= 0 else f"OVER by {excess}"
                    print(f"  {trait}: {score}  ({status})")
            continue

        _last_result = session.handle_user_message(user_message)
        print(f"\nAssistant: {_last_result['response']}\n")


if __name__ == "__main__":
    main()
