"""
Custom component list views that extend NetBox's core views with bulk sync actions.
"""

from django.shortcuts import get_object_or_404
from dcim.models import Device
from dcim.views import DeviceComponentListView
from .actions import ComponentSyncActionsMixin


class SyncEnabledInterfaceListView(ComponentSyncActionsMixin, DeviceComponentListView):
    """Interface list view with sync actions"""
    component_type = 'interfaces'
    
    def get_queryset(self):
        device = get_object_or_404(Device, pk=self.kwargs['pk'])
        return device.vc_interfaces().exclude(
            module_id__isnull=False
        ).exclude(
            type__in=self.get_exclude_interface_types()
        )
    
    def get_exclude_interface_types(self):
        from django.conf import settings
        config = settings.PLUGINS_CONFIG.get("netbox_component_synchronization", {})
        return config.get("exclude_interface_type_list", ["lag", "bridge"])


class SyncEnabledPowerPortListView(ComponentSyncActionsMixin, DeviceComponentListView):
    """Power Port list view with sync actions"""
    component_type = 'power-ports'
    
    def get_queryset(self):
        device = get_object_or_404(Device, pk=self.kwargs['pk'])
        return device.powerports.all().exclude(module_id__isnull=False)


class SyncEnabledConsolePortListView(ComponentSyncActionsMixin, DeviceComponentListView):
    """Console Port list view with sync actions"""
    component_type = 'console-ports'
    
    def get_queryset(self):
        device = get_object_or_404(Device, pk=self.kwargs['pk'])
        return device.consoleports.all().exclude(module_id__isnull=False)


class SyncEnabledConsoleServerPortListView(ComponentSyncActionsMixin, DeviceComponentListView):
    """Console Server Port list view with sync actions"""
    component_type = 'console-server-ports'
    
    def get_queryset(self):
        device = get_object_or_404(Device, pk=self.kwargs['pk'])
        return device.consoleserverports.all().exclude(module_id__isnull=False)


class SyncEnabledPowerOutletListView(ComponentSyncActionsMixin, DeviceComponentListView):
    """Power Outlet list view with sync actions"""
    component_type = 'power-outlets'
    
    def get_queryset(self):
        device = get_object_or_404(Device, pk=self.kwargs['pk'])
        return device.poweroutlets.all().exclude(module_id__isnull=False)


class SyncEnabledFrontPortListView(ComponentSyncActionsMixin, DeviceComponentListView):
    """Front Port list view with sync actions"""
    component_type = 'front-ports'
    
    def get_queryset(self):
        device = get_object_or_404(Device, pk=self.kwargs['pk'])
        return device.frontports.all().exclude(module_id__isnull=False)


class SyncEnabledRearPortListView(ComponentSyncActionsMixin, DeviceComponentListView):
    """Rear Port list view with sync actions"""
    component_type = 'rear-ports'
    
    def get_queryset(self):
        device = get_object_or_404(Device, pk=self.kwargs['pk'])
        return device.rearports.all().exclude(module_id__isnull=False)


class SyncEnabledDeviceBayListView(ComponentSyncActionsMixin, DeviceComponentListView):
    """Device Bay list view with sync actions"""
    component_type = 'device-bays'
    
    def get_queryset(self):
        device = get_object_or_404(Device, pk=self.kwargs['pk'])
        return device.devicebays.all().exclude(module_id__isnull=False)


class SyncEnabledModuleBayListView(ComponentSyncActionsMixin, DeviceComponentListView):
    """Module Bay list view with sync actions"""
    component_type = 'module-bays'
    
    def get_queryset(self):
        device = get_object_or_404(Device, pk=self.kwargs['pk'])
        return device.modulebays.all().filter(level=0)