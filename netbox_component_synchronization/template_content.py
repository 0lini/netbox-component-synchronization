from netbox.plugins import PluginTemplateExtension
from dcim.models import Interface, InterfaceTemplate
from django.conf import settings

config = settings.PLUGINS_CONFIG.get("netbox_component_synchronization", {})


class ComponentListExtension(PluginTemplateExtension):
    """Base template extension for component list views"""
    
    def get_sync_context(self, component_type):
        """Get sync context for the component type"""
        device = self.context.get('object')
        if not device:
            return {}
            
        return {
            'device': device,
            'component_type': component_type,
            'sync_enabled': True,
        }


class InterfaceListExtension(ComponentListExtension):
    model = "dcim.interface"
    
    def buttons(self):
        """Add bulk sync buttons to interface list view"""
        context = self.get_sync_context('interfaces')
        if not context.get('sync_enabled'):
            return ""
            
        return self.render(
            "netbox_component_synchronization/bulk_sync_buttons.html",
            extra_context=context
        )


class PowerPortListExtension(ComponentListExtension):
    model = "dcim.powerport"
    
    def buttons(self):
        """Add bulk sync buttons to power port list view"""
        context = self.get_sync_context('power-ports')
        if not context.get('sync_enabled'):
            return ""
            
        return self.render(
            "netbox_component_synchronization/bulk_sync_buttons.html",
            extra_context=context
        )


class ConsolePortListExtension(ComponentListExtension):
    model = "dcim.consoleport"
    
    def buttons(self):
        """Add bulk sync buttons to console port list view"""
        context = self.get_sync_context('console-ports')
        if not context.get('sync_enabled'):
            return ""
            
        return self.render(
            "netbox_component_synchronization/bulk_sync_buttons.html",
            extra_context=context
        )


class ConsoleServerPortListExtension(ComponentListExtension):
    model = "dcim.consoleserverport"
    
    def buttons(self):
        """Add bulk sync buttons to console server port list view"""
        context = self.get_sync_context('console-server-ports')
        if not context.get('sync_enabled'):
            return ""
            
        return self.render(
            "netbox_component_synchronization/bulk_sync_buttons.html",
            extra_context=context
        )


class PowerOutletListExtension(ComponentListExtension):
    model = "dcim.poweroutlet"
    
    def buttons(self):
        """Add bulk sync buttons to power outlet list view"""
        context = self.get_sync_context('power-outlets')
        if not context.get('sync_enabled'):
            return ""
            
        return self.render(
            "netbox_component_synchronization/bulk_sync_buttons.html",
            extra_context=context
        )


class FrontPortListExtension(ComponentListExtension):
    model = "dcim.frontport"
    
    def buttons(self):
        """Add bulk sync buttons to front port list view"""
        context = self.get_sync_context('front-ports')
        if not context.get('sync_enabled'):
            return ""
            
        return self.render(
            "netbox_component_synchronization/bulk_sync_buttons.html",
            extra_context=context
        )


class RearPortListExtension(ComponentListExtension):
    model = "dcim.rearport"
    
    def buttons(self):
        """Add bulk sync buttons to rear port list view"""
        context = self.get_sync_context('rear-ports')
        if not context.get('sync_enabled'):
            return ""
            
        return self.render(
            "netbox_component_synchronization/bulk_sync_buttons.html",
            extra_context=context
        )


class DeviceBayListExtension(ComponentListExtension):
    model = "dcim.devicebay"
    
    def buttons(self):
        """Add bulk sync buttons to device bay list view"""
        context = self.get_sync_context('device-bays')
        if not context.get('sync_enabled'):
            return ""
            
        return self.render(
            "netbox_component_synchronization/bulk_sync_buttons.html",
            extra_context=context
        )


class ModuleBayListExtension(ComponentListExtension):
    model = "dcim.modulebay"
    
    def buttons(self):
        """Add bulk sync buttons to module bay list view"""
        context = self.get_sync_context('module-bays')
        if not context.get('sync_enabled'):
            return ""
            
        return self.render(
            "netbox_component_synchronization/bulk_sync_buttons.html",
            extra_context=context
        )


class DeviceViewExtension(PluginTemplateExtension):
    model = "dcim.device"
    models = [model]

    def right_page(self):
        """Implements a panel with the number of interfaces on the right side of the page"""
        obj = self.context["object"]
        interfaces = Interface.objects.filter(device=obj)
        real_interfaces = interfaces.exclude(type__in=["virtual", "lag"])
        interface_templates = InterfaceTemplate.objects.filter(
            device_type=obj.device_type
        )

        return self.render(
            "netbox_component_synchronization/number_of_interfaces_panel.html",
            extra_context={
                "interfaces": interfaces,
                "real_interfaces": real_interfaces,
                "interface_templates": interface_templates,
            },
        )


template_extensions = [
    DeviceViewExtension,
    InterfaceListExtension,
    PowerPortListExtension,
    ConsolePortListExtension,
    ConsoleServerPortListExtension,
    PowerOutletListExtension,
    FrontPortListExtension,
    RearPortListExtension,
    DeviceBayListExtension,
    ModuleBayListExtension,
]
