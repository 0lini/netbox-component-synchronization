from django.urls import path

from . import views
from .factory import component_factory


def create_component_urls():
    """Dynamically create URL patterns for all registered components."""
    urlpatterns = []
    
    for component_name, config in component_factory.get_all_configurations().items():
        # Get the view class for this component
        view_class_name = f"{component_name.title()}ComparisonView"
        view_class = getattr(views, view_class_name, None)
        
        if view_class:
            url_pattern = path(
                f"{component_name}-comparison/<int:device_id>/",
                view_class.as_view(),
                name=f"{component_name}_comparison",
            )
            urlpatterns.append(url_pattern)
    
    return urlpatterns


# Define a list of URL patterns to be imported by NetBox. Each pattern maps a URL to
# a specific view so that it can be accessed by users.
urlpatterns = create_component_urls()
