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
from iso639 import languages
from future.utils import string_types
from future.builtins import int
from django.core.validators import URLValidator
import logging
import sys
logger = logging.getLogger("gvsigol")


def can_read_project(user, project):
    """
    Checks whether the user has permissions to read provied project.
    It accepts a project instance, a project name or a project id.
    """
    try:
        if isinstance(project, string_types):
            project = Project.objects.get(name__exact=project)
        elif isinstance(project, int):
            project = Project.objects.get(pk=project)
        if project.is_public:
            return True
        if user.is_superuser:
            return True
        if UserGroupUser.objects.filter(user_id=user.id, user_group__projectusergroup__project_id=project.id).count() > 0:
            return True
    except Exception as e:
        print(e)
    return False

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
                    #layer_group['multiselect'] = lgba.multiselect
                    layer_group['baselayer_group'] = lgba.baselayer_group
                    if lgba.baselayer_group:
                        layer_group['default_baselayer'] = lgba.default_baselayer
                           
            layer_group['id'] = g.id
            layer_group['name'] = g.name
            layer_group['title'] = g.title
            layer_groups.append(layer_group)
            
    for aux in layer_groups:
        if not 'baselayer_group' in aux:
            aux['baselayer_group'] = False
        
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
        try:
            toc[old_name]['name'] = new_name
            toc[old_name]['title'] = title
            toc[new_name] = toc.pop(old_name)
        except Exception as e:
            if old_name == '__default_baselayergroup__':
                toc[old_name] = {
                    "layers": {}, 
                    "order": 990000, 
                    "name": old_name, 
                    "title": title
                }
            pass
        p.project.toc_order = json.dumps(toc)
        p.project.save()
            
   
def toc_remove_layergroups(toc_structure, layer_groups): 
    if not toc_structure:
        return json.dumps({})
    json_toc = json.loads(toc_structure)
    for lg in layer_groups:
        layergroup = LayerGroup.objects.get(id=lg)
        if layergroup.name in json_toc:
            del json_toc[layergroup.name]
            
    return json.dumps(json_toc)

def toc_add_layer(layer): 
    projects_by_layergroup = ProjectLayerGroup.objects.filter(layer_group=layer.layer_group)
    for p in projects_by_layergroup:
        json_toc = p.project.toc_order
        try:
            toc = json.loads(json_toc)
            if layer.layer_group.name in toc:
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
        except Exception:
            pass


def toc_move_layer(layer, old_layer_group): 
    projects_by_layergroup = ProjectLayerGroup.objects.filter(layer_group=old_layer_group)
    for p in projects_by_layergroup:
        json_toc = p.project.toc_order
        try:
            toc = json.loads(json_toc)
            if old_layer_group.name in toc and layer.name in toc.get(old_layer_group.name).get('layers'):
                del toc.get(old_layer_group.name).get('layers')[layer.name]
            p.project.toc_order = json.dumps(toc)
            p.project.save()
        except Exception:
            pass
        
    toc_add_layer(layer)

def toc_remove_layer(layer): 
    projects_by_layergroup = ProjectLayerGroup.objects.filter(layer_group=layer.layer_group)
    for p in projects_by_layergroup:
        json_toc = p.project.toc_order
        try:
            toc = json.loads(json_toc)
            if layer.layer_group.name in toc:
                del toc.get(layer.layer_group.name).get('layers')[layer.name]
            p.project.toc_order = json.dumps(toc)
            p.project.save()
        except Exception:
            #Si json.loads da error en el parseo no se hace nada, se pasa al siguiente e impedimos que pete y se corte la ejecucíón
            pass

def get_absolute_url(url, headers):
    try:
        # first check if it is an absolute url
        validate = URLValidator(schemes=['https','http'])
        validate(url)
        return url
    except:
        # relative URL
        pass
    base_url = settings.BASE_URL
    try:
        origin = headers.get('HTTP_ORIGIN')
        if origin != base_url:
            if origin in settings.ALLOWED_HOST_NAMES:
                base_url = origin
            else:
                logger.warning("Not allowed HTTP_ORIGIN: " + origin)
    except:
        pass
    return base_url + url

def get_geoserver_base_url(request, url):
    return url
   
def get_wms_url(workspace):
    url = workspace.wms_endpoint.replace(settings.BASE_URL, '')
    return url

def get_wfs_url(workspace):
    url = workspace.wfs_endpoint.replace(settings.BASE_URL, '')
    return url

def get_wcs_url(workspace):
    url = workspace.wcs_endpoint.replace(settings.BASE_URL, '')
    return url

def get_cache_url(workspace):
    if workspace.wmts_endpoint and workspace.wmts_endpoint.__len__() > 0:
        url = workspace.wmts_endpoint.replace(settings.BASE_URL, '')
        return url
    
    url = workspace.cache_endpoint.replace(settings.BASE_URL, '')
    return url

def get_catalog_url(request, layer):   
    catalog_url = ''
    if 'gvsigol_plugin_catalog' in settings.INSTALLED_APPS:
        from gvsigol_plugin_catalog import settings as catalog_settings
        from gvsigol_plugin_catalog.models import  LayerMetadata
        
        url = catalog_settings.CATALOG_URL
        try: 
            lm = LayerMetadata.objects.get(layer=layer)
            catalog_url = get_catalog_url_from_uuid(request, lm.metadata_uuid, url)
        except Exception as e:
            pass
        
    return catalog_url

def get_catalog_url_from_uuid(request, metadata_uuid, baseUrl=None, lang=None):
    metadata_url = ''
    if metadata_uuid and 'gvsigol_plugin_catalog' in settings.INSTALLED_APPS:
        if lang is None:
            lang = get_iso_language(request).part2b
        if not baseUrl:
            from gvsigol_plugin_catalog import settings as catalog_settings
            baseUrl = catalog_settings.CATALOG_BASE_URL
        try:
            if 'username' in request.session:
                if request.session['username'] is not None and request.session['password'] is not None:
                    split_catalog_url = baseUrl.split('//')
                    baseUrl = split_catalog_url[0] + '//' + request.session['username'] + ':' + request.session['password'] + '@' + split_catalog_url[1]
            metadata_url = baseUrl + '/srv/' + lang + '/catalog.search#/metadata/' + metadata_uuid
        except Exception as e:
            pass
        
    return metadata_url

def get_layer_metadata_uuid(layer):
    if 'gvsigol_plugin_catalog' in settings.INSTALLED_APPS:
        from gvsigol_plugin_catalog.models import  LayerMetadata
        
        try: 
            lm = LayerMetadata.objects.get(layer=layer)
            return lm.metadata_uuid
        except Exception as e:
            pass
    return ''

def update_layer_metadata_uuid(layer, uuid):
    if 'gvsigol_plugin_catalog' in settings.INSTALLED_APPS:
        from gvsigol_plugin_catalog.models import  LayerMetadata
        
        try: 
            lm = LayerMetadata.objects.get(layer=layer)
            if uuid != '':
                lm.metadata_uuid = uuid
                lm.save()
                return
            else:
                lm.delete()
                return
        except LayerMetadata.MultipleObjectsReturned as e:
            lm = LayerMetadata.objects.filter(layer=layer).delete()
        except LayerMetadata.DoesNotExist as e:
            pass
        if uuid != '':
            lm = LayerMetadata()
            lm.layer = layer
            lm.metadata_uuid = uuid
            lm.save()

def sendMail(user, password):
            
    subject = _('New user account')
    
    first_name = ''
    last_name = ''
    try:
        first_name = str(user.first_name, 'utf-8')
        
    except TypeError:
        first_name = user.first_name
        
    try:
        last_name = str(user.last_name, 'utf-8')
        
    except TypeError:
        last_name = user.last_name
    
    body = _('Account data') + ':\n\n'   
    body = body + '  - ' + _('Username') + ': ' + user.username + '\n'
    body = body + '  - ' + _('First name') + ': ' + first_name + '\n'
    body = body + '  - ' + _('Last name') + ': ' + last_name + '\n'
    body = body + '  - ' + _('Email') + ': ' + user.email + '\n'
    body = body + '  - ' + _('Password') + ': ' + password + '\n'
    
    toAddress = [user.email]           
    fromAddress = settings.EMAIL_HOST_USER
    send_mail(subject, body, fromAddress, toAddress, fail_silently=False)
    
def send_reset_password_email(email, temp_pass):
            
    subject = _('New password')
    
    body = _('This is your new temporary password') + ':\n\n'
    
    body = body + '  - ' + _('Password') + ': ' + temp_pass + '\n\n'
    
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
            for item in list(settings.SUPPORTED_CRS.items()):
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
            print("Connect ... ")
        
        except Exception as e:
            print("Failed to connect!", e)
            return []
        cursor = connection.cursor()
        
        try:        
            create_schema = "SELECT * FROM public.spatial_ref_sys ORDER BY srid;"       
            cursor.execute(create_schema)
            rows = cursor.fetchall()
    
        except Exception as e:
            print("SQL Error", e)
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

def set_state(conf, state):
    for conf_lg in conf['layerGroups']:
        for state_lg in state['layerGroups']:
            if conf_lg['groupName'] == state_lg['groupName']:
                conf_lg['visible'] = state_lg['visible']
                for conf_l in conf_lg['layers']:
                    for state_l in state_lg['layers']:
                        if conf_l['name'] == state_l['name']:
                            conf_l['visible'] = state_l['visible']
                            conf_l['opacity'] = state_l['opacity']
                            conf_l['order'] = state_l['order']
                            conf_l['baselayer'] = state_l['baselayer']
                            if state_l['baselayer']:
                                conf_l['default_baselayer'] = state_l['default_baselayer']
                            
    conf['view'] = {}
    conf['view'] = state['view']
                
    return conf

def get_iso_language(request, default_lang='en'):
    try:
        return languages.get(part1=request.LANGUAGE_CODE)
    except:
        return languages.get(part1=default_lang)

def is_manage_process(exclude_runserver=False, exclude_testserver=False):
    if sys.argv[0].lower().endswith('manage') or sys.argv[0].lower().endswith('manage.py'):
        if len(sys.argv) == 1:
            return True
        elif len(sys.argv) > 1:
            if exclude_runserver and exclude_testserver:
                return (sys.argv[1] != 'runserver' and sys.argv[1] != 'testserver')
            elif exclude_runserver:
                return (sys.argv[1] != 'runserver')
            elif exclude_testserver:
                return (sys.argv[1] != 'testserver')
            else:
                return True
    return False

def is_gvsigol_process():
    from gvsigol.celery import is_celery_process
    return (not is_celery_process() and not is_manage_process(exclude_runserver=True, exclude_testserver=True))

def get_canonical_epsg3857_extent(extent_str):
    """
    Ensures the center of the extent is within the EPSG:3857 projection bounds
    """
    try:
        epsg3857_min_x = -20037508.34
        epsg3857_max_x = 20037508.34
        epsg3857_min_y = -20037508.34
        epsg3857_max_y = 20037508.34
        
        extent = extent_str.split(",")
        min_x = float(extent[0])
        min_y = float(extent[1])
        max_x = float(extent[2])
        max_y = float(extent[3])
        
        extent_width = max_x - min_x
        center_x = min_x + extent_width / 2.0
        
        if (center_x < epsg3857_min_x):
            # we first move the extent to pure negative coordinates to ensure the module brings the center to
            # the "right" world, then we undo this movement to move the center to the right location
            center_x = (center_x + epsg3857_min_x) % (2*epsg3857_min_x) + epsg3857_min_x
        elif (center_x > epsg3857_max_x):
            center_x = (center_x + epsg3857_max_x) % (2*epsg3857_max_x) + epsg3857_max_x
        
        min_x = center_x - extent_width / 2.0
        max_x = center_x + extent_width / 2.0
        
        extent_height = max_y - min_y
        center_y = min_y + extent_height / 2.0

        if (center_y < epsg3857_min_y):
            center_y = (center_y + epsg3857_min_y) % (2*epsg3857_min_y) + epsg3857_min_y
        elif (center_y > epsg3857_max_y):
            center_y = (center_y + epsg3857_max_y) % (2*epsg3857_max_y) + epsg3857_max_y

        min_y = center_y - extent_height / 2.0
        max_y = center_y + extent_height / 2.0
        return str(min_x) + "," + str(min_y) + "," + str(max_x) + "," + str(max_y)
    except:
        logger.exception("Wrong extent")
        return extent_str

GOL_APP_SETTINGS = None
try:
    for app in settings.INSTALLED_APPS:
        if app.startswith("gvsigol_app_"):
            importlib.import_module(app+".settings")
            GOL_APP_SETTINGS = importlib.import_module(app+".settings")
            break
except:
    pass

def get_app_setting(key, default=None):
    """
    Gets the value of a variable from the gvsigol installed app or None
    if the variable does not exist.
    For instance, if the installed app is "gvsigol_app_test", then
    get_app_setting("MYVAR") gets the value of the variable
    gvsigol_app_test.settings.MYVAR
    """
    if GOL_APP_SETTINGS:
        return getattr(GOL_APP_SETTINGS, key, default)


def get_setting(key, default=None):
    """
    Gets the value of a variable from the gvsigol installed app, or from
    the gvsigol/settings.py if the variable is not defined by the app
    or None otherwise.
    For instance, if the installed app is "gvsigol_app_test", then
    get_setting("MYVAR") tries to get the value of the variable
    gvsigol_app_test.settings.MYVAR. If it is not found, it tries to
    get the value of gvsigol.settings.MYVAR. It will return None if
    the variable is not defined on those settings.py files.
    """
    return get_app_setting(key, getattr(settings, key, default))
