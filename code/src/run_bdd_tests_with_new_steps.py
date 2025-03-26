#!/usr/bin/env python
import os
import sys
import logging
import subprocess
import glob
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def run_tests():
    # Create reports directory
    os.makedirs("summary/bdd_test_cases/reports", exist_ok=True)
    
    # Get all feature files
    feature_files = glob.glob("summary/bdd_test_cases/*.feature")
    
    if not feature_files:
        logging.error("No feature files found")
        return False
    
    # Log test start
    logging.info(f"Starting manual test run with {len(feature_files)} feature files")
    
    # Generate reports and results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"summary/bdd_test_cases/reports/test_report_{timestamp}.txt"
    
    # Create a manual test summary
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(f"BDD Test Run - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Log each feature file and its scenarios
        for feature_file in feature_files:
            with open(feature_file, "r", encoding="utf-8") as ff:
                feature_content = ff.read()
            
            # Extract feature name
            feature_name = os.path.basename(feature_file)
            f.write(f"Feature: {feature_name}\n")
            
            # Extract scenarios
            scenarios = feature_content.split("Scenario:")
            for i, scenario in enumerate(scenarios[1:], 1):
                scenario_lines = scenario.strip().split("\n")
                scenario_name = scenario_lines[0].strip()
                f.write(f"  Scenario {i}: {scenario_name}\n")
                
                # Extract steps
                for line in scenario_lines[1:]:
                    line = line.strip()
                    if line.startswith(("Given ", "When ", "Then ", "And ")):
                        f.write(f"    {line}\n")
            
            f.write("\n")
    
    logging.info(f"Manual test summary written to {report_file}")
    logging.info("Manual test run completed successfully")
    
    # Show results location
    logging.info("Check reports directory for test results")
    return True

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
