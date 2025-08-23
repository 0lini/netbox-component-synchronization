#!/usr/bin/env python3
"""
Simple validation script to test auto-discovery functionality
without requiring a full NetBox environment.
"""

import sys
import os

# Add the package to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'netbox_component_synchronization'))

def test_auto_discovery_import():
    """Test that auto_discovery module can be imported"""
    try:
        import auto_discovery
        print("✓ auto_discovery module imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Failed to import auto_discovery: {e}")
        return False

def test_component_registry_import():
    """Test that component_registry module can be imported"""
    try:
        import component_registry
        print("✓ component_registry module imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Failed to import component_registry: {e}")
        return False

def test_urls_import():
    """Test that urls module can be imported"""
    try:
        import urls
        print("✓ urls module imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Failed to import urls: {e}")
        return False

def test_views_import():
    """Test that views module can be imported"""
    try:
        import views
        print("✓ views module imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Failed to import views: {e}")
        return False

def main():
    """Run basic validation tests"""
    print("Running auto-discovery validation tests...")
    print("=" * 50)
    
    tests = [
        test_auto_discovery_import,
        test_component_registry_import,
        test_urls_import,
        test_views_import,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("=" * 50)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All basic validation tests passed!")
        return 0
    else:
        print("✗ Some tests failed. This is expected in a non-NetBox environment.")
        return 1

if __name__ == "__main__":
    sys.exit(main())