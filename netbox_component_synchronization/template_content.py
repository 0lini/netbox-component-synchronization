from netbox.plugins import PluginTemplateExtension
from dcim.models import Interface, InterfaceTemplate
from django.conf import settings

config = settings.PLUGINS_CONFIG.get("netbox_component_synchronization", {})


class DeviceComponentListExtension(PluginTemplateExtension):
    """Template extension for device component list views"""
    model = "dcim.device"
    
    def buttons(self):
        """Add bulk sync buttons to device component list views"""
        device = self.context.get('object')
        request = self.context.get('request')
        
        if not device or not request:
            return ""
        
        # Determine component type from URL
        component_type = self._get_component_type_from_url(request.path)
        if not component_type:
            return ""
            
        context = {
            'device': device,
            'component_type': component_type,
            'sync_enabled': True,
        }
        
        return self.render(
            "netbox_component_synchronization/bulk_sync_buttons.html",
            extra_context=context
        )
    
    def _get_component_type_from_url(self, path):
        """Extract component type from URL path"""
        component_mappings = {
            '/interfaces/': 'interfaces',
            '/power-ports/': 'power-ports', 
            '/console-ports/': 'console-ports',
            '/console-server-ports/': 'console-server-ports',
            '/power-outlets/': 'power-outlets',
            '/front-ports/': 'front-ports',
            '/rear-ports/': 'rear-ports',
            '/device-bays/': 'device-bays',
            '/module-bays/': 'module-bays',
        }
        
        for url_pattern, component_type in component_mappings.items():
            if url_pattern in path:
                return component_type
        return None

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


template_extensions = [DeviceComponentListExtension]
