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
from django.http.response import JsonResponse
from gvsigol import settings
'''
@author: Javier Rodrigo <jrodrigo@scolab.es>
'''

from django.urls import reverse
from django.shortcuts import render, HttpResponse, redirect
from django.http import HttpResponseForbidden
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils.translation import ugettext as _
from .forms import UserCreateForm, UserGroupForm
from django.contrib.auth.models import User
from gvsigol_auth import services as auth_services
from gvsigol_services import geographic_servers
from gvsigol_services import utils as services_utils
from gvsigol_services.models import Workspace, Server
from .utils import superuser_required, staff_required
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.views.decorators.csrf import ensure_csrf_cookie
from . import utils as auth_utils
import json
import re
import base64
from actstream import action
import logging
from gvsigol_core.utils import get_absolute_url
logger = logging.getLogger('gvsigol')
from gvsigol_auth import auth_backend, signals
from gvsigol.settings import GVSIGOL_LDAP, LOGOUT_REDIRECT_URL, AUTH_WITH_REMOTE_USER

_valid_name_regex=re.compile("^[a-zA-Z_][a-zA-Z0-9_]*$")

def login_user(request):
    errors = []
    if request.method == "POST":
        if request.user.is_authenticated:
            logout_user(request)
        username = request.POST.get('username')
        try:
            findUser = User.objects.get(username=username)
        except User.DoesNotExist:
            findUser = None
        if findUser is not None:
            password = request.POST.get('password')
            request.session['username'] = username
            request.session['password'] = password
            user = authenticate(username=username, password=password)
            if user is not None:
                if user.is_active:
                    login(request, user)
                    action.send(user, verb="gvsigol_auth/login")
                    next = request.POST.get('next')
                    if next:
                        response = redirect(next)
                        return response
                    else:
                        return redirect('home')
                
                else:
                    errors.append({'message': _("Your account has been disabled")})
            else:
                errors.append({'message': _("The username and password you have entered do not match our records")})
        else:
            errors.append({'message': _("The username and password you have entered do not match our records")})
        
    else:
        if AUTH_WITH_REMOTE_USER:
            if "HTTP_REMOTE_USER" in request.META:
                if settings.DEBUG == True:
                    print("HTTP_REMOTE_USER: " + request.META['HTTP_REMOTE_USER'])
                request.session['username'] = None
                request.session['password'] = None
                user = authenticate(remote_user=request.META['HTTP_REMOTE_USER'])
                if user is not None:
                    if user.is_active:
                        login(request, user)
                        return redirect('home')
            elif 'HTTP_AUTHORIZATION' in request.META:
                auth = request.META['HTTP_AUTHORIZATION'].split()
                if len(auth) == 2:
                    if auth[0].lower() == "basic":
                        uname, passwd = base64.b64decode(auth[1]).split(':')
                        user = authenticate(username=uname, password=passwd)
                        request.session['username'] = uname
                        request.session['password'] = passwd
                        if user is not None:
                            if user.is_active:
                                login(request, user)
                                request.user = user
                                return redirect('home')
            elif 'HTTP_OIDC_CLAIM_SUB' in request.META:
                if settings.DEBUG == True:
                        print("HTTP_OIDC_CLAIM_SUB: " + request.META['HTTP_OIDC_CLAIM_SUB'])
                request.session['username'] = None
                request.session['password'] = None
                aux = request.META['HTTP_OIDC_CLAIM_SUB']
                if "\\" in aux:
                        aux = aux.split("\\")[1]
                aux = aux.lower()
                user = authenticate(remote_user=aux)
                if user is not None:
                    if user.is_active:
                        login(request, user)
                        return redirect('home')

        else:
            username = request.GET.get('usu')
            try:
                findUser = User.objects.get(username=username)
            except User.DoesNotExist:
                findUser = None
            password = request.GET.get('pass')
            if findUser is not None or password is not None:
                if findUser is not None:
                    request.session['username'] = username
                    request.session['password'] = password
                    user = authenticate(username=username, password=password)
                    if user is not None:
                        if user.is_active:
                            login(request, user)
                            id_solicitud = request.GET.get('id_solicitud')
                            expediente = request.GET.get('expediente')
                            app = request.GET.get('app')
                            token = request.GET.get('token')
                            next = request.GET.get('next')
                            if id_solicitud is not None and app is not None:
                                response = redirect(next)
                                if token is None:
                                    response['Location'] += '?id_solicitud=' + id_solicitud + '&app=' + app
                                else:
                                    response['Location'] += '?id_solicitud=' + id_solicitud + '&app=' + app + '&token=' + token
                                return response

                            if expediente is not None:
                                response = redirect(next)
                                if token is None:
                                    response['Location'] += '?expediente=' + expediente
                                else:
                                    response['Location'] += '?expediente=' + expediente + '&token=' + token
                                return response
                            if next is not None:
                                return redirect(next)

                        else:
                            errors.append({'message': _("Your account has been disabled")})
                    else:
                        errors.append({'message': _("The username and password you have entered do not match our records")})
                else:
                    errors.append({'message': _("The username and password you have entered do not match our records")})

    external_ldap_mode = True
    if 'AD' in GVSIGOL_LDAP and GVSIGOL_LDAP['AD'].__len__() > 0:
        external_ldap_mode = False
    return render(request, 'login.html', {'errors': errors, 'external_ldap_mode': external_ldap_mode})

@ensure_csrf_cookie
def rest_session_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        try:
            findUser = User.objects.get(username=username)
            password = request.POST.get('password')
            request.session['username'] = username
            request.session['password'] = password
            user = authenticate(username=username, password=password)
            if user is not None:
                if user.is_active:
                    login(request, user)
                    action.send(user, verb="gvsigol_auth/login")
                    response = {'success': True}
                    return HttpResponse(json.dumps(response, indent=4), content_type='application/json')
                else:
                    return HttpResponseForbidden("Your account has been disabled")
        except:
            pass
        return HttpResponseForbidden("The username and password you have entered do not match our records")
    # non post requests
    return JsonResponse({"user": request.user.username})

def logout_user(request):
    logout(request)
    return redirect(LOGOUT_REDIRECT_URL)

@login_required()
def password_update(request):  
    if request.method == 'POST':
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        
        if password1 == password2:
            user = User.objects.get(id=request.user.id)
            user.set_password(password1)
            user.save()
            
            auth_services.get_services().ldap_change_user_password(user, password1)
            
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
            
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token =  default_token_generator.make_token(user)

            pass_reset_url = reverse('password_reset_confirmation', kwargs={'user_id': user.id, 'uid': uid, 'token': token})
            pass_reset_url = get_absolute_url(pass_reset_url, request.META)
            auth_utils.send_reset_password_email(user.email, pass_reset_url)
            return redirect('password_reset_success')
        except User.DoesNotExist:
            logger.exception("Error resetting password")
            errors.append(_('User account does not exist'))
            return render(request, 'password_reset.html', {'errors': errors})
        except Exception:
            logger.exception("Error resetting password")
            errors.append(_('That did not work'))
            return render(request, 'password_reset.html', {'errors': errors})
            
    else:
        if 'AD' in GVSIGOL_LDAP and GVSIGOL_LDAP['AD'].__len__() > 0:
            return redirect('login_user')
        return render(request, 'password_reset.html', {})



def password_reset_confirmation(request, user_id, uid, token):
    context = {
        'user_id' : user_id,
        'uid': uid,
        'token': token
        }
            
    return render(request, 'registration/password_reset_confirm.html', context)
       

def password_reset_complete(request):
    """
    View that checks the hash in a password reset link and presents a
    form for entering a new password.
    """
    user_id = request.POST.get('user_id')
    token = request.POST.get('token')

    user = User.objects.get(id=user_id)

    errors = ''
    
    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            temp_pass = request.POST.get('password')
            user.set_password(temp_pass)
            user.save()
            auth_services.get_services().ldap_change_user_password(user, temp_pass)
            
            request.session['username'] = user.username
            request.session['password'] = temp_pass
            user = authenticate(username=user.username, password=temp_pass)
            if user is not None:
                if user.is_active:
                    login(request, user)
                    return redirect('home')
                
                else:
                    errors = _("Your account has been disabled")
            else:
                errors = _("The username and password you have entered do not match our records")


    else:
        errors =  _('Invalid token. Your link has expired, you need to ask for another one.')
            
    return render(request, 'registration/password_reset_confirm.html', {'errors': errors})
       



def password_reset_success(request):
    return render(request, 'password_reset_success.html', {})

@login_required()
@superuser_required
def user_list(request):
    users = auth_backend.get_users_details(exclude_system=True)
    for user in users:
        user["roles"] = "; ".join(user["roles"])
                      
    response = {
        'users': users
    }     
    return render(request, 'user_list.html', response)

@login_required()
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
            
            # flag what has been done to be able to revert if needed
            user_created = False
            user_group_created = False
            role_membership_added = []
            user_role_created = False
            user = None
            try:
                assigned_roles = []   
                for key in form.data:
                    if 'group-' in key:
                        assigned_roles.append(key[len('group-'):])
            
                gs = geographic_servers.get_instance().get_default_server()
                server_object = Server.objects.get(id=int(gs.id))
                                
                if form.data['password1'] == form.data['password2']:
                    user = auth_backend.add_user(
                        form.data['username'].lower(),
                        form.data['password1'],
                        form.data['email'].lower(),
                        form.data['first_name'],
                        form.data['last_name'],
                        superuser=is_superuser,
                        staff=is_staff
                    )
                    user_created = True

                    if user.is_superuser:
                        admin_role = auth_backend.get_admin_role()
                        if auth_backend.add_to_role(user, admin_role):
                            role_membership_added.append(admin_role)
                        
                    for role in assigned_roles:
                        if auth_backend.add_to_role(user, role):
                            role_membership_added.append(role)
                     
                    #User backend
                    if is_superuser or is_staff:
                        role = auth_backend.get_primary_role(user.username)
                        if auth_backend.add_role(role):
                            user_role_created = True
                        """
                        try:
                            role = Role.objects.get(name=auth_backend.get_primary_role(user.username))
                        except:
                            role = Role(
                                name = auth_backend.get_primary_role(form.data['username']),
                                description = _('User group for') + ': ' + form.data['username'].lower()
                            )
                            role.save()
                            django_user_group_created = True
                        role.users.add(user)
                        """
                        """
                        if auth_services.get_services().ldap_add_group(role) != False:
                            ldap_user_group_created = True
                        """
                        auth_backend.add_to_role(user, role)
                        role_membership_added.append(role)
                        # FIXME OIDC CMI deberia hacerse solo si no existe el rol???
                        auth_services.get_services().add_data_directory(role)
                        """
                        auth_services.get_services().add_data_directory(role)
                        
                        if auth_services.get_services().ldap_add_group_member(user, role) != False:
                            ldap_group_membership_added.append(role)
                        """
                        url = server_object.frontend_url + '/'
                        ws_name = 'ws_' + form.data['username'].lower()
                        if gs.createWorkspace(ws_name, url + ws_name):          
                            # save it on DB if successfully created
                            newWs = Workspace(
                                server = server_object,
                                name = ws_name,
                                description = '',
                                uri = url + ws_name,
                                wms_endpoint = url + ws_name + '/wms',
                                wfs_endpoint = url + ws_name + '/wfs',
                                wcs_endpoint = url + ws_name + '/wcs',
                                wmts_endpoint = url + 'gwc/service/wmts',
                                cache_endpoint = url + 'gwc/service/wms',
                                created_by = user.username,
                                is_public = False
                            )
                            newWs.save()
                            
                            ds_name = 'ds_' + form.data['username'].lower()
                            services_utils.create_datastore(user.username, ds_name, newWs)
                            
                            gs.reload_nodes()
                        
                    try:    
                        auth_utils.sendMail(user, form.data['password1'])
                    except Exception as ex:
                        print(str(ex))
                        pass
    
                    return redirect('user_list')
            
            except Exception as e:
                logger.exception("ERROR: Problem creating user")
                print("ERROR: Problem creating user " + str(e))
                errors = []
                errors.append({'message': "ERROR: Problem creating user " + str(e)})
                roles = auth_backend.get_all_roles_details(exclude_system=True)

                # reverting changes
                if user:
                    user_roles = auth_backend.get_roles(user)
                    for role in user_roles:
                        try:
                            if role in role_membership_added:
                                auth_backend.remove_from_role(user, role)
                                #auth_services.get_services().ldap_delete_group_member(user, ugu.user_group)                                
                        except:
                            pass

                    if user_role_created:
                        try:
                            user_role = auth_backend.get_primary_role(user.username)
                            auth_backend.delete_role(user_role)
                        except:
                            pass

                    if user_created:
                        try:
                            auth_backend.delete_user(user)
                        except:
                            pass
                return render(request, 'user_add.html', {'form': form, 'groups': roles, 'errors': errors,'show_pass_form':show_pass_form})

        else:
            roles = auth_backend.get_all_roles_details(exclude_system=True)
            return render(request, 'user_add.html', {'form': form, 'groups': roles, 'show_pass_form':show_pass_form})
    else:
        form = UserCreateForm()
        roles = auth_backend.get_all_roles_details(exclude_system=True)
        return render(request, 'user_add.html', {'form': form, 'groups': roles, 'show_pass_form':show_pass_form})
    
    
@login_required()
@superuser_required
def user_update(request, uid):
    if request.method == 'POST':
        user = User.objects.get(id=int(uid))
        
        assigned_roles = []
        for key in request.POST:
            if 'group-' in key:
                assigned_roles.append(key[len('group-'):])
            
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
        
        admin_role =auth_backend.get_admin_role()
        if user.is_superuser and is_superuser:
            auth_backend.add_to_role(user, admin_role) # FIXME  OIDC CMI ldap
            assigned_roles.append(admin_role)
            
        if not user.is_superuser and is_superuser:
            # FIXME OIDC CMI: we need to set superuser in OIDC
            # FIXME OIDC CMI: discrepancia entre DJANGO_GVSIGOL_ADMIN y ADMIN
            user.is_superuser = True
            user.save()
            auth_backend.add_to_role(user, admin_role) # FIXME ldap
            #admin_group = UserGroup.objects.get(name__exact='admin')
            #auth_services.get_services().ldap_add_group_member(user, admin_group)
            assigned_roles.append(admin_role)
        
        if user.is_superuser and not is_superuser:
            # FIXME OIDC CMI: we need to unset superuser in OIDC
            # FIXME OIDC CMI: discrepancia entre DJANGO_GVSIGOL_ADMIN y ADMIN
            user.is_superuser = False
            user.save()
            auth_backend.remove_from_role(user, admin_role)
            #admin_group = UserGroup.objects.get(name__exact='admin')
            #auth_services.get_services().ldap_delete_group_member(user, admin_group)
        
        auth_backend.set_roles(user, assigned_roles)
        return redirect('user_list')
        
    else:
        selected_user = User.objects.get(id=int(uid))    
        roles = auth_utils.get_all_roles_checked_by_user(selected_user)
        return render(request, 'user_update.html', {'uid': uid, 'selected_user': selected_user, 'user': request.user, 'groups': roles})
        
        
@login_required()
@superuser_required
def user_delete(request, uid):
    if request.method == 'POST':
        auth_backend.delete_user(uid)
        response = {
            'deleted': True
        }     
        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')

@login_required()
@superuser_required
def group_list(request):
    response = {
        'groups': auth_backend.get_all_groups_details()
    }     
    return render(request, 'group_list.html', response)


@login_required()
@superuser_required
def group_add(request):        
    if request.method == 'POST':
        form = UserGroupForm(request.POST)
        message = None
        if form.is_valid():
            try:
                if form.data['name'] == 'admin':
                    message = _("Admin is a reserved group")
                    raise Exception
                
                if _valid_name_regex.search(form.data['name']) == None:
                    message = _("Invalid user group name: '{value}'. Identifiers must begin with a letter or an underscore (_). Subsequent characters can be letters, underscores or numbers").format(value=form.data['name'])
                    raise Exception
                auth_backend.add_group(form.data['name'], desc=form.data['description'])
                signals.role_added.send(sender=None, role=form.data.get('name'))
                return redirect('group_list')
            
            except Exception as e:
                print(str(e))
                return render(request, 'group_add.html', {'form': form, 'message': message})
                
        else:
            return render(request, 'group_add.html', {'form': form})
        
    else:
        form = UserGroupForm()
        return render(request, 'group_add.html', {'form': form})
  
@login_required()
@superuser_required
def group_delete(request, gid):
    if request.method == 'POST':
        role = auth_backend.get_role_details(gid) # FIXME OIDC CMI: debería hacer se de alguna forma más limpia
        auth_backend.delete_role(gid)
        response = {
            'deleted': True
        }     
        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')

@login_required()
def has_group(request):
    """
    GET /gvsigonline/auth/has-group/?group=groupname
    returns {"response": true} or {"response": false} para el usuario actual
    returns 401 si no está autenticado
    returns 400 para otros errores (por ejemplo falta el parámetro group)
    """
    group = request.GET.get('group')
    if not group:
        return JsonResponse({"response": "error"}, status=400)
    return JsonResponse({
        "response": auth_backend.has_group(request, group)
    })

@login_required()
def has_role(request):
    """
    GET /gvsigonline/auth/has-role/?role=rolename
    returns {"response": true} or {"response": false} para el usuario actual
    returns 401 si no está autenticado
    returns 400 para otros errores (por ejemplo falta el parámetro role)
    """
    role = request.GET.get('role')
    if not role:
        return JsonResponse({"response": "error"}, status=400)
    return JsonResponse({
        "response": auth_backend.has_role(request, role)
    })

@login_required()
def get_groups(request):
    """
    GET /gvsigonline/auth/get-groups/
    returns ["group1", "group2"] para el usuario actual
    returns 401 si no está autenticado
    """
    return JsonResponse(auth_backend.get_groups(request), safe=False)

@login_required()
def get_roles(request):
    """
    GET /gvsigonline/auth/get-roles/
    returns ["role1", "role2"] para el usuario actual
    returns 401 si no está autenticado
    """
    return JsonResponse(auth_backend.get_roles(request), safe=False)


"""
TODO:

GET /gvsigonline/auth/has-role/?user=username&role=rolename
returns {"response": true} or {"response": false}
returns 401 si no está autenticado
returns 403 si no lo invoca un superusuario o username
returns 400 para otros errores (por ejemplo falta el parámetro role)

GET /gvsigonline/auth/has-group/?user=username&group=groupname
returns {"response": true} or {"response": false}
returns 401 si no está autenticado
returns 403 si no lo invoca un superusuario o username
returns 400 para otros errores (por ejemplo falta el parámetro group)

GET /gvsigonline/auth/get-roles/?user=username
returns ["role1", "role2"]
returns 403 si no lo invoca un superusuario o username
returns 401 si no está autenticado

GET /gvsigonline/auth/get-groups/?user=username
returns ["group1", "group2"]
returns 403 si no lo invoca un superusuario o username
returns 401 si no está autenticado
"""