import os
import argparse
import logging
from hash_files import process_directory
from git_submodule_version import process_directory_with_git

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def process_all_directories(root_dir, debug=False):
    """Process all subdirectories in the root directory."""
    if not os.path.isdir(root_dir):
        logger.error(f"Error: {root_dir} is not a valid directory")
        return
    
    # Process each subdirectory
    for item in os.listdir(root_dir):
        item_path = os.path.join(root_dir, item)
        if os.path.isdir(item_path):
            logger.info(f"\nProcessing directory: {item}")
            
            # Try Git submodule version detection first
            git_info = process_directory_with_git(item_path, debug)
            
            # Always try file hashing version detection
            logger.info(f"\nAttempting file hashing version detection for: {item}")
            hash_info = process_directory(item_path, debug)
            
            if hash_info:
                logger.info(f"Found version information using file hashing for: {item}")
            else:
                logger.info(f"No version information found using file hashing for: {item}")

def main():
    parser = argparse.ArgumentParser(description='Process all subdirectories to find library versions.')
    parser.add_argument('root_dir', help='Root directory path to process')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode (saves Git info to JSON files)')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help='Set the logging level')
    args = parser.parse_args()
    
    # Set logging level
    logger.setLevel(getattr(logging, args.log_level))
    
    process_all_directories(args.root_dir, args.debug)

if __name__ == "__main__":
    main() 
