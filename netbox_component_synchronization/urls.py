from django.urls import path

from . import views


# Define a list of URL patterns to be imported by NetBox. Each pattern maps a URL to
# a specific view so that it can be accessed by users.
urlpatterns = (
    # Bulk sync actions for component types
    path(
        "bulk-sync/<int:device_id>/<str:component_type>/",
        views.BulkSyncView.as_view(),
        name="bulk_sync",
    ),
)
