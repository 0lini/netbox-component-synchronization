"""
Component registry to reduce code duplication and complexity in views.
This registry defines all component types and their configurations in one place.
"""
from dataclasses import dataclass
from typing import Dict, Callable, Any, Optional
from dcim.models import (
    Device,
    Interface,
    InterfaceTemplate,
    PowerPort,
    PowerPortTemplate,
    ConsolePort,
    ConsolePortTemplate,
    ConsoleServerPort,
    ConsoleServerPortTemplate,
    DeviceBay,
    DeviceBayTemplate,
    FrontPort,
    FrontPortTemplate,
    PowerOutlet,
    PowerOutletTemplate,
    RearPort,
    RearPortTemplate,
    ModuleBay,
    ModuleBayTemplate,
)
from .comparison import (
    FrontPortComparison,
    PowerPortComparison,
    PowerOutletComparison,
    InterfaceComparison,
    ConsolePortComparison,
    ConsoleServerPortComparison,
    DeviceBayComparison,
    RearPortComparison,
    ModuleBayComparison,
)


@dataclass
class ComponentConfig:
    """Configuration for a component type"""
    component_label: str
    model: type
    template_model: type
    comparison_class: type
    permissions: tuple
    factory_fields: tuple
    special_fields: Optional[Dict[str, Any]] = None
    custom_queryset_filter: Optional[str] = None


def get_power_port_name(instance, is_template: bool) -> str:
    """Helper function to get power port name for PowerOutlet"""
    if instance.power_port_id is None:
        return ""
    try:
        if is_template:
            return PowerPortTemplate.objects.get(id=instance.power_port_id).name
        else:
            return PowerPort.objects.get(id=instance.power_port_id).name
    except Exception:
        return ""


# Component registry - single source of truth for all component configurations
COMPONENT_REGISTRY: Dict[str, ComponentConfig] = {
    'interface': ComponentConfig(
        component_label="Interfaces",
        model=Interface,
        template_model=InterfaceTemplate,
        comparison_class=InterfaceComparison,
        permissions=(
            "dcim.view_interface",
            "dcim.add_interface", 
            "dcim.change_interface",
            "dcim.delete_interface",
        ),
        factory_fields=(
            'id', 'name', 'label', 'description', 'type', 'enabled',
            'mgmt_only', 'poe_mode', 'poe_type', 'rf_role'
        ),
        special_fields={
            'type_display': lambda i: i.get_type_display(),
        },
        custom_queryset_filter='exclude_interface_type_list'
    ),
    
    'powerport': ComponentConfig(
        component_label="Power ports",
        model=PowerPort,
        template_model=PowerPortTemplate,
        comparison_class=PowerPortComparison,
        permissions=(
            "dcim.view_powerport",
            "dcim.add_powerport",
            "dcim.change_powerport", 
            "dcim.delete_powerport",
        ),
        factory_fields=(
            'id', 'name', 'label', 'description', 'type', 'maximum_draw', 'allocated_draw'
        ),
        special_fields={
            'type_display': lambda i: i.get_type_display(),
        }
    ),
    
    'consoleport': ComponentConfig(
        component_label="Console ports",
        model=ConsolePort,
        template_model=ConsolePortTemplate,
        comparison_class=ConsolePortComparison,
        permissions=(
            "dcim.view_consoleport",
            "dcim.add_consoleport",
            "dcim.change_consoleport",
            "dcim.delete_consoleport",
        ),
        factory_fields=(
            'id', 'name', 'label', 'description', 'type'
        ),
        special_fields={
            'type_display': lambda i: i.get_type_display(),
        }
    ),
    
    'consoleserverport': ComponentConfig(
        component_label="Console server ports", 
        model=ConsoleServerPort,
        template_model=ConsoleServerPortTemplate,
        comparison_class=ConsoleServerPortComparison,
        permissions=(
            "dcim.view_consoleserverport",
            "dcim.add_consoleserverport",
            "dcim.change_consoleserverport",
            "dcim.delete_consoleserverport",
        ),
        factory_fields=(
            'id', 'name', 'label', 'description', 'type'
        ),
        special_fields={
            'type_display': lambda i: i.get_type_display(),
        }
    ),
    
    'poweroutlet': ComponentConfig(
        component_label="Power outlets",
        model=PowerOutlet,
        template_model=PowerOutletTemplate,
        comparison_class=PowerOutletComparison,
        permissions=(
            "dcim.view_poweroutlet",
            "dcim.add_poweroutlet",
            "dcim.change_poweroutlet",
            "dcim.delete_poweroutlet",
        ),
        factory_fields=(
            'id', 'name', 'label', 'description', 'type', 'feed_leg'
        ),
        special_fields={
            'type_display': lambda i: i.get_type_display(),
            'power_port_name': get_power_port_name,
        }
    ),
    
    'frontport': ComponentConfig(
        component_label="Front ports",
        model=FrontPort,
        template_model=FrontPortTemplate,
        comparison_class=FrontPortComparison,
        permissions=(
            "dcim.view_frontport",
            "dcim.add_frontport",
            "dcim.change_frontport",
            "dcim.delete_frontport",
        ),
        factory_fields=(
            'id', 'name', 'label', 'description', 'type', 'color', 'rear_port_position'
        ),
        special_fields={
            'type_display': lambda i: i.get_type_display(),
        }
    ),
    
    'rearport': ComponentConfig(
        component_label="Rear ports",
        model=RearPort,
        template_model=RearPortTemplate,
        comparison_class=RearPortComparison,
        permissions=(
            "dcim.view_rearport",
            "dcim.add_rearport",
            "dcim.change_rearport",
            "dcim.delete_rearport",
        ),
        factory_fields=(
            'id', 'name', 'label', 'description', 'type', 'color', 'positions'
        ),
        special_fields={
            'type_display': lambda i: i.get_type_display(),
        }
    ),
    
    'devicebay': ComponentConfig(
        component_label="Device bays",
        model=DeviceBay,
        template_model=DeviceBayTemplate,
        comparison_class=DeviceBayComparison,
        permissions=(
            "dcim.view_devicebay",
            "dcim.add_devicebay",
            "dcim.change_devicebay",
            "dcim.delete_devicebay",
        ),
        factory_fields=(
            'id', 'name', 'label', 'description'
        ),
    ),
    
    'modulebay': ComponentConfig(
        component_label="Module bays",
        model=ModuleBay,
        template_model=ModuleBayTemplate,
        comparison_class=ModuleBayComparison,
        permissions=(
            "dcim.view_modulebay",
            "dcim.add_modulebay",
            "dcim.change_modulebay",
            "dcim.delete_modulebay",
        ),
        factory_fields=(
            'id', 'name', 'label', 'description', 'position'
        ),
    ),
}


def get_component_config(component_type: str) -> ComponentConfig:
    """Get component configuration by type"""
    if component_type not in COMPONENT_REGISTRY:
        raise ValueError(f"Unknown component type: {component_type}")
    return COMPONENT_REGISTRY[component_type]


def create_component_factory(config: ComponentConfig) -> Callable:
    """Create a factory function for a component type based on its configuration"""
    def factory(instance, is_template: bool = False):
        # Build arguments dictionary from factory fields
        args = {}
        for field in config.factory_fields:
            args[field] = getattr(instance, field, None)
        
        # Add special fields if any
        if config.special_fields:
            for field_name, field_func in config.special_fields.items():
                if callable(field_func):
                    if field_name == 'power_port_name':
                        # Special case for power_port_name that needs is_template parameter
                        args[field_name] = field_func(instance, is_template)
                    else:
                        args[field_name] = field_func(instance)
                else:
                    args[field_name] = field_func
        
        # Add is_template parameter
        args['is_template'] = is_template
        
        return config.comparison_class(**args)
    
    return factory


def get_component_queryset(device: Device, component_type: str):
    """Get the component queryset for a device and component type"""
    config = get_component_config(component_type)
    
    if component_type == 'interface':
        qs = device.vc_interfaces().exclude(module_id__isnull=False)
        # Apply interface type exclusion filter
        from django.conf import settings
        plugin_config = settings.PLUGINS_CONFIG.get("netbox_component_synchronization", {})
        exclude_types = plugin_config.get("exclude_interface_type_list", [])
        if exclude_types:
            qs = qs.exclude(type__in=exclude_types)
        return qs
    elif component_type == 'modulebay':
        return getattr(device, f"{component_type}s").all().filter(level=0)
    else:
        return getattr(device, f"{component_type}s").all().exclude(module_id__isnull=False)