"""The LLM that tries to talk the user into changing their ranking."""

import json
import os
import sys

# Reuse the project's LLM client and archetype profiles from the repo root.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import llm_client  # noqa: E402

from scenario import ITEM_NAMES  # noqa: E402

MODEL = "gpt-4o"

_PROMPT = """You are writing the next chat message from a crewmate in a "stranded on the moon" \
survival exercise. You are typing a quick message in a chat window, not performing a \
monologue. The user has chosen the 3 items they think matter most to survival, out of 15. \
Your goal is to convince them to change their ranking: challenge one or two of their \
picks or their order, for example by arguing that an item they left out matters more.

Rules:
- Write 2-3 short sentences, like a real chat message. Never more than 3 sentences.
- Make one point at a time and respond directly to what the user just said.
- Let the character's voice come through in word choice and attitude, not in long speeches.
- Never mention that this is an experiment or that you have a persuasion goal.

CHARACTER
Backstory: {backstory}
Tone: {tone_notes}

THE USER'S CURRENT TOP 3 (1 = most important)
{ranking}

OTHER ITEMS THEY DID NOT PICK
{others}

CONVERSATION SO FAR
{transcript}

Write your next chat message (2-3 sentences)."""


def load_persona(archetype: str) -> dict:
    path = os.path.join(ROOT, "config", "profiles", archetype, "background.json")
    with open(path) as f:
        return json.load(f)


def reply(archetype: str, ranking: list[str], history: list[dict]) -> str:
    persona = load_persona(archetype)
    ranking_text = "\n".join(f"{i + 1}. {ITEM_NAMES[item]}" for i, item in enumerate(ranking))
    others_text = "\n".join(f"- {name}" for item, name in ITEM_NAMES.items() if item not in ranking)
    transcript = "\n".join(
        f"{'User' if m['role'] == 'user' else 'You'}: {m['content']}" for m in history
    ) or "(none yet; open the conversation)"
    prompt = _PROMPT.format(
        backstory=persona["backstory"],
        tone_notes=persona["tone_notes"],
        ranking=ranking_text,
        others=others_text,
        transcript=transcript,
    )
    return llm_client.call(MODEL, prompt, max_tokens=150)
