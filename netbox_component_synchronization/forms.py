from django import forms


class ComponentComparisonForm(forms.Form):
    add_to_device = forms.BooleanField(required=False)
    remove_from_device = forms.BooleanField(required=False)
    fix_name = forms.BooleanField(required=False)
    
    # Sync status toggle
    show_sync_status = forms.BooleanField(required=False)
