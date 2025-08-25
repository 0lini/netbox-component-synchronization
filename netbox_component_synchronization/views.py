from typing import Iterable, Callable
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import View
from dcim.models import Device
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.conf import settings
from django.contrib import messages

from .utils import get_components, post_components
from .forms import ComponentComparisonForm
from .factory import component_factory

config = settings.PLUGINS_CONFIG["netbox_component_synchronization"]


def _parse_fix_ids(request, key: str = "fix_name") -> set[int]:
    return {int(x) for x in request.POST.getlist(key) if x.isdigit()}


def _fix_name_components_from_qs(qs: Iterable, fix_ids: set[int]):
    try:
        return qs.filter(id__in=fix_ids)
    except Exception:
        return [c for c in qs if c.id in fix_ids]


def _build_unified_list(qs: Iterable, factory: Callable, *, is_template: bool = False):
    if is_template:
        return [factory(i, is_template=True) for i in qs]
    return [factory(i) for i in qs]


class BaseComponentComparisonView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Base view for component comparison, now uses the factory pattern."""
    
    def __init__(self, component_name: str = None, **kwargs):
        super().__init__(**kwargs)
        self.component_name = component_name
        if component_name:
            self.config = component_factory.get_configuration(component_name)
            self.permission_required = self.config.permissions
            self.component_label = self.config.component_label
            self.Model = self.config.model
            self.TemplateModel = self.config.template_model
            self.ComparisonClass = self.config.comparison_class

    def get_components_qs(self, device: Device):
        """Get the components queryset for the device."""
        if not self.component_name:
            raise NotImplementedError("Component name must be specified")
            
        config = self.config
        
        # Use custom queryset filter if available
        if config.custom_queryset_filter:
            return config.custom_queryset_filter(device)
        
        # Default queryset logic
        model_name = config.model.__name__.lower()
        
        # Get the appropriate manager based on model name
        if model_name == "interface":
            qs = device.vc_interfaces().exclude(module_id__isnull=False)
            # Use global config for interface type exclusion
            from django.conf import settings
            global_config = settings.PLUGINS_CONFIG["netbox_component_synchronization"]
            return qs.exclude(type__in=global_config.get("exclude_interface_type_list", []))
        else:
            # For most other components, use the device's related manager
            manager_name = f"{model_name}s"
            if hasattr(device, manager_name):
                qs = getattr(device, manager_name).all()
                # Exclude modules for most component types
                if hasattr(qs.model, 'module_id'):
                    qs = qs.exclude(module_id__isnull=False)
                return qs
            else:
                raise AttributeError(f"Device has no manager named '{manager_name}'")

    def get_templates_qs(self, device: Device):
        """Get the component templates queryset."""
        return self.TemplateModel.objects.filter(device_type=device.device_type)

    def _factory(self, instance, is_template: bool = False):
        """Factory method using the component factory."""
        return component_factory.create_comparison_object(
            self.component_name, instance, is_template
        )

    def get(self, request, device_id):
        device = get_object_or_404(Device.objects.filter(id=device_id))
        components_qs = self.get_components_qs(device)
        templates_qs = self.get_templates_qs(device)

        unified_components = _build_unified_list(components_qs, self._factory)
        unified_templates = _build_unified_list(templates_qs, self._factory, is_template=True)

        return get_components(
            request,
            device,
            components_qs,
            unified_components,
            unified_templates,
            self.component_label,
        )

    def post(self, request, device_id):
        form = ComponentComparisonForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Invalid form submission.")
            return redirect(request.path)

        device = get_object_or_404(Device.objects.filter(id=device_id))
        components_qs = self.get_components_qs(device)
        templates_qs = self.get_templates_qs(device)

        fix_ids = _parse_fix_ids(request)
        fix_name_components = _fix_name_components_from_qs(components_qs, fix_ids)

        unified_templates = _build_unified_list(templates_qs, self._factory, is_template=True)

        unified_components = [(c, self._factory(c)) for c in fix_name_components]

        return post_components(
            request,
            device,
            components_qs,
            templates_qs,
            self.Model,
            self.TemplateModel,
            unified_components,
            unified_templates,
            self.component_label,
        )

def create_component_view(component_name: str):
    """Factory function to create a component comparison view class."""
    class ComponentComparisonView(BaseComponentComparisonView):
        def __init__(self, **kwargs):
            super().__init__(component_name=component_name, **kwargs)
    
    # Set the class name for debugging purposes
    ComponentComparisonView.__name__ = f"{component_name.title()}ComparisonView"
    ComponentComparisonView.__qualname__ = ComponentComparisonView.__name__
    
    return ComponentComparisonView


# Create all component view classes using the factory
InterfaceComparisonView = create_component_view("interface")
PowerPortComparisonView = create_component_view("powerport")
ConsolePortComparisonView = create_component_view("consoleport")
ConsoleServerPortComparisonView = create_component_view("consoleserverport")
PowerOutletComparisonView = create_component_view("poweroutlet")
FrontPortComparisonView = create_component_view("frontport")
RearPortComparisonView = create_component_view("rearport")
DeviceBayComparisonView = create_component_view("devicebay")
ModuleBayComparisonView = create_component_view("modulebay")
