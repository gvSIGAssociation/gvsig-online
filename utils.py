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
from django.core.mail import send_mail
from django.utils.translation import ugettext as _
from gvsigol_core.models import Project, ProjectUserGroup, ProjectLayerGroup
from gvsigol_services.models import LayerGroup
from gvsigol_auth.models import UserGroup, UserGroupUser
import gvsigol.settings

def is_valid_project(user, pid):
    valid = False
    try:
        project = Project.objects.get(id=int(pid))   
        groups_by_user = UserGroupUser.objects.filter(user_id=user.id)
        
        projects_by_user = []
        for usergroup_user in groups_by_user:
            user_group = UserGroup.objects.get(id=usergroup_user.user_group_id)
            projects_by_group = ProjectUserGroup.objects.filter(user_group_id=user_group.id)
            for project_group in projects_by_group:
                exists = False
                for aux in projects_by_user:
                    if aux.project_id == project_group.project_id:
                        exists = True
                if not exists:
                    projects_by_user.append(project_group)
            
        if len (projects_by_user) > 0:
            for ua in projects_by_user:
                aux = Project.objects.get(id=ua.project_id)
                if project.id == aux.id:
                    valid = True
                    
        return valid
                    
    except Exception as e:
        print e
        return valid

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

def get_groups_by_user(user):
    groups_by_user = UserGroupUser.objects.filter(user_id=user.id)
    
    groups = []
    for g in groups_by_user:
        user_group = UserGroup.objects.get(id=g.user_group_id)
        groups.append(user_group.name)
        
    return groups

def get_all_groups_checked_by_project(project):
    groups_list = UserGroup.objects.all()
    groups_by_project = ProjectUserGroup.objects.filter(project_id=project.id)
    checked = False
    
    groups = []
    for g in groups_list:
        if g.name != 'admin':
            group = {}
            for gbu in groups_by_project:
                if gbu.user_group_id == g.id:
                    checked = True
                    group['checked'] = checked
                           
            group['id'] = g.id
            group['name'] = g.name
            group['description'] = g.description
            groups.append(group)
        
    return groups

def get_all_layer_groups_checked_by_project(project):
    groups_list = LayerGroup.objects.all()
    layer_groups_by_project = ProjectLayerGroup.objects.filter(project_id=project.id)
    checked = False
    
    layer_groups = []
    for g in groups_list:
        if g.name != '__default__':
            layer_group = {}
            for lgba in layer_groups_by_project:
                if lgba.layer_group_id == g.id:
                    checked = True
                    layer_group['checked'] = checked
                           
            layer_group['id'] = g.id
            layer_group['name'] = g.name
            layer_group['title'] = g.title
            layer_groups.append(layer_group)
        
    return layer_groups
        
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