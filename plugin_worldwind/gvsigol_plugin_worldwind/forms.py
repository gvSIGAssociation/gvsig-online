from django import forms
from django.utils.translation import ugettext as _
from gvsigol_core.models import Project

class DirectoryPath(forms.Form):
    #name = forms.CharField(label=_(u'Provider name'), widget=forms.TextInput(attrs={ 'id': 'id_provider', 'class' : 'form-control', 'tabindex': '1'}))
    TYPE_CHOICES = [
        ('url', 'Url'),
        ('mapserver', 'Mapserver')
    ]

    projects = forms.ModelChoiceField(label=_('Project'), required=True, queryset=Project.objects.all(), widget=forms.Select(attrs={'class':'form-control'}))
    type = forms.ChoiceField(label=_('Type'), required=True, 
                             choices = TYPE_CHOICES, widget=forms.Select(attrs={'class':'form-control'}))
    directory_path = forms.CharField(label=_('Directory name'), required=False, widget=forms.TextInput(attrs={ 'id': 'id_directory', 'class' : 'form-control', 'tabindex': '1'}))
    heightUrl = forms.CharField(label=_('Url to get height'), required=False, widget=forms.TextInput(attrs={ 'id': 'id_heightUrl', 'class' : 'form-control', 'tabindex': '2'}))
    layers = forms.CharField(label=_('layers'), required=False, widget=forms.TextInput(attrs={ 'id': 'id_layers', 'class' : 'form-control', 'tabindex': '3'}))

