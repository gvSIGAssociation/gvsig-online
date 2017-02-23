from django import forms
from django.utils.translation import ugettext as _
from gvsigol_core.models import Project

class DirectoryPath(forms.Form):
    #name = forms.CharField(label=_(u'Provider name'), widget=forms.TextInput(attrs={ 'id': 'id_provider', 'class' : 'form-control', 'tabindex': '1'}))
    projects = forms.ModelChoiceField(label=_(u'Project'), required=True, queryset=Project.objects.all(), widget=forms.Select(attrs={'class':'form-control'}))
    directory_path = forms.CharField(label=_(u'Directory name'), widget=forms.TextInput(attrs={ 'id': 'id_directory', 'class' : 'form-control', 'tabindex': '1'}))
