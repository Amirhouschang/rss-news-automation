"""
RSS Feed Fetcher for Local News Automation Project

Fetches news feeds from multiple countries and displays basic information.
"""

import feedparser
import requests
import json
import os
import time
from datetime import datetime, timezone
from typing import List, Dict, Optional


def fetch_feed(url: str, timeout: int = 30) -> Optional[feedparser.FeedParserDict]:
    """
    Fetch an RSS feed with a timeout and validate the response.
    
    Args:
        url (str): The URL of the RSS feed
        timeout (int): Request timeout in seconds
        
    Returns:
        feedparser.FeedParserDict or None: Parsed feed data or None if failed
    """
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        
        # Parse the feed content regardless of Content-Type header
        feed = feedparser.parse(response.content)
        
        # Check if feedparser recognized a supported format
        if not hasattr(feed, 'version') or not feed.version:
            print(f"Warning: No supported RSS/Atom format recognized in response from {url}")
            return None
            
        # Report any parsing warnings
        if hasattr(feed, 'bozo_exception') and feed.bozo_exception:
            print(f"Warnings for {url}: {feed.bozo_exception}")
            
        return feed
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None


def format_date(entry: Dict) -> str:
    """
    Format publication date or return placeholder if missing.
    
    Args:
        entry (Dict): Feed entry dictionary
        
    Returns:
        str: Formatted date or placeholder
    """
    if hasattr(entry, 'published') and entry.published:
        return entry.published
    elif hasattr(entry, 'updated') and entry.updated:
        return entry.updated
    else:
        return "Publication date unavailable"


def get_country_from_source(source_name: str) -> str:
    """
    Determine country from source name.
    
    Args:
        source_name (str): Name of the news source
        
    Returns:
        str: Country name
    """
    if "Tagesschau" in source_name:
        return "Germany"
    elif "IRNA" in source_name:
        return "Iran"
    elif "Chinanews" in source_name:
        return "China"
    elif "TASS" in source_name:
        return "Russia"
    elif "Ukrinform" in source_name:
        return "Ukraine"
    else:
        return "Unknown"


def save_entries_to_json(entries: List[Dict], sources: List[Dict], output_dir: str, timestamp: str) -> None:
    """
    Save fetched entries to a JSON file.
    
    Args:
        entries (List[Dict]): List of news entries
        sources (List[Dict]): List of source status records
        output_dir (str): Directory to save the file
        timestamp (str): Timestamp for filename
    """
    filename = f"rss_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)
    
    # Prepare data structure
    data = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "sources": sources,
        "entries": entries
    }
    
    try:
        # Ensure directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Write to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        print(f"Saved {len(entries)} entries to: {os.path.abspath(filepath)}")
        
    except Exception as e:
        print(f"Error saving to file {filepath}: {e}")
        raise


def main() -> None:
    """
    Main function to fetch and display RSS feeds.
    """
    # Get script directory for relative path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "data", "raw")
    
    # Create timestamp once for both filename and fetched_at
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    
    # List of RSS feeds to fetch
    feeds = [
        {
            "name": "Germany / Tagesschau",
            "url": "https://www.tagesschau.de/index~rss2.xml"
        },
        {
            "name": "Iran / IRNA",
            "url": "https://www.irna.ir/rss"
        },
        {
            "name": "China / Chinanews",
            "url": "https://www.chinanews.com.cn/rss/scroll-news.xml"
        },
        {
            "name": "Russia / TASS",
            "url": "https://tass.ru/rss/v2.xml"
        },
        {
            "name": "Ukraine / Ukrinform",
            "url": "https://www.ukrinform.ua/rss/block-lastnews"
        }
    ]
    
    print("Starting RSS feed fetcher...")
    start_time = time.time()
    
    # Collect all entries and sources
    all_entries = []
    source_statuses = []
    
    for feed_info in feeds:
        print(f"\n{'='*60}")
        print(f"Fetching: {feed_info['name']}")
        
        feed = fetch_feed(feed_info['url'])
        
        # Record source status
        status_record = {
            "country": get_country_from_source(feed_info['name']),
            "source": feed_info['name'],
            "feed_url": feed_info['url'],
            "success": feed is not None,
            "entry_count": 0,
            "error_message": None
        }
        
        if feed is not None:
            # Process all entries from this feed
            for entry in feed.entries:
                entry_data = {
                    "country": get_country_from_source(feed_info['name']),
                    "source": feed_info['name'],
                    "original_title": getattr(entry, 'title', ''),
                    "published_at": getattr(entry, 'published', None),
                    "updated_at": getattr(entry, 'updated', None),
                    "original_url": getattr(entry, 'link', '')
                }
                all_entries.append(entry_data)
            
            status_record["entry_count"] = len(feed.entries)
            print(f"Successfully fetched {len(feed.entries)} entries")
            
            # Display first 5 entries for preview
            print("\nFirst 5 entries:")
            for i, entry in enumerate(feed.entries[:5], 1):
                title = getattr(entry, 'title', 'Title unavailable')
                date = format_date(entry)
                link = getattr(entry, 'link', 'Link unavailable')
                
                print(f"  {i}. Title: {title}")
                print(f"     Date: {date}")
                print(f"     URL: {link}")
        else:
            status_record["error_message"] = "Failed to fetch or parse feed"
            print("Failed to retrieve or parse feed")
        
        source_statuses.append(status_record)
    
    end_time = time.time()
    print(f"\n{'='*60}")
    print(f"Completed in {end_time - start_time:.2f} seconds")
    
    # Save all entries to JSON file
    try:
        save_entries_to_json(all_entries, source_statuses, data_dir, timestamp)
        print(f"Total entries saved: {len(all_entries)}")
    except Exception as e:
        print(f"Failed to save entries: {e}")


if __name__ == "__main__":
    main()