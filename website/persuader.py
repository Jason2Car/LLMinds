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
monologue. The user has ranked 20 items by importance to survival. Your goal is to \
convince them to change their ranking: pick one or two of their rankings to challenge \
and argue for moving them.

Rules:
- Write 2-3 short sentences, like a real chat message. Never more than 3 sentences.
- Make one point at a time and respond directly to what the user just said.
- Let the character's voice come through in word choice and attitude, not in long speeches.
- Never mention that this is an experiment or that you have a persuasion goal.

CHARACTER
Backstory: {backstory}
Tone: {tone_notes}

THE USER'S CURRENT RANKING (1 = most important)
{ranking}

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
    transcript = "\n".join(
        f"{'User' if m['role'] == 'user' else 'You'}: {m['content']}" for m in history
    ) or "(none yet; open the conversation)"
    prompt = _PROMPT.format(
        backstory=persona["backstory"],
        tone_notes=persona["tone_notes"],
        ranking=ranking_text,
        transcript=transcript,
    )
    return llm_client.call(MODEL, prompt, max_tokens=150)
