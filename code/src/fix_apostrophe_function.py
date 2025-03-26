#!/usr/bin/env python
"""
Fix apostrophe issues in BDD step definitions

This script provides a standalone function to fix apostrophe issues in BDD step definitions.
It can be used directly or imported by other scripts.

Usage:
    python fix_apostrophe_function.py
"""

import os
import sys
import re
import logging
import shutil
import ast

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def check_syntax(file_path):
    """Check the syntax of a Python file."""
    logging.info(f"Checking syntax of {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Try to parse the file as Python code
        ast.parse(content)
        logging.info(f"Syntax check passed for {file_path}")
        return True
    except SyntaxError as e:
        logging.error(f"Syntax error in {file_path}: {e}")
        return False
    except Exception as e:
        logging.error(f"Error checking syntax of {file_path}: {e}")
        return False

def fix_apostrophe_issues(file_path):
    """Fix apostrophe issues in step definition files."""
    logging.info(f"Fixing apostrophe issues in {file_path}")
    
    if not os.path.exists(file_path):
        logging.error(f"File not found: {file_path}")
        return False
    
    # Make a backup of the file if it doesn't exist
    backup_path = f"{file_path}.fix_bak"
    try:
        shutil.copy2(file_path, backup_path)
        logging.info(f"Created backup at {backup_path}")
    except Exception as e:
        logging.warning(f"Failed to create backup: {e}")
    
    # Read the file
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    logging.info(f"Processing file with {len(content.split('\n'))} lines")
    
    # Count behave decorators
    behave_count = content.count('@behave.')
    logging.info(f"Found {behave_count} behave decorators")
    
    # Process line by line to handle complex cases
    lines = content.split('\n')
    fixed_count = 0
    
    for i in range(len(lines)):
        line = lines[i]
        original_line = line
        
        # Skip lines that don't contain behave decorators
        if '@behave.' not in line:
            continue
        
        logging.info(f"Processing line {i+1}: {line[:50]}...")
        
        # Extract the decorator type (given, when, then)
        if line.startswith('@behave.given'):
            decorator_type = 'given'
        elif line.startswith('@behave.when'):
            decorator_type = 'when'
        elif line.startswith('@behave.then'):
            decorator_type = 'then'
        else:
            continue
        
        # Fix specific problematic lines directly
        if "users' accounts" in line:
            line = line.replace(
                "I do not have permission to check the balance of other users' accounts", 
                "I do not have permission to check the balance of other users\\' accounts"
            )
            if line != original_line:
                lines[i] = line
                fixed_count += 1
                logging.info(f"Fixed line {i+1} with users' accounts")
                continue
        
        # Check if this line has potential issues (apostrophes or nested quotes)
        if "'" in line:
            # Handle the case where we have single quotes inside single quotes
            if line.startswith(f"@behave.{decorator_type}('") and line.count("'") > 2:
                # Extract the step text
                match = re.search(r'@behave\.' + decorator_type + r'\((?:u)?\'(.+?)\'', line)
                if match:
                    step_text = match.group(1)
                    
                    # Check if step text has problematic characters
                    if "'" in step_text:
                        # Switch to double quotes and properly escape the content
                        escaped_text = step_text.replace("'", "\\'")
                        new_line = f'@behave.{decorator_type}(u"{escaped_text}")'
                        lines[i] = new_line
                        fixed_count += 1
                        logging.info(f"Fixed line {i+1} with single quotes inside single quotes")
                        logging.info(f"Original: {original_line}")
                        logging.info(f"Fixed: {new_line}")
    
    # Join lines back together
    fixed_content = '\n'.join(lines)
    
    # Additional global replacements
    original_length = len(fixed_content)
    
    fixed_content = fixed_content.replace(
        "@behave.given('I do not have permission to check the balance of other users' accounts')",
        '@behave.given(u"I do not have permission to check the balance of other users\' accounts")'
    )
    
    if len(fixed_content) != original_length:
        fixed_count += 1
        logging.info("Fixed global users' accounts line")
    
    # Save the fixed content
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(fixed_content)
    
    logging.info(f"Fixed {fixed_count} issues in {file_path}")
    
    # Check the syntax of the fixed file
    if check_syntax(file_path):
        logging.info(f"Successfully fixed apostrophe issues in {file_path}")
        return True
    else:
        logging.error(f"Syntax issues remain in {file_path} after fixing")
        # Restore from backup if syntax check fails
        try:
            shutil.copy2(backup_path, file_path)
            logging.info(f"Restored original file from backup due to syntax errors")
        except Exception as e:
            logging.error(f"Error restoring from backup: {e}")
        return False

def main():
    """Main function"""
    logging.info("Starting fix of apostrophe issues...")
    
    # Check for command line arguments (file path)
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        # Default to the BDD step definitions file
        bdd_dir = os.path.join(os.getcwd(), "summary", "bdd_test_cases")
        file_path = os.path.join(bdd_dir, "steps", "api_steps.py")
    
    if fix_apostrophe_issues(file_path):
        logging.info(f"Successfully fixed apostrophe issues in {file_path}")
        return 0
    else:
        logging.error(f"Failed to fix apostrophe issues in {file_path}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 