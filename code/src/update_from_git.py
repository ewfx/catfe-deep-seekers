#!/usr/bin/env python
"""
Update BDD test cases and summaries based on Git changes.

This script fetches the latest commit from the remote repository, detects changes,
and only updates the feature files for endpoints that have been added or modified.
It leverages the API flow data to detect endpoint changes rather than parsing Java files.
"""

import subprocess
import sys
import logging
import json
import os
import git
import shutil
import re
import copy
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Define constants
API_FLOW_BACKUP_FILE = "code_index/api_flow_backup.json"
API_FLOW_FILE = "code_index/api_flow.json"

def load_config():
    """Load configuration from config.json"""
    try:
        with open("config.json", "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error("config.json not found")
        return {}
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding config.json: {e}")
        return {}

def pull_latest_changes(repo_dir):
    """Pull the latest changes from the remote repository."""
    logging.info(f"Pulling latest changes from remote repository to {repo_dir}...")
    try:
        repo = git.Repo(repo_dir)
        remote = repo.remote()
        remote.pull()
        logging.info(f"Successfully pulled latest changes. New HEAD: {repo.head.commit.hexsha}")
        return repo.head.commit.hexsha
    except Exception as e:
        logging.error(f"Error pulling latest changes: {e}")
        return None

def backup_api_flow():
    """Make a backup of the current API flow file."""
    if not os.path.exists(API_FLOW_FILE):
        logging.warning(f"API flow file not found: {API_FLOW_FILE}")
        return False
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(API_FLOW_BACKUP_FILE), exist_ok=True)
    
    try:
        # Copy the current API flow file to the backup
        shutil.copy2(API_FLOW_FILE, API_FLOW_BACKUP_FILE)
        logging.info(f"Successfully backed up API flow to {API_FLOW_BACKUP_FILE}")
        return True
    except Exception as e:
        logging.error(f"Error backing up API flow: {e}")
        return False

def load_api_flow(file_path):
    """Load API flow data from the given file."""
    try:
        if not os.path.exists(file_path):
            logging.warning(f"API flow file not found: {file_path}")
            return {}
        
        with open(file_path, 'r', encoding='utf-8') as f:
            api_flow = json.load(f)
        
        logging.info(f"Successfully loaded API flow from {file_path}")
        return api_flow
    except Exception as e:
        logging.error(f"Error loading API flow from {file_path}: {e}")
        return {}

def identify_changed_endpoints(old_api_flow, new_api_flow):
    """Identify endpoints that have been added or modified based on API flow data."""
    changed_endpoints = []
    
    # Check for new or modified endpoints
    for path, new_data in new_api_flow.items():
        if path not in old_api_flow:
            # This is a completely new path
            logging.info(f"New API path detected: {path}")
            for endpoint in new_data.get("endpoints", []):
                http_method = endpoint.get("http_method", "GET")
                changed_endpoints.append((http_method, path))
                logging.info(f"Added new endpoint: {http_method} {path}")
        else:
            # Path exists, check if endpoints are new or modified
            old_endpoints = {(e.get("http_method", "GET"), e.get("method", "")): e 
                            for e in old_api_flow[path].get("endpoints", [])}
            
            for new_endpoint in new_data.get("endpoints", []):
                http_method = new_endpoint.get("http_method", "GET")
                method_name = new_endpoint.get("method", "")
                key = (http_method, method_name)
                
                if key not in old_endpoints:
                    # New endpoint method in existing path
                    changed_endpoints.append((http_method, path))
                    logging.info(f"Added new endpoint method: {http_method} {path}")
                else:
                    # Compare endpoint details to detect changes
                    old_endpoint = old_endpoints[key]
                    # Check for changes in controller class, parameters, or other attributes
                    if (new_endpoint.get("class", "") != old_endpoint.get("class", "") or
                        new_endpoint.get("parameters", []) != old_endpoint.get("parameters", [])):
                        changed_endpoints.append((http_method, path))
                        logging.info(f"Modified endpoint: {http_method} {path}")
    
    # Deduplicate the list of changed endpoints
    unique_endpoints = list(set(changed_endpoints))
    logging.info(f"Found {len(unique_endpoints)} changed or new endpoints")
    return unique_endpoints

def identify_deleted_endpoints(old_api_flow, new_api_flow):
    """Identify endpoints that have been deleted based on API flow data."""
    deleted_endpoints = []
    
    # Check for deleted paths
    for path, old_data in old_api_flow.items():
        if path not in new_api_flow:
            # This path has been completely removed
            logging.info(f"Deleted API path detected: {path}")
            for endpoint in old_data.get("endpoints", []):
                http_method = endpoint.get("http_method", "GET")
                deleted_endpoints.append((http_method, path))
                logging.info(f"Removed endpoint: {http_method} {path}")
        else:
            # Path exists, check if endpoints were removed
            new_endpoints = {(e.get("http_method", "GET"), e.get("method", "")) 
                            for e in new_api_flow[path].get("endpoints", [])}
            
            for old_endpoint in old_data.get("endpoints", []):
                http_method = old_endpoint.get("http_method", "GET")
                method_name = old_endpoint.get("method", "")
                key = (http_method, method_name)
                
                if key not in new_endpoints:
                    # This endpoint method was removed
                    deleted_endpoints.append((http_method, path))
                    logging.info(f"Removed endpoint method: {http_method} {path}")
    
    # Deduplicate the list of deleted endpoints
    unique_deleted = list(set(deleted_endpoints))
    logging.info(f"Found {len(unique_deleted)} deleted endpoints")
    return unique_deleted

def normalize_endpoint_path(endpoint_path):
    """Normalize an endpoint path for feature file naming."""
    # Remove leading/trailing slashes
    path = endpoint_path.strip('/')
    
    # Replace slashes with underscores
    path = path.replace('/', '_')
    
    # Handle typical prefixes like api/v1
    if path.startswith('api_v1_'):
        path = path[7:]  # Remove 'api_v1_' prefix
    
    return path

def find_existing_feature_file(bdd_dir, http_method, endpoint_path):
    """Find an existing feature file that matches the endpoint."""
    normalized_path = normalize_endpoint_path(endpoint_path)
    
    # Common filename patterns
    patterns = [
        f"{http_method.upper()}_{normalized_path}.feature",
        f"{http_method.lower()}_{normalized_path}.feature",
        f"{normalized_path}.feature"
    ]
    
    # Also look for the last part of the path
    last_part = normalized_path.split('_')[-1]
    patterns.append(f"{http_method.upper()}_{last_part}.feature")
    patterns.append(f"{last_part}.feature")
    
    logging.info(f"Looking for existing feature file for {http_method} {endpoint_path}")
    logging.info(f"Checking patterns: {patterns}")
    
    # Search for matching files
    for root, _, files in os.walk(bdd_dir):
        for file in files:
            if file.endswith('.feature'):
                file_lower = file.lower()
                if any(pattern.lower() in file_lower for pattern in patterns):
                    feature_file = os.path.join(root, file)
                    logging.info(f"Found matching feature file: {feature_file}")
                    return feature_file
    
    logging.info(f"No existing feature file found for {http_method} {endpoint_path}")
    return None

def generate_or_update_feature_file(bdd_dir, http_method, endpoint_path):
    """Generate a new feature file or update an existing one for the given endpoint."""
    # Check if a feature file already exists
    existing_file = find_existing_feature_file(bdd_dir, http_method, endpoint_path)
    
    if existing_file:
        # Update existing file
        return update_feature_file(existing_file, http_method, endpoint_path)
    else:
        # Generate new file
        return generate_new_feature_file(bdd_dir, http_method, endpoint_path)

def generate_new_feature_file(bdd_dir, http_method, endpoint_path):
    """Generate a new feature file for the given endpoint."""
    try:
        # Create a normalized filename
        normalized_path = normalize_endpoint_path(endpoint_path)
        feature_filename = f"{http_method.upper()}_{normalized_path}.feature"
        
        # Use the root BDD directory for all new feature files
        feature_file = os.path.join(bdd_dir, feature_filename)
        
        logging.info(f"Generating new feature file: {feature_file}")
        
        # Call generate_artifacts.py with a temporary script
        temp_script = """
import sys
import os
import json
import logging
from generate_artifacts import read_prompt_file, call_openai_api

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def generate_feature_file(feature_file, http_method, endpoint_path):
    \"\"\"Generate a new feature file for an endpoint.\"\"\"
    # Get the BDD test case template
    bdd_template = read_prompt_file("BDD Test Case Template.md")
    if not bdd_template:
        logging.error("Failed to read BDD test case template.")
        return False
    
    # Extract endpoint information from API flow data
    api_flow_file = os.path.join("code_index", "api_flow.json")
    endpoint_info = {
        "path": endpoint_path,
        "method": http_method,
        "controller": "",
        "controller_method": "",
        "service_calls": []
    }
    
    # Get more detailed information from the API flow file
    if os.path.exists(api_flow_file):
        try:
            with open(api_flow_file, 'r', encoding='utf-8') as f:
                api_flow_data = json.load(f)
            
            if endpoint_path in api_flow_data:
                endpoint_data = api_flow_data[endpoint_path]
                # Find the specific endpoint method
                for endpoint in endpoint_data.get("endpoints", []):
                    if endpoint.get("http_method", "").upper() == http_method.upper():
                        endpoint_info = {
                            "path": endpoint_path,
                            "method": http_method,
                            "controller": endpoint.get("class", ""),
                            "controller_method": endpoint.get("method", ""),
                            "parameters": endpoint.get("parameters", []),
                            "service_calls": endpoint_data.get("service_calls", [])
                        }
                        break
        except Exception as e:
            logging.error(f"Error reading API flow data: {e}")
    
    # Prepare the prompt with endpoint information
    prompt = f"{bdd_template}\\n\\nAPI Endpoint Information:\\n```json\\n{json.dumps(endpoint_info, indent=2)}\\n```"
    
    # Call OpenAI API to generate test cases
    test_cases = call_openai_api(prompt)
    if not test_cases:
        logging.error(f"Failed to generate BDD test cases for endpoint: {endpoint_path}")
        return False
    
    # Make sure directory exists
    os.makedirs(os.path.dirname(os.path.abspath(feature_file)), exist_ok=True)
    
    # Write the new feature file
    with open(feature_file, 'w', encoding='utf-8') as f:
        f.write(f"# BDD Test Cases for {http_method} {endpoint_path}\\n\\n")
        f.write(test_cases)
    
    logging.info(f"Successfully generated feature file: {feature_file}")
    return True

# Main script
if __name__ == "__main__":
    feature_file = sys.argv[1]
    http_method = sys.argv[2]
    endpoint_path = sys.argv[3]
    
    success = generate_feature_file(feature_file, http_method, endpoint_path)
    sys.exit(0 if success else 1)
"""
        # Write the temporary script
        temp_script_file = "temp_generate_feature.py"
        with open(temp_script_file, 'w', encoding='utf-8') as f:
            f.write(temp_script)
        
        # Run the script
        cmd = [
            sys.executable,
            temp_script_file,
            feature_file,
            http_method,
            endpoint_path
        ]
        
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        # Clean up
        os.remove(temp_script_file)
        
        if result.stdout:
            logging.info(f"Generation output: {result.stdout}")
        
        if result.stderr:
            logging.warning(f"Generation warnings: {result.stderr}")
        
        if os.path.exists(feature_file):
            logging.info(f"Successfully generated new feature file: {feature_file}")
            return feature_file
        else:
            logging.error(f"Failed to generate feature file: {feature_file}")
            return None
            
    except Exception as e:
        logging.error(f"Error generating feature file: {e}")
        return None

def update_feature_file(feature_file, http_method, endpoint_path):
    """Update an existing feature file with new content."""
    try:
        # Create a backup of the original file
        backup_file = feature_file + f".bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
        shutil.copy2(feature_file, backup_file)
        logging.info(f"Backed up feature file to: {backup_file}")
        
        # Similar to generating a new file, but with backup/restore logic
        temp_script = """
import sys
import os
import json
import logging
from generate_artifacts import read_prompt_file, call_openai_api

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def update_feature_file(feature_file, http_method, endpoint_path):
    \"\"\"Update an existing feature file with new content.\"\"\"
    # Get the BDD test case template
    bdd_template = read_prompt_file("BDD Test Case Template.md")
    if not bdd_template:
        logging.error("Failed to read BDD test case template.")
        return False
    
    # Extract endpoint information from API flow data
    api_flow_file = os.path.join("code_index", "api_flow.json")
    endpoint_info = {
        "path": endpoint_path,
        "method": http_method,
        "controller": "",
        "controller_method": "",
        "service_calls": []
    }
    
    # Get more detailed information from the API flow file
    if os.path.exists(api_flow_file):
        try:
            with open(api_flow_file, 'r', encoding='utf-8') as f:
                api_flow_data = json.load(f)
            
            if endpoint_path in api_flow_data:
                endpoint_data = api_flow_data[endpoint_path]
                # Find the specific endpoint method
                for endpoint in endpoint_data.get("endpoints", []):
                    if endpoint.get("http_method", "").upper() == http_method.upper():
                        endpoint_info = {
                            "path": endpoint_path,
                            "method": http_method,
                            "controller": endpoint.get("class", ""),
                            "controller_method": endpoint.get("method", ""),
                            "parameters": endpoint.get("parameters", []),
                            "service_calls": endpoint_data.get("service_calls", [])
                        }
                        break
        except Exception as e:
            logging.error(f"Error reading API flow data: {e}")
    
    # Prepare the prompt with endpoint information
    prompt = f"{bdd_template}\\n\\nAPI Endpoint Information:\\n```json\\n{json.dumps(endpoint_info, indent=2)}\\n```"
    
    # Call OpenAI API to generate test cases
    test_cases = call_openai_api(prompt)
    if not test_cases:
        logging.error(f"Failed to generate BDD test cases for endpoint: {endpoint_path}")
        return False
    
    # Write the updated feature file
    with open(feature_file, 'w', encoding='utf-8') as f:
        f.write(f"# BDD Test Cases for {http_method} {endpoint_path}\\n\\n")
        f.write(test_cases)
    
    logging.info(f"Successfully updated feature file: {feature_file}")
    return True

# Main script
if __name__ == "__main__":
    feature_file = sys.argv[1]
    http_method = sys.argv[2]
    endpoint_path = sys.argv[3]
    
    success = update_feature_file(feature_file, http_method, endpoint_path)
    sys.exit(0 if success else 1)
"""
        # Write the temporary script
        temp_script_file = "temp_update_feature.py"
        with open(temp_script_file, 'w', encoding='utf-8') as f:
            f.write(temp_script)
        
        # Run the script
        cmd = [
            sys.executable,
            temp_script_file,
            feature_file,
            http_method,
            endpoint_path
        ]
        
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            # Clean up
            os.remove(temp_script_file)
            
            if result.stdout:
                logging.info(f"Update output: {result.stdout}")
            
            if result.stderr:
                logging.warning(f"Update warnings: {result.stderr}")
            
            logging.info(f"Successfully updated feature file: {feature_file}")
            return feature_file
            
        except subprocess.CalledProcessError as e:
            logging.error(f"Error updating feature file: {e}")
            logging.error(f"STDOUT: {e.stdout}")
            logging.error(f"STDERR: {e.stderr}")
            
            # Restore the backup
            shutil.copy2(backup_file, feature_file)
            logging.info(f"Restored feature file from backup: {backup_file}")
            
            # Clean up
            if os.path.exists(temp_script_file):
                os.remove(temp_script_file)
                
            return None
        
    except Exception as e:
        logging.error(f"Error updating feature file: {e}")
        return None

def update_feature_files_for_endpoints(bdd_dir, changed_endpoints):
    """Generate or update feature files for all changed endpoints."""
    updated_files = []
    failed_endpoints = []
    
    for http_method, endpoint_path in changed_endpoints:
        logging.info(f"Processing endpoint: {http_method} {endpoint_path}")
        result = generate_or_update_feature_file(bdd_dir, http_method, endpoint_path)
        
        if result:
            updated_files.append(result)
        else:
            failed_endpoints.append((http_method, endpoint_path))
    
    # Report results
    logging.info(f"Successfully processed {len(updated_files)} feature files")
    if failed_endpoints:
        logging.warning(f"Failed to process {len(failed_endpoints)} endpoints:")
        for method, path in failed_endpoints:
            logging.warning(f"  - {method} {path}")
    
    return updated_files, failed_endpoints

def handle_deleted_endpoints(bdd_dir, deleted_endpoints):
    """Handle feature files for deleted endpoints (either archive or mark as deprecated)."""
    archived_files = []
    
    for http_method, endpoint_path in deleted_endpoints:
        # Find feature files for this endpoint
        feature_file = find_existing_feature_file(bdd_dir, http_method, endpoint_path)
        
        if feature_file:
            # Create an archive directory
            archive_dir = os.path.join(bdd_dir, "archived")
            os.makedirs(archive_dir, exist_ok=True)
            
            # Archive the feature file
            archive_file = os.path.join(archive_dir, os.path.basename(feature_file))
            try:
                # Copy the file to archive
                shutil.copy2(feature_file, archive_file)
                
                # Mark the original file as deprecated by adding a note
                with open(feature_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                with open(feature_file, 'w', encoding='utf-8') as f:
                    f.write(f"# DEPRECATED - This endpoint was removed at {datetime.now()}\n")
                    f.write(f"# Endpoint: {http_method} {endpoint_path}\n\n")
                    f.write(content)
                
                archived_files.append(feature_file)
                logging.info(f"Marked file as deprecated: {feature_file}")
                
            except Exception as e:
                logging.error(f"Error handling deleted endpoint file {feature_file}: {e}")
    
    logging.info(f"Processed {len(archived_files)} files for deleted endpoints")
    return archived_files

def safe_remove_directory(directory):
    """Safely remove a directory even if it has read-only files (Windows issue)."""
    if not os.path.exists(directory):
        return True
        
    logging.info(f"Safely removing directory: {directory}")
    
    try:
        # First attempt - normal removal
        shutil.rmtree(directory)
        return True
    except PermissionError as e:
        logging.warning(f"Permission error when removing directory: {e}")
        
        try:
            # On Windows, try setting files to writeable first
            for root, dirs, files in os.walk(directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        # Make the file writeable
                        os.chmod(file_path, 0o666)
                    except:
                        pass
            
            # Try removal again
            shutil.rmtree(directory)
            return True
        except Exception as e2:
            logging.warning(f"Still unable to remove directory: {e2}")
            
            # As a last resort, try using OS-specific commands
            if os.name == 'nt':  # Windows
                try:
                    # Use RD /S /Q which is more forceful on Windows
                    subprocess.run(["cmd", "/c", f"rd /s /q {directory}"], check=False, capture_output=True)
                    if not os.path.exists(directory):
                        return True
                except Exception as e3:
                    logging.error(f"Failed to remove directory using cmd: {e3}")
            else:  # Unix-like
                try:
                    # Use rm -rf which is more forceful on Unix
                    subprocess.run(["rm", "-rf", directory], check=False, capture_output=True)
                    if not os.path.exists(directory):
                        return True
                except Exception as e3:
                    logging.error(f"Failed to remove directory using rm: {e3}")
    
    # If we're here, all attempts failed
    if os.path.exists(directory):
        logging.error(f"Failed to remove directory: {directory}")
        return False
    return True

def main():
    """Main function to update BDD tests based on API flow changes."""
    logging.info("Starting update process based on commit changes and API flow comparison...")
    
    # Load configuration
    config = load_config()
    clone_dir = config.get("clone_dir", "clonned_repo")
    bdd_dir = os.path.join("summary", "bdd_test_cases")
    
    # Backup the current API flow before making any changes
    if os.path.exists(API_FLOW_FILE):
        backup_api_flow()
        logging.info("Backed up current API flow data")
    
    # Always force clone the repository
    logging.info("Force cloning the repository to ensure latest state...")
    try:
        # Remove existing clone directory if it exists
        if os.path.exists(clone_dir):
            logging.info(f"Removing existing clone directory: {clone_dir}")
            if not safe_remove_directory(clone_dir):
                logging.warning("Could not fully remove directory. Proceeding with caution.")
        
        # Force clone with generate_artifacts.py
        result = subprocess.run(
            ["python", "generate_artifacts.py", "--force-clone", "--llm-optimizations"],
            check=True,
            capture_output=True,
            text=True
        )
        logging.info("Repository force cloned successfully")
    except Exception as e:
        logging.error(f"Error force cloning repository: {e}")
        if hasattr(e, 'stdout'):
            logging.error(f"STDOUT: {e.stdout}")
        if hasattr(e, 'stderr'):
            logging.error(f"STDERR: {e.stderr}")
        return 1
    
    # Generate fresh API flow data
    logging.info("Generating fresh API flow data...")
    try:
        result = subprocess.run(
            ["python", "generate_artifacts.py", "--update-only", "--llm-optimizations"],
            check=True,
            capture_output=True,
            text=True
        )
        logging.info("API flow data regenerated successfully")
    except Exception as e:
        logging.error(f"Error regenerating API flow data: {e}")
        return 1
    
    # Load the backed up API flow (pre-update)
    old_api_flow = load_api_flow(API_FLOW_BACKUP_FILE)
    
    # Load the current API flow (post-update)
    new_api_flow = load_api_flow(API_FLOW_FILE)
    
    if not old_api_flow and not new_api_flow:
        logging.warning("Both old and new API flow data are empty. Nothing to update.")
        return 0
    
    if not old_api_flow:
        logging.warning("No previous API flow data. All endpoints will be treated as new.")
        # Create empty old_api_flow to proceed
        old_api_flow = {}
    
    if not new_api_flow:
        logging.error("Failed to generate new API flow data. Exiting.")
        return 1
    
    # Identify changed endpoints between old and new API flow
    changed_endpoints = identify_changed_endpoints(old_api_flow, new_api_flow)
    
    # Also identify deleted endpoints
    deleted_endpoints = identify_deleted_endpoints(old_api_flow, new_api_flow)
    
    if not changed_endpoints and not deleted_endpoints:
        logging.info("No endpoints have been changed or deleted. Nothing to update.")
        return 0
    
    # Generate or update feature files for changed endpoints
    updated_files, failed_endpoints = update_feature_files_for_endpoints(bdd_dir, changed_endpoints)
    
    # Report on deleted endpoints
    if deleted_endpoints:
        logging.info(f"Found {len(deleted_endpoints)} deleted endpoints:")
        for http_method, endpoint_path in deleted_endpoints:
            logging.info(f"  - {http_method} {endpoint_path}")
            
        # Handle deletion of feature files for removed endpoints
        handle_deleted_endpoints(bdd_dir, deleted_endpoints)
    
    # Final report
    if updated_files:
        logging.info(f"Updated {len(updated_files)} feature files:")
        for file in updated_files:
            logging.info(f"  - {file}")
    
    if failed_endpoints:
        logging.warning(f"Failed to update {len(failed_endpoints)} endpoints")
        return 1
    else:
        logging.info("Update completed successfully!")
        return 0

if __name__ == "__main__":
    sys.exit(main()) 
