"""
Base test classes for universal NetBox component synchronization testing.

This module provides base classes and utilities that work across different
NetBox versions and environments, making tests more universal and maintainable.
"""
import unittest
import sys
import os
from unittest.mock import Mock, MagicMock, patch
from typing import Any, Dict, List, Optional

# Try to import Django components, fallback gracefully
try:
    from django.test import TestCase as DjangoTestCase
    from django.test import RequestFactory
    from django.contrib.auth.models import User
    from django.contrib.messages.storage.fallback import FallbackStorage
    DJANGO_AVAILABLE = True
except ImportError:
    # Fallback for environments without Django
    DJANGO_AVAILABLE = False
    DjangoTestCase = unittest.TestCase


class BaseUniversalTestCase(DjangoTestCase if DJANGO_AVAILABLE else unittest.TestCase):
    """
    Universal base test case that works with or without full Django/NetBox environment.
    
    This class provides common setup and utilities for testing component 
    synchronization functionality across different NetBox versions.
    """
    
    def setUp(self):
        """Set up test environment with graceful degradation."""
        super().setUp()
        self.django_available = DJANGO_AVAILABLE
        
        if DJANGO_AVAILABLE:
            self.factory = RequestFactory()
            self._setup_django_environment()
        else:
            self._setup_mock_environment()
            
    def _setup_django_environment(self):
        """Set up Django-specific test environment."""
        try:
            self.user = User.objects.create_user('testuser', 'test@example.com', 'pass')
        except Exception:
            # If database is not available, create mock user
            self.user = Mock()
            self.user.id = 1
            self.user.username = 'testuser'
            
    def _setup_mock_environment(self):
        """Set up mock environment for testing without Django."""
        self.factory = Mock()
        self.user = Mock()
        self.user.id = 1
        self.user.username = 'testuser'
        
    def create_mock_request(self, method='GET', path='/', user=None, **kwargs):
        """Create a mock request object for testing."""
        if self.django_available and hasattr(self, 'factory'):
            request = getattr(self.factory, method.lower())(path, **kwargs)
            request.user = user or self.user
            
            # Add messages framework
            messages = FallbackStorage(request)
            request._messages = messages
            
            return request
        else:
            # Create mock request
            request = Mock()
            request.method = method.upper()
            request.path = path
            request.user = user or self.user
            request.POST = Mock()
            request.GET = Mock()
            request._messages = Mock()
            return request
            
    def assert_component_config_valid(self, config, component_type):
        """Assert that a component configuration is valid."""
        required_attributes = ['component_label', 'model', 'template_model', 'comparison_class']
        
        for attr in required_attributes:
            self.assertTrue(hasattr(config, attr), 
                          f"Component config for {component_type} missing {attr}")
            self.assertIsNotNone(getattr(config, attr),
                               f"Component config {attr} for {component_type} is None")
                               
    def skip_if_no_django(self):
        """Skip test if Django is not available."""
        if not self.django_available:
            self.skipTest("Django not available")
            
    def skip_if_no_netbox(self):
        """Skip test if NetBox models are not available.""" 
        try:
            from dcim.models import Device, Interface
        except ImportError:
            self.skipTest("NetBox models not available")


class ComponentRegistryTestMixin:
    """Mixin providing common component registry test methods."""
    
    def get_expected_component_types(self):
        """Return list of expected component types for current NetBox version."""
        # Base component types that should exist in all supported versions
        base_types = [
            'interface', 'powerport', 'consoleport', 'consoleserverport',
            'poweroutlet', 'frontport', 'rearport', 'devicebay'
        ]
        
        # Additional types that may be version-specific
        optional_types = ['modulebay']
        
        return base_types, optional_types
        
    def test_registry_completeness(self):
        """Test that component registry contains expected types."""
        from netbox_component_synchronization.component_registry import COMPONENT_REGISTRY
        
        base_types, optional_types = self.get_expected_component_types()
        
        # Check all base types are present
        for component_type in base_types:
            self.assertIn(component_type, COMPONENT_REGISTRY,
                         f"Missing required component type: {component_type}")
                         
        # Check optional types (don't fail if missing)
        present_optional = []
        for component_type in optional_types:
            if component_type in COMPONENT_REGISTRY:
                present_optional.append(component_type)
                
        print(f"Optional component types present: {present_optional}")


class AsyncUtilsTestMixin:
    """Mixin providing common async utilities test methods."""
    
    def create_mock_component_processor(self):
        """Create a mock ComponentProcessor for testing."""
        mock_device = Mock()
        mock_device.id = 1
        mock_device.name = 'test-device'
        
        mock_object_type = Mock()
        mock_object_type.__name__ = 'TestComponent'
        
        mock_template_type = Mock()
        mock_template_type.__name__ = 'TestComponentTemplate'
        
        try:
            from netbox_component_synchronization.async_utils import ComponentProcessor
            processor = ComponentProcessor(
                mock_device, mock_object_type, mock_template_type, 'test'
            )
        except ImportError:
            # Create mock processor if module not available
            processor = Mock()
            processor.device = mock_device
            processor.object_type = mock_object_type
            processor.object_template_type = mock_template_type
            processor.component_type = 'test'
            processor.stats = {'created': 0, 'updated': 0, 'deleted': 0, 'fixed': 0}
            
        return processor


class ValidationTestMixin:
    """Mixin providing validation test utilities."""
    
    def assert_module_importable(self, module_name, package='netbox_component_synchronization'):
        """Assert that a module can be imported."""
        try:
            module_path = f"{package}.{module_name}" if package else module_name
            __import__(module_path)
            return True
        except ImportError as e:
            self.fail(f"Failed to import {module_path}: {e}")
            
    def test_core_modules_importable(self):
        """Test that core plugin modules can be imported."""
        core_modules = [
            'component_registry',
            'utils', 
            'views',
            'forms',
            'comparison'
        ]
        
        for module in core_modules:
            with self.subTest(module=module):
                self.assert_module_importable(module)


def get_netbox_version():
    """Get the current NetBox version if available."""
    try:
        import netbox
        return getattr(netbox, 'VERSION', 'unknown')
    except ImportError:
        return None


def is_netbox_version_at_least(min_version):
    """Check if NetBox version is at least the specified version."""
    current = get_netbox_version()
    if current is None:
        return False
        
    try:
        # Simple version comparison (assumes semantic versioning)
        current_parts = [int(x) for x in current.split('.')]
        min_parts = [int(x) for x in min_version.split('.')]
        
        for i in range(max(len(current_parts), len(min_parts))):
            c = current_parts[i] if i < len(current_parts) else 0
            m = min_parts[i] if i < len(min_parts) else 0
            if c > m:
                return True
            elif c < m:
                return False
        return True
    except (ValueError, AttributeError):
        return False