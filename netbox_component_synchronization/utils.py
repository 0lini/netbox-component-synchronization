import re
from typing import Iterable
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings

# Cache config at module level to avoid repeated dictionary lookups
config = settings.PLUGINS_CONFIG["netbox_component_synchronization"]
_compare_description = config.get("compare_description", True)


def split(s):
    for x, y in re.findall(r"(\d*)(\D*)", s):
        yield "", int(x or "0")
        yield y, 0


def natural_keys(c):
    return tuple(split(c))


def human_sorted(iterable: Iterable):
    return sorted(iterable, key=natural_keys)


def get_components(
    request,
    device,
    components,
    unified_components,
    unified_component_templates,
    component_type,
):
    # List of components and components templates presented in the unified format
    overall_powers = list(set(unified_component_templates + unified_components))
    overall_powers.sort(key=lambda o: natural_keys(o.name))

    # Create dictionaries for O(1) lookup instead of O(n) list.index()
    templates_dict = {item: item for item in unified_component_templates}
    components_dict = {item: item for item in unified_components}

    comparison_templates = []
    comparison_components = []
    for i in overall_powers:
        comparison_templates.append(templates_dict.get(i))
        comparison_components.append(components_dict.get(i))

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
    # Manually validating components and component templates lists
    # Convert POST data to integers and validate against existing IDs
    valid_template_ids = set(component_templates.values_list("id", flat=True))
    valid_component_ids = set(components.values_list("id", flat=True))
    
    add_to_device = [
        int(x) for x in request.POST.getlist("add_to_device") 
        if x.isdigit() and int(x) in valid_template_ids
    ]
    remove_from_device = [
        int(x) for x in request.POST.getlist("remove_from_device")
        if x.isdigit() and int(x) in valid_component_ids
    ]

    # Remove selected component from the device and count them
    deleted = ObjectType.objects.filter(id__in=remove_from_device).delete()[0]

    # Add selected components to the device and count them
    add_to_device_component = ObjectTemplateType.objects.filter(id__in=add_to_device)

    bulk_create = []
    created = 0
    updated = 0
    keys_to_avoid = ["id"]

    if not _compare_description:
        keys_to_avoid.append("description")

    for i in add_to_device_component.values():
        to_create = False

        try:
            tmp = components.get(name=i["name"])
        except ObjectDoesNotExist:
            tmp = ObjectType()
            tmp.device = device
            to_create = True

        for k in i.keys():
            if k not in keys_to_avoid:
                setattr(tmp, k, i[k])

        if to_create:
            # Bulk create does not work for creating ModuleBay
            if ObjectType.__name__ == "ModuleBay":
                tmp.save()
                created += 1
            else:
                bulk_create.append(tmp)
        else:
            tmp.save()
            updated += 1

    created += len(ObjectType.objects.bulk_create(bulk_create))

    # Rename selected components
    # Create dictionary for O(1) lookup instead of O(n) list.index()
    templates_lookup = {template: template for template in unified_component_templates}
    
    fixed = 0
    for component, component_comparison in unified_component:
        corresponding_template = templates_lookup.get(component_comparison)
        if corresponding_template:
            component.name = corresponding_template.name
            component.save()
            fixed += 1

    # Generating result message
    message = []
    if created > 0:
        message.append(f"created {created} {component_type}")
    if updated > 0:
        message.append(f"updated {updated} {component_type}")
    if deleted > 0:
        message.append(f"deleted {deleted} {component_type}")
    if fixed > 0:
        message.append(f"fixed {fixed} {component_type}")
    messages.success(request, "; ".join(message).capitalize())

    return redirect(request.path)
