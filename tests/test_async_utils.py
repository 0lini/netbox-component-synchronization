"""
Universal tests for async utilities functionality.

These tests work across different NetBox versions and environments.
"""
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from tests.base import (
    BaseUniversalTestCase, 
    AsyncUtilsTestMixin,
    ValidationTestMixin
)


class AsyncUtilsTests(BaseUniversalTestCase, AsyncUtilsTestMixin, ValidationTestMixin):
    """Universal tests for async utilities."""
    
    def test_async_utils_import(self):
        """Test that async_utils module can be imported."""
        self.assert_module_importable('async_utils')
        
    def test_parse_form_ids_function(self):
        """Test parse_form_ids function."""
        try:
            from netbox_component_synchronization.async_utils import parse_form_ids
            
            # Test with valid data
            result = parse_form_ids(['1', '2', '3'])
            self.assertEqual(result, [1, 2, 3])
            
            # Test with mixed valid/invalid data
            result = parse_form_ids(['1', 'invalid', '3'])
            self.assertEqual(result, [1, 3])
            
            # Test with empty list
            result = parse_form_ids([])
            self.assertEqual(result, [])
            
        except ImportError:
            self.skipTest("Async utils not available")
            
    def test_filter_valid_ids_function(self):
        """Test filter_valid_ids function."""
        try:
            from netbox_component_synchronization.async_utils import filter_valid_ids
            
            parsed_ids = [1, 2, 3, 4]
            valid_ids = [1, 3, 5]
            
            result = filter_valid_ids(parsed_ids, valid_ids)
            self.assertEqual(result, [1, 3])
            
        except ImportError:
            self.skipTest("Async utils not available")
            
    def test_create_success_message_function(self):
        """Test create_success_message function."""
        try:
            from netbox_component_synchronization.async_utils import create_success_message
            
            stats = {'created': 2, 'updated': 1, 'deleted': 3, 'fixed': 0}
            message = create_success_message(stats, 'interface')
            
            self.assertIsInstance(message, str)
            self.assertIn('interface', message.lower())
            self.assertIn('2', message)  # created count
            self.assertIn('1', message)  # updated count
            self.assertIn('3', message)  # deleted count
            
        except ImportError:
            self.skipTest("Async utils not available")


class ComponentProcessorTests(BaseUniversalTestCase, AsyncUtilsTestMixin):
    """Universal tests for ComponentProcessor class."""
    
    def setUp(self):
        super().setUp()
        self.processor = self.create_mock_component_processor()
        
    def test_component_processor_creation(self):
        """Test ComponentProcessor can be created."""
        try:
            from netbox_component_synchronization.async_utils import ComponentProcessor
            
            mock_device = Mock()
            mock_object_type = Mock()
            mock_template_type = Mock()
            
            processor = ComponentProcessor(mock_device, mock_object_type, mock_template_type, 'test')
            
            self.assertEqual(processor.device, mock_device)
            self.assertEqual(processor.object_type, mock_object_type)
            self.assertEqual(processor.object_template_type, mock_template_type)
            self.assertEqual(processor.component_type, 'test')
            
        except ImportError:
            self.skipTest("ComponentProcessor not available")
            
    def test_component_processor_stats_initialization(self):
        """Test ComponentProcessor initializes stats correctly."""
        expected_stats = {'created': 0, 'updated': 0, 'deleted': 0, 'fixed': 0}
        
        if hasattr(self.processor, 'stats'):
            for key, value in expected_stats.items():
                self.assertIn(key, self.processor.stats)
                self.assertEqual(self.processor.stats[key], value)
                
    @patch('netbox_component_synchronization.async_utils.sync_to_async')
    def test_process_deletions_method(self, mock_sync_to_async):
        """Test process_deletions method."""
        try:
            from netbox_component_synchronization.async_utils import ComponentProcessor
            
            # Create a real processor for testing
            mock_device = Mock()
            mock_object_type = Mock()
            mock_template_type = Mock()
            
            processor = ComponentProcessor(mock_device, mock_object_type, mock_template_type, 'test')
            
            # Mock the deletion operation
            mock_queryset = Mock()
            mock_queryset.delete.return_value = (5, {})
            mock_object_type.objects.filter.return_value = mock_queryset
            
            # Mock sync_to_async
            async def mock_delete():
                return (5, {})
            mock_sync_to_async.return_value = mock_delete
            
            # Test the method
            async def run_test():
                result = await processor.process_deletions([1, 2, 3])
                return result
                
            # Run the async test
            result = asyncio.run(run_test())
            self.assertEqual(result, 5)
            
        except ImportError:
            self.skipTest("ComponentProcessor not available")


class UtilityFunctionTests(BaseUniversalTestCase):
    """Tests for standalone utility functions."""
    
    def test_parse_and_filter_ids_integration(self):
        """Test integration of parsing and filtering functions."""
        try:
            from netbox_component_synchronization.async_utils import parse_form_ids, filter_valid_ids
            
            raw_ids = ['1', '2', 'invalid', '4', '5']
            valid_ids = [1, 2, 3, 4]
            
            parsed = parse_form_ids(raw_ids)
            filtered = filter_valid_ids(parsed, valid_ids)
            
            expected = [1, 2, 4]  # 3 is not in raw_ids, 5 is not in valid_ids
            self.assertEqual(filtered, expected)
            
        except ImportError:
            self.skipTest("Async utility functions not available")
            
    def test_edge_cases(self):
        """Test edge cases for utility functions."""
        try:
            from netbox_component_synchronization.async_utils import parse_form_ids, filter_valid_ids
            
            # Test with None
            self.assertEqual(parse_form_ids(None), [])
            
            # Test with empty strings
            result = parse_form_ids(['', '1', ''])
            self.assertEqual(result, [1])
            
            # Test filter with empty lists
            self.assertEqual(filter_valid_ids([], [1, 2, 3]), [])
            self.assertEqual(filter_valid_ids([1, 2, 3], []), [])
            
        except ImportError:
            self.skipTest("Async utility functions not available")


class AsyncPatternTests(BaseUniversalTestCase):
    """Tests for async patterns and best practices."""
    
    def test_async_function_signatures(self):
        """Test that async functions have correct signatures."""
        try:
            from netbox_component_synchronization.async_utils import ComponentProcessor
            import inspect
            
            processor_class = ComponentProcessor
            
            # Check that expected methods exist and are async
            expected_async_methods = [
                'process_additions',
                'process_deletions', 
                'process_name_fixes'
            ]
            
            for method_name in expected_async_methods:
                if hasattr(processor_class, method_name):
                    method = getattr(processor_class, method_name)
                    self.assertTrue(inspect.iscoroutinefunction(method),
                                  f"{method_name} should be async")
                                  
        except ImportError:
            self.skipTest("ComponentProcessor not available")