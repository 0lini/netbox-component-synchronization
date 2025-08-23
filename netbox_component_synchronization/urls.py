from django.urls import path

from . import views
from .component_registry import get_all_component_types


def create_component_url_patterns():
    """
    Dynamically create URL patterns for all available component types.
    This replaces the need to manually define URLs for each component.
    """
    patterns = []
    
    # Check if auto-discovery is enabled
    try:
        from django.conf import settings
        plugin_config = settings.PLUGINS_CONFIG.get("netbox_component_synchronization", {})
        use_auto_discovery = plugin_config.get("enable_auto_discovery", True)
    except Exception:
        use_auto_discovery = True
    
    if not use_auto_discovery:
        # Return empty list to fall back to static patterns
        return []
    
    # Get all available component types (including auto-discovered ones)
    component_types = get_all_component_types()
    
    for component_type in component_types:
        # Create view class name
        view_class_name = f"{component_type.title()}ComparisonView"
        
        # Get or create the view class
        if hasattr(views, view_class_name):
            view_class = getattr(views, view_class_name)
        else:
            # Create the view class dynamically using the factory
            view_class = views.create_component_view(component_type)
            # Set it on the views module for future reference
            setattr(views, view_class_name, view_class)
        
        # Create URL pattern
        pattern = path(
            f"{component_type}-comparison/<int:device_id>/",
            view_class.as_view(),
            name=f"{component_type}_comparison",
        )
        patterns.append(pattern)
    
    return patterns


# Define a list of URL patterns to be imported by NetBox. Each pattern maps a URL to
# a specific view so that it can be accessed by users.
# Now dynamically generated based on available components.
try:
    dynamic_patterns = create_component_url_patterns()
    if dynamic_patterns:
        urlpatterns = tuple(dynamic_patterns)
    else:
        # Use static patterns if dynamic generation is disabled or returns empty
        raise Exception("Dynamic pattern generation disabled or returned empty")
except Exception as e:
    # Fallback to static patterns if dynamic generation fails
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"Dynamic URL generation failed, using static patterns: {e}")
    
    # Fallback static patterns
    urlpatterns = (
        path(
            "interface-comparison/<int:device_id>/",
            views.InterfaceComparisonView.as_view(),
            name="interface_comparison",
        ),
        path(
            "powerport-comparison/<int:device_id>/",
            views.PowerPortComparisonView.as_view(),
            name="powerport_comparison",
        ),
        path(
            "consoleport-comparison/<int:device_id>/",
            views.ConsolePortComparisonView.as_view(),
            name="consoleport_comparison",
        ),
        path(
            "consoleserverport-comparison/<int:device_id>/",
            views.ConsoleServerPortComparisonView.as_view(),
            name="consoleserverport_comparison",
        ),
        path(
            "poweroutlet-comparison/<int:device_id>/",
            views.PowerOutletComparisonView.as_view(),
            name="poweroutlet_comparison",
        ),
        path(
            "frontport-comparison/<int:device_id>/",
            views.FrontPortComparisonView.as_view(),
            name="frontport_comparison",
        ),
        path(
            "rearport-comparison/<int:device_id>/",
            views.RearPortComparisonView.as_view(),
            name="rearport_comparison",
        ),
        path(
            "devicebay-comparison/<int:device_id>/",
            views.DeviceBayComparisonView.as_view(),
            name="devicebay_comparison",
        ),
        path(
            "modulebay-comparison/<int:device_id>/",
            views.ModuleBayComparisonView.as_view(),
            name="modulebay_comparison",
        ),
    )
