#!/usr/bin/env python
"""
Fix and Run BDD Tests

This script:
1. Fixes common issues in BDD step definitions
2. Runs the BDD tests

Usage:
    python fix_and_run_bdd.py
"""

import os
import sys
import re
import logging
import subprocess
import shutil
import tempfile
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def fix_step_file(file_path):
    """Fix common issues in a step definition file"""
    logging.info(f"Fixing step file: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix 1: Ensure we have the correct imports
    if "from behave import *" in content:
        logging.info("Step file already has wildcard import")
    else:
        # Add the import
        if "import behave" in content:
            content = content.replace("import behave", "import behave\nfrom behave import *")
            logging.info("Added 'from behave import *'")
        else:
            # Add after other imports
            import_section_end = content.find("\n\n", content.find("import "))
            if import_section_end != -1:
                content = content[:import_section_end] + "\nfrom behave import *" + content[import_section_end:]
                logging.info("Added 'from behave import *'")
    
    # Fix 2: Fix apostrophe issues
    content = content.replace(
        "@behave.given('I do not have permission to check the balance of other users' accounts')",
        '@behave.given(u"I do not have permission to check the balance of other users\' accounts")'
    )
    
    content = content.replace(
        "@behave.when('I send a \"POST\" request to \"api/v1/accounts\" with another user's account ID to check their account balance')",
        '@behave.when(u"I send a \\"POST\\" request to \\"api/v1/accounts\\" with another user\'s account ID to check their account balance")'
    )
    
    # Fix 3: Comment out ambiguous step definitions
    lines = content.split('\n')
    
    # Track status code steps to avoid ambiguity
    status_code_parametrized = False
    for line in lines:
        if '{status_code:d}' in line and '@' in line and 'then' in line:
            status_code_parametrized = True
            break
    
    if status_code_parametrized:
        for i in range(len(lines)):
            # Look for specific status code steps
            match = re.search(r'@(?:behave\.)?then\((?:u)?[\'"]I should receive a (\d+) status code[\'"]', lines[i])
            if match and not lines[i].strip().startswith('#'):
                lines[i] = '# ' + lines[i] + ' # Commented out to avoid ambiguity with parametrized version'
                logging.info(f"Commented out ambiguous step at line {i+1}")
                
                # Also comment out the function definition and body
                j = i + 1
                while j < len(lines) and (
                    lines[j].strip().startswith('def ') or 
                    (j < len(lines) and lines[j].startswith('    '))
                ):
                    if not lines[j].strip().startswith('#'):
                        lines[j] = '# ' + lines[j]
                    j += 1
    
    content = '\n'.join(lines)
    
    # Fix 4: Fix the context.response vs context.last_response inconsistency
    content = content.replace(
        "assert context.response is not None",
        "assert context.last_response is not None"
    )
    
    content = content.replace(
        "actual_status = context.response.status_code",
        "actual_status = context.last_response.status_code"
    )
    
    # Write the fixed content
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    logging.info(f"Fixed step file: {file_path}")
    return True

def find_and_fix_step_files():
    """Find and fix all step definition files"""
    logging.info("Finding and fixing step definition files...")
    
    # Directories to search for step definitions
    dirs_to_search = [
        "summary/bdd_test_cases/steps",
        "behave_tests/features/steps"
    ]
    
    for dir_path in dirs_to_search:
        if not os.path.exists(dir_path):
            logging.warning(f"Directory {dir_path} does not exist, skipping")
            continue
        
        # Look for step definition files
        for file_name in os.listdir(dir_path):
            if file_name.endswith("_steps.py"):
                file_path = os.path.join(dir_path, file_name)
                logging.info(f"Found step definition file: {file_path}")
                
                # Backup the file
                backup_path = file_path + ".original"
                if not os.path.exists(backup_path):
                    shutil.copy2(file_path, backup_path)
                    logging.info(f"Backed up original file to {backup_path}")
                
                # Fix the file
                fix_step_file(file_path)
    
    return True

def run_bdd_tests():
    """Run BDD tests using behave"""
    logging.info("Running BDD tests...")
    
    # Check for both possible BDD test locations
    bdd_dirs = [
        "summary/bdd_test_cases",
        "behave_tests/features"
    ]
    
    bdd_dir = None
    for dir_path in bdd_dirs:
        if os.path.exists(dir_path):
            bdd_dir = dir_path
            break
    
    if not bdd_dir:
        logging.error("Could not find BDD test directory")
        return False
    
    # Prepare behave command - Look harder for behave executable
    behave_cmd = "behave"
    if sys.platform == "win32":
        # Try multiple locations for behave.exe
        possible_locations = [
            os.path.join(os.path.dirname(sys.executable), "Scripts", "behave.exe"),
            os.path.join(os.path.dirname(sys.executable), "behave.exe"),
            # Windows Store Python sometimes has executables directly in WindowsApps folder
            r"C:\Users\kritik\AppData\Local\Microsoft\WindowsApps\behave.exe"
        ]
        
        for location in possible_locations:
            if os.path.exists(location):
                behave_cmd = location
                logging.info(f"Found behave executable at: {location}")
                break
        
        # If not found, try to run as python -m behave
        if behave_cmd == "behave":
            logging.info("Behave executable not found, using 'python -m behave'")
            behave_cmd = f"{sys.executable} -m behave"
    
    # Run behave with appropriate options
    try:
        reports_dir = os.path.join(bdd_dir, "reports")
        os.makedirs(reports_dir, exist_ok=True)
        
        # If behave_cmd is a command with arguments, split it
        if " " in behave_cmd:
            cmd = behave_cmd.split() + [
                "-f", "pretty",
                "-o", os.path.join(reports_dir, "bdd_report.txt"),
                "--junit",
                "--junit-directory", reports_dir,
                bdd_dir
            ]
        else:
            cmd = [
                behave_cmd,
                "-f", "pretty",
                "-o", os.path.join(reports_dir, "bdd_report.txt"),
                "--junit",
                "--junit-directory", reports_dir,
                bdd_dir
            ]
        
        logging.info(f"Executing command: {' '.join(cmd)}")
        
        # Set environment variables for the subprocess
        env = os.environ.copy()
        env["PYTHONPATH"] = os.path.abspath(os.path.dirname(bdd_dir))
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
            universal_newlines=True,
            bufsize=1
        )
        
        # Print output in real-time
        for line in iter(process.stdout.readline, ''):
            print(line, end='')
        
        process.stdout.close()
        return_code = process.wait()
        
        if return_code == 0:
            logging.info("BDD tests completed successfully!")
            return True
        else:
            logging.warning(f"BDD tests completed with return code {return_code}")
            return False
    except Exception as e:
        logging.error(f"Error running BDD tests: {e}")
        return False

def main():
    """Main function"""
    logging.info("Starting fix and run BDD tests...")
    
    # Step 1: Find and fix step definition files
    if not find_and_fix_step_files():
        logging.error("Failed to fix step definition files")
        return 1
    
    # Step 2: Run BDD tests
    if not run_bdd_tests():
        logging.error("Failed to run BDD tests")
        return 1
    
    logging.info("Successfully fixed and ran BDD tests")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 