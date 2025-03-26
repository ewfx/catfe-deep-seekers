#!/usr/bin/env python
"""
Fix BDD Step Definitions

This script focuses solely on fixing apostrophe and syntax issues in BDD step definition files.
It doesn't try to run any tests, just ensures the step definition files are syntactically correct.

Usage:
    python fix_bdd_step_definitions.py
"""

import os
import sys
import re
import logging
import shutil
import ast
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

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
    
    # Fix "users'" anywhere in the file
    fixed_content = re.sub(r"users'", r"users\'", fixed_content)
    
    # Fix more complex apostrophe issues
    fixed_content = fixed_content.replace(
        "@behave.when('I send a \"POST\" request to \"api/v1/accounts\" with another user's account ID to check their account balance')",
        '@behave.when(u"I send a \\"POST\\" request to \\"api/v1/accounts\\" with another user\'s account ID to check their account balance")'
    )
    
    # Fix any "user's" anywhere in the file
    fixed_content = re.sub(r"user's", r"user\'s", fixed_content)
    
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

def check_syntax(file_path):
    """Check if a Python file has valid syntax"""
    logging.info(f"Checking syntax of {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Use Python's AST module to validate syntax
        ast.parse(content)
        logging.info(f"✅ Syntax check passed for {file_path}")
        return True
    except SyntaxError as e:
        logging.error(f"❌ Syntax error in {file_path}: {e}")
        if hasattr(e, 'lineno') and hasattr(e, 'offset'):
            # Get the problematic line and context
            lines = content.split('\n')
            if 0 <= e.lineno-1 < len(lines):
                error_line = lines[e.lineno-1]
                logging.error(f"  Line {e.lineno}, Column {e.offset}")
                logging.error(f"  {error_line}")
                
                # Point to the error location
                pointer = ' ' * (e.offset - 1) + '^'
                logging.error(f"  {pointer}")
        return False

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
                    # Verify syntax
                    if check_syntax(file_path):
                        fixed_files.append(file_path)
                        logging.info(f"Successfully fixed and validated {file_path}")
                    else:
                        logging.error(f"Syntax issues remain in {file_path}")
    
    if fixed_files:
        logging.info(f"Fixed {len(fixed_files)} step definition files:")
        for file_path in fixed_files:
            logging.info(f"  - {file_path}")
        return True
    else:
        logging.warning("No step definition files were fixed")
        return False

def main():
    """Main function"""
    logging.info("Starting BDD step definitions fix...")
    
    if find_and_fix_step_definitions():
        logging.info("Successfully fixed BDD step definitions")
        return 0
    else:
        logging.error("Failed to fix some BDD step definitions")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 