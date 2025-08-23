"""
Auto-discovery module for NetBox component types.
This module automatically detects available component types from NetBox
and generates the necessary configuration for synchronization.
"""
import inspect
import logging
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Type, Any
from django.db import models
from django.apps import apps

from .discovery_config import config

logger = logging.getLogger(__name__)


@dataclass
class DiscoveredComponent:
    """Represents a discovered component type with its metadata"""
    name: str
    model: Type[models.Model]
    template_model: Optional[Type[models.Model]]
    component_label: str
    factory_fields: Tuple[str, ...]
    permissions: Tuple[str, ...]
    special_fields: Optional[Dict[str, Any]] = None
    custom_queryset_filter: Optional[str] = None


class ComponentDiscovery:
    """
    Discovers and analyzes NetBox component types automatically.
    """
    
    # Known component relationships - model name to template model name mapping
    COMPONENT_TEMPLATE_MAPPING = {
        'Interface': 'InterfaceTemplate',
        'PowerPort': 'PowerPortTemplate', 
        'ConsolePort': 'ConsolePortTemplate',
        'ConsoleServerPort': 'ConsoleServerPortTemplate',
        'PowerOutlet': 'PowerOutletTemplate',
        'FrontPort': 'FrontPortTemplate',
        'RearPort': 'RearPortTemplate',
        'DeviceBay': 'DeviceBayTemplate',
        'ModuleBay': 'ModuleBayTemplate',
    }
    
    # Common fields that typically exist on component models
    COMMON_COMPONENT_FIELDS = [
        'id', 'name', 'label', 'description'
    ]
    
    # Fields to typically exclude from factory
    EXCLUDED_FIELDS = [
        'created', 'last_updated', 'custom_field_data', 'tags',
        'device', 'device_type', 'module', '_cable_peer', 'cable',
        'link_peers', 'connected_endpoints', 'mark_connected'
    ]
    
    # Maximum number of components to discover (safety limit)
    MAX_COMPONENTS = 50
    
    def __init__(self):
        self.dcim_app = None
        self._discovered_components = {}
        self._discovery_in_progress = False
        
    def _get_dcim_app(self):
        """Get the dcim app instance"""
        if self.dcim_app is None:
            try:
                self.dcim_app = apps.get_app_config('dcim')
            except LookupError:
                raise RuntimeError("DCIM app not found. This plugin requires NetBox.")
        return self.dcim_app
    
    def _is_component_model(self, model: Type[models.Model]) -> bool:
        """
        Determine if a model represents a device component.
        
        A component model should:
        1. Have a foreign key to Device
        2. Have a corresponding template model
        3. Not be a template model itself
        """
        if model.__name__.endswith('Template'):
            return False
            
        # Check if it has a device foreign key
        for field in model._meta.get_fields():
            if (hasattr(field, 'related_model') and 
                field.related_model and 
                field.related_model.__name__ == 'Device'):
                return True
        return False
    
    def _get_template_model(self, component_model: Type[models.Model]) -> Optional[Type[models.Model]]:
        """Get the corresponding template model for a component model"""
        component_name = component_model.__name__
        template_name = self.COMPONENT_TEMPLATE_MAPPING.get(component_name)
        
        if not template_name:
            return None
            
        try:
            dcim_app = self._get_dcim_app()
            return dcim_app.get_model(template_name)
        except LookupError:
            return None
    
    def _analyze_model_fields(self, model: Type[models.Model]) -> Tuple[str, ...]:
        """
        Analyze a model and determine which fields should be included in the factory.
        """
        fields = []
        
        for field in model._meta.get_fields():
            if field.name in self.EXCLUDED_FIELDS:
                continue
                
            # Include fields that are not reverse foreign keys or many-to-many
            if not (field.one_to_many or field.many_to_many):
                # Include basic fields and foreign keys
                if (hasattr(field, 'get_internal_type') and 
                    field.get_internal_type() in [
                        'CharField', 'TextField', 'IntegerField', 'BooleanField',
                        'PositiveIntegerField', 'ForeignKey', 'SmallIntegerField'
                    ]):
                    fields.append(field.name)
        
        # Always ensure common fields are included if they exist
        for common_field in self.COMMON_COMPONENT_FIELDS:
            if (hasattr(model, common_field) and 
                common_field not in fields and 
                common_field not in self.EXCLUDED_FIELDS):
                fields.append(common_field)
        
        return tuple(sorted(fields))
    
    def _generate_permissions(self, model: Type[models.Model]) -> Tuple[str, ...]:
        """Generate the permissions tuple for a component model"""
        app_label = model._meta.app_label
        model_name = model._meta.model_name
        
        return (
            f"{app_label}.view_{model_name}",
            f"{app_label}.add_{model_name}",
            f"{app_label}.change_{model_name}",
            f"{app_label}.delete_{model_name}",
        )
    
    def _generate_special_fields(self, model: Type[models.Model]) -> Optional[Dict[str, Any]]:
        """Generate special fields configuration for a model"""
        special_fields = {}
        
        # Check if model has a get_type_display method (common for choice fields)
        if hasattr(model, 'get_type_display'):
            special_fields['type_display'] = lambda i: i.get_type_display()
        
        # Add special handling for PowerOutlet power_port_name
        if model.__name__ == 'PowerOutlet':
            def get_power_port_name(instance, is_template: bool) -> str:
                if instance.power_port_id is None:
                    return ""
                try:
                    if is_template:
                        from dcim.models import PowerPortTemplate
                        return PowerPortTemplate.objects.get(id=instance.power_port_id).name
                    else:
                        from dcim.models import PowerPort
                        return PowerPort.objects.get(id=instance.power_port_id).name
                except Exception:
                    return ""
            special_fields['power_port_name'] = get_power_port_name
        
        return special_fields if special_fields else None
    
    def _generate_component_label(self, model: Type[models.Model]) -> str:
        """Generate a human-readable label for the component"""
        name = model.__name__
        
        # Convert CamelCase to space-separated words
        import re
        # Insert space before capital letters (except first one)
        spaced = re.sub(r'(?<!^)(?=[A-Z])', ' ', name)
        
        # Handle common cases
        label_map = {
            'Interface': 'Interfaces',
            'Power Port': 'Power ports',
            'Console Port': 'Console ports', 
            'Console Server Port': 'Console server ports',
            'Power Outlet': 'Power outlets',
            'Front Port': 'Front ports',
            'Rear Port': 'Rear ports',
            'Device Bay': 'Device bays',
            'Module Bay': 'Module bays',
        }
        
        return label_map.get(spaced, spaced.lower() + 's')
    
    def discover_components(self) -> Dict[str, DiscoveredComponent]:
        """
        Discover all available component types from NetBox.
        
        Returns:
            Dictionary mapping component type names to DiscoveredComponent objects
        """
        if self._discovered_components:
            return self._discovered_components
        
        if self._discovery_in_progress:
            logger.warning("Discovery already in progress, returning empty dict to prevent recursion")
            return {}
            
        if not config.enabled:
            logger.info("Auto-discovery is disabled in configuration")
            return {}
            
        self._discovery_in_progress = True
        
        try:
            dcim_app = self._get_dcim_app()
        except RuntimeError as e:
            logger.error(f"Failed to get DCIM app: {e}")
            self._discovery_in_progress = False
            return {}
            
        discovered = {}
        processed_count = 0
        
        # Iterate through all models in the dcim app
        for model in dcim_app.get_models():
            if processed_count >= self.MAX_COMPONENTS:
                logger.warning(f"Reached maximum component limit ({self.MAX_COMPONENTS}), stopping discovery")
                break
                
            try:
                if self._is_component_model(model):
                    component_name = model.__name__.lower()
                    
                    # Check if component should be excluded
                    if config.is_component_excluded(component_name):
                        logger.debug(f"Excluding component '{component_name}' per configuration")
                        continue
                    
                    template_model = self._get_template_model(model)
                    
                    # Skip if no template model found
                    if not template_model:
                        logger.debug(f"No template model found for {model.__name__}, skipping")
                        continue
                    
                    factory_fields = self._analyze_model_fields(model)
                    permissions = self._generate_permissions(model)
                    component_label = self._generate_component_label(model)
                    special_fields = self._generate_special_fields(model)
                    
                    # Set custom queryset filter for interface
                    custom_filter = 'exclude_interface_type_list' if component_name == 'interface' else None
                    
                    discovered[component_name] = DiscoveredComponent(
                        name=component_name,
                        model=model,
                        template_model=template_model,
                        component_label=component_label,
                        factory_fields=factory_fields,
                        permissions=permissions,
                        special_fields=special_fields,
                        custom_queryset_filter=custom_filter
                    )
                    
                    logger.debug(f"Discovered component: {component_name}")
                    processed_count += 1
                    
            except Exception as e:
                logger.warning(f"Error processing model {model.__name__}: {e}")
                continue
        
        self._discovered_components = discovered
        self._discovery_in_progress = False
        logger.info(f"Auto-discovery completed: found {len(discovered)} component types")
        return discovered
    
    def get_component_names(self) -> List[str]:
        """Get list of all discovered component names"""
        return list(self.discover_components().keys())
    
    def get_component(self, component_name: str) -> Optional[DiscoveredComponent]:
        """Get a specific discovered component by name"""
        return self.discover_components().get(component_name)


# Global discovery instance
_discovery = ComponentDiscovery()


def discover_components() -> Dict[str, DiscoveredComponent]:
    """Convenience function to discover components"""
    return _discovery.discover_components()


def get_discovered_component(component_name: str) -> Optional[DiscoveredComponent]:
    """Convenience function to get a specific discovered component"""
    return _discovery.get_component(component_name)


def get_component_names() -> List[str]:
    """Convenience function to get component names"""
    return _discovery.get_component_names()