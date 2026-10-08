"""
Article Extractor for Local News Automation Project

Extracts article text from selected news entries.
"""

import argparse
import json
import os
import requests
from datetime import datetime, timezone
import trafilatura
from typing import List, Dict, Optional


def parse_arguments() -> argparse.Namespace:
    """
    Parse command line arguments.
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(description='Extract article text from RSS entries')
    parser.add_argument('--input', required=True, help='Path to input RSS JSON file')
    return parser.parse_args()


def load_input_file(filepath: str) -> Dict:
    """
    Load the input JSON file.
    
    Args:
        filepath (str): Path to input file
        
    Returns:
        Dict: Parsed JSON data
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading input file {filepath}: {e}")
        raise


def find_entry_for_source(entries: List[Dict], source_name: str, country: str) -> Optional[Dict]:
    """
    Find the first entry matching a source and country.
    
    Args:
        entries (List[Dict]): List of all entries
        source_name (str): Name of the news source
        country (str): Country name
        
    Returns:
        Dict or None: Matching entry or None if not found
    """
    for entry in entries:
        if entry['source'] == source_name and entry['country'] == country:
            return entry
    return None


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


def process_entry(entry: Optional[Dict], source_name: str, country: str, input_file_path: str) -> Dict:
    """
    Process a single entry to extract article text.
    
    Args:
        entry (Dict or None): Entry data or None if no entry
        source_name (str): Name of the news source
        country (str): Country name
        input_file_path (str): Path to the input file
        
    Returns:
        Dict: Processed entry with extraction results
    """
    # Create output directory based on input file location
    input_dir = os.path.dirname(input_file_path)
    data_dir = os.path.dirname(input_dir)  # parent of raw directory
    articles_dir = os.path.join(data_dir, "articles")
    
    result = {
        'source': source_name,
        'country': country,
        'extraction_status': None,
        'article_text': None,
        'text_char_count': 0,
        'http_status': None,
        'error_message': None
    }
    
    # If no entry exists for this source, mark as no_entry
    if entry is None:
        result['extraction_status'] = "no_entry"
        result['error_message'] = "No entry found for this source in input data"
        return result
    
    # Copy original fields
    result.update(entry)
    
    # Download the article
    try:
        response = download_article(entry['original_url'])
    except requests.exceptions.HTTPError as e:
        # Handle HTTP errors specifically
        result['extraction_status'] = "download_failed"
        result['error_message'] = str(e)
        if e.response is not None and e.response.status_code is not None:
            result['http_status'] = e.response.status_code
        return result
    except requests.exceptions.RequestException as e:
        # Handle other request errors
        result['extraction_status'] = "download_failed"
        result['error_message'] = str(e)
        return result
    
    # Check if response is valid (should not happen after raise_for_status, but safety check)
    if response is None:
        result['extraction_status'] = "download_failed"
        result['error_message'] = "Failed to download article - no response"
        return result
        
    result['http_status'] = response.status_code
    
    # Extract text
    try:
        extracted_text = extract_article_text(response)
        
        # Check for interstitial content
        if is_interstitial_text(extracted_text):
            result['extraction_status'] = "interstitial"
            result['article_text'] = None
            result['text_char_count'] = 0
            result['error_message'] = "Interstitial page detected: 'Transferring to the website' found"
            return result
        
        if extracted_text:
            result['extraction_status'] = "extracted"
            result['article_text'] = extracted_text
            result['text_char_count'] = len(extracted_text)
        else:
            result['extraction_status'] = "empty"
            result['article_text'] = None
            result['text_char_count'] = 0
            result['error_message'] = "No text extracted from article"
            
    except Exception as e:
        result['extraction_status'] = "extraction_error"
        result['error_message'] = f"Exception during extraction: {str(e)}"
        
    return result


def save_output_file(results: List[Dict], input_file_path: str, timestamp: str) -> None:
    """
    Save extraction results to JSON file.
    
    Args:
        results (List[Dict]): Extraction results
        input_file_path (str): Path to input file
        timestamp (str): Timestamp for filename
    """
    # Derive output directory from input file location
    input_dir = os.path.dirname(input_file_path)
    data_dir = os.path.dirname(input_dir)  # parent of raw directory
    articles_dir = os.path.join(data_dir, "articles")
    
    filename = f"articles_test_{timestamp}.json"
    filepath = os.path.join(articles_dir, filename)
    
    output_data = {
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "input_file": os.path.abspath(input_file_path),
        "results": results
    }
    
    try:
        # Ensure directory exists
        os.makedirs(articles_dir, exist_ok=True)
        
        # Write to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
            
        print(f"Saved extraction results to: {os.path.abspath(filepath)}")
        
    except Exception as e:
        print(f"Error saving to file {filepath}: {e}")
        raise


def main() -> None:
    """
    Main function to extract article text from RSS entries.
    """
    args = parse_arguments()
    
    # Validate input file
    if not os.path.exists(args.input):
        print(f"Input file does not exist: {args.input}")
        return
        
    # Load input data
    try:
        input_data = load_input_file(args.input)
    except Exception as e:
        print(f"Failed to load input data: {e}")
        return
    
    # Validate input structure
    if not isinstance(input_data, dict):
        print("Error: Input file is not a JSON object")
        return
        
    if 'sources' not in input_data or 'entries' not in input_data:
        print("Error: Input file must contain 'sources' and 'entries' keys")
        return
        
    if not isinstance(input_data['sources'], list) or not isinstance(input_data['entries'], list):
        print("Error: 'sources' and 'entries' must be lists")
        return
    
    print("Starting article extraction...")
    
    # Create timestamp once for both filename and extracted_at
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    
    # Process each source
    results = []
    successful_count = 0
    failed_count = 0
    
    for source in input_data['sources']:
        source_name = source.get('source', '')
        country = source.get('country', '')
        
        print(f"\nProcessing: {country} - {source_name}")
        
        # Find matching entry
        entry = find_entry_for_source(input_data['entries'], source_name, country)
        
        # Process entry
        result = process_entry(entry, source_name, country, args.input)
        results.append(result)
        
        # Print status information
        if result['extraction_status'] == 'extracted':
            successful_count += 1
            text_preview = result['article_text'][:300] + "..." if len(result['article_text']) > 300 else result['article_text']
            print(f"  Status: extracted ({result['text_char_count']} characters)")
            print(f"  Preview: {text_preview}")
        elif result['extraction_status'] == 'no_entry':
            failed_count += 1
            print(f"  Status: no_entry")
            if result.get('error_message'):
                print(f"  Error: {result['error_message']}")
        elif result['extraction_status'] == 'download_failed':
            failed_count += 1
            print(f"  Status: download_failed")
            if result.get('error_message'):
                print(f"  Error: {result['error_message']}")
        elif result['extraction_status'] == 'empty':
            failed_count += 1
            print(f"  Status: empty (0 characters)")
            if result.get('error_message'):
                print(f"  Error: {result['error_message']}")
        elif result['extraction_status'] == 'interstitial':
            failed_count += 1
            print(f"  Status: interstitial")
            if result.get('error_message'):
                print(f"  Error: {result['error_message']}")
        elif result['extraction_status'] == 'extraction_error':
            failed_count += 1
            print(f"  Status: extraction_error")
            if result.get('error_message'):
                print(f"  Error: {result['error_message']}")
    
    # Save results
    try:
        save_output_file(results, args.input, timestamp)
        print(f"\nTotal entries processed: {len(results)}")
        print(f"Successful extractions: {successful_count}")
        print(f"Failed extractions: {failed_count}")
    except Exception as e:
        print(f"Failed to save extraction results: {e}")


if __name__ == "__main__":
    main()
