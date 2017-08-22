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
@author: Javier Rodrigo <jrodrigo@scolab.es>
'''

from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import ugettext as _
from django.contrib.auth.models import User
from django import forms

class UserCreateForm(UserCreationForm):
    first_name = forms.CharField(required=True, max_length=150, widget=forms.TextInput(attrs={'class' : 'form-control', 'placeholder': _('First name'), 'tabindex': '1'}))
    last_name = forms.CharField(required=True, max_length=150, widget=forms.TextInput(attrs={'class' : 'form-control', 'placeholder': _('Last name'), 'tabindex': '2'}))
    username = forms.CharField(required=True, max_length=150, widget=forms.TextInput(attrs={'class' : 'form-control', 'placeholder': _('Username'), 'tabindex': '3'}))
    email = forms.EmailField(required=True, widget=forms.TextInput(attrs={'class' : 'form-control', 'placeholder': _('Email'), 'tabindex': '4'}))
    password1 = forms.CharField(required=True, widget=forms.PasswordInput(attrs={'class' : 'form-control', 'placeholder': _('Password'), 'tabindex': '5'}))
    password2 = forms.CharField(required=True, widget=forms.PasswordInput(attrs={'class' : 'form-control', 'placeholder': _('Repeat password'), 'tabindex': '6'}))

    class Meta:
        model = User
        fields = ("first_name", "last_name", "username", "email", "password1", "password2", "is_superuser", "is_staff")

    def save(self, commit=True):
        user = super(UserCreateForm, self).save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.is_superuser = self.cleaned_data["is_superuser"]
        user.is_staff = self.cleaned_data["is_staff"]
        if commit:
            user.save()
        return user

class UserGroupForm(forms.Form):   
    name = forms.CharField(required=True, max_length=150, widget=forms.TextInput(attrs={'class' : 'form-control', 'tabindex': '1'}))
    description = forms.CharField(required=False, max_length=500, widget=forms.TextInput(attrs={'class' : 'form-control', 'tabindex': '2'})) 