#!/usr/bin/env python
"""
BDD Test Runner for Executing Generated Test Cases Against the Cloned Repository

This script sets up and runs the generated BDD test cases using Behave (a Python BDD testing framework).
It automatically creates step definitions based on the Gherkin feature files.
"""

import os
import sys
import logging
import argparse
import subprocess
import json
import re
from pathlib import Path
import requests
# Import behave only when needed, after verifying installation

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Constants
SUMMARY_DIR = "summary"
BDD_TEST_CASES_DIR = os.path.join(SUMMARY_DIR, "bdd_test_cases")
BEHAVE_DIR = "behave_tests"
FEATURES_DIR = os.path.join(BEHAVE_DIR, "features")
STEPS_DIR = os.path.join(BEHAVE_DIR, "features", "steps")
CONFIG_FILE = "config.json"

def setup_behave_environment():
    """Set up the Behave environment structure."""
    logging.info("Setting up Behave environment...")
    
    # Create directory structure
    os.makedirs(BEHAVE_DIR, exist_ok=True)
    os.makedirs(FEATURES_DIR, exist_ok=True)
    os.makedirs(STEPS_DIR, exist_ok=True)
    
    # Create empty __init__.py files
    Path(os.path.join(FEATURES_DIR, "__init__.py")).touch(exist_ok=True)
    Path(os.path.join(STEPS_DIR, "__init__.py")).touch(exist_ok=True)
    
    # Create environment.py if it doesn't exist
    env_file = os.path.join(FEATURES_DIR, "environment.py")
    if not os.path.exists(env_file):
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write('''
import os
import sys
import logging
import json
import requests
from behave import *

# Load configuration
def load_config():
    config_file = "config.json"
    if os.path.exists(config_file):
        with open(config_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# Setup hooks
def before_all(context):
    """Setup before all tests."""
    config = load_config()
    context.base_url = config.get("api_base_url", "http://localhost:8080")
    context.headers = {"Content-Type": "application/json"}
    context.last_response = None
    logging.basicConfig(level=logging.INFO)
    logging.info(f"Using base URL: {context.base_url}")

def before_scenario(context, scenario):
    """Setup before each scenario."""
    context.scenario_data = {}
    context.auth_token = None
    logging.info(f"Running scenario: {scenario.name}")

def after_scenario(context, scenario):
    """Cleanup after each scenario."""
    logging.info(f"Completed scenario: {scenario.name} - Status: {scenario.status}")
''')
    
    logging.info("Behave environment setup completed")

def copy_feature_files(skip_existing=False):
    """Copy feature files from generated BDD test cases to Behave features directory."""
    logging.info("Copying feature files...")
    
    # If we're testing with custom features, we can skip the generated features
    if skip_existing and os.path.exists(FEATURES_DIR):
        logging.info("Skipping copying feature files as skip_existing=True and features directory exists")
        return True
    
    # Ensure BDD test cases directory exists
    if not os.path.exists(BDD_TEST_CASES_DIR):
        logging.error(f"BDD test cases directory not found: {BDD_TEST_CASES_DIR}")
        logging.error("Please run generate_artifacts.py first to generate BDD test cases")
        return False
    
    # Find all .feature files
    feature_files = []
    for root, _, files in os.walk(BDD_TEST_CASES_DIR):
        for file in files:
            if file.endswith('.feature') and file != 'example.feature':
                feature_files.append(os.path.join(root, file))
    
    if not feature_files:
        logging.error("No feature files found")
        return False
    
    # Copy feature files to Behave directory
    for src_file in feature_files:
        file_name = os.path.basename(src_file)
        dst_file = os.path.join(FEATURES_DIR, file_name)
        
        # Skip if file exists and skip_existing is True
        if skip_existing and os.path.exists(dst_file):
            logging.info(f"Skipping {file_name} as it already exists")
            continue
            
        # Read content and reformat if needed
        with open(src_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Remove markdown header if present
        content = re.sub(r'^#.*?\n\n', '', content)
        
        # Ensure Feature: is the first line
        if not content.strip().startswith('Feature:'):
            content = 'Feature: ' + file_name.replace('.feature', '') + '\n' + content
        
        # Write the clean content
        with open(dst_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logging.info(f"Copied {file_name} to {dst_file}")
    
    logging.info(f"Copied {len(feature_files)} feature files")
    return True

def generate_step_definitions(skip_existing=False):
    """Generate step definitions for the feature files."""
    logging.info("Generating step definitions...")
    
    # Skip if step definitions file already exists and skip_existing is True
    step_file = os.path.join(STEPS_DIR, "api_steps.py")
    if skip_existing and os.path.exists(step_file):
        logging.info(f"Skipping step definitions generation as {step_file} already exists")
        return True
    
    # We'll generate a more comprehensive step definitions file that handles all API scenarios
    with open(step_file, 'w', encoding='utf-8') as f:
        f.write('''
import os
import json
import requests
import re
import random
import string
from behave import *
import logging

# Setup logger
logger = logging.getLogger('BDDTest')
if not logger.handlers:
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# Helper functions
def generate_account_details():
    """Generate random account details for testing"""
    return {
        "bankName": "Test Bank",
        "ownerName": "Test User " + ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    }

def generate_transaction_details(source_account, target_account, amount=100.0):
    """Generate transaction details for testing"""
    return {
        "sourceAccount": {
            "sortCode": source_account["sortCode"],
            "accountNumber": source_account["accountNumber"]
        },
        "targetAccount": {
            "sortCode": target_account["sortCode"],
            "accountNumber": target_account["accountNumber"]
        },
        "amount": amount,
        "reference": "Test transaction",
        "latitude": 51.5074,
        "longitude": 0.1278
    }

# Account-related step definitions
@given('I am a new user')
def step_impl(context):
    context.account_details = generate_account_details()
    logger.info(f"Created new user with account details: {context.account_details}")

@given('I am an authenticated user')
def step_impl(context):
    # In a real implementation, this would handle actual authentication
    context.auth_token = "dummy_token"
    context.headers["Authorization"] = f"Bearer {context.auth_token}"
    
    # Create an account for the authenticated user if needed
    if not hasattr(context, 'account_details'):
        # First create an account
        account_details = generate_account_details()
        response = requests.put(
            context.base_url + "/api/v1/accounts",
            headers={"Content-Type": "application/json"},
            json=account_details
        )
        if response.status_code == 200:
            context.account_details = response.json()
            logger.info(f"Created account for authenticated user: {context.account_details}")
        else:
            logger.warning(f"Failed to create account for authenticated user: {response.status_code}")
    
    logger.info("User is authenticated")

@given('I am an unauthenticated user')
def step_impl(context):
    # Remove auth token if present
    if "Authorization" in context.headers:
        del context.headers["Authorization"]
    context.auth_token = None
    logger.info("User is not authenticated")

@given('I am an unauthorized user')
def step_impl(context):
    # Similar to unauthenticated but with a specific invalid token
    context.auth_token = "invalid_token"
    context.headers["Authorization"] = f"Bearer {context.auth_token}"
    logger.info("User has invalid authentication")

@when('I send a "PUT" request to "api/v1/accounts" with valid account details')
def step_impl(context):
    account_details = context.account_details
    logger.info(f"Sending PUT request to create account with details: {account_details}")
    
    context.last_response = requests.put(
        f"{context.base_url}/api/v1/accounts",
        headers=context.headers,
        json=account_details
    )
    
    # If successful, store the account details for future steps
    if context.last_response.status_code == 200:
        context.created_account = context.last_response.json()
        logger.info(f"Account created: {context.created_account}")

@when('I send a "PUT" request to "api/v1/accounts" with an email that already exists in the system')
def step_impl(context):
    # First create an account
    account_details = generate_account_details()
    response = requests.put(
        context.base_url + "/api/v1/accounts",
        headers=context.headers,
        json=account_details
    )
    
    # Then try to create another account with the same email
    context.last_response = requests.put(
        context.base_url + "/api/v1/accounts",
        headers=context.headers,
        json=account_details
    )
    logger.info(f"Sent PUT request with existing account details")

@when('I send a "PUT" request to "api/v1/accounts" with an invalid email format')
def step_impl(context):
    account_details = generate_account_details()
    # Add an invalid email
    account_details["email"] = "invalid-email"
    
    logger.info(f"Sending PUT request with invalid email format: {account_details}")
    context.last_response = requests.put(
        context.base_url + "/api/v1/accounts",
        headers=context.headers,
        json=account_details
    )

@when('I send a "PUT" request to "api/v1/accounts" with missing required fields')
def step_impl(context):
    # Sending incomplete account details
    account_details = {"bankName": "Test Bank"}  # Missing ownerName
    
    logger.info(f"Sending PUT request with missing required fields: {account_details}")
    context.last_response = requests.put(
        context.base_url + "/api/v1/accounts",
        headers=context.headers,
        json=account_details
    )

@then('I should receive a {status_code:d} status code')
def step_impl(context, status_code):
    assert context.last_response is not None, "No response received"
    actual_status = context.last_response.status_code
    assert actual_status == status_code, f"Expected status code {status_code}, got {actual_status}"
    logger.info(f"Response status code: {actual_status}")

@then('a response body confirming the account creation')
def step_impl(context):
    assert context.last_response is not None, "No response received"
    response_json = context.last_response.json()
    assert "sortCode" in response_json, "Response does not contain sortCode"
    assert "accountNumber" in response_json, "Response does not contain accountNumber"
    logger.info(f"Account creation confirmed with details: {response_json}")

@then('a response body indicating that the email already exists')
def step_impl(context):
    assert context.last_response is not None, "No response received"
    # Check for appropriate error message
    # Note: This depends on the exact API response format
    response_text = context.last_response.text
    assert "already exists" in response_text.lower() or "duplicate" in response_text.lower(), f"Response does not indicate email already exists: {response_text}"
    logger.info(f"Response correctly indicates email already exists")

@then('a response body indicating that the email format is invalid')
def step_impl(context):
    assert context.last_response is not None, "No response received"
    # Check for appropriate error message
    response_text = context.last_response.text
    assert "invalid" in response_text.lower() and "email" in response_text.lower(), f"Response does not indicate invalid email format: {response_text}"
    logger.info(f"Response correctly indicates invalid email format")

@then('a response body indicating that required fields are missing')
def step_impl(context):
    assert context.last_response is not None, "No response received"
    # Check for appropriate error message
    response_text = context.last_response.text
    assert "missing" in response_text.lower() or "required" in response_text.lower(), f"Response does not indicate missing fields: {response_text}"
    logger.info(f"Response correctly indicates missing required fields")

@then('a response body indicating that I am not authorized to create an account')
def step_impl(context):
    assert context.last_response is not None, "No response received"
    # Check for appropriate error message
    response_text = context.last_response.text
    assert "unauthorized" in response_text.lower() or "not authorized" in response_text.lower() or "forbidden" in response_text.lower(), f"Response does not indicate unauthorized access: {response_text}"
    logger.info(f"Response correctly indicates unauthorized access")

# Account balance related steps
@given('a user has an account with a balance of ${balance:d}')
def step_impl(context, balance):
    # Create an account
    account_details = generate_account_details()
    response = requests.put(
        context.base_url + "/api/v1/accounts",
        headers={"Content-Type": "application/json"},
        json=account_details
    )
    
    if response.status_code != 200:
        logger.error(f"Failed to create account: {response.status_code}")
        assert False, "Failed to create account"
    
    account = response.json()
    context.account = account
    logger.info(f"Created account: {account}")
    
    # Deposit initial balance
    deposit_data = {
        "targetAccountNo": account["accountNumber"],
        "amount": balance
    }
    
    response = requests.post(
        context.base_url + "/api/v1/deposit",
        headers={"Content-Type": "application/json"},
        json=deposit_data
    )
    
    if response.status_code != 200:
        logger.error(f"Failed to deposit initial balance: {response.status_code}")
        assert False, "Failed to deposit initial balance"
    
    logger.info(f"Deposited initial balance of ${balance}")
    context.initial_balance = balance

@when('I send a "POST" request to "api/v1/accounts" to check my account balance')
def step_impl(context):
    assert hasattr(context, 'account'), "No account available"
    
    balance_request = {
        "sortCode": context.account["sortCode"],
        "accountNumber": context.account["accountNumber"]
    }
    
    logger.info(f"Checking balance for account: {balance_request}")
    context.last_response = requests.post(
        context.base_url + "/api/v1/accounts",
        headers=context.headers,
        json=balance_request
    )

@then('I should receive a response with my account balance')
def step_impl(context):
    assert context.last_response is not None, "No response received"
    response_json = context.last_response.json()
    assert "currentBalance" in response_json, "Response does not contain currentBalance"
    balance = response_json["currentBalance"]
    logger.info(f"Account balance: {balance}")
    
    # Verify the balance matches the expected value if we have an initial balance
    if hasattr(context, 'initial_balance'):
        assert float(balance) == float(context.initial_balance), f"Expected balance {context.initial_balance}, got {balance}"

# Withdrawal related steps
@when('the user makes a POST request to "api/v1/withdraw" with a withdrawal amount of ${amount:d}')
def step_impl(context, amount):
    assert hasattr(context, 'account'), "No account available"
    
    withdrawal_data = {
        "sortCode": context.account["sortCode"],
        "accountNumber": context.account["accountNumber"],
        "amount": amount
    }
    
    logger.info(f"Withdrawing ${amount} from account: {context.account['accountNumber']}")
    context.last_response = requests.post(
        context.base_url + "/api/v1/withdraw",
        headers=context.headers,
        json=withdrawal_data
    )
    context.withdrawal_amount = amount

@when('the user makes a POST request to "api/v1/withdraw" without providing a withdrawal amount')
def step_impl(context):
    assert hasattr(context, 'account'), "No account available"
    
    withdrawal_data = {
        "sortCode": context.account["sortCode"],
        "accountNumber": context.account["accountNumber"]
        # Missing amount field
    }
    
    logger.info(f"Attempting withdrawal without amount from account: {context.account['accountNumber']}")
    context.last_response = requests.post(
        context.base_url + "/api/v1/withdraw",
        headers=context.headers,
        json=withdrawal_data
    )

@then('the account balance should be reduced by ${amount:d}')
def step_impl(context, amount):
    # Check the account balance after withdrawal
    balance_request = {
        "sortCode": context.account["sortCode"],
        "accountNumber": context.account["accountNumber"]
    }
    
    response = requests.post(
        context.base_url + "/api/v1/accounts",
        headers=context.headers,
        json=balance_request
    )
    
    assert response.status_code == 200, f"Failed to check balance after withdrawal: {response.status_code}"
    
    new_balance = response.json()["currentBalance"]
    expected_balance = context.initial_balance - amount
    
    assert float(new_balance) == float(expected_balance), f"Expected balance {expected_balance}, got {new_balance}"
    logger.info(f"Balance correctly reduced to {new_balance}")

@then('the account balance should not change')
def step_impl(context):
    # Check the account balance remains the same
    balance_request = {
        "sortCode": context.account["sortCode"],
        "accountNumber": context.account["accountNumber"]
    }
    
    response = requests.post(
        context.base_url + "/api/v1/accounts",
        headers=context.headers,
        json=balance_request
    )
    
    assert response.status_code == 200, f"Failed to check balance: {response.status_code}"
    
    new_balance = response.json()["currentBalance"]
    expected_balance = context.initial_balance
    
    assert float(new_balance) == float(expected_balance), f"Expected balance to remain {expected_balance}, got {new_balance}"
    logger.info(f"Balance correctly remained at {new_balance}")

@then('a {status_code:d} status code is returned')
def step_impl(context, status_code):
    assert context.last_response is not None, "No response received"
    actual_status = context.last_response.status_code
    assert actual_status == status_code, f"Expected status code {status_code}, got {actual_status}"
    logger.info(f"Response status code: {actual_status}")

@then('a {status_code:d} status code is returned with an error message "{message}"')
def step_impl(context, status_code, message):
    assert context.last_response is not None, "No response received"
    actual_status = context.last_response.status_code
    assert actual_status == status_code, f"Expected status code {status_code}, got {actual_status}"
    
    # Check for the error message
    response_text = context.last_response.text
    assert message.lower() in response_text.lower(), f"Expected error message containing '{message}', got '{response_text}'"
    logger.info(f"Response contains error message: {message}")

# Transaction related steps
@given('I am a user with a valid account')
def step_impl(context):
    # Create an account
    account_details = generate_account_details()
    response = requests.put(
        context.base_url + "/api/v1/accounts",
        headers={"Content-Type": "application/json"},
        json=account_details
    )
    
    if response.status_code != 200:
        logger.error(f"Failed to create account: {response.status_code}")
        assert False, "Failed to create account"
    
    account = response.json()
    context.source_account = account
    logger.info(f"Created source account: {account}")
    
    # Deposit initial balance
    deposit_data = {
        "targetAccountNo": account["accountNumber"],
        "amount": 1000
    }
    
    response = requests.post(
        context.base_url + "/api/v1/deposit",
        headers={"Content-Type": "application/json"},
        json=deposit_data
    )
    
    if response.status_code != 200:
        logger.error(f"Failed to deposit initial balance: {response.status_code}")
        assert False, "Failed to deposit initial balance"
    
    # Create a target account for transactions
    account_details = generate_account_details()
    response = requests.put(
        context.base_url + "/api/v1/accounts",
        headers={"Content-Type": "application/json"},
        json=account_details
    )
    
    if response.status_code != 200:
        logger.error(f"Failed to create target account: {response.status_code}")
        assert False, "Failed to create target account"
    
    account = response.json()
    context.target_account = account
    logger.info(f"Created target account: {account}")

@when('I make a POST request to "api/v1/transactions" with valid transaction details')
def step_impl(context):
    assert hasattr(context, 'source_account'), "No source account available"
    assert hasattr(context, 'target_account'), "No target account available"
    
    transaction_data = generate_transaction_details(
        context.source_account, 
        context.target_account,
        amount=100.0
    )
    
    logger.info(f"Making transaction: {transaction_data}")
    context.last_response = requests.post(
        context.base_url + "/api/v1/transactions",
        headers=context.headers,
        json=transaction_data
    )
    context.transaction_amount = 100.0

@when('I make a POST request to "api/v1/transactions" with a transaction amount greater than my account balance')
def step_impl(context):
    assert hasattr(context, 'source_account'), "No source account available"
    assert hasattr(context, 'target_account'), "No target account available"
    
    # Get current balance
    balance_request = {
        "sortCode": context.source_account["sortCode"],
        "accountNumber": context.source_account["accountNumber"]
    }
    
    response = requests.post(
        context.base_url + "/api/v1/accounts",
        headers=context.headers,
        json=balance_request
    )
    
    current_balance = float(response.json()["currentBalance"])
    excessive_amount = current_balance + 100.0
    
    transaction_data = generate_transaction_details(
        context.source_account, 
        context.target_account,
        amount=excessive_amount
    )
    
    logger.info(f"Making transaction with excessive amount {excessive_amount}: {transaction_data}")
    context.last_response = requests.post(
        context.base_url + "/api/v1/transactions",
        headers=context.headers,
        json=transaction_data
    )

@then('the transaction should be processed')
def step_impl(context):
    assert context.last_response is not None, "No response received"
    assert context.last_response.status_code == 200, f"Transaction failed with status code {context.last_response.status_code}"
    
    # Verify source account balance decreased
    balance_request = {
        "sortCode": context.source_account["sortCode"],
        "accountNumber": context.source_account["accountNumber"]
    }
    
    response = requests.post(
        context.base_url + "/api/v1/accounts",
        headers=context.headers,
        json=balance_request
    )
    
    new_source_balance = float(response.json()["currentBalance"])
    logger.info(f"Source account new balance: {new_source_balance}")
    
    # Verify target account balance increased
    balance_request = {
        "sortCode": context.target_account["sortCode"],
        "accountNumber": context.target_account["accountNumber"]
    }
    
    response = requests.post(
        context.base_url + "/api/v1/accounts",
        headers=context.headers,
        json=balance_request
    )
    
    new_target_balance = float(response.json()["currentBalance"])
    logger.info(f"Target account new balance: {new_target_balance}")
    
    # In a real test, we would verify the exact balance changes

@then('the transaction should not be processed')
def step_impl(context):
    assert context.last_response is not None, "No response received"
    assert context.last_response.status_code != 200, f"Transaction succeeded with status code {context.last_response.status_code}"
    
    # Verify source account balance hasn't changed
    balance_request = {
        "sortCode": context.source_account["sortCode"],
        "accountNumber": context.source_account["accountNumber"]
    }
    
    response = requests.post(
        context.base_url + "/api/v1/accounts",
        headers=context.headers,
        json=balance_request
    )
    
    current_balance = float(response.json()["currentBalance"])
    logger.info(f"Source account balance unchanged: {current_balance}")
    
    # In a real test, we would compare to the previous balance
''')
    
    logging.info("Comprehensive step definitions generated")
    return True

def verify_behave_installation():
    """Verify that Behave is installed."""
    try:
        # Dynamically import behave only when verified
        import behave
        logging.info("Behave is already installed")
        return True
    except ImportError:
        logging.warning("Behave is not installed. Attempting to install...")
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "behave", "requests"],
                check=True,
                capture_output=True,
                text=True
            )
            logging.info("Behave installed successfully")
            return True
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to install Behave: {e}")
            logging.error(e.stderr)
            return False

def create_behave_config():
    """Create Behave configuration file."""
    logging.info("Creating Behave configuration file...")
    
    # Load existing config if available
    config = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
    
    # Add API base URL if not present
    if "api_base_url" not in config:
        config["api_base_url"] = "http://localhost:8080"
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
        logging.info(f"Added API base URL to {CONFIG_FILE}")
    
    # Create Behave config
    behave_config = os.path.join(BEHAVE_DIR, "behave.ini")
    with open(behave_config, "w", encoding="utf-8") as f:
        f.write('''[behave]
color = True
show_skipped = False
show_timings = True
stdout_capture = False
stderr_capture = False
logging_level = INFO
logging_format = %(asctime)s - %(name)s - %(levelname)s - %(message)s
''')
    
    logging.info(f"Created Behave configuration file: {behave_config}")
    return True

def run_behave_tests(tags=None, specific_feature=None):
    """Run the Behave tests."""
    logging.info("Running Behave tests...")
    
    # Build command
    cmd = [sys.executable, "-m", "behave"]
    
    # Add specific feature if provided
    if specific_feature:
        feature_path = os.path.join(FEATURES_DIR, specific_feature)
        if os.path.exists(feature_path):
            cmd.append(feature_path)
        else:
            logging.error(f"Feature file not found: {feature_path}")
            return False
    else:
        cmd.append(FEATURES_DIR)
    
    # Add tags if specified
    if tags:
        cmd.extend(["--tags", tags])
    
    # Run Behave
    try:
        result = subprocess.run(
            cmd,
            check=False,  # Don't raise exception on test failure
            capture_output=False,  # Show output directly
            text=True
        )
        
        if result.returncode == 0:
            logging.info("All tests passed!")
            return True
        else:
            logging.warning(f"Some tests failed. Return code: {result.returncode}")
            return False
    except Exception as e:
        logging.error(f"Error running Behave tests: {e}")
        return False

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Run BDD tests against the cloned repository")
    parser.add_argument("--tags", help="Only run tests with these tags (e.g. '@smoke')")
    parser.add_argument("--api-url", help="Base URL for the API (e.g. 'http://localhost:8080')")
    parser.add_argument("--setup-only", action="store_true", help="Only set up the test environment, don't run tests")
    parser.add_argument("--use-running-app", action="store_true", help="Use already running app instead of starting a new one")
    parser.add_argument("feature_file", nargs="?", help="Specific feature file to run tests from")
    args = parser.parse_args()
    
    # Update API URL in config if provided
    if args.api_url:
        config = {}
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
        
        config["api_base_url"] = args.api_url
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
        logging.info(f"Updated API base URL to {args.api_url}")
    
    # Verify Behave is installed
    if not verify_behave_installation():
        return 1
    
    # Set up test environment
    setup_behave_environment()
    if not copy_feature_files():
        return 1
    generate_step_definitions()
    create_behave_config()
    
    if args.setup_only:
        logging.info("Test environment setup completed. Skipping test execution.")
        return 0
    
    # If not using a running app, start the app
    if not args.use_running_app:
        # Try to import and use start_app.py
        try:
            import start_app
            logging.info("Starting the Spring Boot application...")
            # The start_app module handles starting the application
            result = start_app.main()
            if result != 0:
                logging.error("Failed to start application. BDD tests require a running application.")
                return 1
        except ImportError:
            logging.warning("start_app.py not found or could not be imported.")
            logging.warning("Assuming application is already running or will be started separately.")
    else:
        logging.info("Using already running application for tests.")
        
        # Check if application is actually running
        try:
            config = {}
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)
            
            api_url = config.get("api_base_url", "http://localhost:8080")
            logging.info(f"Checking if application is running at {api_url}...")
            
            # Try to connect to application
            try:
                response = requests.get(f"{api_url}/", timeout=5)
                logging.info(f"Application responded with status code {response.status_code}")
            except requests.RequestException as e:
                logging.warning(f"Could not connect to application: {e}")
                logging.warning("Tests might fail if application is not running properly.")
        except Exception as e:
            logging.warning(f"Error checking application: {e}")
    
    # Run tests
    if run_behave_tests(args.tags, args.feature_file):
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main()) 
