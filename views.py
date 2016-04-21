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
from gvsigol_services.models import LayerGroup
from gvsigol_auth.models import UserGroup, UserGroupUser
from django.contrib.auth.decorators import login_required
from django.utils.translation import ugettext as _
from django.contrib.auth.models import User
from gvsigol_auth.utils import is_admin_user
from gvsigol import settings
import utils as core_utils
import urllib
import json

def not_found_view(request):
    response = render_to_response('404.html', {}, context_instance=RequestContext(request))
    response.status_code = 404
    return response

@login_required(login_url='/gvsigonline/auth/login_user/')
def home(request):
    user = User.objects.get(username=request.user.username)
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
   
    return render_to_response('home.html', {'projects': projects}, RequestContext(request))

@login_required(login_url='/gvsigonline/auth/login_user/')
@is_admin_user
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
@is_admin_user
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
            if 'group-' in key:
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
                    extent = extent
                )
            else:
                project = Project(
                    name = name,
                    description = description,
                    center_lat = latitude,
                    center_lon = longitude,
                    zoom = int(zoom),
                    extent = extent
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
@is_admin_user
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
            if 'group-' in key:
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
@is_admin_user
def project_delete(request, pid):        
    if request.method == 'POST':
        project = Project.objects.get(id=int(pid))
        project.delete()
            
        response = {
            'deleted': True
        }     
        return HttpResponse(json.dumps(response, indent=4), content_type='project/json')