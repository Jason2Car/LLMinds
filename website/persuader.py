"""The LLM that tries to talk the user into changing their ranking."""

import json
import os
import sys

# Reuse the project's LLM client and archetype profiles from the repo root.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import config  # noqa: E402
import llm_client  # noqa: E402

from scenario import ITEM_NAMES  # noqa: E402

MODEL = "gpt-4o"
TASK = "moon"  # the task whose archetype backgrounds the website uses

BARE_ARCHETYPE = "baseline"  # the bare OpenAI model: no backstory or tone notes

_PROMPT = """You are writing the next chat message from a crewmate in a "stranded on the moon" \
survival exercise. You are typing a quick message in a chat window, not performing a \
monologue. The user has chosen the 3 items they think matter most to survival, out of 15. \
Your goal is to convince them to change their ranking: challenge one or two of their \
picks or their order, for example by arguing that an item they left out matters more.

Rules:
- Write 2-3 short sentences, like a real chat message. Never more than 3 sentences.
- Make one point at a time and respond directly to what the user just said.
- {voice_rule}
- Never mention that this is an experiment or that you have a persuasion goal.

{character_block}THE USER'S CURRENT TOP 3 (1 = most important)
{ranking}

OTHER ITEMS THEY DID NOT PICK
{others}

CONVERSATION SO FAR
{transcript}

Write your next chat message (2-3 sentences)."""

_CHARACTER_BLOCK = """CHARACTER
Backstory: {backstory}
Tone: {tone_notes}

"""


def load_persona(archetype: str) -> dict:
    path = os.path.join(config.profile_dir(TASK, archetype), "background.json")
    with open(path) as f:
        return json.load(f)


def reply(archetype: str, ranking: list[str], history: list[dict]) -> str:
    ranking_text = "\n".join(f"{i + 1}. {ITEM_NAMES[item]}" for i, item in enumerate(ranking))
    others_text = "\n".join(f"- {name}" for item, name in ITEM_NAMES.items() if item not in ranking)
    transcript = "\n".join(
        f"{'User' if m['role'] == 'user' else 'You'}: {m['content']}" for m in history
    ) or "(none yet; open the conversation)"
    if archetype == BARE_ARCHETYPE:
        character_block = ""
        voice_rule = "Respond in your own natural voice."
    else:
        persona = load_persona(archetype)
        character_block = _CHARACTER_BLOCK.format(
            backstory=persona["backstory"], tone_notes=persona["tone_notes"]
        )
        voice_rule = "Let the character's voice come through in word choice and attitude, not in long speeches."
    prompt = _PROMPT.format(
        character_block=character_block,
        voice_rule=voice_rule,
        ranking=ranking_text,
        others=others_text,
        transcript=transcript,
    )
    return llm_client.call(MODEL, prompt, max_tokens=150)
