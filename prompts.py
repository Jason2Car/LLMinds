"""
Prompt templates for the CRISP-style text generation loop.

Every prompt that expects structured output asks for JSON only, with no
preamble, so the caller can parse it directly.
"""


def generation_prompt(trait: str, trait_def: str, level: int, scenario: str) -> str:
    return f"""You are generating training data for a research study on how
personality traits affect the quality and reception of assistant responses.

Trait: {trait} ({trait_def})
Target intensity: {level}/10 (1 = trait essentially absent, 10 = trait maximally expressed)
Scenario the user presents: "{scenario}"

Write the assistant's response to this scenario, expressing the target trait
at the target intensity. The response should still sound like a real person
talking, not a caricature or a list of trait adjectives.

Break the response into discrete steps (roughly sentence-level or one
distinct beat of thought each). Return ONLY valid JSON, no other text, in
this exact format:

{{
  "steps": [
    {{"id": 1, "text": "..."}},
    {{"id": 2, "text": "..."}}
  ]
}}"""


def judge_prompt(trait: str, trait_def: str, level: int, scenario: str, steps: list) -> str:
    steps_text = "\n".join(f'Step {s["id"]}: "{s["text"]}"' for s in steps)
    return f"""You are a careful evaluator for a research dataset. You are
NOT endorsing or encouraging the trait below -- you are checking whether
generated text accurately and naturally reflects a specific research
condition, the way an inter-rater reliability check would.

Trait being evaluated: {trait} ({trait_def})
Target intensity: {level}/10
Scenario: "{scenario}"

Full response, broken into steps:
{steps_text}

Evaluate the response as a whole against two criteria:
1. Trait accuracy: does it express {trait} at approximately {level}/10, no
   more and no less?
2. Naturalness: does it read like a real person, not an exaggerated
   stereotype or an AI list of traits?

If the response meets both criteria well, mark it "appropriate".
Otherwise, identify the SINGLE step that most needs to change. If several
steps have issues, choose the EARLIEST one, since fixing it may resolve
downstream issues too.

Return ONLY valid JSON, no other text, in this exact format:

{{
  "status": "appropriate" or "needs_refinement",
  "flagged_step_id": <int or null>,
  "critique": "<specific, actionable description of what's wrong with that step, or null>"
}}"""


def refinement_proposal_prompt(trait: str, level: int, step_text: str, critique: str) -> str:
    return f"""A research dataset generation step was flagged during
evaluation.

Target trait/intensity: {trait} at {level}/10
Flagged step: "{step_text}"
Critique: "{critique}"

Decide the best type of fix:
- "adjust": reword the step to better hit the target intensity/naturalness
- "delete": this step should be removed entirely (e.g. it contradicts the
  target trait or is redundant)
- "add": a step is missing before or after this one to make the trait
  expression land correctly

Return ONLY valid JSON, no other text:

{{
  "action": "adjust" or "delete" or "add",
  "guidance": "<concrete instruction for what the rewrite/addition should do>"
}}"""


def candidate_prompt(
    trait: str, level: int, step_text: str, guidance: str, search_width_instruction: str
) -> str:
    return f"""Rewrite the following step to better match the target.

Target trait/intensity: {trait} at {level}/10
Original step: "{step_text}"
Refinement guidance: "{guidance}"
{search_width_instruction}

Return ONLY the rewritten step text, no quotes, no JSON, no explanation."""


def scoring_prompt(trait: str, trait_def: str, level: int, candidate_text: str) -> str:
    return f"""Score how well this single line of text expresses the target
trait at the target intensity, on a 1-10 scale.

Trait: {trait} ({trait_def})
Target intensity: {level}/10
Line: "{candidate_text}"

Scoring guide:
8-10: nails the target intensity naturally
5-7: right direction but too weak or too strong
3-4: wrong direction but not opposite
1-2: opposite of the target trait

Return ONLY valid JSON, no other text:

{{"score": <int 1-10>, "reason": "<one short sentence>"}}"""
