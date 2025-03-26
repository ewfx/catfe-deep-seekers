#!/usr/bin/env python
"""
Run the fixed version of run_everything.py

This script:
1. Fixes apostrophe issues in step definitions using our standalone fix function
2. Runs run_everything.py to execute the full workflow

Usage:
    python run_fixed_everything.py
"""

import os
import sys
import logging
import subprocess
import importlib.util

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def import_fix_function():
    """Import the fix_apostrophe_issues function from fix_apostrophe_function.py"""
    logging.info("Importing fix_apostrophe_issues function")
    
    # Check if fix_apostrophe_function.py exists
    if not os.path.exists("fix_apostrophe_function.py"):
        logging.error("fix_apostrophe_function.py not found")
        return None
    
    try:
        # Import the module
        spec = importlib.util.spec_from_file_location("fix_apostrophe_function", "fix_apostrophe_function.py")
        fix_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fix_module)
        
        # Check if the module has the required function
        if hasattr(fix_module, "fix_apostrophe_issues"):
            return fix_module.fix_apostrophe_issues
        else:
            logging.error("fix_apostrophe_issues function not found in fix_apostrophe_function.py")
            return None
    except Exception as e:
        logging.error(f"Error importing fix_apostrophe_function.py: {e}")
        return None

def fix_step_definitions():
    """Fix the step definitions file"""
    logging.info("Fixing step definitions")
    
    # Import the fix function
    fix_function = import_fix_function()
    if not fix_function:
        return False
    
    # Determine the BDD directory
    bdd_dir = os.path.join(os.getcwd(), "summary", "bdd_test_cases")
    if not os.path.exists(bdd_dir):
        logging.error(f"BDD directory not found: {bdd_dir}")
        return False
    
    # Fix the step definitions file
    api_steps_path = os.path.join(bdd_dir, "steps", "api_steps.py")
    if not os.path.exists(api_steps_path):
        logging.error(f"API steps file not found: {api_steps_path}")
        return False
    
    logging.info(f"Fixing apostrophe issues in {api_steps_path}")
    if not fix_function(api_steps_path):
        logging.error("Failed to fix apostrophe issues")
        return False
    
    logging.info("✅ Step definitions fixed successfully")
    return True

def run_everything():
    """Run run_everything.py"""
    logging.info("Running run_everything.py")
    
    # Check if run_everything.py exists
    if not os.path.exists("run_everything.py"):
        logging.error("run_everything.py not found")
        return False
    
    try:
        # Run run_everything.py as a subprocess
        logging.info("Starting run_everything.py")
        process = subprocess.Popen(
            ["python", "run_everything.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Display output in real-time
        for line in process.stdout:
            line = line.strip()
            if line:
                logging.info(f"[run_everything] {line}")
        
        # Wait for the process to complete
        process.wait()
        
        if process.returncode == 0:
            logging.info("✅ run_everything.py completed successfully")
            return True
        else:
            logging.error(f"❌ run_everything.py failed with return code {process.returncode}")
            return False
    except Exception as e:
        logging.error(f"Error running run_everything.py: {e}")
        return False

def main():
    """Main function"""
    logging.info("Starting run_fixed_everything.py")
    
    # Fix step definitions
    if not fix_step_definitions():
        logging.error("Failed to fix step definitions")
        return 1
    
    # Run run_everything.py
    if not run_everything():
        logging.error("Failed to run run_everything.py")
        return 1
    
    logging.info("✅ run_fixed_everything.py completed successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 