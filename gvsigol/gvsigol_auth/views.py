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
from gvsigol.basetypes import BackendNotAvailable
from gvsigol.utils import default_sorter
from gvsigol_auth.django_auth import get_admin_role
'''
@author: Javier Rodrigo <jrodrigo@scolab.es>
'''

from django.urls import reverse
from django.shortcuts import render, HttpResponse, redirect
from django.http import HttpResponseForbidden
from django.views.decorators.http import require_http_methods
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils.translation import ugettext as _
from .forms import UserCreateForm, UserGroupForm, UserRoleForm
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
        # TODO: AUTH_WITH_REMOTE_USER deprecated   
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
            auth_backend.update_user(
                username=request.user.username,
                password=password1)
            """
            user.set_password(password1)
            user.save()
            
            auth_services.get_services().ldap_change_user_password(user, password1)
            """
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

            pass_reset_url = reverse('password_reset_confirmation', kwargs={'username': user.username, 'uid': uid, 'token': token})
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



def password_reset_confirmation(request, username, uid, token):
    context = {
        'username' : username,
        'uid': uid,
        'token': token
        }
            
    return render(request, 'registration/password_reset_confirm.html', context)
       

def password_reset_complete(request):
    """
    View that checks the hash in a password reset link and presents a
    form for entering a new password.
    """
    username = request.POST.get('username')
    token = request.POST.get('token')

    user = User.objects.get(username=username)

    errors = ''
    
    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            temp_pass = request.POST.get('password')
            auth_backend.update_user(username, password=temp_pass)            
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
    users = []
    for user in users:
        user["roles"] = "; ".join(user["roles"])
                      
    response = {
        'users': users,
        'read_only_users': settings.AUTH_READONLY_USERS
    }     
    return render(request, 'user_list.html', response)

@login_required()
@superuser_required
@require_http_methods(["HEAD", "POST"])
def datatables_user_list(request):
    draw = request.POST.get('draw')
    start = request.POST.get('start')
    length = request.POST.get('length')
    search = None
    for key in request.POST:
        if key.startswith('search[value]'):
            search = request.POST.get(key)
    
    try:
        response = auth_backend.get_filtered_users_details(exclude_system=True, first=start, max=length, search=search)
        users = response.get('users')
        user_list = []
        for user in users:
            user_list.append([
                                user.get('id'),
                                user.get('username'),
                                user.get('first_name'),
                                user.get('last_name'),
                                user.get('email'),
                                user.get('is_superuser'),
                                user.get('is_staff'),
                                "; ".join(user.get("roles", []))
                            ])
    except Exception as e:
        return JsonResponse({
            "draw": draw,
            "recordsTotal": 0,
            "recordsFiltered": 0,
            "data": [],
            "error": str(e)
        })
    data = {
        "draw": draw,
        "recordsTotal": -1,
        "recordsFiltered": response.get('numberMatched'),
        "data": user_list
    }
    return JsonResponse(data)


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
            is_staff = False
            if 'is_staff' in form.data:
                is_staff = True
                
            is_superuser = False
            if 'is_superuser' in form.data:
                is_superuser = True
                is_staff = True
            
            # flag what has been done to be able to revert if needed
            user_created = False
            role_membership_added = []
            user_role_created = False
            user = None
            errors = []
            try:
                assigned_groups = []
                for key in form.data:
                    if 'group-' in key:
                        assigned_groups.append(key[len('group-'):])

                assigned_roles = []
                for key in form.data:
                    if 'role-' in key:
                        assigned_roles.append(key[len('role-'):])
                                
                if form.data['password1'] == form.data['password2']:
                    user = auth_backend.add_user(
                        form.data['username'].lower(),
                        form.data['password1'],
                        form.data['email'].lower(),
                        form.data['first_name'],
                        form.data['last_name'],
                        groups=assigned_groups,
                        roles=assigned_roles,
                        superuser=is_superuser,
                        staff=is_staff
                    )
                    if user:
                        user_created = True

                        #User backend
                        if is_superuser or is_staff:
                            user_role_created, role = auth_utils.config_staff_user(user.username)
                            role_membership_added.append(role)
                            
                        try:    
                            auth_utils.sendMail(user, form.data['password1'])
                        except Exception as ex:
                            logger.exception(ex)
                            print(str(ex))
                            pass
        
                        return redirect('user_list')
                    errors.append({"message": _("User creation failed")}) # FIXME OIDC CMI should get a reason
            except Exception as e:
                logger.exception("ERROR: Problem creating user")
                message = "ERROR: Problem creating user - " + str(e)
                print(message)
                errors.append({'message': message})
            roles = auth_backend.get_all_roles_details(exclude_system=True)

            # reverting changes
            if user:
                user_roles = auth_backend.get_roles(user)
                for role in user_roles:
                    try:
                        if role in role_membership_added:
                            auth_backend.remove_from_role(user, role)
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
            roles.sort(key=default_sorter)
            response = {'form': form, 'roles': roles, 'errors': errors,'show_pass_form':show_pass_form}
            if auth_backend.check_group_support():
                groups = auth_backend.get_all_groups_details(exclude_system=True)
                groups.sort(key=default_sorter)
                response['groups'] = groups
            return render(request, 'user_add.html', response)

        else:
            roles = auth_backend.get_all_roles_details(exclude_system=True)
            roles.sort(key=default_sorter)
            response = {'form': form, 'roles': roles, 'show_pass_form':show_pass_form}
            if auth_backend.check_group_support():
                groups = auth_backend.get_all_groups_details(exclude_system=True)
                groups.sort(key=default_sorter)
                response['groups'] = groups
            return render(request, 'user_add.html', response)
    else:
        form = UserCreateForm()
        roles = auth_backend.get_all_roles_details(exclude_system=True)
        roles.sort(key=default_sorter)
        response = {'form': form, 'roles': roles, 'show_pass_form':show_pass_form}
        if auth_backend.check_group_support():
            groups = auth_backend.get_all_groups_details(exclude_system=True)
            groups.sort(key=default_sorter)
            response['groups'] = groups
        return render(request, 'user_add.html', response)
    
    
@login_required()
@superuser_required
def user_update(request, username):
    try:
        if request.method == 'POST':
            assigned_groups = []
            for key in request.POST:
                if 'group-' in key:
                    assigned_groups.append(key[len('group-'):])

            assigned_roles = []
            for key in request.POST:
                if 'role-' in key:
                    assigned_roles.append(key[len('role-'):])
                
            is_staff = False
            if 'is_staff' in request.POST:
                is_staff = True
                
            is_superuser = False
            if 'is_superuser' in request.POST:
                is_superuser = True
                is_staff = True

            if settings.AUTH_READONLY_USERS:
                success = auth_backend.update_user(
                    username,
                    superuser=is_superuser,
                    staff=is_staff,
                    groups=assigned_groups,
                    roles=assigned_roles
                )
            else:
                success = auth_backend.update_user(
                        username,
                        email=request.POST.get('email'),
                        first_name=request.POST.get('first_name'),
                        last_name=request.POST.get('last_name'),
                        superuser=is_superuser,
                        staff=is_staff,
                        groups=assigned_groups,
                        roles=assigned_roles
                )
            if success and (is_superuser or is_staff):
                auth_utils.config_staff_user(username)

            return redirect('user_list')
        else:
            selected_user = auth_backend.get_user_details(user=username)
            roles = auth_utils.get_all_roles_checked_by_user(username)
            response = {
                'uid': username,
                'selected_user': selected_user,
                'user': request.user,
                'roles': roles,
                'read_only_users': settings.AUTH_READONLY_USERS
                }
            if auth_backend.check_group_support():
                response['groups'] = auth_utils.get_all_groups_checked_by_user(username)
            return render(request, 'user_update.html', response)
    except BackendNotAvailable:
        message = _("The authentication server is not available. Try again later or contact system administrators.")
        return render(request, 'user_update.html', {'uid': username, 'selected_user': None, 'user': None, 'groups': [], 'roles': []})
        
@login_required()
@superuser_required
def user_delete(request, uid):
    if request.method == 'POST':
        deleted = auth_backend.delete_user(user_id=uid)
        response = {
            'deleted': deleted
        }
        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')

def sort_by_name(a_dict):
    return a_dict.get('name')

@login_required()
@superuser_required
def group_list(request):
    response = {
        'groups': sorted(auth_backend.get_all_groups_details(), key=sort_by_name)
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
                if _valid_name_regex.search(form.data['name']) == None:
                    message = _("Invalid user group name: '{value}'. Identifiers must begin with a letter or an underscore (_). Subsequent characters can be letters, underscores or numbers").format(value=form.data['name'])
                    raise Exception
                auth_backend.add_group(form.data['name'], desc=form.data['description'])
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
def group_delete(request, group_name):
    if request.method == 'POST':
        auth_backend.delete_group(group_name)
        response = {
            'deleted': True
        }     
        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')

@login_required()
@superuser_required
def role_list(request):
    response = {
        'roles': sorted(auth_backend.get_all_roles_details(), key=sort_by_name)
    }     
    return render(request, 'role_list.html', response)


@login_required()
@superuser_required
def role_add(request):        
    if request.method == 'POST':
        form = UserRoleForm(request.POST)
        message = None
        if form.is_valid():
            try:
                if form.data['name'] == 'admin':
                    message = _("Admin is a reserved role")
                    raise Exception
                
                if _valid_name_regex.search(form.data['name']) == None:
                    message = _("Invalid user role name: '{value}'. Identifiers must begin with a letter or an underscore (_). Subsequent characters can be letters, underscores or numbers").format(value=form.data['name'])
                    raise Exception
                auth_backend.add_role(form.data['name'], desc=form.data['description'])
                signals.role_added.send(sender=None, role=form.data.get('name'))
                return redirect('role_list')
            
            except Exception as e:
                print(str(e))
                return render(request, 'role_add.html', {'form': form, 'message': message})
                
        else:
            return render(request, 'role_add.html', {'form': form})
        
    else:
        form = UserRoleForm()
        return render(request, 'role_add.html', {'form': form})
  
@login_required()
@superuser_required
def role_delete(request, role_name):
    if request.method == 'POST':
        if role_name in auth_backend.get_system_roles():
            status = 400
            response = {
                'deleted': False,
                'message': _("System roles can't be deleted")
            }
        else:
            auth_backend.delete_role(role_name)
            response = {
               'deleted': True
            }
            status = 200
        return HttpResponse(json.dumps(response, indent=4), content_type='application/json', status=status)

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
