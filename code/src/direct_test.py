#!/usr/bin/env python
"""
Directly test the fix_apostrophe_issues function in run_everything.py

This script:
1. Imports the fix_apostrophe_issues function from run_everything.py
2. Calls it directly on the api_steps.py file
3. Then runs the behave tests

Usage:
    python direct_test.py
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

def main():
    """Main function"""
    logging.info("Directly testing fix_apostrophe_issues function...")
    
    # First, check if run_everything.py exists
    if not os.path.exists("run_everything.py"):
        logging.error("run_everything.py not found")
        return 1
    
    # Determine the BDD directory
    bdd_dir = os.path.join(os.getcwd(), "summary", "bdd_test_cases")
    if not os.path.exists(bdd_dir):
        logging.error(f"BDD directory not found: {bdd_dir}")
        return 1
    
    api_steps_path = os.path.join(bdd_dir, "steps", "api_steps.py")
    if not os.path.exists(api_steps_path):
        logging.error(f"API steps file not found: {api_steps_path}")
        return 1
    
    try:
        # Load run_everything.py to extract the fix_apostrophe_issues function
        with open("run_everything.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Extract the function definition
        function_start = content.find("def fix_apostrophe_issues")
        if function_start == -1:
            logging.error("Could not find fix_apostrophe_issues function")
            return 1
        
        function_end = content.find("def ", function_start + 1)
        if function_end == -1:
            function_end = len(content)
        
        function_code = content[function_start:function_end]
        
        # Create a temporary module with just this function
        with open("temp_fix_function.py", "w", encoding="utf-8") as f:
            f.write("""
import os
import logging
import re
import shutil

# Setup logging if not already set up
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
""")
            f.write(function_code)
            
            # Add a main function to execute the test
            f.write("""
if __name__ == "__main__":
    api_steps_path = r"{}"
    fix_apostrophe_issues(api_steps_path)
    print("Fix completed")
""".format(api_steps_path.replace("\\", "\\\\")))
        
        # Run the temporary module
        logging.info(f"Running fix_apostrophe_issues on {api_steps_path}")
        result = subprocess.run(
            ["python", "temp_fix_function.py"],
            check=False
        )
        
        if result.returncode != 0:
            logging.error(f"Fix function failed with return code {result.returncode}")
            return 1
        
        logging.info("Successfully fixed apostrophe issues")
        
        # Now run the behave tests
        logging.info(f"Running behave in {bdd_dir}")
        behave_result = subprocess.run(
            ["behave", "--no-capture"],
            cwd=bdd_dir,
            check=False
        )
        
        if behave_result.returncode == 0:
            logging.info("Behave tests completed successfully")
            return 0
        else:
            logging.error(f"Behave tests failed with return code {behave_result.returncode}")
            return 1
            
    except Exception as e:
        logging.error(f"Error: {e}")
        return 1
    finally:
        # Clean up temporary file
        if os.path.exists("temp_fix_function.py"):
            try:
                os.remove("temp_fix_function.py")
            except:
                pass

if __name__ == "__main__":
    sys.exit(main()) 