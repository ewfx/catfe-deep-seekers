#!/usr/bin/env python3
"""
Script to run the Spring Boot Analyzer tests.
"""
import unittest
import sys

def main():
    """Run the tests."""
    print("Running Spring Boot Analyzer tests...")
    
    # Discover and run all tests
    test_suite = unittest.defaultTestLoader.discover('.', pattern='test_*.py')
    test_runner = unittest.TextTestRunner(verbosity=2)
    result = test_runner.run(test_suite)
    
    # Return non-zero exit code if any tests failed
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main()) 