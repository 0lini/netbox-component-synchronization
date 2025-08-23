"""
Utilities for debugging and troubleshooting auto-discovery.
"""
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


def debug_component_discovery():
    """
    Debug function to print detailed information about component discovery.
    Useful for troubleshooting issues.
    """
    try:
        from .auto_discovery import ComponentDiscovery
        from .discovery_config import config
        
        print("=== Component Auto-Discovery Debug Information ===")
        print(f"Auto-discovery enabled: {config.enabled}")
        print(f"Excluded types: {config.excluded_types}")
        print(f"Compare description: {config.compare_description}")
        print()
        
        if not config.enabled:
            print("Auto-discovery is disabled. No components will be discovered.")
            return
        
        discovery = ComponentDiscovery()
        
        try:
            dcim_app = discovery._get_dcim_app()
            print(f"DCIM app found: {dcim_app}")
            print(f"Available models: {len(dcim_app.get_models())}")
            print()
        except Exception as e:
            print(f"Error getting DCIM app: {e}")
            return
        
        print("=== Analyzing Models ===")
        component_models = []
        
        for model in dcim_app.get_models():
            model_name = model.__name__
            is_component = discovery._is_component_model(model)
            template_model = discovery._get_template_model(model) if is_component else None
            
            print(f"Model: {model_name:<20} Component: {is_component:<5} Template: {template_model.__name__ if template_model else 'None'}")
            
            if is_component and template_model:
                component_models.append((model, template_model))
        
        print(f"\nFound {len(component_models)} valid component models")
        print()
        
        print("=== Component Details ===")
        for model, template_model in component_models:
            component_name = model.__name__.lower()
            excluded = config.is_component_excluded(component_name)
            
            print(f"Component: {component_name}")
            print(f"  Model: {model.__name__}")
            print(f"  Template: {template_model.__name__}")
            print(f"  Excluded: {excluded}")
            
            if not excluded:
                try:
                    fields = discovery._analyze_model_fields(model)
                    print(f"  Fields: {', '.join(fields)}")
                    
                    permissions = discovery._generate_permissions(model)
                    print(f"  Permissions: {len(permissions)} permissions")
                    
                    label = discovery._generate_component_label(model)
                    print(f"  Label: {label}")
                    
                except Exception as e:
                    print(f"  Error analyzing: {e}")
            
            print()
        
        print("=== Final Discovery Results ===")
        try:
            discovered = discovery.discover_components()
            print(f"Successfully discovered {len(discovered)} components:")
            for name in sorted(discovered.keys()):
                print(f"  - {name}")
        except Exception as e:
            print(f"Error during discovery: {e}")
            
    except Exception as e:
        print(f"Debug function failed: {e}")


def validate_component_config(component_name: str) -> Dict[str, Any]:
    """
    Validate the configuration for a specific component.
    Returns a dictionary with validation results.
    """
    results = {
        'valid': False,
        'errors': [],
        'warnings': [],
        'info': {}
    }
    
    try:
        from .component_registry import get_component_config
        from .auto_discovery import get_discovered_component
        
        # Try to get the component config
        try:
            config = get_component_config(component_name)
            results['info']['has_config'] = True
            results['info']['component_label'] = config.component_label
            results['info']['field_count'] = len(config.factory_fields)
            results['info']['permission_count'] = len(config.permissions)
        except ValueError:
            results['errors'].append(f"Component '{component_name}' not found in registry")
            return results
        
        # Check if it was auto-discovered
        discovered = get_discovered_component(component_name)
        if discovered:
            results['info']['auto_discovered'] = True
            results['info']['model'] = discovered.model.__name__
            results['info']['template_model'] = discovered.template_model.__name__
        else:
            results['info']['auto_discovered'] = False
        
        # Validate model relationships
        if config.model and config.template_model:
            # Check if models exist and are related correctly
            model_name = config.model.__name__
            template_name = config.template_model.__name__
            
            if not template_name.endswith('Template'):
                results['warnings'].append(f"Template model '{template_name}' doesn't follow naming convention")
            
            expected_template = f"{model_name}Template"
            if template_name != expected_template:
                results['warnings'].append(f"Expected template model '{expected_template}', got '{template_name}'")
        
        # Validate factory fields
        if config.factory_fields:
            required_fields = ['id', 'name']
            for field in required_fields:
                if field not in config.factory_fields:
                    results['warnings'].append(f"Missing recommended field '{field}' in factory_fields")
        else:
            results['errors'].append("No factory fields defined")
        
        # Validate permissions
        if not config.permissions:
            results['warnings'].append("No permissions defined")
        else:
            expected_perms = ['view', 'add', 'change', 'delete']
            for perm_type in expected_perms:
                if not any(perm_type in perm for perm in config.permissions):
                    results['warnings'].append(f"Missing '{perm_type}' permission")
        
        results['valid'] = len(results['errors']) == 0
        
    except Exception as e:
        results['errors'].append(f"Validation failed: {e}")
    
    return results


def list_static_vs_discovered():
    """
    Compare static component definitions with auto-discovered ones.
    """
    try:
        from .component_registry import COMPONENT_REGISTRY, get_all_component_types
        from .auto_discovery import discover_components
        
        # Get static components (the original hardcoded ones)
        static_components = set(['interface', 'powerport', 'consoleport', 'consoleserverport', 
                                'poweroutlet', 'frontport', 'rearport', 'devicebay', 'modulebay'])
        
        # Get all current components
        all_components = set(get_all_component_types())
        
        # Get auto-discovered components
        try:
            discovered = discover_components()
            discovered_components = set(discovered.keys())
        except Exception as e:
            print(f"Error during auto-discovery: {e}")
            discovered_components = set()
        
        print("=== Static vs Auto-Discovered Components ===")
        print(f"Static components: {len(static_components)}")
        print(f"All registered components: {len(all_components)}")
        print(f"Auto-discovered components: {len(discovered_components)}")
        print()
        
        print("Static components:")
        for comp in sorted(static_components):
            status = "✓" if comp in all_components else "✗"
            print(f"  {status} {comp}")
        print()
        
        # New components (discovered but not static)
        new_components = discovered_components - static_components
        if new_components:
            print("New auto-discovered components:")
            for comp in sorted(new_components):
                print(f"  + {comp}")
        else:
            print("No new components discovered")
        
        print()
        
        # Missing components (static but not discovered)
        missing_components = static_components - discovered_components
        if missing_components:
            print("Static components not auto-discovered:")
            for comp in sorted(missing_components):
                print(f"  - {comp}")
        else:
            print("All static components were auto-discovered")
            
    except Exception as e:
        print(f"Comparison failed: {e}")