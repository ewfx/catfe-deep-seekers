#!/usr/bin/env python
import sys
import os
import ast
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def check_syntax(file_path):
    """Check Python file for syntax errors"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        ast.parse(content)
        logging.info(f"✅ No syntax errors found in {file_path}")
        return True
    except SyntaxError as e:
        logging.error(f"❌ Syntax error in {file_path}: {e}")
        logging.error(f"  Line {e.lineno}, Column {e.offset}")
        logging.error(f"  {e.text}")
        return False
    except Exception as e:
        logging.error(f"❌ Error checking {file_path}: {e}")
        return False

def main():
    """Main function"""
    # Check the api_steps.py file
    steps_file = os.path.join("summary", "bdd_test_cases", "steps", "api_steps.py")
    if not os.path.exists(steps_file):
        logging.error(f"❌ File not found: {steps_file}")
        return 1
    
    if check_syntax(steps_file):
        logging.info("✅ Step definitions file is syntactically correct")
        return 0
    else:
        logging.error("❌ Syntax errors found in step definitions file")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 