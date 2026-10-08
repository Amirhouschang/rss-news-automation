"""
Source Diagnostic Tool for Local News Automation Project

Diagnoses access issues and compares RSS content with article text.
"""

import argparse
import json
import os
import requests
from datetime import datetime, timezone
import trafilatura
import feedparser
from typing import List, Dict, Optional
from html.parser import HTMLParser


class MLStripper(HTMLParser):
    """HTML stripper to remove tags from HTML content."""
    
    def __init__(self):
        super().__init__()
        self.reset()
        self.fed = []
        
    def handle_data(self, d):
        self.fed.append(d)
        
    def get_data(self):
        return ''.join(self.fed)


def strip_html(html: str) -> str:
    """
    Remove HTML tags from text.
    
    Args:
        html (str): HTML content
        
    Returns:
        str: Plain text without HTML tags
    """
    if not html:
        return ""
        
    s = MLStripper()
    s.feed(html)
    return s.get_data()


def parse_arguments() -> argparse.Namespace:
    """
    Parse command line arguments.
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(description='Diagnose source access and compare RSS content with article text')
    parser.add_argument('--previous-results', required=True, help='Path to previous article test JSON file')
    return parser.parse_args()


def load_previous_results(filepath: str) -> List[str]:
    """
    Load previously tested URLs from the article test results.
    
    Args:
        filepath (str): Path to previous results file
        
    Returns:
        List[str]: List of original_url values
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        urls = []
        if 'results' in data:
            for result in data['results']:
                if 'original_url' in result and result['original_url']:
                    urls.append(result['original_url'])
                    
        return urls
    except Exception as e:
        print(f"Error reading previous results file {filepath}: {e}")
        return []


def fetch_and_parse_feed(url: str, timeout: int = 30) -> Optional[feedparser.FeedParserDict]:
    """
    Fetch and parse an RSS feed.
    
    Args:
        url (str): Feed URL
        timeout (int): Request timeout in seconds
        
    Returns:
        feedparser.FeedParserDict or None: Parsed feed or None if failed
    """
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        
        feed = feedparser.parse(response.content)
        
        # Check if feedparser recognized a supported format
        if not hasattr(feed, 'version') or not feed.version:
            print(f"Warning: No supported RSS/Atom format recognized in response from {url}")
            return None
            
        return feed
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching feed {url}: {e}")
        return None


def get_first_n_unique_urls(entries: List[Dict], n: int, exclude_urls: List[str]) -> List[Dict]:
    """
    Get first N unique URLs from entries that are not in exclude list.
    
    Args:
        entries (List[Dict]): Feed entries
        n (int): Number of URLs to select
        exclude_urls (List[str]): URLs to exclude
        
    Returns:
        List[Dict]: Selected entries with URL information
    """
    selected = []
    seen_urls = set()
    
    for entry in entries:
        url = getattr(entry, 'link', None)
        if url and url not in seen_urls and url not in exclude_urls:
            selected.append({
                'url': url,
                'title': getattr(entry, 'title', ''),
                'published': getattr(entry, 'published', ''),
                'summary': getattr(entry, 'summary', ''),
                'content': getattr(entry, 'content', []),
                'source': entry.get('source', '') if hasattr(entry, 'source') else '',
                'country': entry.get('country', '') if hasattr(entry, 'country') else ''
            })
            seen_urls.add(url)
            
        if len(selected) >= n:
            break
            
    return selected


def download_article(url: str, timeout: int = 30) -> Optional[requests.Response]:
    """
    Download an article page.
    
    Args:
        url (str): URL to download
        timeout (int): Request timeout in seconds
        
    Returns:
        requests.Response or None: Response object or None if failed
    """
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        print(f"Error downloading {url}: {e}")
        raise


def extract_article_text(response: requests.Response) -> str:
    """
    Extract article text using trafilatura.
    
    Args:
        response (requests.Response): HTTP response object
        
    Returns:
        str: Extracted article text or empty string
    """
    try:
        extracted = trafilatura.extract(
            response.content,
            url=response.url,
            include_comments=False,
            output_format="txt"
        )
        return extracted if extracted else ""
    except Exception as e:
        print(f"Error extracting text from {response.url}: {e}")
        raise


def is_interstitial_text(text: str) -> bool:
    """
    Check if text is an interstitial redirect page.
    
    Args:
        text (str): Extracted text
        
    Returns:
        bool: True if text matches interstitial pattern
    """
    # Check if text is short and contains the specific phrase
    if len(text) <= 300 and "transferring to the website" in text.lower():
        return True
    return False


def process_selected_entry(entry_data: Dict, previous_urls: List[str]) -> Dict:
    """
    Process a selected entry for diagnostic purposes.
    
    Args:
        entry_data (Dict): Entry data from feed
        previous_urls (List[str]): URLs from previous results to exclude
        
    Returns:
        Dict: Processed diagnostic result
    """
    result = {
        'country': entry_data.get('country', ''),
        'source': entry_data.get('source', ''),
        'original_title': entry_data.get('title', ''),
        'published_at': entry_data.get('published', ''),
        'original_url': entry_data.get('url', ''),
        'rss_summary': entry_data.get('summary', ''),
        'rss_content': entry_data.get('content', []),
        'rss_summary_text': '',
        'rss_content_text': '',
        'article_status': None,
        'http_status': None,
        'article_text': None,
        'text_char_count': 0,
        'rejected_text': None
    }
    
    # Process RSS content for readable text
    result['rss_summary_text'] = strip_html(entry_data.get('summary', ''))
    
    content_text_parts = []
    for content_item in entry_data.get('content', []):
        if isinstance(content_item, dict) and 'value' in content_item:
            content_text_parts.append(strip_html(content_item['value']))
        elif isinstance(content_item, str):
            content_text_parts.append(strip_html(content_item))
    
    result['rss_content_text'] = ' '.join(content_text_parts)
    
    # Download and extract article
    try:
        response = download_article(entry_data.get('url', ''))
        
        if response is None:
            result['article_status'] = "download_failed"
            result['error_message'] = "Failed to download article"
            return result
            
        result['http_status'] = response.status_code
        
        # Extract text
        extracted_text = extract_article_text(response)
        
        # Check for interstitial content
        if is_interstitial_text(extracted_text):
            result['article_status'] = "interstitial"
            result['rejected_text'] = extracted_text
            result['article_text'] = None
            result['text_char_count'] = 0
            result['error_message'] = "Interstitial page detected: 'Transferring to the website' found"
            return result
        
        if extracted_text:
            result['article_status'] = "extracted"
            result['article_text'] = extracted_text
            result['text_char_count'] = len(extracted_text)
        else:
            result['article_status'] = "empty"
            result['article_text'] = None
            result['text_char_count'] = 0
            result['error_message'] = "No text extracted from article"
            
    except requests.exceptions.RequestException as e:
        result['article_status'] = "download_failed"
        result['http_status'] = None
        result['error_message'] = str(e)
        return result
    except Exception as e:
        result['article_status'] = "extraction_error"
        result['error_message'] = f"Exception during extraction: {str(e)}"
        
    return result


def save_diagnostic_file(results: List[Dict], feed_errors: List[Dict], input_file_path: str, timestamp: str) -> None:
    """
    Save diagnostic results to JSON file.
    
    Args:
        results (List[Dict]): Diagnostic results
        feed_errors (List[Dict]): Feed parsing errors
        input_file_path (str): Path to previous results file
        timestamp (str): Timestamp for filename
    """
    # Derive output directory from input file location
    input_dir = os.path.dirname(input_file_path)
    data_dir = os.path.dirname(input_dir)  # parent of raw directory
    diagnostics_dir = os.path.join(data_dir, "diagnostics")
    
    filename = f"diagnostic_test_{timestamp}.json"
    filepath = os.path.join(diagnostics_dir, filename)
    
    output_data = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "input_file": os.path.abspath(input_file_path),
        "feed_errors": feed_errors,
        "results": results
    }
    
    try:
        # Ensure directory exists
        os.makedirs(diagnostics_dir, exist_ok=True)
        
        # Write to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
            
        print(f"Saved diagnostic results to: {os.path.abspath(filepath)}")
        
    except Exception as e:
        print(f"Error saving to file {filepath}: {e}")
        raise


def main() -> None:
    """
    Main function to diagnose source access and compare RSS content.
    """
    args = parse_arguments()
    
    # Validate input file
    if not os.path.exists(args.previous_results):
        print(f"Previous results file does not exist: {args.previous_results}")
        return
        
    print("Starting source diagnostic...")
    
    # Load previous results to exclude URLs
    previous_urls = load_previous_results(args.previous_results)
    print(f"Found {len(previous_urls)} previously tested URLs to exclude")
    
    # Create timestamp once for both filename and checked_at
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    
    # Define feeds to check
    feeds = [
        {
            "name": "Iran / IRNA",
            "url": "https://www.irna.ir/rss"
        },
        {
            "name": "Russia / TASS",
            "url": "https://tass.ru/rss/v2.xml"
        }
    ]
    
    all_results = []
    feed_errors = []
    
    for feed_info in feeds:
        print(f"\n{'='*60}")
        print(f"Processing: {feed_info['name']}")
        
        # Fetch and parse feed
        feed = fetch_and_parse_feed(feed_info['url'])
        
        if feed is None:
            feed_errors.append({
                "source": feed_info['name'],
                "url": feed_info['url'],
                "error": "Failed to fetch or parse feed"
            })
            continue
            
        print(f"Feed contains {len(feed.entries)} entries")
        
        # Get first 3 unique URLs (excluding previous results)
        selected_entries = get_first_n_unique_urls(
            feed.entries, 
            3, 
            previous_urls
        )
        
        if not selected_entries:
            print("No new entries found for this feed")
            continue
            
        print(f"Selected {len(selected_entries)} entries for testing")
        
        # Process each selected entry
        for i, entry in enumerate(selected_entries, 1):
            print(f"\nTesting entry {i}: {entry['title'][:50]}...")
            
            # Add source and country info to entry data
            entry['source'] = feed_info['name']
            if "Iran" in feed_info['name']:
                entry['country'] = "Iran"
            elif "Russia" in feed_info['name']:
                entry['country'] = "Russia"
                
            result = process_selected_entry(entry, previous_urls)
            all_results.append(result)
            
            # Print results
            print(f"  Status: {result['article_status']}")
            if result['http_status']:
                print(f"  HTTP Status: {result['http_status']}")
            print(f"  Character count: {result['text_char_count']}")
            
            # Print previews
            preview = (result['rss_summary_text'][:300] + "..." 
                      if len(result['rss_summary_text']) > 300 else result['rss_summary_text'])
            print(f"  RSS Summary: {preview}")
                
            preview = (result['rss_content_text'][:300] + "..." 
                      if len(result['rss_content_text']) > 300 else result['rss_content_text'])
            print(f"  RSS Content: {preview}")
                
            if result['article_text']:
                preview = (result['article_text'][:300] + "..." 
                          if len(result['article_text']) > 300 else result['article_text'])
                print(f"  Article Text: {preview}")
    
    # Save results
    try:
        save_diagnostic_file(all_results, feed_errors, args.previous_results, timestamp)
        successful_count = sum(1 for r in all_results if r['article_status'] == 'extracted')
        print(f"\nTotal entries processed: {len(all_results)}")
        print(f"Successful extractions: {successful_count}")
    except Exception as e:
        print(f"Failed to save diagnostic results: {e}")


if __name__ == "__main__":
    main()
