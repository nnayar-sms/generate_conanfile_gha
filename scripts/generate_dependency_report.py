import os
import json
import argparse
import logging
from pathlib import Path
from process_all_directories import process_all_directories

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Common third-party directory names
THIRD_PARTY_DIRS = [
    '3rdparty',
    'third-party',
    'third_party',
    'thirdparty',
    'external',
    'externals',
    'deps',
    'dependencies',
    'libs',
    'libraries'
]

def get_top_versions(osv_response, num_versions=3):
    """Extract top N versions from OSV API response."""
    matches = osv_response.get("matches", [])
    sorted_matches = sorted(matches, key=lambda x: x.get("score", 0), reverse=True)
    top_versions = []
    
    for match in sorted_matches[:num_versions]:
        version_info = {
            "version": match["repo_info"]["version"],
            "score": match["score"],
            "repository": match["repo_info"]["address"],
            "tag": match["repo_info"]["tag"],
            "file_matches": match.get("minimum_file_matches", "N/A"),
            "diff_files": match.get("estimated_diff_files", "N/A")
        }
        top_versions.append(version_info)
    
    return top_versions

def find_osv_response_files(root_dir):
    """Recursively find all OSV response files in the directory tree."""
    return list(Path(root_dir).rglob("*_osv_response.json"))

def get_library_name(file_path):
    """Extract library name from file path."""
    # Get the directory name from the file path
    dir_name = os.path.basename(os.path.dirname(file_path))
    # Only replace hyphens with underscores, keep 'lib' prefix
    name = dir_name.replace('-', '_')
    return name

def find_failed_libraries(root_dir):
    """Find top-level directories that contain C/C++ files but no OSV response."""
    failed_libraries = []
    extensions = {'.c', '.cc', '.h', '.hh', '.cpp', '.hpp'}
    
    # Only check immediate subdirectories
    for item in os.listdir(root_dir):
        dirpath = os.path.join(root_dir, item)
        if os.path.isdir(dirpath):
            # Check if directory contains C/C++ files
            has_cpp_files = False
            for root, _, files in os.walk(dirpath):
                if any(Path(f).suffix in extensions for f in files):
                    has_cpp_files = True
                    break
            
            if has_cpp_files:
                # Check if there's no corresponding OSV response file
                dir_name = os.path.basename(dirpath)
                osv_file = os.path.join(dirpath, f"{dir_name}_osv_response.json")
                if not os.path.exists(osv_file):
                    failed_libraries.append({
                        "name": dir_name,
                        "path": os.path.abspath(dirpath)
                    })
    
    return failed_libraries

def find_git_info_files(root_dir):
    """Recursively find all Git info files in the directory tree."""
    return list(Path(root_dir).rglob("*_git_info.json"))

def find_no_git_files(root_dir):
    """Recursively find all no-git-info files in the directory tree."""
    return list(Path(root_dir).rglob("*_no_git_info.json"))

def find_no_submodules_files(root_dir):
    """Recursively find all no-submodules-info files in the directory tree."""
    return list(Path(root_dir).rglob("*_no_submodules_info.json"))

def find_third_party_dirs(root_dir):
    """Find all third-party package directories in the given root directory."""
    third_party_dirs = []
    
    # First check immediate subdirectories
    for item in os.listdir(root_dir):
        item_path = os.path.join(root_dir, item)
        if os.path.isdir(item_path) and item.lower() in THIRD_PARTY_DIRS:
            third_party_dirs.append(item_path)
            logger.info(f"Found third-party directory: {item_path}")
    
    # Then recursively search for these directories
    for dirpath, dirnames, _ in os.walk(root_dir):
        for dirname in dirnames:
            if dirname.lower() in THIRD_PARTY_DIRS:
                full_path = os.path.join(dirpath, dirname)
                if full_path not in third_party_dirs:  # Avoid duplicates
                    third_party_dirs.append(full_path)
                    logger.info(f"Found third-party directory: {full_path}")
    
    return third_party_dirs

def process_third_party_dirs(root_dir, debug=False):
    """Process all found third-party directories."""
    third_party_dirs = find_third_party_dirs(root_dir)
    
    if not third_party_dirs:
        logger.warning(f"No third-party directories found in {root_dir}")
        return
    
    logger.info(f"Found {len(third_party_dirs)} third-party directories to process")
    
    for dir_path in third_party_dirs:
        logger.info(f"\nProcessing third-party directory: {dir_path}")
        process_all_directories(dir_path, debug)

def generate_markdown_report(root_dir, output_file="dependency_report.md"):
    """Generate a markdown report of dependencies and their versions."""
    osv_files = find_osv_response_files(root_dir)
    failed_libraries = find_failed_libraries(root_dir)
    git_files = find_git_info_files(root_dir)
    no_git_files = find_no_git_files(root_dir)
    no_submodules_files = find_no_submodules_files(root_dir)
    
    if not any([osv_files, failed_libraries, git_files, no_git_files, no_submodules_files]):
        logger.error(f"No relevant files found in {root_dir} or its subdirectories")
        return
    
    logger.info(f"Found {len(osv_files)} OSV response files, {len(failed_libraries)} failed libraries, "
                f"{len(git_files)} Git info files, {len(no_git_files)} no-git files, "
                f"and {len(no_submodules_files)} no-submodules files")
    
    # Get absolute path for the report file
    report_path = os.path.abspath(os.path.join(root_dir, output_file))
    logger.info(f"Generating report at: {report_path}")
    
    markdown = ["# Dependency Report\n"]
    
    # Add successful libraries section (from OSV API)
    if osv_files:
        markdown.append("## Successfully Processed Libraries (OSV API)\n")
        markdown.append("| Library | Version | Score | Repository | Tag | File Matches | Different Files |")
        markdown.append("|---------|---------|-------|------------|-----|--------------|-----------------|")
        
        for osv_file in osv_files:
            try:
                with open(osv_file, 'r') as f:
                    osv_response = json.load(f)
                
                # Get library name from the directory path
                library_name = get_library_name(osv_file)
                top_versions = get_top_versions(osv_response)
                
                for version in top_versions:
                    markdown.append(
                        f"| {library_name} | {version['version']} | {version['score']} | "
                        f"{version['repository']} | {version['tag']} | {version['file_matches']} | "
                        f"{version['diff_files']} |"
                    )
            except Exception as e:
                logger.error(f"Error processing {osv_file}: {str(e)}")
    
    # Add Git submodule information section
    if git_files:
        markdown.append("\n## Library Versions from Git Submodules\n")
        markdown.append("| Library | Submodule Path | Commit | Tag | Repository |")
        markdown.append("|---------|---------------|--------|-----|------------|")
        
        for git_file in git_files:
            try:
                with open(git_file, 'r') as f:
                    git_info = json.load(f)
                
                library_name = git_info["name"]
                for submodule in git_info["submodules"]:
                    markdown.append(
                        f"| {library_name} | {submodule['path']} | {submodule['commit'][:8]} | "
                        f"{submodule['tag']} | {submodule['repository']} |"
                    )
            except Exception as e:
                logger.error(f"Error processing {git_file}: {str(e)}")
    
    # Add no Git repository section
    if no_git_files:
        markdown.append("\n## Libraries Without Git Repository\n")
        markdown.append("| Library | Path | Reason |")
        markdown.append("|---------|------|--------|")
        
        for no_git_file in no_git_files:
            try:
                with open(no_git_file, 'r') as f:
                    no_git_info = json.load(f)
                markdown.append(f"| {no_git_info['name']} | {no_git_info['path']} | {no_git_info['reason']} |")
            except Exception as e:
                logger.error(f"Error processing {no_git_file}: {str(e)}")
    
    # Add no submodules section
    if no_submodules_files:
        markdown.append("\n## Git Repositories Without Submodules\n")
        markdown.append("| Library | Path | Reason |")
        markdown.append("|---------|------|--------|")
        
        for no_submodules_file in no_submodules_files:
            try:
                with open(no_submodules_file, 'r') as f:
                    no_submodules_info = json.load(f)
                markdown.append(f"| {no_submodules_info['name']} | {no_submodules_info['path']} | {no_submodules_info['reason']} |")
            except Exception as e:
                logger.error(f"Error processing {no_submodules_file}: {str(e)}")
    
    # Add failed libraries section
    if failed_libraries:
        markdown.append("\n## Failed Libraries\n")
        markdown.append("| Library | Path |")
        markdown.append("|---------|------|")
        
        for lib in failed_libraries:
            markdown.append(f"| {lib['name']} | {lib['path']} |")
    
    # Print report to console
    logger.info("\nDependency Report:")
    logger.info("=" * 80)
    print('\n'.join(markdown))
    logger.info("=" * 80)
    
    # Write report to file
    with open(report_path, 'w') as f:
        f.write('\n'.join(markdown))
    
    logger.info(f"Report generated successfully at: {report_path}")

def main():
    parser = argparse.ArgumentParser(description='Generate a dependency report from OSV API responses.')
    parser.add_argument('root_dir', help='Root directory containing OSV response files')
    parser.add_argument('--output', default='dependency_report.md', help='Output markdown file name')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help='Set the logging level')
    parser.add_argument('--auto-detect', action='store_true', 
                       help='Automatically detect and process third-party directories')
    args = parser.parse_args()
    
    # Set logging level
    logger.setLevel(getattr(logging, args.log_level))
    
    if args.auto_detect:
        # Process all detected third-party directories
        logger.info("Auto-detecting third-party directories...")
        process_third_party_dirs(args.root_dir, args.debug)
    else:
        # Process the specified directory
        logger.info(f"Processing directory: {args.root_dir}")
        process_all_directories(args.root_dir, args.debug)
    
    # Generate the report
    logger.info("Generating dependency report...")
    generate_markdown_report(args.root_dir, args.output)

if __name__ == "__main__":
    main() 
