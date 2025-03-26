
import json
import logging
import requests
import behave
import random
import string
import time
import os

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Load successful API request data if available
SUCCESSFUL_API_DATA = {}
data_file = os.path.join(os.path.dirname(__file__), "..", "successful_api_data.json")
if os.path.exists(data_file):
    try:
        with open(data_file, "r", encoding="utf-8") as f:
            SUCCESSFUL_API_DATA = json.load(f)
        logging.info(f"Loaded successful API request data from {data_file}")
    except Exception as e:
        logging.error(f"Error loading successful API request data: {e}")

# Load Postman sample data if available
POSTMAN_SAMPLE_DATA = {}
postman_data_file = os.path.join(os.path.dirname(__file__), "..", "postman_sample_data.json")
if os.path.exists(postman_data_file):
    try:
        with open(postman_data_file, "r", encoding="utf-8") as f:
            POSTMAN_SAMPLE_DATA = json.load(f)
        logging.info(f"Loaded Postman sample data from {postman_data_file}")
    except Exception as e:
        logging.error(f"Error loading Postman sample data: {e}")

# Utility functions
def random_string(length=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def random_number(min=100, max=999):
    return random.randint(min, max)

def is_successful_status(status_code):
    """Check if status code indicates success (2xx)"""
    return 200 <= status_code < 300

def get_sample_data(method, endpoint):
    """Get sample data for an endpoint from various sources"""
    # Check for successful API data first
    key = f"{method}_{endpoint}"
    if key in SUCCESSFUL_API_DATA:
        logging.info(f"Using successful request data for {key}")
        return SUCCESSFUL_API_DATA[key]
    
    # Then check for Postman sample data
    if endpoint in POSTMAN_SAMPLE_DATA and method in POSTMAN_SAMPLE_DATA[endpoint]:
        postman_data = POSTMAN_SAMPLE_DATA[endpoint][method]
        if postman_data and len(postman_data) > 0:
            logging.info(f"Using Postman sample data for {method} {endpoint}")
            return postman_data[0]  # Use the first sample
    
    # Return None if no sample data found
    return None

@behave.given('I am an unauthenticated user')
def step_impl_unauthenticated_user(context):
    # Try to use sample data if available
    accounts_data = get_sample_data("PUT", "accounts")
    
    if accounts_data:
        # Use previously successful data with slight modifications
        context.account_details = dict(accounts_data)
        context.account_details["username"] = f"user_{random_string(5)}"  # Ensure unique username
    else:
        # Generate random account details for testing
        context.account_details = {
            "username": f"user_{random_string(5)}",
            "password": f"pass_{random_string(5)}",
            "email": f"user_{random_string(5)}@example.com",
            "firstName": "Test",
            "lastName": "User",
            "initialBalance": 1000.0,
            "bankName": "Test Bank",
            "ownerName": f"Test User {random_string(5)}",
            "sortCode": f"{random_number():06d}",
            "accountNumber": f"{random_number():08d}",
            "initialCredit": 100.0
        }
    
    logging.info(f"Created account details for unauthenticated user: {context.account_details}")
    context.headers = {}
    
    # Reset response for this scenario
    context.response = None
    context.response_json = None

@behave.given('I am an authenticated user')
def step_impl_authenticated_user(context):
    # Set authentication token
    token = "dummy-token-for-testing"
    context.headers = {"Authorization": f"Bearer {token}"}
    
    # Try to use sample data if available
    accounts_data = get_sample_data("PUT", "accounts")
    
    # Generate account details if not already set
    if not hasattr(context, 'account_details'):
        if accounts_data:
            # Use previously successful data with slight modifications
            context.account_details = dict(accounts_data)
            context.account_details["username"] = f"user_{random_string(5)}"  # Ensure unique username
        else:
            context.account_details = {
                "username": f"user_{random_string(5)}",
                "password": f"pass_{random_string(5)}",
                "email": f"user_{random_string(5)}@example.com",
                "firstName": "Test",
                "lastName": "User",
                "initialBalance": 1000.0,
                "bankName": "Test Bank",
                "ownerName": f"Test User {random_string(5)}",
                "sortCode": f"{random_number():06d}",
                "accountNumber": f"{random_number():08d}",
                "initialCredit": 100.0
            }
    
    # Reset response for this scenario
    context.response = None
    context.response_json = None
    
    # Create an account for this user
    try:
        # Try to create via accounts endpoint
        response = requests.put(
            f"{context.base_url}/accounts",
            json=context.account_details,
            headers=context.headers
        )
        
        if is_successful_status(response.status_code):
            logging.info(f"Created account for authenticated user with status: {response.status_code}")
            try:
                context.account = response.json()
            except:
                context.account = context.account_details
        else:
            logging.warning(f"Could not create account with PUT to /accounts: {response.status_code}")
            # Try alternate endpoint for account creation
            try:
                response = requests.post(
                    f"{context.base_url}/accounts",
                    json=context.account_details,
                    headers=context.headers
                )
                if is_successful_status(response.status_code):
                    logging.info(f"Created account via POST to /accounts: {response.status_code}")
                    try:
                        context.account = response.json()
                    except:
                        context.account = context.account_details
                else:
                    logging.warning(f"Failed to create account via POST: {response.status_code}")
                    # Use the account details as fallback
                    context.account = context.account_details
            except Exception as e:
                logging.error(f"Error trying alternate account creation: {e}")
                context.account = context.account_details
    except Exception as e:
        logging.error(f"Error creating account: {e}")
        context.account = context.account_details

@behave.given('I am a user with valid account')
def step_impl_user_with_valid_account(context):
    # Combine steps for authenticated user
    step_impl_authenticated_user(context)

@behave.given('I am a user with invalid account')
def step_impl_user_with_invalid_account(context):
    # Generate invalid account details
    context.account_details = {
        "username": f"invalid_{random_string(5)}",
        "password": f"pass_{random_string(5)}",
        "email": f"invalid_{random_string(5)}@example.com",
        "firstName": "Invalid",
        "lastName": "User",
        "bankName": "Invalid Bank",
        "ownerName": f"Invalid User {random_string(5)}",
        "sortCode": f"INVALID{random_number():03d}",
        "accountNumber": f"INVALID{random_number():03d}",
        "initialCredit": -100.0  # Invalid negative balance
    }
    logging.info(f"Created invalid account details: {context.account_details}")
    context.headers = {}
    
    # Reset response for this scenario
    context.response = None
    context.response_json = None

@behave.given('I am a user with admin permissions')
def step_impl_user_with_admin_permissions(context):
    # Create admin account
    step_impl_authenticated_user(context)
    context.headers["Role"] = "ADMIN"

@behave.given('I am a user with standard permissions')
def step_impl_user_with_standard_permissions(context):
    # Create standard user account
    step_impl_authenticated_user(context)
    context.headers["Role"] = "USER"

@behave.when('I send a "{method}" request to "{endpoint}" with valid account details')
def step_impl_send_request(context, method, endpoint):
    url = f"{context.base_url}/{endpoint.lstrip('/')}"
    payload = context.account_details
    
    logging.info(f"Sending {method} request to {url} with payload: {payload}")
    
    try:
        if method == "GET":
            context.response = requests.get(url, headers=context.headers)
        elif method == "POST":
            context.response = requests.post(url, json=payload, headers=context.headers)
        elif method == "PUT":
            context.response = requests.put(url, json=payload, headers=context.headers)
        elif method == "DELETE":
            context.response = requests.delete(url, headers=context.headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        logging.info(f"Got response with status code: {context.response.status_code}")
        try:
            context.response_json = context.response.json()
            logging.info(f"Response JSON: {context.response_json}")
        except ValueError:
            logging.info(f"Response was not JSON: {context.response.text}")
            context.response_json = None
            
    except Exception as e:
        logging.error(f"Error sending request: {e}")
        context.response = None
        context.response_json = None

@behave.when('I check the account balance')
def step_impl_check_balance(context):
    assert hasattr(context, 'account'), "No account found in context"
    
    # Try to get sample data for account balance check
    balance_data = get_sample_data("POST", "accounts")
    
    if balance_data:
        # Use sample data but ensure account info is consistent
        balance_request = dict(balance_data)
        if "sortCode" in context.account and "sortCode" in balance_request:
            balance_request["sortCode"] = context.account["sortCode"]
        if "accountNumber" in context.account and "accountNumber" in balance_request:
            balance_request["accountNumber"] = context.account["accountNumber"]
    else:
        balance_request = {
            "sortCode": context.account["sortCode"],
            "accountNumber": context.account["accountNumber"]
        }
    
    logging.info(f"Checking balance with request: {balance_request}")
    
    try:
        context.response = requests.post(
            f"{context.base_url}/accounts",
            json=balance_request,
            headers=context.headers
        )
        
        logging.info(f"Balance check status: {context.response.status_code}")
        
        try:
            context.response_json = context.response.json()
            logging.info(f"Balance response: {context.response_json}")
        except ValueError:
            logging.error(f"Failed to parse balance response: {context.response.text}")
            context.response_json = None
            
    except Exception as e:
        logging.error(f"Error checking balance: {e}")
        context.response = None
        context.response_json = None

@behave.when('I make a deposit of {amount:f}')
def step_impl_make_deposit(context, amount):
    assert hasattr(context, 'account'), "No account found in context"
    
    # Try to use sample data for deposit
    deposit_data = get_sample_data("POST", "deposit")
    
    if deposit_data:
        # Use sample data but with the requested amount
        deposit_request = dict(deposit_data)
        deposit_request["amount"] = amount
        # Make sure account info is consistent
        if "sortCode" in context.account and "sortCode" in deposit_request:
            deposit_request["sortCode"] = context.account["sortCode"]
        if "accountNumber" in context.account and "accountNumber" in deposit_request:
            deposit_request["accountNumber"] = context.account["accountNumber"]
        if "targetAccountNo" in deposit_request and "accountNumber" in context.account:
            deposit_request["targetAccountNo"] = context.account["accountNumber"]
    else:
        deposit_request = {
            "sortCode": context.account["sortCode"],
            "accountNumber": context.account["accountNumber"],
            "amount": amount
        }
    
    logging.info(f"Making deposit with request: {deposit_request}")
    
    try:
        context.response = requests.post(
            f"{context.base_url}/deposit",
            json=deposit_request,
            headers=context.headers
        )
        
        logging.info(f"Deposit status: {context.response.status_code}")
        
        try:
            context.response_json = context.response.json()
            logging.info(f"Deposit response: {context.response_json}")
        except ValueError:
            logging.info(f"Response was not JSON: {context.response.text}")
            context.response_json = None
            
    except Exception as e:
        logging.error(f"Error making deposit: {e}")
        context.response = None
        context.response_json = None

@behave.when('I make a withdrawal of {amount:f}')
def step_impl_make_withdrawal(context, amount):
    assert hasattr(context, 'account'), "No account found in context"
    
    # Try to use sample data for withdrawal
    withdraw_data = get_sample_data("POST", "withdraw")
    
    if withdraw_data:
        # Use sample data but with the requested amount
        withdrawal_request = dict(withdraw_data)
        withdrawal_request["amount"] = amount
        # Make sure account info is consistent
        if "sortCode" in context.account and "sortCode" in withdrawal_request:
            withdrawal_request["sortCode"] = context.account["sortCode"]
        if "accountNumber" in context.account and "accountNumber" in withdrawal_request:
            withdrawal_request["accountNumber"] = context.account["accountNumber"]
    else:
        withdrawal_request = {
            "sortCode": context.account["sortCode"],
            "accountNumber": context.account["accountNumber"],
            "amount": amount
        }
    
    logging.info(f"Making withdrawal with request: {withdrawal_request}")
    
    try:
        context.response = requests.post(
            f"{context.base_url}/withdraw",
            json=withdrawal_request,
            headers=context.headers
        )
        
        logging.info(f"Withdrawal status: {context.response.status_code}")
        
        try:
            context.response_json = context.response.json()
            logging.info(f"Withdrawal response: {context.response_json}")
        except ValueError:
            logging.info(f"Response was not JSON: {context.response.text}")
            context.response_json = None
            
    except Exception as e:
        logging.error(f"Error making withdrawal: {e}")
        context.response = None
        context.response_json = None

@behave.when('I make a transaction of {amount:f} from my account to another account')
def step_impl_make_transaction(context, amount):
    assert hasattr(context, 'account'), "Source account not found in context"
    
    # Try to use sample data for transaction
    transaction_data = get_sample_data("POST", "transactions")
    
    # Create a target account if needed
    if not hasattr(context, 'target_account'):
        # Create a second account for testing transactions
        target_details = {
            "bankName": "Target Bank",
            "ownerName": f"Target User {random_string(5)}",
            "sortCode": f"{random_number():06d}",
            "accountNumber": f"{random_number():08d}",
            "initialCredit": 100.0
        }
        
        try:
            response = requests.put(
                f"{context.base_url}/accounts",
                json=target_details,
                headers=context.headers
            )
            if response.status_code in (200, 201):
                context.target_account = response.json()
                logging.info(f"Created target account: {context.target_account}")
            else:
                logging.error(f"Failed to create target account: {response.status_code} {response.text}")
                return
        except Exception as e:
            logging.error(f"Error creating target account: {e}")
            return
    
    # Build transaction request
    if transaction_data:
        # Use sample data but with our account details
        transaction_request = dict(transaction_data)
        transaction_request["amount"] = amount
        
        # Handle different possible structure formats
        if "sourceAccount" in transaction_data:
            # Format 1: nested accounts objects
            transaction_request["sourceAccount"] = {
                "sortCode": context.account["sortCode"],
                "accountNumber": context.account["accountNumber"]
            }
            transaction_request["targetAccount"] = {
                "sortCode": context.target_account["sortCode"],
                "accountNumber": context.target_account["accountNumber"]
            }
        else:
            # Format 2: flat fields
            transaction_request["fromAccount"] = context.account["accountNumber"]
            transaction_request["fromSortCode"] = context.account["sortCode"]
            transaction_request["toAccount"] = context.target_account["accountNumber"]
            transaction_request["toSortCode"] = context.target_account["sortCode"]
    else:
        transaction_request = {
            "sourceAccount": {
                "sortCode": context.account["sortCode"],
                "accountNumber": context.account["accountNumber"]
            },
            "targetAccount": {
                "sortCode": context.target_account["sortCode"],
                "accountNumber": context.target_account["accountNumber"]
            },
            "amount": amount
        }
    
    logging.info(f"Making transaction with request: {transaction_request}")
    
    try:
        context.response = requests.post(
            f"{context.base_url}/transactions",
            json=transaction_request,
            headers=context.headers
        )
        
        logging.info(f"Transaction status: {context.response.status_code}")
        
        try:
            context.response_json = context.response.json()
            logging.info(f"Transaction response: {context.response_json}")
        except ValueError:
            logging.info(f"Response was not JSON: {context.response.text}")
            context.response_json = None
            
    except Exception as e:
        logging.error(f"Error making transaction: {e}")
        context.response = None
        context.response_json = None

@behave.then('I should receive a {status_code:d} status code')
def step_impl_check_status_code(context, status_code):
    assert context.response is not None, "No response was received"
    assert context.response.status_code == status_code, f"Expected status code {status_code}, got {context.response.status_code}"
    logging.info(f"Status code check passed: {status_code}")

@behave.then('the balance should be {expected_balance:f}')
def step_impl_check_balance_value(context, expected_balance):
    assert context.response_json is not None, "No JSON response was received"
    assert "currentBalance" in context.response_json, "Response does not contain 'currentBalance'"
    
    actual_balance = float(context.response_json["currentBalance"])
    # Allow for tiny floating point differences
    assert abs(actual_balance - expected_balance) < 0.0001, f"Expected balance {expected_balance}, got {actual_balance}"
    logging.info(f"Balance check passed: {expected_balance}")

@behave.then('the response should contain a confirmation message')
def step_impl_check_confirmation_message(context):
    assert context.response_json is not None, "No JSON response was received"
    assert any(k in context.response_json for k in ["message", "confirmation", "status"]), "Response does not contain any confirmation message"
    logging.info(f"Confirmation message check passed")

@behave.then('the response should contain an error message')
def step_impl_check_error_message(context):
    assert context.response_json is not None, "No JSON response was received"
    assert any(k in context.response_json for k in ["error", "message", "status"]), "Response does not contain any error message"
    logging.info(f"Error message check passed")

@behave.then('the account should have been created successfully')
def step_impl_check_account_created(context):
    assert context.response_json is not None, "No JSON response was received"
    assert "sortCode" in context.response_json, "Response does not contain 'sortCode'"
    assert "accountNumber" in context.response_json, "Response does not contain 'accountNumber'"
    assert "ownerName" in context.response_json, "Response does not contain 'ownerName'"
    logging.info(f"Account creation check passed")

@behave.then('the account should not have been created')
def step_impl_check_account_not_created(context):
    assert context.response.status_code != 200, "Account was created (status code 200)"
    logging.info(f"Account not created check passed")
