"""
The live CRISP loop, one module per stage, matching the proposal's
four-stage design:

    profile.py    -- Trait Profile Specification (loads the target vector)
    generator.py  -- Response Generator
    evaluator.py  -- Trait Evaluator
    refiner.py    -- Response Refiner (reward-based adaptive search)
    orchestrator.py -- ties every stage together into the live loop
"""

from .orchestrator import handle_user_message

__all__ = ["handle_user_message"]
