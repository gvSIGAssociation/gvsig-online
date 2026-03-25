from django import forms
from django.utils.translation import gettext as _

class DirectoryCreateForm(forms.Form):
    directory_name = forms.CharField(label=_('Directory name'), widget=forms.TextInput(attrs={'class' : 'form-control', 'tabindex': '1'}))
