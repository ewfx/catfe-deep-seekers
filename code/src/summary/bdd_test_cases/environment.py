
import logging
import requests
import time
import sys

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def before_all(context):
    """Setup the environment before all tests."""
    # Set base URL for API requests
    context.base_url = "http://localhost:8080/api/v1"
    
    # Verify API is accessible
    max_retries = 5
    for i in range(max_retries):
        try:
            response = requests.get(context.base_url)
            logging.info(f"API is accessible at {context.base_url}")
            break
        except requests.exceptions.ConnectionError:
            if i < max_retries - 1:
                logging.warning(f"Could not access API, retrying in 5 seconds ({i+1}/{max_retries})")
                time.sleep(5)
            else:
                logging.warning(f"Could not access API at {context.base_url} after {max_retries} attempts")
                logging.warning("Some tests may fail if the API is not running")

def after_all(context):
    """Clean up after all tests."""
    logging.info("All tests completed")
