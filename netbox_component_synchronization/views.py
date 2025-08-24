from typing import Iterable, Callable
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import View
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
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
from utilities.permissions import get_permission_for_model

from .utils import get_components, post_components, handle_bulk_add_missing, handle_bulk_repair_out_of_sync, handle_bulk_remove_out_of_sync, handle_bulk_sync_all
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


class ComponentActionsMixin:
    """
    Mixin that provides bulk action support for component comparison views.
    Follows NetBox's ActionsMixin pattern.
    """
    actions = {
        'bulk_add_missing': {'add'},
        'bulk_repair_out_of_sync': {'change'},
        'bulk_remove_out_of_sync': {'delete'}, 
        'bulk_sync_all': {'add', 'change', 'delete'},
    }

    def get_permitted_actions(self, user, model=None):
        """
        Return a tuple of actions for which the given user is permitted to do.
        """
        model = model or self.Model

        # Resolve required permissions for each action
        permitted_actions = []
        for action in self.actions:
            required_permissions = [
                get_permission_for_model(model, name) for name in self.actions.get(action, set())
            ]
            if not required_permissions or user.has_perms(required_permissions):
                permitted_actions.append(action)

        return permitted_actions


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


class BaseComponentComparisonView(ComponentActionsMixin, LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = ()
    component_label = "components"
    Model = None
    TemplateModel = None
    ComparisonClass = None

    def get_components_qs(self, device: Device):
        raise NotImplementedError

    def get_templates_qs(self, device: Device):
        return self.TemplateModel.objects.filter(device_type=device.device_type)

    def _factory(self, instance, is_template: bool = False):
        """Default trivial factory (expect subclasses to override)."""
        raise NotImplementedError

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
            view_instance=self,
        )

    def post(self, request, device_id):
        # Check for bulk actions first - handle them directly using the bulk action handlers
        if any(action in request.POST for action in self.actions.keys()):
            return self._handle_bulk_action(request, device_id)
        
        # Handle individual component actions (existing logic)
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
    
    def _handle_bulk_action(self, request, device_id):
        """
        Handle bulk actions using the appropriate bulk action handlers.
        This follows NetBox patterns by delegating to specific handler functions.
        """
        device = get_object_or_404(Device.objects.filter(id=device_id))
        components_qs = self.get_components_qs(device)
        templates_qs = self.get_templates_qs(device)
        
        # Determine which bulk action was requested and call the appropriate handler
        if request.POST.get('bulk_add_missing'):
            return handle_bulk_add_missing(
                request, device, components_qs, templates_qs,
                self.Model, self.TemplateModel, [], self.component_label
            )
        elif request.POST.get('bulk_repair_out_of_sync'):
            return handle_bulk_repair_out_of_sync(
                request, device, components_qs, templates_qs,
                self.Model, self.TemplateModel, [], self.component_label
            )
        elif request.POST.get('bulk_remove_out_of_sync'):
            return handle_bulk_remove_out_of_sync(
                request, device, components_qs, templates_qs,
                self.Model, self.TemplateModel, [], self.component_label
            )
        elif request.POST.get('bulk_sync_all'):
            return handle_bulk_sync_all(
                request, device, components_qs, templates_qs,
                self.Model, self.TemplateModel, [], self.component_label
            )
        else:
            messages.error(request, "Unknown bulk action requested.")
            return redirect(request.path)


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

    def get_components_qs(self, device: Device):
        qs = device.vc_interfaces().exclude(module_id__isnull=False)
        return qs.exclude(type__in=config["exclude_interface_type_list"])

    def _factory(self, i, is_template=False):
        return InterfaceComparison(
            i.id,
            i.name,
            i.label,
            i.description,
            i.type,
            i.get_type_display(),
            i.enabled,
            i.mgmt_only,
            i.poe_mode,
            i.poe_type,
            i.rf_role,
            is_template=is_template,
        )


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

    def get_components_qs(self, device: Device):
        return device.powerports.all().exclude(module_id__isnull=False)

    def _factory(self, i, is_template=False):
        return PowerPortComparison(
            i.id,
            i.name,
            i.label,
            i.description,
            i.type,
            i.get_type_display(),
            i.maximum_draw,
            i.allocated_draw,
            is_template=is_template,
        )


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

    def get_components_qs(self, device: Device):
        return device.consoleports.all().exclude(module_id__isnull=False)

    def _factory(self, i, is_template=False):
        return ConsolePortComparison(
            i.id,
            i.name,
            i.label,
            i.description,
            i.type,
            i.get_type_display(),
            is_template=is_template,
        )


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

    def get_components_qs(self, device: Device):
        return device.consoleserverports.all().exclude(module_id__isnull=False)

    def _factory(self, i, is_template=False):
        return ConsoleServerPortComparison(
            i.id,
            i.name,
            i.label,
            i.description,
            i.type,
            i.get_type_display(),
            is_template=is_template,
        )


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

    def get_components_qs(self, device: Device):
        return device.poweroutlets.all().exclude(module_id__isnull=False)

    def _factory(self, i, is_template=False):
        power_port_name = ""
        if i.power_port_id is not None:
            try:
                if is_template:
                    power_port_name = PowerPortTemplate.objects.get(id=i.power_port_id).name
                else:
                    power_port_name = PowerPort.objects.get(id=i.power_port_id).name
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

    def get_components_qs(self, device: Device):
        return device.frontports.all().exclude(module_id__isnull=False)

    def _factory(self, i, is_template=False):
        return FrontPortComparison(
            i.id,
            i.name,
            i.label,
            i.description,
            i.type,
            i.get_type_display(),
            i.color,
            i.rear_port_position,
            is_template=is_template,
        )


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

    def get_components_qs(self, device: Device):
        return device.rearports.all().exclude(module_id__isnull=False)

    def _factory(self, i, is_template=False):
        return RearPortComparison(
            i.id,
            i.name,
            i.label,
            i.description,
            i.type,
            i.get_type_display(),
            i.color,
            i.positions,
            is_template=is_template,
        )


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

    def get_components_qs(self, device: Device):
        return device.devicebays.all().exclude(module_id__isnull=False)

    def _factory(self, i, is_template=False):
        return DeviceBayComparison(
            i.id, i.name, i.label, i.description, is_template=is_template
        )


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

    def get_components_qs(self, device: Device):
        return device.modulebays.all().filter(level=0)

    def _factory(self, i, is_template=False):
        return ModuleBayComparison(
            i.id, i.name, i.label, i.description, i.position, is_template=is_template
        )
