"""
Async utilities for component synchronization to reduce complexity and improve performance.
"""
import asyncio
from typing import List, Dict, Any, Tuple, Optional
from django.db import transaction
from django.contrib import messages
from django.shortcuts import redirect
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from asgiref.sync import sync_to_async

from .utils import natural_keys

config = settings.PLUGINS_CONFIG.get("netbox_component_synchronization", {})


class ComponentProcessor:
    """Handles component synchronization operations in a more organized way"""
    
    def __init__(self, device, object_type, object_template_type, component_type):
        self.device = device
        self.object_type = object_type
        self.object_template_type = object_template_type
        self.component_type = component_type
        self.stats = {
            'created': 0,
            'updated': 0, 
            'deleted': 0,
            'fixed': 0
        }
        
    async def process_additions(self, add_ids: List[int], components_qs) -> List[Any]:
        """Process components to be added to device"""
        if not add_ids:
            return []
            
        templates = await sync_to_async(list)(
            self.object_template_type.objects.filter(id__in=add_ids).values()
        )
        
        bulk_create = []
        keys_to_avoid = ["id"]
        
        if not config.get("compare_description", True):
            keys_to_avoid.append("description")
            
        components_dict = await self._build_components_dict(components_qs)
        
        for template_data in templates:
            component = await self._create_or_update_component(
                template_data, components_dict, keys_to_avoid
            )
            if component and not hasattr(component, 'pk'):
                # New component to be bulk created
                if self.object_type.__name__ == "ModuleBay":
                    # ModuleBay doesn't support bulk create
                    await sync_to_async(component.save)()
                    self.stats['created'] += 1
                else:
                    bulk_create.append(component)
                    
        if bulk_create:
            created_objects = await sync_to_async(
                self.object_type.objects.bulk_create
            )(bulk_create)
            self.stats['created'] += len(created_objects)
            
        return bulk_create
        
    async def process_deletions(self, remove_ids: List[int]) -> int:
        """Process components to be removed from device"""
        if not remove_ids:
            return 0
            
        deleted_count, _ = await sync_to_async(
            self.object_type.objects.filter(id__in=remove_ids).delete
        )()
        self.stats['deleted'] = deleted_count
        return deleted_count
        
    async def process_name_fixes(self, unified_components, unified_templates):
        """Process name fixes for selected components"""
        if not unified_components:
            return
            
        template_dict = {template.name: template for template in unified_templates}
        
        for component, component_comparison in unified_components:
            if component_comparison.name in template_dict:
                template = template_dict[component_comparison.name]
                if component.name != template.name:
                    component.name = template.name
                    await sync_to_async(component.save)()
                    self.stats['fixed'] += 1
                    
    async def _build_components_dict(self, components_qs) -> Dict[str, Any]:
        """Build a dictionary of existing components by name"""
        components = await sync_to_async(list)(components_qs)
        return {comp.name: comp for comp in components}
        
    async def _create_or_update_component(self, template_data: Dict, 
                                        components_dict: Dict, 
                                        keys_to_avoid: List[str]) -> Optional[Any]:
        """Create or update a component based on template data"""
        name = template_data.get('name')
        if not name:
            return None
            
        # Check if component already exists
        existing_component = components_dict.get(name)
        
        if existing_component:
            # Update existing component
            for key, value in template_data.items():
                if key not in keys_to_avoid:
                    setattr(existing_component, key, value)
            await sync_to_async(existing_component.save)()
            self.stats['updated'] += 1
            return existing_component
        else:
            # Create new component
            component = self.object_type()
            component.device = self.device
            
            for key, value in template_data.items():
                if key not in keys_to_avoid:
                    setattr(component, key, value)
                    
            return component


async def process_component_comparison(
    device,
    components_qs,
    unified_components: List,
    unified_templates: List,
    object_type,
    object_template_type,
    component_type: str,
    add_ids: List[int],
    remove_ids: List[int]
) -> Dict[str, int]:
    """
    Async main processing function for component comparison.
    Returns statistics about the operations performed.
    """
    processor = ComponentProcessor(device, object_type, object_template_type, component_type)
    
    # Process all operations concurrently where possible
    tasks = []
    
    # Process deletions first
    if remove_ids:
        tasks.append(processor.process_deletions(remove_ids))
        
    # Process additions
    if add_ids:
        tasks.append(processor.process_additions(add_ids, components_qs))
        
    # Wait for deletion and addition tasks to complete
    if tasks:
        await asyncio.gather(*tasks)
        
    # Process name fixes (must be after additions/deletions)
    await processor.process_name_fixes(unified_components, unified_templates)
    
    return processor.stats


def create_success_message(stats: Dict[str, int], component_type: str) -> str:
    """Create success message from operation statistics"""
    messages = []
    for operation, count in stats.items():
        if count > 0:
            messages.append(f"{operation} {count} {component_type}")
    
    return "; ".join(messages).capitalize() if messages else f"No changes made to {component_type}"


async def build_comparison_data(unified_components, unified_templates):
    """Build comparison data for template rendering"""
    # Combine and sort components and templates
    overall_items = list(set(unified_templates + unified_components))
    overall_items.sort(key=lambda o: natural_keys(o.name))
    
    comparison_templates = []
    comparison_components = []
    
    # Build parallel lists for template rendering
    for item in overall_items:
        # Find matching template
        try:
            template_match = unified_templates[unified_templates.index(item)]
            comparison_templates.append(template_match)
        except ValueError:
            comparison_templates.append(None)
            
        # Find matching component
        try:
            component_match = unified_components[unified_components.index(item)]
            comparison_components.append(component_match)
        except ValueError:
            comparison_components.append(None)
    
    return list(zip(comparison_templates, comparison_components))


def parse_form_ids(request, field_name: str) -> List[int]:
    """Parse and validate IDs from form submission"""
    raw_values = request.POST.getlist(field_name)
    return [int(x) for x in raw_values if x.isdigit()]


def filter_valid_ids(ids: List[int], valid_ids_qs) -> List[int]:
    """Filter IDs to only include those that exist in the queryset"""
    valid_ids = set(valid_ids_qs.values_list('id', flat=True))
    return [id for id in ids if id in valid_ids]