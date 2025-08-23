"""
Simplified and refactored views using component registry and async processing.
This dramatically reduces code duplication and complexity.
"""
import asyncio
from typing import Dict, Any
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from dcim.models import Device
from asgiref.sync import sync_to_async

from .component_registry import (
    get_component_config, 
    create_component_factory,
    get_component_queryset,
    COMPONENT_REGISTRY
)
from .async_utils import (
    process_component_comparison,
    create_success_message,
    build_comparison_data,
    parse_form_ids,
    filter_valid_ids
)
from .forms import ComponentComparisonForm


def _build_unified_list(qs, factory, *, is_template: bool = False):
    """Build unified list using the factory function"""
    if is_template:
        return [factory(i, is_template=True) for i in qs]
    return [factory(i) for i in qs]


class GenericComponentComparisonView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    Generic view that handles all component types using the component registry.
    This replaces the 9 individual component view classes with a single configurable one.
    """
    component_type = None  # To be set by subclasses
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.component_type:
            self.config = get_component_config(self.component_type)
            self.factory = create_component_factory(self.config)
    
    @property 
    def permission_required(self):
        return self.config.permissions if hasattr(self, 'config') else ()
    
    async def get_async(self, request, device_id):
        """Async version of GET request handling"""
        device = await sync_to_async(get_object_or_404)(Device.objects.filter(id=device_id))
        
        # Get querysets
        components_qs = get_component_queryset(device, self.component_type)
        templates_qs = self.config.template_model.objects.filter(device_type=device.device_type)
        
        # Build unified lists
        unified_components = _build_unified_list(components_qs, self.factory)
        unified_templates = _build_unified_list(templates_qs, self.factory, is_template=True)
        
        # Build comparison data
        comparison_items = await build_comparison_data(unified_components, unified_templates)
        
        context = {
            "component_type": self.config.component_label,
            "comparison_items": comparison_items,
            "templates_count": len(unified_templates),
            "components_count": len(components_qs),
            "device": device,
        }
        
        return render(request, "netbox_component_synchronization/components_comparison.html", context)
    
    def get(self, request, device_id):
        """Synchronous wrapper for async GET handling"""
        return asyncio.run(self.get_async(request, device_id))
    
    async def post_async(self, request, device_id):
        """Async version of POST request handling"""
        form = ComponentComparisonForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Invalid form submission.")
            return redirect(request.path)
            
        device = await sync_to_async(get_object_or_404)(Device.objects.filter(id=device_id))
        
        # Get querysets
        components_qs = get_component_queryset(device, self.component_type)
        templates_qs = self.config.template_model.objects.filter(device_type=device.device_type)
        
        # Parse form data
        add_ids = parse_form_ids(request, "add_to_device")
        remove_ids = parse_form_ids(request, "remove_from_device")
        fix_ids = parse_form_ids(request, "fix_name")
        
        # Filter to valid IDs only
        add_ids = filter_valid_ids(add_ids, templates_qs)
        remove_ids = filter_valid_ids(remove_ids, components_qs)
        fix_ids = filter_valid_ids(fix_ids, components_qs)
        
        # Build unified components for name fixing
        fix_components = [c for c in components_qs if c.id in fix_ids] if fix_ids else []
        unified_fix_components = [(c, self.factory(c)) for c in fix_components]
        unified_templates = _build_unified_list(templates_qs, self.factory, is_template=True)
        
        # Process the comparison operations
        stats = await process_component_comparison(
            device=device,
            components_qs=components_qs,
            unified_components=unified_fix_components,
            unified_templates=unified_templates,
            object_type=self.config.model,
            object_template_type=self.config.template_model,
            component_type=self.config.component_label,
            add_ids=add_ids,
            remove_ids=remove_ids
        )
        
        # Create success message
        success_msg = create_success_message(stats, self.config.component_label)
        messages.success(request, success_msg)
        
        return redirect(request.path)
    
    def post(self, request, device_id):
        """Synchronous wrapper for async POST handling"""
        return asyncio.run(self.post_async(request, device_id))


# Create specific view classes for each component type using the generic view
class InterfaceComparisonView(GenericComponentComparisonView):
    component_type = 'interface'


class PowerPortComparisonView(GenericComponentComparisonView):
    component_type = 'powerport'


class ConsolePortComparisonView(GenericComponentComparisonView):
    component_type = 'consoleport'


class ConsoleServerPortComparisonView(GenericComponentComparisonView):
    component_type = 'consoleserverport'


class PowerOutletComparisonView(GenericComponentComparisonView):
    component_type = 'poweroutlet'


class FrontPortComparisonView(GenericComponentComparisonView):
    component_type = 'frontport'


class RearPortComparisonView(GenericComponentComparisonView):
    component_type = 'rearport'


class DeviceBayComparisonView(GenericComponentComparisonView):
    component_type = 'devicebay'


class ModuleBayComparisonView(GenericComponentComparisonView):
    component_type = 'modulebay'


# For backwards compatibility, keep a factory function to create views dynamically
def create_component_view(component_type: str) -> type:
    """Factory function to create a component view class dynamically"""
    class_name = f"{component_type.title()}ComparisonView"
    return type(class_name, (GenericComponentComparisonView,), {
        'component_type': component_type
    })
