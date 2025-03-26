import os
import sys
import re
import logging

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
        if "'" in line and ("accounts'" in line or "users'" in line):
            # This is a problematic line
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
                
                # Handle nested quotes
                step_text = step_text.replace('"', '\\"')
                
                # Create new line with proper escaping
                lines[i] = f'@behave.{decorator_type}(u"{step_text}")'
    
    fixed_content = '\n'.join(lines)
    
    # Additional fixes for known problematic lines
    # Fix for apostrophe in step definition
    fixed_content = fixed_content.replace(
        '@behave.given("I do not have permission to check the balance of other users\' accounts")',
        '@behave.given(u"I do not have permission to check the balance of other users\' accounts")'
    )
    
    # Fix for nested quotes in step definition
    fixed_content = fixed_content.replace(
        '@behave.when(u"I send a "POST" request to "api/v1/accounts" with another user\'s account ID to check their account balance")',
        '@behave.when(u"I send a \\"POST\\" request to \\"api/v1/accounts\\" with another user\'s account ID to check their account balance")'
    )
    
    # Save the fixed content
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(fixed_content)
    
    logging.info(f"Fixed apostrophe issues in {file_path}")
    return True

def main():
    """Main function"""
    file_path = "summary/bdd_test_cases/steps/api_steps.py"
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    
    success = fix_apostrophe_issues(file_path)
    
    if success:
        logging.info("Successfully fixed apostrophe issues in step definitions file.")
        return 0
    else:
        logging.error("Failed to fix apostrophe issues in step definitions file.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 