import os
import hashlib
import base64
import json
import requests
import argparse
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def calculate_md5_hash(file_path):
    """Calculate MD5 hash of a file and return it as base64 encoded bytes."""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return base64.b64encode(hash_md5.digest()).decode('utf-8')

def find_and_hash_files(root_dir, name, debug=False):
    """Walk through directories and find C/C++ files to hash."""
    file_hashes = []
    extensions = {'.c', '.cc', '.h', '.hh', '.cpp', '.hpp'}
    
    for root, _, files in os.walk(root_dir):
        for file in files:
            if Path(file).suffix in extensions:
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, root_dir)
                try:
                    file_hash = calculate_md5_hash(file_path)
                    file_hashes.append({
                        "hash": file_hash,
                        "file_path": relative_path
                    })
                    if debug:
                        logger.debug(f"Processed file: {relative_path}")
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {str(e)}")
    
    if debug:
        logger.debug(f"Total files processed: {len(file_hashes)}")
    
    return {
        "name": name,
        "file_hashes": file_hashes
    }

def query_osv_api(file_hashes_data, debug=False):
    """Query the OSV API determineversion endpoint with the file hashes data."""
    url = "https://api.osv.dev/v1experimental/determineversion"
    
    # The payload format matches exactly what the API expects
    payload = {
        "name": file_hashes_data["name"],
        "file_hashes": file_hashes_data["file_hashes"]
    }
    
    if debug:
        logger.debug("\nSending payload to OSV API:")
        logger.debug(json.dumps(payload, indent=2))
        logger.debug(f"\nTotal number of files being sent: {len(payload['file_hashes'])}")
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error querying OSV API: {str(e)}")
        return None

def process_directory(root_dir, debug=False):
    """Process a directory to find and hash C/C++ files, then query OSV API."""
    if not os.path.isdir(root_dir):
        logger.error(f"Error: {root_dir} is not a valid directory")
        return None
    
    # Extract name from the last directory in the path
    name = os.path.basename(os.path.normpath(root_dir))
    logger.info(f"Processing library: {name}")
    logger.info(f"Target directory: {os.path.abspath(root_dir)}")
    
    # Generate file hashes
    file_hashes_data = find_and_hash_files(root_dir, name, debug)
    
    if debug:
        # Save file hashes to JSON in the target directory
        hashes_file = os.path.join(root_dir, f"{name}_hashes.json")
        hashes_file_abs = os.path.abspath(hashes_file)
        with open(hashes_file, 'w') as f:
            json.dump(file_hashes_data, f, indent=2)
        logger.info(f"File hashes saved to: {hashes_file_abs}")
    
    # Query OSV API
    osv_response = query_osv_api(file_hashes_data, debug)
    if osv_response:
        # Always save OSV API response to JSON in the target directory
        osv_file = os.path.join(root_dir, f"{name}_osv_response.json")
        osv_file_abs = os.path.abspath(osv_file)
        with open(osv_file, 'w') as f:
            json.dump(osv_response, f, indent=2)
        logger.info(f"OSV API response saved to: {osv_file_abs}")
        
        # Print the matches in a readable format
        logger.info("\nPotential library matches:")
        for match in osv_response.get("matches", []):
            logger.info(f"\nScore: {match['score']}")
            logger.info(f"Version: {match['repo_info']['version']}")
            logger.info(f"Repository: {match['repo_info']['address']}")
            logger.info(f"Tag: {match['repo_info']['tag']}")
            logger.info(f"Minimum file matches: {match.get('minimum_file_matches', 'N/A')}")
            if 'estimated_diff_files' in match:
                logger.info(f"Estimated different files: {match['estimated_diff_files']}")
        return osv_response
    else:
        logger.error("Failed to get response from OSV API")
        return None

def main():
    parser = argparse.ArgumentParser(description='Process C/C++ files and query OSV API for version information.')
    parser.add_argument('root_dir', help='Root directory path to process')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode (saves hashes and responses to JSON files)')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help='Set the logging level')
    args = parser.parse_args()
    
    # Set logging level
    logger.setLevel(getattr(logging, args.log_level))
    
    process_directory(args.root_dir, args.debug)

if __name__ == "__main__":
    main() 