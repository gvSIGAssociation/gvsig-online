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

from django.shortcuts import render_to_response, RequestContext, HttpResponse, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils.translation import ugettext as _
from forms import UserCreateForm, UserGroupForm
from models import UserGroupUser, UserGroup
from django.contrib.auth.models import User
from gvsigol_auth.services import services as core_services
import random, string
from utils import admin_required
import utils as auth_utils
import json

def login_user(request):
    if request.user.is_authenticated():
        logout_user(request)
    errors = []
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        request.session['username'] = username
        request.session['password'] = password
        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                return redirect('home')
            
            else:
                errors.append({'message': _("Your account has been disabled")})
                return render_to_response('login.html', {'errors': errors}, RequestContext(request))
        else:
            errors.append({'message': _("The username and password you have entered do not match our records")})
            return render_to_response('login.html', {'errors': errors}, RequestContext(request))
        
    return render_to_response('login.html', {'errors': errors}, RequestContext(request))

def logout_user(request):
    logout(request)
    return redirect('/gvsigonline/')

@login_required(login_url='/gvsigonline/auth/login_user/')
def password_update(request):  
    if request.method == 'POST':
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        
        if password1 == password2:
            user = User.objects.get(id=request.user.id)
            user.set_password(password1)
            user.save()
            
            core_services.ldap_change_user_password(user, password1)
            
            response = {'success': True}
            
        else:
            response = {'success': False} 
                
        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')
    
def password_reset(request):
    if request.method == 'POST':
        errors = []
        username = request.POST.get('username')
        try:
            user = User.objects.get(username__exact=username)
            temp_pass = ''.join(random.choice(string.ascii_uppercase) for i in range(6))
            user.set_password(temp_pass)
            user.save()
            core_services.ldap_change_user_password(user, temp_pass)
            auth_utils.send_reset_password_email(user.email, temp_pass)
            return redirect('password_reset_success')
            
        except:            
            errors.append(_('User account does not exist'))
            return render_to_response('password_reset.html', {'errors': errors}, RequestContext(request))
            
    else:
        return render_to_response('password_reset.html', {}, RequestContext(request))
        

def password_reset_success(request):
    return render_to_response('password_reset_success.html', {}, RequestContext(request))

@login_required(login_url='/gvsigonline/auth/login_user/')
@admin_required
def user_list(request):
    
    users_list = User.objects.all()
    
    users = []
    for u in users_list:
        groups_by_user = UserGroupUser.objects.filter(user_id=u.id)
        
        groups = ''
        for usergroup_user in groups_by_user:
            user_group = UserGroup.objects.get(id=usergroup_user.user_group_id)
            groups += user_group.name + '; '
            
        user = {}
        user['id'] = u.id
        user['username'] = u.username
        user['first_name'] = u.first_name
        user['last_name'] = u.last_name
        user['is_admin'] = u.is_staff
        user['email'] = u.email
        user['groups'] = groups
        users.append(user)
                      
    response = {
        'users': users
    }     
    return render_to_response('user_list.html', response, context_instance=RequestContext(request))

@login_required(login_url='/gvsigonline/auth/login_user/')
@admin_required
def user_add(request):        
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            assigned_groups = []
            
            is_staff = False
            if 'is_staff' in form.data:
                is_staff = True
            
            assigned_groups = []   
            for key in form.data:
                if 'group-' in key:
                    assigned_groups.append(int(key.split('-')[1]))
            
            try:   
                if form.data['password1'] == form.data['password2']:
                    user = User(
                        username = form.data['username'],
                        first_name = u''.join(form.data['first_name']).encode('utf-8'),
                        last_name = u''.join(form.data['last_name']).encode('utf-8'),
                        email = form.data['email'],
                        is_staff = is_staff,
                    )
                    user.set_password(form.data['password1'])
                    user.save()
                    
                    if user.is_staff:
                        core_services.ldap_add_user(user, form.data['password1'], True)
                        admin_group = UserGroup.objects.get(name__exact='admin')
                        core_services.ldap_add_group_member(user, admin_group)
                        usergroup_user = UserGroupUser(
                            user = user,
                            user_group = admin_group
                        )
                        usergroup_user.save()
                        
                    else:
                        core_services.ldap_add_user(user, form.data['password1'], False)
                        
                    for ag in assigned_groups:
                        user_group = UserGroup.objects.get(id=ag)
                        usergroup_user = UserGroupUser(
                            user = user,
                            user_group = user_group
                        )
                        usergroup_user.save()
                        core_services.ldap_add_group_member(user, user_group)
                        
                    auth_utils.sendMail(user, form.data['password1'])
    
                    return redirect('user_list')
            
            except Exception as e:
                print str(e)
                errors = []
                errors.append({'message': _("The username already exists")})
                groups = auth_utils.get_all_groups()
                return render_to_response('user_add.html', {'form': form, 'groups': groups, 'errors': errors}, context_instance=RequestContext(request))

        else:
            groups = auth_utils.get_all_groups()
            return render_to_response('user_add.html', {'form': form, 'groups': groups}, context_instance=RequestContext(request))
        
    else:
        form = UserCreateForm()
        groups = auth_utils.get_all_groups()
        return render_to_response('user_add.html', {'form': form, 'groups': groups}, context_instance=RequestContext(request))
    
    
@login_required(login_url='/gvsigonline/auth/login_user/')
@admin_required
def user_update(request, uid):        
    if request.method == 'POST':
        user = User.objects.get(id=int(uid))
        
        assigned_groups = []
        for key in request.POST:
            if 'group-' in key:
                assigned_groups.append(int(key.split('-')[1]))
        
        is_staff = False
        if 'is_staff' in request.POST:
            is_staff = True
            
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.email = request.POST.get('email')
        user.save()
        
        if user.is_staff and is_staff:
            admin_group = UserGroup.objects.get(name__exact='admin')
            assigned_groups.append(admin_group.id)
            
        if not user.is_staff and is_staff:
            user.is_staff = True
            user.save()
            admin_group = UserGroup.objects.get(name__exact='admin')
            core_services.ldap_add_group_member(user, admin_group)
            assigned_groups.append(admin_group.id)
        
        if user.is_staff and not is_staff:
            user.is_staff = False
            user.save()
            admin_group = UserGroup.objects.get(name__exact='admin')
            core_services.ldap_delete_group_member(user, admin_group)
        
        groups_by_user = UserGroupUser.objects.filter(user_id=user.id)
        for ugu in  groups_by_user:
            user_group = UserGroup.objects.get(id=ugu.user_group.id)
            core_services.ldap_delete_group_member(user, user_group)
            ugu.delete()
                  
        for ag in assigned_groups:
            user_group = UserGroup.objects.get(id=ag)
            usergroup_user = UserGroupUser(
                user = user,
                user_group = user_group
            )
            usergroup_user.save()
            core_services.ldap_add_group_member(user, user_group)
            
        return redirect('user_list')
                
        
    else:
        user = User.objects.get(id=int(uid))    
        groups = auth_utils.get_all_groups_checked_by_user(user)
        return render_to_response('user_update.html', {'uid': uid, 'user': user, 'groups': groups}, context_instance=RequestContext(request))
        
        
@login_required(login_url='/gvsigonline/auth/login_user/')
@admin_required
def user_delete(request, uid):        
    if request.method == 'POST':
        user = User.objects.get(id=uid)
        
        groups_by_user = UserGroupUser.objects.filter(user_id=user.id)
        for ugu in  groups_by_user:
            user_group = UserGroup.objects.get(id=ugu.user_group.id)
            core_services.ldap_delete_group_member(user, user_group)
        
        core_services.ldap_delete_default_group_member(user)   
        core_services.ldap_delete_user(user)           
        user.delete()
            
        response = {
            'deleted': True
        }     
        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')

@login_required(login_url='/gvsigonline/auth/login_user/')
@admin_required
def group_list(request):
    
    groups_list = UserGroup.objects.all()
    
    groups = []
    for g in groups_list:
        if g.name != 'admin':
            group = {}
            group['id'] = g.id
            group['name'] = g.name
            group['description'] = g.description
            groups.append(group)
                      
    response = {
        'groups': groups
    }     
    return render_to_response('group_list.html', response, context_instance=RequestContext(request))


@login_required(login_url='/gvsigonline/auth/login_user/')
@admin_required
def group_add(request):        
    if request.method == 'POST':
        form = UserGroupForm(request.POST)
        if form.is_valid():
            
            group_name = form.data['name']
            group_description = form.data['description']
            
            group = UserGroup(
                name = group_name,
                description = group_description
            )
            group.save()
                
            core_services.ldap_add_group(group)
            core_services.add_data_directory(group)                               
                      
            return redirect('group_list')
                
        else:
            return render_to_response('group_add.html', {'form': form}, context_instance=RequestContext(request))
        
    else:
        form = UserGroupForm()
        return render_to_response('group_add.html', {'form': form}, context_instance=RequestContext(request))
         
        
@login_required(login_url='/gvsigonline/auth/login_user/')
@admin_required
def group_delete(request, gid):        
    if request.method == 'POST':
        group = UserGroup.objects.get(id=int(gid))
        
        core_services.ldap_delete_group(group)           
        core_services.delete_data_directory(group)
        
        group.delete()
            
        response = {
            'deleted': True
        }     
        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')
