import os
import subprocess
import json
import logging
from pathlib import Path
import argparse

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_git_submodule_info(directory):
    """Get information about Git submodules in the given directory."""
    logger.info(f"Starting get_git_submodule_info for {directory}")
    logger.info(f"Current logging level: {logger.getEffectiveLevel()}")
    
    try:
        # Get submodule information
        result = subprocess.run(
            ['git', 'submodule', 'status'],
            cwd=directory,
            capture_output=True,
            text=True
        )
        
        # Log the raw output for debugging
        logger.info(f"Git submodule status output for {directory}:")
        logger.info(f"Return code: {result.returncode}")
        logger.info(f"Stdout: {result.stdout}")
        logger.info(f"Stderr: {result.stderr}")
        
        if result.returncode != 0:
            logger.info(f"Git submodule status failed with return code {result.returncode}")
            return None

        submodules = []
        for line in result.stdout.splitlines():
            parts = line.strip().split()
            if len(parts) >= 2:
                commit_hash = parts[0].lstrip('-+')
                path = parts[1]
                submodules.append({
                    'path': path,
                    'commit': commit_hash
                })
                logger.info(f"Found submodule: path={path}, commit={commit_hash}")
            else:
                logger.info(f"Skipping malformed line: {line}")

        if not submodules:
            logger.info(f"No submodules found in {directory}")
        else:
            logger.info(f"Found {len(submodules)} submodules in {directory}")

        return submodules
    except Exception as e:
        logger.error(f"Error getting Git submodule info for {directory}: {str(e)}")
        return None

def get_git_tag_from_commit(directory, commit_hash):
    """Get the Git tag associated with a commit hash."""
    try:
        result = subprocess.run(
            ['git', 'describe', '--tags', '--exact-match', commit_hash],
            cwd=directory,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except Exception as e:
        logger.error(f"Error getting Git tag for commit {commit_hash}: {str(e)}")
        return None

def get_git_remote_url(directory):
    """Get the remote URL of a Git repository."""
    try:
        result = subprocess.run(
            ['git', 'remote', 'get-url', 'origin'],
            cwd=directory,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except Exception as e:
        logger.error(f"Error getting Git remote URL for {directory}: {str(e)}")
        return None

def get_git_commit_info(directory, commit_hash):
    """Get detailed information about a Git commit."""
    try:
        # Get commit author and date
        result = subprocess.run(
            ['git', 'show', '-s', '--format=%an|%ae|%ad', commit_hash],
            cwd=directory,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            author_name, author_email, author_date = result.stdout.strip().split('|')
            return {
                "author_name": author_name,
                "author_email": author_email,
                "author_date": author_date
            }
        return None
    except Exception as e:
        logger.error(f"Error getting commit info for {commit_hash}: {str(e)}")
        return None

def process_directory_with_git(root_dir, debug=False):
    """Process a directory to find library versions using Git submodule information."""
    if not os.path.isdir(root_dir):
        logger.error(f"Error: {root_dir} is not a valid directory")
        return None
    
    # Extract name from the last directory in the path
    name = os.path.basename(os.path.normpath(root_dir))
    logger.info(f"\nProcessing library with Git: {name}")
    logger.info(f"Target directory: {os.path.abspath(root_dir)}")
    
    # Check if directory is a Git repository
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--is-inside-work-tree'],
            cwd=root_dir,
            capture_output=True,
            text=True
        )
        is_git_repo = result.returncode == 0
    except Exception as e:
        logger.error(f"Error checking Git repository status: {str(e)}")
        is_git_repo = False
    
    if not is_git_repo:
        # Save information about non-Git repository
        no_git_info = {
            "name": name,
            "path": os.path.abspath(root_dir),
            "reason": "Not a Git repository"
        }
        no_git_file = os.path.join(root_dir, f"{name}_no_git_info.json")
        with open(no_git_file, 'w') as f:
            json.dump(no_git_info, f, indent=2)
        logger.info(f"No Git info saved to: {no_git_file}")
        return no_git_info
    
    # Get Git submodule information
    submodules = get_git_submodule_info(root_dir)
    if not submodules:
        # Save information about repository with no submodules
        no_submodules_info = {
            "name": name,
            "path": os.path.abspath(root_dir),
            "reason": "No submodules found"
        }
        no_submodules_file = os.path.join(root_dir, f"{name}_no_submodules_info.json")
        with open(no_submodules_file, 'w') as f:
            json.dump(no_submodules_info, f, indent=2)
        logger.info(f"No submodules found in {name}")
        logger.info(f"No submodules info saved to: {no_submodules_file}")
        return no_submodules_info
    
    # Only log "Found version information" if we actually found submodules
    logger.info(f"Found version information using Git submodules in {name}")
    
    # Process each submodule
    library_info = {
        "name": name,
        "submodules": []
    }
    
    logger.info(f"\nFound {len(submodules)} submodules in {name}:")
    logger.info("=" * 80)
    
    for submodule in submodules:
        submodule_path = os.path.join(root_dir, submodule['path'])
        if os.path.isdir(submodule_path):
            tag = get_git_tag_from_commit(submodule_path, submodule['commit'])
            remote_url = get_git_remote_url(submodule_path)
            commit_info = get_git_commit_info(submodule_path, submodule['commit'])
            
            submodule_info = {
                "path": submodule['path'],
                "commit": submodule['commit'],
                "tag": tag if tag else "No tag found",
                "repository": remote_url if remote_url else "No remote URL found",
                "commit_info": commit_info
            }
            library_info["submodules"].append(submodule_info)
            
            # Log detailed submodule information
            logger.info(f"\nSubmodule: {submodule['path']}")
            logger.info(f"Commit: {submodule['commit'][:8]}")
            if tag:
                logger.info(f"Tag: {tag}")
            if remote_url:
                logger.info(f"Repository: {remote_url}")
            if commit_info:
                logger.info(f"Author: {commit_info['author_name']} <{commit_info['author_email']}>")
                logger.info(f"Date: {commit_info['author_date']}")
            logger.info("-" * 40)
            
            if debug:
                logger.debug(f"Submodule info: {json.dumps(submodule_info, indent=2)}")
    
    logger.info("=" * 80)
    
    # Always save Git information to JSON in the target directory
    git_file = os.path.join(root_dir, f"{name}_git_info.json")
    git_file_abs = os.path.abspath(git_file)
    with open(git_file, 'w') as f:
        json.dump(library_info, f, indent=2)
    logger.info(f"Git information saved to: {git_file_abs}")
    
    return library_info

def main():
    parser = argparse.ArgumentParser(description='Process directories to find library versions using Git submodule information.')
    parser.add_argument('root_dir', help='Root directory path to process')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode (saves Git info to JSON files)')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help='Set the logging level')
    args = parser.parse_args()
    
    # Set logging level
    logger.setLevel(getattr(logging, args.log_level))
    
    process_directory_with_git(args.root_dir, args.debug)

if __name__ == "__main__":
    main() 
