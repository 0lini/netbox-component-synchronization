"""
Basic tests to validate the refactored component synchronization code.
"""
import asyncio
from unittest import TestCase
from unittest.mock import Mock, MagicMock, patch
from django.test import RequestFactory
from django.contrib.auth.models import User
from django.contrib.messages.storage.fallback import FallbackStorage

from netbox_component_synchronization.component_registry import (
    get_component_config,
    create_component_factory,
    COMPONENT_REGISTRY
)
from netbox_component_synchronization.async_utils import (
    ComponentProcessor,
    parse_form_ids,
    filter_valid_ids,
    create_success_message
)


class ComponentRegistryTests(TestCase):
    """Test the component registry functionality"""
    
    def test_get_component_config_interface(self):
        """Test getting interface configuration"""
        config = get_component_config('interface')
        self.assertEqual(config.component_label, "Interfaces")
        self.assertEqual(config.model.__name__, "Interface")
        self.assertEqual(config.template_model.__name__, "InterfaceTemplate")
        
    def test_get_component_config_invalid(self):
        """Test getting configuration for invalid component type"""
        with self.assertRaises(ValueError):
            get_component_config('invalid_type')
    
    def test_component_registry_completeness(self):
        """Test that all expected component types are in registry"""
        expected_types = [
            'interface', 'powerport', 'consoleport', 'consoleserverport',
            'poweroutlet', 'frontport', 'rearport', 'devicebay', 'modulebay'
        ]
        for component_type in expected_types:
            self.assertIn(component_type, COMPONENT_REGISTRY)
    
    def test_create_component_factory(self):
        """Test that factory functions are created correctly"""
        config = get_component_config('interface')
        factory = create_component_factory(config)
        self.assertTrue(callable(factory))


class AsyncUtilsTests(TestCase):
    """Test async utility functions"""
    
    def test_parse_form_ids(self):
        """Test parsing form IDs"""
        mock_request = Mock()
        mock_request.POST.getlist.return_value = ['1', '2', 'invalid', '3']
        
        result = parse_form_ids(mock_request, 'test_field')
        self.assertEqual(result, [1, 2, 3])
    
    def test_filter_valid_ids(self):
        """Test filtering valid IDs"""
        mock_qs = Mock()
        mock_qs.values_list.return_value = [1, 2, 3, 5]
        
        result = filter_valid_ids([1, 2, 4, 5], mock_qs)
        self.assertEqual(result, [1, 2, 5])
    
    def test_create_success_message(self):
        """Test success message creation"""
        stats = {'created': 2, 'updated': 1, 'deleted': 0, 'fixed': 3}
        message = create_success_message(stats, "interfaces")
        
        self.assertIn("created 2 interfaces", message)
        self.assertIn("updated 1 interfaces", message)
        self.assertIn("fixed 3 interfaces", message)
        self.assertNotIn("deleted", message)
    
    def test_create_success_message_empty(self):
        """Test success message with no changes"""
        stats = {'created': 0, 'updated': 0, 'deleted': 0, 'fixed': 0}
        message = create_success_message(stats, "interfaces")
        
        self.assertEqual(message, "No changes made to interfaces")


class ComponentProcessorTests(TestCase):
    """Test the ComponentProcessor class"""
    
    def setUp(self):
        self.mock_device = Mock()
        self.mock_object_type = Mock()
        self.mock_object_template_type = Mock()
        self.processor = ComponentProcessor(
            self.mock_device,
            self.mock_object_type,
            self.mock_object_template_type,
            "test_component"
        )
    
    def test_processor_initialization(self):
        """Test processor initializes correctly"""
        self.assertEqual(self.processor.device, self.mock_device)
        self.assertEqual(self.processor.object_type, self.mock_object_type)
        self.assertEqual(self.processor.component_type, "test_component")
        self.assertEqual(self.processor.stats['created'], 0)
    
    def test_stats_tracking(self):
        """Test that stats are tracked correctly"""
        self.processor.stats['created'] = 5
        self.processor.stats['updated'] = 3
        
        self.assertEqual(self.processor.stats['created'], 5)
        self.assertEqual(self.processor.stats['updated'], 3)


class UtilsRefactoringTests(TestCase):
    """Test the refactored utility functions"""
    
    def setUp(self):
        self.factory = RequestFactory()
    
    def test_parse_and_filter_ids_functionality(self):
        """Test the new _parse_and_filter_ids function"""
        from netbox_component_synchronization.utils import _parse_and_filter_ids
        
        raw_ids = ['1', '2', 'invalid', '3', '4']
        valid_ids = [1, 2, 3]
        
        result = _parse_and_filter_ids(raw_ids, valid_ids)
        self.assertEqual(result, [1, 2, 3])
    
    def test_create_or_update_component_logic(self):
        """Test component creation/update logic"""
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


if __name__ == '__main__':
    # Simple test runner for basic validation
    import unittest
    unittest.main()