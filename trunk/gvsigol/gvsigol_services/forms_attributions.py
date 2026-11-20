# -*- coding: utf-8 -*-

'''
    gvSIG Online.
    Copyright (C) 2010-2026 SCOLAB.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.
'''

import json

from django import forms
from django.core.exceptions import ValidationError
from django.utils.html import strip_tags
from django.utils.translation import gettext_lazy as _

from .models import AttributionConfig
from .utils import normalize_attributions_modal_section_order


class AttributionConfigForm(forms.ModelForm):
    """
    Formulario principal de la configuración de atribuciones. Cubre la
    información general, el tipo (genérico/proyecto específico), la asociación
    con proyectos y los bloques de copyright y contacto. Los enlaces y los
    adjuntos se gestionan aparte directamente desde la vista (listas dinámicas
    en el template).
    """

    modal_section_order_json = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={'id': 'id_modal_section_order_json'}),
    )

    class Meta:
        model = AttributionConfig
        fields = [
            'name',
            'description',
            'other_title',
            'other_text',
            'logo_internal_path',
            'logo_public_url',
            'kind',
            'project',
            'apply_to_all_projects',
            'is_active',
            'copyright_notice',
            'help_text',
            'contact_organization',
            'contact_person',
            'contact_address',
            'contact_phone',
            'contact_email',
            'legal_notice',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 150}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 500}),
            'other_title': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 150}),
            'other_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'logo_internal_path': forms.TextInput(attrs={'class': 'form-control'}),
            'logo_public_url': forms.TextInput(attrs={'class': 'form-control'}),
            'kind': forms.Select(attrs={'class': 'form-control', 'id': 'id_attr_kind'}),
            'project': forms.Select(attrs={'class': 'form-control', 'id': 'id_attr_project'}),
            'apply_to_all_projects': forms.CheckboxInput(attrs={'id': 'id_attr_apply_all'}),
            'is_active': forms.CheckboxInput(),
            'copyright_notice': forms.Textarea(attrs={'class': 'form-control', 'rows': 6}),
            'help_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 6}),
            'contact_organization': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_address': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_email': forms.TextInput(attrs={'class': 'form-control'}),
            'legal_notice': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }
        labels = {
            'name': _('Title'),
            'description': _('Description'),
            'other_title': _('Custom title'),
            'other_text': _('Custom text'),
            'logo_internal_path': _('Logo internal path'),
            'logo_public_url': _('Logo public URL'),
            'kind': _('Type'),
            'project': _('Associated project'),
            'apply_to_all_projects': _('Active for all projects'),
            'is_active': _('Enabled'),
            'copyright_notice': _('Copyright notice'),
            'help_text': _('Help'),
            'contact_organization': _('Organization'),
            'contact_person': _('Contact person'),
            'contact_address': _('Address'),
            'contact_phone': _('Phone'),
            'contact_email': _('Email'),
            'legal_notice': _('Legal notice'),
        }
        help_texts = {
            'description': _('Use this field to briefly contextualize the attributions. '
                             'A common use case is to present licensing notes.'),
            'copyright_notice': _('Free text shown to viewer users. HTML tags are not allowed.'),
            'help_text': _('Help text shown to viewer users. HTML tags are not allowed.'),
            'other_text': _('Optional custom block shown in the modal between copyright and help. '
                            'HTML tags are not allowed.'),
            'legal_notice': _('Plain text legal information. HTML tags are not allowed.'),
            'apply_to_all_projects': _('When this generic configuration is enabled for all projects '
                                       'it is used as the default attributions whenever no project '
                                       'specific configuration exists.'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['modal_section_order_json'].initial = json.dumps(
                normalize_attributions_modal_section_order(self.instance.modal_section_order)
            )

    def clean_modal_section_order_json(self):
        raw = self.cleaned_data.get('modal_section_order_json')
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            return normalize_attributions_modal_section_order([])
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
            except ValueError:
                raise ValidationError(_('Invalid section order data.'))
            return normalize_attributions_modal_section_order(parsed)
        return normalize_attributions_modal_section_order(raw)

    def save(self, commit=True):
        instance = super().save(commit=False)
        order = self.cleaned_data.get('modal_section_order_json')
        if order is not None:
            instance.modal_section_order = order
        if commit:
            instance.save()
        return instance

    def clean(self):
        cleaned = super().clean()
        kind = cleaned.get('kind')
        project = cleaned.get('project')
        apply_all = cleaned.get('apply_to_all_projects')

        if kind == AttributionConfig.KIND_PROJECT_SPECIFIC:
            if project is None:
                raise ValidationError({'project': _('A project must be selected for project specific configurations.')})
            cleaned['apply_to_all_projects'] = False

            qs = AttributionConfig.objects.filter(
                kind=AttributionConfig.KIND_PROJECT_SPECIFIC,
                project=project,
            )
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError({'project': _('A project specific attributions configuration already exists for this project.')})
        else:
            cleaned['project'] = None
            if apply_all is None:
                cleaned['apply_to_all_projects'] = False

        text_fields = [
            'name',
            'description',
            'other_title',
            'other_text',
            'logo_internal_path',
            'logo_public_url',
            'copyright_notice',
            'help_text',
            'contact_organization',
            'contact_person',
            'contact_address',
            'contact_phone',
            'contact_email',
            'legal_notice',
        ]
        for field_name in text_fields:
            value = cleaned.get(field_name)
            if value is None:
                continue
            # Requirement: no attributions form field must support HTML.
            if strip_tags(value) != value:
                raise ValidationError({
                    field_name: _('HTML tags are not allowed in this field.')
                })

        logo_internal = (cleaned.get('logo_internal_path') or '').strip()
        logo_public = (cleaned.get('logo_public_url') or '').strip()
        if logo_internal and not logo_public:
            from . import utils as services_utils
            cleaned['logo_public_url'] = services_utils.build_attributions_public_url(logo_internal) or ''

        return cleaned
