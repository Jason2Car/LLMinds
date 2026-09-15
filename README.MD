# CRISP-style trait-conditioned text generation

Adapts the "Critique-and-Replan" loop from *The Robot's Inner Critic*
(arXiv:2603.20164) from robot joint control to text generation for
trait-conditioned synthetic training data.

## Setup

```bash
pip install openai
cp config.env.example config.env
# then edit config.env and paste in your real key:
#   API_KEY=your_key_here
```

`llm_client.py` reads the key directly from `config.env` (no environment
variable needed). Keep `config.env` out of version control.

## Run

```bash
python generate_dataset.py
```

This produces:
- `dataset.jsonl` -- clean `{trait, level, scenario, response}` records, ready
  to reformat into your LoRA training format.
- `dataset_audit.jsonl` -- the same records plus the full generate / judge /
  refine / score log for every example, so you can spot-check *why* the
  pipeline converged on a given response, or debug cases where it didn't.

## Files

- `config.py` -- traits, intensity levels, scenarios, models, thresholds.
  **Edit this first** to match your study design.
- `config.env.example` -- copy to `config.env` and fill in your real API key.
- `prompts.py` -- every prompt template used by the loop.
- `llm_client.py` -- thin OpenAI API wrapper with JSON-safe parsing, retries,
  and config.env loading.
- `generate_dataset.py` -- loops the pipeline over your full trait/level/
  scenario grid and writes output files.
- `pipeline/` -- the CRISP loop, one module per stage:
  - `generate.py` -- initial step-broken response generation
  - `evaluate.py` -- holistic judge, pinpoints the flawed step
  - `propose.py` -- decides adjust / delete / add and gives guidance
  - `candidates.py` -- samples a candidate rewrite of a flawed step
  - `score.py` -- scores a single candidate 1-10
  - `search.py` -- the reward-based candidate search over a step
  - `orchestrator.py` -- ties every stage together into the full loop

## How this maps to the original CRISP paper

| Paper (robot behavior) | This pipeline (text) |
|---|---|
| Robot structure file (joints, limits) | `TRAITS` + `LEVELS` in config.py |
| Behavior Generator (steps with timing) | `pipeline/generate.py` (sentence-level steps) |
| VLM holistic evaluation | `pipeline/evaluate.py` (LLM judge) |
| Pinpoint erroneous step | `flagged_step_id` in judge output |
| Adjust / Delete / Add proposal | `pipeline/propose.py` |
| Reward-based Adaptive Search (3 candidates, sigma scaling) | `pipeline/search.py` (uses `candidates.py` + `score.py`) |
| Termination at reward >= threshold | `REWARD_THRESHOLD` in config.py |

## Before you scale this up

1. **Validate the judge against human ratings first.** Run the pipeline on a
   small batch (a few dozen examples), then have humans rate the same
   outputs on trait-accuracy and naturalness. Check that the LLM judge's
   scores correlate with human judgment before trusting it to label your
   full dataset -- this is the biggest assumption the original paper doesn't
   have to make (their reward was grounded in checkable joint angles, not
   subjective trait expression).
2. **Watch your API cost.** Each flawed step can trigger up to
   `MAX_ITERATIONS_PER_STEP * CANDIDATES_PER_ITERATION` extra generation and
   scoring calls. Test on a small grid first and extrapolate cost before
   running the full trait x level x scenario matrix.
3. **Check global coherence after local edits.** The pipeline edits one step
   at a time; it re-runs the holistic judge afterward, but a locally
   "fixed" step can still read oddly in context. Spot-check `dataset.jsonl`
   manually, not just the per-step scores in the audit log.
