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
from geoserver.workspace import Workspace
'''
@author: Javier Rodrigo <jrodrigo@scolab.es>
'''
from django.core.mail import send_mail
from django.utils.translation import ugettext as _
from gvsigol_core.models import Project, ProjectUserGroup, ProjectLayerGroup
from gvsigol_services.models import LayerGroup, Layer
from gvsigol_auth.models import UserGroup, UserGroupUser
from gvsigol import settings
import json
import psycopg2
import os
from numpy import genfromtxt
import importlib
import gvsigol

def is_valid_project(user, project_name):
    valid = False
    try:
        if user.is_superuser:
            valid = True
        else:
            project = Project.objects.get(name__exact=project_name)   
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

def toc_update_layer_group(old_layergroup, old_name, new_name, title): 
    projects_by_layergroup = ProjectLayerGroup.objects.filter(layer_group=old_layergroup)
    for p in projects_by_layergroup:
        json_toc = p.project.toc_order
        toc = json.loads(json_toc)
        toc[old_name]['name'] = new_name
        toc[old_name]['title'] = title
        toc[new_name] = toc.pop(old_name)
        p.project.toc_order = json.dumps(toc)
        p.project.save()
   
def toc_remove_layergroups(toc_structure, layer_groups): 
    if not toc_structure:
        return json.dumps({})
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


def toc_move_layer(layer, old_layer_group): 
    projects_by_layergroup = ProjectLayerGroup.objects.filter(layer_group=old_layer_group)
    for p in projects_by_layergroup:
        json_toc = p.project.toc_order
        toc = json.loads(json_toc)
        if toc.has_key(old_layer_group.name) and layer.name in toc.get(old_layer_group.name).get('layers'):
            del toc.get(old_layer_group.name).get('layers')[layer.name]
        p.project.toc_order = json.dumps(toc)
        p.project.save()
        
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
        
def get_geoserver_base_url(request, url):
    '''
    geoserver_url = None
    if 'username' in request.session:
        if request.session['username'] is not None and request.session['password'] is not None:
            split_geoserver_url = url.split('//')
            geoserver_url = split_geoserver_url[0] + '//' + request.session['username'] + ':' + request.session['password'] + '@' + split_geoserver_url[1]
    else:
        geoserver_url = url
        
    return geoserver_url
    '''
    return url
   
def get_wms_url(request, workspace):
    '''
    wms_url = None
    if 'username' in request.session:
        if request.session['username'] is not None and request.session['password'] is not None:
            split_wms_url = workspace.wms_endpoint.split('//')
            wms_url = split_wms_url[0] + '//' + request.session['username'] + ':' + request.session['password'] + '@' + split_wms_url[1]
    else:
        wms_url = workspace.wms_endpoint
        
    return wms_url
    '''
    return workspace.wms_endpoint

def get_wfs_url(request, workspace):
    '''
    wfs_url = None
    if 'username' in request.session:
        if request.session['username'] is not None and request.session['password'] is not None:
            split_wfs_url = workspace.wfs_endpoint.split('//')
            wfs_url = split_wfs_url[0] + '//' + request.session['username'] + ':' + request.session['password'] + '@' + split_wfs_url[1]
    else:
        wfs_url = workspace.wfs_endpoint
        
    return wfs_url
    '''
    return workspace.wfs_endpoint

def get_cache_url(request, workspace):
    '''
    cache_url = None
    if 'username' in request.session:
        if request.session['username'] is not None and request.session['password'] is not None:
            split_cache_url = workspace.cache_endpoint.split('//')
            cache_url = split_cache_url[0] + '//' + request.session['username'] + ':' + request.session['password'] + '@' + split_cache_url[1]
    else:
        cache_url = workspace.cache_endpoint
        
    return cache_url
    '''
    if workspace.wmts_endpoint and workspace.wmts_endpoint.__len__() > 0:
        return workspace.wmts_endpoint
    
    return workspace.cache_endpoint

def get_catalog_url(request, layer):   
    catalog_url = ''
    if 'gvsigol_plugin_catalog' in settings.INSTALLED_APPS:
        from gvsigol_plugin_catalog import settings as catalog_settings
        from gvsigol_plugin_catalog.models import  LayerMetadata
        
        url = catalog_settings.CATALOG_URL
        try: 
            lm = LayerMetadata.objects.get(layer=layer)
            if 'username' in request.session:
                if request.session['username'] is not None and request.session['password'] is not None:
                    split_catalog_url = url.split('//')
                    catalog_url = split_catalog_url[0] + '//' + request.session['username'] + ':' + request.session['password'] + '@' + split_catalog_url[1]  + 'catalog.search#/metadata/' + lm.metadata_uuid
            else:
                catalog_url = url + 'catalog.search#/metadata/' + lm.metadata_uuid
        except Exception as e:
            pass
        
    return catalog_url

def get_layer_metadata_uuid(layer):   
    if 'gvsigol_plugin_catalog' in settings.INSTALLED_APPS:
        from gvsigol_plugin_catalog import settings as catalog_settings
        from gvsigol_plugin_catalog.models import  LayerMetadata
        
        try: 
            lm = LayerMetadata.objects.get(layer=layer)
            return lm.metadata_uuid
        except Exception as e:
            pass
    return ''

def update_layer_metadata_uuid(layer, uuid):   
    if 'gvsigol_plugin_catalog' in settings.INSTALLED_APPS:
        #from gvsigol_plugin_catalog import settings as catalog_settings
        from gvsigol_plugin_catalog.models import  LayerMetadata
        
        try: 
            lm = LayerMetadata.objects.get(layer=layer)
            lm.metadata_uuid = uuid
            lm.save()
        except LayerMetadata.DoesNotExist as e:
            lm = LayerMetadata()
            lm.layer = layer
            lm.metadata_uuid = uuid
            lm.save()
        except LayerMetadata.MultipleObjectsReturned as e:
            lm = LayerMetadata.objects.filter(layer=layer).delete()
            lm = LayerMetadata()
            lm.layer = layer
            lm.metadata_uuid = uuid
            lm.save()
            

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
    fromAddress = settings.EMAIL_HOST_USER
    send_mail(subject, body, fromAddress, toAddress, fail_silently=False)
    
def send_reset_password_email(email, temp_pass):
            
    subject = _(u'New password')
    
    body = _(u'This is your new temporary password') + ':\n\n'
    
    body = body + '  - ' + _(u'Password') + ': ' + temp_pass + '\n\n'
    
    toAddress = [email]           
    fromAddress = settings.EMAIL_HOST_USER
    send_mail(subject, body, fromAddress, toAddress, fail_silently=False)
    

supported_crs = {}
supported_crs_array = []
def get_supported_crs(used_crs=None):   
    global supported_crs
    global supported_crs_array
    if (not supported_crs) or used_crs:
        
        if settings.USE_DEFAULT_SUPPORTED_CRS:
            for item in settings.SUPPORTED_CRS.items():
                supported_crs_array.append(item[1])
            supported_crs = settings.SUPPORTED_CRS
            return settings.SUPPORTED_CRS
        
        supported_crs = {}
        
        file_crs = genfromtxt(os.path.join(settings.BASE_DIR, 'gvsigol_core/static/crs_axis_order/mapaxisorder.csv'), skip_header=1)
        
        db = settings.DATABASES['default']
        
        dbhost = settings.DATABASES['default']['HOST']
        dbport = settings.DATABASES['default']['PORT']
        dbname = settings.DATABASES['default']['NAME']
        dbuser = settings.DATABASES['default']['USER']
        dbpassword = settings.DATABASES['default']['PASSWORD']
        
        #connection = get_connection(dbhost, dbport, dbname, dbuser, dbpassword)
        try:
            connection = psycopg2.connect("host=" + dbhost +" port=" + dbport +" dbname=" + dbname +" user=" + dbuser +" password="+ dbpassword);
            connection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            print "Connect ... "
        
        except StandardError, e:
            print "Failed to connect!", e
            return []
        cursor = connection.cursor()
        
        try:        
            create_schema = "SELECT * FROM public.spatial_ref_sys ORDER BY srid;"       
            cursor.execute(create_schema)
            rows = cursor.fetchall()
    
        except StandardError, e:
            print "SQL Error", e
            if not e.pgcode == '42710':
                return supported_crs   
            cursor.close();
            connection.close();
                
        for row in rows:
            s = row[4]
            
            unit_found = s.find('+units=')
            unit_const = '+units='.__len__()
            if unit_found > -1:
                data = s[unit_found+unit_const:unit_found+unit_const+1]
                if data == 'm':
                    unit = 'meter'
            else:
                unit = 'degree'
            
            
            s2 = row[3]
            data = s2[s2.find('[')+1:s2.find(',')]
            data = data.replace('"', '')
                
            axis_order = ''
            if row[2] in file_crs and row[4]:
                axis_order = ' +axis=neu'
            
            if row[4]:
                crs = {
                    'code': row[1] + ':' + str(row[2]),
                    'title': data,
                    'definition': row[4] + axis_order,
                    'units': unit+'s'
                }
            
            if not used_crs:
                supported_crs[row[0]] = crs
                supported_crs_array.append(crs)
            else:
                for crs in used_crs:
                    current_crs = row[1]+':'+str(row[2])
                    if current_crs == crs['code']:
                        supported_crs[str(row[0])] = crs
                        supported_crs_array.append(crs)

    return supported_crs    
   
def get_supported_crs_array(used_crs=None):  
    global supported_crs_array
    if (not supported_crs_array) or used_crs:   
        get_supported_crs(used_crs)
    return supported_crs_array
     
def get_plugins_config():
    plugins_config = {}
    for plugin in gvsigol.settings.INSTALLED_APPS:
        if 'gvsigol_app_' in plugin or 'gvsigol_plugin_' in plugin:
            try:
                plugin_settings = importlib.import_module(plugin + ".settings")
                settings_dict = {}
                for config_var in dir(plugin_settings):
                    if not config_var.startswith("__"):
                        settings_dict[config_var] = getattr(plugin_settings, config_var)
                if len(settings_dict) > 0:
                    plugins_config[plugin] = settings_dict
            except ImportError:
                pass
    return plugins_config