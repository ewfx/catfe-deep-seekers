#!/usr/bin/env python
"""
Run All with Fixed Step Definitions

This script:
1. Runs generate_artifacts.py to clone the repo (if needed)
2. Fixes apostrophe issues in step definitions
3. Runs run_everything.py with the fixed step definitions

Usage:
    python run_all_with_fixed_steps.py
"""

import os
import sys
import re
import logging
import subprocess
import shutil
import time
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def run_glean_code_ds():
    """Run generate_artifacts.py to clone the repo and generate artifacts"""
    logging.info("Running generate_artifacts.py...")
    
    try:
        # Check if the script exists
        if not os.path.exists("generate_artifacts.py"):
            logging.error("generate_artifacts.py not found")
            return False
            
        # Run the script
        result = subprocess.run(
            [sys.executable, "generate_artifacts.py"],
            check=True,
            capture_output=True,
            text=True
        )
        
        logging.info(f"generate_artifacts.py completed with output: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Error running generate_artifacts.py: {e.stderr}")
        return False

def fix_apostrophe_issues(file_path):
    """Fix apostrophe issues in the step definitions file"""
    logging.info(f"Fixing apostrophe issues in {file_path}")
    
    if not os.path.exists(file_path):
        logging.error(f"File not found: {file_path}")
        return False
    
    # Make a backup of the original file
    backup_path = file_path + ".bak"
    shutil.copy2(file_path, backup_path)
    logging.info(f"Backed up original file to {backup_path}")
    
    # Read the file
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Process line by line to handle complex cases
    lines = content.split('\n')
    
    # Track status code steps to avoid ambiguity
    status_code_parametrized_line = -1
    specific_status_code_lines = []
    
    for i in range(len(lines)):
        line = lines[i]
        
        # Skip lines that don't contain behave decorators
        if '@behave.' not in line:
            continue
        
        # Track status code steps to prevent ambiguity
        if 'status_code' in line and '@behave.then' in line:
            if '{status_code:d}' in line:
                status_code_parametrized_line = i
            elif any(f"{code} status code" in line for code in ["401", "400", "403", "404", "500"]):
                specific_status_code_lines.append(i)
            
        # Extract the line type and raw step text
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
            match = re.search(r'@behave\.' + decorator_type + r'\((?:u)?[\'"](.+?)[\'"]', line)
            if not match:
                continue
                
            step_text = match.group(1)
            
            # Check if step text has problematic characters
            if "'" in step_text or '"' in step_text:
                # Properly escape the content
                escaped_text = step_text.replace('"', '\\"')
                # Create new properly formatted decorator
                lines[i] = f'@behave.{decorator_type}(u"{escaped_text}")'
        
        # Special case: Check for any nested quotes in "request to" steps that need escaping
        if '"' in line and 'request to' in line:
            # This is likely a step with HTTP method and endpoint in quotes
            match = re.search(r'@behave\.' + decorator_type + r'\(u?"I send a "([^"]+)" request to "([^"]+)"', line)
            if match:
                method, endpoint = match.groups()
                # Replace with properly escaped quotes
                lines[i] = f'@behave.{decorator_type}(u"I send a \\"' + method + '\\" request to \\"' + endpoint + '\\"' + line[line.rfind('"'):]
    
    # Comment out specific status code steps to avoid ambiguity
    for line_num in specific_status_code_lines:
        if line_num >= 0 and line_num < len(lines):
            # Only comment out if we have a parametrized version
            if status_code_parametrized_line >= 0:
                if not lines[line_num].strip().startswith('#'):
                    lines[line_num] = '# ' + lines[line_num] + ' # Commented out to avoid ambiguity with parametrized version'
                    logging.info(f"Commented out ambiguous step at line {line_num+1}")
    
    fixed_content = '\n'.join(lines)
    
    # Additional fixes for common problematic lines
    # Fix apostrophes in users' accounts
    fixed_content = fixed_content.replace(
        "I do not have permission to check the balance of other users' accounts", 
        "I do not have permission to check the balance of other users\' accounts"
    )
    
    # Fix more complex apostrophe issues
    fixed_content = fixed_content.replace(
        "@behave.when('I send a \"POST\" request to \"api/v1/accounts\" with another user's account ID to check their account balance')",
        '@behave.when(u"I send a \\"POST\\" request to \\"api/v1/accounts\\" with another user\'s account ID to check their account balance")'
    )
    
    # Fix "then" import if needed
    if "from behave import *" not in fixed_content and "from behave import then" not in fixed_content:
        # Add the import
        if "import behave" in fixed_content:
            fixed_content = fixed_content.replace("import behave", "import behave\nfrom behave import *")
    
    # Save the fixed content
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(fixed_content)
    
    logging.info(f"Fixed apostrophe issues in {file_path}")
    return True

def find_and_fix_step_definitions():
    """Find and fix all step definition files"""
    logging.info("Finding and fixing step definition files...")
    
    # Directories to search for step definitions
    dirs_to_search = [
        "summary/bdd_test_cases/steps",
        "behave_tests/features/steps"
    ]
    
    fixed_files = []
    
    for dir_path in dirs_to_search:
        if not os.path.exists(dir_path):
            logging.warning(f"Directory {dir_path} does not exist, skipping")
            continue
        
        # Look for step definition files
        for file_name in os.listdir(dir_path):
            if file_name.endswith("_steps.py"):
                file_path = os.path.join(dir_path, file_name)
                logging.info(f"Found step definition file: {file_path}")
                
                # Fix apostrophe issues
                if fix_apostrophe_issues(file_path):
                    fixed_files.append(file_path)
    
    if fixed_files:
        logging.info(f"Fixed {len(fixed_files)} step definition files")
        return True
    else:
        logging.warning("No step definition files were fixed")
        return False

def patch_run_everything():
    """Patch run_everything.py to fix apostrophe issues before BDD tests"""
    logging.info("Patching run_everything.py to handle apostrophe issues...")
    
    # Check if the file exists
    if not os.path.exists("run_everything.py"):
        logging.error("run_everything.py not found")
        return False
    
    # Make a backup of the original file
    backup_path = "run_everything.py.bak"
    if not os.path.exists(backup_path):
        shutil.copy2("run_everything.py", backup_path)
        logging.info(f"Backed up original file to {backup_path}")
    
    # Read the file
    with open("run_everything.py", 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if we already patched it
    if "def fix_apostrophe_issues" in content:
        logging.info("run_everything.py already patched, skipping")
        return True
    
    # Find the run_bdd_tests function
    bdd_test_regex = re.compile(r'def run_bdd_tests\([^)]*\):')
    match = bdd_test_regex.search(content)
    
    if not match:
        logging.error("Could not find run_bdd_tests function in run_everything.py")
        return False
    
    # Find the proper indentation
    pos = match.end()
    next_line_pos = content.find('\n', pos) + 1
    first_line = content[next_line_pos:content.find('\n', next_line_pos)]
    indentation = len(first_line) - len(first_line.lstrip())
    indent = ' ' * indentation
    
    # Add the fix_apostrophe_issues function
    fix_function = """
def fix_apostrophe_issues(file_path):
    \"\"\"Fix apostrophe issues in the step definitions file\"\"\"
    logging.info(f"Fixing apostrophe issues in {file_path}")
    
    if not os.path.exists(file_path):
        logging.error(f"File not found: {file_path}")
        return False
    
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
        
        # Extract the line type and raw step text
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
            import re
            match = re.search(r'@behave\\.' + decorator_type + r'\\((?:u)?[\\'"](.+?)[\\'"]', line)
            if not match:
                continue
                
            step_text = match.group(1)
            
            # Check if step text has problematic characters
            if "'" in step_text or '"' in step_text:
                # Properly escape the content
                escaped_text = step_text.replace('"', '\\\\"')
                # Create new properly formatted decorator
                lines[i] = f'@behave.{decorator_type}(u"{escaped_text}")'
    
    fixed_content = '\\n'.join(lines)
    
    # Additional fixes for common problematic lines
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
    
    # Add the fix function call to run_bdd_tests
    fix_call = f"""
{indent}# Fix apostrophe issues in step definitions
{indent}api_steps_path = os.path.join(bdd_dir, "steps", "api_steps.py")
{indent}if os.path.exists(api_steps_path):
{indent}    fix_apostrophe_issues(api_steps_path)
{indent}    logging.info("Fixed apostrophe issues in step definitions")
{indent}else:
{indent}    logging.warning(f"Step definitions file not found at {{api_steps_path}}")
"""
    
    # Insert the fix function at the end of imports
    import_end = content.find("\n\n", content.rfind("import "))
    if import_end == -1:
        import_end = content.find("\n", content.rfind("import "))
    
    if import_end == -1:
        logging.error("Could not find import section in run_everything.py")
        return False
        
    # Add re import if needed
    if "import re" not in content:
        content = content[:import_end] + "\nimport re" + content[import_end:]
        import_end += len("\nimport re")
    
    # Insert the fix function
    patched_content = content[:import_end] + fix_function + content[import_end:]
    
    # Insert the fix call
    bdd_test_start = patched_content.find('\n', patched_content.find('def run_bdd_tests')) + 1
    patched_content = patched_content[:bdd_test_start] + fix_call + patched_content[bdd_test_start:]
    
    # Write the patched file
    with open("run_everything.py", 'w', encoding='utf-8') as f:
        f.write(patched_content)
    
    logging.info("Successfully patched run_everything.py")
    return True

def run_everything():
    """Run the patched run_everything.py script"""
    logging.info("Running run_everything.py...")
    
    try:
        process = subprocess.Popen(
            [sys.executable, "run_everything.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Print output in real-time
        for line in iter(process.stdout.readline, ''):
            print(line, end='')
        
        process.stdout.close()
        return_code = process.wait()
        
        if return_code == 0:
            logging.info("Successfully ran run_everything.py!")
            return True
        else:
            logging.error(f"Error running run_everything.py: Return code {return_code}")
            return False
    except Exception as e:
        logging.error(f"Exception running run_everything.py: {e}")
        return False

def main():
    """Main function"""
    logging.info("Starting run all with fixed step definitions...")
    
    # Step 1: Run generate_artifacts.py if needed
    if not os.path.exists("summary"):
        if not run_glean_code_ds():
            logging.error("Failed to run generate_artifacts.py")
            return 1
    
    # Step 2: Find and fix step definitions
    if not find_and_fix_step_definitions():
        logging.warning("No step definition files were fixed - they may be already fixed")
    
    # Step 3: Patch run_everything.py
    if not patch_run_everything():
        logging.error("Failed to patch run_everything.py")
        return 1
    
    # Step 4: Run run_everything.py
    if not run_everything():
        logging.error("Failed to run run_everything.py")
        return 1
    
    logging.info("Successfully completed all steps!")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 
