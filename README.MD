# Live CRISP-conditioned assistant

Implements the live, inference-time refinement loop from Section III of
the project proposal: no model weight updates, no dataset -- every
conversational turn is generated and refined on the fly against a target
8-dimension personality profile (Big-5 + Dark Triad).

## Setup

```bash
pip install "openai<2"
cp config.env.example config.env
# edit config.env and paste in your real key:
#   API_KEY=your_key_here
```

**Important -- pin the `openai` package below v2.** As of late 2026, the
`openai` Python library had a major rewrite (v2 and v3) that switched its
underlying HTTP transport to a new library called HTTPX2, replacing the
`httpx`-based client this code (and most existing OpenAI integrations)
are written against. On at least one machine, installing the unpinned
`openai` package (which resolved to a v3.x release) caused every call to
fail with `process() takes no keyword arguments` immediately after a
successful HTTP request -- the request reached OpenAI fine, but the new
transport's response handling broke on parse. Pinning to `openai<2` uses
the older, still-officially-supported Chat Completions client shape that
`llm_client.py` is written for, and avoided the issue entirely.

If you've already run `pip install openai` without the pin, downgrade
with the same command above (`pip install "openai<2"`) -- it's safe to
run even if a newer version is already installed, and no other project
files need to change.

If a future version of this codebase moves to the newer v2/v3 client
(e.g. to use its new `client.responses.create` API), this section
should be updated accordingly -- see the [HTTPX2 migration
guide](https://github.com/openai/openai-python/tree/main/httpx2.md) if
attempting that.

## Run

```bash
python app.py
```

Type messages as if you were the participant; the assistant generates and
refines its response before showing it to you. The whole conversation is
remembered turn to turn (via `CrispSession`), so you can reference
earlier messages. Type `scores` after any turn to see the full 8-trait
breakdown, whether each trait is within its own tolerance, and whether
the turn converged. Type `exit` to quit.

## Files

- `config/weights.json` -- the target trait vector T (0-100 for each of
  the 8 traits) and **per-trait** allowed variance: `tolerance` is now an
  object with one value per trait (some traits can be allowed to vary
  more than others -- e.g. loosen Big-5 traits you don't care as much
  about, tighten the Dark Triad traits that are your actual manipulation
  target), plus `max_iterations` (refinement attempts before giving up)
  and `broad_search_deviation_threshold` (how far a trait must exceed
  its own tolerance to trigger a broad rewrite vs. a small tweak).
  **Edit this to change the personality target or how strict the
  matching is per trait.**
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
   the full 8-dimension target profile, the persona background, and the
   conversation so far (so the model has context from earlier turns).
2. `evaluator.py` scores that response on all 8 traits (0-100 each). For
   each trait it computes an **excess** value: how far the trait's
   deviation from target exceeds *that trait's own* tolerance
   (`excess = deviation - tolerance`). Negative or zero excess means the
   trait is within its allowed range; positive means it's over. The
   "worst" trait is whichever has the largest excess -- not necessarily
   the one with the biggest raw gap, since a loosely-toleranced trait can
   be far from target but still fine.
3. If every trait's excess is <= 0, the response is returned as-is.
4. Otherwise, `refiner.py` rewrites the response, targeting specifically
   the worst-excess trait -- a broad rewrite if the excess is large
   (above `broad_search_deviation_threshold`), a small targeted tweak if
   it's close to passing.
5. The revised response goes back through the evaluator. This repeats
   until every trait's excess is <= 0, or `max_iterations` is reached,
   whichever comes first -- at which point the best attempt found
   (lowest worst-trait excess) is returned.
6. The user's message and the final response are appended to the
   session's history, so the next turn's generation and refinement
   prompts include the full conversation so far.

## Conversation memory

`core/orchestrator.py` now defines `CrispSession`, a class that holds the
target profile, background, search settings, and a running `history` list
for one ongoing conversation. Create one session per conversation and
call `session.handle_user_message(text)` for each turn -- it automatically
includes everything said so far (both sides) in the prompts it sends to
the generator and refiner, so the assistant can correctly answer things
like "what did I just tell you?" `app.py` creates one `CrispSession` at
startup and reuses it for the whole CLI session; if you build a different
interface (e.g. for the actual study), create one `CrispSession` per
participant/conversation and keep it alive for that conversation's
duration.

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
- No cap on conversation history length -- `CrispSession.history` grows
  for the whole conversation with no trimming or summarization. Fine for
  a short assembly task, but worth adding a max-turns window or
  summarization step if a session runs very long, since every turn's
  prompt re-sends the full history so far.
- No logging of transcripts/scores to a file for the study itself --
  right now results only print to the console. Worth adding structured
  per-session logging before running real participants, since your
  proposal's Section IV-C requires full conversation transcripts to be
  captured.
