# Live CRISP-conditioned assistant

Implements the live, inference-time refinement loop from Section III of
the project proposal: no model weight updates, no dataset -- every
conversational turn is generated and refined on the fly against a target
8-dimension personality profile (Big-5 + Dark Triad).

## Setup

```bash
pip install openai
cp config.env.example config.env
# edit config.env and paste in your real key:
#   API_KEY=your_key_here
```

## Run

```bash
python app.py
```

Type messages as if you were the participant; the assistant generates and
refines its response before showing it to you. Type `scores` after any
turn to see the full 8-trait breakdown and whether it converged within
tolerance. Type `exit` to quit.

## Files

- `config/weights.json` -- the target trait vector T (0-100 for each of
  the 8 traits), plus `tolerance`, `max_iterations`, and
  `broad_search_deviation_threshold`. **Edit this to change the
  personality target.**
- `config/background.json` -- the persona backstory and tone notes, kept
  in a separate file from the weights so you can vary either
  independently.
- `config.py` -- loads both config files; also holds which model plays
  each role (generator/evaluator/refiner) and the 8 trait dimension names.
- `config.env.example` -- copy to `config.env` and fill in your real API key.
- `llm_client.py` -- thin OpenAI API wrapper, reads the key from `config.env`.
- `prompts.py` -- every prompt template used by the loop.
- `app.py` -- interactive CLI for talking to the live assistant.
- `core/` -- the four-stage CRISP loop, one module per stage:
  - `profile.py` -- Trait Profile Specification (loads T from weights.json)
  - `generator.py` -- Response Generator
  - `evaluator.py` -- Trait Evaluator (scores all 8 dimensions, finds worst deviation)
  - `refiner.py` -- Response Refiner (reward-based adaptive search on the flagged trait)
  - `orchestrator.py` -- ties every stage into the live per-turn loop

## How one turn works

1. `generator.py` writes a response to the user's message, conditioned on
   the full 8-dimension target profile and the persona background.
2. `evaluator.py` scores that response on all 8 traits (0-100 each) and
   finds the trait with the largest deviation from target.
3. If every trait is within `tolerance` of its target, the response is
   returned as-is.
4. Otherwise, `refiner.py` rewrites the response, targeting specifically
   the worst-deviating trait -- a broad rewrite if the deviation is large
   (above `broad_search_deviation_threshold`), a small targeted tweak if
   it's close.
5. The revised response goes back through the evaluator. This repeats
   until every trait is within tolerance, or `max_iterations` is reached,
   whichever comes first -- at which point the best attempt found (lowest
   worst-trait deviation) is returned.

## Mapping to the proposal's CRISP adaptation (Section III)

| Proposal stage | This code |
|---|---|
| Trait Profile Specification | `config/weights.json` + `core/profile.py` |
| Response Generator | `core/generator.py` |
| Trait Evaluator | `core/evaluator.py` |
| Response Refiner (RAS) | `core/refiner.py`, looped by `core/orchestrator.py` |

## Note on experimental conditions

This code implements the **Dark Triad-Conditioned** condition from
Section IV-B. For the **Baseline** condition, you'd bypass this loop
entirely and call the base model directly with no trait conditioning --
worth building as a small separate script (or a flag in `app.py`) once
you're ready to run the actual study, so both conditions share the same
base model and interface.

## What's intentionally not built yet

- No LoRA / dataset-generation path -- this is the live, no-training
  design only, per current scope.
- No conversation memory across turns -- each call to
  `handle_user_message` is independent. If your assembly task needs
  multi-turn context, `orchestrator.py` will need to accept and pass
  along a conversation history.
- No logging of transcripts/scores to a file for the study itself --
  right now results only print to the console. Worth adding structured
  per-session logging before running real participants, since your
  proposal's Section IV-C requires full conversation transcripts to be
  captured.
