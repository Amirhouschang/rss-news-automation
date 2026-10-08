#!/usr/bin/env python3
"""Import existing Stage 4 records and summaries into PostgreSQL.

No downloads or model calls are performed. Existing news rows are preserved.
All inserts belong to one transaction, so a failure rolls back the import.
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from getpass import getpass
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb


def load_json(path):
    """Read an existing JSON object without modifying the source file."""
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object: {path.name}")
    return data


def parse_date(value, compact_utc=False):
    """Parse dates; preserve missing or ambiguous dates as NULL."""
    if not isinstance(value, str) or not value.strip():
        return None
    value = value.strip()
    if compact_utc:
        try:
            return datetime.strptime(value, "%Y%m%d_%H%M%S_%f").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            pass
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(value)
        except (ValueError, TypeError, OverflowError):
            return None
    # Do not guess a timezone for publication dates.
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


def record_key(record):
    """Match records by source feed and unchanged original URL."""
    feed = record.get("feed_url")
    url = record.get("original_url")
    if not isinstance(feed, str) or not feed.strip():
        raise ValueError("A record is missing its feed_url")
    if not isinstance(url, str) or not url.strip():
        raise ValueError("A record is missing its original_url")
    return feed, url


def index_records(records):
    """Reject duplicate keys instead of silently selecting a record."""
    if not isinstance(records, list):
        raise ValueError("Expected a list of input records")
    indexed = {}
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Expected an object for each input record")
        key = record_key(record)
        if key in indexed:
            raise ValueError(f"Duplicate input URL: {key[1]}")
        indexed[key] = record
    return indexed


def prepare_import(prepared, summaries, raw, model):
    """Validate matching inputs before opening a database transaction."""
    prepared_index = index_records(prepared.get("results"))
    raw_index = index_records(raw.get("entries"))
    fetched_at = parse_date(raw.get("fetched_at"), compact_utc=True)
    if fetched_at is None:
        raise ValueError("The raw snapshot has no usable fetched_at timestamp")
    attempts = summaries.get("attempts")
    if not isinstance(attempts, list):
        raise ValueError("The summaries file has no attempts list")

    rows = []
    seen = set()
    for attempt in attempts:
        if not isinstance(attempt, dict):
            raise ValueError("Invalid summary attempt")
        if attempt.get("model") != model or attempt.get("target_language") != "en":
            continue
        saved_record = attempt.get("full_record")
        if not isinstance(saved_record, dict):
            raise ValueError("A summary attempt has no full_record")
        key = record_key(saved_record)
        if key in seen:
            raise ValueError(f"Multiple model outputs for the same URL: {key[1]}")
        seen.add(key)
        if key not in prepared_index or key not in raw_index:
            raise ValueError(f"Summary URL not present in both inputs: {key[1]}")

        record = prepared_index[key]
        raw_record = raw_index[key]
        for field in ("original_title", "prepared_text", "text_basis"):
            if saved_record.get(field) != record.get(field):
                raise ValueError(f"Input mismatch for {field}: {key[1]}")
        if attempt.get("prepared_text") != record.get("prepared_text"):
            raise ValueError(f"Model input text mismatch: {key[1]}")
        if raw_record.get("original_title") != record.get("original_title"):
            raise ValueError(f"Raw title mismatch: {key[1]}")
        if not isinstance(record.get("original_title"), str):
            raise ValueError(f"Missing original title: {key[1]}")
        basis = record.get("text_basis")
        if basis not in ("article", "rss_content", "rss_summary", "unavailable"):
            raise ValueError(f"Unsupported text_basis: {basis}")

        successful = attempt.get("status") == "success"
        result = attempt.get("result") or {}
        sentences = result.get("summary_sentences")
        if successful:
            if not isinstance(sentences, list) or not 1 <= len(sentences) <= 2:
                raise ValueError(f"Invalid summary sentence list: {key[1]}")
            if any(not isinstance(s, str) or not s.strip() for s in sentences):
                raise ValueError(f"Empty or invalid summary sentence: {key[1]}")
            summary_text = "\n".join(sentences)
            error = None
        else:
            summary_text = None
            error = str(attempt.get("error_message") or attempt.get("error")
                        or "Saved model attempt was unsuccessful")

        response = attempt.get("full_response") or {}
        rows.append({
            "record": record,
            "raw_record": raw_record,
            "fetched_at": fetched_at,
            "summary_text": summary_text,
            "summarized_at": parse_date(response.get("created_at")) if successful else None,
            "status": "success" if successful else "failed",
            "error": error,
        })
    if not rows:
        raise ValueError(f"No English attempts found for model: {model}")
    return rows


def main():
    """Import archived outputs using the existing Stage 6 schema."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--summaries", type=Path, required=True)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--model", default="mistral-small3.1:latest")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5432)
    parser.add_argument("--database", default="rss_news")
    parser.add_argument("--user", default="rss_app")
    args = parser.parse_args()

    try:
        prepared = load_json(args.prepared)
        summaries = load_json(args.summaries)
        raw = load_json(args.raw)
        rows = prepare_import(prepared, summaries, raw, args.model)
        print(f"Validated {len(rows)} archived records for {args.model}")

        # Store import provenance and the exact historical prompt.
        prompt = summaries.get("system_prompt")
        if not isinstance(prompt, str) or not prompt:
            raise ValueError("Missing system prompt in summaries file")
        prompt_version = "sha256:" + hashlib.sha256(prompt.encode()).hexdigest()
        settings = {
            "original_generation_settings": summaries.get("generation_settings"),
            "think_mode": summaries.get("think_mode"),
            "model_digests": summaries.get("model_digests"),
            "system_prompt": prompt,
            "user_prompt_template": summaries.get("user_prompt_template"),
            "original_run_timestamp": summaries.get("run_timestamp"),
            "input_files": {
                "prepared": args.prepared.name,
                "summaries": args.summaries.name,
                "raw": args.raw.name,
            },
        }

        password = os.environ.get("PGPASSWORD") or getpass("Password for rss_app: ")
        inserted = skipped = failures = 0

        # The connection context commits only if every database operation succeeds.
        with psycopg.connect(
            host=args.host, port=args.port, dbname=args.database,
            user=args.user, password=password, connect_timeout=10,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SET LOCAL TIME ZONE 'UTC'")
                cursor.execute("SELECT source_id, feed_url, name, country FROM sources")
                sources = {row[1]: row for row in cursor.fetchall()}
                for row in rows:
                    record = row["record"]
                    source = sources.get(record["feed_url"])
                    if source is None:
                        raise ValueError(f"Source not configured: {record['feed_url']}")
                    if (source[2], source[3]) != (record["source"], record["country"]):
                        raise ValueError("Configured source metadata does not match input")

                cursor.execute(
                    """INSERT INTO runs
                       (run_type, model_name, prompt_version, generation_settings)
                       VALUES ('import', %s, %s, %s) RETURNING run_id""",
                    (args.model, prompt_version, Jsonb(settings)),
                )
                run_id = cursor.fetchone()[0]

                for row in rows:
                    record = row["record"]
                    # Missing publication dates remain NULL; updated_at stays in JSON.
                    publication_raw = record.get("published_at")
                    cursor.execute(
                        """INSERT INTO news (
                            source_id, run_id, original_title, original_url,
                            published_at, published_at_raw, fetched_at,
                            rss_summary_text, rss_content_text, article_text,
                            prepared_text, text_basis, summary_text, summarized_at,
                            processing_status, error_message, raw_rss_entry
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s
                        ) ON CONFLICT (source_id, original_url) DO NOTHING
                        RETURNING news_id""",
                        (
                            sources[record["feed_url"]][0], run_id,
                            record["original_title"], record["original_url"],
                            parse_date(publication_raw), publication_raw,
                            row["fetched_at"], record.get("rss_summary_text"),
                            record.get("rss_content_text"),
                            record.get("article_text_original") or record.get("article_text"),
                            record.get("prepared_text"), record["text_basis"],
                            row["summary_text"], row["summarized_at"],
                            row["status"], row["error"], Jsonb(row["raw_record"]),
                        ),
                    )
                    if cursor.fetchone() is None:
                        skipped += 1
                    else:
                        inserted += 1
                        failures += row["status"] == "failed"

                status = "success" if not failures else (
                    "failed" if failures == inserted else "partial"
                )
                cursor.execute(
                    """UPDATE runs SET finished_at = CURRENT_TIMESTAMP,
                       status = %s, new_count = %s, error_count = %s
                       WHERE run_id = %s""",
                    (status, inserted, failures, run_id),
                )

        print(f"Import committed. Run ID: {run_id}")
        print(f"Inserted: {inserted}; already present: {skipped}; failed summaries: {failures}")
        return 0
    except (OSError, ValueError, TypeError, KeyError, psycopg.Error) as error:
        print(f"Import failed; no changes from this import were committed: {error}",
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
