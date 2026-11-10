"""
Flat-file storage. results.jsonl holds one record per completed test; the
archetype tally is derived from it, so the two can never disagree.
"""

import json
import os
import random
import threading

# DATA_DIR can point at a persistent disk on a hosted deployment.
DATA_DIR = os.environ.get(
    "DATA_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
)
RESULTS_FILE = os.path.join(DATA_DIR, "results.jsonl")

# Archetypes are the Dark Triad profiles under ../config/profiles/.
ARCHETYPES = ["narcissistic", "machiavellian", "psychopathic", "baseline"]

_lock = threading.Lock()


def save_result(record: dict) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with _lock, open(RESULTS_FILE, "a") as f:
        f.write(json.dumps(record) + "\n")


def load_results() -> list[dict]:
    if not os.path.exists(RESULTS_FILE):
        return []
    with open(RESULTS_FILE) as f:
        return [json.loads(line) for line in f if line.strip()]


def tally() -> dict[str, int]:
    counts = {a: 0 for a in ARCHETYPES}
    for r in load_results():
        if r.get("archetype") in counts:
            counts[r["archetype"]] += 1
    return counts


def least_tested_archetype(in_progress: dict[str, int] | None = None, limit: int | None = None) -> str | None:
    """Archetype with the fewest tests (completed plus in progress); ties random.

    With `limit`, archetypes already at the limit are skipped; returns None
    when every archetype is full.
    """
    counts = tally()
    for archetype, n in (in_progress or {}).items():
        counts[archetype] += n
    open_slots = {a: n for a, n in counts.items() if limit is None or n < limit}
    if not open_slots:
        return None
    fewest = min(open_slots.values())
    return random.choice([a for a, n in open_slots.items() if n == fewest])
