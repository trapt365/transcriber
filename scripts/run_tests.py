#!/usr/bin/env python3
"""Test runner script for the transcriber application."""

import os
import sys
import subprocess
import argparse
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_unit_tests(verbose=False, coverage=True):
    """Run unit tests."""
    cmd = ['python', '-m', 'pytest', 'tests/unit/']
    
    if verbose:
        cmd.append('-v')
    
    if coverage:
        cmd.extend([
            '--cov=backend',
            '--cov-report=term-missing',
            '--cov-report=html'
        ])
    
    print("Running unit tests...")
    return subprocess.run(cmd, cwd=project_root).returncode


def run_integration_tests(verbose=False):
    """Run integration tests."""
    cmd = ['python', '-m', 'pytest', 'tests/integration/', '-m', 'integration']
    
    if verbose:
        cmd.append('-v')
    
    print("Running integration tests...")
    return subprocess.run(cmd, cwd=project_root).returncode


def run_all_tests(verbose=False, coverage=True, skip_integration=False):
    """Run all tests."""
    cmd = ['python', '-m', 'pytest']
    
    if skip_integration:
        cmd.extend(['-m', 'not integration'])
    
    if verbose:
        cmd.append('-v')
    
    if coverage:
        cmd.extend([
            '--cov=backend',
            '--cov-report=term-missing',
            '--cov-report=html'
        ])
    
    print("Running all tests...")
    return subprocess.run(cmd, cwd=project_root).returncode


def check_dependencies():
    """Check for required test dependencies."""
    try:
        import pytest
        import pytest_cov
        import pytest_mock
        import pytest_flask
        print("✓ All test dependencies available")
        return True
    except ImportError as e:
        print(f"✗ Missing test dependency: {e}")
        print("Run: pip install -r requirements-dev.txt")
        return False


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description='Run transcriber tests')
    parser.add_argument('--unit', action='store_true', help='Run only unit tests')
    parser.add_argument('--integration', action='store_true', help='Run only integration tests')
    parser.add_argument('--no-coverage', action='store_true', help='Skip coverage reporting')
    parser.add_argument('--skip-integration', action='store_true', help='Skip integration tests')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--check-deps', action='store_true', help='Check test dependencies')
    
    args = parser.parse_args()
    
    if args.check_deps:
        return 0 if check_dependencies() else 1
    
    # Check dependencies first
    if not check_dependencies():
        return 1
    
    # Set test environment
    os.environ['FLASK_ENV'] = 'testing'
    os.environ['TESTING'] = 'true'
    
    exit_code = 0
    
    if args.unit:
        exit_code = run_unit_tests(args.verbose, not args.no_coverage)
    elif args.integration:
        exit_code = run_integration_tests(args.verbose)
    else:
        exit_code = run_all_tests(args.verbose, not args.no_coverage, args.skip_integration)
    
    if exit_code == 0:
        print("\n✓ All tests passed!")
    else:
        print(f"\n✗ Tests failed with exit code {exit_code}")
    
    return exit_code


if __name__ == '__main__':
    sys.exit(main())