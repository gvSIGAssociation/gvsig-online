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
from gvsigol_services.backend_mapservice import backend as mapservice_backend
from gvsigol_services import utils as services_utils
from gvsigol_services.models import Workspace
import random, string
from utils import superuser_required, staff_required
import utils as auth_utils
import json
from gvsigol.settings import GVSIGOL_LDAP, LOGOUT_PAGE_URL, AUTH_WITH_REMOTE_USER

def login_user(request):
    if request.user.is_authenticated():
        logout_user(request)
        print "TEST 1"
        
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
                print "TEST 2"
                return redirect('home')
            
            else:
                errors.append({'message': _("Your account has been disabled")})
                return render_to_response('login.html', {'errors': errors}, RequestContext(request))
        else:
            errors.append({'message': _("The username and password you have entered do not match our records")})
            return render_to_response('login.html', {'errors': errors}, RequestContext(request))
        
    else:
        if AUTH_WITH_REMOTE_USER:
            if "HTTP_REMOTE_USER" in request.META:
                print request.META['HTTP_REMOTE_USER']
                request.session['username'] = None
                request.session['password'] = None
                user = authenticate(remote_user=request.META['HTTP_REMOTE_USER'])
                if user is not None:
                    if user.is_active:
                        login(request, user)
                        return redirect('home')
            
        else:
            '''
            user = authenticate(remote_user="admin")
            request.session['username'] = None
            request.session['password'] = None
            if user is not None:
                if user.is_active:
                    login(request, user)
                    return redirect('home')
            '''
            return render_to_response('login.html', {'errors': errors}, RequestContext(request))

def logout_user(request):
    logout(request)
    return redirect(LOGOUT_PAGE_URL)

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
@staff_required
def user_list(request):
    
    users_list = User.objects.exclude(username='admin')
    
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
        user['is_superuser'] = u.is_superuser
        user['is_staff'] = u.is_staff
        user['email'] = u.email
        user['groups'] = groups
        users.append(user)
                      
    response = {
        'users': users
    }     
    return render_to_response('user_list.html', response, context_instance=RequestContext(request))

@login_required(login_url='/gvsigonline/auth/login_user/')
@superuser_required
def user_add(request):        
    ad_suffix = GVSIGOL_LDAP['AD']
    if not ad_suffix:
        show_pass_form = True
    else:
        show_pass_form = False
        
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():            
            assigned_groups = []
            
            is_staff = False
            if 'is_staff' in form.data:
                is_staff = True
                
            is_superuser = False
            if 'is_superuser' in form.data:
                is_superuser = True
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
                        is_superuser = is_superuser,
                        is_staff = is_staff
                    )
                    user.set_password(form.data['password1'])
                    user.save()
                    
                    admin_group = UserGroup.objects.get(name__exact='admin')
                    if user.is_superuser:
                        core_services.ldap_add_user(user, form.data['password1'], True)                        
                        core_services.ldap_add_group_member(user, admin_group)
                        usergroup_user = UserGroupUser(
                            user = user,
                            user_group = admin_group
                        )
                        usergroup_user.save()
                        
                    else:
                        core_services.ldap_add_user(user, form.data['password1'], False)
                        core_services.ldap_add_group_member(user, admin_group)
                        
                    for ag in assigned_groups:
                        user_group = UserGroup.objects.get(id=ag)
                        usergroup_user = UserGroupUser(
                            user = user,
                            user_group = user_group
                        )
                        usergroup_user.save()
                        core_services.ldap_add_group_member(user, user_group)
                     
                    #User backend 
                    if is_superuser or is_staff:  
                        ugroup = UserGroup(
                            name = 'ug_' + form.data['username'],
                            description = _(u'User group for') + ': ' + form.data['username']
                        )
                        ugroup.save()
                        
                        ugroup_user = UserGroupUser(
                            user = user,
                            user_group = ugroup
                        )
                        ugroup_user.save()
                            
                        core_services.ldap_add_group(ugroup)
                        core_services.add_data_directory(ugroup)
                        core_services.ldap_add_group_member(user, ugroup)
                        
                        url = mapservice_backend.getBaseUrl() + '/'
                        ws_name = 'ws_' + form.data['username']
                        
                        if mapservice_backend.createWorkspace(
                            ws_name,
                            url + ws_name,
                            '',
                            url + ws_name + '/wms',
                            url + ws_name + '/wfs',
                            url + ws_name + '/wcs',
                            url + 'gwc/service/wms'):
                                
                            # save it on DB if successfully created
                            newWs = Workspace(
                                name = ws_name,
                                description = '',
                                uri = url + ws_name,
                                wms_endpoint = url + ws_name + '/wms',
                                wfs_endpoint = url + ws_name + '/wfs',
                                wcs_endpoint = url + ws_name + '/wcs',
                                cache_endpoint = url + 'gwc/service/wms',
                                created_by = user.username
                            )
                            newWs.save()
                            
                            ds_name = 'ds_' + form.data['username']
                            services_utils.create_datastore(request, user.username, ds_name, newWs)
                            
                            mapservice_backend.reload_nodes()
                        
                        
                    auth_utils.sendMail(user, form.data['password1'])
    
                    return redirect('user_list')
            
            except Exception as e:
                print str(e)
                errors = []
                errors.append({'message': _("The username already exists")})
                groups = auth_utils.get_all_groups()
                return render_to_response('user_add.html', {'form': form, 'groups': groups, 'errors': errors,'show_pass_form':show_pass_form}, context_instance=RequestContext(request))

        else:
            groups = auth_utils.get_all_groups()
            return render_to_response('user_add.html', {'form': form, 'groups': groups, 'show_pass_form':show_pass_form}, context_instance=RequestContext(request))
        
    else:
        
        form = UserCreateForm()
        groups = auth_utils.get_all_groups()
        return render_to_response('user_add.html', {'form': form, 'groups': groups, 'show_pass_form':show_pass_form}, context_instance=RequestContext(request))
    
    
@login_required(login_url='/gvsigonline/auth/login_user/')
@superuser_required
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
            
        is_superuser = False
        if 'is_superuser' in request.POST:
            is_superuser = True
            is_staff = True
            
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.email = request.POST.get('email')
        user.is_staff = is_staff
        user.save()
        
        if user.is_superuser and is_superuser:
            admin_group = UserGroup.objects.get(name__exact='admin')
            assigned_groups.append(admin_group.id)
            
        if not user.is_superuser and is_superuser:
            user.is_superuser = True
            user.save()
            admin_group = UserGroup.objects.get(name__exact='admin')
            core_services.ldap_add_group_member(user, admin_group)
            assigned_groups.append(admin_group.id)
        
        if user.is_superuser and not is_superuser:
            user.is_superuser = False
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
        selected_user = User.objects.get(id=int(uid))    
        groups = auth_utils.get_all_groups_checked_by_user(selected_user)
        return render_to_response('user_update.html', {'uid': uid, 'selected_user': selected_user, 'user': request.user, 'groups': groups}, context_instance=RequestContext(request))
        
        
@login_required(login_url='/gvsigonline/auth/login_user/')
@superuser_required
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
@superuser_required
def group_list(request):
    
    groups_list = UserGroup.objects.exclude(name='admin')
    
    groups = []
    for g in groups_list:
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
@superuser_required
def group_add(request):        
    if request.method == 'POST':
        form = UserGroupForm(request.POST)
        if form.is_valid():
            try:
                if form.data['name'] == 'admin':
                    raise Exception
                
                group = UserGroup(
                    name = form.data['name'],
                    description = form.data['description']
                )
                group.save()
                    
                core_services.ldap_add_group(group)
                core_services.add_data_directory(group)                               
                          
                return redirect('group_list')
            
            except Exception as e:
                print str(e)
                message = _("Admin is a reserved group")
                return render_to_response('group_add.html', {'form': form, 'message': message}, context_instance=RequestContext(request))
                
        else:
            return render_to_response('group_add.html', {'form': form}, context_instance=RequestContext(request))
        
    else:
        form = UserGroupForm()
        return render_to_response('group_add.html', {'form': form}, context_instance=RequestContext(request))
         
        
@login_required(login_url='/gvsigonline/auth/login_user/')
@superuser_required
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
