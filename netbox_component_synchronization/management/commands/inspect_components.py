"""
Django management command to inspect auto-discovered components.
"""
from django.core.management.base import BaseCommand
from django.conf import settings

from netbox_component_synchronization.auto_discovery import discover_components
from netbox_component_synchronization.component_registry import get_all_component_types, COMPONENT_REGISTRY


class Command(BaseCommand):
    help = 'Inspect auto-discovered component types'

    def add_arguments(self, parser):
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed information about each component',
        )
        parser.add_argument(
            '--component',
            type=str,
            help='Show details for a specific component type',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Component Synchronization - Auto-Discovery Inspection')
        )
        self.stdout.write('=' * 60)
        
        # Check configuration
        plugin_config = settings.PLUGINS_CONFIG.get("netbox_component_synchronization", {})
        auto_discovery_enabled = plugin_config.get("enable_auto_discovery", True)
        
        self.stdout.write(f"Auto-discovery enabled: {auto_discovery_enabled}")
        self.stdout.write("")
        
        if options['component']:
            self._show_component_details(options['component'])
        elif options['detailed']:
            self._show_detailed_list()
        else:
            self._show_summary()

    def _show_summary(self):
        """Show summary of all component types"""
        self.stdout.write("Available Component Types:")
        self.stdout.write("-" * 30)
        
        try:
            component_types = get_all_component_types()
            for i, component_type in enumerate(sorted(component_types), 1):
                status = "Static" if component_type in ['interface', 'powerport', 'consoleport', 'consoleserverport', 'poweroutlet', 'frontport', 'rearport', 'devicebay', 'modulebay'] else "Auto-discovered"
                self.stdout.write(f"{i:2d}. {component_type:<20} [{status}]")
            
            self.stdout.write("")
            self.stdout.write(f"Total: {len(component_types)} component types")
            
        except Exception as e:
            self.stderr.write(f"Error discovering components: {e}")

    def _show_detailed_list(self):
        """Show detailed information for all components"""
        self.stdout.write("Detailed Component Information:")
        self.stdout.write("-" * 40)
        
        try:
            discovered = discover_components()
            component_types = get_all_component_types()
            
            for component_type in sorted(component_types):
                self.stdout.write(f"\n{component_type.upper()}:")
                
                if component_type in COMPONENT_REGISTRY:
                    config = COMPONENT_REGISTRY[component_type]
                    self.stdout.write(f"  Label: {config.component_label}")
                    self.stdout.write(f"  Model: {config.model.__name__}")
                    self.stdout.write(f"  Template: {config.template_model.__name__}")
                    self.stdout.write(f"  Fields: {', '.join(config.factory_fields)}")
                    self.stdout.write(f"  Permissions: {len(config.permissions)} permissions")
                    
                    if config.special_fields:
                        self.stdout.write(f"  Special fields: {', '.join(config.special_fields.keys())}")
                else:
                    self.stdout.write("  [Configuration not found]")
                    
        except Exception as e:
            self.stderr.write(f"Error getting detailed information: {e}")

    def _show_component_details(self, component_name):
        """Show details for a specific component"""
        self.stdout.write(f"Details for component: {component_name}")
        self.stdout.write("-" * 40)
        
        try:
            if component_name not in COMPONENT_REGISTRY:
                self.stderr.write(f"Component '{component_name}' not found")
                return
                
            config = COMPONENT_REGISTRY[component_name]
            
            self.stdout.write(f"Component Label: {config.component_label}")
            self.stdout.write(f"Model: {config.model.__module__}.{config.model.__name__}")
            self.stdout.write(f"Template Model: {config.template_model.__module__}.{config.template_model.__name__}")
            self.stdout.write(f"Comparison Class: {config.comparison_class.__name__}")
            
            self.stdout.write(f"\nFactory Fields ({len(config.factory_fields)}):")
            for field in config.factory_fields:
                self.stdout.write(f"  - {field}")
            
            self.stdout.write(f"\nPermissions ({len(config.permissions)}):")
            for perm in config.permissions:
                self.stdout.write(f"  - {perm}")
            
            if config.special_fields:
                self.stdout.write(f"\nSpecial Fields ({len(config.special_fields)}):")
                for field_name, field_func in config.special_fields.items():
                    func_info = "callable" if callable(field_func) else str(field_func)
                    self.stdout.write(f"  - {field_name}: {func_info}")
            
            if config.custom_queryset_filter:
                self.stdout.write(f"\nCustom Filter: {config.custom_queryset_filter}")
                
        except Exception as e:
            self.stderr.write(f"Error getting component details: {e}")