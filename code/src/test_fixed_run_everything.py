#!/usr/bin/env python
"""
Test if our fix for run_everything.py works properly

This script:
1. Tests running just the BDD tests with the fixed apostrophe issues function
2. Provides a simplified testing approach

Usage:
    python test_fixed_run_everything.py
"""

import os
import sys
import logging
import importlib.util
import subprocess

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def test_run_bdd_tests():
    """Test running just the BDD tests from run_everything.py"""
    logging.info("Testing the BDD tests from run_everything.py")
    
    # First, check if run_everything.py exists
    if not os.path.exists("run_everything.py"):
        logging.error("run_everything.py not found")
        return False
    
    try:
        # Import the run_everything.py module
        spec = importlib.util.spec_from_file_location("run_everything", "run_everything.py")
        run_everything = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(run_everything)
        
        # Check if the module has the required functions
        if not hasattr(run_everything, "run_bdd_tests"):
            logging.error("run_bdd_tests function not found in run_everything.py")
            return False
        
        if not hasattr(run_everything, "fix_apostrophe_issues"):
            logging.error("fix_apostrophe_issues function not found in run_everything.py")
            return False
        
        # Determine the BDD directory
        bdd_dir = os.path.join(os.getcwd(), "summary", "bdd_test_cases")
        if not os.path.exists(bdd_dir):
            logging.error(f"BDD directory not found: {bdd_dir}")
            return False
        
        # Run the BDD tests
        logging.info(f"Running BDD tests from {bdd_dir}")
        success = run_everything.run_bdd_tests(bdd_dir)
        
        if success:
            logging.info("BDD tests completed successfully")
            return True
        else:
            logging.error("BDD tests failed")
            return False
        
    except Exception as e:
        logging.error(f"Error testing run_everything.py: {e}")
        return False

def run_directly():
    """Run the BDD tests directly using behave"""
    logging.info("Running BDD tests directly using behave")
    
    bdd_dir = os.path.join(os.getcwd(), "summary", "bdd_test_cases")
    if not os.path.exists(bdd_dir):
        logging.error(f"BDD directory not found: {bdd_dir}")
        return False
    
    api_steps_path = os.path.join(bdd_dir, "steps", "api_steps.py")
    
    # Run the fix_apostrophe_issues function directly
    try:
        spec = importlib.util.spec_from_file_location("run_everything", "run_everything.py")
        run_everything = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(run_everything)
        
        if hasattr(run_everything, "fix_apostrophe_issues"):
            logging.info(f"Fixing apostrophe issues in {api_steps_path}")
            run_everything.fix_apostrophe_issues(api_steps_path)
        else:
            logging.error("fix_apostrophe_issues function not found")
            return False
    except Exception as e:
        logging.error(f"Error fixing apostrophe issues: {e}")
        return False
    
    # Run behave directly
    try:
        logging.info(f"Running behave in {bdd_dir}")
        result = subprocess.run(
            ["behave", "--no-capture"],
            cwd=bdd_dir,
            check=False
        )
        
        if result.returncode == 0:
            logging.info("Behave tests completed successfully")
            return True
        else:
            logging.error(f"Behave tests failed with return code {result.returncode}")
            return False
    except Exception as e:
        logging.error(f"Error running behave: {e}")
        return False

def main():
    """Main function"""
    logging.info("Starting test of run_everything.py...")
    
    # Try to run the BDD tests using the function from run_everything.py
    if test_run_bdd_tests():
        logging.info("Successfully ran BDD tests using run_everything.py")
        return 0
    else:
        logging.warning("Failed to run BDD tests using run_everything.py, trying direct execution")
        
        # Try to run the BDD tests directly
        if run_directly():
            logging.info("Successfully ran BDD tests directly")
            return 0
        else:
            logging.error("Failed to run BDD tests")
            return 1

if __name__ == "__main__":
    sys.exit(main()) 