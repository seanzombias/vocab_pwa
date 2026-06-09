#!/usr/bin/env python3
"""Build frontend/data/vocab.json from backend import files."""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [
    ROOT / "backend" / "data" / "axios_article_vocab.json",
    ROOT / "backend" / "data" / "axios_analog_learning_vocab.json",
]
OUTPUT = ROOT / "frontend" / "data" / "vocab.json"
DATE_PATTERN = re.compile(r"\((\d{4}-\d{2}-\d{2})\)")


def infer_date(item: dict) -> str:
    source = item.get("source") or ""
    match = DATE_PATTERN.search(source)
    if match:
        return match.group(1)
    return "2026-05-29"


def normalize(items: list) -> list:
    result = []
    for item in items:
        date = infer_date(item)
        result.append(
            {
                "id": str(uuid.uuid4()),
                "word": item["word"],
                "phrase": item.get("phrase") or "",
                "meaning": item["meaning"],
                "sentence": item["sentence"],
                "source": item.get("source") or "",
                "tags": item.get("tags") or [],
                "created_at": f"{date}T12:00:00+00:00",
            }
        )
    return result


def main() -> int:
    merged: list = []
    for path in SOURCES:
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, list):
            merged.extend(data)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(normalize(merged), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(merged)} entries to {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
