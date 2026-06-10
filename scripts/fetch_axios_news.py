#!/usr/bin/env python3
"""Fetch Axios news via RSS, filter by topic, extract vocab, and import without duplicates."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from pathlib import Path
from typing import Any
from urllib import error, request

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
DATA_DIR = BACKEND_DIR / "data"
CONFIG_PATH = DATA_DIR / "axios_news_config.json"
STATE_PATH = DATA_DIR / "axios_fetched_state.json"
ARTICLES_DIR = DATA_DIR / "axios_articles"
DEFAULT_API = "https://vocab-pwa-api.756121162.workers.dev"
USER_AGENT = "vocab-pwa-fetch/1.0"
OPENROUTER_DEFAULT_BASE = "https://openrouter.ai/api/v1"
OPENROUTER_DEFAULT_MODEL = "openrouter/free"
OPENROUTER_APP_URL = "https://github.com/seanzombias/vocab_pwa"
OPENROUTER_APP_TITLE = "vocab-pwa"
CONTENT_NS = "{http://purl.org/rss/1.0/modules/content/}encoded"
DATE_PATTERN = re.compile(r"\((\d{4}-\d{2}-\d{2})\)")
TAG_RE = re.compile(r"<[^>]+>")
AXIOS_COLUMNS = [
    "Why it matters",
    "Driving the news",
    "Catch up quick",
    "Flashback",
    "Zoom out",
    "Zoom in",
    "The intrigue",
    "Between the lines",
    "What they're saying",
    "The bottom line",
    "Go deeper",
    "Reality check",
]


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def html_to_text(html: str) -> str:
    text = unescape(TAG_RE.sub(" ", html or ""))
    return re.sub(r"\s+", " ", text).strip()


def fetch_url(url: str, timeout: int = 30) -> bytes:
    req = request.Request(url, headers={"User-Agent": USER_AGENT})
    with request.urlopen(req, timeout=timeout) as response:
        return response.read()


def parse_pub_date(value: str) -> str:
    if not value:
        return datetime.now(timezone.utc).date().isoformat()
    try:
        return parsedate_to_datetime(value).astimezone(timezone.utc).date().isoformat()
    except (TypeError, ValueError, OverflowError):
        return datetime.now(timezone.utc).date().isoformat()


def slugify(title: str, pub_date: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return f"{pub_date}_{slug[:60]}" or str(uuid.uuid4())


def build_source(title: str, pub_date: str) -> str:
    return f"Axios — {title} ({pub_date})"


def load_config(path: Path) -> dict[str, Any]:
    config = load_json(path, {})
    if not config:
        raise RuntimeError(f"Missing config: {path}")
    return config


def load_state(path: Path) -> dict[str, Any]:
    state = load_json(path, {"fetched_urls": [], "last_run": None})
    state.setdefault("fetched_urls", [])
    return state


def topic_match(text: str, config: dict[str, Any]) -> tuple[bool, list[str], list[str]]:
    lowered = text.lower()
    matched_topics: list[str] = []
    matched_tags: list[str] = []

    for topic_name, topic in (config.get("include_topics") or {}).items():
        keywords = topic.get("keywords") or []
        if any(keyword.lower() in lowered for keyword in keywords):
            matched_topics.append(topic_name)
            matched_tags.extend(topic.get("tags") or [])

    excluded = [
        keyword
        for keyword in (config.get("exclude_keywords") or [])
        if keyword.lower() in lowered
    ]
    if excluded:
        return False, matched_topics, matched_tags

    if not matched_topics:
        return False, matched_topics, matched_tags

    return True, matched_topics, list(dict.fromkeys(matched_tags))


def parse_feed(xml_bytes: bytes) -> list[dict[str, Any]]:
    root = ET.fromstring(xml_bytes)
    articles: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        if not title or not link or link in seen_urls:
            continue

        description_html = item.findtext("description") or ""
        encoded_el = item.find(CONTENT_NS)
        body_html = encoded_el.text if encoded_el is not None and encoded_el.text else description_html
        pub_date = parse_pub_date(item.findtext("pubDate") or "")
        preview_text = html_to_text(description_html)
        body_text = html_to_text(body_html)
        match_text = f"{title} {preview_text} {body_text}"

        seen_urls.add(link)
        articles.append(
            {
                "title": title,
                "url": link,
                "pub_date": pub_date,
                "preview": preview_text,
                "body": body_text,
                "match_text": match_text,
                "categories": [
                    (cat.text or "").strip()
                    for cat in item.findall("category")
                    if (cat.text or "").strip()
                ],
            }
        )

    return articles


def fetch_feed_articles(config: dict[str, Any]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for feed_url in config.get("feeds") or ["https://api.axios.com/feed/"]:
        xml_bytes = fetch_url(feed_url)
        for article in parse_feed(xml_bytes):
            merged[article["url"]] = article
    return list(merged.values())


def filter_articles(
    articles: list[dict[str, Any]],
    config: dict[str, Any],
    state: dict[str, Any],
) -> list[dict[str, Any]]:
    fetched = set(state.get("fetched_urls") or [])
    selected: list[dict[str, Any]] = []

    for article in articles:
        if article["url"] in fetched:
            continue
        ok, topics, tags = topic_match(article["match_text"], config)
        if not ok:
            continue
        selected.append(
            {
                **article,
                "topics": topics,
                "tags": tags,
                "source": build_source(article["title"], article["pub_date"]),
                "slug": slugify(article["title"], article["pub_date"]),
            }
        )

    selected.sort(key=lambda item: item["pub_date"], reverse=True)
    return selected


def extract_column_vocab(article: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    body = article["body"]
    source = article["source"]
    tags = list(dict.fromkeys(["Axios专栏", *article.get("tags", [])]))

    for column in AXIOS_COLUMNS:
        pattern = re.compile(rf"{re.escape(column)}:\s*(.+?)(?=(?:{'|'.join(map(re.escape, AXIOS_COLUMNS))}):|$)", re.I)
        match = pattern.search(body)
        if not match:
            continue
        sentence = match.group(1).strip()
        if len(sentence) < 20:
            continue
        entries.append(
            {
                "word": column,
                "phrase": f"{column}: {sentence[:80]}".rstrip(" ."),
                "meaning": f"Axios 专栏固定用语：{column}",
                "sentence": f"{column}: {sentence[:240]}",
                "source": source,
                "tags": tags,
            }
        )

    return entries


def read_env_value(key: str) -> str:
    value = os.getenv(key, "").strip()
    if value:
        return value
    env_file = BACKEND_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith(f"{key}="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def extract_vocab_with_llm(article: dict[str, Any], model: str, api_key: str, base_url: str) -> list[dict[str, Any]]:
    prompt = f"""你是英文精读助手。从下面 Axios 新闻正文中提取 8-15 条值得学习的词汇/短语/句式。

要求：
1. 优先提取专栏结构用语（Why it matters, Driving the news, Zoom out 等）和新闻中的高级表达
2. meaning 用中文，简洁说明在本文语境中的含义
3. sentence 必须来自原文
4. tags 包含主题标签 {article.get("tags", [])}，并补充词性标签如 verb/noun/phrase/句式
5. 只输出 JSON 数组，不要 markdown

文章标题：{article["title"]}
正文：
{article["body"][:6000]}
"""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You extract vocabulary for Chinese learners from English news. Reply with JSON array only."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "User-Agent": USER_AGENT,
    }
    if "openrouter.ai" in base_url:
        headers["HTTP-Referer"] = read_env_value("OPENROUTER_APP_URL") or OPENROUTER_APP_URL
        headers["X-OpenRouter-Title"] = read_env_value("OPENROUTER_APP_TITLE") or OPENROUTER_APP_TITLE
    req = request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=120) as response:
            body = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"LLM request failed ({exc.code}): {detail}") from exc

    content = body["choices"][0]["message"]["content"].strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?|```$", "", content, flags=re.M).strip()
    items = json.loads(content)
    if not isinstance(items, list):
        raise RuntimeError("LLM response is not a JSON array")

    normalized: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        entry = {
            "word": str(item.get("word", "")).strip(),
            "phrase": str(item.get("phrase", "")).strip(),
            "meaning": str(item.get("meaning", "")).strip(),
            "sentence": str(item.get("sentence", "")).strip(),
            "source": article["source"],
            "tags": item.get("tags") or article.get("tags", []),
        }
        if entry["word"] and entry["meaning"] and entry["sentence"]:
            normalized.append(entry)
    return normalized


def extract_vocab(article: dict[str, Any], use_llm: bool, model: str, api_key: str, base_url: str) -> list[dict[str, Any]]:
    if use_llm and api_key:
        try:
            return extract_vocab_with_llm(article, model, api_key, base_url)
        except Exception as exc:
            print(f"LLM extraction failed for {article['title']}: {exc}", file=sys.stderr)
    return extract_column_vocab(article)


def dedupe_vocab_entries(entries: list[dict[str, Any]], existing_keys: set[tuple[str, str, str]]) -> list[dict[str, Any]]:
    unique: list[dict[str, Any]] = []
    for entry in entries:
        key = (
            (entry.get("source") or "").strip().lower(),
            (entry.get("word") or "").strip().lower(),
            (entry.get("sentence") or "").strip().lower(),
        )
        if key in existing_keys:
            continue
        existing_keys.add(key)
        unique.append(entry)
    return unique


def load_existing_vocab_keys(local: bool) -> set[tuple[str, str, str]]:
    keys: set[tuple[str, str, str]] = set()

    for json_path in DATA_DIR.glob("axios_*_vocab.json"):
        for item in load_json(json_path, []):
            keys.add(
                (
                    str(item.get("source", "")).strip().lower(),
                    str(item.get("word", "")).strip().lower(),
                    str(item.get("sentence", "")).strip().lower(),
                )
            )

    for article_path in ARTICLES_DIR.glob("*.json"):
        article = load_json(article_path, {})
        for item in article.get("vocab") or []:
            keys.add(
                (
                    str(item.get("source", "")).strip().lower(),
                    str(item.get("word", "")).strip().lower(),
                    str(item.get("sentence", "")).strip().lower(),
                )
            )

    if local:
        import sqlite3

        db_path = BACKEND_DIR / "data" / "vocab.db"
        if db_path.exists():
            conn = sqlite3.connect(db_path)
            try:
                rows = conn.execute("SELECT source, word, sentence FROM vocab").fetchall()
                for source, word, sentence in rows:
                    keys.add((str(source).strip().lower(), str(word).strip().lower(), str(sentence).strip().lower()))
            finally:
                conn.close()

    return keys


def enrich_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    enriched = []
    for item in items:
        entry = dict(item)
        if not entry.get("created_at"):
            source = entry.get("source") or ""
            match = DATE_PATTERN.search(source)
            date = match.group(1) if match else datetime.now(timezone.utc).date().isoformat()
            entry["created_at"] = f"{date}T12:00:00+00:00"
        enriched.append(entry)
    return enriched


def import_vocab(items: list[dict[str, Any]], *, local: bool, api_base: str, token: str | None) -> dict[str, Any]:
    items = enrich_items(items)
    if local:
        sys.path.insert(0, str(BACKEND_DIR))
        from db import get_db  # noqa: WPS433

        return get_db().create_many_deduped(items)

    url = f"{api_base.rstrip('/')}/api/vocab/import"
    payload = json.dumps(items).encode("utf-8")
    req = request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Import failed ({exc.code}): {detail}") from exc


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


def resolve_llm_settings(args: argparse.Namespace) -> tuple[str, str, str]:
    api_key = (
        args.llm_api_key
        or read_env_value("OPENROUTER_API_KEY")
        or read_env_value("OPENAI_API_KEY")
        or ""
    ).strip()
    base_url = (
        args.llm_base_url
        or read_env_value("OPENROUTER_BASE_URL")
        or read_env_value("OPENAI_BASE_URL")
        or OPENROUTER_DEFAULT_BASE
    ).strip()
    model = (
        args.llm_model
        or read_env_value("OPENROUTER_MODEL")
        or read_env_value("OPENAI_MODEL")
        or OPENROUTER_DEFAULT_MODEL
    ).strip()
    return api_key, base_url, model


def run(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    state = load_state(args.state)
    all_articles = fetch_feed_articles(config)
    candidates = filter_articles(all_articles, config, state)

    if args.max_items:
        candidates = candidates[: args.max_items]

    if args.dry_run:
        print(f"Feed articles: {len(all_articles)}")
        print(f"New matching articles: {len(candidates)}")
        for article in candidates:
            print(f"- [{', '.join(article['topics'])}] {article['title']} ({article['pub_date']})")
        return 0

    if not candidates:
        print("No new matching Axios articles.")
        state["last_run"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        save_json(args.state, state)
        return 0

    api_key, base_url, model = resolve_llm_settings(args)
    use_llm = not args.no_llm
    if use_llm and not api_key:
        print(
            "OPENROUTER_API_KEY not set; falling back to Axios column phrase extraction.",
            file=sys.stderr,
        )
        use_llm = False
    elif use_llm:
        print(f"LLM: {model} via {base_url}")

    existing_keys = load_existing_vocab_keys(args.local)
    fetched_urls = set(state.get("fetched_urls") or [])
    all_vocab: list[dict[str, Any]] = []
    saved_articles = 0

    ARTICLES_DIR.mkdir(parents=True, exist_ok=True)

    for article in candidates:
        vocab = extract_vocab(article, use_llm, model, api_key, base_url)
        vocab = dedupe_vocab_entries(vocab, existing_keys)
        article_record = {
            "title": article["title"],
            "url": article["url"],
            "pub_date": article["pub_date"],
            "topics": article["topics"],
            "tags": article["tags"],
            "source": article["source"],
            "body": article["body"],
            "vocab_count": len(vocab),
            "vocab": vocab,
            "fetched_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        }
        save_json(ARTICLES_DIR / f"{article['slug']}.json", article_record)
        fetched_urls.add(article["url"])
        all_vocab.extend(vocab)
        saved_articles += 1
        print(f"Saved: {article['title']} ({len(vocab)} vocab entries)")

    state["fetched_urls"] = sorted(fetched_urls)
    state["last_run"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    save_json(args.state, state)

    print(f"Fetched {saved_articles} new articles, extracted {len(all_vocab)} vocab entries.")

    if args.import_vocab and all_vocab:
        token = None if args.local else resolve_token(args.token)
        result = import_vocab(all_vocab, local=args.local, api_base=args.api, token=token)
        created = result.get("count", len(result.get("items", [])))
        skipped = result.get("skipped", 0)
        print(f"Imported {created} entries (skipped {skipped} duplicates).")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch Axios news and extract vocabulary.")
    parser.add_argument("--config", type=Path, default=CONFIG_PATH, help="Topic filter config JSON")
    parser.add_argument("--state", type=Path, default=STATE_PATH, help="Fetched URL state JSON")
    parser.add_argument("--max-items", type=int, default=5, help="Max new articles per run")
    parser.add_argument("--dry-run", action="store_true", help="Preview matches without saving")
    parser.add_argument("--import", dest="import_vocab", action="store_true", help="Import extracted vocab")
    parser.add_argument("--local", action="store_true", help="Import into local SQLite via backend/db.py")
    parser.add_argument("--api", default=DEFAULT_API, help="Remote API base URL for import")
    parser.add_argument("--token", help="Bearer token for remote import")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM extraction; use Axios column phrases only")
    parser.add_argument("--llm-api-key", help="LLM API key (or OPENROUTER_API_KEY env)")
    parser.add_argument("--llm-base-url", help="LLM base URL (default: OpenRouter)")
    parser.add_argument(
        "--llm-model",
        help="Model slug (default: openrouter/free; also try google/gemma-2-9b-it:free)",
    )
    args = parser.parse_args()
    try:
        return run(args)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
