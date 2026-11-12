"""
Password-protected admin pages for viewing and downloading results.

Enabled only when the ADMIN_PASSWORD environment variable is set (any
username works); otherwise every /admin URL returns 404. Use over HTTPS.
"""

import csv
import hmac
import io
import json
import os

from flask import Blueprint, Response, abort, request

import storage

admin = Blueprint("admin", __name__, url_prefix="/admin")

CSV_COLUMNS = [
    "completed_at", "archetype", "messages_before_change", "total_displacement",
    "items_moved", "max_move", "confidence", "initial_ranking", "final_ranking",
    "session_id",
]


@admin.before_request
def _require_password():
    password = os.environ.get("ADMIN_PASSWORD")
    if not password:
        abort(404)
    auth = request.authorization
    supplied = (auth.password or "") if auth else ""
    if not hmac.compare_digest(supplied.encode(), password.encode()):
        return Response("Login required.", 401,
                        {"WWW-Authenticate": 'Basic realm="Study admin"'})


@admin.get("/")
def dashboard():
    counts = storage.tally()
    target = int(os.environ.get("PER_ARCHETYPE", "10"))
    rows = "".join(
        f"<tr><td>{a}</td><td>{n} / {target}</td></tr>" for a, n in counts.items()
    )
    return (
        "<!doctype html><meta charset=utf-8><title>Study admin</title>"
        "<body style='font-family:system-ui;max-width:520px;margin:32px auto;padding:0 16px'>"
        "<h1>Study results</h1>"
        f"<p>{sum(counts.values())} completed tests.</p>"
        "<table border=1 cellpadding=6 style='border-collapse:collapse'>"
        f"<tr><th>Archetype</th><th>Completed</th></tr>{rows}</table>"
        "<p><a href='/admin/results.csv'>Download results.csv</a> (summary, opens in Excel)<br>"
        "<a href='/admin/results.jsonl'>Download results.jsonl</a> (full data with transcripts)</p>"
        "</body>"
    )


@admin.get("/results.csv")
def results_csv():
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(CSV_COLUMNS)
    for r in storage.load_results():
        row = dict(r)
        row["initial_ranking"] = " > ".join(r["initial_ranking"])
        row["final_ranking"] = " > ".join(r["final_ranking"])
        writer.writerow([row.get(c, "") for c in CSV_COLUMNS])
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=results.csv"})


@admin.get("/results.jsonl")
def results_jsonl():
    body = "".join(json.dumps(r) + "\n" for r in storage.load_results())
    return Response(body, mimetype="application/x-ndjson",
                    headers={"Content-Disposition": "attachment; filename=results.jsonl"})
