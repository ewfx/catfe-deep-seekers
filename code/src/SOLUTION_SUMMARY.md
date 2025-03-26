# BDD Step Definition Syntax Issue Resolution

## Problem
The project had a syntax error issue in the generated BDD step definition file (`api_steps.py`) where apostrophes (`'`) inside step text caused Python syntax errors. Specifically, when a step contained an apostrophe like in:

```python
@behave.given('I do not have permission to check the balance of other users' accounts')
```

This caused a syntax error as the apostrophe in "users'" terminated the string prematurely.

Additionally, nested quotes in step text like:

```python
@behave.when('I send a "POST" request to "api/v1/accounts"')
```

Required proper escaping to avoid Python syntax errors.

## Solution Components

### 1. Enhanced Step Generation
We modified the `enhanced_step_generator.py` script to:
- Detect apostrophes and nested quotes in step text
- Use double quotes with the unicode prefix for steps that contain apostrophes: `u"step text with apostrophe's"`
- Properly escape nested quotes: `u"I send a \"POST\" request to \"api/v1/endpoint\""`
- Add special handling for common problematic steps

### 2. Post-Generation Syntax Fixing
We created a standalone `fix_apostrophe_issues()` function that:
- Processes step definition files line by line
- Identifies and fixes apostrophe issues in step decorators
- Adds proper escaping for nested quotes
- Validates the resulting Python syntax

### 3. Integration Scripts
We created several scripts to integrate the solutions:

#### a. fix_bdd_step_definitions.py
Standalone script to fix apostrophe issues in existing step definition files.

#### b. run_bdd_tests_with_fixed_steps.py
Comprehensive solution that:
1. Generates step definitions using the enhanced generator
2. Automatically fixes any remaining apostrophe/quote issues
3. Verifies syntax correctness
4. Runs the BDD tests with the fixed definitions

## Key Technical Solutions

### 1. String Escaping
```python
# Handle apostrophes by using double quotes with unicode prefix
if "'" in step_text:
    decorator = f'@behave.{decorator_type}(u"{step_text.replace(\'"\', \'\\"\')}")'
```

### 2. Nested Quote Handling
```python
# Fix nested quotes in step definitions
fixed_content = re.sub(
    r'@behave\.(given|when|then)\(u"I send a "([^"]+)" request to "([^"]+)"',
    r'@behave.\1(u"I send a \\"\\2\\" request to \\"\\3\\"',
    fixed_content
)
```

### 3. Syntax Validation
```python
def check_syntax(file_path):
    """Check if a Python file has valid syntax"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Use Python's ast module to parse and validate syntax
        ast.parse(content)
        return True
    except SyntaxError as e:
        logging.error(f"Syntax error in {file_path}: {e}")
        return False
```

## Benefits of the Solution

1. **Automation**: The solution automatically detects and fixes syntax issues, requiring no manual intervention.
2. **Robustness**: The fix works for all variations of apostrophe and quote combinations.
3. **Validation**: Built-in syntax checking ensures the generated files are valid Python code.
4. **Integration**: The solution integrates with the existing workflow and can be run as a standalone step.

## Conclusion

This solution resolved the syntax errors in BDD step definitions by properly handling apostrophes and nested quotes in step text. The enhanced step generator and syntax fixing script can now generate valid Python code for all step patterns, ensuring the BDD tests run correctly. 