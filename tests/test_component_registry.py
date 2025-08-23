"""
Universal tests for component registry functionality.

These tests work across different NetBox versions and environments.
"""
from tests.base import (
    BaseUniversalTestCase, 
    ComponentRegistryTestMixin,
    ValidationTestMixin
)


class ComponentRegistryTests(BaseUniversalTestCase, ComponentRegistryTestMixin, ValidationTestMixin):
    """Universal tests for component registry functionality."""
    
    def test_component_registry_import(self):
        """Test that component registry can be imported."""
        self.assert_module_importable('component_registry')
        
    def test_get_component_config_function(self):
        """Test get_component_config function exists and works."""
        try:
            from netbox_component_synchronization.component_registry import get_component_config
            
            # Test with a known component type
            config = get_component_config('interface')
            self.assert_component_config_valid(config, 'interface')
            
        except ImportError:
            self.skipTest("Component registry not available")
            
    def test_get_component_config_invalid_type(self):
        """Test get_component_config with invalid component type."""
        try:
            from netbox_component_synchronization.component_registry import get_component_config
            
            with self.assertRaises(ValueError):
                get_component_config('invalid_component_type')
                
        except ImportError:
            self.skipTest("Component registry not available")
            
    def test_component_factory_creation(self):
        """Test that component factory functions can be created."""
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
            
    def test_registry_structure(self):
        """Test that component registry has expected structure."""
        try:
            from netbox_component_synchronization.component_registry import COMPONENT_REGISTRY
            
            self.assertIsInstance(COMPONENT_REGISTRY, dict)
            self.assertGreater(len(COMPONENT_REGISTRY), 0)
            
            # Test structure of first registry entry
            first_key = next(iter(COMPONENT_REGISTRY))
            first_config = COMPONENT_REGISTRY[first_key]
            
            self.assert_component_config_valid(first_config, first_key)
            
        except ImportError:
            self.skipTest("Component registry not available")


class ComponentConfigTests(BaseUniversalTestCase):
    """Tests for component configuration objects."""
    
    def setUp(self):
        super().setUp()
        self.skip_if_no_django()
        
    def test_interface_config(self):
        """Test interface component configuration."""
        try:
            from netbox_component_synchronization.component_registry import get_component_config
            
            config = get_component_config('interface')
            
            # Test basic attributes
            self.assertEqual(config.component_label, "Interfaces")
            self.assertIsNotNone(config.model)
            self.assertIsNotNone(config.template_model)
            self.assertIsNotNone(config.comparison_class)
            
            # Test permissions
            self.assertIsInstance(config.permissions, (list, tuple))
            self.assertGreater(len(config.permissions), 0)
            
            # Test factory fields
            self.assertIsInstance(config.factory_fields, (list, tuple))
            self.assertIn('name', config.factory_fields)
            
        except ImportError:
            self.skipTest("Component registry not available")
            
    def test_powerport_config(self):
        """Test power port component configuration."""
        try:
            from netbox_component_synchronization.component_registry import get_component_config
            
            config = get_component_config('powerport')
            
            self.assertEqual(config.component_label, "Power ports")
            self.assertIsNotNone(config.model)
            self.assertIsNotNone(config.template_model)
            
        except ImportError:
            self.skipTest("Component registry not available")


class RegistryConsistencyTests(BaseUniversalTestCase):
    """Tests for component registry consistency across versions."""
    
    def test_all_configs_have_required_fields(self):
        """Test that all component configs have required fields."""
        try:
            from netbox_component_synchronization.component_registry import COMPONENT_REGISTRY
            
            required_fields = ['component_label', 'model', 'template_model', 'comparison_class']
            
            for component_type, config in COMPONENT_REGISTRY.items():
                with self.subTest(component_type=component_type):
                    for field in required_fields:
                        self.assertTrue(hasattr(config, field),
                                      f"{component_type} config missing {field}")
                        
        except ImportError:
            self.skipTest("Component registry not available")
            
    def test_factory_fields_consistency(self):
        """Test that factory fields are consistent."""
        try:
            from netbox_component_synchronization.component_registry import COMPONENT_REGISTRY
            
            for component_type, config in COMPONENT_REGISTRY.items():
                with self.subTest(component_type=component_type):
                    # All configs should have factory_fields
                    self.assertTrue(hasattr(config, 'factory_fields'))
                    self.assertIsInstance(config.factory_fields, (list, tuple))
                    
                    # All should include basic fields
                    fields = config.factory_fields
                    self.assertIn('name', fields, f"{component_type} missing 'name' field")
                    
        except ImportError:
            self.skipTest("Component registry not available")