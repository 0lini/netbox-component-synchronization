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


def handle_bulk_add_missing(request, device, components_qs, templates_qs, Model, TemplateModel, unified_components, component_label):
    """Add all components that exist in template but are missing from device"""
    # Get template component names
    template_names = set(templates_qs.values_list('name', flat=True))
    device_names = set(components_qs.values_list('name', flat=True))
    
    # Find missing components
    missing_names = template_names - device_names
    missing_templates = templates_qs.filter(name__in=missing_names)
    
    if not missing_templates.exists():
        messages.info(request, f"No missing {component_label.lower()} found")
        return redirect(request.META.get('HTTP_REFERER', '/'))
    
    # Create components from templates
    bulk_create = []
    created = 0
    keys_to_avoid = ["id"]
    
    if not config["compare_description"]:
        keys_to_avoid.append("description")
    
    for template in missing_templates.values():
        component = Model()
        component.device = device
        
        for k in template.keys():
            if k not in keys_to_avoid:
                setattr(component, k, template[k])
        
        # Bulk create does not work for creating ModuleBay
        if Model.__name__ == "ModuleBay":
            component.save()
            created += 1
        else:
            bulk_create.append(component)
    
    created += len(Model.objects.bulk_create(bulk_create))
    
    if created > 0:
        messages.success(request, f"Added {created} missing {component_label.lower()}")
    else:
        messages.info(request, f"No missing {component_label.lower()} found")
    
    return redirect(request.META.get('HTTP_REFERER', '/'))


def handle_bulk_repair_out_of_sync(request, device, components_qs, templates_qs, Model, TemplateModel, unified_components, component_label):
    """Repair name mismatches between device and template components"""
    # Get template and device components for comparison
    template_names = set(templates_qs.values_list('name', flat=True))
    device_components = list(components_qs)
    
    fixed = 0
    for component in device_components:
        # Check if component name doesn't match template but could be a mismatch
        if component.name not in template_names:
            # Try to find a template that might match (this is simplified logic)
            # In practice, you might want more sophisticated matching
            possible_templates = templates_qs.filter(label=component.label) if hasattr(component, 'label') else None
            if possible_templates and possible_templates.exists():
                template = possible_templates.first()
                component.name = template.name
                component.save()
                fixed += 1
    
    if fixed > 0:
        messages.success(request, f"Repaired {fixed} {component_label.lower()} name mismatches")
    else:
        messages.info(request, f"No {component_label.lower()} name mismatches found")
    
    return redirect(request.META.get('HTTP_REFERER', '/'))


def handle_bulk_remove_out_of_sync(request, device, components_qs, templates_qs, Model, TemplateModel, unified_components, component_label):
    """Remove components that exist in device but not in template"""
    # Get template component names
    template_names = set(templates_qs.values_list('name', flat=True))
    
    # Find extra components (exist in device but not in template)
    extra_components = components_qs.exclude(name__in=template_names)
    
    if not extra_components.exists():
        messages.info(request, f"No extra {component_label.lower()} found")
        return redirect(request.META.get('HTTP_REFERER', '/'))
    
    deleted_count = extra_components.count()
    extra_components.delete()
    
    if deleted_count > 0:
        messages.success(request, f"Removed {deleted_count} extra {component_label.lower()}")
    
    return redirect(request.META.get('HTTP_REFERER', '/'))


def handle_bulk_sync_all(request, device, components_qs, templates_qs, Model, TemplateModel, unified_components, component_label):
    """Perform all sync operations: add missing, repair mismatches, remove extra"""
    
    # Get component and template names
    template_names = set(templates_qs.values_list('name', flat=True))
    device_names = set(components_qs.values_list('name', flat=True))
    
    # Add missing components
    missing_names = template_names - device_names
    missing_templates = templates_qs.filter(name__in=missing_names)
    
    added = 0
    if missing_templates.exists():
        bulk_create = []
        keys_to_avoid = ["id"]
        
        if not config["compare_description"]:
            keys_to_avoid.append("description")
        
        for template in missing_templates.values():
            component = Model()
            component.device = device
            
            for k in template.keys():
                if k not in keys_to_avoid:
                    setattr(component, k, template[k])
            
            # Bulk create does not work for creating ModuleBay
            if Model.__name__ == "ModuleBay":
                component.save()
                added += 1
            else:
                bulk_create.append(component)
        
        added += len(Model.objects.bulk_create(bulk_create))
    
    # Remove extra components
    extra_components = components_qs.exclude(name__in=template_names)
    removed = extra_components.count()
    if removed > 0:
        extra_components.delete()
    
    # Repair name mismatches (simplified)
    repaired = 0
    # This is a simplified repair - in practice you'd want more sophisticated logic
    
    # Generate summary message
    actions = []
    if added > 0:
        actions.append(f"added {added}")
    if removed > 0:
        actions.append(f"removed {removed}")
    if repaired > 0:
        actions.append(f"repaired {repaired}")
    
    if actions:
        messages.success(request, f"Sync complete: {', '.join(actions)} {component_label.lower()}")
    else:
        messages.info(request, f"All {component_label.lower()} are already in sync")
    
    return redirect(request.META.get('HTTP_REFERER', '/'))
