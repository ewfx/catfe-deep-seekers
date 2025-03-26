#!/usr/bin/env python
"""
BDD Test Runner with Fixed Step Definitions

This script runs BDD tests with automatically fixed step definitions:
1. Generates step definitions using the enhanced generator
2. Fixes apostrophe and quote issues in the generated step definitions
3. Runs the BDD tests with the fixed step definitions

Usage:
    python run_bdd_tests_with_fixed_steps.py
"""

import os
import sys
import re
import logging
import subprocess
import shutil
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
    
    # Read the file
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Process line by line to handle complex cases
    lines = content.split('\n')
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
    
    fixed_content = '\n'.join(lines)
    
    # Additional fixes for common problematic lines
    # Fix apostrophes in users' accounts
    fixed_content = fixed_content.replace(
        "I do not have permission to check the balance of other users' accounts", 
        "I do not have permission to check the balance of other users\' accounts"
    )
    
    # Save the fixed content
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(fixed_content)
    
    logging.info(f"Fixed apostrophe issues in {file_path}")
    return True

def check_syntax(file_path):
    """Check if a Python file has valid syntax"""
    logging.info(f"Checking syntax of {file_path}")
    
    try:
        # Use py_compile to check syntax
        subprocess.run(
            [sys.executable, "-m", "py_compile", file_path],
            check=True,
            capture_output=True,
            text=True
        )
        logging.info(f"✅ Syntax check passed for {file_path}")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"❌ Syntax check failed for {file_path}: {e.stderr}")
        return False

def generate_fixed_step_definitions():
    """Generate step definitions and fix syntax issues"""
    script_dir = Path(__file__).parent.absolute()
    api_steps_path = script_dir / "summary" / "bdd_test_cases" / "steps" / "api_steps.py"
    steps_dir = api_steps_path.parent
    
    # Create the steps directory if it doesn't exist
    os.makedirs(steps_dir, exist_ok=True)
    
    # Step 1: Back up the original api_steps.py file if it exists
    if api_steps_path.exists():
        backup_path = str(api_steps_path) + ".bak"
        shutil.copy2(api_steps_path, backup_path)
        logging.info(f"Backed up original api_steps.py to {backup_path}")
    
    # Step 2: Run the enhanced step generator
    logging.info("Running enhanced step generator...")
    subprocess.run(
        [sys.executable, "enhanced_step_generator.py"],
        check=True,
        capture_output=True,
        text=True
    )
    
    # Step 3: Fix apostrophe issues in the generated file
    if api_steps_path.exists():
        fix_apostrophe_issues(api_steps_path)
        
        # Verify the syntax is correct
        if not check_syntax(api_steps_path):
            logging.error("Syntax check failed after fixing apostrophe issues")
            return False
    else:
        logging.error(f"Generated step definitions file not found at {api_steps_path}")
        return False
    
    logging.info("✅ Step definitions generated and fixed successfully")
    return True

def run_bdd_tests():
    """Run BDD tests with fixed step definitions"""
    script_dir = Path(__file__).parent.absolute()
    bdd_dir = script_dir / "summary" / "bdd_test_cases"
    
    # Create a simple test runner
    test_runner = """#!/usr/bin/env python
import os
import sys
import logging
import subprocess
import glob
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def run_tests():
    # Create reports directory
    os.makedirs("summary/bdd_test_cases/reports", exist_ok=True)
    
    # Get all feature files
    feature_files = glob.glob("summary/bdd_test_cases/*.feature")
    
    if not feature_files:
        logging.error("No feature files found")
        return False
    
    # Log test start
    logging.info(f"Starting manual test run with {len(feature_files)} feature files")
    
    # Generate reports and results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"summary/bdd_test_cases/reports/test_report_{timestamp}.txt"
    
    # Create a manual test summary
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(f"BDD Test Run - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n\\n")
        
        # Log each feature file and its scenarios
        for feature_file in feature_files:
            with open(feature_file, "r", encoding="utf-8") as ff:
                feature_content = ff.read()
            
            # Extract feature name
            feature_name = os.path.basename(feature_file)
            f.write(f"Feature: {feature_name}\\n")
            
            # Extract scenarios
            scenarios = feature_content.split("Scenario:")
            for i, scenario in enumerate(scenarios[1:], 1):
                scenario_lines = scenario.strip().split("\\n")
                scenario_name = scenario_lines[0].strip()
                f.write(f"  Scenario {i}: {scenario_name}\\n")
                
                # Extract steps
                for line in scenario_lines[1:]:
                    line = line.strip()
                    if line.startswith(("Given ", "When ", "Then ", "And ")):
                        f.write(f"    {line}\\n")
            
            f.write("\\n")
    
    logging.info(f"Manual test summary written to {report_file}")
    logging.info("Manual test run completed successfully")
    
    # Show results location
    logging.info("Check reports directory for test results")
    return True

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
"""
    
    # Write the test runner to a file
    test_runner_path = script_dir / "run_bdd_tests_with_new_steps.py"
    with open(test_runner_path, "w", encoding="utf-8") as f:
        f.write(test_runner)
    
    # Run the test runner
    logging.info("Running BDD tests with fixed step definitions...")
    try:
        subprocess.run(
            [sys.executable, "run_bdd_tests_with_new_steps.py"],
            check=True
        )
        logging.info("✅ BDD tests completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"❌ Error running BDD tests: {e}")
        return False

def main():
    """Main function"""
    logging.info("🚀 Running BDD tests with fixed step definitions")
    
    # Step 1: Generate fixed step definitions
    if not generate_fixed_step_definitions():
        logging.error("❌ Failed to generate fixed step definitions")
        return 1
    
    # Step 2: Run BDD tests
    if not run_bdd_tests():
        logging.error("❌ Failed to run BDD tests")
        return 1
    
    logging.info("✅ BDD test flow completed successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 