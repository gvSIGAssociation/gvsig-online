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
from django.shortcuts import render
from django.core.mail import send_mail
from django.utils.translation import ugettext as _
from gvsigol.services_base import BackendNotAvailable
import gvsigol.settings
from functools import wraps
from django.contrib.auth.models import User
from gvsigol.utils import default_sorter
from gvsigol_auth import auth_backend
import logging
import re

LOGGER_NAME = 'gvsigol'

def superuser_required(function):
    def wrap(request, *args, **kwargs):
        if request.user.is_superuser:
            return function(request, *args, **kwargs)
        else:
            return render(request, 'illegal_operation.html', {})

    wrap.__doc__=function.__doc__
    wrap.__name__=function.__name__
    return wrap

def staff_required(function):
    @wraps(function)
    def wrap(request, *args, **kwargs):
        if request.user.is_staff:
            return function(request, *args, **kwargs)
        else:
            return render(request, 'illegal_operation.html', {})
    return wrap

def is_superuser(user):
    return user.is_superuser

def is_staff(user):
    return user.is_staff

def get_all_groups_checked_by_user(username):  # FIXME OIDC CMI
    all_groups = auth_backend.get_all_groups_details()
    user_groups = auth_backend.get_groups(username)
    groups = []
    for group in sorted(all_groups, key=default_sorter):
        for user_group_name in user_groups:
            if group['name'] == user_group_name:
                group['checked'] = True
                break
        groups.append(group)
    return groups

def get_all_roles_checked_by_user(username):  # FIXME OIDC CMI
    all_roles = auth_backend.get_all_roles_details(exclude_system=True)
    user_roles = auth_backend.get_roles(username)
    roles = []
    for role in sorted(all_roles, key=default_sorter):
        for user_role_name in user_roles:
            if role['name'] == user_role_name:
                role['checked'] = True
                break
        roles.append(role)
    return roles

def sendMail(user, password):
    if gvsigol.settings.EMAIL_BACKEND_ACTIVE:       
        subject = _('New user account')
        
        first_name = ''
        last_name = ''
        try:
            first_name = str(user.first_name, 'utf-8')
            
        except TypeError:
            first_name = user.first_name
            
        try:
            last_name = str(user.last_name, 'utf-8')
            
        except TypeError:
            last_name = user.last_name
        
        body = _('Account data') + ':\n\n'   
        body = body + '  - ' + _('Username') + ': ' + user.username + '\n'
        body = body + '  - ' + _('First name') + ': ' + first_name + '\n'
        body = body + '  - ' + _('Last name') + ': ' + last_name + '\n'
        body = body + '  - ' + _('Email') + ': ' + user.email + '\n'
        body_debug = body + '  - ' + _('Password') + ': *****' + '\n'
        body = body + '  - ' + _('Password') + ': ' + password + '\n'
        
        toAddress = [user.email]           
        fromAddress = gvsigol.settings.EMAIL_HOST_USER
        logging.getLogger(LOGGER_NAME).debug('Restore message:\n' + body_debug)
        send_mail(subject, body, fromAddress, toAddress, fail_silently=False)
    
def send_reset_password_email(email, pass_reset_url):
    if gvsigol.settings.EMAIL_BACKEND_ACTIVE:     
        subject = _('Password reset')
        
        body = _('You are receiving this email because we received a password reset request for your account.') + '\n\n'
        body += _('You can reset your password by clicking the link bellow') + ':\n\n'
        body += pass_reset_url + ' \n\n'
        body += _('If you did not request a password reset, please ignore this email. Your password will not change.') + '\n\n'
        
        toAddress = [email]           
        fromAddress = gvsigol.settings.EMAIL_HOST_USER
        
        #print 'Restore message: ' + body
        send_mail(subject, body, fromAddress, toAddress, False, gvsigol.settings.EMAIL_HOST_USER, gvsigol.settings.EMAIL_HOST_PASSWORD)

def get_primary_user_role(request):
    # FIXME CMI OIDC: ROLE_ prefix? move to auth_backend?
    if request.user and request.user.username:
        role = auth_backend.get_primary_role(request.user.username)
        if auth_backend.has_role(request, role):
            return role
    return None

def get_primary_user_role_details(request):
    role = get_primary_user_role(request)
    role_details = auth_backend.get_role_details(role)
    if role_details:
        return [role_details]
    return []
    
def ensure_admin_group():
    """
    Ensures the admin group exists and it is assigned to all superusers
    """
    try:
        admin_role = auth_backend.get_admin_role()
        if not admin_role in auth_backend.get_all_roles():
            auth_backend.add_role(admin_role)
        
        superusers = User.objects.filter(is_superuser=True)
        for user in superusers:
            if not auth_backend.has_role(user, admin_role):
                auth_backend.add_to_role(user, admin_role)
    except BackendNotAvailable:
        logging.getLogger(LOGGER_NAME).warning("Authentication backend is not available. Check configuration and connectivity")

def config_staff_user(username):
    from gvsigol_services import utils
    role = auth_backend.get_primary_role(username)
    user_role_created = auth_backend.add_role(role)
    auth_backend.add_to_role(username, role)
    utils.create_user_workspace(username, role)
    return (user_role_created, role)

def ascii_norm_username(username):
    """
    Creates a ascii-based string similar to the provided username.
    It replaces any character not beloging to [^0-9a-zA-Z]+ pattern by
    underscores (_), and @ character by '_at_' literal. Capital letters are
    converted to lower case.
    This ascii-based version of username is used to create unique resource
    names (workspaces, datastores, layer groups, etc) which don't accept
    special characters.
    """
    return re.sub('[^0-9a-zA-Z]+', '_', username.lower().replace('@', '_at_'))