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
from models import Project, ProjectUserGroup, ProjectLayerGroup
from gvsigol_services.models import Workspace, Datastore, Layer, LayerGroup
from gvsigol_auth.models import UserGroup, UserGroupUser
from django.contrib.auth.decorators import login_required
from django.utils.translation import ugettext as _
from django.contrib.auth.models import User
from gvsigol_auth.utils import admin_required, is_admin_user
import utils as core_utils
from gvsigol_services.backend_geocoding import geocoder
from gvsigol_services.backend_mapservice import backend as mapservice_backend
from gvsigol import settings
import gvsigol_services.utils as services_utils
from operator import itemgetter
import gvsigol
import urllib
import random
import string
import json

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
    if len (projects_by_user) > 0:
        for ua in projects_by_user:
            a = Project.objects.get(id=ua.project_id)
            image = ''
            if "no_project.png" in a.image.url:
                image = a.image.url.replace(settings.MEDIA_URL, '')
            else:
                image = a.image.url
                
            project = {}
            project['id'] = a.id
            project['name'] = a.name
            project['description'] = a.description
            project['image'] = urllib.unquote(image)
            projects.append(project)
            
    if len (projects_by_user) == 1 and not is_admin_user(user) and from_login:
        return redirect('project_load', pid=projects_by_user[0].project_id)
    else:
        return render_to_response('home.html', {'projects': projects}, RequestContext(request))

@login_required(login_url='/gvsigonline/auth/login_user/')
@admin_required
def project_list(request):
    
    project_list = Project.objects.all()
    
    projects = []
    for p in project_list:
        project = {}
        project['id'] = p.id
        project['name'] = p.name
        project['description'] = p.description
        projects.append(project)
                      
    response = {
        'projects': projects
    }     
    return render_to_response('project_list.html', response, context_instance=RequestContext(request))

@login_required(login_url='/gvsigonline/auth/login_user/')
@admin_required
def project_add(request):
    if request.method == 'POST':
        name = request.POST.get('project-name')
        description = request.POST.get('project-description')
        latitude = request.POST.get('center-lat')
        longitude = request.POST.get('center-lon')
        extent = request.POST.get('extent')
        zoom = request.POST.get('zoom')
            
        has_image = False
        if 'project-image' in request.FILES:
            has_image = True
                
        assigned_layergroups = []
        for key in request.POST:
            if 'layergroup-' in key:
                assigned_layergroups.append(int(key.split('-')[1]))
                
        assigned_usergroups = []
        for key in request.POST:
            if 'usergroup-' in key:
                assigned_usergroups.append(int(key.split('-')[1]))
                
        exists = False
        projects = Project.objects.all()
        for p in projects:
            if name == p.name:
                exists = True
                
        layergroups = LayerGroup.objects.exclude(name='__default__')
        groups = core_utils.get_all_groups()
        if name == '':
            message = _(u'You must enter an project name')
            return render_to_response('project_add.html', {'message': message, 'layergroups': layergroups, 'groups': groups}, context_instance=RequestContext(request))
                
        if not exists:
            project = None
            if has_image:
                project = Project(
                    name = name,
                    description = description,
                    image = request.FILES['project-image'],
                    center_lat = latitude,
                    center_lon = longitude,
                    zoom = int(zoom),
                    extent = extent,
                    toc_order = core_utils.get_json_toc(assigned_layergroups)
                )
            else:
                project = Project(
                    name = name,
                    description = description,
                    center_lat = latitude,
                    center_lon = longitude,
                    zoom = int(zoom),
                    extent = extent,
                    toc_order = core_utils.get_json_toc(assigned_layergroups)
                )
            project.save()
            
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
            
        else:
            message = _(u'Project name already exists')
            return render_to_response('project_add.html', {'message': message, 'layergroups': layergroups, 'groups': groups}, context_instance=RequestContext(request))
        
        return redirect('project_list')
    
    else:
        layergroups = LayerGroup.objects.exclude(name='__default__')
        groups = core_utils.get_all_groups()
        return render_to_response('project_add.html', {'layergroups': layergroups, 'groups': groups}, context_instance=RequestContext(request))
    
    
@login_required(login_url='/gvsigonline/auth/login_user/')
@admin_required
def project_update(request, pid):
    if request.method == 'POST':
        name = request.POST.get('project-name')
        description = request.POST.get('project-description')
        latitude = request.POST.get('center-lat')
        longitude = request.POST.get('center-lon')
        extent = request.POST.get('extent')
        zoom = request.POST.get('zoom')
                
        assigned_layergroups = []
        for key in request.POST:
            if 'layergroup-' in key:
                assigned_layergroups.append(int(key.split('-')[1]))
                
        assigned_usergroups = []
        for key in request.POST:
            if 'usergroup-' in key:
                assigned_usergroups.append(int(key.split('-')[1]))
                
        project = Project.objects.get(id=int(pid))
               
        exists = False
        projects = Project.objects.all()
        for p in projects:
            if name == p.name:
                exists = True
                
        sameName = False
        if project.name == name:
            sameName = True
            
            
        if sameName:
            project.description = description
            project.center_lat = latitude
            project.center_lon = longitude
            project.zoom = int(zoom)
            project.extent = extent
            project.toc_order = core_utils.get_json_toc(assigned_layergroups)
            project.save()
            
            for lg in ProjectLayerGroup.objects.filter(project_id=project.id):
                lg.delete()
                    
            for ug in ProjectUserGroup.objects.filter(project_id=project.id):
                ug.delete()
                
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
                
            return redirect('project_list')
            
        else:
            if not exists:
                project.name = name
                project.description = description
                project.center_lat = latitude
                project.center_lon = longitude
                project.zoom = int(zoom)
                project.extent = extent
                project.toc_order = core_utils.get_json_toc(assigned_layergroups)
                project.save()
                
                for lg in ProjectLayerGroup.objects.filter(project_id=project.id):
                    lg.delete()
                    
                for ug in ProjectUserGroup.objects.filter(project_id=project.id):
                    ug.delete()
                
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
                    
                return redirect('project_list')
                    
            else:
                message = _(u'Project name already exists')
                project = Project.objects.get(id=int(pid))    
                groups = core_utils.get_all_groups_checked_by_project(project)
                layer_groups = core_utils.get_all_layer_groups_checked_by_project(project)  
                return render_to_response('project_update.html', {'message': message, 'pid': pid, 'project': project, 'groups': groups, 'layergroups': layer_groups}, context_instance=RequestContext(request))
                
        
        
    else:
        project = Project.objects.get(id=int(pid))    
        groups = core_utils.get_all_groups_checked_by_project(project)
        layer_groups = core_utils.get_all_layer_groups_checked_by_project(project) 
        return render_to_response('project_update.html', {'pid': pid, 'project': project, 'groups': groups, 'layergroups': layer_groups}, context_instance=RequestContext(request))
    
    
@login_required(login_url='/gvsigonline/auth/login_user/')
@admin_required
def project_delete(request, pid):        
    if request.method == 'POST':
        project = Project.objects.get(id=int(pid))
        project.delete()
            
        response = {
            'deleted': True
        }     
        return HttpResponse(json.dumps(response, indent=4), content_type='project/json')
    
@login_required(login_url='/gvsigonline/auth/login_user/')
def project_load(request, pid):
    if core_utils.is_valid_project(request.user, pid):
        return render_to_response('viewer.html', {'supported_crs': gvsigol.settings.SUPPORTED_CRS, 'pid': pid}, context_instance=RequestContext(request))
    else:
        return render_to_response('illegal_operation.html', {}, context_instance=RequestContext(request))

@login_required(login_url='/gvsigonline/auth/login_user/')
def project_get_conf(request):
    if request.method == 'POST':
        pid = request.POST.get('pid')
        
        project = Project.objects.get(id=int(pid))
        toc = json.loads(project.toc_order)
            
        project_layers_groups = ProjectLayerGroup.objects.filter(project_id=project.id)
        layer_groups = []
        workspaces = []
        capabilities = mapservice_backend.getCapabilities(request.session)
        for project_group in project_layers_groups:            
            group = LayerGroup.objects.get(id=project_group.layer_group_id)
            
            conf_group = {}
            conf_group['groupTitle'] = group.title
            conf_group['groupId'] = ''.join(random.choice(string.ascii_uppercase) for i in range(6))
            conf_group['groupOrder'] = toc.get(group.name).get('order')
            conf_group['groupName'] = group.name
            conf_group['cached'] = group.cached
            layers_in_group = Layer.objects.filter(layer_group_id=group.id)
            layers = []
            for l in layers_in_group:
                read_roles = services_utils.get_read_roles(l)
                write_roles = services_utils.get_write_roles(l)
                
                layer = {}                
                layer['name'] = l.name
                layer['title'] = l.title
                layer['abstract'] = l.abstract
                layer['visible'] = l.visible 
                layer['queryable'] = l.queryable 
                layer['cached'] = l.cached
                layer['order'] = toc.get(group.name).get('layers').get(l.name).get('order')
                layer['single_image'] = l.single_image
                layer['read_roles'] = read_roles
                layer['write_roles'] = write_roles
                
                datastore = Datastore.objects.get(id=l.datastore_id)
                workspace = Workspace.objects.get(id=datastore.workspace_id)
                
                if datastore.type == 'v_SHP' or datastore.type == 'v_PostGIS': 
                    layer['is_vector'] = True
                else:
                    layer['is_vector'] = False
                
                properties = capabilities.contents[workspace.name + ':' + l.name]
                defaultCrs = properties.boundingBox[4]
                epsg = gvsigol.settings.SUPPORTED_CRS[defaultCrs.split(':')[1]]
                layer['crs'] = {
                    'crs': defaultCrs,
                    'units': epsg['units']
                }
                
                if properties.timepositions is not None:
                    layer['is_time_layer'] = True
                    layer['time_params'] = {
                        'default': properties.timepositions[0],
                        'values': ','.join(properties.timepositions)
                    }
                
                else:
                    layer['is_time_layer'] = False
                    
                split_wms_url = workspace.wms_endpoint.split('//')
                authenticated_wms_url = split_wms_url[0] + '//' + request.session['username'] + ':' + request.session['password'] + '@' + split_wms_url[1]
                layer['wms_url'] = authenticated_wms_url
                    
                split_wfs_url = workspace.wfs_endpoint.split('//')
                authenticated_wfs_url = split_wfs_url[0] + '//' + request.session['username'] + ':' + request.session['password'] + '@' + split_wfs_url[1]
                layer['wfs_url'] = authenticated_wfs_url
                layer['namespace'] = workspace.uri
                layer['workspace'] = workspace.name                
                #layer['wfs_url'] = workspace.wfs_endpoint
                
                if l.cached:  
                    split_cache_url = workspace.cache_endpoint.split('//')
                    authenticated_cache_url = split_cache_url[0] + '//' + request.session['username'] + ':' + request.session['password'] + '@' + split_cache_url[1]
                    layer['cache_url'] = authenticated_cache_url
                else:
                    layer['cache_url'] = authenticated_wms_url
                    
                layer['legend'] = authenticated_wms_url + '?SERVICE=WMS&VERSION=1.1.1&layer=' + l.name + '&REQUEST=getlegendgraphic&FORMAT=image/png'
                if 'http' in gvsigol.settings.GVSIGOL_CATALOG['URL']:
                    if l.metadata_uuid is not None and l.metadata_uuid != '':
                        split_catalog_url = gvsigol.settings.GVSIGOL_CATALOG['URL'].split('//')
                        authenticated_catalog_url = split_catalog_url[0] + '//' + request.session['username'] + ':' + request.session['password'] + '@' + split_catalog_url[1]  + 'catalog.search#/metadata/' + l.metadata_uuid
                        layer['metadata'] = authenticated_catalog_url
                        
                    else:
                        layer['metadata'] = ''
                    
                else:
                    layer['metadata'] = ''
                                                
                layers.append(layer)
                
                w = {}
                w['name'] = workspace.name
                w['wms_url'] = workspace.wms_endpoint
                workspaces.append(w)
            
            if len(layers) > 0:   
                ordered_layers = sorted(layers, key=itemgetter('order'))
                conf_group['layers'] = ordered_layers
                layer_groups.append(conf_group)
            
        ordered_layer_groups = sorted(layer_groups, key=itemgetter('groupOrder'))
        
        geoserver_url = gvsigol.settings.GVSIGOL_SERVICES['URL']
        split_geoserver_url = geoserver_url.split('//')
        authenticated_geoserver_url = split_geoserver_url[0] + '//' + request.session['username'] + ':' + request.session['password'] + '@' + split_geoserver_url[1]
            
        conf = {
            'pid': pid,
            'user': {
                'id': request.user.id,
                'username': request.user.first_name + ' ' + request.user.last_name,
                'login': request.user.username,
                'email': request.user.email,
                'permissions': {
                    'is_admin': is_admin_user(request.user),
                    'roles': core_utils.get_groups_by_user(request.user)
                }
            },
            "view": {
                "center_lat": project.center_lat,
                "center_lon": project.center_lon, 
                "zoom": project.zoom 
            }, 
            'supported_crs': gvsigol.settings.SUPPORTED_CRS,
            'workspaces': workspaces,
            'layerGroups': ordered_layer_groups,
            'tools': gvsigol.settings.GVSIGOL_TOOLS,
            'base_layers': gvsigol.settings.GVSIGOL_BASE_LAYERS,
            'is_public_project': False,
            'geoserver_base_url': authenticated_geoserver_url
        } 
        
        return HttpResponse(json.dumps(conf, indent=4), content_type='application/json')

        
        
    
def toc_update(request, pid):
    if request.method == 'POST':
        project = Project.objects.get(id=int(pid))
        toc = request.POST.get('toc')
        project.toc_order = toc
        project.save()       
        return HttpResponse(json.dumps({'success': True}, indent=4), content_type='application/json')
    
    else:
        project = Project.objects.get(id=int(pid))      
        toc = json.loads(project.toc_order)
        ordered_toc = sorted(toc.iteritems(), key=lambda (x, y): y['order'])
        return render_to_response('toc_update.html', {'toc': ordered_toc, 'pid': pid}, context_instance=RequestContext(request))
    
def search_candidates(request):
    if request.method == 'GET':
        query = request.GET.get('query')           
        suggestions = geocoder.search_candidates(query)
            
        return HttpResponse(json.dumps(suggestions, indent=4), content_type='application/json')

def get_location_address(request):
    if request.method == 'POST':
        query = request.POST.get('query')
        location = geocoder.get_location_address(query)
        
        return HttpResponse(json.dumps(location, indent=4), content_type='application/json')
    
def export(request, pid):   
    p = Project.objects.get(id=pid)
    image = ''
    if "no_project.png" in p.image.url:
        image = p.image.url.replace(settings.MEDIA_URL, '')
    else:
        image = p.image.url

    return render_to_response('app_print_template.html', {'print_logo_url': urllib.unquote(image)}, context_instance=RequestContext(request))