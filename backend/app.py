import csv
import io
from functools import wraps
from typing import Any, Callable

from flask import Flask, jsonify, request, Response
from flask_cors import CORS

from config import ALLOWED_ORIGINS, PORT, SECRET_KEY, VOCAB_API_TOKEN
from db import get_db

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY
CORS(app, origins=ALLOWED_ORIGINS, supports_credentials=False)


def require_token(view: Callable) -> Callable:
    @wraps(view)
    def wrapped(*args: Any, **kwargs: Any):
        auth = request.headers.get("Authorization", "")
        token = auth[7:].strip() if auth.startswith("Bearer ") else ""
        if not token or token != VOCAB_API_TOKEN:
            return jsonify({"error": "Unauthorized"}), 401
        return view(*args, **kwargs)

    return wrapped


@app.get("/api/health")
def health():
    try:
        database = get_db()
        ok = database.ping()
        return jsonify({"status": "ok", "db": database.backend, "db_ok": ok})
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 503


@app.get("/api/vocab")
def list_vocab():
    today = request.args.get("today") in {"1", "true", "yes"}
    items = get_db().list_vocab(
        date=request.args.get("date") or None,
        tag=request.args.get("tag") or None,
        today=today,
        query=request.args.get("q") or None,
    )
    return jsonify({"items": items, "count": len(items)})


@app.get("/api/vocab/tags")
def vocab_tags():
    return jsonify({"tags": get_db().get_tags()})


@app.get("/api/vocab/dates")
def vocab_dates():
    return jsonify({"dates": get_db().get_dates()})


@app.post("/api/vocab")
@require_token
def create_vocab():
    payload = request.get_json(silent=True) or {}
    try:
        item = get_db().create(payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"item": item}), 201


@app.post("/api/vocab/import")
@require_token
def import_vocab():
    payload = request.get_json(silent=True)
    if not isinstance(payload, list):
        return jsonify({"error": "Expected a JSON array"}), 400
    try:
        result = get_db().create_many_deduped(payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result), 201


@app.delete("/api/vocab/<entry_id>")
@require_token
def delete_vocab(entry_id: str):
    if not get_db().delete(entry_id):
        return jsonify({"error": "Not found"}), 404
    return jsonify({"ok": True})


def _anki_front(item: dict) -> str:
    phrase = item.get("phrase") or ""
    if phrase:
        return f"{item['word']}\n{phrase}"
    return item["word"]


def _anki_back(item: dict) -> str:
    parts = [item["meaning"]]
    if item.get("phrase"):
        parts.append(f"短语: {item['phrase']}")
    parts.append(f"原句: {item['sentence']}")
    if item.get("source"):
        parts.append(f"来源: {item['source']}")
    return "\n\n".join(parts)


@app.get("/api/export/anki.csv")
def export_anki_csv():
    today = request.args.get("today") in {"1", "true", "yes"}
    items = get_db().list_vocab(
        date=request.args.get("date") or None,
        tag=request.args.get("tag") or None,
        today=today,
        query=request.args.get("q") or None,
    )

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Front", "Back", "Tags"])
    for item in items:
        tags = " ".join(item.get("tags") or [])
        writer.writerow([_anki_front(item), _anki_back(item), tags])

    output = "\ufeff" + buffer.getvalue()
    return Response(
        output,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=vocab_anki.csv"},
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=True)
