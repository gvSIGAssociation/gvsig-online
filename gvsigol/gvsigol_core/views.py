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
'''
@author: Javier Rodrigo <jrodrigo@scolab.es>
'''

from django.shortcuts import render_to_response, RequestContext, HttpResponse, redirect
from models import Project, ProjectUserGroup, ProjectLayerGroup, BaseLayer, BaseLayerProject
from gvsigol_services.models import Server, Workspace, Datastore, Layer, LayerGroup
from gvsigol_auth.models import UserGroup, UserGroupUser
from django.contrib.auth.decorators import login_required
from django.utils.translation import ugettext as _
from django.contrib.auth.models import User
from gvsigol_auth.utils import is_superuser, staff_required
import utils as core_utils
from gvsigol_services import geographic_servers
from django.views.decorators.cache import cache_control
from gvsigol import settings
import gvsigol_services.utils as services_utils
from operator import itemgetter
from django import apps
import gvsigol
import urllib
import random
import datetime
import string
import json
import ast
import re

from django.views.decorators.clickjacking import xframe_options_exempt

_valid_name_regex=re.compile("^[a-zA-Z_][a-zA-Z0-9_]*$")

def not_found_view(request):
    response = render_to_response('404.html', {}, context_instance=RequestContext(request))
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
    
    projects = []
    public_projects = []
    if request.user.is_superuser:
        for p in Project.objects.all():
            image = ''
            if "no_project.png" in p.image.url:
                image = p.image.url.replace(settings.MEDIA_URL, '')
            else:
                image = p.image.url
                
            project = {}
            project['id'] = p.id
            project['name'] = p.name
            project['title'] = p.title
            project['description'] = p.description
            project['image'] = urllib.unquote(image)
            
            if p.created_by == request.user.username:
                projects.append(project)
            else:
                if p.is_public:
                    public_projects.append(project)
                else:
                    projects.append(project)
            
    else:
        for p in Project.objects.all():
            image = ''
            if "no_project.png" in p.image.url:
                image = p.image.url.replace(settings.MEDIA_URL, '')
            else:
                image = p.image.url
                
            project = {}
            project['id'] = p.id
            project['name'] = p.name
            project['title'] = p.title
            project['description'] = p.description
            project['image'] = urllib.unquote(image)
            
            
            if p.created_by == request.user.username:    
                projects.append(project)
            
            if p.is_public:
                if p.created_by != request.user.username:    
                    public_projects.append(project)
            else:
                if p.created_by != request.user.username:
                    exists = False    
                    for ua in projects_by_user:
                        if p.id == ua.project_id:
                            exists = True
                    if exists:
                        projects.append(project) 
                        
    external_ldap_mode = True
    if 'AD' in settings.GVSIGOL_LDAP and settings.GVSIGOL_LDAP['AD'].__len__() > 0:
        external_ldap_mode = False

    return render_to_response('home.html', {'projects': projects, 'public_projects': public_projects, 'external_ldap_mode': external_ldap_mode}, RequestContext(request))                   

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
        'projects': projects
    }     
    return render_to_response('project_list.html', response, context_instance=RequestContext(request))

def get_core_tools(enabled=True):
    return [{
        'name': 'gvsigol_tool_zoom',
        'checked': enabled,
        'title': 'Herramientas de zoom',
        'description': 'Zoom más, zoom menos, ...'
    }, {
        'name': 'gvsigol_tool_info',
        'checked': enabled,
        'title': 'Información',
        'description': 'Información del mapa en un punto'
    }, {
        'name': 'gvsigol_tool_measure',
        'checked': enabled,
        'title': 'Herramientas de medida',
        'description': 'Permite medir áreas y distancias'
    }, {
        'name': 'gvsigol_tool_export',
        'checked': enabled,
        'title': 'Exportar a PDF',
        'description': 'Exporta la vista actual a PDF'
    }, {
        'name': 'gvsigol_tool_coordinate',
        'checked': enabled,
        'title': 'Buscar coordinates',
        'description': 'Centra el mapa en unas coordenadas dadas'
    }, {
        'name': 'gvsigol_tool_location',
        'checked': enabled,
        'title': 'Geolocalización',
        'description': 'Centra el mapa en la posición actual'
    }, {
        'name': 'gvsigol_tool_shareview',
        'checked': enabled,
        'title': 'Compartir vista',
        'description': 'Permite compartir la vista en su estado actual'
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
    
def get_available_tools(core_enabled=True, plugin_enabled=False):
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
    base_layers = BaseLayer.objects.all()
    if 'gvsigol_plugin_geocoding' in settings.INSTALLED_APPS:
        from gvsigol_plugin_geocoding.models import Provider 
        providers = Provider.objects.all()
        has_geocoding_plugin = providers.__len__() > 0
        
    project_tools = get_available_tools()
        
    if request.method == 'POST':
        name = request.POST.get('project-name')
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
            
        has_image = False
        if 'project-image' in request.FILES:
            has_image = True
        
        default_baselayer = None
        if 'default_base_layer_selected' in request.POST:
            default_baselayer = request.POST.get('default_base_layer_selected')
            
        assigned_baselayers = []
        assigned_layergroups = []
        assigned_usergroups = []
        for key in request.POST:
            if 'baselayer-' in key:
                assigned_baselayers.append(int(key.split('-')[1]))
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
        
        groups = None
        if request.user.is_superuser:
            groups = core_utils.get_all_groups()
        else:
            groups = core_utils.get_user_groups(request.user.username)
        
        if name == '':
            message = _(u'You must enter an project name')
            return render_to_response('project_add.html', {'message': message, 'layergroups': layergroups, 'tools': project_tools, 'groups': groups, 'base_layers': base_layers, 'has_geocoding_plugin': has_geocoding_plugin}, context_instance=RequestContext(request))
        
        if _valid_name_regex.search(name) == None:
            message = _(u"Invalid project name: '{value}'. Identifiers must begin with a letter or an underscore (_). Subsequent characters can be letters, underscores or numbers").format(value=name)
            return render_to_response('project_add.html', {'message': message, 'layergroups': layergroups, 'tools': project_tools, 'groups': groups, 'base_layers': base_layers, 'has_geocoding_plugin': has_geocoding_plugin}, context_instance=RequestContext(request))
         
        if not exists:
            project = None
            if has_image:
                project = Project(
                    name = name,
                    title = title,
                    description = description,
                    image = request.FILES['project-image'],
                    center_lat = latitude,
                    center_lon = longitude,
                    zoom = int(float(zoom)),
                    extent = extent,
                    toc_order = toc,
                    toc_mode = toc_mode,
                    created_by = request.user.username,
                    is_public = is_public,
                    tools = tools
                )
            else:
                project = Project(
                    name = name,
                    title = title,
                    description = description,
                    center_lat = latitude,
                    center_lon = longitude,
                    zoom = int(float(zoom)),
                    extent = extent,
                    toc_order = toc,
                    toc_mode = toc_mode,
                    created_by = request.user.username,
                    is_public = is_public,
                    tools = tools
                )
            project.save()
            
            for bly in assigned_baselayers:
                baselayer = BaseLayer.objects.get(id=bly)
                is_default = False
                if default_baselayer and int(default_baselayer) == baselayer.id:
                    is_default = True
                project_baselayer = BaseLayerProject(
                    project = project,
                    baselayer = baselayer,
                    is_default = is_default
                )
                project_baselayer.save()
            
            for alg in assigned_layergroups:
                layergroup = LayerGroup.objects.get(id=alg)
                project_layergroup = ProjectLayerGroup(
                    project = project,
                    layer_group = layergroup
                )
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
            return render_to_response('project_add.html', {'message': message, 'tools': project_tools , 'layergroups': layergroups, 'base_layers': base_layers, 'groups': groups, 'has_geocoding_plugin': has_geocoding_plugin}, context_instance=RequestContext(request))
        
       
        
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
            
        base_layers = BaseLayer.objects.all()
        
        return render_to_response('project_add.html', {'layergroups': layergroups, 'tools': project_tools, 'groups': groups, 'base_layers': base_layers, 'has_geocoding_plugin': has_geocoding_plugin}, context_instance=RequestContext(request))
    
    
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
        
        default_baselayer = None
        if 'default_base_layer_selected' in request.POST:
            default_baselayer = request.POST.get('default_base_layer_selected')
              
        assigned_baselayers = []
        assigned_layergroups = []
        assigned_usergroups = []
        for key in request.POST:
            if 'baselayer-' in key:
                assigned_baselayers.append(int(key.split('-')[1]))
            if 'layergroup-' in key:
                assigned_layergroups.append(int(key.split('-')[1]))
            if 'usergroup-' in key:
                assigned_usergroups.append(int(key.split('-')[1]))
                
        has_image = False
        if 'project-image' in request.FILES:
            has_image = True
        
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
        project.description = description
        project.center_lat = latitude
        project.center_lon = longitude
        project.zoom = int(float(zoom))
        project.extent = extent
        project.is_public = is_public
        project.toc_order = toc
        project.toc_mode = toc_mode
        project.tools = tools
        
        if has_image:
            project.image = request.FILES['project-image']
            
        project.save()
        
        for bl in BaseLayerProject.objects.filter(project_id=project.id):
            bl.delete()
        
        for lg in ProjectLayerGroup.objects.filter(project_id=project.id):
            lg.delete()
                
        for ug in ProjectUserGroup.objects.filter(project_id=project.id):
            ug.delete()
            
        
        for bly in assigned_baselayers:
            baselayer = BaseLayer.objects.get(id=bly)
            is_default = False
            if default_baselayer and int(default_baselayer) == baselayer.id:
                is_default = True
            project_baselayer = BaseLayerProject(
                project = project,
                baselayer = baselayer,
                is_default = is_default
            )
            project_baselayer.save()
            
        for alg in assigned_layergroups:
            layergroup = LayerGroup.objects.get(id=alg)
            project_layergroup = ProjectLayerGroup(
                project = project,
                layer_group = layergroup
            )
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
        base_layers = BaseLayer.objects.all()
        base_layers_project = BaseLayerProject.objects.filter(project=project)
        selected_base_layers=[]
        
        selected_base_layer=-1
        for base_layer_project in base_layers_project:
            selected_base_layers.append(base_layer_project.baselayer.id)
            if base_layer_project.is_default:
                selected_base_layer = base_layer_project.baselayer.id
        
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
        return render_to_response('project_update.html', {'tools': projectTools,'pid': pid, 'project': project, 'groups': groups, 'layergroups': layer_groups, 'base_layers': base_layers, 'selected_base_layers': selected_base_layers,'selected_base_layer': selected_base_layer, 'has_geocoding_plugin': has_geocoding_plugin, 'toc': ordered_toc}, context_instance=RequestContext(request))
    
    
@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def project_delete(request, pid):        
    if request.method == 'POST':
        project = Project.objects.get(id=int(pid))
        project.delete()
            
        response = {
            'deleted': True
        }     
        return HttpResponse(json.dumps(response, indent=4), content_type='project/json')
    
    
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
    if core_utils.is_valid_project(request.user, project_name):
        project = Project.objects.get(name__exact=project_name)
        
        has_image = True
        if "no_project.png" in project.image.url:
            has_image = False

        plugins_config = core_utils.get_plugins_config()
        response = render_to_response('viewer.html', {
            'has_image': has_image,
            'supported_crs': core_utils.get_supported_crs(),
            'project': project,
            'pid': project.id,
            'extra_params': json.dumps(request.GET),
            'plugins_config': plugins_config,
            'is_shared_view': False,
            },
            context_instance=RequestContext(request)
        )
        
        #Expira la caché cada día
        tomorrow = datetime.datetime.now() + datetime.timedelta(days = 1)
        tomorrow = datetime.datetime.replace(tomorrow, hour=0, minute=0, second=0)
        expires = datetime.datetime.strftime(tomorrow, "%a, %d-%b-%Y %H:%M:%S GMT")     
        response.set_cookie('key', expires = expires)
        
        return response
    
    else:
        return render_to_response('illegal_operation.html', {}, context_instance=RequestContext(request))
    

@cache_control(max_age=86400)
def load_public_project(request, project_name):
    project = Project.objects.get(name__exact=project_name)
        
    has_image = True
    if "no_project.png" in project.image.url:
        has_image = False

    plugins_config = core_utils.get_plugins_config()
    response = render_to_response('viewer.html', {
        'has_image': has_image,
        'supported_crs': core_utils.get_supported_crs(),
        'project': project,
        'pid': project.id,
        'extra_params': json.dumps(request.GET),
        'plugins_config': plugins_config,
        'is_shared_view': False,
        },
        context_instance=RequestContext(request)
    )
        
    #Expira la caché cada día
    tomorrow = datetime.datetime.now() + datetime.timedelta(days = 1)
    tomorrow = datetime.datetime.replace(tomorrow, hour=0, minute=0, second=0)
    expires = datetime.datetime.strftime(tomorrow, "%a, %d-%b-%Y %H:%M:%S GMT")     
    response.set_cookie('key', expires = expires)
        
    return response

    
@login_required(login_url='/gvsigonline/auth/login_user/')
@xframe_options_exempt
@cache_control(max_age=86400)
def portable_project_load(request, project_name):
    if core_utils.is_valid_project(request.user, project_name):
        project = Project.objects.get(name__exact=project_name)
        response = render_to_response('portable_viewer.html', {'supported_crs': core_utils.get_supported_crs(), 'project': project, 'pid': project.id, 'extra_params': json.dumps(request.GET)}, context_instance=RequestContext(request))
        #Expira la caché cada día
        tomorrow = datetime.datetime.now() + datetime.timedelta(days = 1)
        tomorrow = datetime.datetime.replace(tomorrow, hour=0, minute=0, second=0)
        expires = datetime.datetime.strftime(tomorrow, "%a, %d-%b-%Y %H:%M:%S GMT")     
        response.set_cookie('key', expires = expires)
        return response
    else:
        return render_to_response('illegal_operation.html', {}, context_instance=RequestContext(request))


@login_required(login_url='/gvsigonline/auth/login_user/')
def blank_page(request):
    return render_to_response('blank_page.html', {}, context_instance=RequestContext(request))


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
            conf_group['wms_endpoint'] = server.getWmsEndpoint()
            conf_group['wfs_endpoint'] = server.getWfsEndpoint()
            conf_group['cache_endpoint'] = server.getCacheEndpoint()
            layers_in_group = Layer.objects.filter(layer_group_id=group.id).order_by('order')
            layers = []
            user_roles = core_utils.get_group_names_by_user(request.user)
            
            idx = 0
            for l in layers_in_group:
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
                        layer['name'] = l.name
                        layer['title'] = l.title
                        layer['abstract'] = l.abstract
                        layer['visible'] = l.visible  
                        layer['queryable'] = l.queryable 
                        layer['highlight'] = l.highlight
                        if l.highlight:
                            layer['highlight_scale'] = int(l.highlight_scale)
                            
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
                        
                        try:
                            json_conf = ast.literal_eval(l.conf)
                            layer['conf'] = json.dumps(json_conf)
                        except:
                            layer['conf'] = "{\"fields\":[]}"
                            pass
                        
                        datastore = Datastore.objects.get(id=l.datastore_id)
                        workspace = Workspace.objects.get(id=datastore.workspace_id)
                        
                        if datastore.type == 'v_SHP' or datastore.type == 'v_PostGIS': 
                            layer['is_vector'] = True
                        else:
                            layer['is_vector'] = False
                        
                        layer_info = None
                        defaultCrs = None
                        if datastore.type == 'e_WMS':
                            defaultCrs = 'EPSG:4326'
                        else:
                            server = geographic_servers.get_instance().get_server_by_id(workspace.server.id)
                            (ds_type, layer_info) = server.getResourceInfo(workspace.name, datastore, l.name, "json")
                            if ds_type == 'imagemosaic':
                                ds_type = 'coverage'
                            defaultCrs = layer_info[ds_type]['srs']
                        
                        crs_code = int(defaultCrs.split(':')[1])
                        if crs_code in core_utils.get_supported_crs():
                            epsg = core_utils.get_supported_crs()[crs_code]
                            layer['crs'] = {
                                'crs': defaultCrs,
                                'units': epsg['units']
                            }
                            used_crs.append(epsg)
                        
                        layer['opacity'] = 1   
                        layer['wms_url'] = core_utils.get_wms_url(request, workspace)
                        layer['wms_url_no_auth'] = workspace.wms_endpoint
                        layer['wfs_url'] = core_utils.get_wfs_url(request, workspace)
                        layer['wfs_url_no_auth'] = workspace.wfs_endpoint
                        layer['namespace'] = workspace.uri
                        layer['workspace'] = workspace.name   
                        layer['metadata'] = core_utils.get_catalog_url(request, l)             
                        if l.cached:  
                            layer['cache_url'] = core_utils.get_cache_url(request, workspace)
                        else:
                            layer['cache_url'] = core_utils.get_wms_url(request, workspace)
                        
                        if datastore.type == 'e_WMS':
                            layer['legend'] = ""
                        else: 
                            ls = get_default_style(l)
                            if ls is None:
                                print 'CAPA SIN ESTILO POR DEFECTO: ' + l.name
                                layer['legend'] = core_utils.get_wms_url(request, workspace) + '?SERVICE=WMS&VERSION=1.1.1&layer=' + l.name + '&REQUEST=getlegendgraphic&FORMAT=image/png&LEGEND_OPTIONS=forceLabels:on'
                                layer['legend_no_auth'] = workspace.wms_endpoint + '?SERVICE=WMS&VERSION=1.1.1&layer=' + l.name + '&REQUEST=getlegendgraphic&FORMAT=image/png&LEGEND_OPTIONS=forceLabels:on'
                                layer['legend_graphic'] = core_utils.get_wms_url(request, workspace) + '?SERVICE=WMS&VERSION=1.1.1&layer=' + l.name + '&REQUEST=getlegendgraphic&FORMAT=image/png&LEGEND_OPTIONS=forceLabels:on'
                                layer['legend_graphic_no_auth'] = workspace.wms_endpoint + '?SERVICE=WMS&VERSION=1.1.1&layer=' + l.name + '&REQUEST=getlegendgraphic&FORMAT=image/png&LEGEND_OPTIONS=forceLabels:on'
                                    
                            else:
                                if not ls.has_custom_legend:
                                    layer['legend'] = core_utils.get_wms_url(request, workspace) + '?SERVICE=WMS&VERSION=1.1.1&layer=' + l.name + '&REQUEST=getlegendgraphic&FORMAT=image/png&LEGEND_OPTIONS=forceLabels:on'
                                    layer['legend_no_auth'] = workspace.wms_endpoint + '?SERVICE=WMS&VERSION=1.1.1&layer=' + l.name + '&REQUEST=getlegendgraphic&FORMAT=image/png&LEGEND_OPTIONS=forceLabels:on'
                                    layer['legend_graphic'] = core_utils.get_wms_url(request, workspace) + '?SERVICE=WMS&VERSION=1.1.1&layer=' + l.name + '&REQUEST=getlegendgraphic&FORMAT=image/png&LEGEND_OPTIONS=forceLabels:on'
                                    layer['legend_graphic_no_auth'] = workspace.wms_endpoint + '?SERVICE=WMS&VERSION=1.1.1&layer=' + l.name + '&REQUEST=getlegendgraphic&FORMAT=image/png&LEGEND_OPTIONS=forceLabels:on'
                                else:
                                    layer['legend'] = ls.custom_legend_url
                                    layer['legend_no_auth'] = ls.custom_legend_url
                                    layer['legend_graphic'] = core_utils.get_wms_url(request, workspace) + '?SERVICE=WMS&VERSION=1.1.1&layer=' + l.name + '&REQUEST=getlegendgraphic&FORMAT=image/png&LEGEND_OPTIONS=forceLabels:on'
                                    layer['legend_graphic_no_auth'] = workspace.wms_endpoint + '?SERVICE=WMS&VERSION=1.1.1&layer=' + l.name + '&REQUEST=getlegendgraphic&FORMAT=image/png&LEGEND_OPTIONS=forceLabels:on'
                            
                        layers.append(layer)
                        
                        w = {}
                        w['name'] = workspace.name
                        w['wms_url'] = workspace.wms_endpoint
                        workspaces.append(w)
                    idx = idx + 1
                
                except Exception as e:
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
                
            if len(layers) > 0:   
                ordered_layers = sorted(layers, key=itemgetter('order'), reverse=True)
                conf_group['layers'] = ordered_layers
                layer_groups.append(conf_group)
        
        supported_crs = core_utils.get_supported_crs(used_crs)
           
        ordered_layer_groups = sorted(layer_groups, key=itemgetter('groupOrder'), reverse=True)
        
        resource_manager = 'gvsigol'
        if 'gvsigol_plugin_alfresco' in gvsigol.settings.INSTALLED_APPS:
            resource_manager = 'alfresco'                

        bsly_projs = BaseLayerProject.objects.filter(project=project).order_by('order')
        
        base_layers = []
        for bsly_proj in bsly_projs:
            bsly = bsly_proj.baselayer
            
            base_layer = {}
            if bsly.type_params:
                bsly_params = json.loads(bsly.type_params)
                base_layer.update(bsly_params)
            
            base_layer['name'] = bsly.name
            base_layer['title'] = bsly.title
            base_layer['type'] = bsly.type
            base_layer['active'] = bsly_proj.is_default
            
            base_layers.append(base_layer)
        
        auth_urls = []    
        for s in Server.objects.all():
            auth_urls.append(s.frontend_url + '/wms')
        
        project_tools = json.loads(project.tools) if project.tools else get_available_tools(True, True)  
          
        conf = {
            'pid': pid,
            'project_name': project.name,
            'project_title': project.title,
            'project_image': project.image.url,
            'project_tools': project_tools,
            "view": {
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
            'base_layers': base_layers,
            'is_public_project': project.is_public,
            'resource_manager': resource_manager,
            'remote_auth': settings.AUTH_WITH_REMOTE_USER,
            'temporal_advanced_parameters': gvsigol.settings.TEMPORAL_ADVANCED_PARAMETERS,
            'errors': errors,
            'auth_urls': auth_urls
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
        return render_to_response('toc_update.html', {'toc': ordered_toc, 'pid': pid}, context_instance=RequestContext(request))
    
def export(request, pid):   
    p = Project.objects.get(id=pid)
    image = ''
    if "no_project.png" in p.image.url:
        image = p.image.url.replace(settings.MEDIA_URL, '')
    else:
        image = p.image.url

    return render_to_response('app_print_template.html', {'print_logo_url': urllib.unquote(image)}, context_instance=RequestContext(request))
    
def ogc_services(request):
    workspaces = Workspace.objects.filter(is_public=True)         
    return render_to_response('ogc_services.html', {'workspaces': workspaces}, RequestContext(request))

def select_public_project(request):  
    public_projects = Project.objects.filter(is_public=True)
    
    projects = []
    
    if len (public_projects) <= 0:
        return render_to_response('select_public_project.html', {'projects': projects}, RequestContext(request))
    
    elif len (public_projects) == 1:
        return redirect('load', project_name=public_projects[0].name)
    
    elif len (public_projects) > 1:
        for pp in public_projects:
            p = Project.objects.get(id=pp.id)
            image = ''
            if "no_project.png" in p.image.url:
                image = p.image.url.replace(settings.MEDIA_URL, '')
            else:
                image = p.image.url
                    
            project = {}
            project['id'] = p.id
            project['name'] = p.name
            project['title'] = p.title
            project['description'] = p.description
            project['image'] = urllib.unquote(image)
            projects.append(project)
            
        return render_to_response('select_public_project.html', {'projects': projects}, RequestContext(request))
    
        
def documentation(request):
    lang = request.LANGUAGE_CODE
    response = {
        'intro_url': settings.BASE_URL + '/docs/web/intro/' + lang + '/',
        'admin_guide_url': settings.BASE_URL + '/docs/web/dashboard/' + lang + '/',
        'viewer_url': settings.BASE_URL + '/docs/web/viewer/' + lang + '/',
        'plugins_url': settings.BASE_URL + '/docs/web/plugins/' + lang + '/',
        'mobile_url': settings.BASE_URL + '/docs/mobile/' + lang + '/'
    }
    return render_to_response('documentation.html', response, RequestContext(request))

@login_required(login_url='/gvsigonline/auth/login_user/')
def save_shared_view(request):
    if request.method == 'POST':
        pid = int(request.POST.get('pid'))
        description = request.POST.get('description')
        view_state = request.POST.get('view_state')
        
        name = ''.join(random.choice(string.ascii_uppercase) for i in range(10))
        shared_project = SharedView(
            name=name,
            project_id=pid,
            description=description,
            state=view_state,
            expiration_date=datetime.datetime.now() + datetime.timedelta(days = settings.SHARED_VIEW_EXPIRATION_TIME),
            created_by=request.user.username
        )
        shared_project.save()
        
        response = {
            'shared_url': settings.BASE_URL + '/gvsigonline/core/load_shared_view/' + name
        }
            
        return HttpResponse(json.dumps(response, indent=4), content_type='folder/json')
    
@cache_control(max_age=86400)
def load_shared_view(request, view_name):
    try:
        shared_view = SharedView.objects.get(name__exact=view_name)
        project = Project.objects.get(id=shared_view.project_id)
            
        has_image = True
        if "no_project.png" in project.image.url:
            has_image = False
    
        plugins_config = core_utils.get_plugins_config()
        response = render_to_response('viewer.html', {
            'has_image': has_image,
            'supported_crs': core_utils.get_supported_crs(),
            'project': project,
            'pid': project.id,
            'extra_params': json.dumps(request.GET),
            'plugins_config': plugins_config,
            'is_shared_view': True,
            'shared_view_name': shared_view.name
            },
            context_instance=RequestContext(request)
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
    
    shared_view_list = SharedView.objects.all()
    
    shared_views = []
    for sv in shared_view_list:
        shared_view = {}
        shared_view['id'] = sv.id
        shared_view['name'] = sv.name
        shared_view['created_by'] = sv.created_by
        shared_view['expiration_date'] = sv.expiration_date
        shared_view['description'] = sv.description
        shared_views.append(shared_view)
                      
    response = {
        'shared_views': shared_views
    }     
    return render_to_response('shared_view_list.html', response, context_instance=RequestContext(request))

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
    response = render_to_response('not_found_sharedview.html', {}, context_instance=RequestContext(request))
    response.status_code = 404
    return response
