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
'''
@author: Cesar Martinez <cmartinez@scolab.es>
'''

import ast
from datetime import datetime
import hashlib
from httplib import HTTPResponse
import json
import logging
from math import floor
import os
import random
import re
import shutil
import string
import unicodedata
import urllib
import zipfile

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponseBadRequest, HttpResponseNotFound, HttpResponse
from django.shortcuts import render
from django.shortcuts import render, redirect
from django.utils import timezone
from django.utils.translation import ugettext as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_safe, require_POST, require_GET
from django.utils.html import escape, strip_tags
from future.moves.urllib.parse import urlparse, urlencode
from geoserver import workspace
from lxml import html
from owslib.util import Authentication
from owslib.wms import WebMapService
from owslib.wmts import WebMapTileService
import requests
from requests_futures.sessions import FuturesSession

from backend_postgis import Introspect
from forms_geoserver import CreateFeatureTypeForm
from forms_services import ServerForm, WorkspaceForm, DatastoreForm, LayerForm, LayerUpdateForm, DatastoreUpdateForm, ExternalLayerForm, ServiceUrlForm
from gdal_tools import gdalsrsinfo
import geographic_servers
from gvsigol import settings
from gvsigol.settings import FILEMANAGER_DIRECTORY, LANGUAGES, INSTALLED_APPS, WMS_MAX_VERSION, WMTS_MAX_VERSION, BING_LAYERS
from gvsigol.settings import MOSAIC_DB
from gvsigol_auth.models import UserGroup
from gvsigol_auth.utils import superuser_required, staff_required
from gvsigol_core import utils as core_utils
from gvsigol_core.models import Project
from gvsigol_core.models import ProjectLayerGroup
from gvsigol_services.backend_resources import resource_manager 
from gvsigol_services.models import LayerResource
import gvsigol_services.tiling_service as tiling_service
import locks_utils
from models import LayerFieldEnumeration
from models import Workspace, Datastore, LayerGroup, Layer, LayerReadGroup, LayerWriteGroup, Enumeration, EnumerationItem, \
    LayerLock, Server, Node, ServiceUrl
from rest_geoserver import RequestError
import rest_geoserver
import rest_geowebcache as geowebcache
import signals
import utils
import psycopg2
from psycopg2 import sql

from actstream import action
from actstream.models import Action

logger = logging.getLogger("gvsigol")

_valid_name_regex=re.compile("^[a-zA-Z_][a-zA-Z0-9_]*$")

CONNECT_TIMEOUT = 3.05
READ_TIMEOUT = 30
base_layer_process = {}

@login_required(login_url='/gvsigonline/auth/login_user/')
@require_safe
@superuser_required
def server_list(request):
    response = {
        'servers': Server.objects.values()
    }
    return render(request, 'server_list.html', response)

@login_required(login_url='/gvsigonline/auth/login_user/')
@superuser_required
@require_http_methods(["GET", "POST", "HEAD"])
def server_add(request):
    if request.method == 'POST':
        form = ServerForm(request.POST)
        if form.is_valid():
            # save it on DB if successfully created
            server = Server(**form.cleaned_data)
            server.save()
            
            if len(Server.objects.all()) == 1:
                server.default = True
                server.save()
                
            elif len(Server.objects.all()) > 1:
                if form.cleaned_data['default'] == True:
                    for s in Server.objects.all():
                        s.default = False
                        s.save()
                    server.default = True
                    server.save()
                     
            
            nodes = json.loads(request.POST.get('nodes'))
            for n in nodes:
                node = Node(
                    server = server,
                    status = n['status'],
                    url = n['url'],
                    is_master = n['is_master']
                )
                node.save()
            
            has_master = False
            if len(Node.objects.all()) > 0:
                for n in Node.objects.all():
                    if n.is_master:
                        has_master = True
                
                if not has_master:
                    Node.objects.all()[0].is_master = True
            
            geographic_servers.get_instance().add_server(server)
            
            return HttpResponseRedirect(reverse('server_list'))
                
    else:
        name = 'server_' + ''.join(random.choice(string.ascii_uppercase) for i in range(6))
        form = ServerForm(initial={'name': name})
            
    return render(request, 'server_add.html', {'form': form})

@login_required(login_url='/gvsigonline/auth/login_user/')
@require_POST
@superuser_required
def server_delete(request, svid):
    try:
    
        sv_object = Server.objects.get(id=svid)
        gs = geographic_servers.get_instance().get_server_by_id(svid)
        
        for ws in Workspace.objects.filter(server_id=sv_object.id):
            if gs.deleteWorkspace(ws):
                datastores = Datastore.objects.filter(workspace_id=ws.id)
                for ds in datastores:
                    layers = Layer.objects.filter(external=False).filter(datastore_id=ds.id)
                    for l in layers:
                        gs.deleteLayerStyles(l)
                ws.delete()
            
            else:
                return HttpResponseBadRequest()
        
        for n in Node.objects.filter(server_id=sv_object.id):
            n.delete()
             
        sv_object.delete()
        return HttpResponseRedirect(reverse('server_list'))
        
    except Exception as e:
        print e.message 
        return HttpResponseNotFound(e.message ) 
    
    
@login_required(login_url='/gvsigonline/auth/login_user/')
@superuser_required
def server_update(request, svid):
    if request.method == 'POST':
        title = request.POST.get('server_title')
        description = request.POST.get('server_description')
        frontend_url = request.POST.get('server_frontend_url')
        user = request.POST.get('server_user')
        password = request.POST.get('server_password')
        
        server = Server.objects.get(id=int(svid))
        
        old_frontend_url = server.frontend_url
        
        if 'default' in request.POST:
            for s in Server.objects.all():
                s.default = False
                s.save()
            server.default = True
            server.save()
        
        server.title = title
        server.description = description
        server.frontend_url = frontend_url
        server.user = user
        server.password = password
        server.save() 
        
        workspaces = Workspace.objects.filter(server_id=server.id)
        for ws in workspaces:
            ws.uri = ws.uri.replace(old_frontend_url, frontend_url)
            ws.wms_endpoint = ws.server.getWmsEndpoint(ws.name)
            ws.wfs_endpoint = ws.server.getWfsEndpoint(ws.name)
            ws.wcs_endpoint = ws.server.getWcsEndpoint(ws.name)
            ws.wmts_endpoint = ws.server.getWmtsEndpoint(ws.name)
            ws.cache_endpoint = ws.server.getCacheEndpoint(ws.name)
            ws.save()
            
        for n in Node.objects.filter(server=server):
            n.delete()
        
        json_nodes = json.loads(request.POST.get('nodes')) 
        for n in json_nodes:
            node = Node(
                server = server,
                status = n['status'],
                url = n['url'],
                is_master = n['is_master']
            )
            node.save()

        return redirect('server_list')

    else:
        server = Server.objects.get(id=int(svid))
        nodes = []
        for n in Node.objects.filter(server_id=server.id):
            node = {
                'id': n.id,
                'status': n.status,
                'url': n.url,
                'is_master': n.is_master,
                'exists': True
            }
            nodes.append(node)

        return render(request, 'server_update.html', {'svid': svid, 'server': server, 'nodes': json.dumps(nodes)})
    
@login_required(login_url='/gvsigonline/auth/login_user/')
@require_POST
@superuser_required
def get_server(request, svid):
    try:
        s = Server.objects.get(id=svid)
        
        server = {}
        server['name'] = s.name
        server['title'] = s.title
        server['description'] = s.description
        server['type'] = s.type
        server['frontend_url'] = s.frontend_url
        
        response = {
            'server': server
        }

        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')
    
    except:
        return HttpResponseNotFound('<h1>Server not found{0}</h1>'.format(s.name))

@login_required(login_url='/gvsigonline/auth/login_user/')
@superuser_required
@csrf_exempt   
def reload_node(request, nid):
    if request.method == 'POST':
        node = Node.objects.get(id=int(nid))
        gs = geographic_servers.get_instance().get_server_by_id(node.server_id)
        if gs.reload_node(node.url):
            response = {'reloaded': True}
        else:
            response = {'reloaded': False}

        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')
    

@login_required(login_url='/gvsigonline/auth/login_user/')
@require_safe
@superuser_required
def workspace_list(request):
    response = {
        'workspaces': Workspace.objects.values()
    }
    return render(request, 'workspace_list.html', response)

@login_required(login_url='/gvsigonline/auth/login_user/')
@superuser_required
@require_http_methods(["GET", "POST", "HEAD"])
def workspace_add(request):
    if request.method == 'POST':
        form = WorkspaceForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            if _valid_name_regex.search(name) == None:
                form.add_error(None, _("Invalid workspace name: '{value}'. Identifiers must begin with a letter or an underscore (_). Subsequent characters can be letters, underscores or numbers").format(value=name))
            else:
                form.cleaned_data['is_public'] = form.cleaned_data['is_public'] if form.cleaned_data['is_public'] else False
                if utils.create_workspace(form.cleaned_data['server'].id,
                                       form.cleaned_data['name'],
                                       form.cleaned_data['uri'],
                                       form.cleaned_data,
                                       request.user.username):
                    return HttpResponseRedirect(reverse('workspace_list'))
                else:
                    # FIXME: the backend should raise an exception to identify the cause (e.g. workspace exists, backend is offline)
                    form.add_error(None, _("Error: workspace could not be created"))

    else:
        sv = None
        for s in Server.objects.all():
            if s.default:
                sv = s

        if len(Server.objects.all()) > 0:
            if sv == None:
                sv = Server.objects.all()[0] 
        form = WorkspaceForm(initial={'server': sv})

    return render(request, 'workspace_add.html', {'form': form})

@login_required(login_url='/gvsigonline/auth/login_user/')
@require_http_methods(["GET", "POST", "HEAD"])
@superuser_required
def workspace_import(request):
    """
    FIXME: Not implemented yet.
    Imports on gvSIG Online an existing workspace and all its depending stores, layers, styles, etc
    """
    if request.method == 'POST':
        #form = None #FIXME
        #if form.is_valid():
        #    #get existing ws and associated resources from Geoserver REST API
        #    pass
        ##
        # get selected ws
        # recursively import the proposed ws
        pass
    else:
        # create empty form
        # FIXME: probably does not work
        server = geographic_servers.get_instance().get_server_by_id(id)
        workspaces = server.get_workspaces()
        workspace_names = [n for n in workspaces['name']]
        querySet = Workspace.objects.all().exclude(name__in=workspace_names)
        response = {
            'workspaces': querySet.values()
        }
        return render(request, 'workspace_import.html', response)


@login_required(login_url='/gvsigonline/auth/login_user/')
@require_POST
@superuser_required
def workspace_delete(request, wsid):
    try:
        ws = Workspace.objects.get(id=wsid)
        gs = geographic_servers.get_instance().get_server_by_id(ws.server.id)
        if gs.deleteWorkspace(ws):
            datastores = Datastore.objects.filter(workspace_id=ws.id)
            for ds in datastores:
                layers = Layer.objects.filter(external=False).filter(datastore_id=ds.id)
                for l in layers:
                    gs.deleteLayerStyles(l)
            ws.delete()
            gs.reload_nodes()
            return HttpResponseRedirect(reverse('workspace_list'))
        else:
            return HttpResponseBadRequest()
    except:
        return HttpResponseNotFound('<h1>Workspace not found{0}</h1>'.format(ws.name))


@login_required(login_url='/gvsigonline/auth/login_user/')
@superuser_required
def workspace_update(request, wid):
    if request.method == 'POST':
        description = request.POST.get('workspace-description')
        isPublic = False
        if 'is_public' in request.POST:
            isPublic = True

        workspace = Workspace.objects.get(id=int(wid))

        workspace.description = description
        workspace.is_public = isPublic
        workspace.save()
        return redirect('workspace_list')

    else:
        workspace = Workspace.objects.get(id=int(wid))
        return render(request, 'workspace_update.html', {'wid': wid, 'workspace': workspace})


@login_required(login_url='/gvsigonline/auth/login_user/')
@require_safe
@staff_required
def datastore_list(request):

    datastore_list = None
    if request.user.is_superuser:
        datastore_list = Datastore.objects.all()
    else:
        datastore_list = Datastore.objects.filter(created_by__exact=request.user.username)

    for datastore in datastore_list:
        params = json.loads(datastore.connection_params)
        if 'passwd' in params:
            params['passwd'] = '****'
        if 'password' in params:
            if params['password'] == '':
                params['password'] = ''
            else:
                params['password'] = '****'
        datastore.connection_params = json.dumps(params)

    response = {
        'datastores': datastore_list
    }
    return render(request, 'datastore_list.html', response)


@login_required(login_url='/gvsigonline/auth/login_user/')
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def datastore_add(request):
    if request.method == 'POST':
        post_dict = request.POST.copy()
        type = request.POST.get('type')
        has_errors = False
        if type == 'c_GeoTIFF':
            file = post_dict.get('file')
            try:
                output = gdalsrsinfo(file.replace('file://', ''))
                if output == None or output.__len__() <= 0:
                    has_errors = True
                else:
                    post_dict['connection_params'] = post_dict.get('connection_params').replace('url_replace', file)
            except:
                has_errors = True

        if type == 'c_ImageMosaic':
            file = post_dict.get('file')
            try:
                output = file.replace('file://', '')
                if output == None or output.__len__() <= 0:
                    has_errors = True
                else:
                    post_dict['connection_params'] = post_dict.get('connection_params').replace('url_replace', file)
            except:
                has_errors = True

            #post_dict['connection_params']['date_regex'] = '(?<=_)[0-9]{8}'
            #post_dict['connection_params']['ele_regex'] = ''

        form = DatastoreForm(post_dict)
        if not has_errors and form.is_valid():
            name = form.cleaned_data['name']
            if _valid_name_regex.search(name) == None:
                form.add_error(None, _("Invalid datastore name: '{value}'. Identifiers must begin with a letter or an underscore (_). Subsequent characters can be letters, underscores or numbers").format(value=name))
            else:
                ws = form.cleaned_data['workspace']
                ds = utils.add_datastore(form.cleaned_data['workspace'],
                                  form.cleaned_data['type'],
                                  form.cleaned_data['name'],
                                  form.cleaned_data['description'],
                                  form.cleaned_data['connection_params'],
                                  request.user.username)
                if ds is not None:
                    if type == 'c_ImageMosaic':
                        gs = geographic_servers.get_instance().get_server_by_id(ws.server.id)
                        try:
                            gs.uploadImageMosaic(ws, ds)
                            gs.reload_nodes()
                        except Exception as e:
                            pass
                   
                    return HttpResponseRedirect(reverse('datastore_list'))
                else:
                    # FIXME: the backend should raise an exception to identify the cause (e.g. datastore exists, backend is offline)
                    form.add_error(None, _('Error: Data store could not be created'))
        else:
            if has_errors:
                form.add_error(None, _('Error: GeoTIFF is not georreferenced'))

    else:
        form = DatastoreForm()
        if not request.user.is_superuser:
            form.fields['workspace'].queryset = Workspace.objects.filter(created_by__exact=request.user.username).order_by('name')
    return render(request, 'datastore_add.html', {'fm_directory': FILEMANAGER_DIRECTORY + "/", 'form': form})

@login_required(login_url='/gvsigonline/auth/login_user/')
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def datastore_update(request, datastore_id):
    datastore = Datastore.objects.get(id=datastore_id)
    if datastore==None:
        return HttpResponseNotFound(_('Datastore not found'))
    if request.method == 'POST':
        form = DatastoreUpdateForm(request.POST)
        if form.is_valid():
                dstype = datastore.type
                description = form.cleaned_data.get('description')
                connection_params = form.cleaned_data.get('connection_params')

                got_params = json.loads(connection_params)
                if 'passwd' in got_params and got_params['passwd'] == '****':
                    params = json.loads(datastore.connection_params)
                    got_params['passwd'] = params['passwd']
                    connection_params = json.dumps(got_params)

                if 'password' in got_params and got_params['password'] == '****':
                    params = json.loads(datastore.connection_params)
                    got_params['password'] = params['password']
                    connection_params = json.dumps(got_params)

                gs = geographic_servers.get_instance().get_server_by_id(datastore.workspace.server.id)
                if gs.updateDatastore(datastore.workspace.name, datastore.name,
                                                      description, dstype, connection_params):
                    # REST API does not allow to can't change the workspace or name of a datastore
                    #datastore.workspace = workspace
                    #datastore.name = name
                    datastore.description = description
                    datastore.connection_params = connection_params
                    datastore.save()
                    gs.reload_nodes()
                    return HttpResponseRedirect(reverse('datastore_list'))
                else:
                    form.add_error(None, _("Error updating datastore"))
    else:
        params = json.loads(datastore.connection_params)
        if 'passwd' in params:
            params['passwd'] = '****'
        if 'password' in params:
            if params['password'] == '':
                params['password'] = ''
            else:
                params['password'] = '****'
        datastore.connection_params = json.dumps(params)
        form = DatastoreUpdateForm(instance=datastore)
    return render(request, 'datastore_update.html', {'form': form, 'datastore_id': datastore_id, 'workspace_name': datastore.workspace.name})

@login_required(login_url='/gvsigonline/auth/login_user/')
@require_POST
@staff_required
def datastore_delete(request, dsid):
    try:
        delete_schema = False
        if request.POST.get('delete_schema') == 'true':
            delete_schema = True

        ds = Datastore.objects.get(id=dsid)
        gs = geographic_servers.get_instance().get_server_by_id(ds.workspace.server.id)
        try:
            gs.deleteDatastore(ds.workspace, ds, delete_schema)
            layers = Layer.objects.filter(external=False).filter(datastore_id=ds.id)
            for l in layers:
                gs.deleteLayerStyles(l)

            Datastore.objects.all().filter(name=ds.name).delete()
            if ds.type == 'c_ImageMosaic':
                got_params = json.loads(ds.connection_params)
                mosaic_url = got_params["url"].replace("file://", "")
                split_mosaic_url = mosaic_url.split("/")

                mosaic_name = split_mosaic_url[split_mosaic_url.__len__()-1]

                if os.path.isfile(mosaic_url + "/" + ds.name + ".properties"):
                    os.remove(mosaic_url + "/" + ds.name + ".properties")
                if os.path.isfile(mosaic_url + "/" + mosaic_name + ".properties"):
                    os.remove(mosaic_url + "/" + mosaic_name + ".properties")
                if os.path.isfile(mosaic_url + "/sample_image.dat"):
                    os.remove(mosaic_url + "/sample_image.dat")

                host = MOSAIC_DB['host']
                port = MOSAIC_DB['port']
                dbname = MOSAIC_DB['database']
                user = MOSAIC_DB['user']
                passwd = MOSAIC_DB['passwd']
                schema = 'imagemosaic'
                i = Introspect(database=dbname, host=host, port=port, user=user, password=passwd)
                i.delete_mosaic(ds.name, schema)
                i.close()
                
            gs.reload_nodes()
            return HttpResponseRedirect(reverse('datastore_list'))
        
        except:
            logger.exception("Error deleting store")
            return HttpResponseBadRequest()

    except:
        return HttpResponseNotFound('<h1>Datastore not found{0}</h1>'.format(ds.name))

@login_required(login_url='/gvsigonline/auth/login_user/')
@require_safe
@staff_required
def layer_list(request):

    layer_list = None
    if request.user.is_superuser:
        layer_list = Layer.objects.filter(external=False)
        project_list = Project.objects.all()
        
    else:
        layer_list = Layer.objects.filter(created_by__exact=request.user.username).filter(external=False)
        project_list = Project.objects.filter(created_by__exact=request.user.username)

    layers = []
    for l in layer_list:
        projects = []
        project_layergroups = ProjectLayerGroup.objects.filter(layer_group_id=l.layer_group.id)
        for lg in project_layergroups:
            if lg.project.title is not None:
                projects.append(lg.project.title)
        layer = {
            'id': l.id,
            'type': l.type,
            'thumbnail_url': l.thumbnail.url,
            'name': l.name,
            'title': l.title,
            'datastore_name': l.datastore.name,
            'lg_name': l.layer_group.name,
            'lg_title': l.layer_group.title,
            'cached': l.cached,
            'projects': '; '.join(projects)
        }
        layers.append(layer)
        
    projects = []
    for p in project_list:
        project = {
            'id': p.id,
            'name': p.name,
            'title': p.title
        }
        projects.append(project)
        
    response = {
        'layers': layers,
        'projects': json.dumps(projects)
    }
    return render(request, 'layer_list.html', response)

@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def layer_refresh_extent(request, layer_id):
    layer = Layer.objects.get(pk=layer_id)
    datastore = layer.datastore
    workspace = datastore.workspace
    #server.updateBoundingBoxFromData(layer)
    server = geographic_servers.get_instance().get_server_by_id(workspace.server.id)
    (ds_type, layer_info) = server.getResourceInfo(workspace.name, datastore, layer.name, "json")
    utils.set_layer_extent(layer, ds_type, layer_info, server)
    layer.save()
    return redirect('layer_list')

@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def layer_delete(request, layer_id):
    try:
        layer_delete_operation(request, layer_id)
        return HttpResponseRedirect(reverse('datastore_list'))
    except rest_geoserver.FailedRequestError as e:
        if e.status_code == 503:
            msg = _('ERROR can\'t connect with GeoServer')
            data = {
                    'status': 'ERROR',
                    'status_code': 503,
                    'message': msg,
                }
            return HttpResponse(json.dumps(data))
        if e.status_code == 500:
            msg = _('ERROR can\'t remove GeoServer data. Forcing remove from DataBase')
            layer = Layer.objects.get(pk=layer_id)
            if not 'no_thumbnail.jpg' in layer.thumbnail.name:
                if os.path.isfile(layer.thumbnail.path):
                    os.remove(layer.thumbnail.path)
            Layer.objects.all().filter(pk=layer_id).delete()
            core_utils.toc_remove_layer(layer)

            data = {
                    'status': 'ERROR',
                    'status_code': 500,
                    'message': msg,
                }
            return HttpResponse(json.dumps(data))

        raise rest_geoserver.FailedRequestError(e.status_code, _("Error publishing the layer group. Backend error: {msg}").format(msg=e.get_message()))
    except Exception as e:
        return HttpResponseNotFound('<h1>Error deleting layer: {0}</h1>'.format(layer_id))

@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def layer_delete_operation(request, layer_id):
    layer = Layer.objects.get(pk=layer_id)
    gs = geographic_servers.get_instance().get_server_by_id(layer.datastore.workspace.server.id)
    if layer.layer_group.name != '__default__':
        try:
            gs.deleteGeoserverLayerGroup(layer.layer_group)
        except:
            logger.exception("Error deleting layer group")
    gs.deleteResource(layer.datastore.workspace, layer.datastore, layer)
    gs.deleteLayerStyles(layer)
    signals.layer_deleted.send(sender=None, layer=layer)

    if layer.datastore.type == 'c_ImageMosaic':
        got_params = json.loads(layer.datastore.connection_params)
        mosaic_url = got_params["url"].replace("file://", "")
        split_mosaic_url = mosaic_url.split("/")
        mosaic_name = split_mosaic_url[split_mosaic_url.__len__()-1]

        if os.path.isfile(mosaic_url + "/" + mosaic_name + ".properties"):
            os.remove(mosaic_url + "/" + mosaic_name + ".properties")
        if os.path.isfile(mosaic_url + "/sample_image.dat"):
            os.remove(mosaic_url + "/sample_image.dat")

        host = MOSAIC_DB['host']
        port = MOSAIC_DB['port']
        dbname = MOSAIC_DB['database']
        user = MOSAIC_DB['user']
        passwd = MOSAIC_DB['passwd']
        schema = 'imagemosaic'
        i = Introspect(database=dbname, host=host, port=port, user=user, password=passwd)
        i.delete_mosaic(layer.datastore.name, schema)
        i.close()

    if not 'no_thumbnail.jpg' in layer.thumbnail.name:
        if os.path.isfile(layer.thumbnail.path):
            os.remove(layer.thumbnail.path)
    Layer.objects.all().filter(pk=layer_id).delete()
    gs.setDataRules()
    core_utils.toc_remove_layer(layer)
    gs.createOrUpdateGeoserverLayerGroup(layer.layer_group)
    gs.reload_nodes()



@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def backend_datastore_list(request):
    """
    Lists the resources existing on a data store, retrieving the information
    directly from the backend (which may differ from resources available on
    Django DB). Useful to register new resources on Django DB.
    """
    if 'id_workspace' in request.GET:
        id_ws = request.GET['id_workspace']
        ws = Workspace.objects.get(id=id_ws)
        gs = geographic_servers.get_instance().get_server_by_id(ws.server.id)
        if ws:
            datastores = gs.getDataStores(ws)
            datastores_sorted = sorted(datastores)
            return HttpResponse(json.dumps(datastores_sorted))
    return HttpResponseBadRequest()


@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def backend_resource_list_available(request):
    """
    Lists the resources existing on a data store, retrieving the information
    directly from the backend (which may differ from resurces available on
    Django DB). Useful to register new resources on Django DB.
    """
    if 'id_datastore' in request.GET:
        id_ds = request.GET['id_datastore']
        ds = Datastore.objects.get(id=id_ds)
        if ds:
            gs = geographic_servers.get_instance().get_server_by_id(ds.workspace.server.id)
            resources = gs.getResources(ds.workspace, ds, 'available')
            resources_sorted = sorted(resources)
            return HttpResponse(json.dumps(resources_sorted))
    return HttpResponseBadRequest()

@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def backend_layergroup_list_available(request):
    """
    Lists the resources existing on a data store, retrieving the information
    directly from the backend (which may differ from resurces available on
    Django DB). Useful to register new resources on Django DB.
    """
    if 'id_datastore' in request.GET:
        id_ds = request.GET['id_datastore']
        ds = Datastore.objects.get(id=id_ds)
        if ds:
            layer_groups = []
            for lg in LayerGroup.objects.filter(server_id=ds.workspace.server.id):
                layer_group = {
                    'value': lg.id,
                    'text': lg.name
                }
                layer_groups.append(layer_group)
            return HttpResponse(json.dumps(layer_groups))
        
    return HttpResponseBadRequest()

@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def backend_resource_list_configurable(request):
    """
    Lists the resources existing on a data store, retrieving the information
    directly from the backend (which may differ from resurces available on
    Django DB). Useful to register new resources on Django DB.
    """
    if 'id_datastore' in request.GET:
        id_ds = request.GET['id_datastore']
        ds = Datastore.objects.get(id=id_ds)
        if ds:
            gs = geographic_servers.get_instance().get_server_by_id(ds.workspace.server.id)
            resources = gs.getResources(ds.workspace, ds, 'configurable')
            resources_sorted = sorted(resources)
            return HttpResponse(json.dumps(resources_sorted))
    return HttpResponseBadRequest()


@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def backend_resource_list(request):
    """
    Lists the resources existing on a data store, retrieving the information
    directly from the backend (which may differ from resurces available on
    Django DB). Useful to register new resources on Django DB.
    """
    if 'id_datastore' in request.GET:
        type = 'all'
        if 'type' in request.GET:
            type = request.GET['type']
        id_ds = request.GET['id_datastore']
        ds = Datastore.objects.get(id=id_ds)
        if ds:
            gs = geographic_servers.get_instance().get_server_by_id(ds.workspace.server.id)
            resources = gs.getResources(ds.workspace, ds, type)
            resources_sorted = sorted(resources)
            return HttpResponse(json.dumps(resources_sorted))
    return HttpResponseBadRequest()


@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def backend_fields_list(request):
    """
    Lists the resources existing on a data store, retrieving the information
    directly from the backend (which may differ from resources available on
    Django DB). Useful to register new resources on Django DB.
    """

    if 'name_datastore' in request.GET and 'id_workspace' in request.GET and 'name_resource' in request.GET:
        name = request.GET['name_resource']
        ds_name = request.GET['name_datastore']
        id_ws = request.GET['id_workspace']
        ws = Workspace.objects.get(id=id_ws)
        ds = Datastore.objects.get(name=ds_name, workspace=ws)
        if ds:
            layer = Layer.objects.filter(external=False).filter(datastore=ds, name=name).first()

            params = json.loads(ds.connection_params)
            host = params['host']
            port = params['port']
            dbname = params['database']
            user = params['user']
            passwd = params['passwd']
            schema = params.get('schema', 'public')
            i = Introspect(database=dbname, host=host, port=port, user=user, password=passwd)
            layer_defs = i.get_fields_info(name, schema)
            i.close()
            result_resources = []
            conf = None
            if layer and layer.conf:
                conf = ast.literal_eval(layer.conf)
            for resource_def in layer_defs:
                resource = resource_def['name']
                if conf:
                    founded = False
                    for f in conf['fields']:
                        if f['name'] == resource:
                            field = {}
                            field['name'] = f['name']
                            for id, language in LANGUAGES:
                                field['title-'+id] = f['title-'+id]
                            result_resources.append(field)
                            founded = True
                    if not founded:
                        field = {}
                        field['name'] = resource
                        for id, language in LANGUAGES:
                            field['title-'+id] = resource
                        result_resources.append(field)
                else:
                    field = {}
                    field['name'] = resource
                    for id, language in LANGUAGES:
                        field['title-'+id] = resource
                    result_resources.append(field)

            result_resources_sorted = sorted(result_resources)
            return HttpResponse(json.dumps(result_resources_sorted))

    return HttpResponseBadRequest()


def do_add_layer(server, datastore, name, title, is_queryable, extraParams):
    workspace = datastore.workspace

    """
    server.createTable(form.cleaned_data)
    """
    
    # first create the resource on the backend
    server.createResource(
        workspace,
        datastore,
        name,
        title,
        extraParams=extraParams
    )

    if datastore.type != 'e_WMS' and datastore.type != 'c_ImageMosaic':
        server.setQueryable(
            workspace.name,
            datastore.name,
            datastore.type,
            name,
            is_queryable
        )

def do_config_layer(server, layer, featuretype):
    layer_autoconfig(layer, featuretype)
    layer.save()
    
    ds_type = layer.datastore.type
    if ds_type != 'e_WMS':
        if ds_type == 'c_ImageMosaic':
            server.updateImageMosaicTemporal(layer.datastore, layer)
        elif ds_type[0:2] == 'v_':
            utils.set_time_enabled(server, layer)
        create_symbology(server, layer)
        server.updateThumbnail(layer, 'create')

    core_utils.toc_add_layer(layer)
    server.createOrUpdateGeoserverLayerGroup(layer.layer_group)
    server.reload_nodes()


def create_symbology(server, layer):
    style_name = layer.datastore.workspace.name + '_' + layer.name + '_default'
    server.createDefaultStyle(layer, style_name)
    server.setLayerStyle(layer, style_name, True)
    layer.save()



@login_required(login_url='/gvsigonline/auth/login_user/')
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def layer_add(request):
    return layer_add_with_group(request, None)


@login_required(login_url='/gvsigonline/auth/login_user/')
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def layer_add_with_group(request, layergroup_id):
    redirect_to_layergroup = request.GET.get('redirect')

    if request.method == 'POST':
        form = LayerForm(request.POST)
        abstract = request.POST.get('md-abstract')
        is_visible = False

        if 'visible' in request.POST:
            is_visible = True

        is_queryable = False
        if 'queryable' in request.POST:
            is_queryable = True

        cached = False
        if 'cached' in request.POST:
            cached = True

        single_image = False
        if 'single_image' in request.POST:
            single_image = True
            cached = False
            
        allow_download = False
        if 'allow_download' in request.POST:
            allow_download = True
        
        try:
            maxFeatures = int(request.POST.get('max_features', 0))
        except:
            maxFeatures = 0
            
        detailed_info_enabled = False
        detailed_info_button_title = request.POST.get('detailed_info_button_title')
        detailed_info_html = request.POST.get('detailed_info_html')
        if 'detailed_info_enabled' in request.POST:
            detailed_info_enabled = True
            detailed_info_button_title = request.POST.get('detailed_info_button_title')
            detailed_info_html = request.POST.get('detailed_info_html')

        time_enabled = False
        time_field=''
        time_endfield=''
        time_presentation = ''
        time_resolution_year = 0
        time_resolution_month = 0
        time_resolution_week = 0
        time_resolution_day = 0
        time_resolution_hour = 0
        time_resolution_minute = 0
        time_resolution_second = 0
        time_default_value_mode = ''
        time_default_value = ''

        time_resolution = ''

        if 'time_enabled' in request.POST:
            time_enabled = True
            time_field = request.POST.get('time_enabled_field')
            time_endfield = request.POST.get('time_enabled_endfield')
            time_presentation = request.POST.get('time_presentation')
            time_default_value_mode = request.POST.get('time_default_value_mode')
            time_default_value = request.POST.get('time_default_value')

            time_resolution = request.POST.get('time_resolution')

        if form.is_valid():
            try:
                datastore = form.cleaned_data['datastore']
                workspace = datastore.workspace
                extraParams = {}
                
                if datastore.type == 'v_PostGIS':
                    extraParams['maxFeatures'] = maxFeatures
                    dts = datastore
                    params = json.loads(dts.connection_params)
                    host = params['host']
                    port = params['port']
                    dbname = params['database']
                    user = params['user']
                    passwd = params['passwd']
                    schema = params.get('schema', 'public')
                    i = Introspect(database=dbname, host=host, port=port, user=user, password=passwd)
                    fields = i.get_fields(form.cleaned_data['name'], schema)
                    i.close()
                    
                    for field in fields:
                        if ' ' in field:
                            raise ValueError(_("Invalid layer fields: '{value}'. Layer can't have fields with whitespaces").format(value=field))
                
                server = geographic_servers.get_instance().get_server_by_id(workspace.server.id)
                # first create the resource on the backend
                do_add_layer(server, datastore, form.cleaned_data['name'], form.cleaned_data['title'], is_queryable, extraParams)

                # save it on DB if successfully created
                del form.cleaned_data['format']
                newRecord = Layer(**form.cleaned_data)
                if not newRecord.source_name:
                    newRecord.source_name = newRecord.name
                newRecord.external = False
                newRecord.created_by = request.user.username
                newRecord.type = datastore.type
                newRecord.visible = is_visible
                newRecord.queryable = is_queryable
                newRecord.allow_download = allow_download
                newRecord.cached = cached
                newRecord.single_image = single_image
                newRecord.abstract = abstract
                newRecord.time_enabled = time_enabled
                newRecord.time_enabled_field = time_field
                newRecord.time_enabled_endfield = time_endfield
                newRecord.time_presentation = time_presentation
                newRecord.time_resolution_year = time_resolution_year
                newRecord.time_resolution_month = time_resolution_month
                newRecord.time_resolution_week = time_resolution_week
                newRecord.time_resolution_day = time_resolution_day
                newRecord.time_resolution_hour = time_resolution_hour
                newRecord.time_resolution_minute = time_resolution_minute
                newRecord.time_resolution_second = time_resolution_second
                newRecord.time_default_value_mode = time_default_value_mode
                newRecord.time_default_value = time_default_value
                newRecord.time_resolution = time_resolution
                newRecord.detailed_info_enabled = detailed_info_enabled
                newRecord.detailed_info_button_title = detailed_info_button_title
                newRecord.detailed_info_html = detailed_info_html
                newRecord.timeout = request.POST.get('timeout')
                
                params = {}
                params['format'] = request.POST.get('format')
                newRecord.external_params = json.dumps(params)
                
                newRecord.save()
                
                featuretype = {
                    'max_features': maxFeatures
                }
                do_config_layer(server, newRecord, featuretype)

                if redirect_to_layergroup:
                    return HttpResponseRedirect(reverse('layer_permissions_update', kwargs={'layer_id': newRecord.id})+"?redirect=grouplayer-redirect")
                else:
                    return HttpResponseRedirect(reverse('layer_permissions_update', kwargs={'layer_id': newRecord.id}))

            except Exception as e:
                msg = _("Error: layer could not be published")
                logger.exception(msg)
                try:
                    msg = e.server_message
                except:
                    pass
                logger.exception(msg)
                # FIXME: the backend should raise more specific exceptions to identify the cause (e.g. layer exists, backend is offline)
                form.add_error(None, msg)
    else:
        form = LayerForm()
        if not request.user.is_superuser:
            form.fields['datastore'].queryset = Datastore.objects.filter(created_by__exact=request.user.username)
            form.fields['layer_group'].queryset =(LayerGroup.objects.filter(created_by__exact=request.user.username) | LayerGroup.objects.filter(name='__default__')).order_by('name')


    datastore_types = {}
    types = {}
    for datastore in Datastore.objects.filter():
        types[datastore.id] = datastore.type
        datastore_types[datastore.id] = datastore.type

    return render(request, 'layer_add.html', {
            'form': form,
            'datastore_types': json.dumps(datastore_types),
            'layergroup_id': layergroup_id,
            'redirect_to_layergroup': redirect_to_layergroup})


@login_required(login_url='/gvsigonline/auth/login_user/')
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def layer_update(request, layer_id):
    redirect_to_layergroup = request.GET.get('redirect')

    if request.method == 'POST':
        updatedParams = {}

        layer = Layer.objects.get(id=int(layer_id))
        workspace = request.POST.get('workspace')
        datastore = request.POST.get('datastore')
        name = request.POST.get('name')
        title = request.POST.get('title')
        abstract = request.POST.get('md-abstract')
        updatedParams['title'] = title
        #style = request.POST.get('style')
        layer_group_id = request.POST.get('layer_group')
        layerConf = ast.literal_eval(layer.conf) if layer.conf else {}

        is_visible = False
        if 'visible' in request.POST:
            is_visible = True

        is_queryable = False
        if 'queryable' in request.POST:
            is_queryable = True

        cached = False
        if 'cached' in request.POST:
            cached = True

        single_image = False
        if 'single_image' in request.POST:
            single_image = True
            cached = False
            
        allow_download = False
        if 'allow_download' in request.POST:
            allow_download = True

        if layer.datastore.type.startswith('v_'):
            try:
                maxFeatures = int(request.POST.get('max_features', 0))
            except:
                maxFeatures = 0
            updatedParams['maxFeatures'] = maxFeatures
            layerConf['featuretype'] = layerConf.get('featuretype', {})
            layerConf['featuretype']['max_features'] = maxFeatures

        detailed_info_enabled = False
        detailed_info_button_title = request.POST.get('detailed_info_button_title')
        detailed_info_html = request.POST.get('detailed_info_html')
        if 'detailed_info_enabled' in request.POST:
            detailed_info_enabled = True
            detailed_info_button_title = request.POST.get('detailed_info_button_title')
            detailed_info_html = request.POST.get('detailed_info_html')

        time_enabled = False
        time_field=''
        time_endfield=''
        time_presentation = ''
        time_resolution_year = 0
        time_resolution_month = 0
        time_resolution_week = 0
        time_resolution_day = 0
        time_resolution_hour = 0
        time_resolution_minute = 0
        time_resolution_second = 0
        time_default_value_mode = ''
        time_default_value = ''

        time_resolution = ''

        if 'time_enabled' in request.POST:
            time_enabled = True
            time_field = request.POST.get('time_enabled_field')
            time_endfield = request.POST.get('time_enabled_endfield')
            time_presentation = request.POST.get('time_presentation')
            time_resolution_year = request.POST.get('time_resolution_year')
            time_resolution_month = request.POST.get('time_resolution_month')
            time_resolution_week = request.POST.get('time_resolution_week')
            time_resolution_day = request.POST.get('time_resolution_day')
            time_resolution_hour = request.POST.get('time_resolution_hour')
            time_resolution_minute = request.POST.get('time_resolution_minute')
            time_resolution_second = request.POST.get('time_resolution_second')
            time_default_value_mode = request.POST.get('time_default_value_mode')
            time_default_value = request.POST.get('time_default_value')

            time_resolution = request.POST.get('time_resolution')

        layer_md_uuid = request.POST.get('uuid', '').strip()
        core_utils.update_layer_metadata_uuid(layer, layer_md_uuid)

        old_layer_group = LayerGroup.objects.get(id=layer.layer_group_id)

        ds = Datastore.objects.get(id=layer.datastore.id)
        gs = geographic_servers.get_instance().get_server_by_id(ds.workspace.server.id)
        if gs.updateResource(workspace, layer.datastore.name, layer.datastore.type, name, updatedParams=updatedParams):
            layer.title = title
            layer.cached = cached
            layer.visible = is_visible
            layer.abstract = abstract
            layer.queryable = is_queryable
            layer.allow_download = allow_download
            layer.single_image = single_image
            layer.layer_group_id = layer_group_id
            layer.time_enabled = time_enabled
            layer.time_enabled_field = time_field
            layer.time_enabled_endfield = time_endfield
            layer.time_presentation = time_presentation
            layer.time_resolution_year = time_resolution_year
            layer.time_resolution_month = time_resolution_month
            layer.time_resolution_week = time_resolution_week
            layer.time_resolution_day = time_resolution_day
            layer.time_resolution_hour = time_resolution_hour
            layer.time_resolution_minute = time_resolution_minute
            layer.time_resolution_second = time_resolution_second
            layer.time_default_value_mode = time_default_value_mode
            layer.time_default_value = time_default_value
            layer.time_resolution = time_resolution
            layer.detailed_info_enabled = detailed_info_enabled
            layer.detailed_info_button_title = detailed_info_button_title
            layer.detailed_info_html = detailed_info_html
            layer.timeout = request.POST.get('timeout')
            
            params = {}
            params['format'] = request.POST.get('format')
            layer.external_params = json.dumps(params)
            layer.conf = layerConf
            layer.save()
            
            if 'layer-image' in request.FILES:
                up_file = request.FILES['layer-image']
                path, _ = utils.get_layer_img(layer.id, up_file.name)
                
                destination = open(path, 'wb+')
                for chunk in up_file.chunks():
                    destination.write(chunk)
                    destination.close()
                  

            if layer.datastore.type == 'c_ImageMosaic':
                gs.updateImageMosaicTemporal(layer.datastore, layer)


            if ds.type != 'e_WMS':
                gs.setQueryable(workspace, ds.name, ds.type, name, is_queryable)
                if ds.type == 'v_PostGIS':
                    utils.set_time_enabled(gs, layer)

            new_layer_group = LayerGroup.objects.get(id=layer.layer_group_id)

            if old_layer_group.id != new_layer_group.id:
                core_utils.toc_move_layer(layer, old_layer_group)
                gs.createOrUpdateGeoserverLayerGroup(old_layer_group)
                gs.createOrUpdateGeoserverLayerGroup(new_layer_group)
                                
            gs.reload_nodes()   
        
        if redirect_to_layergroup:
            return HttpResponseRedirect(reverse('layer_permissions_update', kwargs={'layer_id': layer_id})+"?redirect=grouplayer-redirect")
        else:
            return HttpResponseRedirect(reverse('layer_permissions_update', kwargs={'layer_id': layer_id}))
    else:

        layer = Layer.objects.get(id=int(layer_id))
        datastore = Datastore.objects.get(id=layer.datastore.id)
        workspace = Workspace.objects.get(id=datastore.workspace_id)
        form = LayerUpdateForm(instance=layer)
        
        if layer.external_params:
            params = json.loads(layer.external_params)
            for key in params:
                form.initial[key] = params[key]

        if not request.user.is_superuser:
            form.fields['datastore'].queryset = Datastore.objects.filter(created_by__exact=request.user.username)
            form.fields['layer_group'].queryset =(LayerGroup.objects.filter(created_by__exact=request.user.username) | LayerGroup.objects.filter(name='__default__')).order_by('name')

        try:
            layerConf = ast.literal_eval(layer.conf)
        except:
            layerConf = {}
        
        date_fields = []
        if layer.type.startswith('v_'):
            # ensure we get a value for max_features
            layerConf['featuretype'] = layerConf.get('featuretype', {})
            layerConf['featuretype']['max_features'] = layerConf['featuretype'].get('max_features', 0)
        if layer.type == 'v_PostGIS':
            aux_fields = get_date_fields(layer.id)
            if 'fields' in layerConf:
                for field in layerConf['fields']:
                    for data_field in aux_fields:
                        if field['name'] == data_field:
                            date_fields.append(field)

        md_uuid = core_utils.get_layer_metadata_uuid(layer)
        plugins_config = core_utils.get_plugins_config()
        html = True
        if layer.detailed_info_html == None or layer.detailed_info_html == '' or layer.detailed_info_html == 'null':
            html = False
        
        _, layer_image_url = utils.get_layer_img(layer.id, None)
        return render(request, 'layer_update.html', {'html': html, 'layer': layer, 'workspace': workspace, 'form': form, 'layer_id': layer_id, 'layer_conf': layerConf, 'date_fields': json.dumps(date_fields), 'redirect_to_layergroup': redirect_to_layergroup, 'layer_md_uuid': md_uuid, 'plugins_config': plugins_config, 'layer_image_url': layer_image_url, 'datastore_type': layer.datastore.type})

def get_date_fields(layer_id):
    date_fields = []

    layer = Layer.objects.get(id=int(layer_id))
    datastore = Datastore.objects.get(id=layer.datastore_id)
    workspace = Workspace.objects.get(id=datastore.workspace_id)
    gs = geographic_servers.get_instance().get_server_by_id(workspace.server.id)
    (ds_type, resource) = gs.getResourceInfo(workspace.name, datastore, layer.name, "json")
    resource_fields = utils.get_alphanumeric_fields(utils.get_fields(resource))
    for f in resource_fields:
        if f['binding'] == 'java.sql.Date':
            date_fields.append(f['name'])
        if f['binding'] == 'java.sql.Timestamp':
            date_fields.append(f['name'])

    return date_fields


@csrf_exempt
def get_date_fields_from_resource(request):
    if request.method == 'POST':
        resource_name = request.POST.get('name')
        datastore_id = request.POST.get('datastore')

        date_fields = []
        ds = Datastore.objects.get(id=int(datastore_id))
        if ds.type == 'v_PostGIS':
            params = json.loads(ds.connection_params)
            host = params['host']
            port = params['port']
            dbname = params['database']
            user = params['user']
            passwd = params['passwd']
            schema = params.get('schema', 'public')
            i = Introspect(database=dbname, host=host, port=port, user=user, password=passwd)
            layer_defs = i.get_fields_info(resource_name, schema)
            i.close()
            
            for layer_def in layer_defs:
                if layer_def['type'] == 'date':
                    date_fields.append(layer_def['name'])
                if layer_def['type'].startswith('timestamp'):
                    date_fields.append(layer_def['name'])

        response = {
            'date_fields': date_fields
        }

        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')


def layer_autoconfig(layer, featuretype):
    fields = []
    available_languages = []
    for id, language in LANGUAGES:
        available_languages.append(id)

    datastore = layer.datastore
    workspace = datastore.workspace
    server = geographic_servers.get_instance().get_server_by_id(workspace.server.id)
    (ds_type, layer_info) = server.getResourceInfo(workspace.name, datastore, layer.name, "json")
    utils.set_layer_extent(layer, ds_type, layer_info, server)
    if (ds_type != 'coverage'):
        resource_fields = utils.get_alphanumeric_fields(utils.get_fields(layer_info))    
        for f in resource_fields:
            field = {}
            field['name'] = f['name']
            for id, language in LANGUAGES:
                field['title-'+id] = f['name']
            field['visible'] = True
            field['editableactive'] = True
            field['editable'] = True
            for control_field in settings.CONTROL_FIELDS:
                if field['name'] == control_field['name']:
                    field['editableactive'] = False
                    field['editable'] = False
            field['infovisible'] = False
            field['mandatory'] = False
            fields.append(field)

    layer_conf = {
        'fields': fields,
        'featuretype': featuretype
        }

    layer.conf = layer_conf


@login_required(login_url='/gvsigonline/auth/login_user/')
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def layer_config(request, layer_id):
    redirect_to_layergroup = request.GET.get('redirect')

    if request.method == 'POST':
        layer = Layer.objects.get(id=int(layer_id))
        old_conf = ast.literal_eval(layer.conf) if layer.conf else {}

        conf = {
            "featuretype": old_conf.get('featuretype', {})
            }
        fields = []
        counter = int(request.POST.get('counter'))
        for i in range(1, counter+1):
            field = {}
            field['name'] = request.POST.get('field-name-' + str(i))
            for id, language in LANGUAGES:
                field['title-'+id] = request.POST.get('field-title-'+id+'-' + str(i)).strip()
            field['visible'] = False
            if 'field-visible-' + str(i) in request.POST:
                field['visible'] = True
            field['infovisible'] = False
            if 'field-infovisible-' + str(i) in request.POST:
                field['infovisible'] = True
            field['mandatory'] = False
            if 'field-mandatory-' + str(i) in request.POST:
                if _set_field_mandatory(layer_id, field['name'], True):
                    field['mandatory'] = True
                else:
                    field['mandatory'] = False
            else:
                if _set_field_mandatory(layer_id, field['name'], False):
                    field['mandatory'] = False
                else:
                    field['mandatory'] = True
            field['editable'] = False
            if 'field-editable-' + str(i) in request.POST:
                field['editableactive'] = True
                field['editable'] = True
                for control_field in settings.CONTROL_FIELDS:
                    if field['name'] == control_field['name']:
                        field['editableactive'] = False
                        field['editable'] = False
            fields.append(field)
        conf['fields'] = fields
        layer.conf = conf
        layer.save()

        if redirect_to_layergroup:
            layergroup_id = layer.layer_group.id
            return HttpResponseRedirect(reverse('layergroup_update', kwargs={'lgid': layergroup_id}))
        else:
            return redirect('layer_list')

    else:
        layer = Layer.objects.get(id=int(layer_id))
        fields = []
        available_languages = []
        for id, language in LANGUAGES:
            available_languages.append(id)

        try:
            conf = ast.literal_eval(layer.conf)
            fields_used = []
            fields_mand = _get_fields_mandatory(layer_id)
            for f in conf['fields']:
                field = {}
                field['name'] = f['name']
                fields_used.append(f['name'])
                for id, language in LANGUAGES:
                    field['title-'+id] = f['title-'+id]
                field['visible'] = f['visible']
                field['editable'] = f['editable']
                field['editableactive'] = True
                for control_field in settings.CONTROL_FIELDS:
                    if field['name'] == control_field['name']:
                        field['editableactive'] = False
                        field['editable'] = False
                field['infovisible'] = f['infovisible']
                field['mandatory'] = fields_mand[field['name']]
                fields.append(field)

            datastore = Datastore.objects.get(id=layer.datastore_id)
            workspace = Workspace.objects.get(id=datastore.workspace_id)
            gs = geographic_servers.get_instance().get_server_by_id(workspace.server.id)
            (ds_type, resource) = gs.getResourceInfo(workspace.name, datastore, layer.name, "json")
            resource_fields = utils.get_alphanumeric_fields(utils.get_fields(resource))
            for f in resource_fields:
                field = {}
                field['name'] = f['name']
                if not f['name'] in fields_used:
                    for id, language in LANGUAGES:
                        field['title-'+id] = f['name']
                    field['visible'] = True
                    field['editableactive'] = True
                    field['editable'] = True
                    for control_field in settings.CONTROL_FIELDS:
                        if field['name'] == control_field['name']:
                            field['editableactive'] = False
                            field['editable'] = False
                    field['infovisible'] = False
                    field['mandatory'] = False
                    fields.append(field)



        except:
            datastore = Datastore.objects.get(id=layer.datastore_id)
            workspace = Workspace.objects.get(id=datastore.workspace_id)
            gs = geographic_servers.get_instance().get_server_by_id(workspace.server.id)
            (ds_type, resource) = gs.getResourceInfo(workspace.name, datastore, layer.name, "json")
            resource_fields = utils.get_alphanumeric_fields(utils.get_fields(resource))
            for f in resource_fields:
                field = {}
                field['name'] = f['name']
                for id, language in LANGUAGES:
                    field['title-'+id] = f['name']
                field['visible'] = True
                field['editableactive'] = True
                field['editable'] = True
                for control_field in settings.CONTROL_FIELDS:
                    if field['name'] == control_field['name']:
                        field['editableactive'] = False
                        field['editable'] = False
                field['infovisible'] = False
                field['mandatory'] = False
                fields.append(field)
                
        enums = Enumeration.objects.all();
        
        return render(request, 'layer_config.html', {'layer': layer, 'layer_id': layer.id, 'fields': fields, 'fields_json': json.dumps(fields), 'available_languages': LANGUAGES, 'available_languages_array': available_languages, 'redirect_to_layergroup': redirect_to_layergroup, 'enumerations': enums})

def _set_field_mandatory(layer_id, field_name, mandatory):
    """
    Sets a column to NULL or NOT NULL constraint depending on 
    "mandatory" parameter. "Mandatory" should be True to set a column
    to NOT NULL and False otherwise
    """
    i, layername, dsname = utils.get_db_connect_from_layer(layer_id)
    try:
        if(mandatory) :
            i.set_field_mandatory(dsname, layername, field_name)
        else:
            i.set_field_not_mandatory(dsname, layername, field_name)
    except Exception:
        return False
    return True

def _get_field_mandatory(layer_id, field_name):
    i, layername, dsname = utils.get_db_connect_from_layer(layer_id)
    return i.is_column_nullable(dsname, layername, field_name)

def _get_fields_mandatory(layer_id):
    i, layername, dsname = utils.get_db_connect_from_layer(layer_id)
    return i.nullable_cols(dsname, layername)

@login_required(login_url='/gvsigonline/auth/login_user/')
@require_http_methods(["POST"])
@staff_required
def check_has_null_values(request):
    layer_id = request.POST['layer_id']
    field_name = request.POST['field_name']
    i, layername, dsname = utils.get_db_connect_from_layer(layer_id)
    hasnullvalues = i.check_has_null_values(dsname, layername, field_name)
    if(hasnullvalues):
        return utils.get_exception(405, 'The field has null values')
    return HttpResponse('{"response": "ok"}', content_type='application/json')
    

@login_required(login_url='/gvsigonline/auth/login_user/')
@require_http_methods(["POST"])
@staff_required
def convert_to_enumerate(request):
    try: 
        field = request.POST['field']
        enum_id = request.POST['enum_id']
        layer_name = request.POST['layer_name']
        layer_id = request.POST['layer_id']
        autogen = False if request.POST['autogen'] == 'False' else True
    except Exception:
        return utils.get_exception(400, 'Error in the input params')
    usr = request.user

    layer = Layer.objects.get(id=layer_id)
    datastore_name = layer.datastore.name
       
    is_enum, _ = utils.is_field_enumerated(layer, field)
    if is_enum:
        return utils.get_exception(405, 'The field is already enumerated')
    
    if autogen:
        params = json.loads(layer.datastore.connection_params)
        con = Introspect(database=params['database'], host=params['host'], port=params['port'], user=params['user'], password=params['passwd'])
        query = sql.SQL("SELECT {field} FROM {schema}.{table} GROUP BY {field}").format(
            field=sql.Identifier(field),
            schema=sql.Identifier(datastore_name),
            table=sql.Identifier(layer_name))
        con.cursor.execute(query, [])
        rows = con.cursor.fetchall()
        enum_table = Enumeration()
        enum_table.name =  layer_name + "_" + field 
        enum_table.title = re.sub(r'\w+', lambda m:m.group(0).capitalize(), layer_name) + " " + re.sub(r'\w+', lambda m:m.group(0).capitalize(), field)
        enum_table.created_by = usr
        enum_table.save()
        enum_id = enum_table.id
        i = 0
        for row in rows:
            item = EnumerationItem()
            item.name = row[0]
            item.selected = False
            item.order = i
            i = i +1
            item.enumeration_id = enum_id
            item.save()
    
    if enum_id == None:
        return utils.get_exception(400, 'We cannot find a enumerated with this name')
    
    field_enum = LayerFieldEnumeration()
    field_enum.layer = layer
    field_enum.field = field
    field_enum.enumeration_id = enum_id
    field_enum.multiple = False
    field_enum.save()   
    
    return HttpResponse('{"response": "ok"}', content_type='application/json') 

@require_http_methods(["POST"])
@csrf_exempt
def layers_get_temporal_properties(request):
    try:
        #layer = Layer.objects.get(pk=layer_id)
        layers = []
        if 'layers' in request.POST:
            layers = json.loads(request.POST['layers'])
        methodx = ''
        if 'methodx' in request.POST:
            methodx = request.POST['methodx']

        min_value = ''
        max_value = ''
        list_values = []
        temporal_defs = []
        mosaic_values = {}
        for layer_id in layers:
            layer = Layer.objects.get(id=layer_id)
            params = json.loads(layer.datastore.connection_params)
            if layer.datastore.type == 'c_ImageMosaic':
                host = MOSAIC_DB['host']
                port = MOSAIC_DB['port']
                dbname = MOSAIC_DB['database']
                user = MOSAIC_DB['user']
                passwd = MOSAIC_DB['passwd']
                schema = 'imagemosaic'
                i = Introspect(database=dbname, host=host, port=port, user=user, password=passwd)
                temporal_defs = i.get_mosaic_temporal_info(layer.name, schema, layer.time_default_value_mode, layer.time_default_value)
                i.close()

            else:
                host = params['host']
                port = params['port']
                dbname = params['database']
                user = params['user']
                passwd = params['passwd']
                schema = params.get('schema', 'public')
                i = Introspect(database=dbname, host=host, port=port, user=user, password=passwd)
                temporal_defs = i.get_temporal_info(layer.name, schema, layer.time_enabled_field, layer.time_enabled_endfield, layer.time_default_value_mode, layer.time_default_value)
                i.close()
                
            if temporal_defs.__len__() > 0 and temporal_defs[0]['min_value'] != '' and temporal_defs[0]['max_value'] != '':
                aux_min_value = datetime.strptime(temporal_defs[0]['min_value'], '%Y-%m-%d %H:%M:%S')
                if min_value == '' or datetime.strptime(min_value, '%Y-%m-%d %H:%M:%S') > aux_min_value:
                    min_value = temporal_defs[0]['min_value']
                aux_max_value = datetime.strptime(temporal_defs[0]['max_value'], '%Y-%m-%d %H:%M:%S')
                if max_value == '' or datetime.strptime(max_value, '%Y-%m-%d %H:%M:%S') < aux_max_value:
                    max_value = temporal_defs[0]['max_value']
                #list_values = list_values + temporal_defs['list_values']
                if 'values' in temporal_defs[0] and temporal_defs[0]['values']:
                    mosaic_values[layer.name] = temporal_defs[0]['values']


        response = '{"response": "ok", "min_value": "'+str(min_value)+'", "max_value": "'+str(max_value)+'", "list_values": "'+str(list_values)+'", "mosaic_values": "'+json.dumps(mosaic_values).replace("\"", "'")+'"}'
        return HttpResponse(response, content_type='application/json')


    except Exception as e:
        return HttpResponseNotFound('<h1>Temporal properties not found </h1>')



@require_POST
@staff_required
def layer_boundingbox_from_data(request):
    try:
        #layer = Layer.objects.get(pk=layer_id)
        ws_name = request.POST['workspace']
        layer_name = request.POST['layer']
        if ":" in layer_name:
            layer_name = layer_name.split(":")[1]
        workspace = Workspace.objects.get(name=ws_name)
        layer_query_set = Layer.objects.filter(external=False).filter(name=layer_name, datastore__workspace=workspace)
        layer = layer_query_set[0]
        gs = geographic_servers.get_instance().get_server_by_id(workspace.server.id)
        gs.updateBoundingBoxFromData(layer)  
        gs.clearCache(workspace.name, layer)
        gs.updateThumbnail(layer, 'update')
        
        layer_group = LayerGroup.objects.get(id=layer.layer_group_id)
        gs.createOrUpdateGeoserverLayerGroup(layer_group)
        gs.clearLayerGroupCache(layer_group.name)
        gs.reload_nodes()

        return HttpResponse('{"response": "ok"}', content_type='application/json')

    except Exception as e:
        return HttpResponseNotFound('<h1>Layer not found: {0}</h1>'.format(layer.id))


def layer_cache_clear(layer_id):
    layer = Layer.objects.get(id=int(layer_id))
    datastore = Datastore.objects.get(id=layer.datastore.id)
    workspace = Workspace.objects.get(id=datastore.workspace_id)
    gs = geographic_servers.get_instance().get_server_by_id(workspace.server.id)
    gs.clearCache(workspace.name, layer)
    gs.reload_nodes()
            
    gs.updateBoundingBoxFromData(layer)  
    gs.clearCache(workspace.name, layer)
    gs.updateThumbnail(layer, 'update')

    layer_group = LayerGroup.objects.get(id=layer.layer_group_id)
    gs.createOrUpdateGeoserverLayerGroup(layer_group)
    gs.clearLayerGroupCache(layer_group.name)


@login_required(login_url='/gvsigonline/auth/login_user/')
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def cache_clear(request, layer_id):
    redirect_to_layergroup = request.GET.get('redirect')

    layer = Layer.objects.get(id=int(layer_id))
    gs = geographic_servers.get_instance().get_server_by_id(layer.datastore.workspace.server.id)
    if request.method == 'GET' or request.method == 'POST':
        layer_cache_clear(layer_id)
        gs.reload_nodes()
        
    if request.method == 'GET':
        if redirect_to_layergroup:           
            layergroup_id = layer.layer_group.id
            return HttpResponseRedirect(reverse('layergroup_update', kwargs={'lgid': layergroup_id}))
        else:
            return redirect('layer_list')

    else:
        return HttpResponse('{"response": "ok"}', content_type='application/json')
    
@login_required(login_url='/gvsigonline/auth/login_user/')
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def manage_cache_clear(request, layer_id):

    layer = Layer.objects.get(id=int(layer_id))
    layer_group = LayerGroup.objects.get(id=layer.layer_group.id)
    server = Server.objects.get(id=layer_group.server_id)
    gs = geographic_servers.get_instance().get_server_by_id(server.id)
    if request.method == 'GET' or request.method == 'POST':
        if layer.external:
            print 'TO DO'
            
        else:
            layer_cache_clear(layer_id)
            
        gs.reload_nodes()
        
    if request.method == 'GET':
        return redirect('cache_list')

    else:
        return HttpResponse('{"response": "ok"}', content_type='application/json')
    
@login_required(login_url='/gvsigonline/auth/login_user/')
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def group_cache_clear(request, layergroup_id):
    if request.method == 'GET':
        layergroup = LayerGroup.objects.get(id=int(layergroup_id))
        layer_group_cache_clear(layergroup)

        return redirect('layergroup_list')

@login_required(login_url='/gvsigonline/auth/login_user/')
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def layergroup_cache_clear(request, layergroup_id):
    if request.method == 'GET':
        layergroup = LayerGroup.objects.get(id=int(layergroup_id))
        layer_group_cache_clear(layergroup)

        return redirect('layergroup_list')


def layer_group_cache_clear(layergroup):
    last = None    
    layers = Layer.objects.filter(external=False).filter(layer_group_id=int(layergroup.id))
    for layer in layers:
        if not layer.external:
            layer_cache_clear(layer.id)
            last = layer

    if last:
        gs = geographic_servers.get_instance().get_server_by_id(last.datastore.workspace.server.id)
        gs.deleteGeoserverLayerGroup(layergroup)
    
        gs.createOrUpdateGeoserverLayerGroup(layergroup)
        gs.clearLayerGroupCache(layergroup.name)
        gs.reload_nodes()






@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def layer_permissions_update(request, layer_id):
    redirect_to_layergroup = request.GET.get('redirect')

    if request.method == 'POST':
        assigned_read_roups = []
        for key in request.POST:
            if 'read-usergroup-' in key:
                assigned_read_roups.append(int(key.split('-')[2]))

        assigned_write_groups = []
        for key in request.POST:
            if 'write-usergroup-' in key:
                assigned_write_groups.append(int(key.split('-')[2]))

        try:
            layer = Layer.objects.get(id=int(layer_id))
        except Exception as e:
            return HttpResponseNotFound('<h1>Layer not found{0}</h1>'.format(layer.name))

        agroup = UserGroup.objects.get(name__exact='admin')

        read_groups = []
        write_groups = []

        # clean existing groups and assign them again if necessary
        LayerReadGroup.objects.filter(layer=layer).delete()
        if len(assigned_read_roups) > 0:
            lrag = LayerReadGroup()
            lrag.layer = layer
            lrag.group = agroup
            lrag.save()
            read_groups.append(agroup)
        for group in assigned_read_roups:
            try:
                group = UserGroup.objects.get(id=group)
                lrg = LayerReadGroup()
                lrg.layer = layer
                lrg.group = group
                lrg.save()
                read_groups.append(group)
            except:
                pass

        LayerWriteGroup.objects.filter(layer=layer).delete()
        if not layer.type.startswith('c_'):
            lwag = LayerWriteGroup()
            lwag.layer = layer
            lwag.group = agroup
            lwag.save()
            write_groups.append(agroup)
        for group in assigned_write_groups:
            try:
                group = UserGroup.objects.get(id=group)
                lwg = LayerWriteGroup()
                lwg.layer = layer
                lwg.group = group
                lwg.save()
                write_groups.append(group)
            except:
                pass
                
        gs = geographic_servers.get_instance().get_server_by_id(layer.datastore.workspace.server.id)        
        gs.setLayerDataRules(layer, read_groups, write_groups)
        gs.reload_nodes()

        if redirect_to_layergroup:
            layergroup_id = layer.layer_group.id
            return HttpResponseRedirect(reverse('layergroup_update', kwargs={'lgid': layergroup_id}))
        else:
            return redirect('layer_list')
    else:
        try:
            layer = Layer.objects.get(pk=layer_id)
            groups = utils.get_all_user_groups_checked_by_layer(layer)
            return render(request, 'layer_permissions_add.html', {'layer_id': layer.id, 'name': layer.name, 'type': layer.type, 'groups': groups, 'redirect_to_layergroup': redirect_to_layergroup})
        except Exception as e:
            return HttpResponseNotFound('<h1>Layer not found: {0}</h1>'.format(layer_id))

def get_resources_from_workspace(request):
    # FIXME
    if request.method == 'POST':
        wid = request.POST.get('workspace_id')
        layer_list = Layer.objects.filter(external=False)

        resources = []
        for r in layer_list:
            if not resource_published(r):
                datastore = Datastore.objects.get(id=r.datastore_id)
                resource = {}
                if datastore.workspace_id == int(wid):
                    resource['id'] = r.id
                    resource['name'] = r.name
                    resources.append(resource)

        response = {
            'resources': resources
        }
        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')

def resource_published(resource):
    # FIXME
    published = False
    layers = Layer.objects.filter(external=False)
    for layer in layers:
        if layer.resource.id == resource.id:
            published = True

    return published


@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def layergroup_list(request):

    layergroups_list = None
    if request.user.is_superuser:
        layergroups_list = LayerGroup.objects.all()
    else:
        layergroups_list = LayerGroup.objects.filter(created_by__exact=request.user.username)

    layergroups = []
    for lg in layergroups_list:
        if lg.name != '__default__':
            server = Server.objects.get(id=lg.server_id)
            projects = []
            project_layergroups = ProjectLayerGroup.objects.filter(layer_group_id=lg.id)
            for alg in project_layergroups:
                projects.append(alg.project.name)
            layergroup = {}
            layergroup['id'] = lg.id
            layergroup['name'] = lg.name
            layergroup['title'] = lg.title
            layergroup['cached'] = lg.cached
            layergroup['projects'] = '; '.join(projects)
            layergroup['server'] = server.title
            layergroups.append(layergroup)

    response = {
        'layergroups': layergroups
    }
    return render(request, 'layergroup_list.html', response)



@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def layergroup_add(request):
    return layergroup_add_with_project(request, None)


@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def layergroup_add_with_project(request, project_id):
    if request.method == 'POST':
        name = request.POST.get('layergroup_name')
        title = request.POST.get('layergroup_title')
        server_id = request.POST.get('layergroup_server_id')
        
        cached = False
        if 'cached' in request.POST:
            cached = True

        visible = False
        if 'visible' in request.POST:
            visible = True

        if name != '':
            name = request.POST.get('layergroup_name') + '_' + request.user.username
            if _valid_name_regex.search(name) == None:
                message = _("Invalid layer group name: '{value}'. Identifiers must begin with a letter or an underscore (_). Subsequent characters can be letters, underscores or numbers").format(value=name)
                return render(request, 'layergroup_add.html', {'message': message, 'servers': Server.objects.values()})

            exists = False
            layergroups = LayerGroup.objects.all()
            for lg in layergroups:
                if name == lg.name:
                    exists = True

            if not exists:
                layergroup = LayerGroup(
                    server_id = server_id,
                    name = name,
                    title = title,
                    cached = cached,
                    visible = visible,
                    created_by = request.user.username
                )
                layergroup.save()

                project_id = request.POST.get('layergroup_project_id')
                if project_id and project_id != '':
                    project = Project.objects.get(id=int(project_id))
                    project_layergroup = ProjectLayerGroup(
                        project = project,
                        layer_group = layergroup
                    )
                    project_layergroup.save()

                    assigned_layergroups = []
                    prj_lyrgroups = ProjectLayerGroup.objects.filter(project_id=project.id)
                    for prj_lyrgroup in prj_lyrgroups:
                        assigned_layergroups.append(prj_lyrgroup.layer_group.id)

                    toc_structure = core_utils.get_json_toc(assigned_layergroups)
                    project.toc_order = toc_structure
                    project.save()

                if 'redirect' in request.GET:
                    redirect_var = request.GET.get('redirect')
                    if redirect_var == 'create-layer':
                        return HttpResponseRedirect(reverse('layer_create_with_group', kwargs={'layergroup_id': layergroup.id})+"?redirect=grouplayer-redirect")
                    if redirect_var == 'import-layer':
                        return HttpResponseRedirect(reverse('layer_add_with_group', kwargs={'layergroup_id': layergroup.id})+"?redirect=grouplayer-redirect")

                return redirect('layergroup_list')


            else:
                message = _(u'Layer group name already exists')
                return render(request, 'layergroup_add.html', {'message': message, 'servers': Server.objects.values(), 'project_id': project_id, 'workspaces': Workspace.objects.values()})

        else:
            message = _(u'You must enter a name for layer group')
            return render(request, 'layergroup_add.html', {'message': message, 'servers': Server.objects.values(), 'project_id': project_id, 'workspaces': Workspace.objects.values()})

        return redirect('layergroup_list')

    else:
        response = {
            'project_id': project_id,
            'servers': Server.objects.values()
        }
        return render(request, 'layergroup_add.html', response)


def layergroup_mapserver_toc(group, toc_string):
    if toc_string != None or toc_string != '':
        toc_array = toc_string.split(',')
        layers_array = {}
        i=0
        toc_array = toc_array[::-1]
        last = None
        for toc_entry in toc_array:
            layers = Layer.objects.filter(name=toc_entry,layer_group_id=group.id).order_by('order')
            for layer in layers:
                #if not layer.external:
                layer_json = {
                        'name': layer.name,
                        'title': layer.title,
                        'order': 1000+i
                    }
                layer.order = i
                layer.save()
                i = i + 1
                layers_array[layer.name] = layer_json
                if not layer.external:
                    last = layer

        toc_object = {
            'name': group.name,
            'title': group.title,
            'order': 1000,
            'layers': layers_array

        }

        toc={}
        toc[group.name] = toc_object
        
        if last:
            gs = geographic_servers.get_instance().get_server_by_id(last.datastore.workspace.server.id)  
            gs.createOrUpdateSortedGeoserverLayerGroup(toc)
            gs.reload_nodes()


@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def layergroup_update(request, lgid):
    if request.method == 'POST':
        name = request.POST.get('layergroup_name')
        title = request.POST.get('layergroup_title')
        toc = request.POST.get('toc')

        cached = False
        if 'cached' in request.POST:
            cached = True

        visible = False
        if 'visible' in request.POST:
            visible = True

        layergroup = LayerGroup.objects.get(id=int(lgid))

        sameName = False
        if layergroup.name == name:
            sameName = True

        exists = False
        layergroups = LayerGroup.objects.all()
        for lg in layergroups:
            if name == lg.name:
                exists = True

        old_name = layergroup.name

        if sameName:
            layergroup.title = title
            layergroup.cached = cached
            layergroup.visible = visible
            layergroup.save()
            core_utils.toc_update_layer_group(layergroup, old_name, name, title)

            layergroup_mapserver_toc(layergroup, toc)
            layer_group_cache_clear(layergroup)
            if 'redirect' in request.GET:
                redirect_var = request.GET.get('redirect')
                if redirect_var == 'create-layer':
                    return HttpResponseRedirect(reverse('layer_create_with_group', kwargs={'layergroup_id': layergroup.id})+"?redirect=grouplayer-redirect")
                if redirect_var == 'import-layer':
                    return HttpResponseRedirect(reverse('layer_add_with_group', kwargs={'layergroup_id': layergroup.id})+"?redirect=grouplayer-redirect")

            return redirect('layergroup_list')

        else:
            if not exists:
                if _valid_name_regex.search(name) == None:
                    message = _("Invalid layer group name: '{value}'. Identifiers must begin with a letter or an underscore (_). Subsequent characters can be letters, underscores or numbers").format(value=name)
                    return render(request, 'layergroup_update.html', {'message': message, 'servers': Server.objects.values()})

                layergroup.name = name
                layergroup.title = title
                layergroup.cached = cached
                layergroup.visible = visible
                layergroup.save()
                core_utils.toc_update_layer_group(layergroup, old_name, name, title)

                layergroup_mapserver_toc(layergroup, toc)
                layer_group_cache_clear(layergroup)
                if 'redirect' in request.GET:
                    redirect_var = request.GET.get('redirect')
                    if redirect_var == 'create-layer':
                        return HttpResponseRedirect(reverse('layer_create_with_group', kwargs={'layergroup_id': layergroup.id})+"?redirect=grouplayer-redirect")
                    if redirect_var == 'import-layer':
                        return HttpResponseRedirect(reverse('layer_add_with_group', kwargs={'layergroup_id': layergroup.id})+"?redirect=grouplayer-redirect")
                return redirect('layergroup_list')

            else:
                message = _(u'Layer group name already exists')
                return render(request, 'layergroup_update.html', {'message': message, 'layergroup': layergroup, 'servers': Server.objects.values()})

    else:
        layergroup = LayerGroup.objects.get(id=int(lgid))
        layers = Layer.objects.filter(layer_group_id=layergroup.id).order_by('-order') 
        
        response = {
            'lgid': lgid, 
            'layergroup': layergroup, 
            'layers': layers,
            'workspaces': Workspace.objects.values(),
            'servers': Server.objects.values()
        }

        return render(request, 'layergroup_update.html', response)


@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def layergroup_delete(request, lgid):
    if request.method == 'POST':
        layergroup = LayerGroup.objects.get(id=int(lgid))
        server = Server.objects.get(id=layergroup.server_id)
        layers = Layer.objects.filter(layer_group_id=layergroup.id)
        projects_by_layergroup = ProjectLayerGroup.objects.filter(layer_group_id=layergroup.id)

        for p in projects_by_layergroup:
            p.project.toc_order = core_utils.toc_remove_layergroups(p.project.toc_order, [layergroup.id])
            p.project.save()

        for layer in layers:
            default_layer_group = LayerGroup.objects.get(name__exact='__default__')
            layer.layer_group = default_layer_group
            layer.save()
        
        gs = geographic_servers.get_instance().get_server_by_id(server.id)  
        try:      
            gs.deleteGeoserverLayerGroup(layergroup)
            gs.setDataRules()
            gs.reload_nodes()
            
        except Exception:
            layergroup.delete()
        
        response = {
            'deleted': True
        }
        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')


def prepare_string(s):
    return ''.join((c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')).replace (" ", "_").replace ("-", "_").lower()


@login_required(login_url='/gvsigonline/auth/login_user/')
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def layer_create(request):
    return layer_create_with_group(request, None)


@login_required(login_url='/gvsigonline/auth/login_user/')
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def layer_create_with_group(request, layergroup_id):
    redirect_to_layergroup = request.GET.get('redirect')

    layer_type = "gs_vector_layer"
    if request.method == 'POST':

        abstract = request.POST.get('md-abstract')
        is_visible = False
        if 'visible' in request.POST:
            is_visible = True

        is_queryable = False
        if 'queryable' in request.POST:
            is_queryable = True

        cached = False
        if 'cached' in request.POST:
            cached = True

        single_image = False
        if 'single_image' in request.POST:
            single_image = True
            cached = False
            
        allow_download = False
        if 'allow_download' in request.POST:
            allow_download = True

        try:
            maxFeatures = int(request.POST.get('max_features', 0))
        except:
            maxFeatures = 0

        time_enabled = False
        time_field=''
        time_endfield=''
        time_presentation = ''
        time_resolution_year = 0
        time_resolution_month = 0
        time_resolution_week = 0
        time_resolution_day = 0
        time_resolution_hour = 0
        time_resolution_minute = 0
        time_resolution_second = 0
        time_default_value_mode = ''
        time_default_value = ''

        time_resolution = ''

        if 'time_enabled' in request.POST:
            time_enabled = True
            time_field = request.POST.get('time_enabled_field')
            time_endfield = request.POST.get('time_enabled_endfield')
            time_presentation = request.POST.get('time_presentation')
            #time_resolution_year = request.POST.get('time_resolution_year')
            #time_resolution_month = request.POST.get('time_resolution_month')
            #time_resolution_week = request.POST.get('time_resolution_week')
            #time_resolution_day = request.POST.get('time_resolution_day')
            #time_resolution_hour = request.POST.get('time_resolution_hour')
            #time_resolution_minute = request.POST.get('time_resolution_minute')
            #time_resolution_second = request.POST.get('time_resolution_second')
            time_default_value_mode = request.POST.get('time_default_value_mode')
            time_default_value = request.POST.get('time_default_value')

            time_resolution = request.POST.get('time_resolution')


        form = CreateFeatureTypeForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                datastore = form.cleaned_data['datastore']
                server = geographic_servers.get_instance().get_server_by_id(datastore.workspace.server.id)
                form.cleaned_data['name'] = prepare_string(form.cleaned_data['name'])
                server.createTable(form.cleaned_data)
                extraParams = {}
                if datastore.type == 'v_PostGIS':
                    extraParams['maxFeatures'] = maxFeatures

                # first create the resource on the backend
                do_add_layer(server, datastore, form.cleaned_data['name'], form.cleaned_data['title'], is_queryable, extraParams)

                # save it on DB if successfully created
                newRecord = Layer(
                    datastore = datastore,
                    layer_group = form.cleaned_data['layer_group'],
                    name = form.cleaned_data['name'],
                    title = form.cleaned_data['title'],
                    abstract = abstract,
                    created_by = request.user.username,
                    type = form.cleaned_data['datastore'].type,
                    visible = is_visible,
                    queryable = is_queryable,
                    allow_download = allow_download,
                    cached = cached,
                    single_image = single_image
                )
                if not newRecord.source_name:
                    newRecord.source_name = newRecord.name
                newRecord.time_enabled = time_enabled
                newRecord.time_enabled_field = time_field
                newRecord.time_enabled_endfield = time_endfield
                newRecord.time_presentation = time_presentation
                newRecord.time_resolution_year = time_resolution_year
                newRecord.time_resolution_month = time_resolution_month
                newRecord.time_resolution_week = time_resolution_week
                newRecord.time_resolution_day = time_resolution_day
                newRecord.time_resolution_hour = time_resolution_hour
                newRecord.time_resolution_minute = time_resolution_minute
                newRecord.time_resolution_second = time_resolution_second
                newRecord.time_default_value_mode = time_default_value_mode
                newRecord.time_default_value = time_default_value
                newRecord.time_resolution = time_resolution
                newRecord.save()
                
                for i in form.cleaned_data['fields']:
                    if 'enumkey' in i:
                        field_enum = LayerFieldEnumeration()
                        field_enum.layer = newRecord
                        field_enum.field = i['name']
                        field_enum.enumeration_id = int(i['enumkey']) 
                        field_enum.multiple = True if i['type'] == 'multiple_enumeration' else False
                        field_enum.save() 
                featuretype = {
                    'max_features': maxFeatures
                }
                do_config_layer(server, newRecord, featuretype)
                if redirect_to_layergroup:
                    return HttpResponseRedirect(reverse('layer_permissions_update', kwargs={'layer_id': newRecord.id})+"?redirect=grouplayer-redirect")
                else:
                    return HttpResponseRedirect(reverse('layer_permissions_update', kwargs={'layer_id': newRecord.id}))


            except Exception as e:
                try:
                    msg = e.get_message()
                except:
                    msg = _("Error: layer could not be published")
                # FIXME: the backend should raise more specific exceptions to identify the cause (e.g. layer exists, backend is offline)
                form.add_error(None, msg)

                data = {
                    'form': form,
                    'message': msg,
                    'layer_type': layer_type,
                    'enumerations': get_currentuser_enumerations(request)

                }
                return render(request, "layer_create.html", data)

        else:
            forms = []
            if 'gvsigol_plugin_form' in INSTALLED_APPS:
                from gvsigol_plugin_form.models import Form
                forms = Form.objects.all()


            data = {
                'form': form,
                'forms': forms,
                'layer_type': layer_type,
                'enumerations': get_currentuser_enumerations(request)
            }
            return render(request, "layer_create.html", data)

    else:
        form = CreateFeatureTypeForm(user=request.user)
        forms = []

        if 'gvsigol_plugin_form' in INSTALLED_APPS:
            from gvsigol_plugin_form.models import Form
            forms = Form.objects.all()

        data = {
            'form': form,
            'forms': forms,
            'layer_type': layer_type,
            'enumerations': get_currentuser_enumerations(request),
            'layergroup_id': layergroup_id,
            'redirect_to_layergroup': redirect_to_layergroup
        }
        return render(request, "layer_create.html", data)

    return HttpResponseBadRequest()


def get_currentuser_enumerations(request):
    enumeration_list = None
    if request.user.is_superuser:
        enumeration_list = Enumeration.objects.all()
    else:
        enumeration_list = Enumeration.objects.filter(created_by__exact=request.user.username)
        users = User.objects.all()
        for user in users:
            if user.is_superuser:
                enumeration_list2 = Enumeration.objects.filter(created_by__exact=user.username)
                enumeration_list = enumeration_list | enumeration_list2
    return enumeration_list

@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def enumeration_list(request):

    enumeration_list = None
    if request.user.is_superuser:
        enumeration_list = Enumeration.objects.all()
    else:
        enumeration_list = Enumeration.objects.filter(created_by__exact=request.user.username)

    enumerations = []
    for e in enumeration_list:
        enum = {}
        enum['id'] = e.id
        enum['name'] = e.name
        enum['title'] = e.title
        enumerations.append(enum)

    response = {
        'enumerations': enumerations
    }
    return render(request, 'enumeration_list.html', response)


@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def enumeration_add(request):
    if request.method == 'POST':
        name = request.POST.get('enumeration_name')
        title = request.POST.get('enumeration_title')

        aux_title = ''.join(title.encode('ASCII', 'ignore').split())[:4]
        aux_title = aux_title.lower()

        name = name + '_' + re.sub("[!@#$%^&*()[]{};:,./<>?\|`~-=_+ ]", "", aux_title)

        name_exists = False
        enums = Enumeration.objects.all()
        for enum in enums:
            if name == enum.name:
                name_exists = True

        if not name_exists:
            if title != '':
                enum = Enumeration(
                    name = name,
                    title = title,
                    created_by = request.user.username
                )
                enum.save()

                for key in request.POST:
                    if 'item-content' in key:
                        aux_name = request.POST.get(key).strip()
                        while '  ' in aux_name:
                            aux_name = aux_name.replace('  ', ' ')

                        if aux_name.__len__() > 0:
                            item = EnumerationItem(
                                enumeration = enum,
                                name = aux_name,
                                selected = False,
                                order = len(EnumerationItem.objects.filter(enumeration=enum))
                            )
                            item.save()

            else:
                index = len(Enumeration.objects.all())
                enum_name = 'enm_' + str(index)
                message = _(u'You must enter a title for enumeration')
                return render(request, 'enumeration_add.html', {'message': message, 'enum_name': enum_name})
        else:
            index = len(Enumeration.objects.all())
            enum_name = 'enm_' + str(index)
            message = _(u'Name already taken')
            return render(request, 'enumeration_add.html', {'message': message, 'enum_name': enum_name})

        return redirect('enumeration_list')

    else:
        index = len(Enumeration.objects.all())
        enum_name = 'enm_' + str(index)
        return render(request, 'enumeration_add.html', {'enum_name': enum_name})


@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def enumeration_update(request, eid):
    if request.method == 'POST':
        name = request.POST.get('enumeration_name')
        title = request.POST.get('enumeration_title')

        enum = Enumeration.objects.get(id=int(eid))

        enum.name = name
        enum.title = title
        enum.save()

        items = EnumerationItem.objects.filter(enumeration_id=enum.id)
        for i in items:
            i.delete()

        for key in request.POST:
            if 'item-content' in key:
                aux_name = request.POST.get(key).strip()
                while '  ' in aux_name:
                    aux_name = aux_name.replace('  ', ' ')

                if aux_name.__len__() > 0:
                    item = EnumerationItem(
                        enumeration = enum,
                        name = aux_name,
                        selected = False,
                        order = len(EnumerationItem.objects.filter(enumeration=enum))
                    )
                    item.save()

        return redirect('enumeration_list')

    else:
        enum = Enumeration.objects.get(id=int(eid))
        items = EnumerationItem.objects.filter(enumeration_id=enum.id).order_by('name')

        return render(request, 'enumeration_update.html', {'eid': eid, 'enumeration': enum, 'items': items, 'count': len(items) + 1})

@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def create_base_layer(request, pid):
    if request.method == 'POST': 
        global base_layer_process
          
        plg = ProjectLayerGroup.objects.filter(project_id=pid, baselayer_group=True)
        if plg is None or len(plg) == 0:
            return utils.get_exception(400, 'This project does not have base layer')
        id_base_lyr = plg[0].default_baselayer
        base_lyr = Layer.objects.get(id=id_base_lyr)
                                       
        #if tiling_service.exists_base_layer_tiled(pid):
            #    return utils.get_exception(400, 'The base layer already exists')
            
        num_res_levels = None
        try:
            num_res_levels = int(request.POST.get('tiles'))
            format_ = request.POST.get('format')
        except Exception:
            return utils.get_exception(400, 'Wrong number of tiles')
        tilematrixset = request.POST.get('tilematrixset')
        extent = request.POST.get('extent')
        
        if num_res_levels is not None:
            if num_res_levels > 20:
                return utils.get_exception(400, 'The number of resolution levels cannot be greater than 20')
            else:
                tiling_service.tiling_base_layer(base_layer_process, base_lyr, pid, num_res_levels, tilematrixset, format_, extent)
        else:
            return utils.get_exception(400, 'Wrong number of tiles')
                  
    return HttpResponse('{"response": "ok"}', content_type='application/json')
  
@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def base_layer_process_update(request, pid):
    if request.method == 'POST':   
        global base_layer_process
        if str(pid) in base_layer_process:
            return HttpResponse(json.dumps(base_layer_process[str(pid)], indent=4), content_type='application/json')
        else :
            return HttpResponse('{"active" : "false"}', content_type='application/json')
        
@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def stop_base_layer_process(request, pid):
    if request.method == 'POST':   
        if str(pid) in base_layer_process:
            base_layer_process[str(pid)]['stop'] = 'true'
        return HttpResponse('{"response": "ok"}', content_type='application/json')
        
@csrf_exempt
def get_enumeration(request):
    if request.method == 'POST':
        enumerations = []
        enum_names = request.POST.get('enum_names')
        layer_name = request.POST.get('layer_name')
        workspace = request.POST.get('workspace')
        if enum_names.__len__() > 0:
            layer = Layer.objects.get(name=layer_name, datastore__workspace__name=workspace)
            enum_names_array = enum_names.split(',')
            for enum_name in enum_names_array:
                enum = utils.get_enum_entry(layer, enum_name)
                enum_items = utils.get_enum_item_list(layer, enum_name, enum=enum)
                title = enum.title if enum is not None else 'No title defined'
                items = []
                for i in enum_items:
                    item = {}
                    item['name'] = i.name
                    item['selected'] = i.selected
                    items.append(item)

                enumeration = {
                    'title': title,
                    'items': items,
                    'name': enum_name
                }

                enumerations.append(enumeration)

        response = {
            'enumerations': enumerations
        }

        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')


@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def enumeration_delete(request, eid):
    if request.method == 'POST':
        enum = Enumeration.objects.get(id=int(eid))
        enum.delete()
        response = {
            'deleted': True
        }
        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')


@require_GET
@login_required(login_url='/gvsigonline/auth/login_user/')
@superuser_required
def get_geom_tables(request, datastore_id):
    if request.method == 'GET':
        try:
            ds = Datastore.objects.get(pk=datastore_id)
            gs = geographic_servers.get_instance().get_server_by_id(ds.workspace.server.id)
            tables = gs.getGeomColumns(ds)
            data = { 'tables': tables}
            return render(request, 'geom_table_list.html', data)
        except:
            pass
    return HttpResponseBadRequest()

def is_grouped_symbology_request(request, url, aux_response, styles, future_session):
    result = aux_response.result()
    if result.status_code == 200:
        try:
            geojson = json.loads(result.text)

            for i in range(0, len(geojson['features'])):
                properties = geojson['features'][i].get('properties')
                if 'count' in properties and properties.get('count') == 1:
                    style_default = None
                    for style in styles:
                        if style['name'].endswith('_default'):
                            style_default = style['name']

                    #if style_default:
                        #url = url.replace('STYLES=', 'STYLES='+style_default)
                    if 'username' in request.session and 'password' in request.session:
                        if request.session['username'] is not None and request.session['password'] is not None:
                            auth2 = (request.session['username'], request.session['password'])
                            aux_response = future_session.get(url, auth=auth2, verify=False, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT))
        except:
            return aux_response
    return aux_response

@csrf_exempt
def get_feature_info(request):
    if request.method == 'POST':
        results = []
        layers_str = request.POST.get('layers_json')
        layers_json = json.loads(layers_str)

        layers_array = layers_json
        full_features = []

        rs = []
        response = {
        }
        urls = []

        try:
            fut_session = FuturesSession()
            for layer_array in layers_array:
                if layer_array['external']:
                    styles = []
                    if 'styles' in layer_array:
                        styles = layer_array['styles']
                    aux_response = fut_session.get(layer_array['url'], verify=False, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT), proxies=settings.PROXIES)
                    rs.append(is_grouped_symbology_request(request, layer_array['url'], aux_response, styles, fut_session))
                    
                else:
                    #url = request.META['HTTP_ORIGIN'] + layer_array['url']
                    url = core_utils.get_absolute_url(layer_array['url'], request.META)
                    styles = []
                    if 'styles' in layer_array:
                        styles = layer_array['styles']
                    urls.append(url)
                    query_layer = layer_array['query_layer']
                    ws= None
                    if 'workspace' in layer_array:
                        ws = layer_array['workspace']
    
                    print url
    
                    servers = Server.objects.all()
                    auth2 = None
                    url_obj = urlparse(url)
                    for server in servers:
                        server_url_obj = urlparse(server.frontend_url)
                        if url_obj.netloc == server_url_obj.netloc:
                            if query_layer != 'plg_catastro':
                                if 'username' in request.session and 'password' in request.session:
                                    if request.session['username'] is not None and request.session['password'] is not None:
                                        auth2 = (request.session['username'], request.session['password'])
                                        #auth2 = ('admin', 'geoserver')
                                        break
                                        
    
                    aux_response = fut_session.get(url, auth=auth2, verify=False, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT), proxies=settings.PROXIES)
                    rs.append(is_grouped_symbology_request(request, url, aux_response, styles, fut_session))

            i=0
            for layer_array in layers_array:
                #url = request.META['HTTP_ORIGIN'] + layer_array['url']
                url = core_utils.get_absolute_url(layer_array['url'], request.META)
                query_layer = layer_array['query_layer']
                ws= None
                if 'workspace' in layer_array:
                    ws = layer_array['workspace']

                res = rs[i].result()
                if res.status_code == 200:
                    results.append({
                        'url': url,
                        'query_layer': query_layer,
                        'ws': ws,
                        'response': res.text
                        })
                i = i + 1
        except Exception as e:
            print e.message
            response = {
                'error':  str(e.message),
                'urls': urls
            }

        for resultset in results:

            url = resultset['url']
            query_layer = resultset['query_layer']
            ws = resultset['ws']

            features = None
            if query_layer == 'plg_catastro':

                html_content = html.document_fromstring(resultset['response'].decode('utf-8').encode('ascii'))
                for el in html_content.xpath('//body//a'):
                    feat = {}
                    feat['type'] = 'catastro'
                    feat['text'] = el.text
                    feat['href'] = el.xpath('@href')[0]
                    feat['query_layer'] = query_layer
                    features = []
                    features.append(feat)
    
            else:
                if resultset.get('response'):
                    try:
                        geojson = json.loads(resultset.get('response'))
                        if ws:
                            w = Workspace.objects.get(name__exact=ws)
                            layer = Layer.objects.get(name=query_layer, datastore__workspace__name=w.name)

                            for i in range(0, len(geojson['features'])):
                                fid = geojson['features'][i].get('id')
                                resources = []
                                if fid.__len__() > 0:
                                    fid = geojson['features'][i].get('id').split('.')[1]
                                    try:
                                        layer_resources = LayerResource.objects.filter(layer_id=layer.id).filter(feature=fid)
                                        for lr in layer_resources:
                                            (type, rsurl) = utils.get_resource_type(lr)
                                            resource = {
                                                'type': type,
                                                'url': rsurl,
                                                'name': lr.path.split('/')[-1]
                                            }
                                            resources.append(resource)
                                    except Exception as e:
                                        print e.message

                                else:
                                    geojson['features'][i]['type']= 'raster'
                                geojson['features'][i]['resources'] = resources
                                geojson['features'][i]['all_correct'] = resultset['response']
                                geojson['features'][i]['feature'] = fid
                                geojson['features'][i]['layer_name'] = resultset['query_layer']

                            features = geojson['features']
                        else:
                            for i in range(0, len(geojson['features'])):
                                fid = geojson['features'][i].get('id')
                                geojson['features'][i]['resources'] = []
                                geojson['features'][i]['all_correct'] = resultset['response']
                                geojson['features'][i]['feature'] = fid
                                geojson['features'][i]['layer_name'] = resultset['query_layer']

                            features = geojson['features']
                            
                    except Exception as e:
                        print e.message
                        feat = {}
                        feat['type'] = 'plain_or_html'
                        feat['text'] = resultset.get('response')
                        feat['query_layer'] = query_layer
                        features = []
                        features.append(feat)
                        
            if features:
                full_features = full_features + features

            response = {
                'features': full_features
            }

        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')

@csrf_exempt
def get_unique_values(request):
    if request.method == 'POST':
        layer_name = request.POST.get('layer_name')
        layer_ws = request.POST.get('layer_ws')
        field = request.POST.get('field')

        workspace = Workspace.objects.get(name__exact=layer_ws)
        layer = Layer.objects.get(name=layer_name, datastore__workspace__name=workspace.name)

        connection = ast.literal_eval(layer.datastore.connection_params)

        host = connection.get('host')
        port = connection.get('port')
        schema = connection.get('schema')
        database = connection.get('database')
        user = connection.get('user')
        password = connection.get('passwd')

        unique_fields = utils.get_distinct_query(host, port, schema, database, user, password, layer.name, field)

        return HttpResponse(json.dumps({'values': unique_fields}, indent=4), content_type='application/json')


def is_numeric_type(type):
    if type == 'smallint' or type == 'integer' or type == 'bigint' or type == 'decimal' or type == 'numeric' or type == 'real' or type == 'double precision' or type == 'smallserial' or type == 'serial' or type == 'bigserial':
        return True;
    return False;


def is_string_type(type):
    if type.startswith('character varying') or type.startswith('varchar') or type.startswith('character') or type.startswith('char') or type.startswith('text'):
        return True;
    return False;

@csrf_exempt
def get_datatable_data(request):
    if request.method == 'POST':
        layer_name = request.POST.get('layer_name')
        workspace = request.POST.get('workspace')
        wfs_url = request.POST.get('wfs_url')
        property_name = request.POST.get('property_name')
        properties_with_type = request.POST.get('properties_with_type')
        start_index = request.POST.get('start')
        max_features = request.POST.get('length')
        draw = request.POST.get('draw')
        search_value = request.POST.get('search[value]')
        cql_filter = request.POST.get('cql_filter')

        values = None
        recordsTotal = 0
        recordsFiltered = 0

        encoded_property_name = property_name.encode('utf-8')
         
        layer = Layer.objects.get(name=layer_name, datastore__workspace__name=workspace)
        gs = geographic_servers.get_instance().get_server_by_id(layer.datastore.workspace.server.id)
        definition = gs.getFeaturetype(layer.datastore.workspace, layer.datastore, layer.name, layer.title)
        aux_encoded_property_name = ' '
        sortby_field = None
        if 'featureType' in definition and 'attributes' in definition['featureType'] and 'attribute' in definition['featureType']['attributes']:
            attributes = definition['featureType']['attributes']['attribute']
            if isinstance(attributes, list):
                for attribute in attributes:
                    aux_encoded_property_name += attribute['name'] + ' '
                    if not sortby_field and not 'jts.geom' in attribute['binding']:
                        sortby_field = attribute['name']
            else:
                attribute = attributes
                aux_encoded_property_name += attribute['name'] + ' '
                if not sortby_field and not 'jts.geom' in attribute['binding']:
                    sortby_field = attribute['name']

        num_fields = encoded_property_name.split(',').__len__()
        found = -1
        idx = 0
        while found == -1 and num_fields - 1 >= idx:
            if not sortby_field:
                sortby_field = encoded_property_name.split(',')[idx]
            found = aux_encoded_property_name.find(' ' + sortby_field + ' ')
            idx = idx + 1
        encoded_property_name = aux_encoded_property_name.strip().replace(' ',',')

        params = json.loads(layer.datastore.connection_params)
        if not sortby_field:
            sortby_field = encoded_property_name.split(',')[0]

        if sortby_field == 'wkb_geometry' and num_fields > 1:
            sortby_field = encoded_property_name.split(',')[1]

        '''
        i = Introspect(database=params['database'], host=params['host'], port=params['port'], user=params['user'], password=params['passwd'])
        pk_defs = i.get_pk_columns(layer.name, params.get('schema', 'public'))
        i.close()
        
        if len(pk_defs) >= 1:
            sortby_field = str(pk_defs[0])
        '''
        
        #wfs_url = request.META['HTTP_ORIGIN'] + wfs_url
        wfs_url = core_utils.get_absolute_url(wfs_url, request.META)
        try:
            if search_value == '':
                values = {
                    'SERVICE': 'WFS',
                    'VERSION': '1.1.0',
                    'REQUEST': 'GetFeature',
                    'TYPENAME': layer_name,
                    'OUTPUTFORMAT': 'application/json',
                    'MAXFEATURES': max_features,
                    'STARTINDEX': start_index,
                    'PROPERTYNAME': encoded_property_name
                }

                if sortby_field != 'wkb_geometry':
                    values['SORTBY'] = sortby_field

                if cql_filter != '':
                    values['cql_filter'] = cql_filter.encode('utf-8')

                recordsTotal = gs.getFeatureCount(request, wfs_url, layer_name, None)
                recordsFiltered = gs.getFeatureCount(request, wfs_url, layer_name, cql_filter)
                #recordsFiltered = recordsTotal

            else:
                properties = properties_with_type.split(',')
                encoded_value = search_value.encode('ascii', 'replace')

                geoserver_fields = encoded_property_name.split(',')
                raw_search_cql = '('
                for p in properties:
                    if p.split('|')[0] != 'id' and p.split('|')[0] in geoserver_fields:
                        if is_string_type(p.split('|')[1]):
                            raw_search_cql += p.split('|')[0] + " ILIKE '%" + encoded_value.replace('?', '_') +"%'"
                            raw_search_cql += ' OR '

                        elif is_numeric_type(p.split('|')[1]):
                            if search_value.isdigit():
                                raw_search_cql += p.split('|')[0] + ' = ' + search_value
                                raw_search_cql += ' OR '

                if raw_search_cql.endswith(' OR '):
                    raw_search_cql = raw_search_cql[:-4]

                raw_search_cql += ')'
                if raw_search_cql == '()':
                    raw_search_cql = ''

                values = {
                    'SERVICE': 'WFS',
                    'VERSION': '1.1.0',
                    'REQUEST': 'GetFeature',
                    'TYPENAME': layer_name,
                    'OUTPUTFORMAT': 'application/json',
                    'MAXFEATURES': max_features,
                    'STARTINDEX': start_index,
                    'PROPERTYNAME': encoded_property_name
                }
                if sortby_field != 'wkb_geometry':
                    values['SORTBY'] = sortby_field

                if cql_filter == '':
                    values['cql_filter'] = raw_search_cql
                else:
                    values['cql_filter'] = cql_filter.encode('utf-8') + ' AND ' + raw_search_cql
                recordsTotal = gs.getFeatureCount(request, wfs_url, layer_name, None)
                recordsFiltered = gs.getFeatureCount(request, wfs_url, layer_name, cql_filter)

            params = urllib.urlencode(values)
            req = requests.Session()
            if 'username' in request.session and 'password' in request.session:
                if request.session['username'] is not None and request.session['password'] is not None:
                    req.auth = (request.session['username'], request.session['password'])
                    #req.auth = ('admin', 'geoserver')

            print wfs_url + "?" + params
            response = req.post(wfs_url, data=values, verify=False, proxies=settings.PROXIES)
            jsonString = response.text
            geojson = json.loads(jsonString)

            data = []
            for f in geojson['features']:
                row = {}
                for p in f['properties']:
                    row[p] = f['properties'][p]
                row['featureid'] = f['id']
                data.append(row)

            response = {
                'draw': int(draw),
                'recordsTotal': recordsTotal,
                'recordsFiltered': recordsFiltered,
                'data': data
            }

        except Exception as e:
            logger.exception("Error building feature info")
            response = {
                'draw': 0,
                'recordsTotal': 0,
                'recordsFiltered': 0,
                'data': []
            }
            pass

        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')
    
    
@csrf_exempt
def get_feature_wfs(request):
    if request.method == 'POST':
        layer_name = request.POST.get('layer_name')
        workspace = request.POST.get('workspace')
        wfs_url = request.POST.get('wfs_url')
        field = request.POST.get('field')
        field_type = request.POST.get('field_type')
        value = request.POST.get('value')
        operator = request.POST.get('operator')

        try:
            layer = Layer.objects.get(name=layer_name, datastore__workspace__name=workspace)
            if wfs_url == None:
                wfs_url = layer.datastore.workspace.wfs_endpoint
            else:
                wfs_url = core_utils.get_absolute_url(wfs_url, request.META)
              
            cql_filter = None  
            if operator == 'equal_to':
                if field_type == 'character varying':
                    cql_filter = field + "='" + value + "'"
                else:
                    cql_filter = field + "=" + value
            
            elif operator == 'smaller_than':
                cql_filter = field + "<" + value
                
            elif operator == 'greater_than':
                cql_filter = field + ">" + value
            
            data = {
                "SERVICE": "WFS",
                "VERSION": "1.1.0",
                "REQUEST": "GetFeature",
                "TYPENAME": layer_name,
                "OUTPUTFORMAT": "application/json",
                "MAXFEATURES": 500,
                "CQL_FILTER": cql_filter.encode('utf-8')
            }
            
            params = urllib.urlencode(data)
            req = requests.Session()
            if 'username' in request.session and 'password' in request.session:
                if request.session['username'] is not None and request.session['password'] is not None:
                    req.auth = (request.session['username'], request.session['password'])
                    #req.auth = ('admin', 'geoserver')

            print wfs_url + "?" + params
            response = req.post(wfs_url, data=data, verify=False, proxies=settings.PROXIES)
            jsonString = response.text
            geojson = json.loads(jsonString)

            data = []
            for f in geojson['features']:
                row = {}
                for p in f['properties']:
                    row[p] = f['properties'][p]
                row['featureid'] = f['id']
                data.append(row)

            response = {
                'data': data
            }

        except Exception as e:
            logger.exception("Error getting WFS feature")
            response = {
                'data': []
            }
            pass

        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')


@login_required(login_url='/gvsigonline/auth/login_user/')
def add_layer_lock(request):
    layer_name = None
    try:
        ws_name = request.POST['workspace']
        layer_name = request.POST['layer']

        if ":" in layer_name:
            layer_name = layer_name.split(":")[1]
        qualified_layer_name = ws_name + ":" + layer_name
        locks_utils.add_layer_lock(qualified_layer_name, request.user)
        return HttpResponse('{"response": "ok"}', content_type='application/json')
    except Exception as e:
        return HttpResponseNotFound('<h1>Layer is locked: {0}</h1>'.format(layer_name))


@login_required(login_url='/gvsigonline/auth/login_user/')
def remove_layer_lock(request):
    try:
        ws_name = request.POST['workspace']
        layer_name = request.POST['layer']
        if ":" in layer_name:
            layer_name = layer_name.split(":")[1]
        layer = Layer.objects.get(name=layer_name, datastore__workspace__name=ws_name)
        locks_utils.remove_layer_lock(layer, request.user, check_writable=True)
        return HttpResponse('{"response": "ok"}', content_type='application/json')
    except Exception as e:
        return HttpResponseNotFound('<h1>Layer not locked: {0}</h1>'.format(layer.id))

@login_required(login_url='/gvsigonline/auth/login_user/')
@require_safe
@staff_required
def lock_list(request):

    lock_list = None
    if request.user.is_superuser:
        lock_list = LayerLock.objects.all()
    else:
        lock_list = LayerLock.objects.filter(created_by__exact=request.user.username)

    response = {
        'locks': lock_list
    }
    return render(request, 'lock_list.html', response)

@login_required(login_url='/gvsigonline/auth/login_user/')
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def unlock_layer(request, lock_id):
    lock = LayerLock.objects.get(id=int(lock_id))
    lock.delete()
    return redirect('lock_list')

@csrf_exempt
def get_feature_resources(request):
    if request.method == 'POST':
        query_layer = request.POST.get('query_layer')
        workspace = request.POST.get('workspace')
        fid = request.POST.get('fid')
        try:
            layer = Layer.objects.get(name=query_layer, datastore__workspace__name=workspace)
            layer_resources = LayerResource.objects.filter(layer_id=layer.id).filter(feature=int(fid))
            resources = []
            for lr in layer_resources:
                url = settings.MEDIA_URL
                if settings.BASE_URL in url:
                    url = url.replace(settings.BASE_URL, '')
                    
                type = None
                if lr.type == LayerResource.EXTERNAL_IMAGE:
                    type = 'image'
                    url = os.path.join(url, lr.path)
                    name = lr.path.split('/')[-1]
                elif lr.type == LayerResource.EXTERNAL_PDF:
                    type = 'pdf'
                    url = os.path.join(url, lr.path)
                    name = lr.path.split('/')[-1]
                elif lr.type == LayerResource.EXTERNAL_DOC:
                    type = 'doc'
                    url = os.path.join(url, lr.path)
                    name = lr.path.split('/')[-1]
                elif lr.type == LayerResource.EXTERNAL_FILE:
                    type = 'file'
                    url = os.path.join(url, lr.path)
                    name = lr.path.split('/')[-1]
                elif lr.type == LayerResource.EXTERNAL_VIDEO:
                    type = 'video'
                    url = os.path.join(url, lr.path)
                    name = lr.path.split('/')[-1]
                elif lr.type == LayerResource.EXTERNAL_ALFRESCO_DIR:
                    type = 'alfresco_dir'
                    url = lr.path

                resource = {
                    'type': type,
                    'url': url,
                    'name': name,
                    'rid': lr.id
                }
                resources.append(resource)


        except Exception as e:
            print e.message

        response = {
            'resources': resources
        }

        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')

@login_required(login_url='/gvsigonline/auth/login_user/')
@csrf_exempt
def upload_resources(request):
    if request.method == 'POST':
        ws_name = request.POST.get('workspace')
        layer_name = request.POST.get('layer_name')
        fid = request.POST.get('fid')
        if ":" in layer_name:
            layer_name = layer_name.split(":")[1]
        layer = Layer.objects.get(name=layer_name, datastore__workspace__name=ws_name)
        if 'resource' in request.FILES:
            type = None
            resource = request.FILES['resource']
            if 'image/' in resource.content_type:
                type = LayerResource.EXTERNAL_IMAGE
            elif resource.content_type == 'application/pdf':
                type = LayerResource.EXTERNAL_PDF
            elif 'video/' in resource.content_type:
                type = LayerResource.EXTERNAL_VIDEO
            else:
                type = LayerResource.EXTERNAL_FILE

            (saved, path) = resource_manager.save_resource(resource, type)
            if saved:
                res = LayerResource()
                res.feature = int(fid)
                res.layer = layer
                res.path = path
                res.title = ''
                res.type = type
                res.created = timezone.now()
                res.save()
                response = {'success': True}

            else:
                response = {'success': False}

    return HttpResponse(json.dumps(response, indent=4), content_type='application/json')

def get_feat_version(resource, featid):
    try:
        params = json.loads(resource.layer.datastore.connection_params)
        i = Introspect(database=params['database'], host=params['host'], port=params['port'], user=params['user'], password=params['passwd'])
        pks = i.get_pk_columns(resource.layer.name, resource.layer.datastore.name)
        if(pks and len(pks) > 0):
            rows = i.custom_query("SELECT " + settings.VERSION_FIELD + ", " + settings.DATE_FIELD + " FROM "+ resource.layer.datastore.name + "." + resource.layer.name + " WHERE " + pks[0] + "=" + str(featid))
            i.close()
            if(rows and len(rows) > 0): 
                return rows[0][0]
    except Exception:
        return None

@login_required(login_url='/gvsigonline/auth/login_user/')
@csrf_exempt
def delete_resource(request):
    if request.method == 'POST':
        rid = request.POST.get('rid')
        try:
            resource = LayerResource.objects.get(id=int(rid))
            featid = resource.feature
            lyrid = resource.layer.id
            resource.delete()
            historical_url, historical_filepath = resource_manager.delete_resource(resource)
            
            version = get_feat_version(resource, featid)
            response = {'deleted': True, 'featid': featid, 'lyrid': lyrid, 'path': historical_filepath, 'url': historical_url, 'feat_version': version}

        except Exception:
            response = {'deleted': False}
            pass

        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')

@login_required(login_url='/gvsigonline/auth/login_user/')
@csrf_exempt
def delete_resources(request):
    if request.method == 'POST':
        query_layer = request.POST.get('query_layer')
        workspace = request.POST.get('workspace')
        fid = request.POST.get('fid')
        try:
            layer = Layer.objects.get(name=query_layer, datastore__workspace__name=workspace)
            layer_resources = LayerResource.objects.filter(layer_id=layer.id).filter(feature=int(fid))
            featidlist = []
            lyridlist = []
            pathlist = []
            urllist = []
            for resource in layer_resources:
                featidlist.append(resource.feature)
                lyridlist.append(resource.layer.id)
                historical_url, historical_filepath = resource_manager.delete_resource(resource)
                pathlist.append(historical_filepath)
                urllist.append(historical_url)
                resource.delete()
            response = {'deleted': True, 'featidlist': featidlist, 'lyridlist': lyridlist, 'pathlist': pathlist, 'urllist':urllist}

        except Exception as e:
            print e.message
            response = {'deleted': False}
            pass

        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')


@csrf_exempt
def describeLayerConfig(request):
    if request.method == 'POST':
        lyr = request.POST.get('layer')
        workspace = request.POST.get('workspace')
        try:
            l = Layer.objects.get(name=lyr, datastore__workspace__name=workspace)
            read_roles = utils.get_read_roles(l)
            write_roles = utils.get_write_roles(l)

            if len(read_roles) <= 0:
                layer = {}
                layer['name'] = l.name
                layer['title'] = l.title
                layer['abstract'] = l.abstract
                layer['visible'] = l.visible
                layer['queryable'] = l.queryable
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
                layer['cached'] = l.cached
                layer['single_image'] = l.single_image
                layer['read_roles'] = read_roles
                layer['write_roles'] = write_roles

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
                gs = geographic_servers.get_instance().get_server_by_id(workspace.server.id)
                if datastore.type == 'e_WMS':
                    (ds_type, layer_info) = gs.getResourceInfo(workspace.name, datastore, l.name, "json")
                    defaultCrs = 'EPSG:4326'
                else:
                    (ds_type, layer_info) = gs.getResourceInfo(workspace.name, datastore, l.name, "json")
                    defaultCrs = layer_info[ds_type]['srs']

                if defaultCrs.split(':')[1] in core_utils.get_supported_crs():
                    epsg = core_utils.get_supported_crs()[defaultCrs.split(':')[1]]
                    layer['crs'] = {
                        'crs': defaultCrs,
                        'units': epsg['units']
                    }

                layer['wms_url'] = core_utils.get_wms_url(workspace)
                layer['wfs_url'] = core_utils.get_wfs_url(workspace)
                layer['namespace'] = workspace.uri
                layer['workspace'] = workspace.name
                layer['metadata'] = core_utils.get_catalog_url(request, l)
                if l.cached:
                    layer['cache_url'] = core_utils.get_cache_url(workspace)
                else:
                    layer['cache_url'] = core_utils.get_wms_url(workspace)



            response = {'layer': layer}


        except Exception as e:
            print e.message
            response = {'layer': {}}
            pass

        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')
    
@csrf_exempt
def describeFeatureType(request):
    if request.method == 'POST':
        lyr = request.POST.get('layer')
        workspace = request.POST.get('workspace')
        skip_pks = request.POST.get('skip_pks')
        feat_type = _describeFeatureType(lyr, workspace, skip_pks)
        return HttpResponse(json.dumps(feat_type, indent=4), content_type='application/json')

def _describeFeatureType(lyr, workspace, skip_pks):
    try:
        layer = Layer.objects.get(name=lyr, datastore__workspace__name=workspace)
        params = json.loads(layer.datastore.connection_params)
        host = params['host']
        port = params['port']
        dbname = params['database']
        user = params['user']
        passwd = params['passwd']
        schema = params.get('schema', 'public')


        i = Introspect(database=dbname, host=host, port=port, user=user, password=passwd)
        layer_defs = i.get_fields_info(layer.name, schema)
        layer_mv_defs = []
        if layer_defs.__len__() == 0:
            layer_mv_defs = i.get_fields_mv_info(layer.name, schema)
        layer_defs = layer_defs + layer_mv_defs
        geom_defs = i.get_geometry_columns_info(layer.name, schema)
        pk_defs = i.get_pk_columns(layer.name, schema)
        i.close()
        
        for layer_def in layer_defs:
            for geom_def in geom_defs:
                if layer_def['name'] == geom_def[2]:
                    layer_def['type'] = geom_def[5]
                    layer_def['length'] = geom_def[4]
        for layer_def in layer_defs:
            for pk_def in pk_defs:
                if layer_def['name'] == pk_def:
                    layer_defs.remove(layer_def)
            enum, multiple = utils.is_field_enumerated(layer, layer_def['name'])
            if enum:
                if multiple:
                    layer_def['type'] = 'multiple_enumeration'
                else:
                    layer_def['type'] = 'enumeration'

        if skip_pks == 'true':        
            gs = geographic_servers.get_instance().get_server_by_id(layer.datastore.workspace.server.id)
            definition = gs.getFeaturetype(layer.datastore.workspace, layer.datastore, layer.name, layer.title)
            aux_encoded_property_name = ''
            if 'featureType' in definition and 'attributes' in definition['featureType'] and 'attribute' in definition['featureType']['attributes']:
                attributes = definition['featureType']['attributes']['attribute']
                if isinstance(attributes, list):
                    for attribute in attributes:
                        aux_encoded_property_name += attribute['name'] + ' '
                else:
                    attribute = attributes
                    aux_encoded_property_name += attribute['name'] + ' '

            names = aux_encoded_property_name.split(' ');
            layer_defs_aux = []
            for layer_def in layer_defs:
                if layer_def.get('name') in names:
                    layer_defs_aux.append(layer_def)

            layer_defs = layer_defs_aux

        response = {'fields': layer_defs}


    except Exception as e:
        print e.message
        response = {'fields': [], 'error': e.message}
        pass
    
    return response

def describe_feature_type(lyr, workspace):
    try:
        layer = Layer.objects.get(name=lyr, datastore__workspace__name=workspace)
        params = json.loads(layer.datastore.connection_params)
        schema = params.get('schema', 'public')

        i = Introspect(database=params['database'], host=params['host'], port=params['port'], user=params['user'], password=params['passwd'])
        layer_defs = i.get_fields_info(layer.name, schema)
        layer_mv_defs = []
        if layer_defs.__len__() == 0:
            layer_mv_defs = i.get_fields_mv_info(layer.name, schema)
        layer_defs = layer_defs + layer_mv_defs
        geom_defs = i.get_geometry_columns_info(layer.name, schema)
        i.close()
        
        for layer_def in layer_defs:
            for geom_def in geom_defs:
                if layer_def['name'] == geom_def[2]:
                    layer_def['type'] = geom_def[5]
                    layer_def['length'] = geom_def[4]
        for layer_def in layer_defs:
            enum, multiple = utils.is_field_enumerated(layer, layer_def['name'])
            if enum:
                if multiple:
                    layer_def['type'] = 'multiple_enumeration'
                else:
                    layer_def['type'] = 'enumeration'

        response = {'fields': layer_defs}


    except Exception as e:
        print e.message
        response = {'fields': [], 'error': e.message}
        pass
    
    return response

@csrf_exempt
def describeFeatureTypeWithPk(request):
    if request.method == 'POST':
        lyr = request.POST.get('layer')
        workspace = request.POST.get('workspace')
        try:
            layer = Layer.objects.get(name=lyr, datastore__workspace__name=workspace)
            params = json.loads(layer.datastore.connection_params)
            host = params['host']
            port = params['port']
            dbname = params['database']
            user = params['user']
            passwd = params['passwd']
            schema = params.get('schema', 'public')
            i = Introspect(database=dbname, host=host, port=port, user=user, password=passwd)
            layer_defs = i.get_fields_info(layer.name, schema)
            geom_defs = i.get_geometry_columns_info(layer.name, schema)
            pk_defs = i.get_pk_columns(layer.name, schema)
            i.close()
            
            for layer_def in layer_defs:
                for geom_def in geom_defs:
                    if layer_def['name'] == geom_def[2]:
                        layer_def['type'] = geom_def[5]
                        layer_def['length'] = geom_def[4]

            response = {'fields': layer_defs}


        except Exception as e:
            print e.message
            response = {'fields': []}
            pass

        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')



@login_required(login_url='/gvsigonline/auth/login_user/')
@require_safe
@staff_required
def external_layer_list(request):
    if request.user.is_superuser:
        external_layer_list = Layer.objects.filter(external=True)

        response = {
            'external_layers': external_layer_list
        }
        return render(request, 'external_layer_list.html', response)
    else:
        external_layer_list = Layer.objects.filter(external=True).filter(created_by__exact=request.user.username)
        response = {
            'external_layers': external_layer_list
        }
        return render(request, 'external_layer_list.html', response)

@login_required(login_url='/gvsigonline/auth/login_user/')
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def external_layer_add(request):
    if request.method == 'POST':
        form = ExternalLayerForm(request.POST)
        
        try:
            is_visible = False
            if 'visible' in request.POST:
                is_visible = True
    
            cached = False
            if 'cached' in request.POST:
                cached = True
                
            detailed_info_enabled = False
            detailed_info_button_title = request.POST.get('detailed_info_button_title')
            detailed_info_html = request.POST.get('detailed_info_html')
            if 'detailed_info_enabled' in request.POST:
                detailed_info_enabled = True
                detailed_info_button_title = request.POST.get('detailed_info_button_title')
                detailed_info_html = request.POST.get('detailed_info_html')
                
            crs_list = []
            for key in request.POST:
                if 'crs_' in key:
                    crs_list.append({
                        'key': key.split('_')[1],
                        'value': request.POST[key]
                    })
            
            layer_group = LayerGroup.objects.get(id=int(request.POST.get('layer_group')))
            server = Server.objects.get(id=layer_group.server_id)
                
            external_layer = Layer()
            external_layer.external = True
            external_layer.title = request.POST.get('title')
            external_layer.layer_group_id = layer_group.id
            external_layer.type = request.POST.get('type')
            external_layer.visible = is_visible
            external_layer.queryable = False
            external_layer.cached = cached
            external_layer.single_image = False
            external_layer.time_enabled = False
            external_layer.detailed_info_enabled = detailed_info_enabled
            external_layer.detailed_info_button_title = detailed_info_button_title
            external_layer.detailed_info_html = detailed_info_html
            external_layer.created_by = request.user.username
            external_layer.timeout = request.POST.get('timeout')
            
            params = {}
            if external_layer.type == 'WMTS' or external_layer.type == 'WMS':
                params['version'] = request.POST.get('version')
                params['url'] = request.POST.get('url')
                params['cache_url'] = server.getCacheEndpoint()
                params['layers'] = request.POST.get('layers')
                params['format'] = request.POST.get('format')
                params['infoformat'] = request.POST.get('infoformat')
                
            if external_layer.type == 'WMTS':
                params['matrixset'] = request.POST.get('matrixset')
                params['capabilities'] = request.POST.get('capabilities')

            if external_layer.type == 'Bing':
                params['key'] = request.POST.get('key')
                params['layers'] = request.POST.get('layers')

            if external_layer.type == 'XYZ' or external_layer.type == 'OSM':
                params['url'] = request.POST.get('url')
                params['key'] = request.POST.get('key')

            external_layer.external_params = json.dumps(params)

            external_layer.save()

            external_layer.name = 'externallayer_' + str(external_layer.id)
            external_layer.save()
            
            if external_layer.cached:
                if external_layer.type == 'WMS':
                    master_node = geographic_servers.get_instance().get_master_node(server.id)
                    geowebcache.get_instance().add_layer(None, external_layer, server, master_node.getUrl(), crs_list)
                    geographic_servers.get_instance().get_server_by_id(server.id).reload_nodes()

            return redirect('external_layer_list')

        except Exception as e:
            logger.exception("Error creating external layer")
            try:
                msg = e.get_message()
            except:
                msg = _("Error: ExternalLayer could not be published")
            form.add_error(None, msg)

    else:
        form = ExternalLayerForm()

    return render(request, 'external_layer_add.html', {'form': form, 'bing_layers': BING_LAYERS})

@login_required(login_url='/gvsigonline/auth/login_user/')
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def external_layer_update(request, external_layer_id):
    external_layer = Layer.objects.get(id=external_layer_id)
    layer_group = LayerGroup.objects.get(id=external_layer.layer_group.id)
    server = Server.objects.get(id=layer_group.server_id)
    if request.method == 'POST':
        form = ExternalLayerForm(request.POST)
        try:
            is_visible = False
            if 'visible' in request.POST:
                is_visible = True
    
            cached = False
            if 'cached' in request.POST:
                cached = True
                
            detailed_info_enabled = False
            detailed_info_button_title = request.POST.get('detailed_info_button_title')
            detailed_info_html = request.POST.get('detailed_info_html')
            if 'detailed_info_enabled' in request.POST:
                detailed_info_enabled = True
                detailed_info_button_title = request.POST.get('detailed_info_button_title')
                detailed_info_html = request.POST.get('detailed_info_html')
                
            crs_list = []
            for key in request.POST:
                if 'crs_' in key:
                    crs_list.append({
                        'key': key.split('_')[1],
                        'value': request.POST[key]
                    })
            
            master_node = geographic_servers.get_instance().get_master_node(server.id)   
            if external_layer.cached and not cached:
                geowebcache.get_instance().delete_layer(None, external_layer, server, master_node.getUrl())
                geographic_servers.get_instance().get_server_by_id(server.id).reload_nodes()
                
            if not external_layer.cached and cached:
                if external_layer.type == 'WMS':
                    geowebcache.get_instance().add_layer(None, external_layer, server, master_node.getUrl(), crs_list)
                    geographic_servers.get_instance().get_server_by_id(server.id).reload_nodes()
                
            external_layer.title = request.POST.get('title')
            external_layer.type = request.POST.get('type')
            external_layer.layer_group_id = request.POST.get('layer_group')
            external_layer.visible = is_visible
            external_layer.cached = cached
            external_layer.detailed_info_enabled = detailed_info_enabled
            external_layer.detailed_info_button_title = detailed_info_button_title
            external_layer.detailed_info_html = detailed_info_html
            external_layer.timeout = request.POST.get('timeout')
            params = {}

            if external_layer.type == 'WMTS' or external_layer.type == 'WMS':
                params['version'] = request.POST.get('version')
                params['url'] = request.POST.get('url')
                params['cache_url'] = server.getCacheEndpoint()
                params['layers'] = request.POST.get('layers')
                params['format'] = request.POST.get('format')
                params['infoformat'] = request.POST.get('infoformat')
                
            if external_layer.type == 'WMTS':
                params['matrixset'] = request.POST.get('matrixset')
                params['capabilities'] = request.POST.get('capabilities')

            if external_layer.type == 'Bing':
                params['key'] = request.POST.get('key')
                params['layers'] = request.POST.get('layers')

            if external_layer.type == 'XYZ' or external_layer.type == 'OSM':
                params['url'] = request.POST.get('url')
                params['key'] = request.POST.get('key')


            external_layer.external_params = json.dumps(params)
            external_layer.save()
            return redirect('external_layer_list')


        except Exception as e:
            try:
                msg = e.get_message()
            except:
                msg = _("Error: externallayer could not be published")
            form.add_error(None, msg)

    else:
        form = ExternalLayerForm(instance=external_layer)

        if external_layer.external_params:
            params = json.loads(external_layer.external_params)
            for key in params:
                form.initial[key] = params[key]
                
        html = True
        if external_layer.detailed_info_html == None or external_layer.detailed_info_html == '' or external_layer.detailed_info_html == 'null':
            html = False


        response= {
            'form': form,
            'external_layer': external_layer,
            'bing_layers': BING_LAYERS,
            'html': html
        }

    return render(request, 'external_layer_update.html', response)



@login_required(login_url='/gvsigonline/auth/login_user/')
@require_POST
@staff_required
def external_layer_delete(request, external_layer_id):
    try:
        external_layer = Layer.objects.get(id=external_layer_id)
        server = Server.objects.get(id=external_layer.layer_group.server_id)
        master_node = geographic_servers.get_instance().get_master_node(server.id)
        if external_layer.cached:
            if external_layer.type == 'WMS':  
                geowebcache.get_instance().delete_layer(None, external_layer, server, master_node.getUrl())
            geographic_servers.get_instance().get_server_by_id(server.id).reload_nodes()
            
        external_layer.delete()
                
    except Exception as e:
        return HttpResponse('Error deleting external_layer: ' + str(e), status=500)

    return redirect('external_layer_list')

def ows_get_capabilities(url, service, version, layer, remove_extra_params=True):
    if remove_extra_params:
        # remove any param in the query string
        urlObj = urlparse(url)
        url = urlObj.scheme + u'://' + urlObj.netloc + urlObj.path

    layers = []
    formats = []
    infoformats = []
    styles = []
    matrixsets = []
    capabilities = None
    title = ''
    crs_list = None
    
    auth = Authentication(verify=False)
    if service == 'WMS':
        if not version:
            version = WMS_MAX_VERSION
        try:
            print 'Add base layer: ' + url+ ', version: ' + version
            wms = WebMapService(url, version=version, auth=auth)

            print 'Add base layer type ' + wms.identification.type
            title = wms.identification.title
            matrixsets = []
            layers = list(wms.contents)
            #all_formats = wms.getOperationByName('GetMap').formatOptions
            #for f in all_formats:
            #    if f == 'image/png' or f == 'image/jpeg':
            #        formats.append(f)
            formats.append('image/jpeg')
            formats.append('image/png')
            try:
                all_infoformats = wms.getOperationByName('GetFeatureInfo').formatOptions
                for i_format in all_infoformats:
                    if i_format == 'text/plain' or i_format == 'text/html' or i_format == 'application/json' or i_format == 'application/geojson':
                        infoformats.append(i_format)
            except Exception:
                pass
            
            lyr = wms.contents.get(layer)
            if not lyr:
                for capabLyrName in wms.contents:
                    # try discarding the workspace
                    layer_parts = capabLyrName.split(":")
                    if len(layer_parts) > 1 and layer_parts[1] == layer:
                        lyr = wms.contents.get(capabLyrName)
                        break
            if lyr:
                for style_name in lyr.styles:
                    style = lyr.styles[style_name]
                    title = style['title'] if style['title'] else style_name
                    style_def = {'name': style_name, 'title':title}
                    if 'legend' in style:
                        style_def['custom_legend_url'] = style['legend']
                    styles.append(style_def)
                crs_list = lyr.crs_list

        except Exception as e:
            print 'Add base layer ERROR: ' + str(e.message)
            data = {'response': '500',
             'message':  str(e.message)}
            return data

    if service == 'WMTS':
        try:
            if not version:
                version = WMTS_MAX_VERSION
            wmts = WebMapTileService(url, version=version, auth=auth)
            title = wmts.identification.title
            capabilities = wmts.getServiceXML()

            layers = list(wmts.contents)
            if (not layer) and layers.__len__() > 0:
                layer = layers[0]
            else:
                lyr = wmts.contents.get(layer)
                #for lyr_format in lyr.formats:
                #    if not lyr_format in formats:
                #        if lyr_format == 'image/png' or lyr_format == 'image/jpeg':
                #            formats.append(lyr_format)
                formats.append('image/jpeg')
                formats.append('image/png')
                for infoformat in lyr.infoformats:
                    if not infoformat in infoformats:
                        if infoformat == 'text/plain' or infoformat == 'text/html' or infoformat == 'application/json' or infoformat == 'application/geojson':
                            infoformats.append(infoformat)
                for matrixset in lyr.tilematrixsets:
                    if not matrixset in matrixsets:
                        matrixsets.append(matrixset)
                    
                for style_name in lyr.styles:
                    style = lyr.styles[style_name]
                    title = style_name
                    if 'title' in style:
                        title = style['title']
                    style_def = {'name': style_name, 'title':title}
                    if 'legend' in style:
                        style_def['custom_legend_url'] = style['legend']
                    styles.append(style_def)
                for lyr_style in wmts.contents.get(layer).styles:
                    styles.append(lyr_style)
                
        except Exception as e:
            data = {'response': '500',
             'message':  str(e.message)}
            return data

    data = {
        'response': '200',
        'version': version,
        'layers': layers,
        'formats': formats,
        'infoformats': infoformats,
        'styles': styles,
        'title': title,
        'matrixsets': matrixsets,
        'capabilities': capabilities,
        'crs_list': crs_list
    }

    return data

@require_GET
def get_capabilities(request):
    url = request.GET.get('url')
    service = request.GET.get('type')
    version = request.GET.get('version')
    layer = request.GET.get('layer')
    
    data = ows_get_capabilities(url, service, version, layer)
    return HttpResponse(json.dumps(data, indent=4), content_type='application/json')

@login_required(login_url='/gvsigonline/auth/login_user/')
@require_POST
@staff_required
def get_capabilities_from_url(request):
    url = request.POST.get('url')
    service = request.POST.get('type')
    version = request.POST.get('version')
    layer = request.POST.get('layer')
    
    data = ows_get_capabilities(url, service, version, layer, False)
    return HttpResponse(json.dumps(data, indent=4), content_type='application/json')


@login_required(login_url='/gvsigonline/auth/login_user/')
@require_safe
@staff_required
def cache_list(request):

    layer_list = None
    group_list = None
    if request.user.is_superuser:
        layer_list = Layer.objects.filter(cached=True).exclude(type='WMTS')
        group_list = LayerGroup.objects.filter(cached=True)
    else:
        layer_list = Layer.objects.filter(created_by__exact=request.user.username).filter(cached=True).exclude(type='WMTS')
        group_list = LayerGroup.objects.filter(created_by__exact=request.user.username).filter(cached=True)

    response = {
        'layers': layer_list,
        'groups': group_list
    }
    return render(request, 'cache_list.html', response)

@login_required(login_url='/gvsigonline/auth/login_user/')
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def layer_cache_config(request, layer_id):
    layer = Layer.objects.get(id=int(layer_id))
    layer_group = LayerGroup.objects.get(id=layer.layer_group.id)
    server = Server.objects.get(id=layer_group.server_id)
    
    if request.method == 'POST':
        format = request.POST.get('input_format')
        grid_set = request.POST.get('input_grid_set')
        min_x = request.POST.get('input_min_x')
        min_y = request.POST.get('input_min_y')
        max_x = request.POST.get('input_max_x')
        max_y = request.POST.get('input_max_y')
        number_of_tasks = request.POST.get('input_number_of_task')
        operation_type = request.POST.get('input_operation_type')
        zoom_start = request.POST.get('input_zoom_start')
        zoom_stop = request.POST.get('input_zoom_stop')
        
        try:
            if layer.external:
                if settings.CACHE_OPTIONS['OPERATION_MODE'] == 'ONLY_MASTER':
                    master_node = geographic_servers.get_instance().get_master_node(server.id)
                    url = master_node.getUrl()
                    geowebcache.get_instance().execute_cache_operation(None, layer, server, url, min_x, min_y, max_x, max_y, grid_set, zoom_start, zoom_stop, format, operation_type, number_of_tasks)
                
                elif settings.CACHE_OPTIONS['OPERATION_MODE'] == 'ALL_NODES':
                    all_nodes = geographic_servers.get_instance().get_all_nodes(server.id)
                    for n in all_nodes:
                        url = n.getUrl()
                        geowebcache.get_instance().execute_cache_operation(None, layer, server, url, min_x, min_y, max_x, max_y, grid_set, zoom_start, zoom_stop, format, operation_type, number_of_tasks)
                    
            else:
                if settings.CACHE_OPTIONS['OPERATION_MODE'] == 'ONLY_MASTER':
                    master_node = geographic_servers.get_instance().get_master_node(server.id)
                    url = master_node.getUrl()
                    geowebcache.get_instance().execute_cache_operation(layer.datastore.workspace.name, layer, server, url, min_x, min_y, max_x, max_y, grid_set, zoom_start, zoom_stop, format, operation_type, number_of_tasks)
                
                elif settings.CACHE_OPTIONS['OPERATION_MODE'] == 'ALL_NODES':
                    all_nodes = geographic_servers.get_instance().get_all_nodes(server.id)
                    for n in all_nodes:
                        url = n.getUrl()
                        geowebcache.get_instance().execute_cache_operation(layer.datastore.workspace.name, layer, server, url, min_x, min_y, max_x, max_y, grid_set, zoom_start, zoom_stop, format, operation_type, number_of_tasks)
            
            gs = geographic_servers.get_instance().get_server_by_id(server.id)
            gs.reload_nodes()
            
            if not layer.external:
                gs.updateBoundingBoxFromData(layer)
                gs.updateThumbnail(layer, 'update')
       
            layer_list = None
            if request.user.is_superuser:
                layer_list = Layer.objects.filter(cached=True)
            else:
                layer_list = Layer.objects.filter(created_by__exact=request.user.username).filter(cached=True)
        
            response = {
                'layers': layer_list
            }
            return render(request, 'cache_list.html', response)
            
        except Exception as e:
            message = e
            config = None
            tasks = None
            master_node = geographic_servers.get_instance().get_master_node(server.id)
            if layer.external:
                config = geowebcache.get_instance().get_layer(None, layer, server, master_node.getUrl()).get('wmsLayer')
                tasks = geowebcache.get_instance().get_pending_and_running_tasks(None, layer, server, master_node.getUrl())
            else:
                config = geowebcache.get_instance().get_layer(layer.datastore.workspace.name, layer, server, master_node.getUrl()).get('GeoServerLayer')
                tasks = geowebcache.get_instance().get_pending_and_running_tasks(layer.datastore.workspace.name, layer, server, master_node.getUrl())
            
            response = {
                "message": message,
                "layer_id": layer_id,
                "max_zoom_level": range(settings.MAX_ZOOM_LEVEL + 1),
                "grid_subsets": config.get('gridSubsets'),
                "json_grid_subsets": json.dumps(config.get('gridSubsets')),
                "formats": settings.CACHE_OPTIONS['FORMATS'],
                "tasks": tasks['long-array-array']
            }
                
            return render(request, 'layer_cache_config.html', response)
        
        
        
    
    else:      
        config = None
        tasks = None
        master_node = geographic_servers.get_instance().get_master_node(server.id)
        if layer.external:
            config = geowebcache.get_instance().get_layer(None, layer, server, master_node.getUrl()).get('wmsLayer')
            tasks = geowebcache.get_instance().get_pending_and_running_tasks(None, layer, server, master_node.getUrl())
        else:
            config = geowebcache.get_instance().get_layer(layer.datastore.workspace.name, layer, server, master_node.getUrl()).get('GeoServerLayer')
            tasks = geowebcache.get_instance().get_pending_and_running_tasks(layer.datastore.workspace.name, layer, server, master_node.getUrl())
           
        response = {
            "layer_id": layer_id,
            "max_zoom_level": range(settings.MAX_ZOOM_LEVEL + 1),
            "grid_subsets": config.get('gridSubsets'),
            "json_grid_subsets": json.dumps(config.get('gridSubsets')),
            "formats": settings.CACHE_OPTIONS['FORMATS'],
            "tasks": tasks['long-array-array'],
            "latlong_extent": layer.latlong_extent
        }
            
        return render(request, 'layer_cache_config.html', response)
    
@login_required(login_url='/gvsigonline/auth/login_user/')
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def group_cache_config(request, group_id):
    layer_group = LayerGroup.objects.get(id=int(group_id))
    server = Server.objects.get(id=layer_group.server_id)
    
    if request.method == 'POST':
        format = request.POST.get('input_format')
        grid_set = request.POST.get('input_grid_set')
        min_x = request.POST.get('input_min_x')
        min_y = request.POST.get('input_min_y')
        max_x = request.POST.get('input_max_x')
        max_y = request.POST.get('input_max_y')
        number_of_tasks = request.POST.get('input_number_of_task')
        operation_type = request.POST.get('input_operation_type')
        zoom_start = request.POST.get('input_zoom_start')
        zoom_stop = request.POST.get('input_zoom_stop')
        
        try:
            if settings.CACHE_OPTIONS['OPERATION_MODE'] == 'ONLY_MASTER':
                master_node = geographic_servers.get_instance().get_master_node(server.id)
                url = master_node.getUrl()
                geowebcache.get_instance().execute_group_cache_operation(layer_group, server, url, min_x, min_y, max_x, max_y, grid_set, zoom_start, zoom_stop, format, operation_type, number_of_tasks)
                
            elif settings.CACHE_OPTIONS['OPERATION_MODE'] == 'ALL_NODES':
                all_nodes = geographic_servers.get_instance().get_all_nodes(server.id)
                for n in all_nodes:
                    url = n.getUrl()
                    geowebcache.get_instance().execute_group_cache_operation(layer_group, server, url, min_x, min_y, max_x, max_y, grid_set, zoom_start, zoom_stop, format, operation_type, number_of_tasks)
            
            gs = geographic_servers.get_instance().get_server_by_id(server.id)
            gs.reload_nodes()    
            layer_list = None
            group_list = None
            if request.user.is_superuser:
                layer_list = Layer.objects.filter(cached=True)
                group_list = LayerGroup.objects.filter(cached=True)
            else:
                group_list = LayerGroup.objects.filter(created_by__exact=request.user.username).filter(cached=True)
        
            response = {
                'layers': layer_list,
                'groups': group_list
            }
            return render(request, 'cache_list.html', response)
            
        except Exception as e:
            message = e
            config = None
            tasks = None
            master_node = geographic_servers.get_instance().get_master_node(server.id)
            
            config = geowebcache.get_instance().get_group(layer_group, server, master_node.getUrl()).get('GeoServerLayer')
            tasks = geowebcache.get_instance().get_group_pending_and_running_tasks(layer_group, server, master_node.getUrl())
            
            response = {
                "message": message,
                "group_id": group_id,
                "max_zoom_level": range(settings.MAX_ZOOM_LEVEL + 1),
                "grid_subsets": config.get('gridSubsets'),
                "json_grid_subsets": json.dumps(config.get('gridSubsets')),
                "formats": settings.CACHE_OPTIONS['FORMATS'],
                "tasks": tasks['long-array-array']
            }
                
            return render(request, 'group_cache_config.html', response)
        
        
        
    
    else:      
        config = None
        tasks = None
        master_node = geographic_servers.get_instance().get_master_node(server.id)
        
        config = geowebcache.get_instance().get_group(layer_group, server, master_node.getUrl()).get('GeoServerLayer')
        tasks = geowebcache.get_instance().get_group_pending_and_running_tasks(layer_group, server, master_node.getUrl())
                
        response = {
            "group_id": group_id,
            "max_zoom_level": range(settings.MAX_ZOOM_LEVEL + 1),
            "grid_subsets": config.get('gridSubsets'),
            "json_grid_subsets": json.dumps(config.get('gridSubsets')),
            "formats": settings.CACHE_OPTIONS['FORMATS'],
            "tasks": tasks['long-array-array']
        }
            
        return render(request, 'group_cache_config.html', response)
    
@login_required(login_url='/gvsigonline/auth/login_user/')
@require_POST
@staff_required
def get_cache_tasks(request):
    layer_id = request.POST.get('layer_id')
    layer = Layer.objects.get(id=int(layer_id))
    layer_group = LayerGroup.objects.get(id=layer.layer_group.id)
    server = Server.objects.get(id=layer_group.server_id)
    master_node = geographic_servers.get_instance().get_master_node(server.id)
    
    tasks = None
    if layer.external:
        tasks = geowebcache.get_instance().get_pending_and_running_tasks(None, layer, server, master_node.getUrl())
    else:
        tasks = geowebcache.get_instance().get_pending_and_running_tasks(layer.datastore.workspace.name, layer, server, master_node.getUrl())
    
    return HttpResponse(json.dumps(tasks, indent=4), content_type='application/json')

@login_required(login_url='/gvsigonline/auth/login_user/')
@require_POST
@staff_required
def get_group_cache_tasks(request):
    group_id = request.POST.get('group_id')
    layer_group = LayerGroup.objects.get(id=int(group_id))
    server = Server.objects.get(id=layer_group.server_id)
    master_node = geographic_servers.get_instance().get_master_node(server.id)
    
    tasks = geowebcache.get_instance().get_group_pending_and_running_tasks(layer_group, server, master_node.getUrl())
    
    return HttpResponse(json.dumps(tasks, indent=4), content_type='application/json')

@login_required(login_url='/gvsigonline/auth/login_user/')
@require_POST
@staff_required
def kill_all_tasks(request):
    layer_id = request.POST.get('layer_id')
    layer = Layer.objects.get(id=int(layer_id))
    layer_group = LayerGroup.objects.get(id=layer.layer_group.id)
    server = Server.objects.get(id=layer_group.server_id)
    master_node = geographic_servers.get_instance().get_master_node(server.id)
    
    if layer.external:
        geowebcache.get_instance().kill_all_tasks(None, layer, server, master_node.getUrl())
    else:
        geowebcache.get_instance().kill_all_tasks(layer.datastore.workspace.name, layer, server, master_node.getUrl())
    
    geographic_servers.get_instance().get_server_by_id(server.id).reload_nodes()
    
    return HttpResponse(json.dumps({}, indent=4), content_type='application/json')

@login_required(login_url='/gvsigonline/auth/login_user/')
@require_POST
@staff_required
def kill_all_group_tasks(request):
    group_id = request.POST.get('group_id')
    layer_group = LayerGroup.objects.get(id=int(group_id))
    server = Server.objects.get(id=layer_group.server_id)
    master_node = geographic_servers.get_instance().get_master_node(server.id)
    
    geowebcache.get_instance().kill_all_tasks(layer_group, server, master_node.getUrl())
    
    geographic_servers.get_instance().get_server_by_id(server.id).reload_nodes()
    
    return HttpResponse(json.dumps({}, indent=4), content_type='application/json')

@login_required(login_url='/gvsigonline/auth/login_user/')
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def update_thumbnail(request, layer_id):
    layer = Layer.objects.get(id=int(layer_id))
    layer_group = LayerGroup.objects.get(id=layer.layer_group.id)
    server = Server.objects.get(id=layer_group.server_id)
    
    try:
        gs = geographic_servers.get_instance().get_server_by_id(server.id)
        layer = gs.updateThumbnail(layer, 'update')
        return HttpResponse(json.dumps({'success': True, 'updated_thumbnail': layer.thumbnail.url}, indent=4), content_type='application/json')
        
    except Exception as e:
        print str(e)
        return HttpResponse(json.dumps({'success': False}, indent=4), content_type='application/json')
    

@login_required(login_url='/gvsigonline/auth/login_user/')
@require_safe
@superuser_required
def service_url_list(request):
    response = {
        'services': ServiceUrl.objects.values()
    }
    return render(request, 'service_url_list.html', response)

@login_required(login_url='/gvsigonline/auth/login_user/')
@superuser_required
@require_http_methods(["GET", "POST", "HEAD"])
def service_url_add(request):
    if request.method == 'POST':
        form = ServiceUrlForm(request.POST)
        if form.is_valid():
            # save it on DB if successfully created
            service_url = ServiceUrl(**form.cleaned_data)
            service_url.save()
            
            return HttpResponseRedirect(reverse('service_url_list'))
                
    else:
        form = ServiceUrlForm()
            
    return render(request, 'service_url_add.html', {'form': form})

@login_required(login_url='/gvsigonline/auth/login_user/')
@require_POST
@superuser_required
def service_url_delete(request, svid):
    try: 
        service_url = ServiceUrl.objects.get(id=svid)
        service_url.delete()
        return HttpResponseRedirect(reverse('service_url_list'))
        
    except Exception as e:
        print e.message 
        return HttpResponseNotFound(e.message ) 
    
    
@login_required(login_url='/gvsigonline/auth/login_user/')
@superuser_required
def service_url_update(request, svid):
    if request.method == 'POST':
        title = request.POST.get('title')
        type = request.POST.get('type')
        url = request.POST.get('url')
        
        service_url = ServiceUrl.objects.get(id=int(svid))
        
        service_url.title = title
        service_url.type = type
        service_url.url = url
        service_url.save() 
        
        return HttpResponseRedirect(reverse('service_url_list'))
    
    else:
        service_url = ServiceUrl.objects.get(id=int(svid))
        form = ServiceUrlForm(instance=service_url)
        
        return render(request, 'service_url_update.html', {'svid': svid, 'form': form})
    
@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def test_connection(request):
    if request.method == 'POST':
        datastore_type = request.POST.get('ds_type')
        connection_params = json.loads(request.POST.get('connection_params'))
        if datastore_type == 'v_PostGIS':
                
            try:
                connection = psycopg2.connect(
                    user = connection_params.get('user'),
                    password = connection_params.get('passwd'),
                    host = connection_params.get('host'),
                    port = connection_params.get('port'),
                    database = connection_params.get('database')
                )
                response = { 'success': True }
                connection.close()
                
            except Exception as e:
                response = {
                    'error': escape(strip_tags(str(e))),
                    'success': False 
                }
        elif datastore_type == 'e_WMS':
            try:
                user = connection_params.get('username')
                password = connection_params.get('password')
                url = connection_params.get('url')
                
                with requests.get(url, auth=(user, password), stream=True, verify=False) as r:
                    if r.status_code >= 200 or r.status_code < 300:
                        response = { 'success': True }
                    else:
                        response = {
                                'error': _('Connection failed') + '<br>' + _("Status code: ") + str(r.status_code),
                                'success': False 
                            }
            except Exception as e:
                logger.exception("Error connecting WMS")
                response = {
                    'error': _('Connection failed') + '<br>' + escape(strip_tags(str(e))),
                    'success': False 
                }
        else:
                response = {
                    'error': _('Connection error'),
                    'success': False 
                }
        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')
    
#@login_required(login_url='/gvsigonline/auth/login_user/')
@csrf_exempt
def register_action(request):
    if request.method == 'POST':
        layer_name = request.POST.get('layer_name')
        workspace = request.POST.get('workspace')
        layer = Layer.objects.get(name=layer_name, datastore__workspace__name=workspace)
        
        if request.user.is_anonymous:
            action.send(layer, verb="gvsigol_services/layer_activate", action_object=layer)
        else:
            action.send(request.user, verb="gvsigol_services/layer_activate", action_object=layer)

        return HttpResponse(json.dumps({'success': True}, indent=4), content_type='application/json')