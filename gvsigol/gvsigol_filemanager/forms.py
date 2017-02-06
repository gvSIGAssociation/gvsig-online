from django import forms
from django.utils.translation import ugettext as _

class DirectoryCreateForm(forms.Form):
    directory_name = forms.CharField(label=_(u'Directory name'), widget=forms.TextInput(attrs={'class' : 'form-control', 'tabindex': '1'}))
