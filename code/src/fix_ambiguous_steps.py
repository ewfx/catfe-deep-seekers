#!/usr/bin/env python
"""
Fix Ambiguous Step Definitions

This script fixes ambiguous step definitions in BDD step files by:
1. Finding all step definition files
2. Identifying ambiguous steps
3. Commenting out the specific steps that conflict with parameterized steps

Usage:
    python fix_ambiguous_steps.py
"""

import os
import re
import logging
import shutil

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def fix_ambiguous_steps(file_path):
    """Fix ambiguous step definitions in a file"""
    logging.info(f"Fixing ambiguous steps in {file_path}")
    
    if not os.path.exists(file_path):
        logging.error(f"File not found: {file_path}")
        return False
    
    # Make a backup of the original file
    backup_path = file_path + ".bak"
    shutil.copy2(file_path, backup_path)
    logging.info(f"Backed up original file to {backup_path}")
    
    # Read the file content
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Look for the parameterized status code step pattern
    param_pattern = r'@(?:behave\.)?then\((?:u)?[\'"]I should receive a \{status_code:d\} status code[\'"]'
    has_parameterized = re.search(param_pattern, content) is not None
    
    if not has_parameterized:
        logging.info(f"No parameterized status code step found in {file_path}, skipping")
        return True
    
    # Find specific status code steps
    specific_pattern = r'(@(?:behave\.)?then\((?:u)?[\'"]I should receive a (\d+) status code[\'"].*?def.*?\))'
    
    # Process the file line by line to handle the specific step definitions
    lines = content.split('\n')
    
    for i in range(len(lines)):
        # Check if line contains a specific status code step definition
        if re.search(r'@(?:behave\.)?then\((?:u)?[\'"]I should receive a \d+ status code[\'"]', lines[i]):
            if not lines[i].strip().startswith('#'):
                # Comment out the line 
                lines[i] = '# ' + lines[i] + ' # Commented out to avoid ambiguity with parameterized version'
                logging.info(f"Commented out ambiguous step at line {i+1}")
                
                # Also comment out the function definition and body
                j = i + 1
                while j < len(lines) and (lines[j].startswith('def ') or lines[j].startswith('    ')):
                    if not lines[j].strip().startswith('#'):
                        lines[j] = '# ' + lines[j]
                    j += 1
    
    # Write the modified content back to the file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    logging.info(f"Fixed ambiguous steps in {file_path}")
    return True

def find_and_fix_step_definitions():
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
                
                # Fix ambiguous steps
                fix_ambiguous_steps(file_path)
    
    return True

if __name__ == "__main__":
    logging.info("Starting ambiguous step definitions fix...")
    find_and_fix_step_definitions()
    logging.info("Completed fixing ambiguous step definitions") 