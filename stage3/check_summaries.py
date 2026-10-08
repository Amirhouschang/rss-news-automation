#!/usr/bin/env python3
"""Check saved news summaries offline and create a human review report.

Uses only the Python standard library. It never edits the input, contacts an
API, rewrites a summary, or judges whether the source's claims are true.
"""

import argparse
import hashlib
import html
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path


# These scripts are unexpected in English/German output, but a proper name
# may legitimately retain them. Detection therefore produces a review flag.
SCRIPT_PATTERNS = {
    "Chinese characters": re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]+"),
    "Cyrillic characters": re.compile(r"[\u0400-\u052f]+"),
    "Arabic/Persian characters": re.compile(r"[\u0600-\u06ff\ufb50-\ufdff\ufe70-\ufeff]+"),
}
NUMBER_PATTERN = re.compile(r"(?<!\d)\d+(?:[.,]\d+)*(?!\d)")
SCALE_PATTERN = re.compile(
    r"^\s*(billion(?:s)?|milliarden?|milliard|млрд|میلیارد|亿|億|"
    r"million(?:s)?|millionen?|млн|میلیون|thousand(?:s)?|tausend|тыс\.?|هزار|万|萬)"
    r"(?![a-z])", re.IGNORECASE
)
SCALES = {
    "billion": 10**9, "billions": 10**9, "milliarde": 10**9,
    "milliarden": 10**9, "milliard": 10**9, "млрд": 10**9,
    "میلیارد": 10**9, "亿": 10**8, "億": 10**8,
    "million": 10**6, "millions": 10**6, "millionen": 10**6,
    "млн": 10**6, "میلیون": 10**6, "thousand": 1000,
    "thousands": 1000, "tausend": 1000, "тыс": 1000,
    "тыс.": 1000, "هزار": 1000, "万": 10000, "萬": 10000,
}


def normalize_digits(text):
    """Convert Persian/Arabic decimal digits without changing other text."""
    return "".join(str(unicodedata.decimal(c)) if c.isdecimal() else c for c in text)


def numeric_values(token, language=None):
    """Interpret separators conservatively; allow ambiguous source notation."""
    candidates = set()
    if "." in token and "," in token:
        # The rightmost separator is treated as the decimal separator.
        decimal_separator = "." if token.rfind(".") > token.rfind(",") else ","
        other = "," if decimal_separator == "." else "."
        candidates.add(token.replace(other, "").replace(decimal_separator, "."))
    elif "," in token or "." in token:
        separator = "," if "," in token else "."
        parts = token.split(separator)
        grouped = all(len(part) == 3 for part in parts[1:])
        if language == "en" and separator == "," and grouped:
            candidates.add("".join(parts))
        elif language == "de" and separator == "." and grouped:
            candidates.add("".join(parts))
        elif len(parts) == 2:
            candidates.add(token.replace(separator, "."))
            if language is None and grouped:
                candidates.add("".join(parts))
        elif grouped:
            candidates.add("".join(parts))
    else:
        candidates.add(token)
    values = set()
    for candidate in candidates:
        try:
            values.add(Decimal(candidate))
        except InvalidOperation:
            pass
    return values


def extract_numbers(text, language=None):
    """Collect digit-based quantities, including common magnitude units."""
    text = normalize_digits(text)
    items = []
    for match in NUMBER_PATTERN.finditer(text):
        suffix = SCALE_PATTERN.match(text[match.end():])
        scale = SCALES[suffix.group(1).lower()] if suffix else 1
        end = match.end() + suffix.end() if suffix else match.end()
        items.append({
            "text": text[match.start():end],
            "values": {value * scale for value in numeric_values(match.group(), language)},
        })
    # Chinese tenths expressions occur in percentages, e.g. 四成 = 40%.
    chinese_digits = {c: n for n, c in enumerate("零一二三四五六七八九")}
    for match in re.finditer(r"([一二三四五六七八九])成", text):
        items.append({"text": match.group(), "values": {Decimal(chinese_digits[match.group(1)] * 10)}})
    return items


def add_issue(issues, code, message):
    issues.append({"code": code, "message": message})


def check_attempt(attempt, index):
    """Flag observable anomalies; do not claim semantic verification."""
    issues = []
    language = attempt.get("target_language")
    result = attempt.get("result")
    title = ""
    sentences = []
    if attempt.get("status") != "success":
        add_issue(issues, "generation_failed", "The original generation was not successful.")
    if language not in {"en", "de"}:
        add_issue(issues, "unsupported_language", "Only English and German output checks are supported.")
    if not isinstance(result, dict):
        add_issue(issues, "invalid_result", "The result is not a JSON object.")
    else:
        if set(result) != {"translated_title", "summary_sentences"}:
            add_issue(issues, "invalid_fields", "Expected exactly translated_title and summary_sentences.")
        title = result.get("translated_title", "")
        sentences = result.get("summary_sentences", [])
        if not isinstance(title, str) or not title.strip():
            add_issue(issues, "invalid_title", "The translated title is missing or empty.")
            title = title if isinstance(title, str) else ""
        if not isinstance(sentences, list) or not 1 <= len(sentences) <= 2:
            add_issue(issues, "invalid_summary", "Expected a list containing one or two nonempty strings.")
        if not isinstance(sentences, list):
            sentences = []
        if any(not isinstance(s, str) or not s.strip() for s in sentences):
            add_issue(issues, "invalid_sentence", "A summary element is not a nonempty string.")
        sentences = [s for s in sentences if isinstance(s, str)]

    output = "\n".join([title] + sentences)
    original_title = attempt.get("original_title")
    original_text = attempt.get("prepared_text")
    if not isinstance(original_title, str) or not isinstance(original_text, str) or not original_text.strip():
        add_issue(issues, "missing_source", "Source title/text is missing; comparison is incomplete.")
    original_title = original_title if isinstance(original_title, str) else ""
    original_text = original_text if isinstance(original_text, str) else ""

    if language in {"en", "de"}:
        for script, pattern in SCRIPT_PATTERNS.items():
            fragments = sorted(set(pattern.findall(output)))
            if fragments:
                add_issue(issues, "unexpected_script", f"{script} remain in the output: {', '.join(fragments)}. Check whether they are untranslated words or legitimate names.")

    # Values absent from the input are warnings, not proof of an error. Written
    # numbers, dates spelled as month names, rounding, fractions, and less common
    # units are not fully handled. Matching numbers do not prove matching facts.
    if original_text and language in {"en", "de"}:
        source_numbers = extract_numbers(original_title + "\n" + original_text)
        source_values = set().union(*(n["values"] for n in source_numbers)) if source_numbers else set()
        unmatched = sorted({n["text"] for n in extract_numbers(output, language)
                            if n["values"] and n["values"].isdisjoint(source_values)})
        if unmatched:
            add_issue(issues, "number_not_matched", "These output quantities could not be matched automatically to source quantities: " + ", ".join(unmatched) + ". Verify units, written numbers, dates, and rounding manually.")

    return {
        "input_index": index,
        "attempt_number": attempt.get("attempt_number", index + 1),
        "model": attempt.get("model", "Unknown"),
        "country": attempt.get("country", "Unknown"),
        "target_language": language,
        "text_basis": attempt.get("text_basis", "Unknown"),
        "original_status": attempt.get("status"),
        "qc_status": "needs_review" if issues else "not_flagged",
        "issues": issues,
        "original_title": original_title,
        "original_url": attempt.get("original_url", ""),
        "prepared_text": original_text,
        "translated_title": title,
        "summary_sentences": sentences,
        "sampled_for_review": False,
    }


def select_sample(records, per_country, seed):
    """Select reproducible unflagged samples per country, model, and language."""
    groups = defaultdict(list)
    for record in records:
        if record["qc_status"] == "not_flagged":
            groups[(str(record["country"]), str(record["model"]), str(record["target_language"]))].append(record)
    for candidates in groups.values():
        def rank(record):
            key = f"{seed}|{record['model']}|{record['target_language']}|{record['original_url']}|{record['input_index']}"
            return hashlib.sha256(key.encode("utf-8")).hexdigest()
        for record in sorted(candidates, key=rank)[:per_country]:
            record["sampled_for_review"] = True


def cell(text):
    """Escape source content so it cannot break the side-by-side HTML table."""
    return html.escape(str(text)).replace("\n", "<br>")


def make_report(data, include_all):
    """Put flagged results and unflagged samples beside their original input."""
    lines = [
        "# News Summary Quality Review", "",
        f"Checked: {data['counts']['checked']}; needs review: {data['counts']['needs_review']}; not flagged: {data['counts']['not_flagged']}.", "",
        "**Not flagged does not mean verified or correct.** This is an offline heuristic check, not a language detector, semantic fact checker, or political/credibility assessment.", "",
        "Numeric warnings may be false alarms. Numbers written as words, unusual units, dates, and rounding need manual review. Matching values can still refer to the wrong event or period.", "",
        "The sentence check validates one or two list elements; it does not reliably count grammatical sentences within an element.", "",
        "## Manual review checklist", "",
        "- Compare the output only with the supplied source title and prepared text.",
        "- Check names, organizations, numbers, units, dates, and comparison periods.",
        "- Preserve the source's meaning, certainty, tone, and existing attribution.",
        "- Check for added or strengthened statements, such as 'destroyed' instead of 'hit'.",
        "- Do not replace the source's perspective with your own or add outside facts.",
        "- RSS-summary input provides less context than an article; retain that limitation.", "",
        "## Results for review", "",
    ]
    for record in data["records"]:
        if not include_all and record["qc_status"] != "needs_review" and not record["sampled_for_review"]:
            continue
        reason = "Automatic flag" if record["qc_status"] == "needs_review" else "Unflagged sample" if record["sampled_for_review"] else "Unflagged result"
        lines.extend([
            f"### Attempt {record['attempt_number']}: {cell(record['country'])} / {cell(record['target_language'])}", "",
            f"Model: {cell(record['model'])}; basis: {cell(record['text_basis'])}; status: `{record['qc_status']}`; selection: {reason}.", "",
        ])
        for issue in record["issues"]:
            lines.append(f"- **{issue['code']}**: {cell(issue['message'])}")
        lines.extend([
            "", "<table>", "<thead><tr><th>Original input</th><th>Generated output</th></tr></thead>",
            "<tbody><tr>",
            f"<td><strong>{cell(record['original_title'])}</strong><br><br>{cell(record['prepared_text'])}</td>",
            f"<td><strong>{cell(record['translated_title'])}</strong><br><br>{cell(chr(10).join(record['summary_sentences']))}</td>",
            "</tr></tbody></table>", "",
            f"Source URL: {cell(record['original_url'])}", "",
            "Manual decision: [ ] acceptable [ ] correction needed [ ] uncertain", "",
            "Reviewer notes:", "",
        ])
    return "\n".join(lines)


def nonnegative_int(value):
    value = int(value)
    if value < 0:
        raise argparse.ArgumentTypeError("Must be zero or greater.")
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Saved summaries JSON file.")
    parser.add_argument("--language", choices=["en", "de", "all"], default="en", help="Output language to check (default: en).")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent / "data" / "quality")
    parser.add_argument("--sample-per-country", type=nonnegative_int, default=1, help="Unflagged samples per country/model/language (default: 1).")
    parser.add_argument("--seed", type=int, default=42, help="Seed for reproducible sample selection.")
    parser.add_argument("--report-all", action="store_true", help="Include every checked result in the Markdown report.")
    args = parser.parse_args()

    try:
        with args.input.open(encoding="utf-8") as handle:
            source = json.load(handle)
        if not isinstance(source, dict) or not isinstance(source.get("attempts"), list):
            raise ValueError("Input must be an object containing an attempts list.")
        if any(not isinstance(a, dict) for a in source["attempts"]):
            raise ValueError("Every attempt must be a JSON object.")
        # An unknown/missing language is retained for review, rather than hidden.
        records = [check_attempt(a, i) for i, a in enumerate(source["attempts"])
                   if args.language == "all" or a.get("target_language") == args.language
                   or a.get("target_language") not in {"en", "de"}]
        if not records:
            raise ValueError("No attempts matched the requested language.")
        select_sample(records, args.sample_per_country, args.seed)
        counts = Counter(record["qc_status"] for record in records)
        now = datetime.now(timezone.utc)
        data = {
            "checked_at": now.isoformat(),
            "input_path": str(args.input.resolve()),
            "language_filter": args.language,
            "sample_seed": args.seed,
            "sample_per_country": args.sample_per_country,
            "limitations": ["Heuristic checks cannot establish semantic accuracy or verify source truth.", "Numeric matching can produce false positives and false negatives.", "Unflagged output is not automatically approved."],
            "counts": {"checked": len(records), "needs_review": counts["needs_review"], "not_flagged": counts["not_flagged"], "unflagged_samples": sum(r["sampled_for_review"] for r in records)},
            "records": records,
        }
        args.output_dir.mkdir(parents=True, exist_ok=True)
        stamp = now.strftime("%Y%m%d_%H%M%S_%fZ")
        json_path = args.output_dir / f"quality_{stamp}.json"
        report_path = args.output_dir / f"quality_report_{stamp}.md"
        # Exclusive creation prevents accidental overwrite of earlier reports.
        with json_path.open("x", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        with report_path.open("x", encoding="utf-8") as handle:
            handle.write(make_report(data, args.report_all))
        print(f"Checked: {len(records)}")
        print(f"Needs review: {counts['needs_review']}")
        print(f"Not flagged: {counts['not_flagged']} (not automatically verified)")
        print(f"Additional unflagged samples: {data['counts']['unflagged_samples']}")
        print(f"Quality results saved to: {json_path.resolve()}")
        print(f"Review report saved to: {report_path.resolve()}")
        return 0
    except (OSError, ValueError, TypeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
