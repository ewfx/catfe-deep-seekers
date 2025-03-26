import os
import re
import sys
import logging
import ast

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def check_apostrophe_issues(file_path):
    """Check if there are any apostrophe issues in the file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all behave decorator lines
    decorator_lines = re.findall(r'@behave\.(given|when|then)\([^)]+\)', content)
    problem_lines = []
    
    # Find all decorator lines with an apostrophe
    apostrophe_decorator_lines = []
    for line_no, line in enumerate(content.split('\n'), start=1):
        if '@behave.' in line and "'" in line:
            if "u'" in line and "')" in line and "'" in line[line.find("u'")+2:line.rfind("')")]:
                problem_lines.append((line_no, line))
    
    if problem_lines:
        logging.error(f"Found {len(problem_lines)} lines with potential apostrophe issues:")
        for line_no, line in problem_lines:
            logging.error(f"  Line {line_no}: {line}")
        return False
    
    logging.info("No apostrophe issues found in decorators.")
    
    # Also check if the file has valid Python syntax
    try:
        ast.parse(content)
        logging.info("File has valid Python syntax.")
        return True
    except SyntaxError as e:
        logging.error(f"Syntax error in {file_path}: {e}")
        return False

def check_step_coverage(step_file, feature_dir):
    """Check if all steps in feature files are covered"""
    # Get all steps from feature files
    all_steps = set()
    feature_files = [os.path.join(feature_dir, f) for f in os.listdir(feature_dir) if f.endswith('.feature')]
    
    for feature_file in feature_files:
        with open(feature_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract steps from the feature file
        steps = re.findall(r'(Given|When|Then|And)\s+(.+?)$', content, re.MULTILINE)
        for step_type, step_text in steps:
            all_steps.add(step_text.strip())
    
    # Get all step implementations
    with open(step_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    implemented_steps = []
    step_decorators = re.findall(r'@behave\.(given|when|then)\([^)]+\)', content)
    
    # Check if all steps are implemented
    missing_steps = []
    for step in all_steps:
        found = False
        pattern = re.escape(step).replace('\\"', '[^"]*').replace('\\$\\d+', '\\$\\d+')
        if re.search(pattern, content, re.IGNORECASE):
            found = True
        
        if not found:
            missing_steps.append(step)
    
    if missing_steps:
        logging.warning(f"Found {len(missing_steps)} steps without implementations:")
        for step in missing_steps:
            logging.warning(f"  - {step}")
        return False
    
    logging.info(f"All {len(all_steps)} steps have implementations.")
    return True

def main():
    step_file = "summary/bdd_test_cases/steps/api_steps.py"
    feature_dir = "summary/bdd_test_cases"
    
    if not os.path.exists(step_file):
        logging.error(f"Step file not found: {step_file}")
        return False
    
    apostrophe_check = check_apostrophe_issues(step_file)
    coverage_check = check_step_coverage(step_file, feature_dir)
    
    if apostrophe_check and coverage_check:
        logging.info("✅ All checks passed successfully!")
        return True
    else:
        logging.error("❌ Some checks failed.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 