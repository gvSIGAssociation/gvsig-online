# -*- coding: utf-8 -*-

'''
    gvSIG Online.
    Copyright (C) 2007-2015 gvSIG Association.

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
from django.shortcuts import render_to_response, RequestContext
from django.core.mail import send_mail
from django.utils.translation import ugettext as _
from models import UserGroup, UserGroupUser
import gvsigol.settings

def superuser_required(function):
    def wrap(request, *args, **kwargs):
        if request.user.is_superuser:
            return function(request, *args, **kwargs)
        else:
            return render_to_response('illegal_operation.html', {}, context_instance=RequestContext(request))

    wrap.__doc__=function.__doc__
    wrap.__name__=function.__name__
    return wrap

def staff_required(function):
    def wrap(request, *args, **kwargs):
        if request.user.is_staff:
            return function(request, *args, **kwargs)
        else:
            return render_to_response('illegal_operation.html', {}, context_instance=RequestContext(request))

    wrap.__doc__=function.__doc__
    wrap.__name__=function.__name__
    return wrap

def is_superuser(user):            
    return user.is_superuser

def get_all_groups():
    groups_list = UserGroup.objects.all()
    
    groups = []
    for g in groups_list:
        if g.name != 'admin':
            group = {}
            group['id'] = g.id
            group['name'] = g.name
            group['description'] = g.description
            groups.append(group)
        
    return groups

def get_all_groups_checked_by_user(user):
    groups_list = UserGroup.objects.all()
    groups_by_user = UserGroupUser.objects.filter(user_id=user.id)
    checked = False
    
    groups = []
    for g in groups_list:
        if g.name != 'admin':
            group = {}
            for gbu in groups_by_user:
                if gbu.user_group_id == g.id:
                    checked = True
                    group['checked'] = checked
                           
            group['id'] = g.id
            group['name'] = g.name
            group['description'] = g.description
            groups.append(group)
        
    return groups
        
def sendMail(user, password):
            
    subject = _(u'New user account')
    
    first_name = ''
    last_name = ''
    try:
        first_name = unicode(user.first_name, 'utf-8')
        
    except TypeError:
        first_name = user.first_name
        
    try:
        last_name = unicode(user.last_name, 'utf-8')
        
    except TypeError:
        last_name = user.last_name
    
    body = _(u'Account data') + ':\n\n'   
    body = body + '  - ' + _(u'Username') + ': ' + user.username + '\n'
    body = body + '  - ' + _(u'First name') + ': ' + first_name + '\n'
    body = body + '  - ' + _(u'Last name') + ': ' + last_name + '\n'
    body = body + '  - ' + _(u'Email') + ': ' + user.email + '\n'
    body = body + '  - ' + _(u'Password') + ': ' + password + '\n'
    
    toAddress = [user.email]           
    fromAddress = gvsigol.settings.EMAIL_HOST_USER
    send_mail(subject, body, fromAddress, toAddress, fail_silently=False)
    
def send_reset_password_email(email, temp_pass):
            
    subject = _(u'New password')
    
    body = _(u'This is your new temporary password') + ':\n\n'
    
    body = body + '  - ' + _(u'Password') + ': ' + temp_pass + '\n\n'
    
    toAddress = [email]           
    fromAddress = gvsigol.settings.EMAIL_HOST_USER
    send_mail(subject, body, fromAddress, toAddress, fail_silently=False)