"""
RSS News Preparation Script for Stage 2

This script fetches fresh RSS feeds from multiple news sources and prepares up to five news items per country.
It extracts article text using trafilatura, handles special cases like IRNA interstitial pages, and provides
cleaned text for later translation and summarization without calling any AI models.

Input:
- RSS feed URLs for Germany (Tagesschau), Iran (IRNA), China (Chinanews), Russia (TASS), Ukraine (Ukrinform)

Output:
- Raw snapshot of fetched entries saved to: stage2/data/raw/rss_<timestamp>.json
- Prepared news items saved to: stage2/data/prepared/prepared_<timestamp>.json

Each output file contains all required metadata for later processing.
"""

import argparse
import json
import os
import sys
import time
import urllib.parse
from datetime import datetime, timezone
from html.parser import HTMLParser

import feedparser
import requests
import trafilatura


# Named constants for timeout values
CONNECT_TIMEOUT = 3.05  # Connection timeout in seconds (time to establish TCP connection)
READ_TIMEOUT = 20.0     # Read timeout in seconds (time to receive response data)


class MLStripper(HTMLParser):
    """
    A class to strip HTML tags from text using Python's HTMLParser.

    This helps convert RSS HTML content into readable plain text.
    """
    def __init__(self):
        super().__init__()
        self.reset()
        self.fed = []
        self.in_script_or_style = False

    def handle_starttag(self, tag, attrs):
        if tag in ['script', 'style']:
            self.in_script_or_style = True
        elif tag in ['p', 'div', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            self.fed.append('\n')

    def handle_endtag(self, tag):
        if tag in ['script', 'style']:
            self.in_script_or_style = False
        elif tag in ['p', 'div', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            self.fed.append('\n')

    def handle_data(self, d):
        if not self.in_script_or_style:
            self.fed.append(d)

    def get_data(self):
        return ''.join(self.fed)


def strip_tags(html):
    """
    Remove HTML tags from input text.

    Args:
        html (str): Input text containing HTML tags

    Returns:
        str: Text with HTML tags removed
    """
    s = MLStripper()
    s.feed(html)
    return s.get_data()


def fetch_feed(feed_url):
    """
    Fetch an RSS or Atom feed from a given URL.

    Args:
        feed_url (str): The URL of the RSS/Atom feed

    Returns:
        dict: A dictionary with status, HTTP status, entry count, entries list,
              and bozo warnings. If fetching fails, it includes error information.
    """
    # Measure download time
    start_download = time.perf_counter()

    try:
        # Use tuple timeout (connect_timeout, read_timeout)
        response = requests.get(feed_url, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT))
        response.raise_for_status()
        download_time = time.perf_counter() - start_download

        # Measure parsing time
        start_parse = time.perf_counter()
        feed = feedparser.parse(response.content)
        parse_time = time.perf_counter() - start_parse

        if not feed.version:
            raise ValueError("No RSS/Atom version found")

        # Handle optional bozo_exception field properly
        bozo_exception = feed.get("bozo_exception")
        warning_text = str(bozo_exception) if bozo_exception else None

        # Print any warnings while preserving usable entries
        if warning_text:
            print(f"Warning for {feed_url}: {warning_text}")

        return {
            'status': 'success',
            'http_status': response.status_code,
            'entry_count': len(feed.entries),
            'entries': feed.entries,
            'bozo_warnings': warning_text,
            'error_message': None,
            'download_time': download_time,
            'parse_time': parse_time
        }
    except requests.exceptions.HTTPError as e:
        # Explicit check: only access .response if it exists
        http_status = e.response.status_code if e.response is not None else None
        download_time = time.perf_counter() - start_download
        return {
            'status': 'failed',
            'http_status': http_status,
            'error_message': str(e),
            'entry_count': 0,
            'entries': [],
            'bozo_warnings': None,
            'download_time': download_time,
            'parse_time': None
        }
    except requests.exceptions.RequestException as e:
        # Handle other request errors
        download_time = time.perf_counter() - start_download
        return {
            'status': 'failed',
            'http_status': getattr(e.response, 'status_code', None) if e.response is not None else None,
            'error_message': str(e),
            'entry_count': 0,
            'entries': [],
            'bozo_warnings': None,
            'download_time': download_time,
            'parse_time': None
        }
    except Exception as e:
        download_time = time.perf_counter() - start_download
        return {
            'status': 'failed',
            'http_status': None,
            'error_message': str(e),
            'entry_count': 0,
            'entries': [],
            'bozo_warnings': None,
            'download_time': download_time,
            'parse_time': None
        }


def fetch_article(url):
    """
    Fetch and extract text from a news article URL.

    Args:
        url (str): The URL of the article to fetch

    Returns:
        dict: A dictionary with status, final URL, HTTP status, error message,
              article text, and rejected text. If fetching or extracting fails,
              it includes error information.

    Important details:
    - Explicitly checks if exception.response is not None to preserve real HTTP status
    - Detects IRNA interstitial page by checking if extracted text is at most 300 chars
      and contains "transferring to the website" (case-insensitive)
    """
    # Measure download time
    start_download = time.perf_counter()

    try:
        # Use tuple timeout (connect_timeout, read_timeout)
        response = requests.get(url, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT))
        response.raise_for_status()
        download_time = time.perf_counter() - start_download

        # Measure extraction time
        start_extract = time.perf_counter()
        final_url = response.url
        raw_text = trafilatura.extract(response.content, url=final_url, include_comments=False)
        extract_time = time.perf_counter() - start_extract

        if not raw_text or len(raw_text.strip()) == 0:
            return {
                'status': 'failed',
                'final_url': final_url,
                'http_status': response.status_code,
                'error_message': 'No text extracted',
                'article_text': None,
                'rejected_text': None,
                'download_time': download_time,
                'extract_time': extract_time
            }
        # Detect IRNA interstitial
        if len(raw_text) <= 300 and "transferring to the website" in raw_text.lower():
            return {
                'status': 'rejected',
                'final_url': final_url,
                'http_status': response.status_code,
                'error_message': 'IRNA interstitial page',
                'article_text': None,
                'rejected_text': raw_text,
                'download_time': download_time,
                'extract_time': extract_time
            }
        return {
            'status': 'success',
            'final_url': final_url,
            'http_status': response.status_code,
            'error_message': None,
            'article_text': raw_text,
            'rejected_text': None,
            'download_time': download_time,
            'extract_time': extract_time
        }
    except requests.exceptions.HTTPError as e:
        # Explicit check: only access .response if it exists
        http_status = e.response.status_code if e.response is not None else None
        download_time = time.perf_counter() - start_download
        return {
            'status': 'failed',
            'final_url': getattr(e.response, 'url', url),
            'http_status': http_status,
            'error_message': str(e),
            'article_text': None,
            'rejected_text': None,
            'download_time': download_time,
            'extract_time': None
        }
    except requests.exceptions.RequestException as e:
        # Handle other request errors
        download_time = time.perf_counter() - start_download
        return {
            'status': 'failed',
            'final_url': url,
            'http_status': getattr(e.response, 'status_code', None) if e.response is not None else None,
            'error_message': str(e),
            'article_text': None,
            'rejected_text': None,
            'download_time': download_time,
            'extract_time': None
        }
    except Exception as e:
        download_time = time.perf_counter() - start_download
        return {
            'status': 'failed',
            'final_url': url,
            'http_status': None,
            'error_message': str(e),
            'article_text': None,
            'rejected_text': None,
            'download_time': download_time,
            'extract_time': None
        }


def is_tagesschau_video_or_livestream(url):
    """
    Check if a Tagesschau URL refers to a video or livestream page.

    Args:
        url (str): The URL to check

    Returns:
        bool: True if the URL is a video or livestream page
    """
    try:
        parsed = urllib.parse.urlparse(url)
        path = parsed.path

        # Check for /video/ paths
        if path.startswith('/video/'):
            return True

        # Check for paths ending with video-*
        path_components = [comp for comp in path.split('/') if comp]
        if path_components and path_components[-1].startswith('video-'):
            return True

        # Check for /multimedia/livestreams/ paths
        if path.startswith('/multimedia/livestreams/'):
            return True

        return False
    except Exception:
        return False


def clean_chinanews_footer(text, url):
    """
    Remove the standard footer from Chinanews articles.

    Args:
        text (str): The raw extracted article text
        url (str): The original URL of the article

    Returns:
        tuple: (cleaned_text, changed) where changed indicates if cleanup was applied
    """
    if not text:
        return text, False

    # Parse the URL to check hostname
    try:
        parsed_url = urllib.parse.urlparse(url)
        hostname = parsed_url.hostname
        if not hostname or not (hostname == "chinanews.com.cn" or hostname.endswith(".chinanews.com.cn")):
            return text, False  # Only apply to chinanews.com.cn domains
    except Exception:
        return text, False

    lines = text.strip().split('\n')

    # Look for category heading ending in 新闻精选： or 新闻精选:
    footer_line_index = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Check for any category ending with "新闻精选：" or "新闻精选:"
        if stripped.endswith("新闻精选：") or stripped.endswith("新闻精选:"):
            # Verify the next non-empty line is a timestamp
            j = i + 1
            while j < len(lines):
                next_line = lines[j].strip()
                if next_line:
                    # Timestamp format: - 2026年10月07日 18:26:14
                    if next_line.startswith('- ') and '年' in next_line and '月' in next_line and '日' in next_line:
                        footer_line_index = i
                        break
                    else:
                        break
                j += 1
            if footer_line_index is not None:
                break

    if footer_line_index is not None:
        # Check if immediately preceding non-empty line is exactly "相关新闻"
        prev_nonempty_index = None
        for k in range(footer_line_index - 1, -1, -1):
            if lines[k].strip():
                prev_nonempty_index = k
                break

        # Remove the footer and everything after it
        cleaned_lines = lines[:footer_line_index]

        # If previous non-empty line is exactly "相关新闻", remove that too
        if prev_nonempty_index is not None and lines[prev_nonempty_index].strip() == "相关新闻":
            cleaned_lines = lines[:prev_nonempty_index]

        cleaned_text = '\n'.join(cleaned_lines).strip()
        return cleaned_text, True

    return text, False


def process_country(country, source, feed_url, limit_per_country):
    """
    Process all entries from a single news source (country).

    Args:
        country (str): The country name
        source (source): The news source name
        feed_url (str): The RSS feed URL for this source
        limit_per_country (int): Maximum number of items to select per country

    Returns:
        tuple: (results_list, raw_entries_list, source_status_dict) with processed items,
               all fetched entries, and source status record.
    """
    # Measure total processing time for the country
    start_total = time.perf_counter()

    # Step 1: Fetch the RSS feed exactly once
    feed_data = fetch_feed(feed_url)

    # Step 2: Prepare source status record for saving
    source_status = {
        'country': country,
        'source': source,
        'feed_url': feed_url,
        'fetch_status': feed_data['status'],
        'entry_count': feed_data['entry_count'],
        'selected_count': 0,
        'http_status': feed_data['http_status'],
        'error_message': feed_data['error_message'],
        'warning_text': feed_data['bozo_warnings'],
        'download_time': feed_data['download_time'],
        'parse_time': feed_data['parse_time']
    }

    if feed_data['status'] == 'failed':
        print(f"Failed to fetch {source}: {feed_data['error_message']}")
        source_status['total_processing_time'] = time.perf_counter() - start_total
        return [], [], source_status

    # Step 3: Build raw_entries from ALL original feed entries before any filtering
    raw_entries = []
    for entry in feed_data['entries']:
        url = getattr(entry, 'link', None)
        # Append one raw record unconditionally for each feed entry
        raw_entry = {
            'country': country,
            'source': source,
            'feed_url': feed_url,
            'original_title': getattr(entry, 'title', ''),
            'original_url': url,  # Keep original URL unchanged
            'published_at': getattr(entry, 'published', None),
            'updated_at': getattr(entry, 'updated', None),
            'raw_rss_summary': getattr(entry, 'summary', ''),
            'raw_rss_content': getattr(entry, 'content', [])
        }
        raw_entries.append(raw_entry)

    # Step 4: Filter and validate URLs before deduplication
    valid_entries = []
    for entry in feed_data['entries']:
        url = getattr(entry, 'link', None)
        if not url:
            continue
        try:
            parsed = urllib.parse.urlparse(url)
            if parsed.scheme in ['http', 'https'] and parsed.netloc:
                valid_entries.append(entry)
        except Exception:
            continue

    # Step 5: Apply exclusions for Tagesschau video/livestream entries
    excluded_count = 0
    if source == "Tagesschau":
        filtered_valid_entries = []
        for entry in valid_entries:
            url = getattr(entry, 'link', None)
            if url and is_tagesschau_video_or_livestream(url):
                excluded_count += 1
                continue
            filtered_valid_entries.append(entry)
        valid_entries = filtered_valid_entries

    # Step 6: Deduplicate URLs using full URLs (preserving query parameters)
    seen_urls = set()
    unique_entries = []
    for entry in valid_entries:
        url = getattr(entry, 'link', None)
        if not url:
            continue
        # Also check for query parameters
        full_url = url
        if full_url not in seen_urls:
            seen_urls.add(full_url)
            unique_entries.append(entry)

    # Step 7: Select up to limit_per_country distinct entries in feed order
    selected_entries = unique_entries[:limit_per_country]

    # Update source status with number of excluded entries
    source_status['excluded_count'] = excluded_count
    source_status['selected_count'] = len(selected_entries)

    # Print exclusion info
    if excluded_count > 0:
        print(f"Excluded {excluded_count} media entries from {country}/{source}")

    results = []

    # Step 8: Process each selected entry to get prepared result
    for idx, entry in enumerate(selected_entries):
        original_url = getattr(entry, 'link', None)
        if not original_url or not (original_url.startswith('http://') or original_url.startswith('https://')):
            continue

        # Show progress before fetching article
        print(f"Fetching {country}/{source} - Item {idx+1}/{len(selected_entries)}: {original_url}", flush=True)

        # Fetch article text for this entry
        article_result = fetch_article(original_url)

        # Show progress after processing
        final_url = article_result['final_url']
        http_status = article_result['http_status']
        article_text = article_result['article_text']
        rejected_text = article_result['rejected_text']
        article_status = article_result['status']
        download_time = article_result['download_time']
        extract_time = article_result['extract_time']

        # Unconditionally read RSS summary and content values for this entry
        rss_summary = getattr(entry, 'summary', '')
        rss_content_values = getattr(entry, 'content', [])

        # Clean RSS content for this specific entry
        cleaned_summary = strip_tags(rss_summary) if rss_summary else ''
        cleaned_content_list = [strip_tags(content.get('value', '')) for content in rss_content_values if content.get('value')]
        cleaned_content = ' '.join(cleaned_content_list) if cleaned_content_list else ''

        # Choose the best text for later processing (priority order)
        prepared_text = None
        text_basis = 'unavailable'
        article_cleanup_applied = False

        # Check if this is a Chinanews article that needs footer cleanup
        if article_status == 'success' and article_text and article_text.strip():
            # Apply cleanup only to Chinanews articles
            cleaned_article_text, cleanup_applied = clean_chinanews_footer(article_text, original_url)
            article_cleanup_applied = cleanup_applied
            prepared_text = cleaned_article_text
            # Store the cleaned text in article_text and update character count
            article_text = cleaned_article_text
            text_basis = 'article'
        elif article_status == 'rejected':
            # For IRNA, show explicit labels
            print(f"Article {original_url} was rejected (interstitial page)", flush=True)
            # Fallback to RSS content or summary
            if cleaned_content.strip():
                prepared_text = cleaned_content
                text_basis = 'rss_content'
            elif cleaned_summary.strip():
                prepared_text = cleaned_summary
                text_basis = 'rss_summary'
        else:
            # Get RSS content for fallback
            if cleaned_content.strip():
                prepared_text = cleaned_content
                text_basis = 'rss_content'
            elif cleaned_summary.strip():
                prepared_text = cleaned_summary
                text_basis = 'rss_summary'

        # Build final item dictionary with all metadata
        item = {
            'country': country,
            'source': source,
            'feed_url': feed_url,
            'original_title': getattr(entry, 'title', ''),
            'original_url': original_url,
            'published_at': getattr(entry, 'published', None),
            'updated_at': getattr(entry, 'updated', None),
            'final_url': final_url,
            'http_status': http_status,
            'article_status': article_status,
            'error_message': article_result['error_message'],
            'article_text': article_text,
            'article_text_original': article_result['article_text'],
            'article_cleanup_applied': article_cleanup_applied,
            'rejected_text': rejected_text,
            'rss_summary_text': cleaned_summary,
            'rss_content_text': cleaned_content,
            'prepared_text': prepared_text,
            'text_basis': text_basis,
            'download_time': download_time,
            'extract_time': extract_time,
            'prepared_text_char_count': len(prepared_text) if prepared_text else 0
        }

        results.append(item)

        # Print final result after processing
        print("Processed", country, source, "item", idx + 1, "status:", article_status, "basis:", text_basis, flush=True)

    # Calculate total processing time for this country
    source_status['total_processing_time'] = time.perf_counter() - start_total

    return results, raw_entries, source_status


def main():
    """
    Main function to run the RSS news preparation script.

    Parses command-line arguments, fetches feeds from all sources, processes
    articles, and saves outputs to JSON files.

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    # Measure total script runtime
    start_total = time.perf_counter()

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Fetch and prepare news items from RSS feeds.")
    parser.add_argument('--limit-per-country', type=int, default=5, help='Number of articles per country (default: 5)')
    args = parser.parse_args()

    if args.limit_per_country < 1:
        print("Error: --limit-per-country must be at least 1")
        sys.exit(1)

    # Set up output paths based on script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")  # Include microseconds
    raw_output_path = os.path.join(script_dir, 'data', 'raw', f'rss_{timestamp}.json')
    prepared_output_path = os.path.join(script_dir, 'data', 'prepared', f'prepared_{timestamp}.json')

    # Create output directories
    os.makedirs(os.path.dirname(raw_output_path), exist_ok=True)
    os.makedirs(os.path.dirname(prepared_output_path), exist_ok=True)

    # Define news sources to fetch
    sources = [
        {"country": "Germany", "source": "Tagesschau", "url": "https://www.tagesschau.de/index~rss2.xml"},
        {"country": "Iran", "source": "IRNA", "url": "https://www.irna.ir/rss"},
        {"country": "China", "source": "Chinanews", "url": "https://www.chinanews.com.cn/rss/scroll-news.xml"},
        {"country": "Russia", "source": "TASS", "url": "https://tass.ru/rss/v2.xml"},
        {"country": "Ukraine", "source": "Ukrinform", "url": "https://www.ukrinform.ua/rss/block-lastnews"}
    ]

    # Process all sources
    all_results = []
    all_raw_entries = []
    source_status_records = []

    for src in sources:
        country = src['country']
        source = src['source']
        feed_url = src['url']

        print(f"Processing {country} / {source}...")
        results, raw_entries, source_status = process_country(country, source, feed_url, args.limit_per_country)
        all_results.extend(results)
        all_raw_entries.extend(raw_entries)
        source_status_records.append(source_status)

    # Save raw snapshot to file
    try:
        raw_output = {
            "fetched_at": timestamp,
            "sources": source_status_records,
            "entries": all_raw_entries
        }
        with open(raw_output_path, 'w', encoding='utf-8') as f:
            json.dump(raw_output, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Failed to save raw snapshot: {e}")
        sys.exit(1)

    # Save processed results to file
    try:
        prepared_output = {
            "prepared_at": timestamp,
            "raw_input_file": os.path.basename(raw_output_path),
            "sources": source_status_records,
            "results": all_results
        }
        with open(prepared_output_path, 'w', encoding='utf-8') as f:
            json.dump(prepared_output, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Failed to save prepared results: {e}")
        sys.exit(1)

    # Print summary statistics
    selected_count = len(all_results)
    article_based = sum(1 for r in all_results if r['text_basis'] == 'article')
    rss_content_based = sum(1 for r in all_results if r['text_basis'] == 'rss_content')
    rss_summary_based = sum(1 for r in all_results if r['text_basis'] == 'rss_summary')
    unavailable = sum(1 for r in all_results if r['text_basis'] == 'unavailable')

    print("\n=== Summary ===")
    print(f"Selected items: {selected_count}")
    print(f"Article-based items: {article_based}")
    print(f"RSS-content based items: {rss_content_based}")
    print(f"RSS-summary based items: {rss_summary_based}")
    print(f"Unavailable items: {unavailable}")

    # Print preview of each selected item
    for item in all_results:
        preview_text = item.get("prepared_text") or ""
        if len(preview_text) > 300:
            preview = preview_text[:297] + "..."
        else:
            preview = preview_text
        print(
            f"{item['country']} / {item['source']}: "
            f"{item['original_title'][:100]}... "
            f"[{item['article_status']} | {item['text_basis']} | {item['prepared_text_char_count']} chars] "
            f"Preview: {preview}"
        )

    # Print timing measurements
    total_time = time.perf_counter() - start_total
    print(f"\n=== Timing ===")
    print(f"Total script runtime: {total_time:.2f} seconds", flush=True)

    for status in source_status_records:
        if status['download_time'] is not None:
            print(f"{status['country']} / {status['source']} download: {status['download_time']:.2f} seconds", flush=True)
        if status['parse_time'] is not None:
            print(f"{status['country']} / {status['source']} parse: {status['parse_time']:.2f} seconds", flush=True)
        if status['total_processing_time'] is not None:
            print(f"{status['country']} / {status['source']} total processing: {status['total_processing_time']:.2f} seconds",
flush=True)

    print(f"\nRaw snapshot saved to: {raw_output_path}")
    print(f"Prepared results saved to: {prepared_output_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
