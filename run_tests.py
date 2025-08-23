#!/usr/bin/env python3
"""
Universal test runner for NetBox Component Synchronization plugin.

This script can run tests in different environments:
1. Full NetBox environment (with Django and NetBox models)
2. Django-only environment (without NetBox models) 
3. Minimal environment (without Django)

The tests gracefully degrade based on available dependencies.
"""
import sys
import os
import subprocess
import argparse
from pathlib import Path

# Add the plugin to Python path
plugin_dir = Path(__file__).parent
sys.path.insert(0, str(plugin_dir))


def check_environment():
    """Check what's available in the current environment."""
    environment = {
        'django': False,
        'netbox': False,
        'pytest': False
    }
    
    try:
        import django
        environment['django'] = True
        print(f"✓ Django {django.VERSION} available")
    except ImportError:
        print("✗ Django not available")
        
    try:
        import netbox
        environment['netbox'] = True
        print(f"✓ NetBox available")
    except ImportError:
        print("✗ NetBox not available")
        
    try:
        import pytest
        environment['pytest'] = True
        print(f"✓ pytest available")
    except ImportError:
        print("✗ pytest not available")
        
    return environment


def run_pytest_tests(test_dir="tests", verbose=True):
    """Run tests using pytest."""
    cmd = ["python", "-m", "pytest"]
    
    if verbose:
        cmd.append("-v")
        
    cmd.extend([
        test_dir,
        "--tb=short",
        "--disable-warnings"
    ])
    
    print(f"Running: {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=plugin_dir)


def run_unittest_tests(test_pattern="test_*.py", verbose=True):
    """Run tests using unittest."""
    cmd = ["python", "-m", "unittest"]
    
    if verbose:
        cmd.append("-v")
        
    cmd.append("discover")
    cmd.extend(["-s", ".", "-p", test_pattern])
    
    print(f"Running: {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=plugin_dir)


def run_validation_only():
    """Run basic validation tests."""
    print("Running basic validation tests...")
    
    try:
        # Import validation test
        from test_validation import main as validation_main
        return validation_main()
    except ImportError:
        print("Validation test not available, running basic import test")
        
        # Basic import test
        try:
            import netbox_component_synchronization
            print("✓ Plugin package imports successfully")
            return 0
        except ImportError as e:
            print(f"✗ Plugin package import failed: {e}")
            return 1


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="Universal test runner for NetBox Component Synchronization")
    parser.add_argument("--test-type", choices=["all", "unit", "integration", "validation"], 
                       default="all", help="Type of tests to run")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--pytest", action="store_true", help="Force pytest usage")
    parser.add_argument("--unittest", action="store_true", help="Force unittest usage")
    
    args = parser.parse_args()
    
    print("NetBox Component Synchronization - Universal Test Runner")
    print("=" * 60)
    
    # Check environment
    env = check_environment()
    print()
    
    # Determine test strategy
    if args.test_type == "validation":
        return run_validation_only()
        
    # Choose test runner
    if args.pytest and env['pytest']:
        runner = "pytest"
    elif args.unittest:
        runner = "unittest"
    elif env['pytest']:
        runner = "pytest"
    else:
        runner = "unittest"
        
    print(f"Using test runner: {runner}")
    print()
    
    # Run tests based on environment and preferences
    if runner == "pytest":
        if args.test_type == "unit":
            result = run_pytest_tests("tests/test_*.py", args.verbose)
        elif args.test_type == "integration":
            result = run_pytest_tests("tests/test_*integration*.py", args.verbose)
        else:
            result = run_pytest_tests("tests", args.verbose)
    else:
        # Use unittest
        if args.test_type == "unit":
            result = run_unittest_tests("test_*.py", args.verbose)
        else:
            result = run_unittest_tests("test_*.py", args.verbose)
    
    return result.returncode if hasattr(result, 'returncode') else result


if __name__ == "__main__":
    sys.exit(main())