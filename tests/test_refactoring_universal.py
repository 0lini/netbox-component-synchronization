"""
Universal tests for refactored component synchronization functionality.

This file replaces test_refactoring.py with more universal tests that work
across different NetBox versions and environments.
"""
import asyncio
from unittest.mock import Mock, MagicMock, patch
from tests.base import (
    BaseUniversalTestCase,
    ComponentRegistryTestMixin,
    AsyncUtilsTestMixin,
    ValidationTestMixin
)


class UniversalComponentRegistryTests(BaseUniversalTestCase, ComponentRegistryTestMixin):
    """Universal tests for component registry functionality."""
    
    def test_get_component_config_interface(self):
        """Test getting interface configuration."""
        try:
            from netbox_component_synchronization.component_registry import get_component_config
            
            config = get_component_config('interface')
            self.assertEqual(config.component_label, "Interfaces")
            self.assertIsNotNone(config.model)
            self.assertIsNotNone(config.template_model)
            self.assert_component_config_valid(config, 'interface')
            
        except ImportError:
            self.skipTest("Component registry not available")
    
    def test_get_component_config_invalid(self):
        """Test getting configuration for invalid component type."""
        try:
            from netbox_component_synchronization.component_registry import get_component_config
            
            with self.assertRaises(ValueError):
                get_component_config('invalid_type')
                
        except ImportError:
            self.skipTest("Component registry not available")
    
    def test_component_registry_completeness(self):
        """Test that all expected component types are in registry."""
        self.test_registry_completeness()
    
    def test_create_component_factory(self):
        """Test that factory functions are created correctly."""
        try:
            from netbox_component_synchronization.component_registry import (
                get_component_config,
                create_component_factory
            )
            
            config = get_component_config('interface')
            factory = create_component_factory(config)
            
            # Verify factory is callable
            self.assertTrue(callable(factory))
            
        except ImportError:
            self.skipTest("Component registry not available")


class UniversalAsyncUtilsTests(BaseUniversalTestCase, AsyncUtilsTestMixin):
    """Universal tests for async utility functions."""
    
    def test_parse_form_ids_functionality(self):
        """Test parse_form_ids function with various inputs."""
        try:
            from netbox_component_synchronization.async_utils import parse_form_ids
            
            # Test normal case
            result = parse_form_ids(['1', '2', '3'])
            self.assertEqual(result, [1, 2, 3])
            
            # Test with invalid entries
            result = parse_form_ids(['1', 'invalid', '3'])
            self.assertEqual(result, [1, 3])
            
            # Test empty case
            result = parse_form_ids([])
            self.assertEqual(result, [])
            
        except ImportError:
            self.skipTest("Async utils not available")
            
    def test_filter_valid_ids_functionality(self):
        """Test filter_valid_ids function."""
        try:
            from netbox_component_synchronization.async_utils import filter_valid_ids
            
            parsed_ids = [1, 2, 3, 4]
            valid_ids = [1, 3, 5, 7]
            
            result = filter_valid_ids(parsed_ids, valid_ids)
            self.assertEqual(result, [1, 3])
            
        except ImportError:
            self.skipTest("Async utils not available")
            
    def test_create_success_message_functionality(self):
        """Test create_success_message function."""
        try:
            from netbox_component_synchronization.async_utils import create_success_message
            
            stats = {'created': 2, 'updated': 1, 'deleted': 3, 'fixed': 1}
            message = create_success_message(stats, 'interface')
            
            self.assertIsInstance(message, str)
            self.assertIn('interface', message.lower())
            
        except ImportError:
            self.skipTest("Async utils not available")


class UniversalComponentProcessorTests(BaseUniversalTestCase, AsyncUtilsTestMixin):
    """Universal tests for ComponentProcessor class."""
    
    def setUp(self):
        super().setUp()
        self.processor = self.create_mock_component_processor()
        
    def test_component_processor_initialization(self):
        """Test ComponentProcessor initialization."""
        try:
            from netbox_component_synchronization.async_utils import ComponentProcessor
            
            mock_device = Mock()
            mock_device.id = 1
            mock_device.name = 'test-device'
            
            mock_object_type = Mock()
            mock_object_type.__name__ = 'Interface'
            
            mock_template_type = Mock()
            mock_template_type.__name__ = 'InterfaceTemplate'
            
            processor = ComponentProcessor(
                mock_device, mock_object_type, mock_template_type, 'interface'
            )
            
            self.assertEqual(processor.device, mock_device)
            self.assertEqual(processor.object_type, mock_object_type)
            self.assertEqual(processor.object_template_type, mock_template_type)
            self.assertEqual(processor.component_type, 'interface')
            
            # Check stats initialization
            expected_stats = {'created': 0, 'updated': 0, 'deleted': 0, 'fixed': 0}
            for key in expected_stats:
                self.assertIn(key, processor.stats)
                self.assertEqual(processor.stats[key], 0)
                
        except ImportError:
            self.skipTest("ComponentProcessor not available")


class UniversalUtilsRefactoringTests(BaseUniversalTestCase):
    """Universal tests for refactored utility functions."""
    
    def setUp(self):
        super().setUp()
        self.factory = self.create_mock_request('GET', '/')
        
    def test_parse_and_filter_ids_functionality(self):
        """Test the integrated _parse_and_filter_ids function."""
        try:
            from netbox_component_synchronization.utils import _parse_and_filter_ids
            
            raw_ids = ['1', '2', 'invalid', '3', '4']
            valid_ids = [1, 2, 3]
            
            result = _parse_and_filter_ids(raw_ids, valid_ids)
            self.assertEqual(result, [1, 2, 3])
            
        except ImportError:
            self.skipTest("Utils module not available")
            
    def test_create_or_update_component_logic(self):
        """Test component creation/update logic."""
        try:
            from netbox_component_synchronization.utils import _create_or_update_component
            from django.core.exceptions import ObjectDoesNotExist
            
            # Mock objects
            mock_object_type = Mock()
            mock_device = Mock()
            mock_components = Mock()
            
            # Test update existing component
            existing_component = Mock()
            mock_components.get.return_value = existing_component
            
            template_data = {'name': 'test', 'label': 'Test Component'}
            keys_to_avoid = ['id']
            
            result = _create_or_update_component(
                mock_object_type, mock_device, mock_components, 
                template_data, keys_to_avoid
            )
            
            self.assertEqual(result['action'], 'update')
            self.assertEqual(result['object'], existing_component)
            
            # Test create new component
            mock_components.get.side_effect = ObjectDoesNotExist()
            mock_new_component = Mock()
            mock_object_type.return_value = mock_new_component
            
            result = _create_or_update_component(
                mock_object_type, mock_device, mock_components, 
                template_data, keys_to_avoid
            )
            
            self.assertEqual(result['action'], 'create')
            self.assertEqual(result['object'], mock_new_component)
            
        except ImportError:
            self.skipTest("Utils module or Django not available")


class UniversalIntegrationTests(BaseUniversalTestCase):
    """Universal integration tests for the plugin."""
    
    def test_component_workflow_integration(self):
        """Test that component workflow can be initiated."""
        try:
            from netbox_component_synchronization.component_registry import get_component_config
            from netbox_component_synchronization.async_utils import ComponentProcessor
            
            # Get a component config
            config = get_component_config('interface')
            
            # Create mock objects for workflow
            mock_device = Mock()
            mock_device.id = 1
            
            # Create processor
            processor = ComponentProcessor(
                mock_device, config.model, config.template_model, 'interface'
            )
            
            # Verify processor is ready for operations
            self.assertIsNotNone(processor.device)
            self.assertIsNotNone(processor.object_type)
            self.assertIsNotNone(processor.object_template_type)
            
        except ImportError:
            self.skipTest("Integration components not available")
            
    def test_view_and_registry_integration(self):
        """Test that views can access component registry."""
        try:
            from netbox_component_synchronization.views import GenericComponentComparisonView
            from netbox_component_synchronization.component_registry import get_component_config
            
            # Test that view class exists
            self.assertTrue(callable(GenericComponentComparisonView))
            
            # Test that registry provides data for views
            config = get_component_config('interface')
            self.assertIsNotNone(config.model)
            self.assertIsNotNone(config.template_model)
            
        except ImportError:
            self.skipTest("Views or registry not available")


if __name__ == '__main__':
    # Simple test runner for basic validation
    import unittest
    unittest.main(verbosity=2)