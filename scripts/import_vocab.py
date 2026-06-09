#!/usr/bin/env python3
"""Import vocabulary entries from a JSON file."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib import error, request

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
DEFAULT_API = "https://vocab-pwa-api.onrender.com"


def load_items(path: Path) -> list:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError("JSON file must contain an array of vocabulary objects")
    return data


def import_remote(api_base: str, token: str, items: list) -> dict:
    url = f"{api_base.rstrip('/')}/api/vocab/import"
    payload = json.dumps(items).encode("utf-8")
    req = request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=60) as response:
            body = response.read().decode("utf-8")
            return json.loads(body)
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Import failed ({exc.code}): {detail}") from exc


def import_local(items: list) -> dict:
    sys.path.insert(0, str(BACKEND_DIR))
    from db import get_db  # noqa: WPS433

    created = get_db().create_many(items)
    return {"count": len(created), "items": created}


def resolve_token(explicit: str | None) -> str:
    if explicit:
        return explicit.strip()
    for key in ("VOCAB_API_TOKEN",):
        value = os.getenv(key, "").strip()
        if value:
            return value
    env_file = BACKEND_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("VOCAB_API_TOKEN="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("Missing API token. Pass --token or set VOCAB_API_TOKEN.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Import vocabulary JSON into vocab_pwa.")
    parser.add_argument("json_file", type=Path, help="Path to JSON array file")
    parser.add_argument("--api", default=DEFAULT_API, help="Remote API base URL")
    parser.add_argument("--token", help="Bearer token for remote import")
    parser.add_argument("--local", action="store_true", help="Write directly to local SQLite")
    args = parser.parse_args()

    if not args.json_file.exists():
        print(f"File not found: {args.json_file}", file=sys.stderr)
        return 1

    items = load_items(args.json_file)
    if args.local:
        result = import_local(items)
    else:
        token = resolve_token(args.token)
        result = import_remote(args.api, token, items)

    print(f"Imported {result.get('count', len(items))} entries.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
