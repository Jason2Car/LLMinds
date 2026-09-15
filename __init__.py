"""
CRISP-style generate -> critique -> pinpoint -> refine -> score loop,
split into one module per stage.

Stages:
    generate.py     -- initial step-broken response generation
    evaluate.py      -- holistic judge, pinpoints the flawed step
    propose.py       -- decides adjust/delete/add and gives guidance
    candidates.py    -- samples candidate rewrites of a flawed step
    score.py         -- scores a single candidate 1-10
    search.py         -- the reward-based candidate search over a step
    orchestrator.py  -- ties every stage together into the full loop
"""

from .orchestrator import run_pipeline

__all__ = ["run_pipeline"]
