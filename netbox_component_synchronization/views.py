from typing import Iterable, Callable
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import View
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
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.conf import settings
from django.contrib import messages

from .utils import get_components, post_components
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
from .forms import ComponentComparisonForm

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
    permission_required = ()
    component_label = "components"
    Model = None
    TemplateModel = None
    ComparisonClass = None
    # Optional: define which fields to extract from the model instance
    factory_fields = ('id', 'name', 'label', 'description')
    # Optional: related field to select_related for query optimization
    select_related_field = None
    # Optional: device component accessor (e.g., 'powerports', 'consoleports')
    device_component_accessor = None

    def get_components_qs(self, device: Device):
        """Get components queryset. Can be overridden for custom logic."""
        if self.device_component_accessor is None:
            raise NotImplementedError("Must define device_component_accessor or override get_components_qs")
        
        qs = getattr(device, self.device_component_accessor).all().exclude(module_id__isnull=False)
        
        if self.select_related_field:
            qs = qs.select_related(self.select_related_field)
        
        return qs

    def get_templates_qs(self, device: Device):
        qs = self.TemplateModel.objects.filter(device_type=device.device_type)
        
        if self.select_related_field:
            qs = qs.select_related(self.select_related_field)
        
        return qs

    def _factory(self, instance, is_template: bool = False):
        """
        Generic factory method that creates a comparison object.
        Can be overridden for custom logic.
        """
        if self.ComparisonClass is None:
            raise NotImplementedError("Must define ComparisonClass or override _factory")
        
        # Build kwargs from factory_fields
        kwargs = {}
        for field in self.factory_fields:
            value = getattr(instance, field, None)
            # Handle get_FOO_display() methods for choice fields
            if field.endswith('_display'):
                base_field = field.replace('_display', '')
                display_method = f'get_{base_field}_display'
                if hasattr(instance, display_method):
                    value = getattr(instance, display_method)()
            kwargs[field] = value
        
        kwargs['is_template'] = is_template
        
        return self.ComparisonClass(**kwargs)

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


class InterfaceComparisonView(BaseComponentComparisonView):
    permission_required = (
        "dcim.view_interface",
        "dcim.add_interface",
        "dcim.change_interface",
        "dcim.delete_interface",
    )
    component_label = "Interfaces"
    Model = Interface
    TemplateModel = InterfaceTemplate
    ComparisonClass = InterfaceComparison
    factory_fields = ('id', 'name', 'label', 'description', 'type', 'type_display', 'enabled', 'mgmt_only', 'poe_mode', 'poe_type', 'rf_role')

    def get_components_qs(self, device: Device):
        # Custom logic for interfaces due to vc_interfaces() and type exclusion
        qs = device.vc_interfaces().exclude(module_id__isnull=False)
        return qs.exclude(type__in=config["exclude_interface_type_list"])


class PowerPortComparisonView(BaseComponentComparisonView):
    permission_required = (
        "dcim.view_powerport",
        "dcim.add_powerport",
        "dcim.change_powerport",
        "dcim.delete_powerport",
    )
    component_label = "Power ports"
    Model = PowerPort
    TemplateModel = PowerPortTemplate
    ComparisonClass = PowerPortComparison
    device_component_accessor = "powerports"
    factory_fields = ('id', 'name', 'label', 'description', 'type', 'type_display', 'maximum_draw', 'allocated_draw')


class ConsolePortComparisonView(BaseComponentComparisonView):
    permission_required = (
        "dcim.view_consoleport",
        "dcim.add_consoleport",
        "dcim.change_consoleport",
        "dcim.delete_consoleport",
    )
    component_label = "Console ports"
    Model = ConsolePort
    TemplateModel = ConsolePortTemplate
    ComparisonClass = ConsolePortComparison
    device_component_accessor = "consoleports"
    factory_fields = ('id', 'name', 'label', 'description', 'type', 'type_display')


class ConsoleServerPortComparisonView(BaseComponentComparisonView):
    permission_required = (
        "dcim.view_consoleserverport",
        "dcim.add_consoleserverport",
        "dcim.change_consoleserverport",
        "dcim.delete_consoleserverport",
    )
    component_label = "Console server ports"
    Model = ConsoleServerPort
    TemplateModel = ConsoleServerPortTemplate
    ComparisonClass = ConsoleServerPortComparison
    device_component_accessor = "consoleserverports"
    factory_fields = ('id', 'name', 'label', 'description', 'type', 'type_display')


class PowerOutletComparisonView(BaseComponentComparisonView):
    permission_required = (
        "dcim.view_poweroutlet",
        "dcim.add_poweroutlet",
        "dcim.change_poweroutlet",
        "dcim.delete_poweroutlet",
    )
    component_label = "Power outlets"
    Model = PowerOutlet
    TemplateModel = PowerOutletTemplate
    ComparisonClass = PowerOutletComparison
    device_component_accessor = "poweroutlets"
    select_related_field = 'power_port'
    factory_fields = ('id', 'name', 'label', 'description', 'type', 'type_display', 'feed_leg')

    def _factory(self, i, is_template=False):
        # Custom factory for power_port_name handling
        power_port_name = ""
        if i.power_port_id is not None:
            try:
                # Access the related object directly (already fetched via select_related)
                power_port_name = i.power_port.name
            except Exception:
                power_port_name = ""
        
        return PowerOutletComparison(
            i.id,
            i.name,
            i.label,
            i.description,
            i.type,
            i.get_type_display(),
            power_port_name=power_port_name,
            feed_leg=i.feed_leg,
            is_template=is_template,
        )


class FrontPortComparisonView(BaseComponentComparisonView):
    permission_required = (
        "dcim.view_frontport",
        "dcim.add_frontport",
        "dcim.change_frontport",
        "dcim.delete_frontport",
    )
    component_label = "Front ports"
    Model = FrontPort
    TemplateModel = FrontPortTemplate
    ComparisonClass = FrontPortComparison
    device_component_accessor = "frontports"
    factory_fields = ('id', 'name', 'label', 'description', 'type', 'type_display', 'color', 'rear_port_position')


class RearPortComparisonView(BaseComponentComparisonView):
    permission_required = (
        "dcim.view_rearport",
        "dcim.add_rearport",
        "dcim.change_rearport",
        "dcim.delete_rearport",
    )
    component_label = "Rear ports"
    Model = RearPort
    TemplateModel = RearPortTemplate
    ComparisonClass = RearPortComparison
    device_component_accessor = "rearports"
    factory_fields = ('id', 'name', 'label', 'description', 'type', 'type_display', 'color', 'positions')


class DeviceBayComparisonView(BaseComponentComparisonView):
    permission_required = (
        "dcim.view_devicebay",
        "dcim.add_devicebay",
        "dcim.change_devicebay",
        "dcim.delete_devicebay",
    )
    component_label = "Device bays"
    Model = DeviceBay
    TemplateModel = DeviceBayTemplate
    ComparisonClass = DeviceBayComparison
    device_component_accessor = "devicebays"
    factory_fields = ('id', 'name', 'label', 'description')


class ModuleBayComparisonView(BaseComponentComparisonView):
    permission_required = (
        "dcim.view_modulebay",
        "dcim.add_modulebay",
        "dcim.change_modulebay",
        "dcim.delete_modulebay",
    )
    component_label = "Module bays"
    Model = ModuleBay
    TemplateModel = ModuleBayTemplate
    ComparisonClass = ModuleBayComparison
    factory_fields = ('id', 'name', 'label', 'description', 'position')

    def get_components_qs(self, device: Device):
        # Custom logic for module bays - filter by level=0
        return device.modulebays.all().filter(level=0)
