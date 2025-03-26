#!/usr/bin/env python
"""
Run BDD Tests with Fixed Step Definitions

This script:
1. Fixes apostrophe issues in step definitions
2. Properly formats step definitions to handle quotes and apostrophes
3. Runs the BDD tests using behave against the actual application

Usage:
    python run_bdd_with_fixed_steps.py
"""

import os
import sys
import re
import logging
import subprocess
import shutil
import tempfile
from pathlib import Path
import ast

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
    
    # Fix more complex apostrophe issues
    fixed_content = fixed_content.replace(
        "@behave.when('I send a \"POST\" request to \"api/v1/accounts\" with another user's account ID to check their account balance')",
        '@behave.when(u"I send a \\"POST\\" request to \\"api/v1/accounts\\" with another user\'s account ID to check their account balance")'
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

def enhance_step_definitions(bdd_dir):
    """Generate enhanced step definitions with all fixes"""
    logging.info("Generating enhanced step definitions...")
    
    steps_dir = os.path.join(bdd_dir, "steps")
    os.makedirs(steps_dir, exist_ok=True)
    
    api_steps_path = os.path.join(steps_dir, "api_steps.py")
    if os.path.exists(api_steps_path):
        # Backup the original file
        backup_path = api_steps_path + ".bak"
        shutil.copy2(api_steps_path, backup_path)
        logging.info(f"Backed up original api_steps.py to {backup_path}")
    
    # Run the enhanced step generator
    try:
        result = subprocess.run(
            [sys.executable, "enhanced_step_generator.py"],
            check=True,
            capture_output=True,
            text=True
        )
        logging.info(f"Enhanced step generator output: {result.stdout}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error running enhanced step generator: {e.stderr}")
        return False
    
    # Fix apostrophe issues in generated file
    if os.path.exists(api_steps_path):
        fix_apostrophe_issues(api_steps_path)
        
        # Verify syntax
        if not check_syntax(api_steps_path):
            logging.error("Syntax issues remain after fixing apostrophes")
            return False
    else:
        logging.error(f"Generated step definitions file not found at {api_steps_path}")
        return False
    
    logging.info("Successfully enhanced step definitions")
    return True

def run_bdd_tests_with_behave(bdd_dir):
    """Run BDD tests using behave"""
    logging.info("Running BDD tests using behave...")
    
    # Prepare behave command
    behave_cmd = "behave"
    if sys.platform == "win32":
        # Look for behave in Python scripts directory
        python_scripts = os.path.join(os.path.dirname(sys.executable), "Scripts")
        behave_path = os.path.join(python_scripts, "behave.exe")
        if os.path.exists(behave_path):
            behave_cmd = behave_path
    
    # Run behave with appropriate options
    try:
        cmd = [
            behave_cmd,
            "-f", "pretty",
            "-o", os.path.join(bdd_dir, "reports", "bdd_report.txt"),
            "--junit",
            "--junit-directory", os.path.join(bdd_dir, "reports"),
            bdd_dir
        ]
        
        logging.info(f"Executing command: {' '.join(cmd)}")
        
        # Set environment variables for the subprocess
        env = os.environ.copy()
        env["PYTHONPATH"] = os.path.abspath(os.path.dirname(bdd_dir))
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
            universal_newlines=True,
            bufsize=1
        )
        
        # Print output in real-time
        for line in iter(process.stdout.readline, ''):
            print(line, end='')
        
        process.stdout.close()
        return_code = process.wait()
        
        if return_code == 0:
            logging.info("BDD tests completed successfully!")
        else:
            logging.warning(f"BDD tests completed with return code {return_code}")
        
        return return_code
    except Exception as e:
        logging.error(f"Error running BDD tests: {e}")
        return 1

def main():
    """Main function"""
    logging.info("Starting BDD tests with fixed step definitions")
    
    # Define paths
    bdd_dir = "summary/bdd_test_cases"
    os.makedirs(os.path.join(bdd_dir, "reports"), exist_ok=True)
    
    # Step 1: Generate enhanced step definitions
    if not enhance_step_definitions(bdd_dir):
        logging.error("Failed to enhance step definitions")
        return 1
    
    # Step 2: Run BDD tests with behave
    return run_bdd_tests_with_behave(bdd_dir)

if __name__ == "__main__":
    sys.exit(main()) 