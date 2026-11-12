"""
Stranded-on-the-moon persuasion study.

Flow: start -> initial ranking -> chat with the persuader -> final ranking
-> 1-7 confidence rating -> result saved.

Run locally from this folder:  python app.py   (http://localhost:5001)
In production:  gunicorn app:app  (see ../render.yaml)
"""

import os
import time
import uuid

from flask import Flask, jsonify, request

import persuader
import storage
from scenario import ITEMS, SCENARIO_TEXT, is_valid_ranking, rank_change

app = Flask(__name__, static_folder="static", static_url_path="")

# Target number of participants per archetype (completed tests plus tests in
# progress); once every archetype has this many, the study is closed.
PER_ARCHETYPE = int(os.environ.get("PER_ARCHETYPE", "10"))
SESSION_TTL = 60 * 60  # abandoned sessions stop holding a slot after an hour
MAX_MESSAGES = int(os.environ.get("MAX_MESSAGES", "40"))  # user messages per session
MAX_MESSAGE_CHARS = 1000

# In-progress sessions, keyed by session id. Lost on restart; only completed
# tests are persisted.
sessions: dict[str, dict] = {}


def _session():
    s = sessions.get((request.get_json(silent=True) or {}).get("session_id"))
    return s


def _user_messages(s) -> int:
    return sum(1 for m in s["history"] if m["role"] == "user")


def _error(msg, code=400):
    return jsonify({"error": msg}), code


def _llm_error():
    """Log the real failure server-side; visitors only get a generic message
    (provider errors can echo back part of the API key)."""
    app.logger.exception("LLM call failed")
    return _error("Something went wrong generating a reply. Please try again.", 502)


@app.get("/")
def index():
    return app.send_static_file("index.html")


@app.post("/api/start")
def start():
    now = time.time()
    for key in [k for k, v in sessions.items() if now - v["started_at"] > SESSION_TTL]:
        del sessions[key]
    active = {a: 0 for a in storage.ARCHETYPES}
    for v in sessions.values():
        active[v["archetype"]] += 1
    archetype = storage.least_tested_archetype(active, PER_ARCHETYPE)
    if archetype is None:
        return _error("This study has reached its maximum number of responses. "
                      "Thank you for your interest!", 403)
    sid = uuid.uuid4().hex
    sessions[sid] = {
        "archetype": archetype,
        "stage": "initial",
        "started_at": time.time(),
        "history": [],
    }
    # The archetype is deliberately not sent to the browser.
    return jsonify({"session_id": sid, "scenario": SCENARIO_TEXT, "items": ITEMS,
                    "max_messages": MAX_MESSAGES})


@app.post("/api/ranking")
def initial_ranking():
    s = _session()
    ranking = (request.get_json() or {}).get("ranking")
    if not s or s["stage"] != "initial":
        return _error("Unknown session or wrong stage.")
    if not is_valid_ranking(ranking):
        return _error("Ranking must contain all 20 items exactly once.")
    try:
        opening = persuader.reply(s["archetype"], ranking, [])
    except Exception:
        return _llm_error()
    s["initial_ranking"] = ranking
    s["stage"] = "chat"
    s["history"].append({"role": "assistant", "content": opening})
    return jsonify({"message": opening})


@app.post("/api/message")
def message():
    s = _session()
    text = ((request.get_json() or {}).get("message") or "").strip()
    if not s or s["stage"] != "chat":
        return _error("Unknown session or wrong stage.")
    if not text:
        return _error("Empty message.")
    if len(text) > MAX_MESSAGE_CHARS:
        return _error(f"Messages are limited to {MAX_MESSAGE_CHARS} characters.")
    if _user_messages(s) >= MAX_MESSAGES:
        return _error("You've reached the message limit. Please re-rank to continue.")
    history = s["history"] + [{"role": "user", "content": text}]
    try:
        answer = persuader.reply(s["archetype"], s["initial_ranking"], history)
    except Exception:
        return _llm_error()
    s["history"] = history + [{"role": "assistant", "content": answer}]
    return jsonify({"message": answer, "remaining": MAX_MESSAGES - _user_messages(s)})


@app.post("/api/final")
def final_ranking():
    s = _session()
    ranking = (request.get_json() or {}).get("ranking")
    if not s or s["stage"] != "chat":
        return _error("Unknown session or wrong stage.")
    if not is_valid_ranking(ranking):
        return _error("Ranking must contain all 20 items exactly once.")
    s["final_ranking"] = ranking
    s["stage"] = "confidence"
    return jsonify({"ok": True})


@app.post("/api/confidence")
def confidence():
    s = _session()
    rating = (request.get_json() or {}).get("confidence")
    if not s or s["stage"] != "confidence":
        return _error("Unknown session or wrong stage.")
    if not isinstance(rating, int) or not 1 <= rating <= 7:
        return _error("Confidence must be an integer from 1 to 7.")

    change = rank_change(s["initial_ranking"], s["final_ranking"])
    storage.save_result({
        "session_id": request.get_json()["session_id"],
        "archetype": s["archetype"],
        "completed_at": time.time(),
        "messages_before_change": sum(1 for m in s["history"] if m["role"] == "user"),
        "initial_ranking": s["initial_ranking"],
        "final_ranking": s["final_ranking"],
        "total_displacement": change["total_displacement"],
        "items_moved": change["items_moved"],
        "max_move": change["max_move"],
        "confidence": rating,
        "transcript": s["history"],
    })
    del sessions[request.get_json()["session_id"]]
    return jsonify({"ok": True})


@app.get("/api/tally")
def tally():
    return jsonify(storage.tally())


if __name__ == "__main__":
    app.run(port=int(os.environ.get("PORT", "5001")))
