#!/usr/bin/env python
import os
import subprocess
import shutil
import logging
import sys

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def run_enhanced_step_generator():
    """Run the enhanced step generator to create improved step definitions"""
    logging.info("Running enhanced step generator...")
    result = subprocess.run(["python", "enhanced_step_generator.py"], 
                           capture_output=True, text=True)
    
    if result.returncode != 0:
        logging.error(f"Error running enhanced step generator: {result.stderr}")
        return False
    
    logging.info(f"Enhanced step generator output: {result.stdout}")
    return True

def backup_original_files():
    """Backup original step definition files before replacing them"""
    steps_dir = os.path.join("summary", "bdd_test_cases", "steps")
    api_steps_file = os.path.join(steps_dir, "api_steps.py")
    
    if os.path.exists(api_steps_file):
        backup_file = api_steps_file + ".bak"
        shutil.copy2(api_steps_file, backup_file)
        logging.info(f"Backed up original api_steps.py to {backup_file}")
    
    return True

def restore_original_files():
    """Restore original step definition files after running"""
    steps_dir = os.path.join("summary", "bdd_test_cases", "steps")
    api_steps_file = os.path.join(steps_dir, "api_steps.py")
    backup_file = api_steps_file + ".bak"
    
    if os.path.exists(backup_file):
        shutil.copy2(backup_file, api_steps_file)
        logging.info(f"Restored original api_steps.py from {backup_file}")
    
    return True

def run_everything_fixed():
    """Run the run_everything_fixed.py script"""
    logging.info("Running run_everything_fixed.py...")
    process = subprocess.Popen(["python", "run_everything_fixed.py"], 
                             stdout=subprocess.PIPE, 
                             stderr=subprocess.STDOUT,
                             text=True,
                             bufsize=1)
    
    # Print output in real-time
    for line in iter(process.stdout.readline, ''):
        print(line, end='')
        sys.stdout.flush()
    
    process.wait()
    return process.returncode == 0

def main():
    """Main function to run the process"""
    try:
        # Step 1: Backup original files
        if not backup_original_files():
            logging.error("Failed to backup original files. Aborting.")
            return 1
        
        # Step 2: Run enhanced step generator
        if not run_enhanced_step_generator():
            logging.error("Failed to generate enhanced step definitions. Aborting.")
            restore_original_files()
            return 1
        
        # Step 3: Run run_everything_fixed.py
        success = run_everything_fixed()
        
        # Step 4: Restore original files (optional)
        # Uncomment the following if you want to restore original files
        # restore_original_files()
        
        if success:
            logging.info("Successfully ran run_everything_fixed.py with enhanced step definitions!")
            return 0
        else:
            logging.error("run_everything_fixed.py completed with errors.")
            return 1
        
    except Exception as e:
        logging.error(f"Error running the process: {e}")
        restore_original_files()
        return 1

if __name__ == "__main__":
    sys.exit(main()) 