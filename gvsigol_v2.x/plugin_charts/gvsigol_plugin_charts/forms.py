# -*- coding: utf-8 -*-

'''
    gvSIG Online.
    Copyright (C) 2010-2017 SCOLAB.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

'''
@author: Javi Rodrigo <jrodrigo@scolab.es>
'''

from django.utils.translation import ugettext as _
from gvsigol_services.models import Layer
from models import Chart
from django import forms

chart_types = (
    ('barchart', _('Bar Chart')),
    ('linechart', _('Line Chart')),
    ('piechart', _('Pie Chart')),
)

class ChartForm(forms.Form):
    layer = forms.ModelChoiceField(label=_(u'Layer'), required=True, queryset=Layer.objects.all().order_by('title'), widget=forms.Select(attrs={'class' : 'form-control', 'tabindex': '1'}))
    type = forms.ChoiceField(label=_(u'Type'), choices=chart_types, required=True, widget=forms.Select(attrs={'class':'form-control', 'tabindex': '2'}))  
    title = forms.CharField(label=_(u'Title'), required=True, max_length=150, widget=forms.TextInput(attrs={'class' : 'form-control', 'tabindex': '3'}))
    description = forms.CharField(label=_(u'Description'), required=False, max_length=500, widget=forms.TextInput(attrs={'class' : 'form-control', 'tabindex': '4'}))
    
    class Meta:
        model = Chart
        fields = ['layer', 'type', 'title', 'description']