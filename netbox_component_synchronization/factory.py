"""
Component factory system for creating comparison objects and managing component types.
"""

from dataclasses import dataclass, field
from typing import Type, Callable, Dict, Any, Optional
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
class ComponentConfiguration:
    """Configuration for a component type."""
    model: Type
    template_model: Type
    comparison_class: Type
    component_label: str
    permissions: tuple
    extra_attributes: tuple = field(default_factory=tuple)
    custom_factory: Optional[Callable] = None
    custom_queryset_filter: Optional[Callable] = None
    url_name: str = ""
    
    def __post_init__(self):
        if not self.url_name:
            # Generate URL name from model name
            self.url_name = f"{self.model.__name__.lower()}_comparison"


class ComponentFactory:
    """Factory for creating component comparison objects."""
    
    def __init__(self):
        self._configurations: Dict[str, ComponentConfiguration] = {}
        self._register_default_components()
    
    def register_component(self, name: str, config: ComponentConfiguration):
        """Register a component configuration."""
        self._configurations[name] = config
    
    def get_configuration(self, name: str) -> ComponentConfiguration:
        """Get component configuration by name."""
        return self._configurations[name]
    
    def get_all_configurations(self) -> Dict[str, ComponentConfiguration]:
        """Get all registered component configurations."""
        return self._configurations.copy()
    
    def create_comparison_object(self, name: str, instance, is_template: bool = False):
        """Create a comparison object for the given component type."""
        config = self._configurations[name]
        
        if config.custom_factory:
            return config.custom_factory(instance, is_template=is_template)
        
        return self._default_factory(config, instance, is_template)
    
    def _default_factory(self, config: ComponentConfiguration, instance, is_template: bool = False):
        """Default factory method for creating comparison objects."""
        # Common attributes for all components
        base_args = [
            instance.id,
            instance.name,
            instance.label,
            instance.description,
        ]
        
        # Add type and type_display for typed components
        comparison_class = config.comparison_class
        if hasattr(comparison_class, 'type'):
            base_args.extend([
                instance.type,
                instance.get_type_display(),
            ])
        
        # Add extra attributes specific to this component type
        extra_values = []
        for attr in config.extra_attributes:
            if callable(attr):
                # Handle computed attributes
                extra_values.append(attr(instance, is_template))
            else:
                # Handle simple attribute names
                extra_values.append(getattr(instance, attr, ""))
        
        # Create the comparison object
        return comparison_class(*base_args, *extra_values, is_template=is_template)
    
    def _register_default_components(self):
        """Register all default component types."""
        
        # Interface
        self.register_component("interface", ComponentConfiguration(
            model=Interface,
            template_model=InterfaceTemplate,
            comparison_class=InterfaceComparison,
            component_label="Interfaces",
            permissions=(
                "dcim.view_interface",
                "dcim.add_interface",
                "dcim.change_interface",
                "dcim.delete_interface",
            ),
            extra_attributes=("enabled", "mgmt_only", "poe_mode", "poe_type", "rf_role"),
        ))
        
        # Power Port
        self.register_component("powerport", ComponentConfiguration(
            model=PowerPort,
            template_model=PowerPortTemplate,
            comparison_class=PowerPortComparison,
            component_label="Power ports",
            permissions=(
                "dcim.view_powerport",
                "dcim.add_powerport",
                "dcim.change_powerport",
                "dcim.delete_powerport",
            ),
            extra_attributes=("maximum_draw", "allocated_draw"),
        ))
        
        # Console Port
        self.register_component("consoleport", ComponentConfiguration(
            model=ConsolePort,
            template_model=ConsolePortTemplate,
            comparison_class=ConsolePortComparison,
            component_label="Console ports",
            permissions=(
                "dcim.view_consoleport",
                "dcim.add_consoleport",
                "dcim.change_consoleport",
                "dcim.delete_consoleport",
            ),
        ))
        
        # Console Server Port
        self.register_component("consoleserverport", ComponentConfiguration(
            model=ConsoleServerPort,
            template_model=ConsoleServerPortTemplate,
            comparison_class=ConsoleServerPortComparison,
            component_label="Console server ports",
            permissions=(
                "dcim.view_consoleserverport",
                "dcim.add_consoleserverport",
                "dcim.change_consoleserverport",
                "dcim.delete_consoleserverport",
            ),
        ))
        
        # Power Outlet (needs custom factory due to power_port_name logic)
        def power_outlet_factory(instance, is_template=False):
            power_port_name = ""
            if instance.power_port_id is not None:
                try:
                    if is_template:
                        power_port_name = PowerPortTemplate.objects.get(id=instance.power_port_id).name
                    else:
                        power_port_name = PowerPort.objects.get(id=instance.power_port_id).name
                except Exception:
                    power_port_name = ""
            
            return PowerOutletComparison(
                instance.id,
                instance.name,
                instance.label,
                instance.description,
                instance.type,
                instance.get_type_display(),
                power_port_name=power_port_name,
                feed_leg=instance.feed_leg,
                is_template=is_template,
            )
        
        self.register_component("poweroutlet", ComponentConfiguration(
            model=PowerOutlet,
            template_model=PowerOutletTemplate,
            comparison_class=PowerOutletComparison,
            component_label="Power outlets",
            permissions=(
                "dcim.view_poweroutlet",
                "dcim.add_poweroutlet",
                "dcim.change_poweroutlet",
                "dcim.delete_poweroutlet",
            ),
            custom_factory=power_outlet_factory,
        ))
        
        # Front Port
        self.register_component("frontport", ComponentConfiguration(
            model=FrontPort,
            template_model=FrontPortTemplate,
            comparison_class=FrontPortComparison,
            component_label="Front ports",
            permissions=(
                "dcim.view_frontport",
                "dcim.add_frontport",
                "dcim.change_frontport",
                "dcim.delete_frontport",
            ),
            extra_attributes=("color", "rear_port_position"),
        ))
        
        # Rear Port
        self.register_component("rearport", ComponentConfiguration(
            model=RearPort,
            template_model=RearPortTemplate,
            comparison_class=RearPortComparison,
            component_label="Rear ports",
            permissions=(
                "dcim.view_rearport",
                "dcim.add_rearport",
                "dcim.change_rearport",
                "dcim.delete_rearport",
            ),
            extra_attributes=("color", "positions"),
        ))
        
        # Device Bay
        self.register_component("devicebay", ComponentConfiguration(
            model=DeviceBay,
            template_model=DeviceBayTemplate,
            comparison_class=DeviceBayComparison,
            component_label="Device bays",
            permissions=(
                "dcim.view_devicebay",
                "dcim.add_devicebay",
                "dcim.change_devicebay",
                "dcim.delete_devicebay",
            ),
        ))
        
        # Module Bay (needs custom queryset filter)
        def module_bay_queryset_filter(device: Device):
            return device.modulebays.all().filter(level=0)
        
        self.register_component("modulebay", ComponentConfiguration(
            model=ModuleBay,
            template_model=ModuleBayTemplate,
            comparison_class=ModuleBayComparison,
            component_label="Module bays",
            permissions=(
                "dcim.view_modulebay",
                "dcim.add_modulebay",
                "dcim.change_modulebay",
                "dcim.delete_modulebay",
            ),
            extra_attributes=("position",),
            custom_queryset_filter=module_bay_queryset_filter,
        ))


# Global factory instance
component_factory = ComponentFactory()