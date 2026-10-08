#!/usr/bin/env python3
"""Archive today's RSS news, then summarize a uniform random sample per source.

Store original data in PostgreSQL before extraction or model inference.
Use one fixed local model. Do not modify the Stage 4 scripts or archived data.
Run from any directory; Stage 4 paths are resolved relative to this file.
Persist the sample in runs.generation_settings before processing it.
Use --resume-run RUN_ID to retry the same sample without drawing again.
"""

import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys
import random
import time
from datetime import date, datetime, timezone
from email.utils import parsedate_to_datetime
from getpass import getpass
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import psycopg
import requests
from psycopg.types.json import Jsonb


# Keep one model for the operational pipeline.
MODEL_NAME = "mistral-small3.1:latest"
LOCK_KEY = 726384190
STAGE4_DIR = Path(__file__).resolve().parent.parent / "stage4"
DAY_TIMEZONE = ZoneInfo("Europe/Berlin")


def load_script(name, path):
    """Load existing helper functions without calling the script's main()."""
    if not path.is_file():
        raise FileNotFoundError(f"Required Stage 4 script is missing: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_date(value):
    """Convert explicit publication times to UTC without guessing timezones."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(value)
        except (ValueError, TypeError, OverflowError):
            return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


def make_raw_record(source, entry):
    """Preserve the original RSS title, URL, dates and content."""
    return {
        "country": source["country"],
        "source": source["name"],
        "feed_url": source["feed_url"],
        "original_title": entry.get("title", ""),
        "original_url": entry.get("link"),
        "published_at": entry.get("published"),
        "updated_at": entry.get("updated"),
        "raw_rss_summary": entry.get("summary", ""),
        "raw_rss_content": entry.get("content", []),
        "rss_entry": json.loads(json.dumps(dict(entry), ensure_ascii=False, default=str)),
    }


def filter_source_day(raw, target_day, allow_updated=False):
    """Use publication dates; permit update dates only when explicitly requested.

    Explicit timezones are converted to Europe/Berlin. A timezone-free date
    is compared as the calendar date supplied by the publisher, without
    inventing a UTC timestamp. Never substitute the fetch date.
    """
    field = "published_at"
    value = raw.get(field)
    if not value and allow_updated:
        field = "updated_at"
        value = raw.get(field)
    if not isinstance(value, str) or not value.strip():
        return False, "missing_date"
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(value)
        except (ValueError, TypeError, OverflowError):
            return False, "missing_date"
    aware = parsed.tzinfo is not None and parsed.utcoffset() is not None
    source_day = parsed.astimezone(DAY_TIMEZONE).date() if aware else parsed.date()
    if source_day != target_day:
        return False, "other_day"
    raw["_date_filter"] = {
        "target_date": target_day.isoformat(),
        "field": field,
        "original_value": value,
        "calendar_basis": "Europe/Berlin" if aware else "publisher_date_without_timezone",
    }
    return True, None


def resolve_dw_publication(raw):
    """Read the original publication date from DW article metadata.

    Keep the RSS date separately. Never use dateModified as datePublished.
    Reject absent or conflicting publication metadata rather than guessing.
    """
    url = raw.get("original_url") or ""
    host = urlparse(url).hostname or ""
    if host != "dw.com" and not host.endswith(".dw.com"):
        return
    if raw.get("published_at"):
        return
    try:
        response = requests.get(
            url, headers={"User-Agent": "Mozilla/5.0"}, timeout=(5, 15)
        )
        response.raise_for_status()
        values = set(re.findall(
            r'"datePublished"\s*:\s*"([^"\r\n]+)"', response.text
        ))
        if len(values) != 1:
            raise ValueError("Missing or conflicting datePublished metadata")
        value = values.pop()
        if parse_date(value) is None:
            raise ValueError("Publication metadata has no valid timezone-aware date")
        raw["rss_published_at"] = raw.get("published_at")
        raw["published_at"] = value
        raw["_publication_metadata"] = {
            "field": "datePublished", "value": value,
            "origin": "article", "final_url": response.url,
        }
    except (requests.RequestException, ValueError) as error:
        raw["_publication_metadata"] = {"error": str(error), "origin": "article"}
        print(f"DW publication date unavailable: {url}: {error}", flush=True)


def prepare_record(preparation, raw):
    """Reuse Stage 4 extraction and its article/content/summary priority."""
    result = preparation.fetch_article(raw["original_url"])
    summary = preparation.strip_tags(raw.get("raw_rss_summary") or "")
    content = " ".join(
        preparation.strip_tags(item.get("value") or "")
        for item in (raw.get("raw_rss_content") or [])
        if isinstance(item, dict) and item.get("value")
    )
    original_article = result.get("article_text")
    text = None
    basis = "unavailable"
    cleanup = False
    if result.get("status") == "success" and original_article and original_article.strip():
        text, cleanup = preparation.clean_chinanews_footer(
            original_article, raw["original_url"]
        )
        basis = "article"
    elif content.strip():
        text, basis = content, "rss_content"
    elif summary.strip():
        text, basis = summary, "rss_summary"

    record = dict(raw)
    record.update({
        "article_text": original_article,
        "rss_summary_text": summary,
        "rss_content_text": content,
        "prepared_text": text,
        "text_basis": basis,
    })
    # Preserve extraction failures even when an RSS fallback succeeds.
    metadata = dict(raw)
    metadata["_extraction"] = {
        "status": result.get("status"),
        "http_status": result.get("http_status"),
        "final_url": result.get("final_url"),
        "error_message": result.get("error_message"),
        "rejected_text": result.get("rejected_text"),
        "article_cleanup_applied": cleanup,
    }
    return record, metadata


def process_news(connection, preparation, summarization, news_id, run_id, raw):
    """Commit prepared text before generation and persist the final outcome."""
    record, metadata = prepare_record(preparation, raw)
    with connection.cursor() as cursor:
        cursor.execute(
            """UPDATE news SET run_id = %s, article_text = %s,
               rss_summary_text = %s, rss_content_text = %s,
               prepared_text = %s, text_basis = %s, raw_rss_entry = %s,
               processing_status = 'processing', error_message = NULL
               WHERE news_id = %s""",
            (run_id, record["article_text"], record["rss_summary_text"],
             record["rss_content_text"], record["prepared_text"],
             record["text_basis"], Jsonb(metadata), news_id),
        )

    if not record["original_title"] or not str(record["original_title"]).strip():
        output = {"status": "error", "error": "Missing original title"}
    elif not record["prepared_text"] or not record["prepared_text"].strip():
        output = {"status": "error", "error": "No usable article or RSS text"}
    else:
        print(f"Summarizing news {news_id}: {raw['country']} | {record['text_basis']}", flush=True)
        output = summarization.execute_generation(MODEL_NAME, "en", record, False)

    success = output.get("status") == "success"
    summary_text = None
    if success:
        result = output.get("result") or {}
        sentences = result.get("summary_sentences")
        if not isinstance(sentences, list) or not 1 <= len(sentences) <= 2 or any(
            not isinstance(sentence, str) or not sentence.strip() for sentence in sentences
        ):
            success = False
            output["error"] = "Invalid summary structure"
        else:
            summary_text = "\n".join(sentences)

    error = None if success else str(output.get("error") or "Generation failed")
    metadata["_generation"] = {
        "model": MODEL_NAME,
        "status": "success" if success else "failed",
        "elapsed": output.get("elapsed"),
        "timing": output.get("timing"),
        "error_message": error,
    }
    with connection.cursor() as cursor:
        cursor.execute(
            """UPDATE news SET summary_text = %s,
               summarized_at = CASE WHEN %s THEN clock_timestamp() ELSE NULL END,
               processing_status = %s, error_message = %s, raw_rss_entry = %s
               WHERE news_id = %s""",
            (summary_text, success, "success" if success else "failed",
             error, Jsonb(metadata), news_id),
        )
    print(f"Saved news {news_id}: {'success' if success else 'failed'}", flush=True)
    if error:
        print(f"Error: {error}", flush=True)
    return success


# Identify runs made by this archive-and-sample implementation.
SELECTION_MODE = "uniform_random_per_source_v1"


def sample_ids(candidate_ids, limit):
    """Sample without replacement using operating-system randomness."""
    unique_ids = sorted(set(candidate_ids))
    size = min(limit, len(unique_ids)) if limit else len(unique_ids)
    return random.SystemRandom().sample(unique_ids, size)


def save_settings(connection, run_id, settings):
    """Commit the selection and progress metadata independently of inference."""
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE runs SET generation_settings = %s WHERE run_id = %s",
            (Jsonb(settings), run_id),
        )


def archive_source(connection, preparation, source, run_id, target_day, allow_updated):
    """Inspect the entire feed and archive all valid entries published today."""
    started = time.monotonic()
    print(f"Archiving {source['country']} / {source['name']}...", flush=True)
    feed = preparation.fetch_feed(source["feed_url"])
    report = {
        "source_id": source["source_id"], "source": source["name"],
        "country": source["country"], "status": feed["status"],
        "entry_count": feed["entry_count"], "http_status": feed.get("http_status"),
        "warning": feed.get("bozo_warnings"), "error": feed.get("error_message"),
        "on_target_date": 0, "other_day": 0, "missing_date": 0,
        "invalid_url": 0, "inserted": 0, "already_present": 0,
    }
    if feed["status"] != "success":
        report["archive_seconds"] = round(time.monotonic() - started, 3)
        print(f"Feed failed: {report['error']}", flush=True)
        return report

    fetched_at = datetime.now(timezone.utc)
    seen = set()
    for entry in feed["entries"]:
        raw = make_raw_record(source, entry)
        url = raw["original_url"]
        try:
            parsed = urlparse(url) if isinstance(url, str) else None
        except ValueError:
            parsed = None
        if parsed is None or parsed.scheme not in ("http", "https") or not parsed.netloc:
            report["invalid_url"] += 1
            continue
        if url in seen:
            continue
        seen.add(url)

        # Reuse a previously resolved DW date, avoiding another metadata request.
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT published_at_raw, raw_rss_entry FROM news "
                "WHERE source_id = %s AND original_url = %s",
                (source["source_id"], url),
            )
            existing = cursor.fetchone()
        if not raw.get("published_at"):
            if existing and (existing[1] or {}).get("_publication_metadata", {}).get("value"):
                raw["published_at"] = existing[0]
                raw["_publication_metadata"] = existing[1]["_publication_metadata"]
            else:
                resolve_dw_publication(raw)
        eligible, reason = filter_source_day(raw, target_day, allow_updated)
        if not eligible:
            report[reason] += 1
            continue
        report["on_target_date"] += 1
        summary = preparation.strip_tags(raw.get("raw_rss_summary") or "")
        content = " ".join(
            preparation.strip_tags(item.get("value") or "")
            for item in (raw.get("raw_rss_content") or [])
            if isinstance(item, dict) and item.get("value")
        )
        with connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO news (source_id, run_id, original_title, original_url,
                   published_at, published_at_raw, fetched_at, rss_summary_text,
                   rss_content_text, raw_rss_entry, processing_status)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'skipped')
                   ON CONFLICT (source_id, original_url) DO NOTHING RETURNING news_id""",
                (source["source_id"], run_id, raw["original_title"] or "", url,
                 parse_date(raw["published_at"]), raw["published_at"], fetched_at,
                 summary, content, Jsonb(raw)),
            )
            created = cursor.fetchone()
        report["inserted" if created else "already_present"] += 1
    report["archive_seconds"] = round(time.monotonic() - started, 3)
    print(
        f"{source['name']}: {report['on_target_date']} today; "
        f"{report['inserted']} newly archived; {report['already_present']} already present; "
        f"{report['missing_date']} without a usable date; "
        f"archive time {report['archive_seconds']:.2f}s",
        flush=True,
    )
    return report


def select_archived_news(connection, sources, target_day, limit):
    """Draw independently from each source's unique archived records for today.

    Existing successful summaries remain eligible: processing history must not
    bias the draw. Resume uses the saved IDs instead of calling this function.
    """
    selected = []
    reports = []
    for source in sources:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT news_id FROM news WHERE source_id = %s "
                "AND raw_rss_entry->'_date_filter'->>'target_date' = %s "
                "ORDER BY news_id",
                (source["source_id"], target_day.isoformat()),
            )
            candidates = [row[0] for row in cursor.fetchall()]
        chosen = sample_ids(candidates, limit)
        selected.extend(chosen)
        reports.append({
            "source_id": source["source_id"], "source": source["name"],
            "country": source["country"], "candidate_count": len(candidates),
            "selected_news_ids": chosen,
        })
        print(f"Random sample {source['name']}: {len(chosen)} of {len(candidates)}", flush=True)
    return selected, reports


def main():
    """Archive first, persist a random sample, then summarize selected items."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--limit-per-country", "--sample-per-source", dest="sample_limit",
        type=int, default=5,
        help="Random sample size per source, not archive limit; default 5; 0 selects all",
    )
    parser.add_argument("--resume-run", type=int,
                        help="Retry a saved selection without fetching feeds or drawing again")
    parser.add_argument("--date", type=date.fromisoformat,
                        help="Publication date YYYY-MM-DD; default today in Europe/Berlin")
    parser.add_argument("--allow-updated", action="store_true",
                        help="Allow updated date only when published date is absent")
    parser.add_argument("--non-interactive", action="store_true",
                        help="Use libpq credentials such as PGPASSFILE; never prompt")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5432)
    parser.add_argument("--database", default="rss_news")
    parser.add_argument("--user", default="rss_app")
    args = parser.parse_args()
    if args.sample_limit < 0 or (args.resume_run is not None and args.resume_run <= 0):
        parser.error("The sample limit must be nonnegative and the run ID positive")
    if args.resume_run and (args.date or args.allow_updated):
        parser.error("A resumed run uses its saved date and date rules")
    if sys.version_info < (3, 12):
        print("Use Python 3.12 or newer in jupyter-env.", file=sys.stderr)
        return 1
    started = time.monotonic()
    target_day = args.date or datetime.now(DAY_TIMEZONE).date()
    try:
        preparation = load_script("rss_preparation", STAGE4_DIR / "prepare_news.py")
        summarization = load_script("rss_summarization", STAGE4_DIR / "summarize_news_test.py")
        kwargs = dict(host=args.host, port=args.port, dbname=args.database,
                      user=args.user, connect_timeout=10, autocommit=True)
        if not args.non_interactive:
            kwargs["password"] = os.environ.get("PGPASSWORD") or getpass("Password for rss_app: ")
        connection = psycopg.connect(**kwargs)
    except (OSError, ImportError, SyntaxError, psycopg.Error) as error:
        print(f"Startup failed: {error}", file=sys.stderr)
        return 1

    run_id = None
    active_news_id = None
    inserted = already_present = successful = reused = errors = 0
    selected_ids = []
    settings = {}
    fatal_error = None
    model_used = False
    exit_code = 0
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_try_advisory_lock(%s)", (LOCK_KEY,))
            if not cursor.fetchone()[0]:
                print("Another daily_news process is already running; exiting.", flush=True)
                return 0
            if args.resume_run:
                cursor.execute(
                    "SELECT model_name, generation_settings FROM runs "
                    "WHERE run_id = %s AND run_type = 'daily'", (args.resume_run,),
                )
                previous = cursor.fetchone()
                if not previous or previous[0] != MODEL_NAME:
                    raise ValueError("No resumable daily run for the fixed model")
                settings = previous[1]
                if settings.get("selection_mode") != SELECTION_MODE or "selected_news_ids" not in settings:
                    raise ValueError("This run has no saved random selection; start a new run")
                # Refuse to silently change prompts or generation parameters on retry.
                if (settings.get("system_prompt") != summarization.SYSTEM_PROMPT or
                        settings.get("user_prompt_template") != summarization.USER_PROMPT_TEMPLATE):
                    raise ValueError("Stage 4 prompts changed since this run; restore them before retrying")
                current_payload = summarization.prepare_generation_payload(MODEL_NAME, "en", {
                    "original_title": "", "text_basis": "rss_summary", "prepared_text": ""
                }, False)
                if settings.get("options") != current_payload["options"]:
                    raise ValueError("Generation options changed since this run; restore them before retrying")
                selected_ids = settings["selected_news_ids"]
                if not isinstance(selected_ids, list) or any(type(i) is not int or i <= 0 for i in selected_ids):
                    raise ValueError("Invalid saved selection")
                target_day = date.fromisoformat(settings["target_date"])
                run_id = args.resume_run
                cursor.execute(
                    "UPDATE runs SET status = 'running', finished_at = NULL, "
                    "error_message = NULL WHERE run_id = %s", (run_id,),
                )
                inserted = int(settings.get("outcome", {}).get("inserted", 0))
                already_present = int(settings.get("outcome", {}).get("already_present", 0))
                print(f"Resuming run {run_id}: using the saved {len(selected_ids)} selected IDs", flush=True)
            else:
                payload = summarization.prepare_generation_payload(MODEL_NAME, "en", {
                    "original_title": "", "text_basis": "rss_summary", "prepared_text": ""
                }, False)
                settings = {
                    "system_prompt": summarization.SYSTEM_PROMPT,
                    "user_prompt_template": summarization.USER_PROMPT_TEMPLATE,
                    "options": payload["options"], "think": False,
                    "translation_enabled": False, "selection_mode": SELECTION_MODE,
                    "sample_per_source": args.sample_limit,
                    "target_date": target_day.isoformat(), "date_timezone": "Europe/Berlin",
                    "allow_updated": args.allow_updated,
                    "dw_publication_date_origin": "article.datePublished",
                }
                cursor.execute(
                    """INSERT INTO runs (run_type, model_name, prompt_version, generation_settings)
                       VALUES ('daily', %s, %s, %s) RETURNING run_id""",
                    (MODEL_NAME, "sha256:" + hashlib.sha256(summarization.SYSTEM_PROMPT.encode()).hexdigest(),
                     Jsonb(settings)),
                )
                run_id = cursor.fetchone()[0]
                cursor.execute(
                    "SELECT source_id, name, country, feed_url FROM sources "
                    "WHERE is_active AND language = 'en' ORDER BY source_id"
                )
                sources = [dict(zip(("source_id", "name", "country", "feed_url"), row))
                           for row in cursor.fetchall()]
                if not sources:
                    raise ValueError("No active English-language sources are configured")

        print(f"Daily run {run_id}; fixed model: {MODEL_NAME}; publication date: {target_day}", flush=True)
        if not args.resume_run:
            archive_started = time.monotonic()
            reports = []
            # Finish archiving every source before selecting or generating anything.
            for source in sources:
                report = archive_source(connection, preparation, source, run_id,
                                        target_day, args.allow_updated)
                reports.append(report)
                inserted += report["inserted"]
                already_present += report["already_present"]
                errors += int(report["status"] != "success")
                settings["source_results"] = reports
                settings["outcome"] = {"inserted": inserted, "already_present": already_present}
                save_settings(connection, run_id, settings)
            settings["archive_seconds"] = round(time.monotonic() - archive_started, 3)
            selected_ids, settings["selection_by_source"] = select_archived_news(
                connection, sources, target_day, args.sample_limit
            )
            settings["selected_news_ids"] = selected_ids
            settings["selection_saved_at"] = datetime.now(timezone.utc).isoformat()
            # Save before any article extraction or model request; retries reuse these IDs.
            save_settings(connection, run_id, settings)
        else:
            errors += sum(int(r["status"] != "success") for r in settings.get("source_results", []))

        rows = []
        if selected_ids:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT news_id, raw_rss_entry, processing_status, summary_text "
                    "FROM news WHERE news_id = ANY(%s)", (selected_ids,),
                )
                by_id = {row[0]: row for row in cursor.fetchall()}
            if len(by_id) != len(selected_ids):
                raise ValueError("A selected news record is missing; do not delete data during a run")
            rows = [by_id[i] for i in selected_ids]
        needs_model = any(row[2] != "success" or not (row[3] or "").strip() for row in rows)
        if needs_model:
            tags = summarization.validate_and_fetch_models([MODEL_NAME])
            digest = tags[MODEL_NAME]
            if args.resume_run and settings.get("model_digest") not in (None, digest):
                raise ValueError("The model digest changed; restore the original model before retrying")
            settings["model_digest"] = digest
            save_settings(connection, run_id, settings)

        summary_started = time.monotonic()
        for index, (news_id, raw, status, summary_text) in enumerate(rows, 1):
            if status == "success" and (summary_text or "").strip():
                reused += 1
                successful += 1
                print(f"Selected {index}/{len(rows)}: reusing saved summary for news {news_id}", flush=True)
                continue
            active_news_id = news_id
            model_used = True
            print(f"Selected {index}/{len(rows)}: {raw['country']} / {raw['source']}", flush=True)
            ok = process_news(connection, preparation, summarization, news_id, run_id, raw)
            successful += int(ok)
            errors += int(not ok)
            active_news_id = None
        settings["summarization_seconds"] = round(time.monotonic() - summary_started, 3)
        if errors:
            exit_code = 1
    except (Exception, KeyboardInterrupt, SystemExit) as error:
        fatal_error = str(error) or type(error).__name__
        errors += 1
        exit_code = 1
        print(f"Run stopped: {fatal_error}", file=sys.stderr)
    finally:
        if run_id is not None:
            try:
                with connection.cursor() as cursor:
                    if active_news_id is not None:
                        cursor.execute(
                            "UPDATE news SET processing_status = 'failed', error_message = %s "
                            "WHERE news_id = %s", (fatal_error or "Processing interrupted", active_news_id),
                        )
                    settings["execution_seconds"] = round(time.monotonic() - started, 3)
                    settings["outcome"] = {
                        "inserted": inserted, "already_present": already_present,
                        "selected": len(selected_ids), "successful_summaries": successful,
                        "reused_summaries": reused,
                    }
                    status = "success" if not errors else ("partial" if successful or inserted else "failed")
                    cursor.execute(
                        """UPDATE runs SET finished_at = clock_timestamp(), status = %s,
                           new_count = %s, error_count = %s, error_message = %s,
                           generation_settings = %s WHERE run_id = %s""",
                        (status, inserted, errors, fatal_error, Jsonb(settings), run_id),
                    )
            except psycopg.Error as error:
                print(f"Could not finalize the run record: {error}", file=sys.stderr)
                exit_code = 1
        if model_used:
            try:
                summarization.unload_model(MODEL_NAME)
            except Exception as error:
                print(f"Could not unload model: {error}", file=sys.stderr)
        connection.close()

    print(f"Run ID: {run_id}; new: {inserted}; selected: {len(selected_ids)}; "
          f"already present: {already_present}; successful summaries: {successful}; errors: {errors}", flush=True)
    print(f"Total runtime: {time.monotonic() - started:.2f} seconds", flush=True)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
