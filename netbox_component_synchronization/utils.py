import re
from typing import Iterable
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings

# Import the new async functionality
from .async_utils import build_comparison_data

config = settings.PLUGINS_CONFIG["netbox_component_synchronization"]


def split(s):
    for x, y in re.findall(r"(\d*)(\D*)", s):
        yield "", int(x or "0")
        yield y, 0


def natural_keys(c):
    return tuple(split(c))


def human_sorted(iterable: Iterable):
    return sorted(iterable, key=natural_keys)


async def get_components_async(
    request,
    device,
    components,
    unified_components,
    unified_component_templates,
    component_type,
):
    """Async version of get_components with improved efficiency"""
    comparison_items = await build_comparison_data(unified_components, unified_component_templates)
    
    return render(
        request,
        "netbox_component_synchronization/components_comparison.html",
        {
            "component_type": component_type,
            "comparison_items": comparison_items,
            "templates_count": len(unified_component_templates),
            "components_count": len(components),
            "device": device,
        },
    )


def get_components(
    request,
    device,
    components,
    unified_components,
    unified_component_templates,
    component_type,
):
    """Legacy synchronous version - maintained for backward compatibility"""
    # List of components and components templates presented in the unified format
    overall_powers = list(set(unified_component_templates + unified_components))
    overall_powers.sort(key=lambda o: natural_keys(o.name))

    comparison_templates = []
    comparison_components = []
    for i in overall_powers:
        try:
            comparison_templates.append(
                unified_component_templates[unified_component_templates.index(i)]
            )
        except ValueError:
            comparison_templates.append(None)

        try:
            comparison_components.append(
                unified_components[unified_components.index(i)]
            )
        except ValueError:
            comparison_components.append(None)

    comparison_items = list(zip(comparison_templates, comparison_components))
    return render(
        request,
        "netbox_component_synchronization/components_comparison.html",
        {
            "component_type": component_type,
            "comparison_items": comparison_items,
            "templates_count": len(unified_component_templates),
            "components_count": len(components),
            "device": device,
        },
    )


# Legacy post_components function - simplified and improved but maintained for compatibility
def post_components(
    request,
    device,
    components,
    component_templates,
    ObjectType,
    ObjectTemplateType,
    unified_component,
    unified_component_templates,
    component_type,
):
    """
    Legacy synchronous version of component processing.
    This has been simplified to reduce complexity while maintaining backward compatibility.
    """
    # Parse form data with better validation
    add_to_device = _parse_and_filter_ids(
        request.POST.getlist("add_to_device"),
        component_templates.values_list("id", flat=True)
    )
    remove_from_device = _parse_and_filter_ids(
        request.POST.getlist("remove_from_device"),
        components.values_list("id", flat=True)
    )

    # Process deletions
    deleted = _process_deletions(ObjectType, remove_from_device)
    
    # Process additions
    created, updated = _process_additions(
        ObjectType, ObjectTemplateType, device, components, add_to_device
    )
    
    # Process name fixes
    fixed = _process_name_fixes(unified_component, unified_component_templates)

    # Generate and display result message
    _create_and_display_message(request, created, updated, deleted, fixed, component_type)

    return redirect(request.path)


def _parse_and_filter_ids(raw_ids, valid_ids):
    """Parse IDs from strings and filter to only valid ones"""
    parsed_ids = [int(x) for x in raw_ids if x.isdigit()]
    valid_ids_set = set(valid_ids)
    return [id for id in parsed_ids if id in valid_ids_set]


def _process_deletions(ObjectType, remove_ids):
    """Process component deletions"""
    if not remove_ids:
        return 0
    return ObjectType.objects.filter(id__in=remove_ids).delete()[0]


def _process_additions(ObjectType, ObjectTemplateType, device, components, add_ids):
    """Process component additions and updates"""
    if not add_ids:
        return 0, 0
        
    add_to_device_component = ObjectTemplateType.objects.filter(id__in=add_ids)
    
    bulk_create = []
    created = 0
    updated = 0
    keys_to_avoid = ["id"]

    if not config.get("compare_description", True):
        keys_to_avoid.append("description")

    for template_data in add_to_device_component.values():
        component = _create_or_update_component(
            ObjectType, device, components, template_data, keys_to_avoid
        )
        
        if component['action'] == 'create':
            if ObjectType.__name__ == "ModuleBay":
                # Bulk create does not work for creating ModuleBay
                component['object'].save()
                created += 1
            else:
                bulk_create.append(component['object'])
        elif component['action'] == 'update':
            component['object'].save()
            updated += 1

    if bulk_create:
        created += len(ObjectType.objects.bulk_create(bulk_create))
        
    return created, updated


def _create_or_update_component(ObjectType, device, components, template_data, keys_to_avoid):
    """Create or update a single component"""
    try:
        existing_component = components.get(name=template_data["name"])
        # Update existing component
        for k, v in template_data.items():
            if k not in keys_to_avoid:
                setattr(existing_component, k, v)
        return {'action': 'update', 'object': existing_component}
    except ObjectDoesNotExist:
        # Create new component
        new_component = ObjectType()
        new_component.device = device
        for k, v in template_data.items():
            if k not in keys_to_avoid:
                setattr(new_component, k, v)
        return {'action': 'create', 'object': new_component}


def _process_name_fixes(unified_component, unified_component_templates):
    """Process name fixes for selected components"""
    fixed = 0
    template_dict = {template.name: template for template in unified_component_templates}
    
    for component, component_comparison in unified_component:
        if component_comparison.name in template_dict:
            corresponding_template = template_dict[component_comparison.name]
            if component.name != corresponding_template.name:
                component.name = corresponding_template.name
                component.save()
                fixed += 1
                
    return fixed


def _create_and_display_message(request, created, updated, deleted, fixed, component_type):
    """Create and display success message"""
    message_parts = []
    if created > 0:
        message_parts.append(f"created {created} {component_type}")
    if updated > 0:
        message_parts.append(f"updated {updated} {component_type}")
    if deleted > 0:
        message_parts.append(f"deleted {deleted} {component_type}")
    if fixed > 0:
        message_parts.append(f"fixed {fixed} {component_type}")
    
    if message_parts:
        messages.success(request, "; ".join(message_parts).capitalize())
    else:
        messages.info(request, f"No changes made to {component_type}")
