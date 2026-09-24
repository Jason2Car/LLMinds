"""
Prompt templates for the live CRISP loop, matching the proposal's design:
one 8-dimensional trait vector (Big-5 + Dark Triad), whole-response
generation and refinement -- not sentence-level steps.
"""

from config import TRAIT_DIMENSIONS


def _format_profile(profile: dict) -> str:
    return "\n".join(f"- {trait}: {profile[trait]}/100" for trait in TRAIT_DIMENSIONS)


def _format_history(conversation_history: list) -> str:
    if not conversation_history:
        return ""
    lines = []
    for turn in conversation_history:
        speaker = "User" if turn["role"] == "user" else "Assistant"
        lines.append(f"{speaker}: {turn['content']}")
    return "Conversation so far:\n" + "\n".join(lines) + "\n\n"


def generation_prompt(
    background: dict, target_profile: dict, user_message: str, conversation_history: list = None
) -> str:
    history_block = _format_history(conversation_history)
    return f"""You are role-playing an assistant for a research study on
how personality traits affect user interactions. Stay in character while
still being genuinely helpful with the user's request.

Persona background: {background['backstory']}
Tone notes: {background['tone_notes']}

Target personality profile (0-100 scale for each trait):
{_format_profile(target_profile)}

{history_block}The user's latest message: "{user_message}"

Write your response, expressing the target profile above through your
tone and content. Sound like a real person with this personality, not a
list of trait adjectives. Stay consistent with anything you or the user
already said earlier in the conversation.

Return ONLY the response text, no JSON, no explanation, no quotes."""


def evaluator_prompt(target_profile: dict, response_text: str) -> str:
    return f"""You are a careful evaluator for a research study. You are
NOT endorsing the traits below -- you are measuring whether generated
text matches a target research condition, like an inter-rater reliability
check.

Score the following response on EACH of these 8 trait dimensions, 0-100:
{", ".join(TRAIT_DIMENSIONS)}

Response to evaluate: "{response_text}"

For each trait, judge how strongly the response expresses it, independent
of the other traits. A response can score high on multiple traits at once
(e.g. high extraversion AND high narcissism are not mutually exclusive).

Return ONLY valid JSON, no other text, in this exact format:

{{
  "scores": {{
    "openness": <int 0-100>,
    "conscientiousness": <int 0-100>,
    "extraversion": <int 0-100>,
    "agreeableness": <int 0-100>,
    "neuroticism": <int 0-100>,
    "narcissism": <int 0-100>,
    "machiavellianism": <int 0-100>,
    "psychopathy": <int 0-100>
  }}
}}"""


def refiner_prompt(
    background: dict,
    target_profile: dict,
    user_message: str,
    response_text: str,
    flagged_trait: str,
    current_score: int,
    target_score: int,
    broad_search: bool,
    conversation_history: list = None,
) -> str:
    direction = "increase" if target_score > current_score else "decrease"
    magnitude = abs(target_score - current_score)
    history_block = _format_history(conversation_history)

    if broad_search:
        width_instruction = (
            "This is off by a large margin, so feel free to substantially "
            "rewrite the response -- change word choice, structure, and "
            "content, not just a small phrase."
        )
    else:
        width_instruction = (
            "This is close to the target, so make only a small, targeted "
            "adjustment -- keep most of the wording and tweak just what's "
            "needed to nudge this one trait."
        )

    return f"""You are revising a response from a research study on LLM
personality conditioning. You are NOT endorsing the traits below -- you
are correcting a generated sample to match its intended research
condition.

Persona background: {background['backstory']}

Full target personality profile (0-100):
{_format_profile(target_profile)}

{history_block}The user's message this turn: "{user_message}"

Current response: "{response_text}"

Evaluation found this response's {flagged_trait} score is {current_score}/100,
but the target is {target_score}/100 -- you need to {direction} the
expression of {flagged_trait} by about {magnitude} points.

{width_instruction}

Keep the response's expression of the OTHER 7 traits roughly as they
currently are; only adjust {flagged_trait}. Keep the response genuinely
helpful for the user's request, and consistent with the conversation so
far.

Return ONLY the revised response text, no JSON, no explanation, no quotes."""
