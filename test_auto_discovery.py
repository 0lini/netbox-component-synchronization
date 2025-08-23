"""
Tests specifically for the auto-discovery functionality.
These tests should be run in a NetBox environment with Django available.
"""
import unittest
from unittest.mock import Mock, patch, MagicMock

try:
    from django.test import TestCase
    from django.apps import apps
    DJANGO_AVAILABLE = True
except ImportError:
    # Fallback for environments without Django
    DJANGO_AVAILABLE = False
    TestCase = unittest.TestCase


class AutoDiscoveryTests(TestCase):
    """Test the auto-discovery functionality"""
    
    def setUp(self):
        if not DJANGO_AVAILABLE:
            self.skipTest("Django not available")
    
    @patch('netbox_component_synchronization.auto_discovery.apps')
    def test_component_discovery_basic(self, mock_apps):
        """Test basic component discovery functionality"""
        from netbox_component_synchronization.auto_discovery import ComponentDiscovery
        
        # Mock the dcim app and models
        mock_app = Mock()
        mock_apps.get_app_config.return_value = mock_app
        
        # Create mock models
        mock_interface = Mock()
        mock_interface.__name__ = 'Interface'
        mock_interface._meta.get_fields.return_value = []
        
        mock_interface_template = Mock() 
        mock_interface_template.__name__ = 'InterfaceTemplate'
        
        mock_app.get_models.return_value = [mock_interface]
        mock_app.get_model.return_value = mock_interface_template
        
        discovery = ComponentDiscovery()
        
        # Mock the device field check
        with patch.object(discovery, '_is_component_model', return_value=True):
            with patch.object(discovery, '_get_template_model', return_value=mock_interface_template):
                with patch.object(discovery, '_analyze_model_fields', return_value=('id', 'name')):
                    components = discovery.discover_components()
                    
        self.assertIsInstance(components, dict)
    
    def test_component_label_generation(self):
        """Test component label generation"""
        from netbox_component_synchronization.auto_discovery import ComponentDiscovery
        
        discovery = ComponentDiscovery()
        
        # Mock a model
        mock_model = Mock()
        mock_model.__name__ = 'PowerPort'
        
        label = discovery._generate_component_label(mock_model)
        self.assertEqual(label, 'Power ports')
        
        # Test another case
        mock_model.__name__ = 'Interface'
        label = discovery._generate_component_label(mock_model)
        self.assertEqual(label, 'Interfaces')
    
    def test_permissions_generation(self):
        """Test permissions generation"""
        from netbox_component_synchronization.auto_discovery import ComponentDiscovery
        
        discovery = ComponentDiscovery()
        
        # Mock a model
        mock_model = Mock()
        mock_model._meta.app_label = 'dcim'
        mock_model._meta.model_name = 'interface'
        
        permissions = discovery._generate_permissions(mock_model)
        expected = (
            'dcim.view_interface',
            'dcim.add_interface',
            'dcim.change_interface',
            'dcim.delete_interface',
        )
        self.assertEqual(permissions, expected)
    
    def test_field_analysis(self):
        """Test model field analysis"""
        from netbox_component_synchronization.auto_discovery import ComponentDiscovery
        
        discovery = ComponentDiscovery()
        
        # Mock model fields
        mock_field1 = Mock()
        mock_field1.name = 'name'
        mock_field1.one_to_many = False
        mock_field1.many_to_many = False
        mock_field1.get_internal_type.return_value = 'CharField'
        
        mock_field2 = Mock()
        mock_field2.name = 'created' 
        mock_field2.one_to_many = False
        mock_field2.many_to_many = False
        mock_field2.get_internal_type.return_value = 'DateTimeField'
        
        mock_model = Mock()
        mock_model._meta.get_fields.return_value = [mock_field1, mock_field2]
        
        fields = discovery._analyze_model_fields(mock_model)
        
        # Should include 'name' but exclude 'created'
        self.assertIn('name', fields)
        self.assertNotIn('created', fields)


class ComponentRegistryAutoDiscoveryTests(TestCase):
    """Test component registry integration with auto-discovery"""
    
    def setUp(self):
        if not DJANGO_AVAILABLE:
            self.skipTest("Django not available")
    
    @patch('netbox_component_synchronization.component_registry.discover_components')
    def test_registry_population(self, mock_discover):
        """Test that registry gets populated from auto-discovery"""
        from netbox_component_synchronization.component_registry import _populate_registry_from_discovery
        from netbox_component_synchronization.auto_discovery import DiscoveredComponent
        
        # Mock discovered component
        mock_model = Mock()
        mock_model.__name__ = 'TestComponent'
        
        mock_template = Mock()
        
        mock_discovered = DiscoveredComponent(
            name='testcomponent',
            model=mock_model,
            template_model=mock_template,
            component_label='Test components',
            factory_fields=('id', 'name'),
            permissions=('dcim.view_testcomponent',),
        )
        
        mock_discover.return_value = {'testcomponent': mock_discovered}
        
        # This should not raise an exception
        _populate_registry_from_discovery()
    
    def test_get_all_component_types(self):
        """Test getting all component types"""
        from netbox_component_synchronization.component_registry import get_all_component_types
        
        with patch('netbox_component_synchronization.component_registry._populate_registry_from_discovery'):
            component_types = get_all_component_types()
            self.assertIsInstance(component_types, list)
            # Should include the static ones at minimum
            self.assertIn('interface', component_types)
            self.assertIn('powerport', component_types)


class UrlGenerationTests(TestCase):
    """Test URL pattern generation"""
    
    def setUp(self):
        if not DJANGO_AVAILABLE:
            self.skipTest("Django not available")
    
    @patch('netbox_component_synchronization.urls.get_all_component_types')
    @patch('netbox_component_synchronization.urls.views')
    def test_url_pattern_creation(self, mock_views, mock_get_types):
        """Test that URL patterns are created correctly"""
        from netbox_component_synchronization.urls import create_component_url_patterns
        
        mock_get_types.return_value = ['interface', 'powerport']
        mock_views.InterfaceComparisonView = Mock()
        mock_views.PowerportComparisonView = Mock() 
        mock_views.create_component_view = Mock(return_value=Mock())
        
        patterns = create_component_url_patterns()
        
        self.assertIsInstance(patterns, list)
        self.assertEqual(len(patterns), 2)


class IntegrationTests(TestCase):
    """Integration tests for the complete auto-discovery flow"""
    
    def setUp(self):
        if not DJANGO_AVAILABLE:
            self.skipTest("Django not available")
    
    @patch('netbox_component_synchronization.auto_discovery.apps')
    @patch('netbox_component_synchronization.component_registry.discover_components')
    def test_complete_autodiscovery_flow(self, mock_discover, mock_apps):
        """Test the complete flow from discovery to URL generation"""
        from netbox_component_synchronization.auto_discovery import DiscoveredComponent
        from netbox_component_synchronization.component_registry import get_all_component_types
        from netbox_component_synchronization.urls import create_component_url_patterns
        
        # Mock discovered component
        mock_model = Mock()
        mock_model.__name__ = 'TestPort'
        
        mock_template = Mock()
        mock_template.__name__ = 'TestPortTemplate'
        
        mock_discovered = DiscoveredComponent(
            name='testport',
            model=mock_model,
            template_model=mock_template,
            component_label='Test ports',
            factory_fields=('id', 'name', 'type'),
            permissions=('dcim.view_testport', 'dcim.add_testport'),
        )
        
        mock_discover.return_value = {'testport': mock_discovered}
        
        # Test that the component gets included in the registry
        component_types = get_all_component_types()
        self.assertIn('testport', component_types)
        
        # Test URL pattern generation (will use mocks)
        with patch('netbox_component_synchronization.urls.views') as mock_views:
            mock_views.create_component_view = Mock(return_value=Mock())
            
            patterns = create_component_url_patterns()
            
            # Should have created patterns for all components including the new one
            self.assertIsInstance(patterns, list)
            
            # Check that views were created for discovered components
            if patterns:  # Only check if patterns were generated
                mock_views.create_component_view.assert_called()
    
    def test_configuration_integration(self):
        """Test that configuration settings are properly integrated"""
        from netbox_component_synchronization.discovery_config import AutoDiscoveryConfig
        
        config = AutoDiscoveryConfig()
        
        # Test default values
        self.assertIsInstance(config.enabled, bool)
        self.assertIsInstance(config.excluded_types, list)
        self.assertIsInstance(config.compare_description, bool)
        
        # Test exclusion check
        result = config.is_component_excluded('testcomponent')
        self.assertIsInstance(result, bool)


if __name__ == '__main__':
    unittest.main()