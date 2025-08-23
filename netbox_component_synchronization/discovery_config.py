"""
Configuration and utilities for the auto-discovery feature.
"""
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def get_plugin_config() -> Dict[str, Any]:
    """Get plugin configuration with safe defaults"""
    try:
        from django.conf import settings
        return settings.PLUGINS_CONFIG.get("netbox_component_synchronization", {})
    except (ImportError, AttributeError):
        return {}


def is_auto_discovery_enabled() -> bool:
    """Check if auto-discovery is enabled"""
    config = get_plugin_config()
    return config.get("enable_auto_discovery", True)


def get_excluded_component_types() -> list:
    """Get list of component types to exclude from auto-discovery"""
    config = get_plugin_config()
    return config.get("exclude_auto_discovery_types", [])


def should_compare_description() -> bool:
    """Check if description should be compared"""
    config = get_plugin_config()
    return config.get("compare_description", True)


class AutoDiscoveryConfig:
    """Configuration class for auto-discovery settings"""
    
    @property
    def enabled(self) -> bool:
        return is_auto_discovery_enabled()
    
    @property
    def excluded_types(self) -> list:
        return get_excluded_component_types()
    
    @property
    def compare_description(self) -> bool:
        return should_compare_description()
    
    def is_component_excluded(self, component_name: str) -> bool:
        """Check if a component type should be excluded"""
        return component_name.lower() in [t.lower() for t in self.excluded_types]


# Global config instance
config = AutoDiscoveryConfig()