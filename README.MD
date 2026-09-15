# CRISP-style trait-conditioned text generation

Adapts the "Critique-and-Replan" loop from *The Robot's Inner Critic*
(arXiv:2603.20164) from robot joint control to text generation for
trait-conditioned synthetic training data.

## Setup

```bash
pip install openai
export OPENAI_API_KEY=your_key_here
```

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
- `prompts.py` -- every prompt template used by the loop.
- `llm_client.py` -- thin OpenAI API wrapper with JSON-safe parsing and retries.
- `crisp_pipeline.py` -- the actual generate -> critique -> pinpoint ->
  refine -> score loop.
- `generate_dataset.py` -- loops the pipeline over your full trait/level/
  scenario grid and writes output files.

## How this maps to the original CRISP paper

| Paper (robot behavior) | This pipeline (text) |
|---|---|
| Robot structure file (joints, limits) | `TRAITS` + `LEVELS` in config.py |
| Behavior Generator (steps with timing) | `generate_initial_steps` (sentence-level steps) |
| VLM holistic evaluation | `evaluate_response` (LLM judge) |
| Pinpoint erroneous step | `flagged_step_id` in judge output |
| Adjust / Delete / Add proposal | `propose_refinement` |
| Reward-based Adaptive Search (3 candidates, sigma scaling) | `refine_step` (3 candidates, broad/fine search width) |
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
