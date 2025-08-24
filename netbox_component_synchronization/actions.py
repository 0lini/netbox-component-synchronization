"""
Custom NetBox ActionsMixin implementation for component synchronization.
This module provides bulk sync actions that integrate with NetBox's existing component list views.
"""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.conf import settings
from dcim.models import Device
from netbox.views.generic.mixins import ActionsMixin

from .utils import (
    handle_bulk_add_missing,
    handle_bulk_repair_out_of_sync,
    handle_bulk_remove_out_of_sync,
    handle_bulk_sync_all,
)

config = settings.PLUGINS_CONFIG.get("netbox_component_synchronization", {})


class ComponentSyncActionsMixin(ActionsMixin):
    """
    Mixin that adds component synchronization bulk actions to NetBox component list views.
    Following NetBox's ActionsMixin pattern for native integration.
    """
    
    # Define the bulk sync actions
    actions = {
        'bulk_sync_add_missing': {'permission': 'add', 'label': 'Add Missing Components'},
        'bulk_sync_repair': {'permission': 'change', 'label': 'Repair Out of Sync'}, 
        'bulk_sync_remove': {'permission': 'delete', 'label': 'Remove Out of Sync'},
        'bulk_sync_all': {'permission': 'change', 'label': 'Sync All Components'},
    }
    
    def get_extra_context(self, request, instance):
        """Add sync-specific context to the view"""
        context = super().get_extra_context(request, instance)
        
        # Add device and sync status information
        if hasattr(instance, 'device'):
            device = instance.device
        elif hasattr(self, 'get_device'):
            device = self.get_device()
        else:
            device = None
            
        if device and device.device_type:
            context.update({
                'sync_device': device,
                'sync_enabled': True,
                'component_type': self.get_component_type(),
            })
            
        return context
    
    def get_device(self):
        """Extract device from URL parameters"""
        device_id = self.kwargs.get('device_id') or self.request.resolver_match.kwargs.get('device_id')
        if device_id:
            return get_object_or_404(Device, id=device_id)
        return None
    
    def get_component_type(self):
        """Determine component type from view class or URL"""
        # This should be overridden by specific component view classes
        return getattr(self, 'component_type', 'interfaces')
    
    def get_component_mapping(self):
        """Get the component mapping for this view"""
        from .views import COMPONENT_MAPPINGS
        component_type = self.get_component_type()
        return COMPONENT_MAPPINGS.get(component_type, {})
    
    def bulk_sync_add_missing(self, request, queryset):
        """Add missing components from device type template"""
        device = self.get_device()
        if not device or not device.device_type:
            messages.error(request, "Device or device type not found.")
            return redirect(request.path)
            
        mapping = self.get_component_mapping()
        if not mapping:
            messages.error(request, "Invalid component type.")
            return redirect(request.path)
            
        components_qs = mapping['get_components_qs'](device)
        templates_qs = mapping['template_model'].objects.filter(device_type=device.device_type)
        
        return handle_bulk_add_missing(
            request, device, components_qs, templates_qs,
            mapping['model'], mapping['template_model'], [], 
            mapping['component_label']
        )
    
    def bulk_sync_repair(self, request, queryset):
        """Repair name mismatches between device and template components"""
        device = self.get_device()
        if not device or not device.device_type:
            messages.error(request, "Device or device type not found.")
            return redirect(request.path)
            
        mapping = self.get_component_mapping()
        if not mapping:
            messages.error(request, "Invalid component type.")
            return redirect(request.path)
            
        components_qs = mapping['get_components_qs'](device)
        templates_qs = mapping['template_model'].objects.filter(device_type=device.device_type)
        
        return handle_bulk_repair_out_of_sync(
            request, device, components_qs, templates_qs,
            mapping['model'], mapping['template_model'], [], 
            mapping['component_label']
        )
    
    def bulk_sync_remove(self, request, queryset):
        """Remove components that don't exist in template"""
        device = self.get_device()
        if not device or not device.device_type:
            messages.error(request, "Device or device type not found.")
            return redirect(request.path)
            
        mapping = self.get_component_mapping()
        if not mapping:
            messages.error(request, "Invalid component type.")
            return redirect(request.path)
            
        components_qs = mapping['get_components_qs'](device)
        templates_qs = mapping['template_model'].objects.filter(device_type=device.device_type)
        
        return handle_bulk_remove_out_of_sync(
            request, device, components_qs, templates_qs,
            mapping['model'], mapping['template_model'], [], 
            mapping['component_label']
        )
    
    def bulk_sync_all(self, request, queryset):
        """Perform complete synchronization (add missing, repair mismatches, remove extra)"""
        device = self.get_device()
        if not device or not device.device_type:
            messages.error(request, "Device or device type not found.")
            return redirect(request.path)
            
        mapping = self.get_component_mapping()
        if not mapping:
            messages.error(request, "Invalid component type.")
            return redirect(request.path)
            
        components_qs = mapping['get_components_qs'](device)
        templates_qs = mapping['template_model'].objects.filter(device_type=device.device_type)
        
        return handle_bulk_sync_all(
            request, device, components_qs, templates_qs,
            mapping['model'], mapping['template_model'], [], 
            mapping['component_label']
        )