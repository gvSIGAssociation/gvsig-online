from django import forms
from gvsigol_plugin_sentilo.models import SentiloConfiguration

class SentiloConfigurationForm(forms.ModelForm):
    class Meta:
        model = SentiloConfiguration
        fields = '__all__'
