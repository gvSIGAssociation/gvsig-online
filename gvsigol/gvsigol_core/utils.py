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
from geoserver.workspace import Workspace
'''
@author: Javier Rodrigo <jrodrigo@scolab.es>
'''
from django.core.mail import send_mail
from django.utils.translation import ugettext as _
from gvsigol_core.models import Project, ProjectUserGroup, ProjectLayerGroup, PublicViewerLayerGroup, PublicViewer, PublicViewerLayerGroup
from gvsigol_services.models import LayerGroup, Layer
from gvsigol_auth.models import UserGroup, UserGroupUser
import gvsigol.settings
import json

def is_valid_project(user, pid):
    valid = False
    try:
        if user.is_superuser:
            valid = True
        else:
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
    
def is_valid_public_project(pid):
    valid = False
    project = Project.objects.get(id=int(pid))
    if project.is_public:
        valid = True
                        
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

def get_user_groups(user):
    groups_list = UserGroup.objects.filter(name__exact='ug_' + user)
    
    groups = []
    for g in groups_list:
        if g.name != 'admin':
            group = {}
            group['id'] = g.id
            group['name'] = g.name
            group['description'] = g.description
            group['checked'] = True
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

def get_group_names_by_user(user):
    groups_by_user = UserGroupUser.objects.filter(user_id=user.id)
    
    groups = []
    for g in groups_by_user:
        user_group = UserGroup.objects.get(id=g.user_group_id)
        groups.append(user_group.name)
        
    return groups

def get_groups():
    groups = []
    for g in UserGroup.objects.all():
        groups.append(g.name)
        
    return groups


def get_all_groups_checked_by_project(request, project):
    groups_list = None
    if request.user.is_superuser:
        groups_list = UserGroup.objects.all()
    else:
        groups_list = UserGroup.objects.filter(name__exact='ug_' + request.user.username)
        
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

def get_all_layer_groups_checked_by_project(request, project):
    
    groups_list = None
    if request.user.is_superuser:
        groups_list = LayerGroup.objects.all()
    else:
        groups_list = LayerGroup.objects.filter(created_by__exact=request.user.username)

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

def get_all_layer_groups_in_public_viewer(public_viewer):
    groups_list = LayerGroup.objects.all()
    pv_layer_groups =  PublicViewerLayerGroup.objects.filter(public_viewer_id=public_viewer.id)
    checked = False
    
    layer_groups = []
    for g in groups_list:
        if g.name != '__default__':
            layer_group = {}
            for lgba in pv_layer_groups:
                if lgba.layer_group_id == g.id:
                    checked = True
                    layer_group['checked'] = checked
                           
            layer_group['id'] = g.id
            layer_group['name'] = g.name
            layer_group['title'] = g.title
            layer_groups.append(layer_group)
        
    return layer_groups

def get_json_toc(project_layergroups):
    toc = {}
    count1 = 1
    for lg in project_layergroups:
        lg_count = count1 * 1000
        toc_layergroup = {}
        layer_group = LayerGroup.objects.get(id=lg)
        toc_layergroup['name'] = layer_group.name
        toc_layergroup['title'] = layer_group.title
        toc_layergroup['order'] = lg_count
        
        toc_layers = {}
        layers_in_group = Layer.objects.filter(layer_group_id=layer_group.id)
        count2 = 1
        for l in layers_in_group: 
            toc_layers[l.name] = {
                'name': l.name,
                'title': l.title,
                'order': lg_count + count2
            }
            count2 += 1
        toc_layergroup['layers'] = toc_layers
        toc[layer_group.name] = toc_layergroup
        count1 += 1
        
    return json.dumps(toc)

def toc_add_layergroups(toc_structure, layer_groups): 
    json_toc = json.loads(toc_structure)
    indexes = []
    for key in json_toc:
        indexes.append(int(json_toc.get(key).get('order')))
    if len(indexes) <= 0:
        count1 = 1
    else:
        count1 = (max(indexes) / 1000) + 1
    for lg in layer_groups:
        lg_count = count1 * 1000
        toc_layergroup = {}
        layer_group = LayerGroup.objects.get(id=lg)
        toc_layergroup['name'] = layer_group.name
        toc_layergroup['title'] = layer_group.title
        toc_layergroup['order'] = lg_count
        
        toc_layers = {}
        layers_in_group = Layer.objects.filter(layer_group_id=layer_group.id)
        count2 = 1
        for l in layers_in_group: 
            toc_layers[l.name] = {
                'name': l.name,
                'title': l.title,
                'order': lg_count + count2
            }
            count2 += 1
        toc_layergroup['layers'] = toc_layers
        json_toc[layer_group.name] = toc_layergroup
        count1 += 1
        
    return json.dumps(json_toc)

def toc_update_layer_group(old_layergroup, old_name, new_name): 
    projects_by_layergroup = ProjectLayerGroup.objects.filter(layer_group=old_layergroup)
    for p in projects_by_layergroup:
        json_toc = p.project.toc_order
        toc = json.loads(json_toc)
        toc[old_name]['name'] = new_name
        toc[new_name] = toc.pop(old_name)
        p.project.toc_order = json.dumps(toc)
        p.project.save()
        
    if len(PublicViewer.objects.all()) == 1:
        public_viewer = PublicViewer.objects.all()[0]
        json_toc2 = public_viewer.toc_order
        toc2 = json.loads(json_toc2)
        try:
            toc2[old_name]['name'] = new_name
            toc2[new_name] = toc2.pop(old_name)
            public_viewer.toc_order = json.dumps(toc2)
            public_viewer.save()
            
        except Exception as e:
            print _('Public viewer TOC is empty')
   
def toc_remove_layergroups(toc_structure, layer_groups): 
    json_toc = json.loads(toc_structure)
    for lg in layer_groups:
        layergroup = LayerGroup.objects.get(id=lg)
        if json_toc.has_key(layergroup.name):
            del json_toc[layergroup.name]
            
    return json.dumps(json_toc)

def toc_add_layer(layer): 
    projects_by_layergroup = ProjectLayerGroup.objects.filter(layer_group=layer.layer_group)
    for p in projects_by_layergroup:
        json_toc = p.project.toc_order
        toc = json.loads(json_toc)
        if toc.has_key(layer.layer_group.name):
            indexes = []
            for l in toc.get(layer.layer_group.name).get('layers'):
                indexes.append(int(toc.get(layer.layer_group.name).get('layers').get(l).get('order')))
            
            if len(indexes) > 0:
                order = max(indexes) + 1
            else:
                lg_order = toc.get(layer.layer_group.name).get('order')
                order = int(lg_order) + 1
                
            toc.get(layer.layer_group.name).get('layers')[layer.name] = {
                'name': layer.name,
                'title': layer.title,
                'order': order
            }
        p.project.toc_order = json.dumps(toc)
        p.project.save()
        
    if len(PublicViewer.objects.all()) == 1:
        public_viewer = PublicViewer.objects.all()[0]
        json_toc2 = public_viewer.toc_order
        toc2 = json.loads(json_toc2)
        if toc2.has_key(layer.layer_group.name):
            indexes = []
            for l in toc2.get(layer.layer_group.name).get('layers'):
                indexes.append(int(toc2.get(layer.layer_group.name).get('layers').get(l).get('order')))
            
            if len(indexes) > 0:
                order = max(indexes) + 1
            else:
                lg_order = toc2.get(layer.layer_group.name).get('order')
                order = int(lg_order) + 1
                
            toc2.get(layer.layer_group.name).get('layers')[layer.name] = {
                'name': layer.name,
                'title': layer.title,
                'order': order
            }
        public_viewer.toc_order = json.dumps(toc2)
        public_viewer.save()


def toc_move_layer(layer, old_layer_group): 
    projects_by_layergroup = ProjectLayerGroup.objects.filter(layer_group=old_layer_group)
    for p in projects_by_layergroup:
        json_toc = p.project.toc_order
        toc = json.loads(json_toc)
        if toc.has_key(old_layer_group.name):
            del toc.get(old_layer_group.name).get('layers')[layer.name]
        p.project.toc_order = json.dumps(toc)
        p.project.save()
        
    if len(PublicViewer.objects.all()) == 1:
        public_viewer = PublicViewer.objects.all()[0]
        json_toc2 = public_viewer.toc_order
        toc2 = json.loads(json_toc2)
        if toc2.has_key(old_layer_group.name):
            del toc2.get(old_layer_group.name).get('layers')[layer.name]
        public_viewer.toc_order = json.dumps(toc2)
        public_viewer.save()
        
    toc_add_layer(layer)

def toc_remove_layer(layer): 
    projects_by_layergroup = ProjectLayerGroup.objects.filter(layer_group=layer.layer_group)
    for p in projects_by_layergroup:
        json_toc = p.project.toc_order
        toc = json.loads(json_toc)
        if toc.has_key(layer.layer_group.name):
            del toc.get(layer.layer_group.name).get('layers')[layer.name]
        p.project.toc_order = json.dumps(toc)
        p.project.save()
        
    if len(PublicViewer.objects.all()) == 1:
        public_viewer = PublicViewer.objects.all()[0]
        json_toc2 = public_viewer.toc_order
        toc2 = json.loads(json_toc2)
        if toc2.has_key(layer.layer_group.name):
            del toc2.get(layer.layer_group.name).get('layers')[layer.name]
        public_viewer.toc_order = json.dumps(toc2)
        public_viewer.save()
        
def get_geoserver_base_url(request, url):
    geoserver_url = None
    if 'username' in request.session:
        if request.session['username'] is not None and request.session['password'] is not None:
            split_geoserver_url = url.split('//')
            geoserver_url = split_geoserver_url[0] + '//' + request.session['username'] + ':' + request.session['password'] + '@' + split_geoserver_url[1]
    else:
        geoserver_url = url
        
    return geoserver_url
        
def get_wms_url(request, workspace):
    wms_url = None
    if 'username' in request.session:
        if request.session['username'] is not None and request.session['password'] is not None:
            split_wms_url = workspace.wms_endpoint.split('//')
            wms_url = split_wms_url[0] + '//' + request.session['username'] + ':' + request.session['password'] + '@' + split_wms_url[1]
    else:
        wms_url = workspace.wms_endpoint
        
    return wms_url

def get_wfs_url(request, workspace):
    wfs_url = None
    if 'username' in request.session:
        if request.session['username'] is not None and request.session['password'] is not None:
            split_wfs_url = workspace.wfs_endpoint.split('//')
            wfs_url = split_wfs_url[0] + '//' + request.session['username'] + ':' + request.session['password'] + '@' + split_wfs_url[1]
    else:
        wfs_url = workspace.wfs_endpoint
        
    return wfs_url

def get_cache_url(request, workspace):
    cache_url = None
    if 'username' in request.session:
        if request.session['username'] is not None and request.session['password'] is not None:
            split_cache_url = workspace.cache_endpoint.split('//')
            cache_url = split_cache_url[0] + '//' + request.session['username'] + ':' + request.session['password'] + '@' + split_cache_url[1]
    else:
        cache_url = workspace.cache_endpoint
        
    return cache_url

def get_catalog_url(request, url, layer):
    catalog_url = None
    if 'username' in request.session:
        if request.session['username'] is not None and request.session['password'] is not None:
            split_catalog_url = url.split('//')
            catalog_url = split_catalog_url[0] + '//' + request.session['username'] + ':' + request.session['password'] + '@' + split_catalog_url[1]  + 'catalog.search#/metadata/' + layer.metadata_uuid
    else:
        catalog_url = url + 'catalog.search#/metadata/' + layer.metadata_uuid
        
    return catalog_url
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