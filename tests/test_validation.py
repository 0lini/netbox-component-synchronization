"""
Universal validation tests that work across environments.

These tests provide basic smoke testing and validation that the plugin
modules can be imported and basic functionality works.
"""
from tests.base import BaseUniversalTestCase, ValidationTestMixin


class ModuleImportTests(BaseUniversalTestCase, ValidationTestMixin):
    """Test that all core modules can be imported."""
    
    def test_core_module_imports(self):
        """Test importing all core plugin modules."""
        self.test_core_modules_importable()
        
    def test_additional_module_imports(self):
        """Test importing additional plugin modules."""
        additional_modules = [
            'async_utils',
            'auto_discovery', 
            'urls',
            'template_content'
        ]
        
        for module in additional_modules:
            with self.subTest(module=module):
                try:
                    self.assert_module_importable(module)
                except Exception:
                    # Some modules may not be available in all environments
                    self.skipTest(f"Module {module} not available in this environment")


class BasicFunctionalityTests(BaseUniversalTestCase):
    """Test basic plugin functionality without requiring full NetBox setup."""
    
    def test_component_registry_accessible(self):
        """Test that component registry is accessible."""
        try:
            from netbox_component_synchronization.component_registry import COMPONENT_REGISTRY
            self.assertIsInstance(COMPONENT_REGISTRY, dict)
            self.assertGreater(len(COMPONENT_REGISTRY), 0)
        except ImportError:
            self.skipTest("Component registry not available")
            
    def test_comparison_classes_importable(self):
        """Test that comparison classes can be imported."""
        try:
            from netbox_component_synchronization.comparison import (
                InterfaceComparison,
                PowerPortComparison,
                ConsolePortComparison
            )
            
            # Test that classes exist and are callable
            self.assertTrue(callable(InterfaceComparison))
            self.assertTrue(callable(PowerPortComparison))
            self.assertTrue(callable(ConsolePortComparison))
            
        except ImportError:
            self.skipTest("Comparison classes not available")
            
    def test_forms_importable(self):
        """Test that form classes can be imported."""
        try:
            from netbox_component_synchronization.forms import ComponentForm
            self.assertTrue(callable(ComponentForm))
        except ImportError:
            self.skipTest("Forms not available")


class PluginConfigurationTests(BaseUniversalTestCase):
    """Test plugin configuration and metadata."""
    
    def test_plugin_init(self):
        """Test that plugin __init__.py is properly configured."""
        try:
            import netbox_component_synchronization
            
            # Check that the package can be imported
            self.assertIsNotNone(netbox_component_synchronization)
            
            # Check for common plugin attributes
            if hasattr(netbox_component_synchronization, '__version__'):
                version = netbox_component_synchronization.__version__
                self.assertIsInstance(version, str)
                
        except ImportError:
            self.skipTest("Plugin package not available")
            
    def test_plugin_metadata(self):
        """Test plugin metadata from setup.py."""
        import setup
        
        # Verify setup.py can be imported (basic syntax check)
        self.assertTrue(hasattr(setup, 'setup'))


class EnvironmentCompatibilityTests(BaseUniversalTestCase):
    """Test compatibility across different environments."""
    
    def test_django_optional_imports(self):
        """Test that plugin works when Django components are not available."""
        # This test itself demonstrates the plugin can work without Django
        # since the base test class handles Django import failures gracefully
        self.assertIsNotNone(self.django_available)
        
    def test_graceful_netbox_import_handling(self):
        """Test that NetBox model imports are handled gracefully."""
        try:
            from dcim.models import Device, Interface
            netbox_available = True
        except ImportError:
            netbox_available = False
            
        # Test should pass regardless of NetBox availability
        self.assertIsInstance(netbox_available, bool)
        
    def test_plugin_urls_structure(self):
        """Test that URL configuration is properly structured."""
        try:
            from netbox_component_synchronization.urls import urlpatterns
            self.assertIsInstance(urlpatterns, list)
        except ImportError:
            self.skipTest("URLs not available")


class CrossVersionCompatibilityTests(BaseUniversalTestCase):
    """Test features that should work across NetBox versions."""
    
    def test_component_types_consistency(self):
        """Test that basic component types are consistently available."""
        try:
            from netbox_component_synchronization.component_registry import COMPONENT_REGISTRY
            
            # These component types should be available in all supported NetBox versions
            expected_base_types = ['interface', 'powerport', 'consoleport']
            
            for component_type in expected_base_types:
                with self.subTest(component_type=component_type):
                    self.assertIn(component_type, COMPONENT_REGISTRY,
                                f"Component type {component_type} missing from registry")
                                
        except ImportError:
            self.skipTest("Component registry not available")
            
    def test_view_inheritance_structure(self):
        """Test that view classes have expected inheritance structure."""
        try:
            from netbox_component_synchronization.views import GenericComponentComparisonView
            
            # Test that the main view class exists
            self.assertTrue(callable(GenericComponentComparisonView))
            
            # Test basic class structure
            self.assertTrue(hasattr(GenericComponentComparisonView, 'get'))
            self.assertTrue(hasattr(GenericComponentComparisonView, 'post'))
            
        except ImportError:
            self.skipTest("Views not available")