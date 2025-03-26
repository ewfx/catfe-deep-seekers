#!/usr/bin/env python
import os
import re
import sys
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
        
        # Check for apostrophes in step text
        if "'" in line:
            # This is a potentially problematic line
            if line.startswith('@behave.given'):
                decorator_type = 'given'
            elif line.startswith('@behave.when'):
                decorator_type = 'when'
            elif line.startswith('@behave.then'):
                decorator_type = 'then'
            else:
                continue
                
            # Extract the step text
            match = re.search(r"@behave\." + decorator_type + r"\((?:u)?['\"](.+?)['\"]", line)
            if match:
                step_text = match.group(1)
                
                # Handle nested quotes and apostrophes
                if '"' in step_text or "'" in step_text:
                    # We have nested quotes or apostrophes - needs fixing
                    step_text = step_text.replace('"', '\\"')
                    # Convert to double-quoted string
                    lines[i] = f'@behave.{decorator_type}(u"{step_text}")'
    
    fixed_content = '\n'.join(lines)
    
    # Additional specific fixes for common issues
    # Fix nested quotes in step definitions
    fixed_content = re.sub(
        r'@behave\.(given|when|then)\(u"I send a "([^"]+)" request to "([^"]+)"',
        r'@behave.\1(u"I send a \\"\\2\\" request to \\"\\3\\"',
        fixed_content
    )
    
    # Save the fixed content
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(fixed_content)
    
    logging.info(f"Fixed apostrophe issues in {file_path}")
    return True

def check_syntax(file_path):
    """Check if a Python file has valid syntax"""
    logging.info(f"Checking syntax of {file_path}")
    
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", file_path],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        logging.info(f"Syntax check passed for {file_path}")
        return True
    else:
        logging.error(f"Syntax check failed for {file_path}: {result.stderr}")
        return False

def run_with_automatic_fixes():
    """Run the integration script with automatic fixes for step definitions"""
    script_dir = Path(__file__).parent.absolute()
    api_steps_path = script_dir / "summary" / "bdd_test_cases" / "steps" / "api_steps.py"
    
    # Step 1: Back up the original api_steps.py file if it exists
    if api_steps_path.exists():
        backup_path = str(api_steps_path) + ".bak"
        shutil.copy2(api_steps_path, backup_path)
        logging.info(f"Backed up original api_steps.py to {backup_path}")
    
    # Step 2: Run the enhanced step generator
    logging.info("Running enhanced step generator...")
    result = subprocess.run(
        [sys.executable, "enhanced_step_generator.py"],
        capture_output=True,
        text=True
    )
    logging.info(f"Enhanced step generator output: {result.stdout}")
    
    # Step 3: Fix apostrophe issues in the generated file
    if api_steps_path.exists():
        fix_apostrophe_issues(api_steps_path)
        
        # Verify the syntax is correct
        if not check_syntax(api_steps_path):
            logging.error("Syntax check failed after fixing apostrophe issues")
            return 1
    else:
        logging.error(f"Generated step definitions file not found at {api_steps_path}")
        return 1
    
    # Step 4: Run the main script with fixed step definitions
    logging.info("Running run_everything_fixed.py...")
    process = subprocess.Popen(
        [sys.executable, "run_everything_fixed.py"],
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
        logging.info("Successfully ran run_everything_fixed.py with fixed step definitions!")
    else:
        logging.error(f"Error running run_everything_fixed.py: Return code {return_code}")
    
    return return_code

if __name__ == "__main__":
    sys.exit(run_with_automatic_fixes()) 