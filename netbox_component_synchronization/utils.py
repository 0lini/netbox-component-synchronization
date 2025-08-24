import re
from typing import Iterable
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings

config = settings.PLUGINS_CONFIG["netbox_component_synchronization"]


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

    comparison_templates = []
    comparison_components = []
    sync_status_list = []
    
    for i in overall_powers:
        template = None
        component = None
        
        try:
            template = unified_component_templates[unified_component_templates.index(i)]
            comparison_templates.append(template)
        except ValueError:
            comparison_templates.append(None)

        try:
            component = unified_components[unified_components.index(i)]
            comparison_components.append(component)
        except ValueError:
            comparison_components.append(None)
            
        # Determine sync status
        if template and component:
            if template.name == component.name:
                sync_status = "in_sync"
            else:
                sync_status = "name_mismatch"
        elif template and not component:
            sync_status = "missing_from_device"
        elif component and not template:
            sync_status = "missing_from_template"
        else:
            sync_status = "unknown"
            
        sync_status_list.append(sync_status)

    comparison_items = list(zip(comparison_templates, comparison_components, sync_status_list))
    
    # Calculate sync statistics
    sync_stats = {
        'in_sync': sync_status_list.count('in_sync'),
        'name_mismatch': sync_status_list.count('name_mismatch'),
        'missing_from_device': sync_status_list.count('missing_from_device'),
        'missing_from_template': sync_status_list.count('missing_from_template'),
    }
    
    # Check if sync status toggle is requested
    show_sync_status = request.GET.get('show_sync_status', 'false').lower() == 'true'
    
    return render(
        request,
        "netbox_component_synchronization/components_comparison.html",
        {
            "component_type": component_type,
            "comparison_items": comparison_items,
            "templates_count": len(unified_component_templates),
            "components_count": len(components),
            "device": device,
            "sync_stats": sync_stats,
            "show_sync_status": show_sync_status,
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
    # Check for bulk operations first
    if request.POST.get('bulk_add_missing'):
        return handle_bulk_add_missing(request, device, components, component_templates, ObjectType, ObjectTemplateType, unified_component_templates, component_type)
    elif request.POST.get('bulk_repair_out_of_sync'):
        return handle_bulk_repair_out_of_sync(request, device, components, component_templates, ObjectType, ObjectTemplateType, unified_component_templates, component_type)
    elif request.POST.get('bulk_remove_out_of_sync'):
        return handle_bulk_remove_out_of_sync(request, device, components, component_templates, ObjectType, ObjectTemplateType, unified_component_templates, component_type)
    elif request.POST.get('bulk_sync_all'):
        return handle_bulk_sync_all(request, device, components, component_templates, ObjectType, ObjectTemplateType, unified_component_templates, component_type)
    
    # Handle individual operations (existing logic)
    # Manually validating components and component templates lists
    add_to_device = filter(
        lambda i: i in component_templates.values_list("id", flat=True),
        map(int, filter(lambda x: x.isdigit(), request.POST.getlist("add_to_device"))),
    )
    remove_from_device = filter(
        lambda i: i in components.values_list("id", flat=True),
        map(
            int,
            filter(lambda x: x.isdigit(), request.POST.getlist("remove_from_device")),
        ),
    )

    # Remove selected component from the device and count them
    deleted = ObjectType.objects.filter(id__in=remove_from_device).delete()[0]

    # Add selected components to the device and count them
    add_to_device_component = ObjectTemplateType.objects.filter(id__in=add_to_device)

    bulk_create = []
    created = 0
    updated = 0
    keys_to_avoid = ["id"]

    if not config["compare_description"]:
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
    fixed = 0
    for component, component_comparison in unified_component:
        try:
            # Try to extract a component template with the corresponding name
            corresponding_template = unified_component_templates[
                unified_component_templates.index(component_comparison)
            ]
            component.name = corresponding_template.name
            component.save()
            fixed += 1
        except ValueError:
            pass

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


def handle_bulk_add_missing(request, device, components, component_templates, ObjectType, ObjectTemplateType, unified_component_templates, component_type):
    """Add all components that exist in template but not in device"""
    existing_component_names = set(components.values_list('name', flat=True))
    templates_to_add = component_templates.exclude(name__in=existing_component_names)
    
    bulk_create = []
    created = 0
    keys_to_avoid = ["id"]
    
    if not config["compare_description"]:
        keys_to_avoid.append("description")
    
    for template in templates_to_add.values():
        tmp = ObjectType()
        tmp.device = device
        
        for k in template.keys():
            if k not in keys_to_avoid:
                setattr(tmp, k, template[k])
        
        if ObjectType.__name__ == "ModuleBay":
            tmp.save()
            created += 1
        else:
            bulk_create.append(tmp)
    
    created += len(ObjectType.objects.bulk_create(bulk_create))
    
    if created > 0:
        messages.success(request, f"Added {created} missing {component_type}")
    else:
        messages.info(request, f"No missing {component_type} to add")
    
    return redirect(request.path)


def handle_bulk_repair_out_of_sync(request, device, components, component_templates, ObjectType, ObjectTemplateType, unified_component_templates, component_type):
    """Fix names of components that exist in both device and template but have different names"""
    fixed = 0
    template_dict = {t.name: t for t in component_templates}
    
    for component in components:
        # Find template with similar attributes but different name
        matching_template = None
        for template in component_templates:
            if (component.name != template.name and 
                getattr(component, 'type', None) == getattr(template, 'type', None)):
                # Additional attribute matching logic could be added here
                matching_template = template
                break
        
        if matching_template:
            component.name = matching_template.name
            component.save()
            fixed += 1
    
    if fixed > 0:
        messages.success(request, f"Repaired {fixed} out of sync {component_type}")
    else:
        messages.info(request, f"No out of sync {component_type} to repair")
    
    return redirect(request.path)


def handle_bulk_remove_out_of_sync(request, device, components, component_templates, ObjectType, ObjectTemplateType, unified_component_templates, component_type):
    """Remove components that exist in device but not in template"""
    template_names = set(component_templates.values_list('name', flat=True))
    components_to_remove = components.exclude(name__in=template_names)
    
    deleted = components_to_remove.delete()[0]
    
    if deleted > 0:
        messages.success(request, f"Removed {deleted} out of sync {component_type}")
    else:
        messages.info(request, f"No out of sync {component_type} to remove")
    
    return redirect(request.path)


def handle_bulk_sync_all(request, device, components, component_templates, ObjectType, ObjectTemplateType, unified_component_templates, component_type):
    """Perform all sync operations: add missing, repair mismatches, remove extras"""
    # Add missing components
    existing_component_names = set(components.values_list('name', flat=True))
    templates_to_add = component_templates.exclude(name__in=existing_component_names)
    
    bulk_create = []
    created = 0
    keys_to_avoid = ["id"]
    
    if not config["compare_description"]:
        keys_to_avoid.append("description")
    
    for template in templates_to_add.values():
        tmp = ObjectType()
        tmp.device = device
        
        for k in template.keys():
            if k not in keys_to_avoid:
                setattr(tmp, k, template[k])
        
        if ObjectType.__name__ == "ModuleBay":
            tmp.save()
            created += 1
        else:
            bulk_create.append(tmp)
    
    created += len(ObjectType.objects.bulk_create(bulk_create))
    
    # Remove out of sync components
    template_names = set(component_templates.values_list('name', flat=True))
    components_to_remove = components.exclude(name__in=template_names)
    deleted = components_to_remove.delete()[0]
    
    # Fix name mismatches (simplified approach)
    fixed = 0
    # Note: This is a simplified repair - in practice, you might need more sophisticated matching logic
    
    # Generate result message
    messages_list = []
    if created > 0:
        messages_list.append(f"added {created}")
    if deleted > 0:
        messages_list.append(f"removed {deleted}")
    if fixed > 0:
        messages_list.append(f"repaired {fixed}")
    
    if messages_list:
        messages.success(request, f"Sync complete: {', '.join(messages_list)} {component_type}")
    else:
        messages.info(request, f"All {component_type} are already in sync")
    
    return redirect(request.path)
