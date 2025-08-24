from django.shortcuts import get_object_or_404, redirect
from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.conf import settings
from django.http import HttpResponseBadRequest
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

from .utils import (
    handle_bulk_add_missing,
    handle_bulk_repair_out_of_sync,
    handle_bulk_remove_out_of_sync,
    handle_bulk_sync_all,
)

config = settings.PLUGINS_CONFIG["netbox_component_synchronization"]


# Mapping of component types to their models and templates
COMPONENT_MAPPINGS = {
    'interfaces': {
        'model': Interface,
        'template_model': InterfaceTemplate,
        'permissions': ('dcim.view_interface', 'dcim.add_interface', 'dcim.change_interface', 'dcim.delete_interface'),
        'component_label': 'Interfaces',
        'get_components_qs': lambda device: device.vc_interfaces().exclude(module_id__isnull=False).exclude(type__in=config["exclude_interface_type_list"]),
    },
    'power-ports': {
        'model': PowerPort,
        'template_model': PowerPortTemplate,
        'permissions': ('dcim.view_powerport', 'dcim.add_powerport', 'dcim.change_powerport', 'dcim.delete_powerport'),
        'component_label': 'Power ports',
        'get_components_qs': lambda device: device.powerports.all().exclude(module_id__isnull=False),
    },
    'console-ports': {
        'model': ConsolePort,
        'template_model': ConsolePortTemplate,
        'permissions': ('dcim.view_consoleport', 'dcim.add_consoleport', 'dcim.change_consoleport', 'dcim.delete_consoleport'),
        'component_label': 'Console ports',
        'get_components_qs': lambda device: device.consoleports.all().exclude(module_id__isnull=False),
    },
    'console-server-ports': {
        'model': ConsoleServerPort,
        'template_model': ConsoleServerPortTemplate,
        'permissions': ('dcim.view_consoleserverport', 'dcim.add_consoleserverport', 'dcim.change_consoleserverport', 'dcim.delete_consoleserverport'),
        'component_label': 'Console server ports',
        'get_components_qs': lambda device: device.consoleserverports.all().exclude(module_id__isnull=False),
    },
    'power-outlets': {
        'model': PowerOutlet,
        'template_model': PowerOutletTemplate,
        'permissions': ('dcim.view_poweroutlet', 'dcim.add_poweroutlet', 'dcim.change_poweroutlet', 'dcim.delete_poweroutlet'),
        'component_label': 'Power outlets',
        'get_components_qs': lambda device: device.poweroutlets.all().exclude(module_id__isnull=False),
    },
    'front-ports': {
        'model': FrontPort,
        'template_model': FrontPortTemplate,
        'permissions': ('dcim.view_frontport', 'dcim.add_frontport', 'dcim.change_frontport', 'dcim.delete_frontport'),
        'component_label': 'Front ports',
        'get_components_qs': lambda device: device.frontports.all().exclude(module_id__isnull=False),
    },
    'rear-ports': {
        'model': RearPort,
        'template_model': RearPortTemplate,
        'permissions': ('dcim.view_rearport', 'dcim.add_rearport', 'dcim.change_rearport', 'dcim.delete_rearport'),
        'component_label': 'Rear ports',
        'get_components_qs': lambda device: device.rearports.all().exclude(module_id__isnull=False),
    },
    'device-bays': {
        'model': DeviceBay,
        'template_model': DeviceBayTemplate,
        'permissions': ('dcim.view_devicebay', 'dcim.add_devicebay', 'dcim.change_devicebay', 'dcim.delete_devicebay'),
        'component_label': 'Device bays',
        'get_components_qs': lambda device: device.devicebays.all().exclude(module_id__isnull=False),
    },
    'module-bays': {
        'model': ModuleBay,
        'template_model': ModuleBayTemplate,
        'permissions': ('dcim.view_modulebay', 'dcim.add_modulebay', 'dcim.change_modulebay', 'dcim.delete_modulebay'),
        'component_label': 'Module bays',
        'get_components_qs': lambda device: device.modulebays.all().filter(level=0),
    },
}


class BulkSyncView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    Handle bulk synchronization actions for component types.
    This view is called via AJAX from template extensions.
    """
    
    def get_permission_required(self):
        """Dynamically set permissions based on component type"""
        component_type = self.kwargs.get('component_type')
        if component_type in COMPONENT_MAPPINGS:
            return COMPONENT_MAPPINGS[component_type]['permissions']
        return ()
    
    def post(self, request, device_id, component_type):
        # Validate component type
        if component_type not in COMPONENT_MAPPINGS:
            return HttpResponseBadRequest(f"Invalid component type: {component_type}")
            
        mapping = COMPONENT_MAPPINGS[component_type]
        device = get_object_or_404(Device.objects.filter(id=device_id))
        
        components_qs = mapping['get_components_qs'](device)
        templates_qs = mapping['template_model'].objects.filter(device_type=device.device_type)
        
        Model = mapping['model']
        TemplateModel = mapping['template_model']
        component_label = mapping['component_label']
        
        # Determine which bulk action was requested
        action = request.POST.get('action')
        
        if action == 'add_missing':
            return handle_bulk_add_missing(
                request, device, components_qs, templates_qs,
                Model, TemplateModel, [], component_label
            )
        elif action == 'repair_out_of_sync':
            return handle_bulk_repair_out_of_sync(
                request, device, components_qs, templates_qs,
                Model, TemplateModel, [], component_label
            )
        elif action == 'remove_out_of_sync':
            return handle_bulk_remove_out_of_sync(
                request, device, components_qs, templates_qs,
                Model, TemplateModel, [], component_label
            )
        elif action == 'sync_all':
            return handle_bulk_sync_all(
                request, device, components_qs, templates_qs,
                Model, TemplateModel, [], component_label
            )
        else:
            messages.error(request, "Unknown bulk action requested.")
            # Redirect back to the component list view
            return redirect(f'/dcim/devices/{device_id}/{component_type}/')
