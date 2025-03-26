import os
import json
import javalang
import git
import hashlib
import logging
import concurrent.futures
from tqdm import tqdm
from collections import defaultdict
import networkx as nx
import subprocess
import stat
import matplotlib.pyplot as plt
import pydot
from PIL import Image
import re
import openai
import time
from pathlib import Path
import argparse
import shutil

# Setup structured logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

INDEX_DIR = "code_index"
LAST_COMMIT_FILE = "last_commit.json"
CONFIG_FILE = "config.json"
GRAPH_FILE = "dependency_graph.dot"
INDEX_JSON = os.path.join(INDEX_DIR, "index.json")
API_FLOW_JSON = os.path.join(INDEX_DIR, "api_flow.json")
SEQUENCE_DIAGRAM_FILE = os.path.join(INDEX_DIR, "sequence_diagram.puml")

# Summary directories and files
SUMMARY_DIR = "summary"
FILE_SUMMARIES_DIR = os.path.join(SUMMARY_DIR, "file_summaries")
MODULE_SUMMARIES_DIR = os.path.join(SUMMARY_DIR, "module_summaries")
BDD_TEST_CASES_DIR = os.path.join(SUMMARY_DIR, "bdd_test_cases")
SUMMARY_OF_SUMMARIES_FILE = os.path.join(SUMMARY_DIR, "summary_of_summaries.md")
PROMPTS_DIR = "prompts"

# Common Java framework packages to filter out
EXTERNAL_PACKAGES = {
    'org.springframework', 'javax', 'java', 'org.hibernate', 'org.junit',
    'org.mockito', 'org.apache', 'com.fasterxml', 'io.swagger', 'lombok',
    'jakarta', 'org.slf4j', 'ch.qos.logback', 'org.json', 'com.google',
    'org.testng', 'junit', 'org.junit.jupiter', 'org.junit.jupiter.api'
}

# Spring Boot specific annotations
SPRING_ANNOTATIONS = {
    '@RestController', '@Controller', '@Service', '@Repository', '@Component',
    '@Autowired', '@Value', '@Configuration', '@Bean', '@RequestMapping',
    '@GetMapping', '@PostMapping', '@PutMapping', '@DeleteMapping', '@PatchMapping'
}

# Test-related keywords to filter out
TEST_KEYWORDS = {
    'Test', 'Tests', 'TestCase', 'TestSuite', 'IntegrationTest', 
    'UnitTest', 'Spec', 'Specification', 'IT', 'E2E'
}

def is_test_class(class_name, file_path):
    # Check if class name contains test keywords
    if any(keyword in class_name for keyword in TEST_KEYWORDS):
        return True
    
    # Check if file path contains test-related directories
    test_dirs = {'test', 'tests', 'testing', 'it', 'e2e'}
    path_parts = file_path.lower().split(os.sep)
    return any(test_dir in path_parts for test_dir in test_dirs)

def is_external_dependency(dependency):
    return any(dependency.startswith(pkg) for pkg in EXTERNAL_PACKAGES)

def get_package_name(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tree = javalang.parse.parse(f.read())
            for path, node in tree:
                if isinstance(node, javalang.tree.PackageDeclaration):
                    return node.name
    except:
        pass
    return "default"

def load_config():
    """Load configuration from config.json"""
    try:
        with open("config.json", "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except FileNotFoundError:
        logging.info("config.json not found, using default configuration")
        return {
            "repo_url": "https://github.com/pauldragoslav/Spring-boot-Banking",
            "clone_dir": "./clonned_repo"
        }
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding config.json: {e}")
        logging.info("Using default configuration")
        return {
            "repo_url": "https://github.com/pauldragoslav/Spring-boot-Banking",
            "clone_dir": "./clonned_repo"
        }


CONFIG = load_config()


def clone_repo(repo_url, clone_dir):
    try:
        if os.path.exists(clone_dir):
            # Check if it's a git repository
            if os.path.exists(os.path.join(clone_dir, '.git')):
                logging.info(f"Repository already exists at {clone_dir}. Skipping clone.")
                return
            else:
                logging.warning(f"Directory {clone_dir} exists but is not a git repository. Deleting and re-cloning...")
                import shutil
                shutil.rmtree(clone_dir)

        logging.info(f"Cloning repository {repo_url} into {clone_dir}...")
        git.Repo.clone_from(repo_url, clone_dir)
        logging.info("Repository cloned successfully!")

        # ✅ Ensure `cloned_repo/` has full read/write/execute permissions
        os.chmod(clone_dir, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)

        # ✅ Recursively set permissions for all files and directories
        for root, dirs, files in os.walk(clone_dir):
            for dir_name in dirs:
                os.chmod(os.path.join(root, dir_name), stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
            for file_name in files:
                os.chmod(os.path.join(root, file_name),
                         stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH)

        logging.info(f"Permissions set for {clone_dir} to allow read & write access.")

    except git.exc.GitError as e:
        logging.error(f"Error cloning repository: {e}")
    except Exception as e:
        logging.error(f"Unexpected error while setting permissions: {e}")


def initialize_index():
    os.makedirs(INDEX_DIR, exist_ok=True)
    if not os.path.exists(INDEX_JSON) or os.stat(INDEX_JSON).st_size == 0:
        logging.warning(f"{INDEX_JSON} was missing or empty. Initializing with an empty dictionary.")
        save_to_file(INDEX_JSON, {})


def save_to_file(file_name, data):
    # ✅ Fix: Avoid duplicate paths
    file_path = file_name if os.path.isabs(file_name) else os.path.join(INDEX_DIR, os.path.basename(file_name))

    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)  # ✅ Ensure directory exists
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        logging.info(f"File saved: {file_path}")  # ✅ Log file path
    except IOError as e:
        logging.error(f"Error saving to file {file_path}: {e}")


def load_from_file(file_name):
    # ✅ Fix: Ensure correct file path
    file_path = file_name if os.path.isabs(file_name) else os.path.join(INDEX_DIR, os.path.basename(file_name))

    try:
        if os.path.exists(file_path):
            if os.stat(file_path).st_size == 0:  # ✅ Handle empty files
                logging.warning(f"File {file_path} is empty. Returning empty dictionary.")
                return {}
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            logging.warning(f"File {file_path} does not exist. Returning empty dictionary.")
    except (IOError, json.JSONDecodeError) as e:
        logging.error(f"Error loading file {file_path}: {e}")
    return {}


def extract_api_endpoints(tree):
    endpoints = []
    for path, node in tree:
        if isinstance(node, javalang.tree.ClassDeclaration):
            class_annotations = [ann.name for ann in node.annotations]
            base_path = ""
            
            # Check for @RequestMapping at class level
            for ann in node.annotations:
                if ann.name == 'RequestMapping':
                    if hasattr(ann, 'element') and ann.element:
                        for elem in ann.element:
                            if isinstance(elem, tuple) and len(elem) == 2:
                                name, value = elem
                                if name == 'value':
                                    base_path = value.value.strip('"')
                                    break
            
            # Check for @RestController or @Controller
            if any(ann in class_annotations for ann in ['RestController', 'Controller']):
                for member in node.body:
                    if isinstance(member, javalang.tree.MethodDeclaration):
                        method_annotations = [ann.name for ann in member.annotations]
                        http_method = None
                        path = ""
                        
                        # Check for HTTP method annotations
                        for ann in member.annotations:
                            if ann.name in ['GetMapping', 'PostMapping', 'PutMapping', 'DeleteMapping', 'PatchMapping']:
                                http_method = ann.name.replace('Mapping', '').upper()
                                if hasattr(ann, 'element') and ann.element:
                                    for elem in ann.element:
                                        if isinstance(elem, tuple) and len(elem) == 2:
                                            name, value = elem
                                            if name == 'value':
                                                path = value.value.strip('"')
                                                break
                                break
                        
                        if http_method:
                            full_path = f"{base_path}/{path}".replace("//", "/")
                            endpoints.append({
                                "method": http_method,
                                "path": full_path,
                                "class": node.name,
                                "method_name": member.name,
                                "line_number": member.position.line
                            })
    return endpoints

def extract_api_flow(tree, file_path):
    """Extract API flow including service and repository dependencies."""
    api_flow = {
        "endpoints": [],
        "service_calls": [],
        "repository_calls": []
    }
    
    current_class = None
    current_method = None
    
    # Read the file content to extract annotation values directly
    with open(file_path, 'r', encoding='utf-8') as f:
        file_content = f.read()
    
    for path, node in tree:
        if isinstance(node, javalang.tree.ClassDeclaration):
            current_class = node.name
            class_annotations = [ann.name for ann in node.annotations]
            
            # Check for Spring annotations
            is_controller = any(ann in class_annotations for ann in ['RestController', 'Controller'])
            is_service = any(ann in class_annotations for ann in ['Service'])
            is_repository = any(ann in class_annotations for ann in ['Repository'])
            
            base_path = ""
            for ann in node.annotations:
                if ann.name == 'RequestMapping':
                    if hasattr(ann, 'element') and ann.element:
                        for elem in ann.element:
                            if isinstance(elem, tuple) and len(elem) == 2:
                                name, value = elem
                                if name == 'value':
                                    base_path = value.value.strip('"')
                                    break
            
            if is_controller:
                for member in node.body:
                    if isinstance(member, javalang.tree.MethodDeclaration):
                        current_method = member.name
                        method_annotations = [ann.name for ann in member.annotations]
                        http_method = None
                        endpoint_path = ""
                        
                        # Check for HTTP method annotations
                        for ann in member.annotations:
                            if ann.name in ['GetMapping', 'PostMapping', 'PutMapping', 'DeleteMapping', 'PatchMapping']:
                                http_method = ann.name.replace('Mapping', '').upper()
                                
                                # Extract path using regex
                                if member.position:
                                    line_number = member.position.line
                                    # Get a few lines before the method declaration to find the annotation
                                    lines = file_content.split('\n')
                                    for i in range(max(0, line_number - 10), line_number):
                                        if ann.name in lines[i]:
                                            # Extract path from annotation
                                            match = re.search(r'value\s*=\s*"([^"]*)"', lines[i])
                                            if match:
                                                endpoint_path = match.group(1)
                                            break
                                break
                        
                        if http_method:
                            api_flow["endpoints"].append({
                                "method": current_method,
                                "path": endpoint_path,
                                "class": current_class,
                                "line_number": member.position.line,
                                "http_method": http_method
                            })
            
            # Track service and repository dependencies
            for member in node.body:
                if isinstance(member, javalang.tree.FieldDeclaration):
                    for var in member.declarators:
                        field_type = member.type.name
                        if 'Service' in field_type:
                            api_flow["service_calls"].append({
                                "class": current_class,
                                "service": field_type,
                                "field": var.name
                            })
                        elif 'Repository' in field_type:
                            api_flow["repository_calls"].append({
                                "class": current_class,
                                "repository": field_type,
                                "field": var.name
                            })
    
    return api_flow

def parse_java_file(file_path):
    logging.info(f"Parsing Java file: {file_path}")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tree = javalang.parse.parse(f.read())
    except (javalang.parser.JavaSyntaxError, FileNotFoundError, IOError) as e:
        error_message = f"Error parsing Java file {file_path}: {e}"
        logging.error(error_message)
        return error_message

    index_data = load_from_file(INDEX_JSON)
    package_name = get_package_name(file_path)

    parsed_data = {
        "package": package_name,
        "classes": [], 
        "methods": [], 
        "fields": [], 
        "dependencies": [],
        "call_graph": [], 
        "inheritance": [], 
        "annotations": [], 
        "references": [],
        "api_flow": extract_api_flow(tree, file_path)
    }

    for path, node in tree:
        if isinstance(node, javalang.tree.ClassDeclaration):
            if not is_test_class(node.name, file_path):
                parsed_data["classes"].append({
                    "name": node.name,
                    "line_number": node.position.line,
                    "package": package_name,
                    "annotations": [ann.name for ann in node.annotations]
                })
        elif isinstance(node, javalang.tree.MethodDeclaration):
            if not any(keyword in node.name for keyword in TEST_KEYWORDS):
                parsed_data["methods"].append({
                    "name": node.name,
                    "line_number": node.position.line,
                    "annotations": [ann.name for ann in node.annotations]
                })
        elif isinstance(node, javalang.tree.Import):
            if not is_external_dependency(node.path):
                parsed_data["dependencies"].append(node.path)

    index_data[file_path] = parsed_data
    save_to_file(INDEX_JSON, index_data)

    # Save API flow data
    api_flow_data = load_from_file(API_FLOW_JSON)
    # Clear existing data to avoid duplicates
    api_flow_data = {}

    # Group endpoints by their full path
    for file_path, data in index_data.items():
        for endpoint in data.get("api_flow", {}).get("endpoints", []):
            base_path = ""
            # Find the base path from class annotations
            for class_info in data.get("classes", []):
                if class_info["name"] == endpoint["class"]:
                    for ann in class_info.get("annotations", []):
                        if "RequestMapping" in ann:
                            # Extract base path from RequestMapping
                            # This is a simplification - in a real implementation, you'd need to parse the annotation value
                            base_path = "api/v1"  # Default for this project
                            break
            
            full_path = f"{base_path}/{endpoint['path']}".replace("//", "/")
            
            if full_path not in api_flow_data:
                api_flow_data[full_path] = {
                    "endpoints": [],
                    "service_calls": []
                }
            
            api_flow_data[full_path]["endpoints"].append({
                "method": endpoint["method"],
                "path": endpoint["path"],
                "class": endpoint["class"],
                "line_number": endpoint["line_number"],
                "http_method": endpoint.get("http_method", "")
            })
            
            # Add service calls for this endpoint's controller
            for service_call in data.get("api_flow", {}).get("service_calls", []):
                if service_call["class"] == endpoint["class"]:
                    # Check if this service call is already added
                    service_already_added = False
                    for existing_service in api_flow_data[full_path].get("service_calls", []):
                        if (existing_service["class"] == service_call["class"] and 
                            existing_service["service"] == service_call["service"] and
                            existing_service["field"] == service_call["field"]):
                            service_already_added = True
                            break
                    
                    if not service_already_added:
                        api_flow_data[full_path]["service_calls"].append(service_call)

    save_to_file(API_FLOW_JSON, api_flow_data)

    return f"Successfully parsed {file_path}"


def load_last_commit():
    """Load the last processed commit hash."""
    last_commit_path = os.path.join(INDEX_DIR, LAST_COMMIT_FILE)
    if os.path.exists(last_commit_path):
        try:
            with open(last_commit_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('commit_hash', '')
        except json.JSONDecodeError:
            logging.warning(f"Error parsing {last_commit_path}. Starting with empty commit hash.")
    return ''

def save_last_commit(commit_hash):
    """Save the last processed commit hash."""
    last_commit_path = os.path.join(INDEX_DIR, LAST_COMMIT_FILE)
    os.makedirs(os.path.dirname(last_commit_path), exist_ok=True)
    with open(last_commit_path, 'w', encoding='utf-8') as f:
        json.dump({'commit_hash': commit_hash}, f, indent=4)

def get_current_commit(repo_path):
    """Get the current commit hash of the repository."""
    try:
        repo = git.Repo(repo_path)
        return repo.head.commit.hexsha
    except Exception as e:
        logging.error(f"Error getting current commit: {e}")
        return ''

def detect_changes_from_git(repo_path):
    """Detect file changes by comparing with the last processed commit.
    
    Returns a tuple of (modified_files, deleted_files, new_files).
    """
    logging.info(f"Detecting changes from Git repository at {repo_path}...")
    
    # Get the last processed commit hash
    last_commit = load_last_commit()
    
    # Get the current commit hash
    current_commit = get_current_commit(repo_path)
    
    if not current_commit:
        logging.error("Failed to get current commit hash. Cannot detect changes.")
        return ([], [], [])
    
    if not last_commit:
        logging.info("No previous commit found. Treating all files as new.")
        # Find all Java files in the repository
        java_files = []
        for root, _, files in os.walk(repo_path):
            # Skip .git directories
            if '.git' in root:
                continue
                
            # Skip test directories
            if 'test' in root.lower():
                continue
                
            # Process Java files
            for file in files:
                if file.endswith(".java"):
                    file_path = os.path.join(root, file)
                    java_files.append(file_path)
        
        # Save the current commit hash
        save_last_commit(current_commit)
        
        logging.info(f"Found {len(java_files)} new Java files.")
        return ([], [], java_files)
    
    # If commits are the same, no changes
    if current_commit == last_commit:
        logging.info("No changes detected in Git repository.")
        return ([], [], [])
    
    # Get changes between commits
    try:
        repo = git.Repo(repo_path)
        
        # Get the diff between commits
        diff = repo.git.diff('--name-status', last_commit, current_commit)
        
        # Parse the diff to get modified, deleted, and new files
        modified_files = []
        deleted_files = []
        new_files = []
        
        for line in diff.splitlines():
            parts = line.split('\t')
            if len(parts) >= 2:
                status = parts[0]
                file_path = os.path.join(repo_path, parts[1])
                
                # Skip non-Java files and test files
                if not file_path.endswith('.java') or 'test' in file_path.lower():
                    continue
                
                if status.startswith('M'):  # Modified
                    modified_files.append(file_path)
                elif status.startswith('D'):  # Deleted
                    deleted_files.append(file_path)
                elif status.startswith('A'):  # Added
                    new_files.append(file_path)
        
        # Save the current commit hash
        save_last_commit(current_commit)
        
        logging.info(f"Detected {len(modified_files)} modified files, {len(deleted_files)} deleted files, and {len(new_files)} new files.")
        return (modified_files, deleted_files, new_files)
        
    except Exception as e:
        logging.error(f"Error detecting changes from Git: {e}")
        return ([], [], [])

def scan_directory_incremental(directory):
    """Scan all Java files in the directory, skipping only test directories."""
    java_files = []
    
    logging.info(f"Starting scan of directory: {directory}")
    
    # Walk through all directories and find Java files
    for root, dirs, files in os.walk(directory):
        # Skip .git directories
        if '.git' in root:
            continue
            
        # Skip test directories
        if 'test' in root.lower():
            continue
            
        # Process Java files
        for file in files:
            if file.endswith(".java"):
                file_path = os.path.join(root, file)
                java_files.append(file_path)
                logging.info(f"Adding file to analysis: {file_path}")

    logging.info(f"Found {len(java_files)} Java files to analyze")
    
    if not java_files:
        logging.warning("No Java files found. Skipping indexing.")
        return

    # Create index directory if it doesn't exist
    initialize_index()
    
    # Process files sequentially to avoid multiprocessing issues
    with tqdm(total=len(java_files), desc="Indexing Files") as pbar:
        for file_path in java_files:
            try:
                result = parse_java_file(file_path)
                if result and "Error" in result:
                    logging.error(result)
            except Exception as e:
                logging.error(f"Error processing {file_path}: {str(e)}")
            pbar.update(1)
    
    # Save current commit hash for future change detection
    current_commit = get_current_commit(directory)
    if current_commit:
        save_last_commit(current_commit)
    else:
        logging.warning("Could not get current commit hash. Changes may not be detected correctly in the future.")

def scan_and_update(directory):
    """Scan the repository for changes and update affected BDD test cases."""
    logging.info(f"Scanning repository for changes: {directory}")
    
    # Detect file changes from Git
    modified_files, deleted_files, new_files = detect_changes_from_git(directory)
    
    # If there are any changes, update the test cases
    if modified_files or deleted_files or new_files:
        # Initialize index and directories if needed
        initialize_index()
        initialize_summary_dirs()
        
        # Update BDD test cases
        update_summaries_and_test_cases(modified_files, deleted_files, new_files)
        
        logging.info("Successfully updated BDD test cases.")
    else:
        logging.info("No changes detected. Skipping update.")


def initialize_summary_dirs():
    """Initialize summary directories."""
    os.makedirs(SUMMARY_DIR, exist_ok=True)
    os.makedirs(BDD_TEST_CASES_DIR, exist_ok=True)


def read_prompt_file(prompt_file):
    """Read a prompt file from the prompts directory."""
    prompt_path = os.path.join(PROMPTS_DIR, prompt_file)
    logging.info(f"Attempting to read prompt file: {prompt_path}")
    
    if not os.path.exists(prompt_path):
        logging.error(f"Prompt file does not exist: {prompt_path}")
        return None
        
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            content = f.read()
            logging.info(f"Successfully read prompt file: {prompt_path} ({len(content)} characters)")
            return content
    except Exception as e:
        logging.error(f"Error reading prompt file {prompt_path}: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return None


def call_openai_api(prompt, max_retries=3, retry_delay=2):
    """Call OpenAI API with retry logic."""
    config = load_config()
    api_key = config.get("openai_api_key")
    
    if not api_key:
        logging.error("OpenAI API key not found in config.json. Please add 'openai_api_key' to your config.")
        return None
    
    client = openai.OpenAI(api_key=api_key)
    
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="gpt-4",  # or another model like "gpt-3.5-turbo"
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that analyzes code and provides summaries."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.2
            )
            return response.choices[0].message.content
        except Exception as e:
            logging.error(f"Error calling OpenAI API (attempt {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                return None


def generate_bdd_test_cases():
    """Generate BDD test cases for each API endpoint in the API flow data."""
    logging.info("Generating BDD test cases for API endpoints...")
    
    # Load the API flow data
    api_flow_data = load_from_file(API_FLOW_JSON)
    if not api_flow_data:
        logging.warning("No API flow data found. Run scan_directory_incremental first.")
        return None
    
    # Get the BDD test case template
    bdd_template = read_prompt_file("BDD Test Case Template.md")
    if not bdd_template:
        logging.error("Failed to read BDD test case template.")
        return None
    
    # Create directory for BDD test cases if it doesn't exist
    os.makedirs(BDD_TEST_CASES_DIR, exist_ok=True)
    
    # Track the generated test cases
    generated_test_cases = []
    
    # Generate test cases for each API endpoint
    for endpoint_path, endpoint_data in api_flow_data.items():
        for endpoint in endpoint_data.get("endpoints", []):
            # Create a meaningful endpoint ID
            http_method = endpoint.get("http_method", "GET")
            endpoint_id = f"{http_method}_{endpoint_path.replace('/', '_').strip('_')}"
            
            # Prepare the prompt with endpoint information
            endpoint_info = {
                "path": endpoint_path,
                "method": http_method,
                "controller": endpoint.get("class", ""),
                "controller_method": endpoint.get("method", ""),
                "service_calls": endpoint_data.get("service_calls", [])
            }
            
            prompt = f"{bdd_template}\n\nAPI Endpoint Information:\n```json\n{json.dumps(endpoint_info, indent=2)}\n```"
            
            # Call OpenAI API to generate test cases
            test_cases = call_openai_api(prompt)
            if not test_cases:
                logging.error(f"Failed to generate BDD test cases for endpoint: {endpoint_path}")
                continue
            
            # Save the test cases
            test_case_file = os.path.join(BDD_TEST_CASES_DIR, f"{endpoint_id}.feature")
            with open(test_case_file, 'w', encoding='utf-8') as f:
                f.write(f"# BDD Test Cases for {http_method} {endpoint_path}\n\n")
                f.write(test_cases)
            
            generated_test_cases.append(test_case_file)
            logging.info(f"Generated BDD test cases for endpoint: {endpoint_path}")
    
    # Create a summary of generated test cases
    if generated_test_cases:
        summary_file = os.path.join(BDD_TEST_CASES_DIR, "test_cases_summary.md")
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("# BDD Test Cases Summary\n\n")
            f.write("This directory contains BDD test cases generated for API endpoints in the application.\n\n")
            f.write("## Generated Test Cases\n\n")
            for test_case in generated_test_cases:
                relative_path = os.path.relpath(test_case, BDD_TEST_CASES_DIR)
                f.write(f"- [{relative_path}]({relative_path})\n")
        
        logging.info(f"Generated BDD test cases summary: {summary_file}")
        return summary_file
    else:
        logging.warning("No BDD test cases were generated.")
        return None


def generate_summaries(directory, force_regenerate=False):
    """Generate BDD test cases for API endpoints.
    
    Args:
        directory: The directory containing Java files to analyze.
        force_regenerate: If True, regenerate test cases even if they already exist.
    """
    # Initialize summary directories
    initialize_summary_dirs()
    
    # Generate BDD test cases for API endpoints
    bdd_test_summary = generate_bdd_test_cases()
    if bdd_test_summary:
        logging.info(f"BDD test cases generated: {bdd_test_summary}")


def generate_api_flow_for_llm(directory):
    """Generate API flow representation in JSON format for better LLM consumption.
    
    This creates a more structured representation of the API endpoints and their relationships
    to controllers, services, and repositories for easier consumption by LLMs.
    """
    logging.info("Generating API flow representation for LLM consumption...")
    
    # Load the existing API flow data
    api_flow_data = load_from_file(API_FLOW_JSON)
    if not api_flow_data:
        logging.warning("No API flow data found. Run scan_directory_incremental first.")
        return None
    
    # Load the index data to get more information about the components
    index_data = load_from_file(INDEX_JSON)
    if not index_data:
        logging.warning("No index data found. Run scan_directory_incremental first.")
        return None
    
    # Create the enhanced API flow representation
    enhanced_api_flow = {}
    
    for endpoint_path, endpoint_data in api_flow_data.items():
        for endpoint in endpoint_data.get("endpoints", []):
            endpoint_key = f"{endpoint_path}:{endpoint.get('http_method', 'GET')}"
            
            # Initialize the endpoint entry
            if endpoint_key not in enhanced_api_flow:
                enhanced_api_flow[endpoint_key] = {
                    "endpoint": endpoint_path,
                    "method": endpoint.get("http_method", "GET"),
                    "controller": {
                        "file": f"{endpoint.get('class', '')}.java",
                        "method": endpoint.get("method", ""),
                        "responsibility": f"Handles {endpoint_path} requests"
                    },
                    "serviceChain": [],
                    "repositoryAccess": [],
                    "dataModels": [],
                    "dependencies": []
                }
            
            # Add service chain information
            for service_call in endpoint_data.get("service_calls", []):
                service_info = {
                    "file": f"{service_call.get('service', '')}.java",
                    "method": "Unknown",  # We don't have this information in the current data
                    "responsibility": f"Business logic for {endpoint_path}"
                }
                
                if service_info not in enhanced_api_flow[endpoint_key]["serviceChain"]:
                    enhanced_api_flow[endpoint_key]["serviceChain"].append(service_info)
                
                # Add as a dependency as well
                if service_info["file"] not in enhanced_api_flow[endpoint_key]["dependencies"]:
                    enhanced_api_flow[endpoint_key]["dependencies"].append(service_info["file"])
            
            # Try to find repository access information from the index data
            for file_path, file_data in index_data.items():
                # Check if this is a repository file
                if "Repository" in file_path:
                    # Add to repository access
                    repo_info = {
                        "file": os.path.basename(file_path),
                        "method": "Unknown",  # We don't have this information in the current data
                        "dataAccessed": os.path.basename(file_path).replace("Repository.java", "")
                    }
                    
                    if repo_info not in enhanced_api_flow[endpoint_key]["repositoryAccess"]:
                        enhanced_api_flow[endpoint_key]["repositoryAccess"].append(repo_info)
                
                # Check if this is a model file
                elif "models" in file_path or "entities" in file_path:
                    model_file = os.path.basename(file_path)
                    if model_file not in enhanced_api_flow[endpoint_key]["dataModels"]:
                        enhanced_api_flow[endpoint_key]["dataModels"].append(model_file)
    
    # Save the enhanced API flow representation
    enhanced_api_flow_file = os.path.join(SUMMARY_DIR, "enhanced_api_flow.json")
    with open(enhanced_api_flow_file, 'w', encoding='utf-8') as f:
        json.dump(enhanced_api_flow, f, indent=2)
    
    logging.info(f"Enhanced API flow representation saved to {enhanced_api_flow_file}")
    return enhanced_api_flow_file


def generate_component_relationship_matrix():
    """Generate a component relationship matrix showing dependencies between components.
    
    This creates a markdown table showing which components depend on which other components,
    and which components use each component.
    """
    logging.info("Generating component relationship matrix...")
    
    # Load the index data
    index_data = load_from_file(INDEX_JSON)
    if not index_data:
        logging.warning("No index data found. Run scan_directory_incremental first.")
        return None
    
    # Create dictionaries to track dependencies
    depends_on = defaultdict(set)
    used_by = defaultdict(set)
    
    # Process all files to build the dependency graph
    for file_path, file_data in index_data.items():
        component_name = os.path.basename(file_path).replace(".java", "")
        
        # Process dependencies
        for dependency in file_data.get("dependencies", []):
            # Skip external dependencies
            if any(ext_pkg in dependency for ext_pkg in EXTERNAL_PACKAGES):
                continue
                
            # Extract the component name from the dependency
            dep_parts = dependency.split(".")
            if len(dep_parts) > 0:
                dep_component = dep_parts[-1]
                depends_on[component_name].add(dep_component)
                used_by[dep_component].add(component_name)
    
    # Create the markdown table
    matrix_content = "# Component Relationship Matrix\n\n"
    matrix_content += "| Component | Depends On | Used By |\n"
    matrix_content += "|-----------|-----------|--------|\n"
    
    # Sort components alphabetically
    components = sorted(set(list(depends_on.keys()) + list(used_by.keys())))
    
    for component in components:
        deps = ", ".join(sorted(depends_on[component])) if component in depends_on else ""
        users = ", ".join(sorted(used_by[component])) if component in used_by else ""
        matrix_content += f"| {component} | {deps} | {users} |\n"
    
    # Save the matrix
    matrix_file = os.path.join(SUMMARY_DIR, "component_relationship_matrix.md")
    with open(matrix_file, 'w', encoding='utf-8') as f:
        f.write(matrix_content)
    
    logging.info(f"Component relationship matrix saved to {matrix_file}")
    return matrix_file


def generate_llm_prompt_templates():
    """Generate effective prompt templates for LLM analysis.
    
    This creates a set of prompt templates that can be used to analyze the codebase
    with LLMs, including templates for feature implementation, code change impact,
    and self-correction mechanisms.
    """
    logging.info("Generating LLM prompt templates...")
    
    # Create the prompts directory if it doesn't exist
    llm_prompts_dir = os.path.join(SUMMARY_DIR, "llm_prompts")
    os.makedirs(llm_prompts_dir, exist_ok=True)
    
    # General analysis prompt template
    general_analysis_template = """# Spring Boot Application Analysis

## Application Context
{insert relevant high-level application summary}

## Components Relevant to Query
{insert summaries of the 3-5 most relevant components}

## API Flows Related to Query
{insert API flow data for endpoints relevant to the query}

## Question
{insert specific question}

## Instructions
1. Analyze the question in relation to the provided Spring Boot application context
2. Provide a detailed technical response addressing the question
3. Cite specific code files and components in your answer using the format [FileName.java]
4. Identify any potential impacts or considerations across components
5. If any information seems missing, note assumptions you're making
"""

    # Feature implementation prompt template
    feature_implementation_template = """# Feature Implementation Analysis

## Application Context
{insert relevant high-level application summary}

## Components Relevant to Feature
{insert summaries of the 3-5 most relevant components}

## API Flows Related to Feature
{insert API flow data for endpoints relevant to the feature}

## Feature Request
{insert feature description}

## Instructions
1. Analyze how the requested feature would be implemented in this Spring Boot application
2. Identify which existing components would need to be modified
3. Specify any new components that would need to be created
4. Describe the changes required to each component
5. Identify potential challenges or considerations for implementation
6. Cite specific code files and components in your answer using the format [FileName.java]

## Example Response Format:
```
Implementing [Feature Name] would require:

1. Modifications to existing components:
   - [ExistingComponent1.java]: {specific changes}
   - [ExistingComponent2.java]: {specific changes}

2. New components needed:
   - [NewComponent1.java]: {purpose and functionality}
   - [NewComponent2.java]: {purpose and functionality}

3. Implementation steps:
   {step-by-step implementation plan}

4. Potential challenges:
   {list of challenges and considerations}
```
"""

    # Code change impact prompt template
    code_change_impact_template = """# Code Change Impact Analysis

## Application Context
{insert relevant high-level application summary}

## Component Relationship Matrix
{insert relevant portion of component relationship matrix}

## Proposed Change
{insert description of proposed code change}

## Instructions
1. Analyze the impact of the proposed change on the Spring Boot application
2. Identify all components that would be directly affected by the change
3. Identify all components that would be indirectly affected through dependencies
4. Assess the scope of the change (isolated vs. widespread)
5. Identify potential risks or considerations
6. Cite specific code files and components in your answer using the format [FileName.java]

## Example Response Format:
```
Changing [Component] would impact:

1. Direct impacts:
   - [Component1.java]: {specific impact}
   - [Component2.java]: {specific impact}

2. Indirect impacts (through dependencies):
   - [Component3.java] depends on [Component1.java]: {specific impact}
   - [Component4.java] uses [Component2.java]: {specific impact}

3. Scope assessment:
   {assessment of whether the change is isolated or widespread}

4. Risks and considerations:
   {list of risks and considerations}
```
"""

    # Comprehensive analysis prompt template
    comprehensive_analysis_template = """# Comprehensive Spring Boot Application Analysis

## Application Context
{insert relevant high-level application summary}

## Components Relevant to Analysis
{insert summaries of the 3-5 most relevant components}

## API Flows Related to Analysis
{insert API flow data for endpoints relevant to the analysis}

## Component Relationship Matrix
{insert relevant portion of component relationship matrix}

## Analysis Requests
### General Query
{insert specific question}

### Feature Implementation
{insert feature description}

### Code Change Impact
{insert description of proposed code change}

## Analysis Instructions

### 1. General Query Analysis
1. Analyze the question in relation to the provided Spring Boot application context
2. Provide a detailed technical response addressing the question
3. Cite specific code files and components in your answer using the format [FileName.java]
4. Identify any potential impacts or considerations across components

### 2. Feature Implementation Analysis
1. Analyze how the requested feature would be implemented in this Spring Boot application
2. Identify which existing components would need to be modified
3. Specify any new components that would need to be created
4. Describe the changes required to each component
5. Identify potential challenges or considerations for implementation

### 3. Code Change Impact Analysis
1. Analyze the impact of the proposed change on the Spring Boot application
2. Identify all components that would be directly affected by the change
3. Identify all components that would be indirectly affected through dependencies
4. Assess the scope of the change (isolated vs. widespread)
5. Identify potential risks or considerations

## Response Format

### General Query Response
Provide a detailed technical response to the query, citing specific code files and components using the format [FileName.java]. Include any relevant code examples, architectural considerations, and potential limitations.

### Feature Implementation Response
```
Implementing [Feature Name] would require:

1. Modifications to existing components:
   - [ExistingComponent1.java]: {specific changes}
   - [ExistingComponent2.java]: {specific changes}

2. New components needed:
   - [NewComponent1.java]: {purpose and functionality}
   - [NewComponent2.java]: {purpose and functionality}

3. Implementation steps:
   {step-by-step implementation plan}

4. Potential challenges:
   {list of challenges and considerations}
```

### Code Change Impact Response
```
Changing [Component] would impact:

1. Direct impacts:
   - [Component1.java]: {specific impact}
   - [Component2.java]: {specific impact}

2. Indirect impacts (through dependencies):
   - [Component3.java] depends on [Component1.java]: {specific impact}
   - [Component4.java] uses [Component2.java]: {specific impact}

3. Scope assessment:
   {assessment of whether the change is isolated or widespread}

4. Risks and considerations:
   {list of risks and considerations}
```
"""

    # Self-correction mechanism prompt template
    self_correction_template = """# Self-Correction Review

## Original Response
{insert original LLM response}

## Application Context
{insert relevant high-level application summary}

## Component Relationship Matrix
{insert relevant portion of component relationship matrix}

## Instructions
Review the original response and verify:
1. Are all cited files actually mentioned in the application context?
2. Are the described relationships between components consistent with the provided component relationship matrix?
3. Are the described API flows consistent with the provided API flow data?
4. Does the impact analysis consider all dependent components from the relationship matrix?
5. Correct any inconsistencies and explain the corrections.

## Example Response Format:
```
Review of original response:

1. File reference accuracy:
   - [CorrectReference.java]: Verified in application context
   - [IncorrectReference.java]: Not found in application context, should be [CorrectFile.java]

2. Component relationship accuracy:
   - [Component1.java] correctly identified as depending on [Component2.java]
   - [Component3.java] incorrectly described as using [Component4.java], no such relationship exists

3. API flow accuracy:
   - The described flow for [/api/endpoint] is consistent with the API flow data
   - The described flow for [/api/another] is inconsistent, should include [MissingComponent.java]

4. Impact analysis completeness:
   - [MissingDependentComponent.java] was not considered but would be affected

Corrected response:
{insert corrected response}
```
"""
    
    # Save the templates
    with open(os.path.join(llm_prompts_dir, "general_analysis_template.md"), 'w', encoding='utf-8') as f:
        f.write(general_analysis_template)
        
    with open(os.path.join(llm_prompts_dir, "feature_implementation_template.md"), 'w', encoding='utf-8') as f:
        f.write(feature_implementation_template)
        
    with open(os.path.join(llm_prompts_dir, "code_change_impact_template.md"), 'w', encoding='utf-8') as f:
        f.write(code_change_impact_template)
        
    with open(os.path.join(llm_prompts_dir, "comprehensive_analysis_template.md"), 'w', encoding='utf-8') as f:
        f.write(comprehensive_analysis_template)
        
    with open(os.path.join(llm_prompts_dir, "self_correction_template.md"), 'w', encoding='utf-8') as f:
        f.write(self_correction_template)
        
    logging.info("LLM prompt templates generated successfully")


def update_affected_api_endpoints(modified_files, deleted_files, new_files):
    """Update the API flow data for affected API endpoints based on file changes."""
    logging.info("Updating affected API endpoints...")
    
    # Load the index and API flow data
    index_data = load_from_file(INDEX_JSON)
    api_flow_data = load_from_file(API_FLOW_JSON)
    
    affected_endpoints = set()
    
    # Process modified files
    for file_path in modified_files:
        # Re-parse the modified file
        parse_java_file(file_path)
        
        # Check if this file affected any API endpoints
        file_endpoints = get_file_endpoints(file_path, index_data)
        affected_endpoints.update(file_endpoints)
    
    # Process new files
    for file_path in new_files:
        # Parse the new file
        parse_java_file(file_path)
        
        # Check if this file affected any API endpoints
        file_endpoints = get_file_endpoints(file_path, index_data)
        affected_endpoints.update(file_endpoints)
    
    # Process deleted files
    for file_path in deleted_files:
        # Check if this file affected any API endpoints
        file_endpoints = get_file_endpoints(file_path, index_data)
        affected_endpoints.update(file_endpoints)
        
        # Remove the file from the index
        if file_path in index_data:
            del index_data[file_path]
    
    # Save the updated index
    save_to_file(INDEX_JSON, index_data)
    
    logging.info(f"Updated {len(affected_endpoints)} affected API endpoints.")
    return affected_endpoints

def get_file_endpoints(file_path, index_data):
    """Get the API endpoints affected by a file."""
    endpoints = set()
    
    # Check if the file is directly associated with an endpoint (controller)
    if file_path in index_data:
        for endpoint in index_data[file_path].get("api_flow", {}).get("endpoints", []):
            path = endpoint.get("path", "")
            http_method = endpoint.get("http_method", "")
            if path and http_method:
                endpoints.add(f"{http_method}_{path}")
    
    # Check if the file is referenced by any endpoints (service, repository)
    file_basename = os.path.basename(file_path).replace(".java", "")
    for f_path, data in index_data.items():
        if f_path != file_path:  # Don't check the file against itself
            # Check services
            for service in data.get("api_flow", {}).get("service_calls", []):
                if service.get("service", "") == file_basename:
                    for endpoint in data.get("api_flow", {}).get("endpoints", []):
                        path = endpoint.get("path", "")
                        http_method = endpoint.get("http_method", "")
                        if path and http_method:
                            endpoints.add(f"{http_method}_{path}")
            
            # Check repositories
            for repo in data.get("api_flow", {}).get("repository_calls", []):
                if repo.get("repository", "") == file_basename:
                    for endpoint in data.get("api_flow", {}).get("endpoints", []):
                        path = endpoint.get("path", "")
                        http_method = endpoint.get("http_method", "")
                        if path and http_method:
                            endpoints.add(f"{http_method}_{path}")
    
    return endpoints

def update_bdd_test_case(endpoint_id):
    """Update a BDD test case for a specific API endpoint."""
    logging.info(f"Updating BDD test case for endpoint: {endpoint_id}")
    
    # Load the API flow data
    api_flow_data = load_from_file(API_FLOW_JSON)
    
    # Extract the path and HTTP method from the endpoint ID
    parts = endpoint_id.split('_', 1)
    if len(parts) != 2:
        logging.error(f"Invalid endpoint ID format: {endpoint_id}")
        return None
    
    http_method, path_parts = parts[0], parts[1]
    path = '/' + path_parts.replace('_', '/')
    
    # Find the endpoint data
    endpoint_data = None
    for endpoint_path, data in api_flow_data.items():
        if endpoint_path == path or endpoint_path.replace('//', '/') == path:
            endpoint_data = data
            break
    
    if not endpoint_data:
        logging.error(f"Endpoint not found: {path}")
        return None
    
    # Find the specific endpoint with the matching HTTP method
    endpoint = None
    for ep in endpoint_data.get("endpoints", []):
        if ep.get("http_method", "") == http_method:
            endpoint = ep
            break
    
    if not endpoint:
        logging.error(f"Endpoint with HTTP method {http_method} not found for path {path}")
        return None
    
    # Generate the BDD test case
    bdd_template = read_prompt_file("BDD Test Case Template.md")
    if not bdd_template:
        logging.error("Failed to read BDD test case template.")
        return None
    
    # Prepare the prompt with endpoint information
    endpoint_info = {
        "path": path,
        "method": http_method,
        "controller": endpoint.get("class", ""),
        "controller_method": endpoint.get("method", ""),
        "service_calls": endpoint_data.get("service_calls", [])
    }
    
    prompt = f"{bdd_template}\n\nAPI Endpoint Information:\n```json\n{json.dumps(endpoint_info, indent=2)}\n```"
    
    # Call OpenAI API to generate test cases
    test_cases = call_openai_api(prompt)
    if not test_cases:
        logging.error(f"Failed to generate BDD test cases for endpoint: {path}")
        return None
    
    # Save the test case
    test_case_file = os.path.join(BDD_TEST_CASES_DIR, f"{endpoint_id}.feature")
    with open(test_case_file, 'w', encoding='utf-8') as f:
        f.write(f"# BDD Test Cases for {http_method} {path}\n\n")
        f.write(test_cases)
    
    logging.info(f"Generated BDD test case for endpoint: {path}")
    return test_case_file

def update_summaries_and_test_cases(modified_files, deleted_files, new_files):
    """Update BDD test cases for modified, deleted, and new files."""
    logging.info("Updating BDD test cases...")
    
    # Update affected API endpoints
    affected_endpoints = update_affected_api_endpoints(modified_files, deleted_files, new_files)
    
    # Update BDD test cases for affected endpoints
    for endpoint_id in affected_endpoints:
        update_bdd_test_case(endpoint_id)
    
    # Update BDD test cases summary
    if affected_endpoints:
        update_bdd_test_cases_summary()
    
    logging.info("Completed updating BDD test cases.")

def update_bdd_test_cases_summary():
    """Update the BDD test cases summary file."""
    logging.info("Updating BDD test cases summary...")
    
    # Get all BDD test case files
    test_case_files = []
    for root, _, files in os.walk(BDD_TEST_CASES_DIR):
        for file in files:
            if file.endswith('.feature') and file != 'example.feature':
                test_case_files.append(os.path.join(root, file))
    
    # Create a summary of generated test cases
    if test_case_files:
        summary_file = os.path.join(BDD_TEST_CASES_DIR, "test_cases_summary.md")
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("# BDD Test Cases Summary\n\n")
            f.write("This directory contains BDD test cases generated for API endpoints in the application.\n\n")
            f.write("## Generated Test Cases\n\n")
            for test_case in test_case_files:
                relative_path = os.path.relpath(test_case, BDD_TEST_CASES_DIR)
                f.write(f"- [{relative_path}]({relative_path})\n")
        
        logging.info(f"Updated BDD test cases summary: {summary_file}")
        return summary_file
    else:
        logging.warning("No BDD test cases found.")
        return None

def get_api_flow_data():
    """Get the API flow data from the API_FLOW_JSON file."""
    return load_from_file(API_FLOW_JSON)

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

if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Generate BDD test cases for API endpoints")
    parser.add_argument("--force-clone", action="store_true", help="Force clone repository even if it already exists")
    parser.add_argument("--force-bdd-tests", action="store_true", help="Force regenerate BDD test cases even if they already exist")
    parser.add_argument("--skip-bdd-tests", action="store_true", help="Skip generating BDD test cases")
    parser.add_argument("--llm-optimizations", action="store_true", help="Generate LLM-optimized templates")
    parser.add_argument("--update-only", action="store_true", help="Only scan for changes and update affected test cases")
    args = parser.parse_args()
    
    # Load configuration
    config = load_config()
    repo_url = config.get("repo_url", "https://github.com/pauldragoslav/Spring-boot-Banking")
    clone_dir = config.get("clone_dir", "./clonned_repo")

    # Handle force clone if specified
    if args.force_clone:
        logging.info(f"Forcing clone: removing existing directory {clone_dir}")
        if os.path.exists(clone_dir):
            if not safe_remove_directory(clone_dir):
                logging.warning(f"Could not fully remove {clone_dir}, but will attempt to proceed")

    # Create clone directory if it doesn't exist
    os.makedirs(clone_dir, exist_ok=True)
    
    # Clone repository
    clone_repo(repo_url, clone_dir)
    
    # Check if we should only update based on changes
    if args.update_only:
        logging.info("Running in update-only mode. Scanning for changes...")
        scan_and_update(clone_dir)
        logging.info("Update completed.")
        exit(0)
    
    # Full processing mode
    # Initialize index and scan directory
    initialize_index()
    scan_directory_incremental(clone_dir)
    
    # Generate BDD test cases if not skipped
    if not args.skip_bdd_tests:
        logging.info("Generating BDD test cases...")
        initialize_summary_dirs()
        bdd_test_summary = generate_bdd_test_cases()
        if bdd_test_summary:
            logging.info(f"BDD test cases generated: {bdd_test_summary}")
    else:
        logging.info("Skipping BDD test case generation.")
        
    # Generate LLM optimizations if requested
    if args.llm_optimizations:
        logging.info("Generating LLM optimizations...")
        
        # Generate enhanced API flow representation
        api_flow_file = generate_api_flow_for_llm(clone_dir)
        if api_flow_file:
            logging.info(f"Enhanced API flow representation generated: {api_flow_file}")
        
        # Generate component relationship matrix
        matrix_file = generate_component_relationship_matrix()
        if matrix_file:
            logging.info(f"Component relationship matrix generated: {matrix_file}")
        
        # Generate LLM prompt templates
        templates_dir = generate_llm_prompt_templates()
        if templates_dir:
            logging.info(f"LLM prompt templates generated in: {templates_dir}")
            
        logging.info("LLM optimizations completed.")
    else:
        logging.info("Skipping LLM optimizations. Use --llm-optimizations to generate them.")

