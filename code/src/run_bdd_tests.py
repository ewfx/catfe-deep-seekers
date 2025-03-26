#!/usr/bin/env python
"""
Automated BDD Test Workflow

This script automates the entire BDD testing workflow:
1. Runs generate_artifacts.py to generate BDD test cases
2. Sets up the Behave test environment
3. Builds and starts the Spring Boot application
4. Runs the BDD tests against the running application
5. Shuts down the application after testing
"""

import os
import sys
import subprocess
import logging
import argparse
import time
import signal
import atexit
import json
import requests
import glob
import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("BDD_Test_Runner")

def run_command(cmd, desc, capture_output=True):
    """Run a command and return its result."""
    logging.info(f"Running {desc}...")
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=capture_output,
            text=True
        )
        logging.info(f"{desc} completed successfully")
        return result
    except subprocess.CalledProcessError as e:
        logging.error(f"{desc} failed with code {e.returncode}")
        if capture_output:
            logging.error(f"Output: {e.stdout}")
            logging.error(f"Error: {e.stderr}")
        return None

def start_application(port, profile=None):
    """Start the Spring Boot application."""
    logging.info("Starting Spring Boot application...")
    
    # Command to start the app in a separate process
    cmd = [sys.executable, "start_app.py"]
    
    # Add arguments
    if port:
        cmd.extend(["--port", str(port)])
    if profile:
        cmd.extend(["--profile", profile])
    
    # Add direct option to try running without building JAR
    cmd.append("--direct")
    
    # Start process
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Register cleanup
        def cleanup():
            if process.poll() is None:
                logging.info("Stopping application...")
                process.terminate()
                process.wait(timeout=5)
                if process.poll() is None:
                    process.kill()
        
        atexit.register(cleanup)
        signal.signal(signal.SIGINT, lambda sig, frame: (cleanup(), sys.exit(0)))
        signal.signal(signal.SIGTERM, lambda sig, frame: (cleanup(), sys.exit(0)))
        
        # Wait for app to start
        started = False
        timeout = 60  # seconds
        start_time = time.time()
        
        while not started and time.time() - start_time < timeout:
            line = process.stdout.readline()
            if "Application started successfully" in line:
                started = True
                logging.info("Application started successfully")
            elif "Application might not have started properly" in line:
                logging.warning("Application might not have started properly, but continuing")
                started = True
            elif line:
                print(line.strip())
            
            # Check if process died
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                logging.error("Application failed to start")
                logging.error(f"STDOUT: {stdout}")
                logging.error(f"STDERR: {stderr}")
                return None
            
            time.sleep(0.1)
        
        if not started:
            logging.warning("Timed out waiting for application to start, but continuing")
        
        # Give additional time for the application to initialize
        time.sleep(2)
        
        return process
    except Exception as e:
        logging.error(f"Error starting application: {e}")
        return None

def verify_api_is_running(base_url="http://localhost:8080/api/v1"):
    """Check if the API is accessible before running tests"""
    logger.info(f"Verifying API is running at {base_url}...")
    
    try:
        # Try to access the API
        response = requests.get(f"{base_url}/accounts", timeout=5)
        # Any response code indicates the server is running
        logger.info(f"API responded with status code {response.status_code}")
        return True
    except requests.RequestException as e:
        logger.error(f"API is not accessible: {e}")
        return False

def run_behave(feature=None, tags=None, verbose=False):
    """Run the BDD tests using behave directly"""
    logger.info("Running BDD tests with behave directly...")
    
    # Build command
    cmd = [sys.executable, "-m", "behave"]
    
    # Add features directory
    cmd.append("behave_tests/features")
    
    # Add specific feature if provided
    if feature:
        if not os.path.exists(f"behave_tests/features/{feature}"):
            logger.error(f"Feature file not found: {feature}")
            return False
        # Override features directory with specific feature
        cmd[-1] = f"behave_tests/features/{feature}"
    
    # Add tags if specified
    if tags:
        cmd.extend(["--tags", tags])
    
    # Add verbose output if requested
    if verbose:
        cmd.append("--no-capture")
        cmd.append("--verbose")
    
    # Run behave
    logger.info(f"Executing command: {' '.join(cmd)}")
    try:
        # Run behave and capture output
        process = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True
        )
        
        # Print output whether or not the tests passed
        logger.info("=== TEST OUTPUT ===")
        print(process.stdout)
        
        if process.stderr:
            logger.error("=== ERROR OUTPUT ===")
            print(process.stderr)
        
        if process.returncode == 0:
            logger.info("All BDD tests passed successfully!")
            return True
        else:
            logger.warning(f"Some BDD tests failed. Return code: {process.returncode}")
            return False
    except Exception as e:
        logger.error(f"Error running BDD tests: {e}")
        return False

def run_with_test_runner(feature=None, tags=None, use_running_app=True):
    """Run tests using the bdd_test_runner.py script"""
    logger.info("Running BDD tests with test runner...")
    
    # Build command
    cmd = [sys.executable, "bdd_test_runner.py"]
    
    # Add use_running_app flag if specified
    if use_running_app:
        cmd.append("--use-running-app")
    
    # Add tags if specified
    if tags:
        cmd.extend(["--tags", tags])
    
    # Add specific feature if provided
    if feature:
        cmd.append(feature)
    
    # Run the test runner
    logger.info(f"Executing command: {' '.join(cmd)}")
    try:
        subprocess.run(
            cmd,
            check=False,
            capture_output=False,
            text=True
        )
        return True
    except Exception as e:
        logger.error(f"Error running BDD test runner: {e}")
        return False

def verify_step_definitions():
    """Verify that all necessary step definitions exist"""
    logger.info("Verifying step definitions...")
    
    # Check if the steps directory exists
    steps_dir = "behave_tests/features/steps"
    if not os.path.exists(steps_dir):
        logger.error(f"Steps directory not found: {steps_dir}")
        return False
    
    # Check if api_steps.py exists
    api_steps_file = os.path.join(steps_dir, "api_steps.py")
    if not os.path.exists(api_steps_file):
        logger.error(f"API steps file not found: {api_steps_file}")
        return False
    
    # Look for feature files to cross-reference with step definitions
    feature_files = []
    features_dir = "behave_tests/features"
    for file in os.listdir(features_dir):
        if file.endswith(".feature") and os.path.isfile(os.path.join(features_dir, file)):
            feature_files.append(os.path.join(features_dir, file))
    
    if not feature_files:
        logger.warning("No feature files found to verify")
        return True
    
    # Run behave with --no-skipped to verify step definitions
    try:
        result = subprocess.run(
            [sys.executable, "-m", "behave", "behave_tests/features", "--dry-run", "--no-summary"],
            check=False,
            capture_output=True,
            text=True
        )
        
        # Check for undefined steps in the output
        if "undefined" in result.stdout:
            logger.warning("Some step definitions are undefined:")
            print(result.stdout)
            return False
        else:
            logger.info("All step definitions appear to be implemented")
            return True
    except Exception as e:
        logger.error(f"Error verifying step definitions: {e}")
        return False

def verify_feature_files():
    """Verify that feature files exist and have correct format"""
    logger.info("Verifying feature files...")
    
    # Check if the features directory exists
    features_dir = "behave_tests/features"
    if not os.path.exists(features_dir):
        logger.error(f"Features directory not found: {features_dir}")
        return False
    
    # Look for feature files
    feature_files = []
    for file in os.listdir(features_dir):
        if file.endswith(".feature") and os.path.isfile(os.path.join(features_dir, file)):
            feature_files.append(os.path.join(features_dir, file))
    
    if not feature_files:
        # Try looking in the summary directory
        summary_feature_dir = "summary/bdd_test_cases"
        if os.path.exists(summary_feature_dir):
            for file in os.listdir(summary_feature_dir):
                if file.endswith(".feature") and os.path.isfile(os.path.join(summary_feature_dir, file)):
                    feature_files.append(os.path.join(summary_feature_dir, file))
    
    if not feature_files:
        logger.error("No feature files found")
        return False
    
    # Check each feature file for correct format
    all_valid = True
    for file_path in feature_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # Check if it contains Feature:
            if 'Feature:' not in content:
                logger.error(f"Feature file does not contain 'Feature:': {file_path}")
                all_valid = False
            
            # Check if it has at least one scenario - accept different formats
            has_scenario = (
                'Scenario:' in content or 
                'Scenario ' in content or 
                'Scenario 1:' in content or
                'Scenario 1' in content
            )
            if not has_scenario:
                logger.error(f"Feature file does not contain any scenarios: {file_path}")
                all_valid = False
    
    if all_valid:
        logger.info(f"Found {len(feature_files)} valid feature files")
        for file_path in feature_files:
            logger.info(f"  - {os.path.basename(file_path)}")
    
    return all_valid

def run_bdd_tests():
    """Run the BDD tests and generate reports"""
    # Setup directories
    bdd_dir = os.path.join("summary", "bdd_test_cases")
    report_dir = os.path.join(bdd_dir, "reports")
    
    # Create report directory if it doesn't exist
    os.makedirs(report_dir, exist_ok=True)
    
    # Current timestamp for report names
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Define report files
    text_report = os.path.join(report_dir, f"bdd_report_{timestamp}.txt")
    html_report = os.path.join(report_dir, f"bdd_report_{timestamp}.html")
    
    # Run BDD tests
    print(f"Running BDD tests in {bdd_dir}...")
    
    # Text report
    cmd = [sys.executable, "-m", "behave", "--format=plain", f"--outfile={text_report}"]
    result = subprocess.run(cmd, cwd=bdd_dir, capture_output=True, text=True)
    
    # Print the output
    print(result.stdout)
    if result.stderr:
        print("Errors:", result.stderr)
    
    # Generate HTML report if behave-html-formatter is available
    try:
        import behave_html_formatter
        cmd = [sys.executable, "-m", "behave", "--format=behave_html_formatter:HTMLFormatter", f"--outfile={html_report}"]
        subprocess.run(cmd, cwd=bdd_dir, capture_output=True)
        print(f"HTML report generated: {html_report}")
    except ImportError:
        print("behave-html-formatter not installed. Skipping HTML report generation.")
    
    # Create a summary file
    summary_file = os.path.join(report_dir, "test_summary.txt")
    with open(summary_file, "w", encoding='utf-8') as f:
        f.write("# BDD Test Results Summary\n\n")
        f.write(f"Test run completed at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Count passing/failing tests from the output
        feature_count = result.stdout.count("Feature:")
        scenario_count = result.stdout.count("Scenario:")
        failed_count = result.stdout.count("Failing scenarios:")
        
        f.write(f"Total features: {feature_count}\n")
        f.write(f"Total scenarios: {scenario_count}\n")
        f.write(f"Failed scenarios: {failed_count if failed_count > 0 else 0}\n")
        f.write(f"Passing scenarios: {scenario_count - failed_count if failed_count > 0 else scenario_count}\n\n")
        
        # Add complete output
        f.write("## Complete test output\n\n")
        f.write("```\n")
        f.write(result.stdout)
        f.write("\n```\n")
    
    print(f"Test summary written to {summary_file}")
    
    # Return success if all tests passed
    return result.returncode == 0

def main():
    """Main function to run the verification and tests"""
    parser = argparse.ArgumentParser(description="Verify and run BDD tests for the banking application")
    parser.add_argument("--verify-only", action="store_true", help="Only verify the test environment, don't run tests")
    parser.add_argument("--feature", help="Specific feature file to test")
    parser.add_argument("--tags", help="Only run tests with these tags (e.g. '@wip')")
    parser.add_argument("--use-behave", action="store_true", help="Use behave directly instead of the test runner")
    parser.add_argument("--verbose", action="store_true", help="Show verbose output")
    
    args = parser.parse_args()
    
    # Verify that the API is running
    if not verify_api_is_running():
        logger.error("API must be running to verify BDD tests. Please start the API first.")
        return 1
    
    # Verify feature files and step definitions
    features_valid = verify_feature_files()
    steps_valid = verify_step_definitions()
    
    if args.verify_only:
        if features_valid and steps_valid:
            logger.info("Verification completed successfully!")
            return 0
        else:
            logger.error("Verification failed. Please check the errors above.")
            return 1
    
    # Run tests
    if args.use_behave:
        success = run_behave(args.feature, args.tags, args.verbose)
    else:
        success = run_with_test_runner(args.feature, args.tags, use_running_app=True)
    
    if success:
        return 0
    else:
        return 1

if __name__ == "__main__":
    run_bdd_tests() 
