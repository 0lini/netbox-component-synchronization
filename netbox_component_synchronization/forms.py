from django import forms


class ComponentComparisonForm(forms.Form):
    add_to_device = forms.BooleanField(required=False)
    remove_from_device = forms.BooleanField(required=False)
    fix_name = forms.BooleanField(required=False)
    
    # Bulk action fields
    bulk_add_missing = forms.BooleanField(required=False)
    bulk_repair_out_of_sync = forms.BooleanField(required=False)  
    bulk_remove_out_of_sync = forms.BooleanField(required=False)
    bulk_sync_all = forms.BooleanField(required=False)
    
    # Sync status toggle
    show_sync_status = forms.BooleanField(required=False)
