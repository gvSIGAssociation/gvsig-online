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
from gvsigol_core.utils import get_supported_crs
from gvsigol_symbology.models import StyleLayer
from gdaltools.metadata import project
from gvsigol_core.models import SharedView
from django.http.response import JsonResponse
from gvsigol_core import forms
'''
@author: Javier Rodrigo <jrodrigo@scolab.es>
'''

from django.shortcuts import render, HttpResponse, redirect
from django.http import HttpResponseForbidden
from models import Project, ProjectUserGroup, ProjectLayerGroup
from gvsigol_services.models import Server, Workspace, Datastore, Layer, LayerGroup, ServiceUrl
from gvsigol_auth.models import UserGroup, UserGroupUser
from django.contrib.auth.decorators import login_required
from django.utils.translation import ugettext as _
from django.contrib.auth.models import User, AnonymousUser
from gvsigol_auth.utils import superuser_required, is_superuser, staff_required
import utils as core_utils
from gvsigol_services import geographic_servers, utils, backend_postgis
from django.views.decorators.cache import cache_control
from gvsigol import settings
import gvsigol_services.utils as services_utils
from operator import itemgetter
from django import apps
from django.core.mail import send_mail
from owslib.util import Authentication
from owslib.wmts import WebMapTileService
import gvsigol
import urllib
import random
import datetime
import string
import json
import ast
import re

from django.views.decorators.clickjacking import xframe_options_exempt
from actstream import action
from actstream.models import Action
from iso639 import languages
from django.core.exceptions import PermissionDenied
from django.utils.crypto import get_random_string
from gvsigol_core.forms import CloneProjectForm
from django.contrib import messages
from django.shortcuts import redirect

_valid_name_regex=re.compile("^[a-zA-Z_][a-zA-Z0-9_]*$")
import logging
logger = logging.getLogger("gvsigol")

def not_found_view(request):
    response = render(request, '404.html', {})
    response.status_code = 404
    return response

@login_required(login_url='/gvsigonline/auth/login_user/')
def home(request):
    user = User.objects.get(username=request.user.username)
    groups_by_user = UserGroupUser.objects.filter(user_id=user.id)

    from_login = False
    if 'HTTP_REFERER' in request.META:
        if 'auth/login_user' in request.META['HTTP_REFERER']:
            from_login = True
    if settings.AUTH_WITH_REMOTE_USER == True:
            from_login = True

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

    media_url = settings.MEDIA_URL[:-1]
    projects = []
    public_projects = []
    if request.user.is_superuser:
        for p in Project.objects.all():
            image = ''
            if "no_project.png" in p.image.url:
                image = p.image.url.replace(media_url, '')
            else:
                image = p.image.url.replace(settings.BASE_URL, '')

            project = {}
            project['id'] = p.id
            project['name'] = p.name
            project['title'] = p.title
            project['description'] = p.description
            project['image'] = urllib.unquote(image)

            if p.is_public:
                public_projects.append(project)
            else:
                projects.append(project)
    else:
        for p in Project.objects.all():
            image = ''
            if "no_project.png" in p.image.url:
                media_url = settings.MEDIA_URL[:-1]
                image = p.image.url.replace(media_url, '')
            else:
                image = p.image.url.replace(settings.BASE_URL, '')
                
            project = {}
            project['id'] = p.id
            project['name'] = p.name
            project['title'] = p.title
            project['description'] = p.description
            project['image'] = urllib.unquote(image)

            if p.is_public:
                public_projects.append(project)
            else:
                if p.created_by == request.user.username:
                    projects.append(project)
                if p.created_by != request.user.username:
                    for ua in projects_by_user:
                        if p.id == ua.project_id:
                            projects.append(project)
                            break

    external_ldap_mode = True
    if 'AD' in settings.GVSIGOL_LDAP and settings.GVSIGOL_LDAP['AD'].__len__() > 0:
        external_ldap_mode = False

    return render(request, 'home.html', {'projects': projects, 'public_projects': public_projects, 'external_ldap_mode': external_ldap_mode})

@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def project_list(request):

    project_list = None
    if request.user.is_superuser:
        project_list = Project.objects.all()
    else:
        project_list = Project.objects.filter(created_by__exact=request.user.username)

    projects = []
    for p in project_list:
        project = {}
        project['id'] = p.id
        project['name'] = p.name
        project['title'] = p.title
        project['description'] = p.description
        project['is_public'] = p.is_public
        projects.append(project)

    response = {
        'projects': projects,
        'servers': Server.objects.all().order_by('-default')
    }
    return render(request, 'project_list.html', response)

def get_core_tools(enabled=True):
    return [{
        'name': 'gvsigol_tool_navigationhistory',
        'checked': enabled,
        'title': _(u'Navigation history'),
        'description': _(u'Browse the view forward and backward')
    },{
        'name': 'gvsigol_tool_zoom',
        'checked': enabled,
        'title': _(u'Zoom tools'),
        'description': _(u'Zoom in, zoom out, ...')
    }, {
        'name': 'gvsigol_tool_info',
        'checked': enabled,
        'title': _(u'Feature info'),
        'description': _(u'Map information at point')
    }, {
        'name': 'gvsigol_tool_measure',
        'checked': enabled,
        'title': _(u'Measure tools'),
        'description': _(u'It allows to measure areas and distances')
    }, {
        'name': 'gvsigol_tool_coordinate',
        'checked': enabled,
        'title': _(u'Search coordinates'),
        'description': _(u'Center the map at given coordinates')
    }, {
        'name': 'gvsigol_tool_coordinatecalc',
        'checked': enabled,
        'title': _(u'Coordinate calculator'),
        'description': _(u'Transform coordinates between different systems')
    }, {
        'name': 'gvsigol_tool_location',
        'checked': enabled,
        'title': _(u'Geolocation'),
        'description': _(u'Center the map in the current position')
    }, {
        'name': 'gvsigol_tool_shareview',
        'checked': enabled,
        'title': _(u'Share view'),
        'description': _(u'Allows you to share the view in its current state')
    }, {
        'name': 'gvsigol_tool_selectfeature',
        'checked': enabled,
        'title': _(u'Select feature'),
        'description': _(u'Select features from current layers')
    }]

def get_plugin_tools(enabled=False):
    project_tools = []
    for key in apps.apps.app_configs:
        app = apps.apps.app_configs[key]
        if 'gvsigol_plugin_' in app.name:
            project_tools.append({
                'name': app.name,
                'checked': enabled,
                'title': app.name,
                'description': app.verbose_name
            })
    return project_tools

def get_available_tools(core_enabled=True, plugin_enabled=True):
    """
    Gets the definition of available tools
    (core tools plus plugin tools)

    Parameters:
    :param core_enabled: Whether the core tools should enabled. Defaults to True
    :param plugin_enabled: Whether the plugin tools should enabled. Defaults to False
    """
    return get_core_tools(core_enabled) + get_plugin_tools(plugin_enabled)

@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def project_add(request):

    has_geocoding_plugin = False
    if 'gvsigol_plugin_geocoding' in settings.INSTALLED_APPS:
        from gvsigol_plugin_geocoding.models import Provider
        providers = Provider.objects.all()
        has_geocoding_plugin = providers.__len__() > 0

    project_tools = get_available_tools()

    if request.method == 'POST':
        name = request.POST.get('project-name')

        name = re.sub(r'[^a-zA-Z0-9 ]',r'',name) #for remove all characters
        name = re.sub(' ','',name)

        logo_link = request.POST.get('project-logo-link')
        title = request.POST.get('project-title')
        description = request.POST.get('project-description')
        latitude = request.POST.get('center-lat')
        longitude = request.POST.get('center-lon')
        extent = request.POST.get('extent')
        zoom = request.POST.get('zoom')
        toc = request.POST.get('toc_value')
        toc_mode = request.POST.get('toc_mode')
        tools = request.POST.get('project_tools')

        is_public = False
        if 'is_public' in request.POST:
            is_public = True
            
        show_project_icon = False
        if 'show_project_icon' in request.POST:
            show_project_icon = True
        
        selectable_groups = False
        if 'selectable_groups' in request.POST:
            selectable_groups = True
            
        restricted_extent = False
        if 'restricted_extent' in request.POST:
            restricted_extent = True

        has_image = False
        if 'project-image' in request.FILES:
            has_image = True
            
        has_logo = False
        if 'project-logo' in request.FILES:
            has_logo = True

        try:
            selected_base_layer = int(request.POST.get('selected_base_layer'))
        except:
            selected_base_layer = None
            
        selected_base_group = None
        if 'selected_base_group' in request.POST:
            selected_base_group = request.POST.get('selected_base_group')

        assigned_layergroups = []
        assigned_usergroups = []
        for key in request.POST:
            if 'layergroup-' in key:
                assigned_layergroups.append(int(key.split('-')[1]))
            if 'usergroup-' in key:
                assigned_usergroups.append(int(key.split('-')[1]))

        exists = False
        projects = Project.objects.all()
        for p in projects:
            if name == p.name:
                exists = True

        layergroups = None
        if request.user.is_superuser:
            layergroups = LayerGroup.objects.exclude(name='__default__')
        else:
            layergroups = LayerGroup.objects.exclude(name='__default__').filter(created_by__exact=request.user.username)
            
        prepared_layer_groups = []
        for lg in layergroups:
            layer_group = {}
            layer_group['id'] = lg.id
            layer_group['name'] = lg.name
            layer_group['title'] = lg.title
            layer_group['layers'] = []
            layers = Layer.objects.filter(layer_group_id=lg.id)
            for l in layers:
                layer_group['layers'].append({
                    'id': l.id,
                    'title': l.title
                })
            prepared_layer_groups.append(layer_group)

        groups = None
        if request.user.is_superuser:
            groups = core_utils.get_all_groups()
        else:
            groups = core_utils.get_user_groups(request.user.username)

        if name == '':
            message = _(u'You must enter an project name')
            return render(request, 'project_add.html', {'message': message, 'layergroups': prepared_layer_groups, 'tools': project_tools, 'groups': groups, 'has_geocoding_plugin': has_geocoding_plugin})

        if _valid_name_regex.search(name) == None:
            message = _(u"Invalid project name: '{value}'. Identifiers must begin with a letter or an underscore (_). Subsequent characters can be letters, underscores or numbers").format(value=name)
            return render(request, 'project_add.html', {'message': message, 'layergroups': prepared_layer_groups, 'tools': project_tools, 'groups': groups, 'has_geocoding_plugin': has_geocoding_plugin})

        if not exists:
            project = Project(
                name = name,
                title = title,
                logo_link = logo_link,
                description = description,
                center_lat = latitude,
                center_lon = longitude,
                zoom = int(float(zoom)),
                extent = extent,
                toc_order = toc,
                toc_mode = toc_mode,
                created_by = request.user.username,
                is_public = is_public,
                show_project_icon = show_project_icon,
                selectable_groups = selectable_groups,
                restricted_extent = restricted_extent,
                tools = tools
            )
            project.save()
            
            if has_image:
                project.image = request.FILES['project-image']
                project.save()
            
            if has_logo:
                project.logo = request.FILES['project-logo']
                project.save()

            for alg in assigned_layergroups:
                layergroup = LayerGroup.objects.get(id=alg)
                baselayer_group = False
                if selected_base_group != '' and alg == int(selected_base_group):
                    baselayer_group = True
                project_layergroup = ProjectLayerGroup(
                    project = project,
                    layer_group = layergroup,
                    multiselect = True,
                    baselayer_group = baselayer_group
                )
                project_layergroup.save()
                if baselayer_group and selected_base_layer:
                    project_layergroup.default_baselayer = selected_base_layer
                    project_layergroup.save()

            for aug in assigned_usergroups:
                usergroup = UserGroup.objects.get(id=aug)
                project_usergroup = ProjectUserGroup(
                    project = project,
                    user_group = usergroup
                )
                project_usergroup.save()

            admin_group = UserGroup.objects.get(name__exact='admin')
            project_usergroup = ProjectUserGroup(
                project = project,
                user_group = admin_group
            )
            project_usergroup.save()

            if 'redirect' in request.GET:
                redirect_var = request.GET.get('redirect')
                if redirect_var == 'new-layer-group':
                    return redirect('layergroup_add_with_project', project_id=str(project.id))


        else:
            message = _(u'Project name already exists')
            return render(request, 'project_add.html', {'message': message, 'tools': project_tools , 'layergroups': prepared_layer_groups, 'groups': groups, 'has_geocoding_plugin': has_geocoding_plugin})



        return redirect('project_list')

    else:
        layergroups = None
        if request.user.is_superuser:
            layergroups = LayerGroup.objects.exclude(name='__default__')
        else:
            layergroups = LayerGroup.objects.exclude(name='__default__').filter(created_by__exact=request.user.username)

        groups = None
        if request.user.is_superuser:
            groups = core_utils.get_all_groups()
        else:
            groups = core_utils.get_user_groups(request.user.username)
        
        prepared_layer_groups = []
        for lg in layergroups:
            layer_group = {}
            layer_group['id'] = lg.id
            layer_group['name'] = lg.name
            layer_group['title'] = lg.title
            layer_group['layers'] = []
            layers = Layer.objects.filter(layer_group_id=lg.id)
            for l in layers:
                layer_group['layers'].append({
                    'id': l.id,
                    'title': l.title
                })
            prepared_layer_groups.append(layer_group)

        return render(request, 'project_add.html', {'layergroups': prepared_layer_groups, 'tools': project_tools, 'groups': groups, 'has_geocoding_plugin': has_geocoding_plugin})


@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def project_update(request, pid):

    has_geocoding_plugin = False
    if 'gvsigol_plugin_geocoding' in settings.INSTALLED_APPS:
        from gvsigol_plugin_geocoding.models import Provider
        providers = Provider.objects.all()
        has_geocoding_plugin = providers.__len__() > 0

    if request.method == 'POST':
        name = request.POST.get('project-name')
        title = request.POST.get('project-title')
        logo_link = request.POST.get('project-logo-link')
        description = request.POST.get('project-description')
        latitude = request.POST.get('center-lat')
        longitude = request.POST.get('center-lon')
        extent = request.POST.get('extent')
        zoom = request.POST.get('zoom')
        toc = request.POST.get('toc_value')
        toc_mode = request.POST.get('toc_mode')
        tools = request.POST.get('project_tools')

        is_public = False
        if 'is_public' in request.POST:
            is_public = True
            
        show_project_icon = False
        if 'show_project_icon' in request.POST:
            show_project_icon = True
            
        selectable_groups = False
        if 'selectable_groups' in request.POST:
            selectable_groups = True
            
        restricted_extent = False
        if 'restricted_extent' in request.POST:
            restricted_extent = True

        try:
            selected_base_layer = int(request.POST.get('selected_base_layer'))
        except:
            selected_base_layer = None
            
        selected_base_group = None
        if 'selected_base_group' in request.POST:
            selected_base_group = request.POST.get('selected_base_group')

        assigned_layergroups = []
        assigned_usergroups = []
        for key in request.POST:
            if 'layergroup-' in key:
                assigned_layergroups.append(int(key.split('-')[1]))
            if 'usergroup-' in key:
                assigned_usergroups.append(int(key.split('-')[1]))

        has_image = False
        if 'project-image' in request.FILES:
            has_image = True
            
        has_logo = False
        if 'project-logo' in request.FILES:
            has_logo = True

        project = Project.objects.get(id=int(pid))

        old_layer_groups = []
        for lg in ProjectLayerGroup.objects.filter(project_id=project.id):
            old_layer_groups.append(lg.layer_group.id)

        if set(assigned_layergroups) != set(old_layer_groups):
            core_utils.toc_remove_layergroups(project.toc_order, old_layer_groups)
            toc_structure = core_utils.get_json_toc(assigned_layergroups)
            project.toc_order = toc_structure

        name = re.sub(r'[^a-zA-Z0-9 ]',r'',name) #for remove all characters
        name = re.sub(' ','',name)

        project.name = name
        project.title = title
        project.logo_link = logo_link
        project.description = description
        project.center_lat = latitude
        project.center_lon = longitude
        project.zoom = int(float(zoom))
        project.extent = extent
        project.is_public = is_public
        project.toc_order = toc
        project.toc_mode = toc_mode
        project.tools = tools
        project.show_project_icon = show_project_icon
        project.selectable_groups = selectable_groups
        project.restricted_extent = restricted_extent

        if has_image:
            project.image = request.FILES['project-image']
            
        if has_logo:
            project.logo = request.FILES['project-logo']

        project.save()

        for lg in ProjectLayerGroup.objects.filter(project_id=project.id):
            lg.delete()

        for ug in ProjectUserGroup.objects.filter(project_id=project.id):
            ug.delete()
            
        for alg in assigned_layergroups:
            layergroup = LayerGroup.objects.get(id=alg)
            baselayer_group = False
            try:
                if alg == int(selected_base_group):
                    baselayer_group = True
            except:
                print 'ERROR: selected_base_group is not defined'
            project_layergroup = ProjectLayerGroup(
                project = project,
                layer_group = layergroup,
                multiselect = True,
                baselayer_group = baselayer_group
            )
            project_layergroup.save()
            if baselayer_group and selected_base_layer:
                project_layergroup.default_baselayer = selected_base_layer
                project_layergroup.save()

        for aug in assigned_usergroups:
            usergroup = UserGroup.objects.get(id=aug)
            project_usergroup = ProjectUserGroup(
                project = project,
                user_group = usergroup
            )
            project_usergroup.save()

        admin_group = UserGroup.objects.get(name__exact='admin')
        project_usergroup = ProjectUserGroup(
            project = project,
            user_group = admin_group
        )
        project_usergroup.save()

        if 'redirect' in request.GET:
            redirect_var = request.GET.get('redirect')
            if redirect_var == 'new-layer-group':
                return redirect('layergroup_add_with_project', project_id=str(project.id))


        return redirect('project_list')

    else:
        project = Project.objects.get(id=int(pid))
        groups = core_utils.get_all_groups_checked_by_project(request, project)
        layer_groups = core_utils.get_all_layer_groups_checked_by_project(request, project)

        if project.toc_order:
            toc = json.loads(project.toc_order)
            for g in toc:
                group = toc.get(g)
                ordered_layers = sorted(group.get('layers').iteritems(), key=lambda (x, y): y['order'], reverse=True)
                group['layers'] = ordered_layers
            ordered_toc = sorted(toc.iteritems(), key=lambda (x, y): y['order'], reverse=True)
        else:
            ordered_toc = {}
            for g in layer_groups:
                ordered_toc[g['name']] = {'name': g['name'], 'title': g['title'], 'order': 1000, 'layers': {}}
            ordered_toc = sorted(ordered_toc.iteritems(), key=lambda (x, y): y['order'], reverse=True)
        projectTools = json.loads(project.tools) if project.tools else get_available_tools(True, True)

        for defaultTool in get_available_tools(True, True):
            founded = False
            for projectTool in projectTools:
                if projectTool['name'] == defaultTool['name']:
                    founded = True
                    break

            if not founded:
                defaultTool['checked'] = False
                projectTools.append(defaultTool)
              
        for lg in layer_groups:
            lg['layers'] = []
            layers = Layer.objects.filter(layer_group_id=lg['id'])
            for l in layers:   
                baselayer = False           
                if lg['baselayer_group']:
                    if l.id == lg['default_baselayer']:
                        baselayer = True
                lg['layers'].append({
                    'id': l.id,
                    'title': l.title,
                    'baselayer': baselayer
                })
        
        url_base_lyr = ''
        icon = settings.BASE_URL + settings.STATIC_URL + 'img/processing.gif'
        if(project.baselayer_version > 0):
            url_base_lyr = settings.MEDIA_URL + settings.LAYERS_ROOT + "/" + project.name + '_prj_' + str(project.baselayer_version) + ".zip"
                    
        return render(request, 'project_update.html', {'tools': projectTools,
                                                       'pid': pid, 
                                                       'project': project, 
                                                       'groups': groups, 
                                                       'layergroups': layer_groups, 
                                                       'has_geocoding_plugin': has_geocoding_plugin, 
                                                       'toc': ordered_toc, 
                                                       'superuser' : is_superuser(request.user), 
                                                       'processing_icon' : icon,
                                                       'url_base_lyr' : url_base_lyr
                                                       })


@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def project_delete(request, pid):
    if request.method == 'POST':
        try:
            if request.user.is_superuser:
                project = Project.objects.get(id=int(pid))
            else:
                project = Project.objects.get(id=int(pid), created_by__exact=request.user.username)
            project.delete()
            response = {
                'deleted': True
            }
            return HttpResponse(json.dumps(response, indent=4), content_type='project/json')
        except:
            logger.exception("Error deleting project")
            return HttpResponseForbidden({"deleted": False, "error": "Not allowed"})

def load(request, project_name):
    project = Project.objects.get(name__exact=project_name)

    if project.is_public:
        if request.user and request.user.is_authenticated():
            return redirect('load_project', project_name=project.name)
        else:
            return redirect('load_public_project', project_name=project.name)

    else:
        return redirect('load_project', project_name=project.name)

@login_required(login_url='/gvsigonline/auth/login_user/')
@cache_control(max_age=86400)
def load_project(request, project_name):
    if core_utils.can_read_project(request.user, project_name):
        project = Project.objects.get(name__exact=project_name)

        has_image = True
        if "no_project.png" in project.image.url:
            has_image = False

        plugins_config = core_utils.get_plugins_config()
        response = render(request, 'viewer.html', {
            'has_image': has_image,
            'supported_crs': core_utils.get_supported_crs(),
            'project': project,
            'project_logo': project.logo.url.replace(settings.BASE_URL, ''),
            'project_image': project.image.url.replace(settings.BASE_URL, ''),
            'pid': project.id,
            'extra_params': json.dumps(request.GET),
            'plugins_config': plugins_config,
            'is_shared_view': False,
            'main_page': settings.LOGOUT_PAGE_URL
            }
        )

        #Expira la caché cada día
        tomorrow = datetime.datetime.now() + datetime.timedelta(days = 1)
        tomorrow = datetime.datetime.replace(tomorrow, hour=0, minute=0, second=0)
        expires = datetime.datetime.strftime(tomorrow, "%a, %d-%b-%Y %H:%M:%S GMT")
        response.set_cookie('key', expires = expires)

        action.send(request.user, verb="gvsigol_core/get_conf", action_object=project)

        return response

    else:
        return render(request, 'illegal_operation.html', {})


@cache_control(max_age=86400)
def load_public_project(request, project_name):
    project = Project.objects.get(name__exact=project_name)
    if not core_utils.can_read_project(request.user, project):
        return render(request, 'illegal_operation.html', {})

    has_image = True
    if "no_project.png" in project.image.url:
        has_image = False

    plugins_config = core_utils.get_plugins_config()
    response = render(request, 'viewer.html', {
        'has_image': has_image,
        'supported_crs': core_utils.get_supported_crs(),
        'project': project,
        'project_logo': project.logo.url.replace(settings.BASE_URL, ''),
        'project_image': project.image.url.replace(settings.BASE_URL, ''),
        'pid': project.id,
        'extra_params': json.dumps(request.GET),
        'plugins_config': plugins_config,
        'is_shared_view': False,
        'main_page': settings.LOGOUT_PAGE_URL
        }
    )

    #Expira la caché cada día
    tomorrow = datetime.datetime.now() + datetime.timedelta(days = 1)
    tomorrow = datetime.datetime.replace(tomorrow, hour=0, minute=0, second=0)
    expires = datetime.datetime.strftime(tomorrow, "%a, %d-%b-%Y %H:%M:%S GMT")
    response.set_cookie('key', expires = expires)

    action.send(project, verb="gvsigol_core/get_conf", action_object=project)

    return response


@login_required(login_url='/gvsigonline/auth/login_user/')
@xframe_options_exempt
@cache_control(max_age=86400)
def portable_project_load(request, project_name):
    if core_utils.can_read_project(request.user, project_name):
        project = Project.objects.get(name__exact=project_name)
        response = render(request, 'portable_viewer.html', {'supported_crs': core_utils.get_supported_crs(), 'project': project, 'pid': project.id, 'extra_params': json.dumps(request.GET)})
        #Expira la caché cada día
        tomorrow = datetime.datetime.now() + datetime.timedelta(days = 1)
        tomorrow = datetime.datetime.replace(tomorrow, hour=0, minute=0, second=0)
        expires = datetime.datetime.strftime(tomorrow, "%a, %d-%b-%Y %H:%M:%S GMT")
        response.set_cookie('key', expires = expires)
        return response
    else:
        return render(request, 'illegal_operation.html', {})


@login_required(login_url='/gvsigonline/auth/login_user/')
def blank_page(request):
    return render(request, 'blank_page.html', {})


def get_layer_styles(layer):
    styles = []
    stllyrs = StyleLayer.objects.filter(layer_id = layer.id)
    for stllyr in stllyrs:
        stl=stllyr.style
        if not stl.name.endswith('__tmp'):
            style={
                'name' : stl.name,
                'title' : stl.title,
                'is_default': stl.is_default,
                'has_custom_legend': stl.has_custom_legend,
                'custom_legend_url': stl.custom_legend_url
                }
            styles.append(style)
    return styles

def get_default_style(layer):
    default = None
    stllyrs = StyleLayer.objects.filter(layer_id = layer.id)
    for stllyr in stllyrs:
        stl=stllyr.style
        if stl.is_default:
            default = stl
    return default


def project_get_conf(request):
    if request.method == 'POST':
        errors = []
        pid = request.POST.get('pid')
        is_shared_view = json.loads(request.POST.get('shared_view'))

        project = Project.objects.get(id=int(pid))
        if not project.toc_order:
            project.toc_order = "{}"
        toc = json.loads(project.toc_order)

        used_crs = []
        crs_code = int('EPSG:4326'.split(':')[1])
        if crs_code in core_utils.get_supported_crs():
            epsg = core_utils.get_supported_crs()[crs_code]
            used_crs.append(epsg)
        crs_code = int('EPSG:3857'.split(':')[1])
        if crs_code in core_utils.get_supported_crs():
            epsg = core_utils.get_supported_crs()[crs_code]
            used_crs.append(epsg)
        crs_code = int('EPSG:4258'.split(':')[1])
        if crs_code in core_utils.get_supported_crs():
            epsg = core_utils.get_supported_crs()[crs_code]
            used_crs.append(epsg)

        project_layers_groups = ProjectLayerGroup.objects.filter(project_id=project.id)
        layer_groups = []
        workspaces = []
        
        language = core_utils.get_iso_language(request)

        count = 0
        for project_group in project_layers_groups:
            group = LayerGroup.objects.get(id=project_group.layer_group_id)
            server = Server.objects.get(id=group.server_id)

            conf_group = {}
            conf_group['groupTitle'] = group.title
            conf_group['groupId'] = ''.join(random.choice(string.ascii_uppercase) for i in range(6))
            if toc.get(group.name):
                conf_group['groupOrder'] = toc.get(group.name).get('order')
            else:
                conf_group['groupOrder'] = count
            count = count + 1
            conf_group['groupName'] = group.name
            conf_group['cached'] = group.cached
            conf_group['visible'] = group.visible
            if project_group.baselayer_group:
                conf_group['visible'] = False 
            conf_group['basegroup'] = project_group.baselayer_group
            conf_group['wms_endpoint'] = server.getWmsEndpoint()
            conf_group['wfs_endpoint'] = server.getWfsEndpoint()
            conf_group['cache_endpoint'] = server.getCacheEndpoint()
            layers_in_group = Layer.objects.filter(layer_group_id=group.id).order_by('order')
            layers = []
            user_roles = core_utils.get_group_names_by_user(request.user)
            
            allows_getmap = True
            servers_list = []
            
            idx = 0
            for l in layers_in_group:
                if not l.external:
                    try:
                        read_roles = services_utils.get_read_roles(l)
                        write_roles = services_utils.get_write_roles(l)
    
                        readable = False
                        if len(read_roles) == 0:
                            readable = True
                        else:
                            for ur in user_roles:
                                for rr in read_roles:
                                    if ur == rr:
                                        readable = True
    
                        if readable:
                            layer = {}
                            layer['external'] = False
                            if project_group.baselayer_group:
                                layer['baselayer'] = True
                                if l.id == project_group.default_baselayer:
                                    layer['default_baselayer'] = True
                                else:
                                    layer['default_baselayer'] = False
                            else:
                                layer['baselayer'] = False
                                
                            layer['name'] = l.name
                            layer['title'] = l.title
                            layer['abstract'] = l.abstract
                            layer['visible'] = l.visible
                            layer['type'] = l.type
                            layer['queryable'] = l.queryable
                            layer['allow_download'] = l.allow_download
                            layer['detailed_info_enabled'] = l.detailed_info_enabled
                            layer['detailed_info_button_title'] = l.detailed_info_button_title
                            layer['detailed_info_html'] = l.detailed_info_html
    
                            layer['time_enabled'] = l.time_enabled
                            if layer['time_enabled']:
                                layer['ref'] = l.id
                                layer['time_enabled_field'] = l.time_enabled_field
                                layer['time_enabled_endfield'] = l.time_enabled_endfield
                                layer['time_presentation'] = l.time_presentation
                                layer['time_resolution_year'] = l.time_resolution_year
                                layer['time_resolution_month'] = l.time_resolution_month
                                layer['time_resolution_week'] = l.time_resolution_week
                                layer['time_resolution_day'] = l.time_resolution_day
                                layer['time_resolution_hour'] = l.time_resolution_hour
                                layer['time_resolution_minute'] = l.time_resolution_minute
                                layer['time_resolution_second'] = l.time_resolution_second
                                layer['time_default_value_mode'] = l.time_default_value_mode
                                layer['time_default_value'] = l.time_default_value
    
                                layer['time_resolution'] = l.time_resolution
    
                            layer['cached'] = l.cached
    
                            order = int(conf_group['groupOrder']) + l.order
                            layer['order'] = order
                            layer['single_image'] = l.single_image
                            layer['read_roles'] = read_roles
                            layer['write_roles'] = write_roles
                            layer['styles'] = get_layer_styles(l)
                            
                            if l.external_params:
                                params = json.loads(l.external_params)
                                layer['format'] = params.get('format')
    
                            try:
                                json_conf = ast.literal_eval(l.conf)
                                layer['conf'] = json.dumps(json_conf)
                            except:
                                layer['conf'] = "{\"fields\":[]}"
                                pass
    
                            datastore = Datastore.objects.get(id=l.datastore_id)
                            workspace = Workspace.objects.get(id=datastore.workspace_id)
                            
                            servers_list.append(workspace.server.name)
                            
                            if datastore.type == 'v_SHP' or datastore.type == 'v_PostGIS':
                                layer['is_vector'] = True
                            else:
                                layer['is_vector'] = False
    
                            defaultCrs = None
                            if str(datastore.type) == 'e_WMS':
                                defaultCrs = 'EPSG:4326'
                            else:
                                defaultCrs = l.native_srs
    
                            crs_code = int(defaultCrs.split(':')[1])
                            if crs_code in core_utils.get_supported_crs():
                                epsg = core_utils.get_supported_crs()[crs_code]
                                layer['crs'] = {
                                    'crs': defaultCrs,
                                    'units': epsg['units']
                                }
                                used_crs.append(epsg)
                                
                            layer['native_srs'] = l.native_srs
                            layer['native_extent'] = l.native_extent
                            layer['latlong_extent'] = l.latlong_extent
                            layer['opacity'] = 1
                            layer['wms_url'] = core_utils.get_wms_url(workspace)
                            layer['wms_url_no_auth'] = core_utils.get_wms_url(workspace)
                            if datastore.type.startswith('v_'):
                                layer['wfs_url'] = core_utils.get_wfs_url(workspace)
                                layer['wfs_url_no_auth'] = core_utils.get_wfs_url(workspace)
                            elif datastore.type.startswith('c_'):
                                layer['wcs_url'] = core_utils.get_wcs_url(workspace)
                            layer['namespace'] = workspace.uri
                            layer['workspace'] = workspace.name
                            layer['metadata'] = core_utils.get_layer_metadata_uuid(l)
                            layer['metadata_url'] = core_utils.get_catalog_url_from_uuid(request, layer['metadata'], lang=language.part2b)
                            if l.cached:
                                layer['cache_url'] = core_utils.get_cache_url(workspace)
                            else:
                                layer['cache_url'] = core_utils.get_wms_url(workspace)
    
                            if datastore.type == 'e_WMS':
                                layer['legend'] = ""
                            else:
                                ls = get_default_style(l)
                                if ls is None:
                                    print 'CAPA SIN ESTILO POR DEFECTO: ' + l.name
                                    layer['legend'] = core_utils.get_wms_url(workspace) + '?SERVICE=WMS&VERSION=1.1.1&layer=' + l.name + '&REQUEST=getlegendgraphic&FORMAT=image/png&LEGEND_OPTIONS=forceLabels:on'
                                    layer['legend_no_auth'] = core_utils.get_wms_url(workspace) + '?SERVICE=WMS&VERSION=1.1.1&layer=' + l.name + '&REQUEST=getlegendgraphic&FORMAT=image/png&LEGEND_OPTIONS=forceLabels:on'
                                    layer['legend_graphic'] = core_utils.get_wms_url(workspace) + '?SERVICE=WMS&VERSION=1.1.1&layer=' + l.name + '&REQUEST=getlegendgraphic&FORMAT=image/png&LEGEND_OPTIONS=forceLabels:on'
                                    layer['legend_graphic_no_auth'] = core_utils.get_wms_url(workspace) + '?SERVICE=WMS&VERSION=1.1.1&layer=' + l.name + '&REQUEST=getlegendgraphic&FORMAT=image/png&LEGEND_OPTIONS=forceLabels:on'
    
                                else:
                                    if not ls.has_custom_legend:
                                        layer['legend'] = core_utils.get_wms_url(workspace) + '?SERVICE=WMS&VERSION=1.1.1&layer=' + l.name + '&REQUEST=getlegendgraphic&FORMAT=image/png&LEGEND_OPTIONS=forceLabels:on'
                                        layer['legend_no_auth'] = core_utils.get_wms_url(workspace) + '?SERVICE=WMS&VERSION=1.1.1&layer=' + l.name + '&REQUEST=getlegendgraphic&FORMAT=image/png&LEGEND_OPTIONS=forceLabels:on'
                                        layer['legend_graphic'] = core_utils.get_wms_url(workspace) + '?SERVICE=WMS&VERSION=1.1.1&layer=' + l.name + '&REQUEST=getlegendgraphic&FORMAT=image/png&LEGEND_OPTIONS=forceLabels:on'
                                        layer['legend_graphic_no_auth'] = core_utils.get_wms_url(workspace) + '?SERVICE=WMS&VERSION=1.1.1&layer=' + l.name + '&REQUEST=getlegendgraphic&FORMAT=image/png&LEGEND_OPTIONS=forceLabels:on'
                                    else:
                                        layer['legend'] = ls.custom_legend_url
                                        layer['legend_no_auth'] = ls.custom_legend_url
                                        layer['legend_graphic'] = core_utils.get_wms_url(workspace) + '?SERVICE=WMS&VERSION=1.1.1&layer=' + l.name + '&REQUEST=getlegendgraphic&FORMAT=image/png&LEGEND_OPTIONS=forceLabels:on'
                                        layer['legend_graphic_no_auth'] = core_utils.get_wms_url(workspace) + '?SERVICE=WMS&VERSION=1.1.1&layer=' + l.name + '&REQUEST=getlegendgraphic&FORMAT=image/png&LEGEND_OPTIONS=forceLabels:on'
                            
                            layer['timeout'] = l.timeout
                            _, urlicon = utils.get_layer_img(l.id, None)
                            layer['icon'] = urlicon 
                            layers.append(layer)
    
                            w = {}
                            w['name'] = workspace.name
                            w['wms_url'] = core_utils.get_wms_url(workspace)
                            workspaces.append(w)
                        idx = idx + 1
    
                    except Exception as e:
                        logger.exception('error getting layer conf')
                        datastore = Datastore.objects.get(id=l.datastore_id)
                        workspace = Workspace.objects.get(id=datastore.workspace_id)
    
                        error = {
                            'layer': l.name,
                            'datastore': datastore.name,
                            'workspace': workspace.name,
                            'error': str(e)
                        }
                        errors.append(error)
                        pass
                    
                else:
                    allows_getmap = False
                    
                    layer = {}
                    if project_group.baselayer_group:
                        layer['baselayer'] = True
                        if l.id == project_group.default_baselayer:
                            layer['default_baselayer'] = True
                        else:
                            layer['default_baselayer'] = False
                    else:
                        layer['baselayer'] = False
                    
                    layer['opacity'] = 1
                    layer['external'] = True   
                    layer['name'] = l.name
                    layer['title'] = l.title
                    layer['abstract'] = l.abstract
                    layer['visible'] = l.visible
                    layer['queryable'] = l.queryable
                    layer['cached'] = l.cached
                    layer['type'] = l.type
                    layer['detailed_info_enabled'] = l.detailed_info_enabled
                    layer['detailed_info_button_title'] = l.detailed_info_button_title
                    layer['detailed_info_html'] = l.detailed_info_html
                    layer['metadata'] = core_utils.get_layer_metadata_uuid(l)
                    layer['metadata_url'] = core_utils.get_catalog_url_from_uuid(request, layer['metadata'], lang=language.part2b)
                    
                    if l.cached:
                        if l.external_params:
                            params = json.loads(l.external_params)
                            layer['cache_url'] = params.get('cache_url')
                            layer['format'] = params.get('format')
                        
                    if l.external_params:
                        params = json.loads(l.external_params)
                        if l.type == 'WMTS' and not 'capabilities' in params:
                            version = settings.WMTS_MAX_VERSION
                            if 'version' in params:
                                version = params['version']
                            wmts = WebMapTileService(params['url'], version=version)
                            capabilities = wmts.getServiceXML()
                            params['capabilities'] = capabilities
                            l.external_params = json.dumps(params)
                            l.save()
                        layer.update(params)
    
                    order = int(conf_group['groupOrder']) + l.order
                    layer['order'] = order
                    
                    layer['timeout'] = l.timeout
                    layers.append(layer)
            
            if allows_getmap:
                if len(servers_list) > 0 :
                    allows_getmap = all(elem == servers_list[0] for elem in servers_list)        
            conf_group['allows_getmap'] = allows_getmap
            
            if len(layers) > 0:
                ordered_layers = sorted(layers, key=itemgetter('order'), reverse=True)
                conf_group['layers'] = ordered_layers
                layer_groups.append(conf_group)

        supported_crs = core_utils.get_supported_crs(used_crs)

        ordered_layer_groups = sorted(layer_groups, key=itemgetter('groupOrder'), reverse=True)

        resource_manager = 'gvsigol'
        if 'gvsigol_plugin_alfresco' in gvsigol.settings.INSTALLED_APPS:
            resource_manager = 'alfresco'



        auth_urls = []
        for s in Server.objects.all():
            if settings.BASE_URL in s.frontend_url:
                u = s.frontend_url.replace(settings.BASE_URL, '')
                auth_urls.append(u + '/wms')
            else:
                auth_urls.append(s.frontend_url + '/wms')

        project_tools = json.loads(project.tools) if project.tools else get_available_tools(True, True)

        gvsigol_app = None
        for app in settings.INSTALLED_APPS:
            if 'gvsigol_app_' in app:
                gvsigol_app = app

        conf = {
            'pid': pid,
            'gvsigol_app': gvsigol_app,
            'project_name': project.name,
            'project_title': project.title,
            'project_logo': project.logo.url.replace(settings.BASE_URL, ''),
            'project_logo_link': project.logo_link,
            'project_image': project.image.url.replace(settings.BASE_URL, ''),
            'project_tools': project_tools,
            "view": {
                "restricted_extent": project.restricted_extent,
                "extent": project.extent.split(','),
                "center_lat": project.center_lat,
                "center_lon": project.center_lon,
                "zoom": project.zoom,
                "max_zoom_level": gvsigol.settings.MAX_ZOOM_LEVEL
            },
            'supported_crs': supported_crs,
            'workspaces': workspaces,
            'layerGroups': ordered_layer_groups,
            'tools': gvsigol.settings.GVSIGOL_TOOLS,
            'tile_size': gvsigol.settings.TILE_SIZE,
            'is_public_project': project.is_public,
            'show_project_icon': project.show_project_icon,
            'selectable_groups': project.selectable_groups,
            'resource_manager': resource_manager,
            'remote_auth': settings.AUTH_WITH_REMOTE_USER,
            'temporal_advanced_parameters': gvsigol.settings.TEMPORAL_ADVANCED_PARAMETERS,
            'errors': errors,
            'auth_urls': auth_urls
        }
        
        if language:
            conf['language'] = {
                'iso639_1': request.LANGUAGE_CODE,
                'iso639_2b': language.part2b
            }
        

        if request.user and request.user.id:
            conf['user'] = {
                'id': request.user.id,
                'username': request.user.first_name + ' ' + request.user.last_name,
                'login': request.user.username,
                'email': request.user.email,
                'permissions': {
                    'is_superuser': is_superuser(request.user),
                    'roles': core_utils.get_group_names_by_user(request.user)
                },
                'credentials': {
                    'username': request.session['username'],
                    'password': request.session['password']
                }
            }
        if is_shared_view:
            view_name = request.POST.get('shared_view_name')
            shared_view = SharedView.objects.get(name__exact=view_name)
            state = json.loads(shared_view.state)

            conf = core_utils.set_state(conf, state)

        return HttpResponse(json.dumps(conf, indent=4), content_type='application/json')


def toc_update(request, pid):
    if request.method == 'POST':
        project = Project.objects.get(id=int(pid))
        toc = request.POST.get('toc')
        project.toc_order = toc
        project.save()

        toc_object = json.loads(toc)
        server = geographic_servers.get_instance().get_server_by_id(id)
        server.createOrUpdateSortedGeoserverLayerGroup(toc_object)

        return HttpResponse(json.dumps({'success': True}, indent=4), content_type='application/json')

    else:
        project = Project.objects.get(id=int(pid))
        toc = json.loads(project.toc_order)
        for g in toc:
            group = toc.get(g)
            ordered_layers = sorted(group.get('layers').iteritems(), key=lambda (x, y): y['order'], reverse=True)
            group['layers'] = ordered_layers
        ordered_toc = sorted(toc.iteritems(), key=lambda (x, y): y['order'], reverse=True)
        return render(request, 'toc_update.html', {'toc': ordered_toc, 'pid': pid})

def export(request, pid):
    p = Project.objects.get(id=pid)
    image = ''
    if "no_project.png" in p.image.url:
        media_url = settings.MEDIA_URL[:-1]
        image = p.image.url.replace(media_url, '')
    else:
        image = p.image.url
        
    return render(request, 'app_print_template.html', {'print_logo_url': urllib.unquote(image)})

def ogc_services(request):
    wms = ServiceUrl.objects.filter(type='WMS')
    wmts = ServiceUrl.objects.filter(type='WMTS')
    wfs = ServiceUrl.objects.filter(type='WFS')
    csw = ServiceUrl.objects.filter(type='CSW')
    return render(request, 'services_view.html', {'wms': wms, 'wmts': wmts, 'wfs': wfs, 'csw': csw})

def select_public_project(request):
    public_projects = Project.objects.filter(is_public=True)

    projects = []

    if len (public_projects) <= 0:
        return render(request, 'select_public_project.html', {'projects': projects})

    elif len (public_projects) == 1:
        return redirect('load', project_name=public_projects[0].name)

    elif len (public_projects) > 1:
        for pp in public_projects:
            p = Project.objects.get(id=pp.id)
            image = ''
            if "no_project.png" in p.image.url:
                media_url = settings.MEDIA_URL[:-1]
                image = p.image.url.replace(media_url, '')
            else:
                image = p.image.url

            project = {}
            project['id'] = p.id
            project['name'] = p.name
            project['title'] = p.title
            project['description'] = p.description
            project['image'] = urllib.unquote(image)
            projects.append(project)

        return render(request, 'select_public_project.html', {'projects': projects})


def documentation(request):
    lang = request.LANGUAGE_CODE
    response = {
        'intro_url': '/docs/web/intro/' + lang + '/',
        'admin_guide_url': '/docs/web/dashboard/' + lang + '/',
        'viewer_url': '/docs/web/viewer/' + lang + '/',
        'plugins_url': '/docs/web/plugins/' + lang + '/',
        'mobile_url': '/docs/mobile/' + lang + '/'
    }
    return render(request, 'documentation.html', response)

def do_save_shared_view(pid, description, view_state, expiration, user, internal=False):
    name = datetime.date.today().strftime("%Y%m%d") + get_random_string(length=32)
    shared_url = settings.BASE_URL + '/gvsigonline/core/load_shared_view/' + name
    shared_project = SharedView(
        name=name,
        project_id=pid,
        description=description,
        url=shared_url,
        state=view_state,
        expiration_date=expiration,
        created_by=user.username,
        internal=internal
    )
    shared_project.save()
    return shared_project

#@login_required(login_url='/gvsigonline/auth/login_user/')
def save_shared_view(request):
    if request.method == 'POST':
        pid = int(request.POST.get('pid'))
        if not core_utils.can_read_project(request.user, pid):
            return HttpResponse(json.dumps({'result': 'illegal_operation', 'shared_url': ''}, indent=4), content_type='folder/json')
        #emails = request.POST.get('emails')
        description = request.POST.get('description')
        view_state = request.POST.get('view_state')
        expiration_date = datetime.datetime.now() + datetime.timedelta(days = settings.SHARED_VIEW_EXPIRATION_TIME)
        shared_view = do_save_shared_view(pid, description, view_state, expiration_date, request.user)
        #for email in emails.split(';'):
        #    send_shared_view(email, shared_url)
        response = {
            'shared_url': shared_view.url
        }
        return HttpResponse(json.dumps(response, indent=4), content_type='folder/json')
    
def send_shared_view(destination, shared_url):
    if gvsigol.settings.EMAIL_BACKEND_ACTIVE:       
        subject = _(u'Shared view')
        
        body = _(u'Shared view') + ':\n\n'   
        body = body + '  - ' + _(u'Link') + ': ' + shared_url + '\n'
        
        toAddress = [destination]           
        fromAddress = gvsigol.settings.EMAIL_HOST_USER
        
        print 'Restore message: ' + body
        try:
            send_mail(subject, body, fromAddress, toAddress, fail_silently=False)
        except Exception as e:
            print e.smtp_error
            pass

@cache_control(max_age=86400)
def load_shared_view(request, view_name):
    try:
        shared_view = SharedView.objects.get(name__exact=view_name)
        project = Project.objects.get(id=shared_view.project_id)
        if shared_view.internal and not request.user.is_superuser:
            raise PermissionDenied
        if not (project.is_public or request.user.is_authenticated()):
            shared_url = settings.BASE_URL + '/gvsigonline/auth/login_user/?next=/gvsigonline/core/load_shared_view/' + view_name
            return redirect(shared_url)

        has_image = True
        if "no_project.png" in project.image.url:
            has_image = False

        plugins_config = core_utils.get_plugins_config()
        response = render(request, 'viewer.html', {
            'has_image': has_image,
            'supported_crs': core_utils.get_supported_crs(),
            'project': project,
            'project_logo': project.logo.url.replace(settings.BASE_URL, ''),
            'project_image': project.image.url.replace(settings.BASE_URL, ''),
            'pid': project.id,
            'extra_params': json.dumps(request.GET),
            'plugins_config': plugins_config,
            'is_shared_view': True,
            'shared_view_name': shared_view.name,
            'main_page': settings.LOGOUT_PAGE_URL
            }
        )

        #Expira la caché cada día
        tomorrow = datetime.datetime.now() + datetime.timedelta(days = 1)
        tomorrow = datetime.datetime.replace(tomorrow, hour=0, minute=0, second=0)
        expires = datetime.datetime.strftime(tomorrow, "%a, %d-%b-%Y %H:%M:%S GMT")
        response.set_cookie('key', expires = expires)

        return response

    except Exception:
        return redirect('not_found_sharedview')

@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def shared_view_list(request):

    shared_view_list = SharedView.objects.filter(internal=False)

    shared_views = []
    for sv in shared_view_list:
        shared_view = {}
        shared_view['id'] = sv.id
        shared_view['url'] = sv.url
        shared_view['expiration_date'] = sv.expiration_date
        shared_view['description'] = sv.description
        shared_views.append(shared_view)

    response = {
        'shared_views': shared_views
    }
    return render(request, 'shared_view_list.html', response)

@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def shared_view_delete(request, svid):
    if request.method == 'POST':
        shared_view = SharedView.objects.get(id=int(svid))
        shared_view.delete()

        response = {
            'deleted': True
        }
        return HttpResponse(json.dumps(response, indent=4), content_type='project/json')

def not_found_sharedview(request):
    response = render(request, 'not_found_sharedview.html', {})
    response.status_code = 404
    return response

@login_required(login_url='/gvsigonline/auth/login_user/')
@superuser_required
def project_clone(request, pid):
    try:
        if request.user.is_superuser:
            project = Project.objects.get(id=int(pid))
        else:
            project = Project.objects.get(id=int(pid), created_by__exact=request.user.username)
    except:
        project = None
    if request.method == 'POST':
        form = CloneProjectForm(request.POST)
        if form.is_valid():
            if not project:
                form.add_error(None, _('Operation not allowed on project: ')+str(pid))
            name = form.cleaned_data.get('project_name')
            title = form.cleaned_data.get('project_title')
            target_workspace_name = form.cleaned_data.get('target_workspace')
            target_datastore_name = form.cleaned_data.get('target_datastore')
            target_server = form.cleaned_data.get('target_server')
            copy_data = form.cleaned_data.get('copy_data')
            permission_choice = form.cleaned_data.get('permission_choice')

            if target_server.frontend_url.endswith("/"):
                uri = target_server.frontend_url + target_workspace_name
            else:
                uri = target_server.frontend_url + "/" + target_workspace_name

            values = {
                "name": target_workspace_name,
                "description": target_workspace_name + " ws",
                "uri": uri,
                "wms_endpoint": target_server.getWmsEndpoint(target_workspace_name),
                "wfs_endpoint": target_server.getWfsEndpoint(target_workspace_name),
                "wcs_endpoint": target_server.getWcsEndpoint(target_workspace_name),
                "wmts_endpoint": target_server.getWmtsEndpoint(target_workspace_name),
                "cache_endpoint": target_server.getCacheEndpoint(target_workspace_name)
            }
            target_workspace = services_utils.create_workspace(target_server.id, target_workspace_name, uri, values, request.user.username)
            if target_workspace:
                datastore = services_utils.create_datastore(request.user.username, target_datastore_name, target_workspace)
                project.clone(target_datastore=datastore, name=name, title=title, copy_layer_data=copy_data, permissions=permission_choice)
                messages.add_message(request, messages.INFO, _('The project was successfully cloned.'))
                return redirect('project_update', pid=project.id)
    else:
        form = CloneProjectForm()
        if not project:
            form.add_error(None, _('Operation not allowed on project: ')+str(pid))
    servers = Server.objects.all()
    return render(request, 'project_clone.html', {'form': form, 'servers': servers})

    