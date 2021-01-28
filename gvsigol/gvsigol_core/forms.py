'''
Created on 17 jul. 2020

@author: Cesar Martinez Izquierdo
'''

from django import forms
from django.core.validators import RegexValidator
from django.utils.translation import ugettext_lazy as _
from gvsigol_core.models import Project
from gvsigol_services.models import Workspace, Server, CLONE_PERMISSION_CLONE, CLONE_PERMISSION_SKIP
from gvsigol_services import utils as services_utils

PERMISSION_CHOICES = (
    (CLONE_PERMISSION_CLONE, _("Clone project and layer permissions")),
    (CLONE_PERMISSION_SKIP, _("Don't apply any permission. Cloned layers will become public")),
    )

class CloneProjectForm(forms.Form):
    project_title = forms.CharField(required=True,
                                    widget=forms.TextInput(attrs={'placeholder': _("New project title"), 'class': 'form-control'}))
    project_name = forms.CharField(required=True,
                            validators=[
                                RegexValidator(
                                    regex='^[a-z0-9][a-z0-9_]*$',
                                    message=_('must start by a lower case alphanumeric and contain lower case alphanumerics or underscores')
                                ),
                            ],widget=forms.TextInput(attrs={'placeholder': _("New project name"), 'class': 'form-control'}))
    target_workspace = forms.CharField(required=True,
                                        validators=[
                                            RegexValidator(
                                                regex='^[a-z0-9][a-z0-9_]*$',
                                                message=_('must start by a lower case alphanumeric and contain lower case alphanumerics or underscores')
                                            ),
                                        ],
                                        max_length=63,widget=forms.TextInput(attrs={'placeholder': _('Target workspace name'), 'class': 'form-control'}))
    target_datastore = forms.CharField(required=True,
                                        validators=[
                                            RegexValidator(
                                                regex='^[a-z0-9][a-z0-9_]*$',
                                                message=_('must start by a lower case alphanumeric and contain lower case alphanumerics or underscores')
                                            ),
                                        ],
                                        max_length=63,widget=forms.TextInput(attrs={'placeholder': _('Target datastore and database schema name'), 'class': 'form-control'}))
    target_server = forms.CharField(required=True,
                            validators=[
                                RegexValidator(
                                    regex='^[0-9]+$',
                                    message=_('numeric value required')
                                ),
                            ])
    copy_data = forms.BooleanField(required=False, initial=False)
    permission_choice = forms.ChoiceField(required=True, choices=PERMISSION_CHOICES, initial=CLONE_PERMISSION_CLONE, widget=forms.Select(attrs={'class':'form-control'}))

    def clean_project_name(self):
        data = self.cleaned_data['project_name']
        if Project.objects.filter(name=data).exists():
            self.add_error('project_name', _('Project exists'))
        return data
    def clean_target_workspace(self):
        data = self.cleaned_data['target_workspace']
        if Workspace.objects.filter(name=data).exists():
            self.add_error('target_workspace', _('Workspace exists'))
        return data
    def clean_target_datastore(self):
        data = self.cleaned_data['target_datastore']
        if services_utils.check_schema_exists(data):
            self.add_error('target_datastore', _('Database schema exists'))
        return data
    def clean_target_server(self):
        data = self.cleaned_data['target_server']
        try:
            data = Server.objects.get(pk=data)
        except:
            self.add_error("target_server", _('Server does not exist'))
        return data
    