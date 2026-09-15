"""
Driver script: runs the CRISP loop across every (trait, level, scenario)
combination in config.py and writes results to JSONL files.

Usage:
    export ANTHROPIC_API_KEY=your_key_here
    python generate_dataset.py

Outputs:
    dataset.jsonl       -- one clean training example per line
    dataset_audit.jsonl -- same examples plus the full generate/critique/
                            refine log, for debugging and manual QA
"""

import json
import logging

import config
from pipeline import run_pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def main():
    total = len(config.TRAITS) * len(config.LEVELS) * len(config.SCENARIOS)
    done = 0

    with open("dataset.jsonl", "w") as clean_out, open("dataset_audit.jsonl", "w") as audit_out:
        for trait in config.TRAITS:
            for level in config.LEVELS:
                for scenario in config.SCENARIOS:
                    done += 1
                    log.info(f"[{done}/{total}] trait={trait} level={level} scenario={scenario[:40]}...")

                    try:
                        result = run_pipeline(trait, level, scenario)
                    except Exception as e:  # noqa: BLE001
                        log.error(f"Failed on trait={trait} level={level} scenario={scenario}: {e}")
                        continue

                    clean_record = {
                        "trait": result["trait"],
                        "level": result["level"],
                        "scenario": result["scenario"],
                        "response": result["final_text"],
                    }
                    clean_out.write(json.dumps(clean_record) + "\n")
                    clean_out.flush()

                    audit_out.write(json.dumps(result) + "\n")
                    audit_out.flush()

    log.info(f"Done. Wrote {done} records to dataset.jsonl (see dataset_audit.jsonl for full logs).")


if __name__ == "__main__":
    main()
