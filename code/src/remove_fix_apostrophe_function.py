#!/usr/bin/env python
"""
Remove the fix_apostrophe_issues function and its call from run_everything.py

This script:
1. Removes the fix_apostrophe_issues function definition
2. Removes the call to this function in run_bdd_tests

Usage:
    python remove_fix_apostrophe_function.py
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

def remove_fix_function():
    """Remove the fix_apostrophe_issues function from run_everything.py"""
    logging.info("Removing fix_apostrophe_issues function from run_everything.py")
    
    # Check if run_everything.py exists
    if not os.path.exists("run_everything.py"):
        logging.error("run_everything.py not found")
        return False
    
    # Create a backup
    backup_path = "run_everything.py.bak_clean"
    shutil.copy2("run_everything.py", backup_path)
    logging.info(f"Created backup at {backup_path}")
    
    # Read the file
    with open("run_everything.py", 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if the function exists
    if "def fix_apostrophe_issues" not in content:
        logging.info("fix_apostrophe_issues function not found in run_everything.py")
        return True
    
    # Remove the function definition
    content = re.sub(
        r'def fix_apostrophe_issues.*?return True\n',
        '',
        content,
        flags=re.DOTALL
    )
    
    # Remove the call to the function in run_bdd_tests
    content = re.sub(
        r'# Fix apostrophe issues in step definitions\s+api_steps_path = os\.path\.join\(bdd_dir, "steps", "api_steps\.py"\)\s+if os\.path\.exists\(api_steps_path\):\s+fix_apostrophe_issues\(api_steps_path\).*?logging\.warning\(f"Step definitions file not found at \{api_steps_path\}"\)',
        '',
        content,
        flags=re.DOTALL
    )
    
    # Write the modified content
    with open("run_everything.py", 'w', encoding='utf-8') as f:
        f.write(content)
    
    logging.info("Successfully removed fix_apostrophe_issues function from run_everything.py")
    return True

def main():
    """Main function"""
    logging.info("Starting removal of fix function...")
    
    if remove_fix_function():
        logging.info("Successfully removed fix_apostrophe_issues function and its call")
        return 0
    else:
        logging.error("Failed to remove fix_apostrophe_issues function")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 