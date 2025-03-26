#!/usr/bin/env python
"""
Fix apostrophe_issues function in run_everything.py

This script:
1. Adds a properly formatted fix_apostrophe_issues function to run_everything.py
2. Adds a call to this function in the run_bdd_tests function

Usage:
    python fix_apostrophe_in_run_everything.py
"""

import os
import sys
import re
import logging
import shutil

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def inject_fix_function():
    """Inject the fix_apostrophe_issues function into run_everything.py"""
    logging.info("Injecting fix_apostrophe_issues function into run_everything.py")
    
    # Check if run_everything.py exists
    if not os.path.exists("run_everything.py"):
        logging.error("run_everything.py not found")
        return False
    
    # Create a backup if it doesn't exist already
    backup_path = "run_everything.py.bak2"
    if not os.path.exists(backup_path):
        shutil.copy2("run_everything.py", backup_path)
        logging.info(f"Created backup at {backup_path}")
    
    # Read the file
    with open("run_everything.py", 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if the function already exists
    if "def fix_apostrophe_issues" in content:
        logging.info("fix_apostrophe_issues function already exists, removing it first")
        # Remove the existing function
        content = re.sub(r'def fix_apostrophe_issues.*?return True\n', '', content, flags=re.DOTALL)
    
    # Find an appropriate place to insert the function - after setup_environment_py
    setup_env_pos = content.find("def setup_environment_py")
    if setup_env_pos == -1:
        logging.error("Could not find setup_environment_py function")
        return False
    
    # Find the end of the setup_environment_py function
    setup_env_end = content.find("def", setup_env_pos + 1)
    if setup_env_end == -1:
        logging.error("Could not find the end of setup_environment_py function")
        return False
    
    # The new function to insert
    fix_function = """
def fix_apostrophe_issues(file_path):
    \"\"\"Fix apostrophe issues in step definition files.\"\"\"
    logging.info(f"Fixing apostrophe issues in {file_path}")
    
    if not os.path.exists(file_path):
        logging.error(f"File not found: {file_path}")
        return False
    
    # Make a backup of the file if it doesn't exist
    backup_path = f"{file_path}.bak"
    if not os.path.exists(backup_path):
        try:
            shutil.copy2(file_path, backup_path)
            logging.info(f"Created backup at {backup_path}")
        except Exception as e:
            logging.warning(f"Failed to create backup: {e}")
    
    # Read the file
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Process line by line to handle complex cases
    lines = content.split('\\n')
    
    for i in range(len(lines)):
        line = lines[i]
        
        # Skip lines that don't contain behave decorators
        if '@behave.' not in line:
            continue
        
        # Extract the decorator type (given, when, then)
        if line.startswith('@behave.given'):
            decorator_type = 'given'
        elif line.startswith('@behave.when'):
            decorator_type = 'when'
        elif line.startswith('@behave.then'):
            decorator_type = 'then'
        else:
            continue
        
        # Check if this line has potential issues (apostrophes or nested quotes)
        if ("'" in line and not line.startswith(f'@behave.{decorator_type}(u"')) or '"' in line:
            # Extract step text using regex
            match = re.search(r'@behave\\.' + decorator_type + r'\\((?:u)?[\'"](.+?)[\'"]', line)
            if not match:
                continue
                
            step_text = match.group(1)
            
            # Check if step text has problematic characters
            if "'" in step_text or '"' in step_text:
                # Properly escape the content
                escaped_text = step_text.replace('"', '\\\\"')
                # Create a new, properly formatted decorator
                lines[i] = f'@behave.{decorator_type}(u"{escaped_text}")'
    
    # Join lines back together
    fixed_content = '\\n'.join(lines)
    
    # Additional fixes for common problematic lines
    if "users' accounts" in fixed_content:
        fixed_content = fixed_content.replace(
            "I do not have permission to check the balance of other users' accounts", 
            "I do not have permission to check the balance of other users\\' accounts"
        )
    
    # Save the fixed content
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(fixed_content)
    
    logging.info(f"Fixed apostrophe issues in {file_path}")
    return True
"""
    
    # Insert the function
    new_content = content[:setup_env_end] + fix_function + content[setup_env_end:]
    
    # Now find the run_bdd_tests function
    run_bdd_pos = new_content.find("def run_bdd_tests")
    if run_bdd_pos == -1:
        logging.error("Could not find run_bdd_tests function")
        return False
    
    # Find the first line in the function
    run_bdd_body_start = new_content.find("\n", run_bdd_pos) + 1
    
    # Determine the indentation level
    indentation = 4
    for i in range(run_bdd_body_start, len(new_content)):
        if new_content[i] != ' ' and new_content[i] != '\n':
            indentation = i - run_bdd_body_start
            break
    
    indent = ' ' * indentation
    
    # Create the fix call
    fix_call = f"""
{indent}# Fix apostrophe issues in step definitions
{indent}api_steps_path = os.path.join(bdd_dir, "steps", "api_steps.py")
{indent}if os.path.exists(api_steps_path):
{indent}    fix_apostrophe_issues(api_steps_path)
{indent}    logging.info("Fixed apostrophe issues in step definitions")
{indent}else:
{indent}    logging.warning(f"Step definitions file not found at {{api_steps_path}}")
"""
    
    # Check if the call already exists
    if "fix_apostrophe_issues(api_steps_path)" in new_content:
        logging.info("Fix call already exists in run_bdd_tests, not adding again")
    else:
        # Insert the call at the beginning of the function body
        new_content = new_content[:run_bdd_body_start] + fix_call + new_content[run_bdd_body_start:]
    
    # Write the modified content
    with open("run_everything.py", 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    logging.info("Successfully injected fix_apostrophe_issues function into run_everything.py")
    return True

def main():
    """Main function"""
    logging.info("Starting fix of run_everything.py...")
    
    if inject_fix_function():
        logging.info("Successfully fixed run_everything.py")
        return 0
    else:
        logging.error("Failed to fix run_everything.py")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 