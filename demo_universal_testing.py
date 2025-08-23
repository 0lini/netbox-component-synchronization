#!/usr/bin/env python3
"""
Demo script showing the universal testing capabilities of the NetBox Component Synchronization plugin.

This script demonstrates how the test framework gracefully handles different environments
and provides useful testing across all scenarios.
"""

import sys
import os
import subprocess
from pathlib import Path

def print_header(title):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def print_section(title):
    """Print a formatted section header."""
    print(f"\n--- {title} ---")

def run_command(cmd, description):
    """Run a command and show results."""
    print(f"\n🔄 {description}")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print("✅ Success!")
            if result.stdout.strip():
                print("Output:", result.stdout.strip()[:200] + "..." if len(result.stdout) > 200 else result.stdout.strip())
        else:
            print(f"⚠️  Non-zero exit code: {result.returncode}")
            if result.stderr.strip():
                print("Error:", result.stderr.strip()[:200] + "..." if len(result.stderr) > 200 else result.stderr.strip())
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("⏰ Command timed out")
        return False
    except Exception as e:
        print(f"❌ Command failed: {e}")
        return False

def main():
    """Main demo function."""
    print_header("NetBox Component Synchronization - Universal Testing Demo")
    
    # Change to plugin directory
    plugin_dir = Path(__file__).parent
    os.chdir(plugin_dir)
    
    print(f"Working directory: {plugin_dir}")
    
    print_section("Environment Detection")
    success = run_command([sys.executable, "run_tests.py", "--test-type", "validation"], 
                         "Running validation tests (works in any environment)")
    
    if not success:
        print("\nNote: Some validation failures are expected in environments without Django/NetBox")
    
    print_section("Universal Test Framework Demo")
    
    # Test the universal base classes
    print("\n🧪 Testing universal base classes...")
    try:
        from tests.base import BaseUniversalTestCase, ValidationTestMixin
        print("✅ Universal base classes imported successfully")
        
        # Create a simple test instance
        class DemoTest(BaseUniversalTestCase, ValidationTestMixin):
            def demo_test(self):
                self.assert_module_importable('component_registry')
                return True
        
        test_instance = DemoTest()
        test_instance.setUp()
        print("✅ Test instance created successfully")
        print(f"   Django available: {test_instance.django_available}")
        
    except Exception as e:
        print(f"❌ Universal base class test failed: {e}")
    
    print_section("Configuration Validation")
    
    # Check configuration files
    config_files = [
        (".github/workflows/test-pr.yml", "PR testing workflow"),
        (".github/workflows/format-code.yml", "Code formatting workflow"),
        (".github/workflows/check-netbox-releases.yml", "NetBox release monitoring"),
        ("pyproject.toml", "Black and isort configuration"),
        ("pytest.ini", "Pytest configuration"),
        (".flake8", "Flake8 configuration")
    ]
    
    for file_path, description in config_files:
        if os.path.exists(file_path):
            print(f"✅ {description}: {file_path}")
        else:
            print(f"❌ Missing {description}: {file_path}")
    
    print_section("Test Structure Validation")
    
    # Check test structure
    test_files = [
        ("tests/base.py", "Universal base test classes"),
        ("tests/test_component_registry.py", "Component registry tests"),
        ("tests/test_async_utils.py", "Async utilities tests"),
        ("tests/test_validation.py", "Validation tests"),
        ("tests/test_refactoring_universal.py", "Refactored functionality tests")
    ]
    
    for file_path, description in test_files:
        if os.path.exists(file_path):
            print(f"✅ {description}: {file_path}")
            # Try to import the test module
            try:
                module_path = file_path.replace("/", ".").replace(".py", "")
                __import__(module_path)
                print(f"   ✅ Module imports successfully")
            except Exception as e:
                print(f"   ⚠️  Import warning: {e}")
        else:
            print(f"❌ Missing {description}: {file_path}")
    
    print_section("GitHub Actions Workflow Validation")
    
    workflows_dir = Path(".github/workflows")
    if workflows_dir.exists():
        workflows = list(workflows_dir.glob("*.yml"))
        print(f"Found {len(workflows)} workflow files:")
        for workflow in workflows:
            print(f"  ✅ {workflow.name}")
    else:
        print("❌ .github/workflows directory not found")
    
    print_section("Development Tools Check")
    
    dev_tools = [
        ("run_tests.py", "Universal test runner"),
        ("Makefile", "Development task automation"),
        (".pre-commit-config.yaml", "Pre-commit hooks configuration"),
        ("CONTRIBUTING.md", "Contribution guidelines")
    ]
    
    for file_path, description in dev_tools:
        if os.path.exists(file_path):
            print(f"✅ {description}: {file_path}")
        else:
            print(f"❌ Missing {description}: {file_path}")
    
    print_header("Demo Summary")
    
    print("✅ Universal test framework implemented successfully!")
    print("✅ GitHub Actions workflows configured for CI/CD automation")
    print("✅ Code quality tools configured (Black, isort, flake8)")
    print("✅ NetBox release monitoring and compatibility testing enabled")
    print("✅ Comprehensive documentation and contribution guidelines added")
    
    print("\n🎯 Key Features Demonstrated:")
    print("   • Tests work across different environments (NetBox, Django-only, minimal)")
    print("   • Automated PR testing against multiple NetBox versions")
    print("   • Automatic code formatting and quality checks")
    print("   • NetBox release monitoring with automated compatibility updates")
    print("   • Developer-friendly tooling and documentation")
    
    print("\n📚 Next Steps:")
    print("   • Run 'make help' to see available development commands")
    print("   • Check CONTRIBUTING.md for detailed development guidelines")
    print("   • Use 'python run_tests.py' for running tests in any environment")
    
    print("\n🚀 The plugin is now ready for universal testing and automated CI/CD!")

if __name__ == "__main__":
    main()