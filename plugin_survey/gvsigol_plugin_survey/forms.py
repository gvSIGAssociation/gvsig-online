from django import forms
from django.utils.translation import ugettext as _
from gvsigol_core.models import Project
from gvsigol_services.models import Datastore
from models import Survey, SurveySection
from gvsigol_core import utils as core_utils

supported_srs = tuple((x['code'].replace('EPSG:',''),x['code']+' - '+x['title']) for x in core_utils.get_supported_crs_array())
supported_srs_and_blank = (('', '---------'),) + supported_srs

class SurveyForm(forms.ModelForm):
    class Meta:
        model = Survey
        fields = ['name', 'title']
    name = forms.CharField(label=_(u'Name'), required=True, max_length=100, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    title = forms.CharField(label=_(u'Title'), required=True, max_length=150, widget=forms.TextInput(attrs={'class' : 'form-control'}))
    datastore = forms.ModelChoiceField(label=_(u'Datastore'), required=True, queryset=Datastore.objects.all().order_by('name'), widget=forms.Select(attrs={'class' : 'form-control js-example-basic-single'}))
    
class SurveySectionForm(forms.ModelForm):
    class Meta:
        model = SurveySection
        fields = ['name', 'title', 'srs']
        
    name = forms.CharField(label=_(u'Name'), required=True, max_length=250, widget=forms.TextInput(attrs={'class': 'form-control', 'tabindex': '2'}))
    title = forms.CharField(label=_(u'Title'), required=True, max_length=250, widget=forms.TextInput(attrs={'class': 'form-control', 'tabindex': '2'}))
    srs = forms.ChoiceField(label=_(u'SRS'), required=False, choices=supported_srs_and_blank, widget=forms.Select(attrs={'class' : 'form-control js-example-basic-single'}))
    definition = forms.CharField(label=_(u'Definition'), required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'tabindex': '4'}))


class UploadFileForm(forms.Form):
    name = forms.ModelChoiceField(label=_(u'Name'), required=True, queryset=Survey.objects.all().order_by('name'), widget=forms.Select(attrs={'class':'form-control js-example-basic-single'}))
    fileupload = forms.FileField(label=_(u'File'), required=True, widget=forms.FileInput(attrs={'accept' : '.sqlite,.gpap'}))