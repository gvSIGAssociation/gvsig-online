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
import json
import logging
import os
import random
import re
import string
import urllib.request, urllib.parse, urllib.error
import xmltodict

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.urls import reverse
from django.http import HttpResponseRedirect, HttpResponseBadRequest, HttpResponseNotFound, HttpResponse, HttpResponseForbidden, StreamingHttpResponse
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from django.utils.translation import ugettext as _, ugettext_lazy, ugettext

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_safe, require_POST, require_GET
from django.utils.html import escape, strip_tags
from urllib.parse import urlparse
import zipfly
from owslib.util import Authentication
from owslib.wms import WebMapService
from owslib.wmts import WebMapTileService
import requests
from requests_futures.sessions import FuturesSession

from gvsigol.basetypes import BackendNotAvailable

from .backend_postgis import Introspect
from .backend_postgis import SqlFrom, SqlField, SqlJoinFields
from .forms_geoserver import CreateFeatureTypeForm
from .forms_services import ServerForm, SqlViewForm, WorkspaceForm, DatastoreForm, LayerForm, LayerUpdateForm, DatastoreUpdateForm, ExternalLayerForm, ServiceUrlForm
from gdaltools import gdalsrsinfo
from . import geographic_servers
from gvsigol import settings
from gvsigol.settings import FILEMANAGER_DIRECTORY, LANGUAGES, INSTALLED_APPS, WMS_MAX_VERSION, WMTS_MAX_VERSION, BING_LAYERS
from gvsigol.settings import MOSAIC_DB
from gvsigol_auth.utils import superuser_required, staff_required, get_primary_user_role, ascii_norm_username
from gvsigol_auth import auth_backend
from gvsigol_core import utils as core_utils
from gvsigol_core.views import forbidden_view
from gvsigol_core.models import Project, ProjectRole, ProjectBaseLayerTiling
from gvsigol_core.models import ProjectLayerGroup, TilingProcessStatus
from gvsigol_symbology.models import Style
from gvsigol_core.views import not_found_view
from gvsigol_services.backend_resources import resource_manager
from gvsigol_services.models import LayerResource, TriggerProcedure, Trigger, LayerReadRole, LayerWriteRole
import gvsigol_services.tiling_service as tiling_service
from .models import LayerFieldEnumeration, SqlView
from .models import Workspace, Datastore, LayerGroup, Layer, Enumeration, EnumerationItem, \
    LayerLock, Server, Node, ServiceUrl, LayerGroupRole, LayerTopologyConfiguration
from .rest_geoserver import RequestError
from . import rest_geoserver
from . import rest_geowebcache as geowebcache
from . import signals
from . import utils
import psycopg2
from psycopg2 import sql

from actstream import action
from actstream.models import Action
from django_sendfile import sendfile
from gvsigol_services.backend_geoserver import _valid_sql_name_regex
from lxml import etree, html
from django.contrib import messages


from . import tasks
import time
from django.core import serializers as serial
from django.db.models import Max
from gvsigol_auth.signals import role_deleted
from django.views.decorators.cache import never_cache

logger = logging.getLogger("gvsigol")

_valid_name_regex=re.compile("^[a-zA-Z_][a-zA-Z0-9_]*$")

CONNECT_TIMEOUT = 3.05
READ_TIMEOUT = 30
base_layer_process = {}


def role_deleted_handler(sender, **kwargs):
    try:
        role = kwargs['role']
        LayerReadRole.objects.filter(role=role).delete()
        LayerWriteRole.objects.filter(role=role).delete()
    except Exception as e:
        print(e)
        pass

def connect_signals():
    role_deleted.connect(role_deleted_handler)

connect_signals()


@login_required()
@require_safe
@superuser_required
def server_list(request):
    response = {
        'servers': list(Server.objects.values())
    }
    return render(request, 'server_list.html', response)

@login_required()
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
                    status = n.get('status', 'active'),
                    url = n['url'],
                    is_master = n['is_master']
                )
                node.save()

            master_list = Node.objects.filter(server=server, is_master=True)
            if master_list.count() == 0:
                node_list = Node.objects.filter(server=server)
                if node_list.count() > 0:
                    node_list[0].is_master = True
                    node_list[0].save()
                else:
                    # if no nodes are created, set the first one as master
                    node = Node(
                        server = server,
                        status = 'active',
                        url = server.frontend_url,
                        is_master = True
                    )
                    node.save()

            geographic_servers.get_instance().add_server(server)
            return HttpResponseRedirect(reverse('server_list'))

    else:
        name = 'server_' + ''.join(random.choice(string.ascii_uppercase) for i in range(6))
        form = ServerForm(initial={'name': name})

    return render(request, 'server_add.html', {'form': form})

@login_required()
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
        logger.exception("Error deleting server: " + str(e))
        return HttpResponseNotFound(str(e) )


@login_required()
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
        geographic_servers.reset_instance()
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

@login_required()
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

@login_required()
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


@login_required()
@require_safe
@superuser_required
def workspace_list(request):
    workspaces = [ {
        'id': w.id,
        'name': w.name,
        'description': w.description,
        'uri': w.uri,
        'is_public': w.is_public,
        'server': w.server.title_name
        }
        for w in Workspace.objects.all()
    ]
    response = {
        'workspaces': workspaces
    }
    return render(request, 'workspace_list.html', response)

@login_required()
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

@login_required()
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
            'workspaces': list(querySet.values())
        }
        return render(request, 'workspace_import.html', response)


@login_required()
@require_POST
@superuser_required
def workspace_delete(request, wsid):
    ws = None
    try:
        ws = Workspace.objects.get(id=wsid)
        utils._workspace_delete(ws, reload_nodes=True)
        return HttpResponseRedirect(reverse('workspace_list'))
    except BackendNotAvailable:
        return HttpResponse('The map server is not available. Try again later or contact the system administrators', status=503)
    except:
        if ws:
            ws_str = ws.name
        else:
            ws_str = wsid
        return HttpResponseNotFound('Workspace not found: {0}'.format(ws_str))

@login_required()
@superuser_required
def workspace_update(request, wid):
    if request.method == 'POST':
        uri = request.POST.get('workspace-uri')
        description = request.POST.get('workspace-description')
        isPublic = False
        if 'is_public' in request.POST:
            isPublic = True

        workspace = Workspace.objects.get(id=int(wid))

        workspace.description = description
        workspace.uri = uri
        workspace.is_public = isPublic
        workspace.save()
        return redirect('workspace_list')

    else:
        workspace = Workspace.objects.get(id=int(wid))
        return render(request, 'workspace_update.html', {'wid': wid, 'workspace': workspace})


@login_required()
@require_safe
@staff_required
def datastore_list(request):

    datastore_list = None
    if request.user.is_superuser:
        datastore_list = Datastore.objects.all()
    else:
        # no consideramos DefaultUserDatastore porque por el momento sólo permitimos actualizar el datastore
        # a superusuarios o al creador
        datastore_list = Datastore.objects.filter(created_by=request.user.username).order_by('name')

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


@login_required()
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
            except Exception as e:
                logger.exception(str(e))
                has_errors = True

        if type == 'c_ImageMosaic':
            file = post_dict.get('file')
            try:
                output = file.replace('file://', '')
                if output == None or output.__len__() <= 0:
                    has_errors = True
                else:
                    if file[-1] != '/':
                        file = file + '/'
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
            elif name.lower() != name:
                form.add_error(None, _("Invalid datastore name: '{value}'. Identifiers must be in lowercase.").format(value=name))
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

@login_required()
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def datastore_update(request, datastore_id):
    try:
        datastore = Datastore.objects.get(id=datastore_id)
    except Datastore.DoesNotExist:
        return HttpResponseNotFound('<h1>Datastore not found {0}</h1>'.format(datastore_id))
    if not utils.can_manage_datastore(request.user, datastore):
        return forbidden_view(request)
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
                expose_pks_old = gs.datastore_check_exposed_pks(datastore)
                if gs.updateDatastore(datastore.workspace.name, datastore.name,
                                                      description, dstype, connection_params):
                    # REST API does not allow to can't change the workspace or name of a datastore
                    #datastore.workspace = workspace
                    #datastore.name = name
                    datastore.description = description
                    datastore.connection_params = connection_params
                    datastore.save()
                    expose_pks_new = gs.datastore_check_exposed_pks(datastore)
                    if expose_pks_old != expose_pks_new:
                        for layer in datastore.layer_set.all():
                            gs.reload_featuretype(layer, attributes=True, nativeBoundingBox=True, latLonBoundingBox=True)
                            layer.get_config_manager().refresh_field_conf(include_pks=expose_pks_new)
                            layer.save()
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

@login_required()
@require_POST
@staff_required
def datastore_delete(request, dsid):
    try:
        ds = Datastore.objects.get(id=dsid)
    except Datastore.DoesNotExist:
        return HttpResponseNotFound('<h1>Datastore not found {0}</h1>'.format(dsid))
    if not utils.can_manage_datastore(request.user, ds):
        return forbidden_view(request)
    try:
        delete_schema = False
        if request.POST.get('delete_schema') == 'true':
            delete_schema = True
        gs = geographic_servers.get_instance().get_server_by_id(ds.workspace.server.id)
        gs.deleteDatastore(ds.workspace, ds, delete_schema=delete_schema)
        utils.delete_datastore_elements(ds, gs=gs)
        return HttpResponseRedirect(reverse('datastore_list'))

    except:
        logger.exception("Error deleting store")
        return HttpResponseBadRequest()


@login_required()
@require_safe
@staff_required
def layer_list(request):

    layer_list = None
    if request.user.is_superuser:
        layer_list = Layer.objects.filter(external=False)
        project_list = Project.objects.all()
    else:
        user_roles = auth_backend.get_roles(request)
        layer_list = (Layer.objects.filter(created_by=request.user.username, external=False)
            | Layer.objects.filter(layermanagerole__role__in=user_roles, external=False)).distinct()
        project_list = core_utils.get_user_projects(request, permissions=ProjectRole.PERM_MANAGE)
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
            'thumbnail_url': l.thumbnail.url.replace(settings.BASE_URL, ''),
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


def _layer_refresh_extent(layer):
    datastore = layer.datastore
    workspace = datastore.workspace
    #server.updateBoundingBoxFromData(layer)
    server = geographic_servers.get_instance().get_server_by_id(workspace.server.id)
    if datastore.type == 'v_PostGIS':
        server.reload_featuretype(layer, attributes=True, nativeBoundingBox=True, latLonBoundingBox=True)
        # restore dynamic grid subsets for gwc layers
        server.set_gwclayer_dynamic_subsets(workspace, layer.name)
        server.reload_nodes()
    (ds_type, layer_info) = server.getResourceInfo(workspace.name, datastore, layer.name, "json")
    utils.set_layer_extent(layer, ds_type, layer_info, server)

@login_required()
@staff_required
def layer_refresh_conf(request, layer_id):
    try:
        layer = Layer.objects.get(pk=layer_id)
        if not utils.can_manage_layer(request, layer):
            return HttpResponseForbidden('{"response": "error"}', content_type='application/json')
        _layer_refresh_extent(layer)
        if layer.type.startswith('v_'):
            server = geographic_servers.get_instance().get_server_by_id(layer.datastore.workspace.server.id)
            expose_pks = server.datastore_check_exposed_pks(layer.datastore)
            layer.get_config_manager().refresh_field_conf(include_pks=expose_pks)
        layer.save()
        if layer.type.startswith('v_'):
            i, source_name, schema = layer.get_db_connection()
            with i as conn:
                # ensure the pk sequence has a consistent status
                conn.update_pk_sequences(source_name, schema=schema)
        return JsonResponse({"result": "ok"})
    except:
        logger.exception("Error refreshing layer conf")
        return JsonResponse({"result": "error"}, status=500)
@login_required()
@staff_required
def layer_delete(request, layer_id):
    try:
        response = layer_delete_operation(request, layer_id)
        if response:
            return response
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

@login_required()
@staff_required
def layer_delete_operation(request, layer_id):
    try:
        layer = Layer.objects.get(pk=layer_id)
        if not utils.can_manage_layer(request, layer):
            msg = _('ERROR User is not authorized to perform this operation')
            data = {
                    'status': 'ERROR',
                    'status_code': 403,
                    'message': msg,
                }
            return HttpResponse(json.dumps(data), status_code=403)
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
        Layer.objects.filter(pk=layer_id).delete()
        gs.deleteLayerRules(layer)
        core_utils.toc_remove_layer(layer)
        gs.createOrUpdateGeoserverLayerGroup(layer.layer_group)
        gs.reload_nodes()
    except Exception as e:
        logger.exception("error deleting layer")
        data = {
                'status': 'ERROR',
                'status_code': 400,
                'message': str(e),
            }
        return JsonResponse(data, status=400)



@login_required()
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


@login_required()
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
        if not utils.can_manage_datastore(request.user, ds):
            return HttpResponseForbidden(json.dumps([]))
        if ds:
            gs = geographic_servers.get_instance().get_server_by_id(ds.workspace.server.id)
            resources = gs.getResources(ds.workspace, ds, 'available')
            resources_sorted = sorted(resources)
            return HttpResponse(json.dumps(resources_sorted))
    return HttpResponseBadRequest()

@login_required()
@staff_required
def layergroup_list_editable(request):
    """
    Lists the layer groups editable by the current user
    """
    if 'id_datastore' in request.GET:
        id_ds = request.GET['id_datastore']
        layergroup_id = request.GET.get('layergroup_id')
        ds = Datastore.objects.get(id=id_ds)
        if not utils.can_manage_datastore(request, ds):
            return HttpResponseForbidden("[]")
        if ds:
            layer_groups = []
            if layergroup_id:
                lg_list = utils.get_user_layergroups(request).filter(id=layergroup_id)
            else:
                lg_list = utils.get_user_layergroups(request, permissions=LayerGroupRole.PERM_INCLUDEINPROJECTS) | LayerGroup.objects.filter(name='__default__')
            lg_list = lg_list.filter(server_id=ds.workspace.server.id).order_by('name').distinct()
            for lg in lg_list:
                layer_group = {
                    'value': lg.id,
                    'text': lg.name
                }
                layer_groups.append(layer_group)
            return JsonResponse(layer_groups, safe=False)

    return HttpResponseBadRequest()

@login_required()
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
        if not utils.can_manage_datastore(request.user, ds):
            return HttpResponseForbidden("[]")
        if ds:
            gs = geographic_servers.get_instance().get_server_by_id(ds.workspace.server.id)
            resources = gs.getResources(ds.workspace, ds, 'configurable')
            resources_sorted = sorted(resources)
            return HttpResponse(json.dumps(resources_sorted))
    return HttpResponseBadRequest()


@login_required()
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
        if not utils.can_manage_datastore(request.user, ds):
            return HttpResponseForbidden("[]")
        if ds:
            gs = geographic_servers.get_instance().get_server_by_id(ds.workspace.server.id)
            resources = gs.getResources(ds.workspace, ds, type)
            resources_sorted = sorted(resources)
            return HttpResponse(json.dumps(resources_sorted))
    return HttpResponseBadRequest()


@login_required()
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
    elif 'datastore_id' in request.GET and 'table_name' in request.GET:
        datastore_id = request.GET['datastore_id']
        name = request.GET['table_name']
        ds = Datastore.objects.get(id=datastore_id)
    if ds:
        if not utils.can_manage_datastore(request.user, ds):
            return HttpResponseForbidden("[]")
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
                            field['title-'+id] = f.get('title-'+id, field['name'])
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

        result_resources_sorted = sorted(result_resources, key=lambda rk: rk.get('name', ''))
        return HttpResponse(json.dumps(result_resources_sorted))

    return HttpResponseBadRequest()


def do_add_layer(server, datastore, name, title, is_queryable, extraParams):
    workspace = datastore.workspace

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
    if ds_type == 'c_ImageMosaic':
        server.updateImageMosaicTemporal(layer.datastore, layer)
    elif ds_type[0:2] == 'v_':
        utils.set_time_enabled(server, layer)
    if ds_type != 'e_WMS':
        create_symbology(server, layer)
        server.updateThumbnail(layer, 'create')

    core_utils.toc_add_layer(layer)
    server.createOrUpdateGeoserverLayerGroup(layer.layer_group)
    server.reload_nodes()

def create_symbology(server, layer):
    style_name = layer.datastore.workspace.name + '_' + layer.name + '_1'
    server.createDefaultStyle(layer, style_name)
    server.setLayerStyle(layer, style_name, True)
    layer.save()



@login_required()
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def layer_add(request):
    return layer_add_with_group(request, None)


@login_required()
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def layer_add_with_group(request, layergroup_id):
    redirect_to_layergroup = request.GET.get('redirect')
    from_redirect = request.GET.get('from_redirect')
    project_id = request.GET.get('project_id')

    if redirect_to_layergroup:
        if from_redirect:
            query_string = '?redirect=' + from_redirect
        else:
            query_string = ''
        if project_id:
            back_url =  reverse('layergroup_update_with_project', kwargs={'lgid': layergroup_id, 'project_id': project_id})+query_string
        else:
            back_url = reverse('layergroup_update', kwargs={'lgid': layergroup_id})+query_string
    else:
        back_url = reverse('layer_list')

    roles = []
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

        real_time = False
        if 'real_time' in request.POST:
            real_time = True

        vector_tile = False
        if 'vector_tile' in request.POST:
            vector_tile = True

        is_public = (request.POST.get('resource-is-public') is not None)

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
                layergroup = form.cleaned_data['layer_group']
                if not utils.can_manage_datastore(request, datastore):
                    raise ValueError(_("You are not allowed to manage the selected datastore"))
                if not utils.can_use_layergroup(request, layergroup, permission=LayerGroupRole.PERM_INCLUDEINPROJECTS):
                    raise ValueError(_("You are not allowed to manage the selected layergroup"))
                workspace = datastore.workspace
                extraParams = {}

                assigned_read_roles = []
                assigned_write_roles = []
                assigned_manage_roles = []
                for key in request.POST:
                    if 'read-usergroup-' in key:
                        assigned_read_roles.append(key[len('read-usergroup-'):])
                    elif 'manage-usergroup-' in key:
                        assigned_manage_roles.append(key[len('manage-usergroup-'):])

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
                    with i as c:
                        fields = c.get_fields(form.cleaned_data['name'], schema)
                        is_view = c.is_view(schema, form.cleaned_data['name'])

                    if not is_view:
                        for key in request.POST:
                            if 'write-usergroup-' in key:
                                assigned_write_roles.append(key[len('write-usergroup-'):])
                else:
                    is_view = False
                roles = utils.get_layer_checked_roles_from_user_input(assigned_read_roles, assigned_write_roles, assigned_manage_roles)
                if datastore.type == 'v_PostGIS':
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
                newRecord.real_time = real_time
                newRecord.vector_tile = vector_tile
                newRecord.update_interval = request.POST.get('update_interval')

                params = {}
                params['format'] = request.POST.get('format')
                newRecord.external_params = json.dumps(params)

                newRecord.save()

                featuretype = {
                    'max_features': maxFeatures
                }

                utils.set_layer_permissions(newRecord, is_public, assigned_read_roles, assigned_write_roles, assigned_manage_roles)
                do_config_layer(server, newRecord, featuretype)

                if redirect_to_layergroup and (layergroup_id != newRecord.layer_group.id):
                    new_layergroup_id = newRecord.layer_group.id
                    if project_id:
                        to_url =  reverse('layergroup_update_with_project', kwargs={'lgid': new_layergroup_id, 'project_id': project_id})+query_string
                    else:
                        to_url = reverse('layergroup_update', kwargs={'lgid': new_layergroup_id})+query_string
                else:
                    to_url = back_url
                return HttpResponseRedirect(to_url)
            except rest_geoserver.RequestError as e:
                msg = e.server_message
                logger.exception(msg)
                form.add_error(None, msg)
            except Exception as e:
                msg = _("Error: layer could not be published") + '. ' + str(e)
                logger.exception(msg)
                # FIXME: the backend should raise more specific exceptions to identify the cause (e.g. layer exists, backend is offline)
                form.add_error(None, msg)

    else:
        form = LayerForm()
        if not request.user.is_superuser:
            form.fields['datastore'].queryset = (Datastore.objects.filter(created_by=request.user.username) |
                  Datastore.objects.filter(defaultuserdatastore__username=request.user.username)).order_by('name').distinct()
            form.fields['layer_group'].queryset = (utils.get_user_layergroups(request) | LayerGroup.objects.filter(name='__default__')).order_by('name').distinct()
        if layergroup_id:
            try:
                lyrgroup = LayerGroup.objects.get(id=layergroup_id)
                form.fields['datastore'].queryset = form.fields['datastore'].queryset.filter(workspace__server__id=lyrgroup.server_id)
                form.fields['layer_group'].queryset = form.fields['layer_group'].queryset.filter(id=layergroup_id)
            except LayerGroup.DoesNotExist:
                pass
        roles = utils.get_all_user_roles_checked_by_layer(None, get_primary_user_role(request))
        is_public = False

    datastore_types = {}
    for datastore in Datastore.objects.all():
        datastore_types[datastore.id] = datastore.type
    return render(request, 'layer_add.html', {
            'form': form,
            'datastore_types': json.dumps(datastore_types),
            'roles': roles,
            'resource_is_public': is_public,
            'redirect_to_layergroup': redirect_to_layergroup,
            'layergroup_id': layergroup_id,
            'from_redirect': from_redirect,
            'project_id': project_id,
            'back_url': back_url
            })

@login_required()
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def layer_update(request, layer_id):
    redirect_to_layergroup = request.GET.get('redirect')
    from_redirect = request.GET.get('from_redirect')
    project_id = request.GET.get('project_id')
    layergroup_id = request.GET.get('layergroup_id')
    try:
        layer = Layer.objects.get(id=int(layer_id))
        if not utils.can_manage_layer(request, layer):
            return forbidden_view(request)
    except Layer.DoesNotExist:
        return not_found_view(request)

    if request.method == 'POST':
        updatedParams = {}
        workspace = request.POST.get('workspace')
        datastore = request.POST.get('datastore')
        name = request.POST.get('name')
        title = request.POST.get('title')
        abstract = request.POST.get('md-abstract')
        updatedParams['title'] = title
        if not layergroup_id:
            layergroup_id = request.POST.get('layer_group', None)
        try:
            if layergroup_id:
                layer_group = LayerGroup.objects.get(id=layergroup_id)
            else:
                layer_group = layer.layer_group
        except LayerGroup.DoesNotExist:
            return not_found_view(request)
        if layer.layer_group != layer_group and not (utils.can_manage_layergroup(request, layer.layer_group)
                                                     and utils.can_manage_layergroup(request, layer_group)):
            # don't allow changing layer_group if the user can't manage the previous and the new layergroups
            return forbidden_view(request)
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

        real_time = False
        if 'real_time' in request.POST:
            real_time = True

        vector_tile = False
        if 'vector_tile' in request.POST:
            vector_tile = True

        assigned_read_roles = []
        assigned_manage_roles = []
        for key in request.POST:
            if 'read-usergroup-' in key:
                assigned_read_roles.append(key[len('read-usergroup-'):])
            elif 'manage-usergroup-' in key:
                assigned_manage_roles.append(key[len('manage-usergroup-'):])

        assigned_write_roles = []
        if layer.type == 'v_PostGIS':
            i, params = layer.datastore.get_db_connection()
            with i as c:
                is_view = c.is_view(layer.datastore.name, layer.source_name)
        else:
            is_view = False
        if not is_view:
            for key in request.POST:
                if 'write-usergroup-' in key:
                    assigned_write_roles.append(key[len('write-usergroup-'):])

        is_public = (request.POST.get('resource-is-public') is not None)

        if layer.datastore.type.startswith('v_'):
            try:
                maxFeatures = int(request.POST.get('max_features', 0))
            except:
                maxFeatures = 0
            updatedParams['maxFeatures'] = maxFeatures
            layerConf['featuretype'] = layerConf.get('featuretype', {})
            layerConf['featuretype']['max_features'] = maxFeatures

        detailed_info_enabled = (request.POST.get('detailed_info_enabled') is not None)
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
            try:
                time_resolution_year = int(request.POST.get('time_resolution_year'))
                time_resolution_month = int(request.POST.get('time_resolution_month'))
                time_resolution_week = int(request.POST.get('time_resolution_week'))
                time_resolution_day = int(request.POST.get('time_resolution_day'))
                time_resolution_hour = int(request.POST.get('time_resolution_hour'))
                time_resolution_minute = int(request.POST.get('time_resolution_minute'))
                time_resolution_second = int(request.POST.get('time_resolution_second'))
            except:
                logger.exception('Error getting time values')

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
            layer.layer_group = layer_group
            max_order = layer_group.layer_set.aggregate(Max('order')).get('order__max')
            layer.order = max_order + 1 if max_order is not None else layer.order
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
            try:
                layer.timeout = int(request.POST.get('timeout'))
            except:
                layer.timeout = None
            layer.real_time = real_time
            layer.vector_tile = vector_tile
            try:
                layer.update_interval = int(request.POST.get('update_interval'))
            except:
                layer.update_interval = None

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

            utils.set_layer_permissions(layer, is_public, assigned_read_roles, assigned_write_roles, assigned_manage_roles)
            gs.reload_nodes()
        if from_redirect:
            query_string = '?redirect=' + from_redirect
        else:
            query_string = ''
        if redirect_to_layergroup:
            if project_id:
                return HttpResponseRedirect(reverse('layergroup_update_with_project', kwargs={'lgid': layer.layer_group.id, 'project_id': project_id}) + query_string)
            else:
                return HttpResponseRedirect(reverse('layergroup_update', kwargs={'lgid': layer.layer_group.id}) + query_string)
        else:
            return redirect('layer_list')
    else:
        datastore = Datastore.objects.get(id=layer.datastore.id)
        workspace = Workspace.objects.get(id=datastore.workspace_id)
        form = LayerUpdateForm(request, layergroup_id=layergroup_id, instance=layer)

        if layer.external_params:
            params = json.loads(layer.external_params)
            for key in params:
                form.initial[key] = params[key]

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
            i, params = layer.datastore.get_db_connection()
            with i as c:
                is_view = c.is_view(layer.datastore.name, layer.source_name)
        else:
            is_view = False

        md_uuid = core_utils.get_layer_metadata_uuid(layer)
        plugins_config = core_utils.get_plugins_config()
        html = True
        if layer.detailed_info_html == None or layer.detailed_info_html == '' or layer.detailed_info_html == 'null':
            html = False

        _, layer_image_url = utils.get_layer_img(layer.id, None)
        roles = utils.get_all_user_roles_checked_by_layer(layer)
        return render(request, 'layer_update.html', {
            'html': html, 'layer': layer,
            'workspace': workspace,
            'form': form,
            'layer_id': layer_id,
            'layer_conf': layerConf,
            'date_fields': json.dumps(date_fields),

            'layer_md_uuid': md_uuid,
            'plugins_config': plugins_config,
            'layer_image_url': layer_image_url,
            'datastore_type': layer.datastore.type,
            'roles': roles,
            'resource_is_public': layer.public,
            'is_view': is_view,
            'redirect_to_layergroup': redirect_to_layergroup,
            'layergroup_id': layergroup_id,
            'project_id': project_id,
            'from_redirect': from_redirect
        })

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
        if not utils.can_manage_datastore(request, ds):
            return {
                'date_fields': date_fields,
                'status': 'error',
                'error_message': 'not allowed'
            }
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

    # Preservar configuración existente de campos especiales
    existing_conf = layer.conf
    existing_fields_config = {}
    if existing_conf:
        try:
            if isinstance(existing_conf, str):
                existing_conf = ast.literal_eval(existing_conf)
            for field in existing_conf.get('fields', []):
                if field.get('gvsigol_type') == 'link' or field.get('type_params') or field.get('field_format'):
                    existing_fields_config[field['name']] = {
                        'gvsigol_type': field.get('gvsigol_type', ''),
                        'type_params': field.get('type_params', {}),
                        'field_format': field.get('field_format', {})
                    }
        except:
            pass

    layer_conf = {
        'featuretype': featuretype,
        }

    if ds_type  == 'featureType':
        expose_pks = server.datastore_check_exposed_pks(datastore)
        lyr_conf = layer.get_config_manager()
        fields = lyr_conf.get_updated_field_conf(include_pks=expose_pks)
        
        # Agregar campos virtuales (como link) si no se recuperan de la base de datos
        existing_field_names = {field.get('name') for field in fields}
        for field_name, field_config in existing_fields_config.items():
            if field_name not in existing_field_names:
                # Crear campo virtual con configuración básica
                virtual_field = {
                    'name': field_name,
                    'gvsigol_type': field_config['gvsigol_type'],
                    'type_params': field_config['type_params'],
                    'field_format': field_config['field_format'],
                    'visible': True,
                    'infovisible': True,
                    'nullable': True,
                    'mandatory': False,
                    'editable': False,
                    'editableactive': False
                }
            
                for id, language in LANGUAGES:
                    virtual_field['title-' + id] = field_name
                
                fields.append(virtual_field)
        
        # Restaurar configuración de campos especiales para campos existentes
        for field in fields:
            field_name = field.get('name')
            if field_name in existing_fields_config:
                field['gvsigol_type'] = existing_fields_config[field_name]['gvsigol_type']
                field['type_params'] = existing_fields_config[field_name]['type_params']
                field['field_format'] = existing_fields_config[field_name]['field_format']
                if field['gvsigol_type'] == 'link':
                    field['editable'] = False
                    field['editableactive'] = False
        
        layer_conf['fields'] = fields
        layer_conf['form_groups'] = _parse_form_groups([], fields)
    layer.conf = layer_conf

def _parse_form_groups(form_groups, fields):
    if not(isinstance(form_groups, list)) or len(form_groups) == 0:
        form_groups = [{
            'name': 'group1'
        }]
    all_fields = { f.get('name'): True for f in fields }
    # ensure all fields and translations are present

    for group in form_groups:
        group_fields = group.get('fields', [])
        for field in group_fields:
            if all_fields.get(field):
                del all_fields[field]
            else:
                group_fields.remove(field)
        for id, language in LANGUAGES:
            title_lang = 'title-'+id
            if group.get(title_lang) is None:
                group[title_lang] = ''
        group['fields'] = group_fields
    group0_fields = form_groups[0].get("fields", [])
    for f in all_fields:
        group0_fields.append(f)
    form_groups[0]["fields"] = group0_fields
    return form_groups


def _generate_topology_trigger_sql(rule_type, layer, **kwargs):
    """
    Genera el SQL para crear triggers topológicos dinámicamente
    """
    try:
        # Obtener información de la capa
        i, source_name, schema = layer.get_db_connection()
        table_name = source_name if source_name else layer.name
        full_table_name = f"{schema}.{table_name}"
        
        # Obtener la primary key y el campo de geometría dinámicamente
        with i as conn:
            pk_columns = conn.get_pk_columns(table_name, schema)
            geom_columns = conn.get_geometry_columns(table_name, schema)
            geom_columns_info = conn.get_geometry_columns_info(table_name, schema)
        
        # Validar que existan PK y geometría
        if not pk_columns:
            raise Exception(f"No se encontró primary key para la tabla {full_table_name}")
        if not geom_columns:
            raise Exception(f"No se encontró campo de geometría para la tabla {full_table_name}")
        
        # Usar la primera PK y primera columna de geometría (normalmente solo hay una de cada)
        pk_field = pk_columns[0]
        geom_field = geom_columns[0]
        
        # Obtener el SRID de la geometría para determinar la precisión del SnapToGrid
        layer_srid = None
        if geom_columns_info and len(geom_columns_info) > 0:
            # geom_columns_info[0][4] es el SRID (posición 4 en la tupla)
            layer_srid = geom_columns_info[0][4]
        
        # Determinar la precisión usando el archivo crs_definitions.json
        snap_precision = 0.001  # Default para métrico
        if layer_srid:
            try:
                import json
                import os
                crs_file_path = os.path.join(settings.BASE_DIR, 'gvsigol', 'crs_definitions.json')
                with open(crs_file_path, 'r') as f:
                    crs_definitions = json.load(f)
                
                srid_str = str(layer_srid)
                if srid_str in crs_definitions:
                    units = crs_definitions[srid_str].get('units', '')
                    if units == 'degrees':
                        # Sistema geográfico (grados decimales) - usar precisión muy alta
                        snap_precision = 0.000000001
                    elif units == 'meters':
                        # Sistema métrico (metros) - usar precisión al milímetro
                        snap_precision = 0.001
                    else:
                        # Default para unidades desconocidas
                        snap_precision = 0.001
                        logger.warning(f"Unidades desconocidas '{units}' para SRID {layer_srid}, usando precisión métrica por defecto")
                else:
                    logger.warning(f"SRID {layer_srid} no encontrado en crs_definitions.json, usando precisión métrica por defecto")
            except Exception as e:
                logger.error(f"Error leyendo crs_definitions.json para SRID {layer_srid}: {str(e)}")
                snap_precision = 0.001  # Default seguro
        
        logger.info(f"Generando trigger {rule_type} para tabla {full_table_name}: PK='{pk_field}', Geom='{geom_field}', SRID={layer_srid}, SnapToGrid precision={snap_precision}")
        
        # Nombres únicos para funciones y triggers (con esquema para la función)
        function_name_simple = f"{rule_type}_{table_name.lower()}"
        function_name = f"{schema}.{function_name_simple}"
        trigger_name = f"trigger_{rule_type}_{table_name.lower()}"
        
        if rule_type == "must_not_overlaps":
            # SQL para función MUST NOT OVERLAPS
            function_sql = f"""
            CREATE OR REPLACE FUNCTION {function_name}()
            RETURNS TRIGGER AS
            $$
            DECLARE
                radio INTEGER := 1;
                snap_precision NUMERIC := {snap_precision};
                conflicting_id TEXT;
                overlap_geom GEOMETRY;
                overlap_area NUMERIC;
                overlap_geojson TEXT;
                error_message TEXT;
                intersection_dimension INTEGER;
            BEGIN
                -- Buscar overlaps usando ST_Relate con patrones DE-9IM específicos
                -- Aplicamos SnapToGrid al milímetro para evitar problemas de precisión
                SELECT {pk_field}::TEXT, 
                       ST_Intersection(NEW.{geom_field}, {geom_field}),
                       ST_Area(ST_Intersection(NEW.{geom_field}, {geom_field})),
                       ST_Dimension(ST_Intersection(NEW.{geom_field}, {geom_field}))
                INTO conflicting_id, overlap_geom, overlap_area, intersection_dimension
                FROM {full_table_name}
                WHERE ST_DWithin(ST_Transform(NEW.{geom_field}, 3857), ST_Transform({geom_field}, 3857), radio) -- Optimización espacial
                  AND (
                                              -- Patrón para overlaps reales (interior-interior se intersecta): 'T*T***T**'
                       ST_Relate(ST_SnapToGrid(NEW.{geom_field}, {snap_precision}), ST_SnapToGrid({geom_field}, {snap_precision}), 'T*T***T**')
                        OR
                        -- Patrón para geometrías idénticas: 'T*F**FFF*' (igualdad)
                       ST_Relate(ST_SnapToGrid(NEW.{geom_field}, {snap_precision}), ST_SnapToGrid({geom_field}, {snap_precision}), 'T*F**FFF*')
                  )
                  AND {pk_field} <> NEW.{pk_field} -- Excluir el registro actual en caso de actualización
                LIMIT 1;

                -- Si hay solapamiento real, generar mensaje de error detallado
                IF conflicting_id IS NOT NULL THEN
                    -- Obtener la geometría completa del solape como GEOJSON en EPSG:4326
                    SELECT ST_AsGeoJSON(ST_Transform(overlap_geom, 4326))
                    INTO overlap_geojson;
                    
                    -- Construir mensaje de error estructurado con GEOJSON
                    error_message := 'TOPOLOGY ERROR: Geometry overlaps with existing feature. ' ||
                                    'Overlap area: ' || COALESCE(overlap_area::TEXT, 'NULL') || ' sq units. ' ||
                                    'Overlap geometry: ##' || COALESCE(overlap_geojson, 'NULL') || '##.';
                    
                    -- Lanzar excepción con información detallada
                    RAISE EXCEPTION '%', error_message;
                END IF;

                -- Si no hay solapamiento, continuar con la inserción/actualización
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """
            
            # SQL para trigger
            trigger_sql = f"""
            CREATE TRIGGER {trigger_name}
            BEFORE INSERT OR UPDATE ON {full_table_name}
            FOR EACH ROW
            EXECUTE FUNCTION {function_name}();
            """
            
            return {
                'function_sql': function_sql,
                'trigger_sql': trigger_sql,
                'function_name': function_name,
                'function_name_simple': function_name_simple,
                'trigger_name': trigger_name,
                'table_name': full_table_name,
                'schema': schema,
                'pk_field': pk_field,
                'geom_field': geom_field
            }
        
        elif rule_type == "must_not_have_gaps":
            # SQL para función MUST NOT HAVE GAPS
            function_sql = f"""
            CREATE OR REPLACE FUNCTION {function_name}()
            RETURNS TRIGGER AS $$
            DECLARE
                bounding_geom geometry;
                bounding_line geometry;
                area_unida geometry;
                area_resto geometry;
                area_final geometry;
                geometry_3857 geometry;
                radio INTEGER := 500;
                gap_geom geometry;
                gap_geojson TEXT;
                error_message TEXT;
            BEGIN
                -- Transformar la nueva geometría a 3857
                geometry_3857 := ST_Transform(NEW.{geom_field}, 3857);

                -- Paso 1: Generar el Convex Hull de los polígonos existentes dentro del radio (incluyendo el nuevo)
                -- Trabajamos en el SRID original para evitar mezclas
                SELECT ST_ConvexHull(ST_Union(geom_union)) INTO bounding_geom
                FROM (
                    SELECT {geom_field} as geom_union FROM {full_table_name} 
                    WHERE ST_DWithin(ST_Transform({geom_field}, 3857), geometry_3857, radio)
                    AND {pk_field} <> NEW.{pk_field} -- se excluye por si es una actualizacion solo contar con la nueva modificación
                    UNION ALL
                    SELECT NEW.{geom_field} as geom_union
                ) AS combined_geoms;

                -- Paso 2: Generar el límite (línea) del Convex Hull
                bounding_line := ST_Boundary(bounding_geom);
                
                -- Paso 3: Unir todas las geometrías existentes dentro del radio
                SELECT ST_Union({geom_field}) INTO area_unida
                FROM {full_table_name}
                WHERE ST_DWithin(ST_Transform({geom_field}, 3857), geometry_3857, radio)
                AND {pk_field} <> NEW.{pk_field};

                -- Restar del Bounding Box la geometría unida y la nueva geometría
                -- Usar ST_GeomFromText con el mismo SRID que bounding_geom
                area_resto := ST_Difference(bounding_geom, COALESCE(area_unida, ST_SetSRID(ST_GeomFromText('POLYGON EMPTY'), ST_SRID(bounding_geom))));
                IF area_resto IS NOT NULL THEN
                    area_resto := ST_Difference(area_resto, NEW.{geom_field});
                END IF;

                -- Paso 4: Descartar los polígonos que toquen el límite del Bounding Box
                WITH desempacados AS (
                    SELECT (ST_Dump(area_resto)).geom AS geometry
                )
                SELECT ST_Union(geometry) INTO area_final
                FROM desempacados
                WHERE NOT ST_Touches(geometry, bounding_line);

                -- Paso 5: Comprobar si alguna de las geometrías restantes interseca con el nuevo polígono con un buffer de 1 mm
                -- El buffer es necesario porque el Touches no detecta nada por cuestiones decimales.
                -- Trabajamos todo en 3857 para las operaciones de buffer y distancia
                SELECT ST_Transform(remaining_geom.geom, ST_SRID(NEW.{geom_field})) INTO gap_geom
                FROM (
                    SELECT (ST_Dump(area_final)).geom AS geom
                ) AS remaining_geom
                WHERE ST_Intersects(
                    ST_Transform(remaining_geom.geom, 3857), -- Convertir las geometrías restantes a 3857
                    ST_Buffer(geometry_3857, 0.001) -- Buffer de 1 mm en 3857
                )
                LIMIT 1;

                -- Si se detecta un hueco, generar mensaje de error con GeoJSON
                IF gap_geom IS NOT NULL THEN
                    -- Obtener la geometría del hueco como GEOJSON en EPSG:4326
                    SELECT ST_AsGeoJSON(ST_Transform(gap_geom, 4326))
                    INTO gap_geojson;
                    
                    -- Construir mensaje de error estructurado con GEOJSON
                    error_message := 'TOPOLOGY ERROR: New geometry creates a gap in the layer coverage. ' ||
                                    'Gap geometry: ##' || COALESCE(gap_geojson, 'NULL') || '##.';
                    
                    -- Lanzar excepción con información detallada
                    RAISE EXCEPTION '%', error_message;
                END IF;

                -- Si no hay huecos, continuar con la operación
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """
            
            # SQL para trigger
            trigger_sql = f"""
            CREATE TRIGGER {trigger_name}
            BEFORE INSERT OR UPDATE ON {full_table_name}
            FOR EACH ROW
            EXECUTE FUNCTION {function_name}();
            """
            
            return {
                'function_sql': function_sql,
                'trigger_sql': trigger_sql,
                'function_name': function_name,
                'function_name_simple': function_name_simple,
                'trigger_name': trigger_name,
                'table_name': full_table_name,
                'schema': schema,
                'pk_field': pk_field,
                'geom_field': geom_field
            }
        
        # Aquí se pueden añadir más tipos de reglas en el futuro
        
        elif rule_type == "must_not_overlap_with":
            # SQL para función MUST NOT OVERLAP WITH
            overlap_geom_fields = kwargs.get('overlap_geom_fields', {})
            
            if not overlap_geom_fields:
                logger.error(f"overlap_geom_fields es requerido para la regla must_not_overlap_with")
                return None
            
            # Construir la consulta dinámica para cada tabla en overlap_layers
            overlap_checks = []
            for layer_name, overlap_geom_field in overlap_geom_fields.items():
                overlap_check = f"""
                    -- Comprobar solapamiento con {layer_name}
                    SELECT 1
                    INTO result
                    FROM {layer_name}
                    WHERE ST_DWithin(ST_Transform(NEW.{geom_field}, 3857), ST_Transform({overlap_geom_field}, 3857), radio) 
                      AND ST_Overlaps(ST_SnapToGrid(NEW.{geom_field}, {snap_precision}), ST_SnapToGrid({overlap_geom_field}, {snap_precision}))
                    LIMIT 1;

                    -- Si encuentra un solapamiento, lanza una excepción
                    IF result = 1 THEN
                        -- Obtener geometría del solapamiento para el error
                        SELECT ST_AsGeoJSON(ST_Transform(ST_Intersection(NEW.{geom_field}, {overlap_geom_field}), 4326))
                        INTO overlap_geojson
                        FROM {layer_name}
                        WHERE ST_DWithin(ST_Transform(NEW.{geom_field}, 3857), ST_Transform({overlap_geom_field}, 3857), radio) 
                          AND ST_Overlaps(ST_SnapToGrid(NEW.{geom_field}, {snap_precision}), ST_SnapToGrid({overlap_geom_field}, {snap_precision}))
                        LIMIT 1;
                        
                        error_message := 'TOPOLOGY ERROR: Geometry overlaps with layer ' || '{layer_name.replace(".", "-")}' || '. ' ||
                                        'Overlap geometry: ##' || COALESCE(overlap_geojson, 'NULL') || '##.';
                        RAISE EXCEPTION '%', error_message;
                    END IF;
                    
                    -- Resetear result para la siguiente verificación
                    result := NULL;"""
                overlap_checks.append(overlap_check)
            
            # Unir todas las verificaciones
            all_overlap_checks = ''.join(overlap_checks)
            
            function_sql = f"""
            CREATE OR REPLACE FUNCTION {function_name}()
            RETURNS TRIGGER AS
            $$
            DECLARE
                result INTEGER;  -- Variable para almacenar el resultado de la consulta
                radio INTEGER := 1; -- Definir el radio como variable
                snap_precision NUMERIC := {snap_precision};
                error_message TEXT;
                overlap_geojson TEXT;
            BEGIN
                {all_overlap_checks}

                -- Si no hay solapamiento, continuar con la inserción/actualización
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """
            
            # SQL para trigger
            trigger_sql = f"""
            CREATE TRIGGER {trigger_name}
            BEFORE INSERT OR UPDATE ON {full_table_name}
            FOR EACH ROW
            EXECUTE FUNCTION {function_name}();
            """
            
            return {
                'function_sql': function_sql,
                'trigger_sql': trigger_sql,
                'function_name': function_name,
                'function_name_simple': function_name_simple,
                'trigger_name': trigger_name,
                'table_name': full_table_name,
                'schema': schema,
                'pk_field': pk_field,
                'geom_field': geom_field,
                'overlap_geom_fields': overlap_geom_fields
            }
        
        elif rule_type == "must_be_covered_by":
            # SQL para función MUST BE COVERED BY
            covered_by_layer = kwargs.get('covered_by_layer')
            covered_geom_field = kwargs.get('covered_geom_field')
            
            if not covered_by_layer:
                logger.error(f"covered_by_layer es requerido para la regla must_be_covered_by")
                return None
            
            if not covered_geom_field:
                logger.error(f"covered_geom_field es requerido para la regla must_be_covered_by")
                return None
            
            # Parsear schema.tabla de la capa de cobertura
            if '.' not in covered_by_layer:
                logger.error(f"covered_by_layer debe tener formato schema.tabla: {covered_by_layer}")
                return None
            
            function_sql = f"""
            CREATE OR REPLACE FUNCTION {function_name}()
            RETURNS TRIGGER AS
            $$
            DECLARE
                radio INTEGER := 1; -- Definir el radio como variable
                snap_precision NUMERIC := {snap_precision};
                error_message TEXT;
                uncovered_geom GEOMETRY;
                uncovered_geojson TEXT;
                covering_union GEOMETRY;
            BEGIN
                -- Obtener la unión de todas las geometrías que podrían cubrir la nueva geometría
                SELECT ST_Union({covered_geom_field})
                INTO covering_union
                FROM {covered_by_layer}
                WHERE ST_DWithin(ST_Transform(NEW.{geom_field}, 3857), ST_Transform({covered_geom_field}, 3857), radio)
                  AND ST_Intersects(ST_SnapToGrid({covered_geom_field}, {snap_precision}), ST_SnapToGrid(NEW.{geom_field}, {snap_precision}));

                -- Si hay geometrías que intersectan, calcular la parte no cubierta
                IF covering_union IS NOT NULL THEN
                    -- Calcular la diferencia: parte de la nueva geometría que NO está cubierta
                    uncovered_geom := ST_Difference(NEW.{geom_field}, covering_union);
                    
                    -- Si queda alguna parte sin cubrir, es un error
                    IF uncovered_geom IS NOT NULL AND NOT ST_IsEmpty(uncovered_geom) THEN
                        -- Obtener la geometría no cubierta como GEOJSON en EPSG:4326
                        SELECT ST_AsGeoJSON(ST_Transform(uncovered_geom, 4326))
                        INTO uncovered_geojson;
                        
                        -- Construir mensaje de error estructurado con GEOJSON
                        error_message := 'TOPOLOGY ERROR: Geometry is not covered by any feature in the reference layer. ' ||
                                        'Uncovered geometry: ##' || COALESCE(uncovered_geojson, 'NULL') || '##.';
                        
                        -- Lanzar excepción con información detallada
                        RAISE EXCEPTION '%', error_message;
                    END IF;
                ELSE
                    -- No hay geometrías que intersecten, toda la nueva geometría está sin cubrir
                    SELECT ST_AsGeoJSON(ST_Transform(NEW.{geom_field}, 4326))
                    INTO uncovered_geojson;
                    
                    -- Construir mensaje de error estructurado con GEOJSON
                    error_message := 'TOPOLOGY ERROR: Geometry is not covered by any feature in the reference layer. ' ||
                                    'Uncovered geometry: ##' || COALESCE(uncovered_geojson, 'NULL') || '##.';
                    
                    -- Lanzar excepción con información detallada
                    RAISE EXCEPTION '%', error_message;
                END IF;

                -- Si la geometría está completamente cubierta, continuar con la inserción/actualización
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """
            
            # SQL para trigger
            trigger_sql = f"""
            CREATE TRIGGER {trigger_name}
            BEFORE INSERT OR UPDATE ON {full_table_name}
            FOR EACH ROW
            EXECUTE FUNCTION {function_name}();
            """
            
            return {
                'function_sql': function_sql,
                'trigger_sql': trigger_sql,
                'function_name': function_name,
                'function_name_simple': function_name_simple,
                'trigger_name': trigger_name,
                'table_name': full_table_name,
                'schema': schema,
                'pk_field': pk_field,
                'geom_field': geom_field,
                'covered_by_layer': covered_by_layer,
                'covered_geom_field': covered_geom_field
            }
        
        elif rule_type == "must_be_contiguous":
            # SQL para función MUST BE CONTIGUOUS - Tu lógica original exacta
            contiguous_tolerance = kwargs.get('contiguous_tolerance', 1.0)  # Default del modelo
            
            function_sql = f"""
            CREATE OR REPLACE FUNCTION {function_name}()
            RETURNS TRIGGER AS
            $$
            DECLARE
                tolerance NUMERIC := {contiguous_tolerance};
                snap_precision NUMERIC := {snap_precision};
                error_message TEXT;
                problem_geojson TEXT;
                valid_vertex_count INTEGER := 0;
                vertex_3857 geometry;
                min_distance NUMERIC;
                vertex_counter INTEGER := 0;
                total_points INTEGER;
                closest_invalid_vertex geometry;
                closest_invalid_distance NUMERIC := 999999;
            BEGIN
                -- PASO 1: ¿Toca por borde en SRID 3857? → VÁLIDO inmediatamente
                IF EXISTS (
                    SELECT 1
                    FROM {full_table_name}
                    WHERE ST_Relate(
                        ST_SnapToGrid(ST_Transform(NEW.{geom_field}, 3857), {snap_precision}),
                        ST_SnapToGrid(ST_Transform({geom_field}, 3857), {snap_precision}), 
                        'F***1****') -- Toca por borde
                    AND {pk_field} <> NEW.{pk_field}
                ) THEN
                    RETURN NEW;
                END IF;

                -- PASO 2: Contar vértices dentro de tolerancia (en metros) - SIN DUPLICADOS
                -- Contar total de puntos
                SELECT ST_NPoints(ST_Transform(NEW.{geom_field}, 3857)) INTO total_points;
                
                FOR vertex_3857 IN
                    SELECT (ST_DumpPoints(ST_Transform(NEW.{geom_field}, 3857))).geom
                LOOP
                    vertex_counter := vertex_counter + 1;
                    
                    -- Saltar el último punto (que es igual al primero)
                    IF vertex_counter >= total_points THEN
                        EXIT;
                    END IF;
                    
                    -- Calcular distancia mínima de este vértice a CUALQUIER geometría existente
                    SELECT MIN(ST_Distance(vertex_3857, ST_Transform({geom_field}, 3857)))
                    INTO min_distance
                    FROM {full_table_name}
                    WHERE {pk_field} <> NEW.{pk_field};
                    
                    -- Si está dentro de tolerancia, contarlo
                    IF min_distance IS NOT NULL AND min_distance <= tolerance THEN
                        valid_vertex_count := valid_vertex_count + 1;
                        
                        -- Optimización: si ya tenemos 2, no necesitamos más
                        IF valid_vertex_count >= 2 THEN
                            RETURN NEW;
                        END IF;
                    ELSE
                        -- Este vértice NO cumple tolerancia, ¿es el más cercano a cumplirla?
                        IF min_distance IS NOT NULL AND min_distance < closest_invalid_distance THEN
                            closest_invalid_distance := min_distance;
                            closest_invalid_vertex := vertex_3857;
                        END IF;
                    END IF;
                END LOOP;
                
                -- PASO 3: No hay suficientes vértices cercanos → ERROR
                -- Devolver el vértice que NO cumple tolerancia pero está más cerca de cumplirla
                IF closest_invalid_vertex IS NOT NULL THEN
                    SELECT ST_AsGeoJSON(ST_Transform(closest_invalid_vertex, 4326))
                    INTO problem_geojson;
                    
                    error_message := 'TOPOLOGY ERROR: Geometry is not contiguous. Only ' || valid_vertex_count || 
                                    ' vertices within tolerance (' || tolerance || 'm), minimum required: 2. ' ||
                                    'Closest vertex that violates tolerance (distance: ' || ROUND(closest_invalid_distance, 2) || 'm): ##' || 
                                    COALESCE(problem_geojson, 'NULL') || '##.';
                ELSE
                    -- Fallback al centroide si no se encontró ningún vértice inválido
                    SELECT ST_AsGeoJSON(ST_Transform(ST_Centroid(NEW.{geom_field}), 4326))
                    INTO problem_geojson;
                    
                    error_message := 'TOPOLOGY ERROR: Geometry is not contiguous. Only ' || valid_vertex_count || 
                                    ' vertices within tolerance (' || tolerance || 'm), minimum required: 2. ' ||
                                    'Geometry centroid: ##' || COALESCE(problem_geojson, 'NULL') || '##.';
                END IF;
                
                RAISE EXCEPTION '%', error_message;
            END;
            $$ LANGUAGE plpgsql;

            """
            
            # SQL para trigger
            trigger_sql = f"""
            CREATE TRIGGER {trigger_name}
            BEFORE INSERT OR UPDATE ON {full_table_name}
            FOR EACH ROW
            EXECUTE FUNCTION {function_name}();
            """
            
            return {
                'function_sql': function_sql,
                'trigger_sql': trigger_sql,
                'function_name': function_name,
                'function_name_simple': function_name_simple,
                'trigger_name': trigger_name,
                'table_name': full_table_name,
                'schema': schema,
                'pk_field': pk_field,
                'geom_field': geom_field,
                'contiguous_tolerance': contiguous_tolerance
            }
        
        else:
            logger.warning(f"Tipo de regla topológica no implementada: {rule_type}")
            return None
            
    except Exception as e:
        logger.error(f"Error generando SQL para trigger {rule_type}: {str(e)}")
        return None

def _apply_topology_trigger(layer, rule_type, **kwargs):
    """
    Aplica un trigger topológico a una capa
    """
    try:
        # Obtener conexión a la base de datos
        i, source_name, schema = layer.get_db_connection()
        
        with i as conn:
            # Para la regla must_be_covered_by, obtener el campo geometría de la tabla de cobertura
            if rule_type == "must_be_covered_by":
                covered_by_layer = kwargs.get('covered_by_layer')
                
                if covered_by_layer and '.' in covered_by_layer:
                    covered_schema, covered_table = covered_by_layer.split('.', 1)
                    
                    covered_geom_columns = conn.get_geometry_columns(covered_table, covered_schema)
                    
                    if not covered_geom_columns:
                        logger.error(f"No se encontró campo de geometría para la tabla de cobertura {covered_by_layer}")
                        return False
                    
                    kwargs['covered_geom_field'] = covered_geom_columns[0]
                    logger.info(f"Campo geometría de tabla de cobertura {covered_by_layer}: '{covered_geom_columns[0]}'")
            
            # Para la regla must_not_overlap_with, obtener los campos geometría de las tablas objetivo
            elif rule_type == "must_not_overlap_with":
                overlap_layers = kwargs.get('overlap_layers', [])
                logger.info(f"Processing must_not_overlap_with for layer {layer.id} with overlap_layers: {overlap_layers}")
                overlap_geom_fields = {}
                
                for layer_name in overlap_layers:
                    logger.info(f"Processing overlap layer: {layer_name}")
                    if '.' in layer_name:
                        overlap_schema, overlap_table = layer_name.split('.', 1)
                        logger.info(f"Split layer {layer_name} into schema: {overlap_schema}, table: {overlap_table}")
                        
                        overlap_geom_columns = conn.get_geometry_columns(overlap_table, overlap_schema)
                        logger.info(f"Found geometry columns for {layer_name}: {overlap_geom_columns}")
                        
                        if not overlap_geom_columns:
                            logger.error(f"No se encontró campo de geometría para la tabla {layer_name}")
                            return False
                        
                        overlap_geom_fields[layer_name] = overlap_geom_columns[0]
                        logger.info(f"Campo geometría de tabla {layer_name}: '{overlap_geom_columns[0]}'")
                    else:
                        logger.error(f"overlap_layer debe tener formato schema.tabla: {layer_name}")
                        return False
                
                logger.info(f"Final overlap_geom_fields: {overlap_geom_fields}")
                kwargs['overlap_geom_fields'] = overlap_geom_fields
            
            trigger_info = _generate_topology_trigger_sql(rule_type, layer, **kwargs)
            if not trigger_info:
                return False
            
            # Establecer search_path para asegurar el esquema correcto
            conn.cursor.execute(f"SET search_path TO {trigger_info['schema']}, public;")
            
            # Primero eliminar trigger y función si existen (para evitar conflictos)
            _remove_topology_trigger_internal(conn, trigger_info)
            
            # Crear función
            conn.cursor.execute(trigger_info['function_sql'])
            logger.info(f"Función topológica creada: {trigger_info['function_name']}")
            
            # Crear trigger
            conn.cursor.execute(trigger_info['trigger_sql'])
            logger.info(f"Trigger topológico creado: {trigger_info['trigger_name']} en {trigger_info['table_name']}")
            
            return True
            
    except Exception as e:
        logger.error(f"Error aplicando trigger {rule_type} para capa {layer.id}: {str(e)}")
        return False

def _remove_topology_trigger(layer, rule_type, **kwargs):
    """
    Elimina un trigger topológico de una capa
    """
    try:
        # Para eliminación, solo necesitamos los nombres, no toda la generación de SQL
        trigger_info = _get_topology_trigger_names(layer, rule_type)
        if not trigger_info:
            return False
        
        # Obtener conexión a la base de datos
        i, source_name, schema = layer.get_db_connection()
        
        with i as conn:
            # Establecer search_path para asegurar el esquema correcto
            conn.cursor.execute(f"SET search_path TO {trigger_info['schema']}, public;")
            return _remove_topology_trigger_internal(conn, trigger_info)
            
    except Exception as e:
        logger.error(f"Error eliminando trigger {rule_type} para capa {layer.id}: {str(e)}")
        return False

def _remove_topology_trigger_internal(conn, trigger_info):
    """
    Función interna para eliminar trigger y función
    """
    try:
        # Eliminar trigger si existe
        drop_trigger_sql = f"DROP TRIGGER IF EXISTS {trigger_info['trigger_name']} ON {trigger_info['table_name']};"
        conn.cursor.execute(drop_trigger_sql)
        logger.info(f"Trigger eliminado: {trigger_info['trigger_name']}")
        
        # Eliminar función si existe
        drop_function_sql = f"DROP FUNCTION IF EXISTS {trigger_info['function_name']}();"
        conn.cursor.execute(drop_function_sql)
        logger.info(f"Función eliminada: {trigger_info['function_name']}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error en _remove_topology_trigger_internal: {str(e)}")
        return False

def _apply_topology_triggers_for_layer(layer, topology_config):
    """
    Aplica o elimina triggers topológicos según la configuración de la capa
    """
    try:
        # MUST NOT OVERLAPS
        if topology_config.no_overlap:
            success = _apply_topology_trigger(layer, "must_not_overlaps")
            if not success:
                logger.error(f"Fallo al aplicar trigger must_not_overlaps para capa {layer.id}")
        else:
            success = _remove_topology_trigger(layer, "must_not_overlaps")
            if not success:
                logger.warning(f"Fallo al eliminar trigger must_not_overlaps para capa {layer.id}")
        
        # MUST NOT HAVE GAPS
        if topology_config.no_gaps:
            success = _apply_topology_trigger(layer, "must_not_have_gaps")
            if not success:
                logger.error(f"Fallo al aplicar trigger must_not_have_gaps para capa {layer.id}")
        else:
            success = _remove_topology_trigger(layer, "must_not_have_gaps")
            if not success:
                logger.warning(f"Fallo al eliminar trigger must_not_have_gaps para capa {layer.id}")
        
        # Aquí se pueden añadir más reglas en el futuro:
        
        # MUST BE COVERED BY
        if topology_config.must_be_covered_by:
            if topology_config.covered_by_layer:
                success = _apply_topology_trigger(layer, "must_be_covered_by", covered_by_layer=topology_config.covered_by_layer)
                if not success:
                    logger.error(f"Fallo al aplicar trigger must_be_covered_by para capa {layer.id}")
            else:
                logger.warning(f"No se puede aplicar trigger must_be_covered_by para capa {layer.id}: covered_by_layer no especificado")
        else:
            success = _remove_topology_trigger(layer, "must_be_covered_by")
            if not success:
                logger.warning(f"Fallo al eliminar trigger must_be_covered_by para capa {layer.id}")
        
        # MUST NOT OVERLAP WITH
        if topology_config.must_not_overlap_with:
            logger.info(f"Applying must_not_overlap_with rule for layer {layer.id}")
            if topology_config.overlap_layers:
                logger.info(f"Overlap layers configured: {topology_config.overlap_layers}")
                success = _apply_topology_trigger(layer, "must_not_overlap_with", overlap_layers=topology_config.overlap_layers)
                if not success:
                    logger.error(f"Fallo al aplicar trigger must_not_overlap_with para capa {layer.id}")
                else:
                    logger.info(f"Successfully applied must_not_overlap_with trigger for layer {layer.id}")
            else:
                logger.warning(f"No se puede aplicar trigger must_not_overlap_with para capa {layer.id}: overlap_layers no especificado")
        else:
            logger.info(f"Removing must_not_overlap_with rule for layer {layer.id}")
            success = _remove_topology_trigger(layer, "must_not_overlap_with")
            if not success:
                logger.warning(f"Fallo al eliminar trigger must_not_overlap_with para capa {layer.id}")
            else:
                logger.info(f"Successfully removed must_not_overlap_with trigger for layer {layer.id}")
        
        # MUST BE CONTIGUOUS
        if topology_config.must_be_contiguous:
            success = _apply_topology_trigger(layer, "must_be_contiguous", 
                                            contiguous_tolerance=topology_config.contiguous_tolerance)
            if not success:
                logger.error(f"Fallo al aplicar trigger must_be_contiguous para capa {layer.id}")
        else:
            success = _remove_topology_trigger(layer, "must_be_contiguous")
            if not success:
                logger.warning(f"Fallo al eliminar trigger must_be_contiguous para capa {layer.id}")
        
        # etc... más reglas en el futuro
        
        logger.info(f"Triggers topológicos actualizados para capa {layer.id}")
        
    except Exception as e:
        logger.error(f"Error aplicando triggers topológicos para capa {layer.id}: {str(e)}")

def _save_layer_topology_rules(request, layer):
    """
    Guarda las reglas topológicas desde request.POST (formulario) o request.body (JSON API)
    
    Args:
        request: HttpRequest
        layer: La instancia de Layer
    """
    try:
        # Detectar automáticamente si los datos vienen del formulario o de la API JSON
        if 'topology_no_overlap' in request.POST:
            # Datos vienen del formulario (layer_config.html)
            data = {
                'no_overlap': request.POST.get('topology_no_overlap', 'false').lower() == 'true',
                'no_gaps': request.POST.get('topology_no_gaps', 'false').lower() == 'true',
                'must_be_covered_by': request.POST.get('topology_must_be_covered_by', 'false').lower() == 'true',
                'covered_by_layer': request.POST.get('topology_covered_by_layer', '').strip(),
                'must_not_overlap_with': request.POST.get('topology_must_not_overlap_with', 'false').lower() == 'true',
                'must_be_contiguous': request.POST.get('topology_must_be_contiguous', 'false').lower() == 'true',
                'contiguous_tolerance': float(request.POST.get('topology_contiguous_tolerance', '1.0'))
            }
            
            # Parsear overlap_layers de JSON
            overlap_layers_json = request.POST.get('topology_overlap_layers', '[]')
            logger.info(f"DEBUG Frontend overlap_layers_json: '{overlap_layers_json}'")
            try:
                data['overlap_layers'] = json.loads(overlap_layers_json)
                logger.info(f"DEBUG Frontend parsed overlap_layers: {data['overlap_layers']}")
            except json.JSONDecodeError:
                logger.error(f"DEBUG Frontend JSON decode error for: '{overlap_layers_json}'")
                data['overlap_layers'] = []
                
            # Para formularios, no lanzar excepción que interrumpa el guardado principal
            raise_exceptions = False
        else:
            # Datos vienen de la API JSON (request.body)
            try:
                data = json.loads(request.body)
                logger.info(f"DEBUG API JSON data: {data}")
                logger.info(f"DEBUG API overlap_layers: {data.get('overlap_layers', [])}")
            except json.JSONDecodeError:
                if hasattr(request, 'body') and request.body:
                    raise ValueError("Invalid JSON data in request body")
                else:
                    return  # No hay datos topológicos en el request
            
            # Para API, lanzar excepciones para dar feedback al frontend
            raise_exceptions = True
        
        # Extraer datos (normalizados)
        no_overlap = data.get('no_overlap', False)
        no_gaps = data.get('no_gaps', False)
        must_be_covered_by = data.get('must_be_covered_by', False)
        covered_by_layer = data.get('covered_by_layer', '').strip()
        must_not_overlap_with = data.get('must_not_overlap_with', False)
        overlap_layers = data.get('overlap_layers', [])
        must_be_contiguous = data.get('must_be_contiguous', False)
        contiguous_tolerance = float(data.get('contiguous_tolerance', 1.0))
        
        # Función auxiliar para convertir formato datastore:tabla a schema.tabla
        def convert_layer_format(layer_identifier):
            """
            Convierte de formato 'datastore:tabla' a 'schema.tabla'
            """
            logger.info(f"DEBUG convert_layer_format: Input = '{layer_identifier}'")
            
            if not layer_identifier or ':' not in layer_identifier:
                logger.info(f"DEBUG convert_layer_format: No conversion needed, returning = '{layer_identifier}'")
                return layer_identifier
            
            try:
                datastore_name, table_name = layer_identifier.split(':', 1)
                logger.info(f"DEBUG convert_layer_format: Split into datastore='{datastore_name}', table='{table_name}'")
                
                # Buscar el datastore para obtener el schema
                target_datastore = Datastore.objects.filter(name=datastore_name).first()
                logger.info(f"DEBUG convert_layer_format: Found datastore = {target_datastore}")
                
                if target_datastore:
                    params = json.loads(target_datastore.connection_params)
                    schema = params.get('schema', 'public')
                    result = f"{schema}.{table_name}"
                    logger.info(f"DEBUG convert_layer_format: Schema='{schema}', Final result = '{result}'")
                    return result
                else:
                    # Si no se encuentra el datastore, devolver el original
                    logger.warning(f"DEBUG convert_layer_format: Datastore '{datastore_name}' not found, returning original = '{layer_identifier}'")
                    return layer_identifier
            except Exception as e:
                logger.error(f"DEBUG convert_layer_format: Error convirtiendo formato de capa {layer_identifier}: {str(e)}")
                return layer_identifier
        
        # Preparar los datos limpios, convirtiendo a formato schema.tabla si es necesario
        covered_by_layer_clean = ''
        if must_be_covered_by and covered_by_layer:
            if '.' in covered_by_layer:
                # Ya está en formato schema.tabla
                covered_by_layer_clean = covered_by_layer
            elif ':' in covered_by_layer:
                # Convertir de datastore:tabla a schema.tabla
                covered_by_layer_clean = convert_layer_format(covered_by_layer)
            else:
                logger.warning(f"Invalid covered_by_layer format: {covered_by_layer}")
        
        # Convertir cada capa en la lista de overlap_layers
        overlap_layers_clean = []
        if must_not_overlap_with and overlap_layers:
            logger.info(f"Processing overlap_layers for layer {layer.id}: {overlap_layers}")
            for layer_ref in overlap_layers:
                if isinstance(layer_ref, str):
                    if '.' in layer_ref:
                        # Ya está en formato schema.tabla
                        overlap_layers_clean.append(layer_ref)
                        logger.info(f"Added overlap layer (schema.tabla format): {layer_ref}")
                    elif ':' in layer_ref:
                        # Convertir de datastore:tabla a schema.tabla
                        converted = convert_layer_format(layer_ref)
                        if converted:
                            overlap_layers_clean.append(converted)
                            logger.info(f"Converted overlap layer from {layer_ref} to {converted}")
                        else:
                            logger.error(f"Failed to convert overlap layer format: {layer_ref}")
                    else:
                        logger.warning(f"Invalid overlap layer format: {layer_ref}")
                else:
                    logger.warning(f"Invalid overlap layer type: {type(layer_ref)}")
            logger.info(f"Final overlap_layers_clean for layer {layer.id}: {overlap_layers_clean}")
        
        # Crear o actualizar la configuración de topología
        topology_config, created = LayerTopologyConfiguration.objects.get_or_create(
            layer=layer,
            defaults={
                'no_overlap': no_overlap,
                'no_gaps': no_gaps,
                'must_be_covered_by': must_be_covered_by,
                'covered_by_layer': covered_by_layer_clean,
                'must_not_overlap_with': must_not_overlap_with,
                'overlap_layers': overlap_layers_clean,
                'must_be_contiguous': must_be_contiguous,
                'contiguous_tolerance': contiguous_tolerance
            }
        )
        
        if not created:
            # Actualizar configuración existente
            topology_config.no_overlap = no_overlap
            topology_config.no_gaps = no_gaps
            topology_config.must_be_covered_by = must_be_covered_by
            topology_config.covered_by_layer = covered_by_layer_clean
            topology_config.must_not_overlap_with = must_not_overlap_with
            topology_config.overlap_layers = overlap_layers_clean
            topology_config.must_be_contiguous = must_be_contiguous
            topology_config.contiguous_tolerance = contiguous_tolerance
            topology_config.save()
        
        logger.info(f"Topology rules saved for layer {layer.id}: {topology_config.get_active_rules_count()} active rules")
        
        # Aplicar o eliminar triggers topológicos según la configuración
        _apply_topology_triggers_for_layer(layer, topology_config)
        
        return topology_config
        
    except Exception as e:
        logger.error(f"Error saving topology rules for layer {layer.id}: {str(e)}")
        if raise_exceptions:
            raise
        # Para formularios, no lanzar excepción para no interrumpir el guardado principal




@login_required()
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def layer_config(request, layer_id):
    redirect_to_layergroup = request.GET.get('redirect')
    layer = Layer.objects.get(id=int(layer_id))
    if not utils.can_manage_layer(request, layer):
        return forbidden_view(request)
    redirect_to_layergroup = request.GET.get('redirect')
    from_redirect = request.GET.get('from_redirect')
    project_id = request.GET.get('project_id')
    layergroup_id = request.GET.get('layergroup_id')

    if request.method == 'POST':
        i, params = layer.datastore.get_db_connection()
        with i as c:
            is_view = c.is_view(layer.datastore.name, layer.source_name)
        old_conf = ast.literal_eval(layer.conf) if layer.conf else {}

        conf = {
            "featuretype": old_conf.get('featuretype', {})
            }
        fields = []
        counter = int(request.POST.get('counter', 0))
        
        existing_fields = {}
        if 'fields' in old_conf:
            for old_field in old_conf['fields']:
                existing_fields[old_field.get('name', '')] = old_field
        
        for i in range(1, counter+1):
            field = {}
            field['name'] = request.POST.get('field-name-' + str(i))
            
            # Preservar gvsigol_type, type_params y field_format de la configuración anterior
            if field['name'] in existing_fields:
                existing_field = existing_fields[field['name']]
                field['gvsigol_type'] = existing_field.get('gvsigol_type', '')
                field['type_params'] = existing_field.get('type_params', {})
                field['field_format'] = existing_field.get('field_format', {})
            
            for id, language in LANGUAGES:
                field['title-'+id] = request.POST.get('field-title-'+id+'-' + str(i), field['name']).strip()
            field['visible'] = False
            if 'field-visible-' + str(i) in request.POST:
                field['visible'] = True
            field['infovisible'] = False
            if 'field-infovisible-' + str(i) in request.POST:
                field['infovisible'] = True
            nullable = (request.POST.get('field-nullable-' + str(i), False) != False)
            _set_field_nullable(layer_id, field['name'], nullable)
            field['nullable'] = nullable
            if not nullable:
                field['mandatory'] = True
            else:
                field['mandatory'] = (request.POST.get('field-mandatory-' + str(i), False) != False)
            field['editable'] = False
            if not is_view and 'field-editable-' + str(i) in request.POST:
                field['editableactive'] = True
                field['editable'] = True
            for control_field in settings.CONTROL_FIELDS:
                if field['name'] == control_field['name']:
                    field['editableactive'] = control_field.get('editableactive', False)
                    field['editable'] = control_field.get('editable', False)
                    field['visible'] = control_field.get('visible', field['visible'])
                    field['mandatory'] = control_field.get('mandatory', field['mandatory'])
                    field['nullable'] = control_field.get('nullable', field['nullable'])
                if  Trigger.objects.filter(layer=layer, field=field['name']).exists():
                    field['editableactive'] = False
                    field['editable'] = False
            fields.append(field)
        conf['fields'] = fields
        try:
            form_groups = json.loads(request.POST.get('form_groups', []))
        except:
            form_groups = None
        form_groups = _parse_form_groups(form_groups, fields)
        conf['form_groups'] = form_groups
        layer.conf = conf
        layer.save()

        # Guardar reglas topológicas si se han enviado
        _save_layer_topology_rules(request, layer)

        if from_redirect:
            query_string = '?redirect=' + from_redirect
        else:
            query_string = ''
        if redirect_to_layergroup:
            layergroup_id = layer.layer_group.id
            if project_id:
                return HttpResponseRedirect(reverse('layergroup_update_with_project', kwargs={'lgid': layergroup_id, 'project_id': project_id}) + query_string)
            else:
                return HttpResponseRedirect(reverse('layergroup_update', kwargs={'lgid': layergroup_id}) + query_string)
        else:
            return redirect('layer_list')
    else:
        available_languages = []
        for lang_id, _ in LANGUAGES:
            available_languages.append(lang_id)
        try:
            i, params = layer.datastore.get_db_connection()
            with i as c:
                is_view = c.is_view(layer.datastore.name, layer.source_name)
        except:
            logger.exception('Error checking layer is_view')
            is_view = False
        try:
            gs = geographic_servers.get_instance().get_server_by_id(layer.datastore.workspace.server.id)
            expose_pks = gs.datastore_check_exposed_pks(layer.datastore)
            lyr_conf = layer.get_config_manager()
            fields = lyr_conf.get_field_viewconf(include_pks=expose_pks)
            form_groups = _parse_form_groups(lyr_conf._conf.get('form_groups', []), fields)
        except:
            logger.exception("Retrieving fields")
            fields = []
            form_groups = []
            is_view = []
        enums = Enumeration.objects.all()
        procedures = []
        disabled_procedures = core_utils.get_setting('GVSIGOL_DISABLED_PROCEDURES', [])
        for procedure in TriggerProcedure.objects.all():
            if not procedure.signature in disabled_procedures:
                procedures.append(procedure)
        data = {
            'layer': layer,
            'layer_id': layer.id,
            'fields': fields,
            'fields_json': json.dumps(fields),
            'form_groups': form_groups,
            'available_languages': LANGUAGES,
            'available_languages_array': available_languages,
            'enumerations': enums,
            'procedures':  procedures,
            'is_view': is_view,
            'redirect_to_layergroup': redirect_to_layergroup,
            'layergroup_id': layergroup_id,
            'project_id': project_id,
            'from_redirect': from_redirect
        }
        return render(request, 'layer_config.html', data)

def _set_field_nullable(layer_id, field_name, nullable):
    """
    Sets a column to NULL or NOT NULL constraint depending on
    "mandatory" parameter. "Mandatory" should be True to set a column
    to NOT NULL and False otherwise
    """
    i, layername, dsname = utils.get_db_connect_from_layer(layer_id)
    try:
        with i as con: # autoclose connection
            con.set_field_nullable(dsname, layername, field_name, nullable)
    except Exception:
        return False
    return True

@login_required()
@require_http_methods(["POST"])
@staff_required
def check_nullable(request):
    layer_id = request.POST['layer_id']
    field_name = request.POST['field_name']
    if not utils.can_manage_layer(request, int(layer_id)):
        return JsonResponse({"response": "Error: not allowed"}, status_code=403)
    i, layername, dsname = utils.get_db_connect_from_layer(layer_id)
    hasnullvalues = i.check_has_null_values(dsname, layername, field_name)
    if(hasnullvalues):
        return utils.get_exception(405, 'The field has null values')
    return HttpResponse('{"response": "ok"}', content_type='application/json')


@login_required()
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
    if not utils.can_manage_layer(request, layer):
        return HttpResponseForbidden('{"response": "error"}', content_type='application/json')

    is_enum, _ = utils.is_field_enumerated(layer, field)
    if is_enum:
        return utils.get_exception(405, 'The field is already enumerated')

    if autogen:
        params = json.loads(layer.datastore.connection_params)
        con = Introspect(database=params['database'], host=params['host'], port=params['port'], user=params['user'], password=params['passwd'])
        schema = params.get('schema', 'public')
        query = sql.SQL("SELECT {field} FROM {schema}.{table} GROUP BY {field}").format(
            field=sql.Identifier(field),
            schema=sql.Identifier(schema),
            table=sql.Identifier(layer_name))
        con.cursor.execute(query, [])
        rows = con.cursor.fetchall()
        enum_table = Enumeration()
        enum_table.name =  layer_name + "_" + field
        enum_table.title = re.sub(r'\w+', lambda m:m.group(0).capitalize(), layer_name) + " " + re.sub(r'\w+', lambda m:m.group(0).capitalize(), field)
        enum_table.created_by = usr
        enum_table.save()
        enum_id = enum_table.id

        item = EnumerationItem()
        item.name = ''
        item.selected = False
        item.order = 0
        item.enumeration_id = enum_id
        item.save()

        i = 1
        for row in rows:
            if(row[0] is not None and row[0] != ''):
                try:
                    item = EnumerationItem()
                    item.name = row[0]
                    item.selected = False
                    item.order = i
                    i = i + 1
                    item.enumeration_id = enum_id
                    item.save()
                except Exception:
                    #Si da un error insertando no se inserta ese elemento pero no se bloquea.
                    #Siempre los pueden añadir a mano si falta alguno
                    pass

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
        ws_name = request.POST['workspace']
        layer_name = request.POST['layer']
        if ":" in layer_name:
            layer_name = layer_name.split(":")[1]
        layer = Layer.objects.get(external=False, name=layer_name, datastore__workspace__name=ws_name)
        if not utils.can_write_layer(request, layer):
            return HttpResponseNotFound("<h1>Permission denied to modify layer: {0}</h1>".format(layer.id))
        tasks.refresh_layer_info.apply_async(args=[layer.id])
        return HttpResponse('{"response": "ok"}', content_type='application/json')
    except Layer.DoesNotExist:
        return HttpResponseNotFound('<h1>Layer not found: {0}</h1>'.format(layer.id))
    except Exception as e:
        logger.exception('Error')
        return HttpResponseNotFound('<h1>Layer not found: {0}</h1>'.format(layer.id))

def _layer_cache_clear(layer_id):
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

@login_required()
@require_POST
@staff_required
def layer_cache_clear(request, layer_id):
    try:
        layer = Layer.objects.get(id=int(layer_id))
        if not utils.can_manage_layer(request, layer):
            return HttpResponseForbidden('{"response": "error"}', content_type='application/json')
        layer_group = LayerGroup.objects.get(id=layer.layer_group.id)
        server = Server.objects.get(id=layer_group.server_id)
        gs = geographic_servers.get_instance().get_server_by_id(server.id)
        if not layer.external:
            _layer_cache_clear(layer_id)
            gs.reload_nodes()
            return HttpResponse('{"response": "ok"}', content_type='application/json')
    except Exception as e:
        error_message = ugettext_lazy('Error clearing cache. Cause: {cause}.').format(cause=str(e))
    else:
        error_message = ugettext_lazy('Not supported.')
    return JsonResponse({"response": "error", "cause": error_message}, status=400)

@login_required()
@require_POST
@staff_required
def layergroup_cache_clear(request, layergroup_id):
    try:
        layergroup = LayerGroup.objects.get(id=int(layergroup_id))
        if not utils.can_manage_layergroup(request.user, layergroup):
            return forbidden_view(request)
        layer_group_cache_clear(layergroup)
        return redirect('layergroup_list')
    except Exception as e:
        error_message = ugettext_lazy('Error clearing cache. Cause: {cause}.').format(cause=str(e))
    return JsonResponse({"response": "error", "cause": error_message}, status=400)

def layer_group_cache_clear(layergroup):
    last = None
    layers = Layer.objects.filter(external=False).filter(layer_group_id=int(layergroup.id))
    for layer in layers:
        if not layer.external:
            _layer_cache_clear(layer.id)
            last = layer

    if last:
        gs = geographic_servers.get_instance().get_server_by_id(last.datastore.workspace.server.id)
        gs.deleteGeoserverLayerGroup(layergroup)

        gs.createOrUpdateGeoserverLayerGroup(layergroup)
        gs.clearLayerGroupCache(layergroup.name)
        gs.reload_nodes()


@login_required()
@staff_required
def layergroup_list(request):
    layergroups_list = utils.get_user_layergroups(request, permissions=LayerGroupRole.PERM_MANAGE)
    project_id = request.GET.get('project_id')
    if project_id is not None:
        layergroups_list = layergroups_list.filter(projectlayergroup__project__id=project_id)
    layergroups_list = layergroups_list.order_by('id').distinct()
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
        'layergroups': layergroups,
        'project_id': project_id
    }
    return render(request, 'layergroup_list.html', response)



@login_required()
@staff_required
def layergroup_add(request):
    return layergroup_add_with_project(request, None)


@login_required()
@staff_required
def layergroup_add_with_project(request, project_id):
    redirect_var = request.GET.get('redirect')
    from_redirect = request.GET.get('from_redirect')
    if redirect_var == 'project-layergroup-list':
        back_url = reverse('layergroup_list') + "?project_id=" + str(project_id)
    elif redirect_var == 'project-update':
        back_url = reverse('project_update', args=[project_id])
    else:
        back_url = reverse('layergroup_list')

    if request.method == 'POST':
        name = request.POST.get('layergroup_name')
        title = request.POST.get('layergroup_title')
        server_id = request.POST.get('layergroup_server_id')
        from_page = request.GET.get('from')

        cached = False
        if 'cached' in request.POST:
            cached = True

        visible = False
        if 'visible' in request.POST:
            visible = True

        assigned_includeinprojects_roles = []
        assigned_manage_roles = []
        for key in request.POST:
            if 'includeinprojects-userrole-' in key:
                assigned_includeinprojects_roles.append(key[len('includeinprojects-userrole-'):])
            elif 'manage-userrole-' in key:
                assigned_manage_roles.append(key[len('manage-userrole-'):])
        roles = utils.get_layergroup_checked_roles_from_user_input(assigned_includeinprojects_roles, assigned_manage_roles)

        if not name:
            message = _('You must enter a name for layer group')
            response = {'message': message, 'servers': list(Server.objects.values()), 'project_id': project_id, 'roles': roles, 'workspaces': list(Workspace.objects.values()), 'back_url': back_url}
            if from_redirect:
                response['redirect'] = from_redirect
            elif redirect_var:
                response['redirect'] = redirect_var
            return render(request, 'layergroup_add.html', response)

        name = name + '_' + ascii_norm_username(request.user.username)
        if _valid_name_regex.search(name) == None:
            message = _("Invalid layer group name: '{value}'. Identifiers must begin with a letter or an underscore (_). Subsequent characters can be letters, underscores or numbers").format(value=name)
            response = {'message': message, 'servers': list(Server.objects.values()), 'project_id': project_id, 'roles': roles, 'workspaces': list(Workspace.objects.values()), 'back_url': back_url}
            if from_redirect:
                response['redirect'] = from_redirect
            elif redirect_var:
                response['redirect'] = redirect_var
            return render(request, 'layergroup_add.html', redirect_var)

        if LayerGroup.objects.filter(name=name).exists():
            message = _('Layer group name already exists')
            response = {'message': message, 'servers': list(Server.objects.values()), 'project_id': project_id, 'roles': roles, 'workspaces': list(Workspace.objects.values()), 'back_url': back_url}
            if from_redirect:
                response['redirect'] = from_redirect
            elif redirect_var:
                response['redirect'] = redirect_var
            return render(request, 'layergroup_add.html', redirect_var)

        layergroup = LayerGroup(
            server_id = server_id,
            name = name,
            title = title,
            cached = cached,
            visible = visible,
            created_by = request.user.username
        )
        layergroup.save()
        utils.set_layergroup_permissions(layergroup, assigned_includeinprojects_roles, assigned_manage_roles)

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


        if redirect_var == 'project-layergroup-list':
            url = reverse('layergroup_list') + "?project_id=" + str(project_id)
            return redirect(url)
        if redirect_var == 'project-update':
            return redirect('project_update', pid=project_id)
        query_string = "?redirect=grouplayer-redirect"
        if from_redirect:
            query_string = query_string + "&from_redirect=" + from_redirect
        if project_id:
            query_string = query_string + "&project_id=" + str(project_id)
        if redirect_var == 'create-layer':
            return HttpResponseRedirect(reverse('layer_create_with_group', kwargs={'layergroup_id': layergroup.id})+query_string)
        if redirect_var == 'import-layer':
            return HttpResponseRedirect(reverse('layer_add_with_group', kwargs={'layergroup_id': layergroup.id})+query_string)
        return redirect('layergroup_list')
    else:
        roles = utils.get_all_user_roles_checked_by_layergroup(None, get_primary_user_role(request))
        response = {
            'servers': list(Server.objects.values()),
            'roles': roles,
            'project_id': project_id,
            'back_url': back_url
        }
        if redirect_var:
            response['redirect'] = redirect_var
        return render(request, 'layergroup_add.html', response)

def layergroup_mapserver_toc(group, toc_string):
    if toc_string != None or toc_string != '':
        layer_ids = toc_string.split(',')
        layer_ids = layer_ids[::-1]
        layers_dict = {}
        last = None
        i=0
        for layer_id in layer_ids:
            try:
                layer = Layer.objects.get(id=int(layer_id))
                layer_json = {
                    'name': layer.name,
                    'title': layer.title,
                    'order': 1000+i
                }
                layer.order = i
                layer.save()
                i = i + 1
                
                if not layer.external:
                    layers_dict[layer.name] = layer_json
                    last = layer
            except:
                logger.exception("Getting layer to update layer group order")

        if len(layers_dict)> 0:
            toc_object = {
                'name': group.name,
                'title': group.title,
                'order': 1000,
                'layers': layers_dict

            }

            toc={}
            toc[group.name] = toc_object
            gs = geographic_servers.get_instance().get_server_by_id(last.datastore.workspace.server.id)
            gs.createOrUpdateSortedGeoserverLayerGroup(toc)
            gs.set_gwclayer_dynamic_subsets(None, group.name)
            gs.reload_nodes()

def _layergroup_update(request, lgid, project_id):
    redirect_var = request.GET.get('redirect')
    from_redirect_var = request.GET.get('from_redirect')
    if redirect_var == 'project-layergroup-list':
        back_url = reverse('layergroup_list') + "?project_id=" + str(project_id)
    else:
        back_url = reverse('layergroup_list')
    if request.method == 'POST':
        name = request.POST.get('layergroup_name')
        title = request.POST.get('layergroup_title')
        toc = request.POST.get('toc')
        layergroup = LayerGroup.objects.get(id=int(lgid))
        if not utils.can_manage_layergroup(request.user, layergroup):
            return forbidden_view(request)

        assigned_includeinprojects_roles = []
        assigned_manage_roles = []
        for key in request.POST:
            if 'includeinprojects-userrole-' in key:
                assigned_includeinprojects_roles.append(key[len('includeinprojects-userrole-'):])
            elif 'manage-userrole-' in key:
                assigned_manage_roles.append(key[len('manage-userrole-'):])
        roles = utils.get_layergroup_checked_roles_from_user_input(assigned_includeinprojects_roles, assigned_manage_roles)

        cached = False
        if 'cached' in request.POST:
            cached = True

        visible = False
        if 'visible' in request.POST:
            visible = True

        if layergroup.name != name: # name changed
            if LayerGroup.objects.filter(name=name).exists():
                message = _('Layer group name already exists')
                return render(request, 'layergroup_update.html', {'message': message, 'layergroup': layergroup, 'layers': layers, 'roles': roles, 'workspaces': list(Workspace.objects.values()),'servers': list(Server.objects.values()), 'project_id': project_id, 'redirect': redirect_var, 'back_url': back_url})

            if _valid_name_regex.search(name) == None:
                message = _("Invalid layer group name: '{value}'. Identifiers must begin with a letter or an underscore (_). Subsequent characters can be letters, underscores or numbers").format(value=name)
                return render(request, 'layergroup_update.html', {'message': message, 'layergroup': layergroup, 'layers': layers, 'roles': roles, 'workspaces': list(Workspace.objects.values()),'servers': list(Server.objects.values()), 'project_id': project_id, 'redirect': redirect_var, 'back_url': back_url})

        old_name = layergroup.name
        layergroup.name = name
        layergroup.title = title
        layergroup.cached = cached
        layergroup.visible = visible
        layergroup.save()
        utils.set_layergroup_permissions(layergroup, assigned_includeinprojects_roles, assigned_manage_roles)
        layergroup_mapserver_toc(layergroup, toc)
        core_utils.toc_update_layer_group(layergroup, old_name, name, title)
        layer_group_cache_clear(layergroup)

        if redirect_var == 'project-layergroup-list':
            url = reverse('layergroup_list') + "?project_id=" + str(project_id)
            return redirect(url)
        if redirect_var == 'project-update':
            url = reverse('project_update', kwargs={'pid': project_id})
            return redirect(url)

        query_string = "?redirect=grouplayer-redirect"
        if from_redirect_var:
            query_string = query_string + "&from_redirect=" + from_redirect_var
        if project_id:
            query_string = query_string + "&project_id=" + str(project_id)
        if redirect_var == 'create-layer':
            return HttpResponseRedirect(reverse('layer_create_with_group', kwargs={'layergroup_id': layergroup.id})+query_string)
        if redirect_var == 'import-layer':
            return HttpResponseRedirect(reverse('layer_add_with_group', kwargs={'layergroup_id': layergroup.id})+query_string)
        return redirect('layergroup_list')
    else:
        layergroup = LayerGroup.objects.get(id=int(lgid))
        layers = []
        for layer in  Layer.objects.filter(layer_group_id=layergroup.id).order_by('-order'):
            lyr_def = {
                'id': layer.id,
                'name': layer.name,
                'fqn': layer.full_qualified_name,
                'title': layer.title,
                'type': layer.type,
                'order': layer.order,
                'external': layer.external,
                'cached': layer.cached,
                'can_manage': utils.can_manage_layer(request, layer)
            }
            layers.append(lyr_def)
        roles = utils.get_all_user_roles_checked_by_layergroup(layergroup, get_primary_user_role(request))

        response = {
            'lgid': lgid,
            'layergroup': layergroup,
            'layers': layers,
            'roles': roles,
            'workspaces': list(Workspace.objects.values()),
            'servers': list(Server.objects.values()),
            'project_id': project_id,
            'redirect': redirect_var,
            'back_url': back_url
        }

        return render(request, 'layergroup_update.html', response)


@login_required()
@staff_required
def layergroup_update(request, lgid):
    return _layergroup_update(request, lgid, None)

@login_required()
@staff_required
def layergroup_update_with_project(request, lgid, project_id):
    return _layergroup_update(request, lgid, project_id)

@login_required()
@staff_required
def layergroup_delete(request, lgid):
    if request.method == 'POST':
        layergroup = LayerGroup.objects.get(id=int(lgid))
        if not utils.can_manage_layergroup(request.user, layergroup):
            return HttpResponseForbidden('{"deleted": false}', content_type='application/json')
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

        except Exception: # ignore Geoserver failures because the group may only exist in gvsigol
            logger.exception("Error deleting layer group")
        layergroup.delete()

        response = {
            'deleted': True
        }
        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')


@login_required()
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def layer_create(request):
    return layer_create_with_group(request, None)


@login_required()
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def layer_create_with_group(request, layergroup_id):
    redirect_to_layergroup = request.GET.get('redirect')
    from_redirect = request.GET.get('from_redirect')
    project_id = request.GET.get('project_id')
    layer_type = "gs_vector_layer"

    if redirect_to_layergroup:
        if from_redirect:
            query_string = '?redirect=' + from_redirect
        else:
            query_string = ''
        if project_id:
            back_url = reverse('layergroup_update_with_project', kwargs={'lgid': layergroup_id, 'project_id': project_id}) + query_string
        else:
            back_url = reverse('layergroup_update', kwargs={'lgid': layergroup_id}) + query_string
    else:
        back_url = reverse('layer_list')


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

        detailed_info_enabled = (request.POST.get('detailed_info_enabled') is not None)
        detailed_info_button_title = request.POST.get('detailed_info_button_title')
        detailed_info_html = request.POST.get('detailed_info_html')

        assigned_read_roles = []
        assigned_write_roles = []
        assigned_manage_roles = []
        for key in request.POST:
            if 'read-usergroup-' in key:
                assigned_read_roles.append(key[len('read-usergroup-'):])
            elif 'write-usergroup-' in key:
                assigned_write_roles.append(key[len('write-usergroup-'):])
            elif 'manage-usergroup-' in key:
                assigned_manage_roles.append(key[len('manage-usergroup-'):])

        is_public = (request.POST.get('resource-is-public') is not None)

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


        form = CreateFeatureTypeForm(request.POST, request=request, layergroup_id=layergroup_id)
        if form.is_valid():
            try:
                datastore = form.cleaned_data['datastore']
                server = geographic_servers.get_instance().get_server_by_id(datastore.workspace.server.id)
                layergroup = form.cleaned_data['layer_group']
                if _valid_name_regex.search(form.cleaned_data['name']) == None:
                    msg = _("Invalid datastore name: '{value}'. Identifiers must begin with a letter or an underscore (_). Subsequent characters can be letters, underscores or numbers").format(value=form.cleaned_data['name'])
                    form.add_error(None, msg)
                elif not utils.can_manage_datastore(request, datastore):
                    msg = _("You are not allowed to manage the selected datastore")
                    form.add_error(None, msg)
                elif not utils.can_use_layergroup(request, layergroup, permission=LayerGroupRole.PERM_INCLUDEINPROJECTS):
                    msg = _("You are not allowed to manage the selected layergroup")
                    form.add_error(None, msg)

                else:
                    server.normalizeTableFields(form.cleaned_data['fields'])
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
                    max_order = layergroup.layer_set.aggregate(Max('order')).get('order__max')
                    newRecord.order = max_order + 1 if max_order is not None else newRecord.order
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
                    
                    # Guardar configuración inicial con campos especiales antes de layer_autoconfig
                    initial_conf = {
                        'fields': []
                    }
                    
                    for i in form.cleaned_data['fields']:
                        field_conf = {
                            'name': i['name'],
                            'gvsigol_type': i.get('gvsigol_type', ''),
                            'type_params': i.get('type_params', {})
                        }
                        initial_conf['fields'].append(field_conf)
                    
                    newRecord.conf = initial_conf
                    newRecord.save()

                    for i in form.cleaned_data['fields']:
                        if 'enumkey' in i:
                            field_enum = LayerFieldEnumeration()
                            field_enum.layer = newRecord
                            field_enum.field = i['name']
                            field_enum.enumeration_id = int(i['enumkey'])
                            field_enum.multiple = True if i['type'] == 'multiple_enumeration' else False
                            field_enum.save()
                        if i.get('calculation'):
                            try:
                                calculation = i.get('calculation')
                                procedure = TriggerProcedure.objects.get(signature=calculation)
                                trigger = Trigger()
                                trigger.layer = newRecord
                                trigger.field = i['name']
                                trigger.procedure = procedure
                                trigger.save()

                                trigger.install()
                            except:
                                logger.exception("Error creating trigger for calculated field")

                    featuretype = {
                        'max_features': maxFeatures
                    }
                    utils.set_layer_permissions(newRecord, is_public, assigned_read_roles, assigned_write_roles, assigned_manage_roles)
                    do_config_layer(server, newRecord, featuretype)

                    if redirect_to_layergroup:
                        new_layergroup_id = newRecord.layer_group.id
                        if project_id:
                            to_url = reverse('layergroup_update_with_project', kwargs={'lgid': new_layergroup_id, 'project_id': project_id}) + query_string
                        else:
                            to_url = reverse('layergroup_update', kwargs={'lgid': new_layergroup_id}) + query_string
                    else:
                        to_url = back_url
                    return HttpResponseRedirect(to_url)

            except psycopg2.errors.DuplicateTable as e1:
                logger.exception("Error creating layer: table already exists")
                try:
                    msg = e1.get_message()
                except:
                    msg = _("Error: table already exists. Try to publish the layer instead of creating an empty one.")
                form.add_error(None, msg)
            except Exception as e:
                logger.exception("Error creating layer")
                try:
                    msg = e.get_message()
                except:
                    msg = _("Error: layer could not be published")
                # FIXME: the backend should raise more specific exceptions to identify the cause (e.g. layer exists, backend is offline)
                form.add_error(None, msg)

            roles = utils.get_layer_checked_roles_from_user_input(assigned_read_roles, assigned_write_roles, assigned_manage_roles)
            data = {
                'form': form,
                'message': msg,
                'layer_type': layer_type,
                'enumerations': get_currentuser_enumerations(request),
                'roles': roles,
                'resource_is_public': is_public,
                'project_id': project_id,
                'from_redirect': from_redirect,
                'detailed_info_enabled': detailed_info_enabled,
                'detailed_info_button_title': detailed_info_button_title,
                'detailed_info_html': detailed_info_html,
                'back_url': back_url
            }
            return render(request, "layer_create.html", data)

        else:
            forms = []
            if 'gvsigol_plugin_form' in INSTALLED_APPS:
                from gvsigol_plugin_form.models import Form
                forms = Form.objects.all()
            roles = utils.get_layer_checked_roles_from_user_input(assigned_read_roles, assigned_write_roles, assigned_manage_roles)
            data = {
                'form': form,
                'forms': forms,
                'layer_type': layer_type,
                'enumerations': get_currentuser_enumerations(request),
                'procedures':  TriggerProcedure.objects.all(),
                'roles': roles,
                'resource_is_public': is_public,
                'redirect_to_layergroup': redirect_to_layergroup,
                'layergroup_id': layergroup_id,
                'project_id': project_id,
                'from_redirect': from_redirect,
                'detailed_info_enabled': detailed_info_enabled,
                'detailed_info_button_title': detailed_info_button_title,
                'detailed_info_html': detailed_info_html,
                'back_url': back_url
            }
            return render(request, "layer_create.html", data)

    else:
        form = CreateFeatureTypeForm(request=request, layergroup_id=layergroup_id)
        forms = []

        if 'gvsigol_plugin_form' in INSTALLED_APPS:
            from gvsigol_plugin_form.models import Form
            forms = Form.objects.all()
        # since created layers are empty, it makes sense to set write permissions for the creator
        roles = utils.get_all_user_roles_checked_by_layer(None, get_primary_user_role(request), creator_all=True)
        data = {
            'form': form,
            'forms': forms,
            'layer_type': layer_type,
            'enumerations': get_currentuser_enumerations(request),
            'procedures':  TriggerProcedure.objects.all(),
            'roles': roles,
            'resource_is_public': False,
            'redirect_to_layergroup': redirect_to_layergroup,
            'layergroup_id': layergroup_id,
            'project_id': project_id,
            'from_redirect': from_redirect,
            'back_url': back_url
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

@login_required()
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


@login_required()
@staff_required
def enumeration_add(request):
    if request.method == 'POST':
        name = request.POST.get('enumeration_name')
        title = request.POST.get('enumeration_title')
        order_type = request.POST.get('order_type')

        aux_title = b"".join(title.encode('ASCII', 'ignore').split())[:4]
        aux_title = aux_title.lower()

        name = name + '_' + re.sub("[!@#$%^&*()[]{};:,./<>?\|`~-=_+ ]", "", aux_title.decode("utf-8"))

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
                    created_by = request.user.username,
                    order_type = order_type
                )
                enum.save()

                items_data = []
                for key in request.POST:
                    if 'item-content' in key:
                        aux_name = request.POST.get(key).strip()
                        while '  ' in aux_name:
                            aux_name = aux_name.replace('  ', ' ')

                        if aux_name.__len__() > 0:
                            items_data.append(aux_name)

                if order_type == Enumeration.ALPHABETICAL:
                    items_data.sort(key=lambda x: x.lower())

                for index, item_name in enumerate(items_data):
                    item = EnumerationItem(
                        enumeration = enum,
                        name = item_name,
                        selected = False,
                        order = index 
                    )
                    item.save()

            else:
                index = len(Enumeration.objects.all())
                enum_name = 'enm_' + str(index)
                message = _('You must enter a title for enumeration')
                return render(request, 'enumeration_add.html', {
                    'message': message, 
                    'enum_name': enum_name,
                    'MANUAL': Enumeration.MANUAL,
                    'ALPHABETICAL': Enumeration.ALPHABETICAL
                })
        else:
            index = len(Enumeration.objects.all())
            enum_name = 'enm_' + str(index)
            message = _('Name already taken')
            return render(request, 'enumeration_add.html', {
                'message': message, 
                'enum_name': enum_name,
                'MANUAL': Enumeration.MANUAL,
                'ALPHABETICAL': Enumeration.ALPHABETICAL
            })

        return redirect('enumeration_list')

    else:
        index = len(Enumeration.objects.all())
        enum_name = 'enm_' + str(index)
        return render(request, 'enumeration_add.html', {
            'enum_name': enum_name,
            'MANUAL': Enumeration.MANUAL,
            'ALPHABETICAL': Enumeration.ALPHABETICAL
        })


@login_required()
@staff_required
def enumeration_update(request, eid):
    if request.method == 'POST':
        name = request.POST.get('enumeration_name')
        title = request.POST.get('enumeration_title')
        order_type = request.POST.get('order_type')

        enum = Enumeration.objects.get(id=int(eid))

        enum.name = name
        enum.title = title
        enum.order_type = order_type
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

        return render(request, 'enumeration_update.html', {
            'eid': eid,
            'enumeration': enum,
            'items': items,
            'count': len(items) + 1,
            'MANUAL': Enumeration.MANUAL,
            'ALPHABETICAL': Enumeration.ALPHABETICAL
        })

#***************************************************
# TILEADO CAPAS BASE
#***************************************************

@login_required()
@staff_required
def create_base_layer(request, pid):
    if request.method == 'POST':
        plg = ProjectLayerGroup.objects.filter(project_id=pid, baselayer_group=True)
        if plg is None or len(plg) == 0:
            return utils.get_exception(400, 'This project does not have base layer')
        id_base_lyr = plg[0].default_baselayer
        base_lyr = Layer.objects.get(id=id_base_lyr)

        num_res_levels = None
        try:
            num_res_levels = int(request.POST.get('tiles'))
            format_ = request.POST.get('format')
        except Exception:
            return utils.get_exception(400, 'Wrong number of tiles')
        tilematrixset = request.POST.get('tilematrixset')
        extent = request.POST.get('extent')
        version = int(round(time.time() * 1000))

        base_layer_process = {}
        if num_res_levels is not None:
            if num_res_levels > 22:
                return utils.get_exception(400, 'The number of resolution levels cannot be greater than 22')
            else:
                tasks.tiling_base_layer(base_layer_process, version, base_lyr, pid, num_res_levels, tilematrixset, format_, extent)
        else:
            return utils.get_exception(400, 'Wrong number of tiles')

    return HttpResponse('{"response": "' + str(base_layer_process[str(pid)]['extent_processed']) + '"}', content_type='application/json')




@login_required()
@staff_required
def retry_base_layer_process(request, pid):
    if request.method == 'POST':
        prj = ProjectBaseLayerTiling.objects.get(id=pid)
        if(prj is not None):
            if not os.path.exists(prj.folder_prj):
                return utils.get_exception(400, 'This project does not have a base layer downloading')
        else:
            return utils.get_exception(400, 'This project does not have base layer running')
        version = prj.version
        processes = TilingProcessStatus.objects.filter(version=version)
        for tiling_status in processes: #solo debería haber uno
            tiling_status.stop = 'false'
            tiling_status.active = 'true'
            tiling_status.save()
            base_layer_process[prj.id] = tiling_status
            tasks.retry_base_layer_tiling(base_layer_process, prj, tiling_status)

    return HttpResponse('{"response": "ok"}', content_type='application/json')



@login_required()
@staff_required
def base_layer_process_update(request, pid):
    if request.method == 'POST':
        try:
            base_layer_tiling = ProjectBaseLayerTiling.objects.get(id=pid)
            version = base_layer_tiling.version
            status_json = {}
            status = TilingProcessStatus.objects.filter(version=version)
            if(status is not None) :
                for s in status:
                    status_json = serial.serialize('json', status)
                    status_json = json.loads(status_json)[0]['fields']
                    return HttpResponse(json.dumps(status_json, indent=4), content_type='application/json')
        except Exception as e:
            pass
        return HttpResponse('{"active" : "false"}', content_type='application/json')


@login_required()
@staff_required
def stop_base_layer_process(request, pid):
    if request.method == 'POST':
        base_layer_tiling = ProjectBaseLayerTiling.objects.get(id=pid)
        version = base_layer_tiling.version
        status_json = {}
        processes = TilingProcessStatus.objects.filter(version=version)
        for tiling_status in processes: #solo debería haber uno
            tiling_status.stop = 'true'
            tiling_status.save()

#***************************************************

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


@login_required()
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
@login_required()
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
            for layer in layers_array:
                layer['url'] = core_utils.get_absolute_url(layer['url'], request.META)
                url = layer['url']
                if layer['external']:
                    styles = []
                    if 'styles' in layer:
                        styles = layer['styles']
                    aux_response = fut_session.get(url, verify=False, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT), proxies=settings.PROXIES)
                    rs.append(is_grouped_symbology_request(request, url, aux_response, styles, fut_session))

                else:
                    styles = []
                    urls.append(url)
                    query_layer = layer['query_layer']
                    ws = None
                    if 'workspace' in layer:
                        ws = layer['workspace']

                    cluster = False
                    for s in styles:
                        if s['is_default'] == True:
                            style_name = s['name']
                            if Style.objects.filter(type = 'CP', name=style_name, stylelayer__layer__name=query_layer, stylelayer__layer__datastore__workspace__name=ws).exists():
                                cluster = True

                    print(url)
                    auth2 = None
                    headers = None
                    if query_layer != 'plg_catastro' and \
                            ((request.session.get('username') is not None and \
                            request.session.get('password') is not None) or \
                            request.session.get('oidc_access_token')):
                        servers = Server.objects.all()
                        url_obj = urlparse(url)
                        for server in servers:
                            server_url_obj = urlparse(server.frontend_url)
                            if url_obj.netloc == server_url_obj.netloc:
                                auth2, headers = utils.getAuthElements(request)
                            elif server_url_obj.netloc == '':
                                for host in settings.ALLOWED_HOST_NAMES:
                                    host_obj = urlparse(host)
                                    if url_obj.netloc == host_obj.netloc:
                                        auth2, headers = utils.getAuthElements(request)
                                if auth2 or headers:
                                    break

                    aux_response = fut_session.get(url, auth=auth2, headers=headers, verify=False, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT), proxies=settings.PROXIES)
                    rs.append(is_grouped_symbology_request(request, url, aux_response, styles, fut_session))

            i=0
            for layer in layers_array:
                url = layer['url']
                query_layer = layer['query_layer']
                ws= None
                if 'workspace' in layer:
                    ws = layer['workspace']

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
            print(str(e))
            response = {
                'error':  str(str(e)),
                'urls': urls
            }

        for resultset in results:

            url = resultset['url']
            query_layer = resultset['query_layer']
            ws = resultset['ws']

            features = None
            if query_layer == 'plg_catastro':
                html_content = html.document_fromstring(resultset['response'].encode('ascii'))
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
                                    if not cluster:
                                        fid = geojson['features'][i].get('id').split('.')[1]
                                        try:
                                            layer_resources = LayerResource.objects.filter(layer_id=layer.id).filter(feature=fid)
                                            for lr in layer_resources:
                                                res_type = utils.get_resource_type_label(lr.type)
                                                resource = {
                                                    'type': res_type,
                                                    'url': lr.get_url(),
                                                    'title': lr.title,
                                                    'name': lr.path.split('/')[-1],
                                                    'id': lr.id
                                                }
                                                resources.append(resource)
                                        except Exception as e:
                                            print(str(e))
                                    else:
                                        geojson['features'][i]['resources'] = resources
                                        geojson['features'][i]['all_correct'] = resultset['response']
                                        geojson['features'][i]['feature'] = fid
                                        geojson['features'][i]['layer_name'] = resultset['query_layer']

                                        features = get_clustered_values(geojson['features'], layer.datastore.name)

                                else:
                                    geojson['features'][i]['type']= 'raster'

                                if not cluster:
                                    geojson['features'][i]['resources'] = resources
                                    geojson['features'][i]['all_correct'] = resultset['response']
                                    geojson['features'][i]['feature'] = fid
                                    geojson['features'][i]['layer_name'] = resultset['query_layer']
                            if not cluster:
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
                        print(str(e))
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

def get_clustered_values(geojson, ds_name):

    datastore = Datastore.objects.get(name__exact=ds_name)
    params = json.loads(datastore.connection_params)
    host = params['host']
    port = params['port']
    dbname = params['database']
    user = params['user']
    passwd = params['passwd']

    conn = psycopg2.connect(database=dbname, host=host, port=port, user=user, password=passwd)
    cur = conn.cursor()

    lyr_name = geojson[0]['layer_name']
    limit = geojson[0]['properties']['count']

    coordinates = geojson[0]['geometry']['coordinates']

    features = []

    query = sql.SQL("SELECT row_to_json(fila) FROM (SELECT * FROM {schema}.{lyr} ORDER BY ST_DISTANCE('SRID=3857;POINT({x_} {y_})'::geometry, ST_TRANSFORM(wkb_geometry, 3857)) ASC LIMIT %s) AS fila").format(
        schema = sql.Identifier(ds_name),
        lyr = sql.Identifier(lyr_name),
        x_ = sql.SQL(str(coordinates[0])),
        y_ = sql.SQL(str(coordinates[1]))
    )
    cur.execute(query,[limit])

    """
    geombbox = json.dumps(geojson[0]['properties']['geomBBOX'])
    query = sql.SQL("SELECT row_to_json(fila) FROM (SELECT * FROM {schema}.{lyr} WHERE ST_INTERSECTS(ST_SetSRID(ST_GeomFromGeoJSON(%s), 3857), ST_TRANSFORM(wkb_geometry, 3857)) = true ) AS fila").format(
            schema = sql.Identifier(ds_name),
            lyr = sql.Identifier(lyr_name)
        )

    cur.execute(query,[str(geombbox)])
    """

    for row in cur:
        f = {}
        f['type'] = 'Feature'
        f['id'] =lyr_name+'.'+str(row[0]['ogc_fid'])
        f['geometry'] = row[0]['wkb_geometry']
        f['properties'] = row[0]
        del f['properties']['wkb_geometry']
        f['resources'] = []
        f['feature'] = str(row[0]['ogc_fid'])
        f['layer_name'] = lyr_name

        features.append(f)

    return features

@csrf_exempt
def get_unique_values(request):
    if request.method == 'POST':
        layer_name = request.POST.get('layer_name')
        layer_ws = request.POST.get('layer_ws')
        field = request.POST.get('field')

        workspace = Workspace.objects.get(name__exact=layer_ws)
        layer = Layer.objects.get(name=layer_name, datastore__workspace__name=workspace.name)
        if not utils.can_read_layer(request, layer):
            return HttpResponseForbidden(json.dumps({'values': []}), content_type='application/json')

        i, source_name, schema = layer.get_db_connection()
        with i as c:
            unique_fields = c.get_unique_values(schema, source_name, field)
            return HttpResponse(json.dumps({'values': unique_fields}, indent=4), content_type='application/json')


def is_numeric_type(type):
    if type == 'smallint' or type == 'integer' or type == 'bigint' or type == 'decimal' or type == 'numeric' or type == 'real' or type == 'double precision' or type == 'smallserial' or type == 'serial' or type == 'bigserial':
        return True;
    return False;


def is_string_type(type):
    if type.startswith('character varying') or type.startswith('varchar') or type.startswith('character') or type.startswith('char') or type.startswith('text') or type == 'enumeration':
        return True;
    return False;

@csrf_exempt
def get_datatable_data(request):
    if request.method == 'POST':
        layer_name = request.POST.get('layer_name')
        workspace = request.POST.get('workspace')
        layer = Layer.objects.select_related("datastore__workspace__server") \
                    .get(name=layer_name, datastore__workspace__name=workspace)
        if not utils.can_read_layer(request, layer):
            response = {
                'draw': 0,
                'recordsTotal': 0,
                'recordsFiltered': 0,
                'data': []
            }
            return HttpResponseForbidden(json.dumps(response), content_type='application/json')
        qualified_name = workspace + ":" + layer_name
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

        gs = geographic_servers.get_instance().get_server_by_id(layer.datastore.workspace.server.id)
        definition = gs.getFeaturetype(layer.datastore.workspace, layer.datastore, layer.name, layer.title)
        aux_property_name = ' '
        sortby_field = None
        if 'featureType' in definition and 'attributes' in definition['featureType'] and 'attribute' in definition['featureType']['attributes']:
            attributes = definition['featureType']['attributes']['attribute']
            if isinstance(attributes, list):
                for attribute in attributes:
                    aux_property_name += str(attribute['name']) + ' '
                    if not sortby_field and not 'jts.geom' in attribute['binding']:
                        sortby_field = attribute['name']
            else:
                attribute = attributes
                aux_property_name += str(attribute['name']) + ' '
                if not sortby_field and not 'jts.geom' in attribute['binding']:
                    sortby_field = attribute['name']

        num_fields = property_name.split(',').__len__()
        found = -1
        idx = 0
        while found == -1 and num_fields - 1 >= idx:
            if not sortby_field:
                sortby_field = property_name.split(',')[idx]
            found = aux_property_name.find(' ' + sortby_field + ' ')
            idx = idx + 1
        property_name = aux_property_name.strip().replace(' ',',')

        params = json.loads(layer.datastore.connection_params)
        if not sortby_field:
            sortby_field = property_name.split(',')[0]

        if sortby_field == 'wkb_geometry' and num_fields > 1:
            sortby_field = property_name.split(',')[1]

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
                    'TYPENAME': qualified_name,
                    'OUTPUTFORMAT': 'application/json',
                    'MAXFEATURES': max_features,
                    'STARTINDEX': start_index,
                    'PROPERTYNAME': property_name
                }

                if sortby_field != 'wkb_geometry':
                    values['SORTBY'] = sortby_field

                if cql_filter != '':
                    values['cql_filter'] = cql_filter

                recordsTotal = gs.getFeatureCount(request, wfs_url, qualified_name, None)
                recordsFiltered = gs.getFeatureCount(request, wfs_url, qualified_name, cql_filter)
                #recordsFiltered = recordsTotal

            else:
                properties = properties_with_type.split(',')
                geoserver_fields = property_name.split(',')
                raw_search_cql = '('
                for p in properties:
                    if p.split('|')[0] != 'id' and p.split('|')[0] in geoserver_fields:
                        if is_string_type(p.split('|')[1]):
                            raw_search_cql += p.split('|')[0] + " ILIKE '%" + search_value.replace('?', '_') +"%'"
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
                    'TYPENAME': qualified_name,
                    'OUTPUTFORMAT': 'application/json',
                    'MAXFEATURES': max_features,
                    'STARTINDEX': start_index,
                    'PROPERTYNAME': property_name
                }
                if sortby_field != 'wkb_geometry':
                    values['SORTBY'] = sortby_field

                if cql_filter == '':
                    values['cql_filter'] = raw_search_cql
                else:
                    values['cql_filter'] = cql_filter + ' AND ' + raw_search_cql
                recordsTotal = gs.getFeatureCount(request, wfs_url, qualified_name, None)
                recordsFiltered = gs.getFeatureCount(request, wfs_url, qualified_name, values['cql_filter'])

            req = gs.getUserAuthSession(request)
            response = req.post(wfs_url, data=values, verify=False, proxies=settings.PROXIES)
            try:
                geojson = response.json()
            except:
                logger.error("wfs request error. Status_code: {}".format(response.status_code))
                logger.error(response.text)
                raise

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
            logger.exception("Error building get_datatable_data")
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
        layer = Layer.objects.select_related("datastore__workspace__server") \
                    .get(name=layer_name, datastore__workspace__name=workspace)
        if not utils.can_read_layer(request, layer):
            return HttpResponseForbidden('{"data": []}', content_type='application/json')
        field = request.POST.get('field')
        field_type = request.POST.get('field_type')
        value = request.POST.get('value')
        operator = request.POST.get('operator')

        try:
            wfs_url = layer.datastore.workspace.server.getWfsEndpoint(workspace)
            wfs_url = core_utils.get_absolute_url(wfs_url, request.META)

            cql_filter = None
            if operator == 'equal_to':
                if field_type == 'character varying' or field_type == 'enumeration':
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

            params = urllib.parse.urlencode(data)
            if not layer.external:
                session = utils.getUserAuthSession(request)
            else:
                session = requests.Session()
            print(wfs_url + "?" + params)
            response = session.post(wfs_url, data=data, verify=False, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT), proxies=settings.PROXIES)
            geojson = response.json()

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

@csrf_exempt
def get_feature_resources(request):
    if request.method == 'POST':
        query_layer = request.POST.get('query_layer')
        workspace = request.POST.get('workspace')
        fid = request.POST.get('fid')
        try:
            layer = Layer.objects.get(name=query_layer, datastore__workspace__name=workspace)
            if not utils.can_read_feature(request, layer, fid):
                return HttpResponseForbidden()
            layer_resources = LayerResource.objects.filter(layer_id=layer.id).filter(feature=int(fid))
            resources = []
            for lr in layer_resources:
                url = lr.get_url()
                name = lr.path.split('/')[-1]
                title = lr.title
                res_type = utils.get_resource_type_label(lr.type)
                resource = {
                    'type': res_type,
                    'url': url,
                    'name': name,
                    'title': title,
                    'rid': lr.id
                }
                resources.append(resource)
        except Exception as e:
            print(str(e))

        response = {
            'resources': resources
        }

        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')

@require_safe
def get_resource(request, resource_id):
    try:
        resource = LayerResource.objects.get(id=resource_id)
        if not utils.can_read_feature(request, resource.layer, resource.feature):
            return HttpResponseForbidden()
        return sendfile(request, resource.get_abspath(), attachment=False)
    except:
        logger.exception("Error getting resource")
        return HttpResponseNotFound()

@login_required()
def upload_resources(request):
    if request.method == 'POST':
        ws_name = request.POST.get('workspace')
        layer_name = request.POST.get('layer_name')
        fid = request.POST.get('fid')
        version = request.POST.get('version', 0)
        if ":" in layer_name:
            layer_name = layer_name.split(":")[1]
        layer = Layer.objects.get(name=layer_name, datastore__workspace__name=ws_name)
        if not utils.can_write_feature(request, layer, fid):
            return HttpResponseForbidden()
        if 'resource' in request.FILES:
            """
            Don't check version for resource upload. The uploads will run concurrently if
            several files are uploaded, so we could get inconsistent versions.
            Since modification of resources is not allowed now (only add/remove is allowed),
            increasing the version number should be enough for uploads.
            """
            resource = request.FILES['resource']
            res_type = utils.get_resource_type(resource.content_type)
            (saved, path) = resource_manager.save_resource(resource, layer.id, res_type)
            if saved:
                res = LayerResource()
                res.feature = int(fid)
                res.layer = layer
                res.path = path
                res.title = resource.name
                res.type = res_type
                res.created = timezone.now()
                res.save()
                response = {'success': True, 'id': res.pk, 'path': path}
                version, version_date = utils.update_feat_version(res.layer, res.feature)
                if version is not None:
                    signals.layerresource_created.send(sender=res.__class__,
                       layer=res.layer,
                       featid=res.feature,
                       resource_id=res.pk,
                       version=version,
                       path=path,
                       user=request.user)
                    response['feat_version'] = version
                    response['feat_date'] = str(version_date)
            else:
                response = {'success': False}
        else:
            response = {'success': False}
    return HttpResponse(json.dumps(response, indent=4), content_type='application/json')


@login_required()
def delete_resource(request):
    if request.method == 'POST':
        rid = request.POST.get('rid')
        version = request.POST.get(settings.VERSION_FIELD, 0)
        try:
            resource = LayerResource.objects.get(id=int(rid))
            if not utils.can_write_feature(request, resource.layer, resource.feature):
                return HttpResponseForbidden()
            check_version = utils.check_feature_version(resource.layer, resource.feature, int(version))
            if check_version == False:
                response = HttpResponse("Version conflict")
                response.status_code = 409
                return response
            featid = resource.feature
            lyrid = resource.layer.id
            resource.delete()
            historical_filepath = resource_manager.delete_resource(resource)
            response = {'deleted': True, 'featid': featid, 'lyrid': lyrid, 'path': historical_filepath}
            if check_version is not None:
                version, version_date = utils.update_feat_version(resource.layer, resource.feature)
                signals.layerresource_deleted.send(sender=None,
                                                   layer=resource.layer,
                                                   featid=featid,
                                                   resource_id=resource.pk,
                                                   version=version,
                                                   historical_path=historical_filepath,
                                                   user=request.user)
                response['feat_version'] = version
                response['feat_date'] = str(version_date)
                try:
                    # missing if plugin_restapi is not installed
                    response['url'] = reverse('get_layer_historic_resource', args=[lyrid, featid, version])
                except:
                    pass

        except Exception:
            logger.exception("Error deleting resource")
            response = {'deleted': False}
            pass

        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')

@login_required()
def delete_resources(request):
    if request.method == 'POST':
        query_layer = request.POST.get('query_layer')
        workspace = request.POST.get('workspace')
        fid = request.POST.get('fid')
        version = request.POST.get('feat_version_gvol')
        try:
            layer = Layer.objects.get(name=query_layer, datastore__workspace__name=workspace)
            if not utils.can_write_feature(request, layer, fid):
                return HttpResponseForbidden()
            layer_resources = LayerResource.objects.filter(layer_id=layer.id).filter(feature=int(fid))
            pathlist = []
            for resource in layer_resources:
                resource.delete()
                historical_filepath = resource_manager.delete_resource(resource)
                pathlist.append(historical_filepath)
                signals.layerresource_deleted.send(sender=None,
                                               layer=resource.layer,
                                               featid=resource.feature,
                                               resource_id=resource.pk,
                                               version=version,
                                               historical_path=historical_filepath,
                                               user=request.user)
            response = {'deleted': True, 'pathlist': pathlist}

        except Exception as e:
            print(str(e))
            response = {'deleted': False}
            pass

        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')


@csrf_exempt
def describe_layer_config(request):
    if request.method == 'POST':
        lyr = request.POST.get('layer')
        workspace = request.POST.get('workspace')
        try:
            l = Layer.objects.select_related("datastore__workspace__server") \
                    .get(name=lyr, datastore__workspace__name=workspace)
            if utils.can_read_layer(request, l):
                read_roles = utils.get_read_roles(l)
                write_roles = utils.get_write_roles(l)
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
                layer['public'] = l.public

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
                #layer['namespace'] = workspace.uri
                layer['namespace'] = core_utils.get_absolute_url(workspace.uri, request.META)
                layer['workspace'] = workspace.name
                layer['metadata'] = core_utils.get_catalog_url(request, l)
                if l.cached:
                    layer['cache_url'] = core_utils.get_cache_url(workspace)
                else:
                    layer['cache_url'] = core_utils.get_wms_url(workspace)



            response = {'layer': layer}


        except Exception as e:
            print(str(e))
            response = {'layer': {}}
            pass

        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')

@csrf_exempt
def describeFeatureType(request):
    if request.method == 'POST':
        lyr = request.POST.get('layer')
        workspace = request.POST.get('workspace')
        try:
            layer = Layer.objects.select_related("datastore__workspace__server") \
                    .get(name=lyr, datastore__workspace__name=workspace)
            if not utils.can_read_layer(request, layer):
                response = {'fields': [], 'error': 'Not authorized'}
                return HttpResponseForbidden(response, content_type='application/json')
            skip_pks = request.POST.get('skip_pks')
            feat_type = _describeFeatureType(layer, skip_pks)
            return HttpResponse(json.dumps(feat_type, indent=4), content_type='application/json')
        except:
            response = {'fields': [], 'error': 'Not found'}
            return HttpResponse(json.dumps(response, indent=4), content_type='application/json')

def _describeFeatureType(layer, skip_pks):
    try:
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

        gs = geographic_servers.get_instance().get_server_by_id(layer.datastore.workspace.server.id)
        expose_pks = gs.datastore_check_exposed_pks(layer.datastore)

        for layer_def in layer_defs:
            for geom_def in geom_defs:
                if layer_def['name'] == geom_def[2]:
                    layer_def['type'] = geom_def[5]
                    layer_def['length'] = geom_def[4]

        for layer_def in layer_defs:
            if not expose_pks or skip_pks == 'true':
                if layer_def['name'] in pk_defs:
                    layer_defs.remove(layer_def)
            enum, multiple = utils.is_field_enumerated(layer, layer_def['name'])
            if enum:
                if multiple:
                    layer_def['type'] = 'multiple_enumeration'
                else:
                    layer_def['type'] = 'enumeration'

        response = {'fields': layer_defs}

    except Exception as e:
        print(str(e))
        response = {'fields': [], 'error': str(e)}
        pass

    return response

def describe_feature_type(lyr, workspace):
    try:
        layer = Layer.objects.get(name=lyr, datastore__workspace__name=workspace)
        params = json.loads(layer.datastore.connection_params)
        schema = params.get('schema', 'public')

        i = Introspect(database=params['database'], host=params['host'], port=params['port'], user=params['user'], password=params['passwd'])
        layer_defs = i.get_fields_info(layer.name, schema)
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
        print(str(e))
        response = {'fields': [], 'error': str(e)}
        pass

    return response

@csrf_exempt
def describeFeatureTypeWithPk(request):
    if request.method == 'POST':
        lyr = request.POST.get('layer')
        workspace = request.POST.get('workspace')
        try:
            layer = Layer.objects.get(name=lyr, datastore__workspace__name=workspace)
            if not utils.can_read_layer(request, layer):
                response = {'fields': [], 'error': 'Not authorized'}
                return HttpResponseForbidden(response, content_type='application/json')

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
            i.close()

            for layer_def in layer_defs:
                for geom_def in geom_defs:
                    if layer_def['name'] == geom_def[2]:
                        layer_def['type'] = geom_def[5]
                        layer_def['length'] = geom_def[4]

            response = {'fields': layer_defs}


        except Exception as e:
            print(str(e))
            response = {'fields': []}
            pass

        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')



@login_required()
@require_safe
@staff_required
def external_layer_list(request):
    if request.user.is_superuser:
        external_layer_list = Layer.objects.filter(external=True).order_by('id')

        response = {
            'external_layers': external_layer_list
        }
        return render(request, 'external_layer_list.html', response)
    else:
        user_roles = auth_backend.get_roles(request)
        external_layer_list = (Layer.objects.filter(created_by=request.user.username, external=True)
            | Layer.objects.filter(layermanagerole__role__in=user_roles, external=True)).order_by('id').distinct()
        response = {
            'external_layers': external_layer_list
        }
        return render(request, 'external_layer_list.html', response)

@login_required()
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def external_layer_add(request):
    back_url = reverse('external_layer_list')
    if request.method == 'POST':
        form = ExternalLayerForm(request, request.POST)

        try:
            is_visible = False
            if 'visible' in request.POST:
                is_visible = True

            cached = False
            if 'cached' in request.POST:
                cached = True

            detailed_info_enabled = (request.POST.get('detailed_info_enabled') is not None)
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
            external_layer.public = True
            external_layer.title = request.POST.get('title')
            external_layer.layer_group = layer_group
            max_order = layer_group.layer_set.aggregate(Max('order')).get('order__max')
            external_layer.order = max_order + 1 if max_order is not None else external_layer.order
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
                params['get_map_url'] = request.POST.get('get_map_url')
                params['cache_url'] = server.getCacheEndpoint()
                params['layers'] = request.POST.get('layers')
                params['format'] = request.POST.get('format')
                params['infoformat'] = request.POST.get('infoformat')

            if external_layer.type == 'WMTS':
                params['matrixset'] = request.POST.get('matrixset')
                params['tilematrix'] = request.POST.get('tilematrix')
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

            return HttpResponseRedirect(back_url)

        except Exception as e:
            logger.exception("Error creating external layer")
            try:
                msg = e.get_message()
            except:
                msg = _("Error: ExternalLayer could not be published")
            form.add_error(None, msg)

    else:
        form = ExternalLayerForm(request)

    return render(request, 'external_layer_add.html', {'form': form, 'bing_layers': BING_LAYERS, 'back_url': back_url})

@login_required()
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def external_layer_update(request, external_layer_id):
    redirect_to_layergroup = request.GET.get('redirect')
    from_redirect = request.GET.get('from_redirect')
    project_id = request.GET.get('project_id')
    layergroup_id = request.GET.get('layergroup_id')
    external_layer = Layer.objects.get(id=external_layer_id)
    if not utils.can_manage_layer(request, external_layer):
        return forbidden_view(request)

    if redirect_to_layergroup:
        if from_redirect:
            query_string = '?redirect=' + from_redirect
        else:
            query_string = ''
        if project_id:
            back_url = reverse('layergroup_update_with_project', kwargs={'lgid': layergroup_id, 'project_id': project_id}) + query_string
        else:
            back_url = reverse('layergroup_update', kwargs={'lgid': layergroup_id}) + query_string
    else:
        back_url = reverse('external_layer_list')

    if request.method == 'POST':
        form = ExternalLayerForm(request, request.POST)
        if not layergroup_id:
            layergroup_id = request.POST.get('layer_group')
        try:
            layer_group = LayerGroup.objects.get(id=layergroup_id)
        except LayerGroup.DoesNotExist:
            return not_found_view(request)
        if not utils.can_use_layergroup(request, layer_group, permission=LayerGroupRole.PERM_INCLUDEINPROJECTS):
            return forbidden_view(request)
        server = Server.objects.get(id=layer_group.server_id)

        try:
            is_visible = False
            if 'visible' in request.POST:
                is_visible = True

            cached = False
            if 'cached' in request.POST:
                cached = True

            detailed_info_enabled = (request.POST.get('detailed_info_enabled') is not None)
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
            external_layer.layer_group = layer_group
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
                params['get_map_url'] = request.POST.get('get_map_url')
                params['cache_url'] = server.getCacheEndpoint()
                params['layers'] = request.POST.get('layers')
                params['format'] = request.POST.get('format')
                params['infoformat'] = request.POST.get('infoformat')

            if external_layer.type == 'WMTS':
                params['matrixset'] = request.POST.get('matrixset')
                params['tilematrix'] = request.POST.get('tilematrix')
                params['capabilities'] = request.POST.get('capabilities')

            if external_layer.type == 'Bing':
                params['key'] = request.POST.get('key')
                params['layers'] = request.POST.get('layers')

            if external_layer.type == 'XYZ' or external_layer.type == 'OSM':
                params['url'] = request.POST.get('url')
                params['key'] = request.POST.get('key')

            #geographic_servers.get_instance().get_server_by_id(server.id).updateThumbnail(external_layer)
            external_layer.external_params = json.dumps(params)
            external_layer.save()

            if redirect_to_layergroup:
                # recalculate to_url since layergroup_id may change
                if project_id:
                    to_url = reverse('layergroup_update_with_project', kwargs={'lgid': layergroup_id, 'project_id': project_id}) + query_string
                else:
                    to_url = reverse('layergroup_update', kwargs={'lgid': layergroup_id}) + query_string
            else:
                to_url = back_url
            return HttpResponseRedirect(to_url)

        except Exception as e:
            try:
                msg = e.get_message()
            except:
                msg = _("Error: externallayer could not be published")
            form.add_error(None, msg)

            response= {
                'message': msg,
                'form': form,
                'external_layer': external_layer,
                'bing_layers': BING_LAYERS,
                'html': False,
                'redirect_to_layergroup': redirect_to_layergroup,
                'project_id': project_id,
                'layergroup_id': layergroup_id,
                'from_redirect': from_redirect,
                'back_url': back_url
            }

    else:
        form = ExternalLayerForm(request, instance=external_layer)

        if external_layer.external_params:
            params = json.loads(external_layer.external_params)
            for key in params:
                form.initial[key] = params[key]

        html = True
        if external_layer.detailed_info_html == None or external_layer.detailed_info_html == '' or external_layer.detailed_info_html == 'null':
            html = False

        if layergroup_id:
            form.fields['layer_group'].queryset = form.fields['layer_group'].queryset.filter(id=layergroup_id)
        response= {
            'form': form,
            'external_layer': external_layer,
            'bing_layers': BING_LAYERS,
            'html': html,
            'redirect_to_layergroup': redirect_to_layergroup,
            'project_id': project_id,
            'layergroup_id': layergroup_id,
            'from_redirect': from_redirect,
            'back_url': back_url
        }

    return render(request, 'external_layer_update.html', response)



@login_required()
@require_POST
@staff_required
def external_layer_delete(request, external_layer_id):
    external_layer = Layer.objects.get(id=external_layer_id)
    if not utils.can_manage_layer(request, external_layer):
        return forbidden_view(request)
    try:
        server = Server.objects.get(id=external_layer.layer_group.server_id)
        master_node = geographic_servers.get_instance().get_master_node(server.id)
        if external_layer.cached:
            if external_layer.type == 'WMS':
                geowebcache.get_instance().delete_layer(None, external_layer, server, master_node.getUrl())
            geographic_servers.get_instance().get_server_by_id(server.id).reload_nodes()

        external_layer.delete()
        return redirect('external_layer_list')

    except Exception as e:
        if e.server_message:
            if 'Unknown layer' in e.server_message:
                external_layer.delete()
                return redirect('external_layer_list')

        return HttpResponse('Error deleting external_layer: ' + str(e), status=500)



def ows_get_capabilities(url, service, version, layer, remove_extra_params=True):
    if remove_extra_params:
        # remove any param in the query string
        urlObj = urlparse(url)
        url = urlObj.scheme + '://' + urlObj.netloc + urlObj.path

    layers = []
    formats = []
    infoformats = []
    styles = []
    matrixsets = []
    capabilities = None
    title = ''
    crs_list = None
    get_map_url = url
    matrix = {}

    auth = Authentication(verify=False)
    try:
        if service == 'WMS':
            if not version:
                try:
                    response = requests.get(url)
                    data = xmltodict.parse(response.content)
                    version = data['WMT_MS_Capabilities']['@version']
                except:
                    version = WMS_MAX_VERSION

            print('Add base layer: ' + url+ ', version: ' + version)
            wms = WebMapService(url, version=version, auth=auth)

            print('Add base layer type ' + wms.identification.type)
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

            get_map_url = wms.getOperationByName('GetMap').methods[0]['url']

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

        elif service == 'WMTS':
            if not version:
                version = WMTS_MAX_VERSION
            wmts = WebMapTileService(url, version=version, auth=auth)
            title = wmts.identification.title
            try:
                capabilities = etree.tostring(wmts._capabilities, encoding='unicode')
            except:
                capabilities = wmts.getServiceXML()
                capabilities = capabilities.decode('utf-8')

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
                        
                    if hasattr(lyr, 'tilematrixsetlinks') and lyr.tilematrixsetlinks and lyr.tilematrixsetlinks[matrixset]:
                        tilematrixsetlinks = lyr.tilematrixsetlinks[matrixset]
                        if hasattr(tilematrixsetlinks, 'tilematrixlimits'):
                            tilematrixlimits = tilematrixsetlinks.tilematrixlimits
                            if tilematrixlimits and isinstance(tilematrixlimits, dict):
                                matrix[matrixset] = get_json_tilematrix(tilematrixlimits)
                                #print("Tile matrix LINK: " + matrixset + " @ " + str(matrix[matrixset]))

                    if len(matrix) == 0 and hasattr(wmts, 'tilematrixsets') and wmts.tilematrixsets and wmts.tilematrixsets[matrixset]:
                        tilematrixset = wmts.tilematrixsets[matrixset]
                        if hasattr(tilematrixset, 'tilematrix'):
                            tilematrix = tilematrixset.tilematrix
                            if tilematrix and isinstance(tilematrix, dict):
                                matrix[matrixset] = get_json_tilematrix(tilematrix)
                                #print("Tile matrix:" + str(matrix[matrixset]))

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
        logger.exception(str(e))
        data = {'response': '500',
            'message':  str(e)}
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
        'crs_list': crs_list,
        'get_map_url': get_map_url,
        'tilematrix' : matrix 
    }

    return data


def get_json_tilematrix(matrix):
    id = None
    mincol = 0
    minrow = 0
    maxcol = None
    maxrow = None
    result = []
    for i in matrix:
        level = matrix[i]
        if hasattr(level, 'identifier'):
            id = level.identifier
        elif hasattr(level, 'tilematrix'):
            id = level.tilematrix
        if hasattr(level, 'matrixheight') and hasattr(level, 'matrixwidth'):
            maxcol = level.matrixheight - 1
            maxrow = level.matrixwidth - 1
        elif hasattr(level, 'mintilerow') and hasattr(level, 'mintilecol'):
            mincol = level.mintilecol
            minrow = level.mintilerow
            maxcol = level.maxtilecol
            maxrow = level.maxtilerow
        
        # result.append({
        #     'id': id,
        #     'mincol': mincol,
        #     'minrow': minrow,
        #     'maxcol': maxcol,
        #     'maxrow': maxrow
        # })
        result.append(id)

    return result



@require_GET
def get_capabilities(request):
    url = request.GET.get('url')
    service = request.GET.get('type')
    version = request.GET.get('version')
    layer = request.GET.get('layer')

    data = ows_get_capabilities(url, service, version, layer)
    return HttpResponse(json.dumps(data, indent=4), content_type='application/json')

@login_required()
@require_POST
@staff_required
def get_capabilities_from_url(request):
    url = request.POST.get('url')
    service = request.POST.get('type')
    version = request.POST.get('version')
    layer = request.POST.get('layer')

    data = ows_get_capabilities(url, service, version, layer, False)


    return HttpResponse(json.dumps(data, indent=4), content_type='application/json')


@login_required()
@require_safe
@staff_required
def cache_list(request):

    layer_list = None
    group_list = None
    if request.user.is_superuser:
        layer_list = Layer.objects.filter(cached=True).exclude(type__in=['WMTS', 'XYZ']).order_by('id')
        group_list = LayerGroup.objects.filter(cached=True)
    else:
        user_roles = auth_backend.get_roles(request)
        layer_list = (Layer.objects.filter(created_by=request.user.username, cached=True)
            | Layer.objects.filter(layermanagerole__role__in=user_roles, cached=True)).exclude(type__in=['WMTS', 'XYZ']).order_by('id').distinct()
        group_list = utils.get_user_layergroups(request).filter(cached=True)
    response = {
        'layers': layer_list,
        'groups': group_list
    }
    return render(request, 'cache_list.html', response)

@login_required()
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def layer_cache_config(request, layer_id):
    layer = Layer.objects.get(id=int(layer_id))
    if not utils.can_manage_layer(request, layer):
        return forbidden_view(request)
    layer_group = LayerGroup.objects.get(id=layer.layer_group.id)
    server = Server.objects.get(id=layer_group.server_id)

    if request.method == 'POST':
        format = request.POST.get('input_format')
        grid_set = request.POST.get('input_grid_set')
        min_x = request.POST.get('min_x')
        min_y = request.POST.get('min_y')
        max_x = request.POST.get('max_x')
        max_y = request.POST.get('max_y')
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
            #gs.reload_nodes()

            if not layer.external:
                gs.updateBoundingBoxFromData(layer)
                gs.updateThumbnail(layer, 'update')

            layer_list = None
            if request.user.is_superuser:
                layer_list = Layer.objects.filter(cached=True).order_by('id')
            else:
                user_roles = auth_backend.get_roles(request)
                layer_list = (Layer.objects.filter(created_by=request.user.username, cached=True)
                    | Layer.objects.filter(layermanagerole__role__in=user_roles, cached=True)).exclude(type__in=['WMTS', 'XYZ']).order_by('id').distinct()

            response = {
                'layers': layer_list
            }
            return render(request, 'cache_list.html', response)

        except Exception as e:
            error_message = ugettext_lazy('Error configuring layer. Cause: {cause}.').format(cause=str(e))
            logger.exception(error_message)
            messages.error(request, error_message)
            response = HttpResponseRedirect(request.path)
            response.status_code = 303
            return response
            #response = HttpResponse(content="", status=303)
            #response["Location"] = request.path
            #return redirect('cache_list')
            #redirect_class = HttpResponsePermanentRedirect if permanent else HttpResponseRedirect
            response = HttpResponseRedirect(request.path)
            response.status_code = 303
            return response

            """
            message = e
            config = None
            tasks = None
            master_node = geographic_servers.get_instance().get_master_node(server.id)
            if layer.external:
                #config = geowebcache.get_instance().get_layer(None, layer, server, master_node.getUrl()).get('wmsLayer')
                tasks = geowebcache.get_instance().get_pending_and_running_tasks(None, layer, server, master_node.getUrl())
            else:
                #config = geowebcache.get_instance().get_layer(layer.datastore.workspace.name, layer, server, master_node.getUrl()).get('GeoServerLayer')
                tasks = geowebcache.get_instance().get_pending_and_running_tasks(layer.datastore.workspace.name, layer, server, master_node.getUrl())

            response = {
                "message": message,
                "layer_id": layer_id,
                "max_zoom_level": list(range(settings.MAX_ZOOM_LEVEL + 1)),
                "grid_subsets": settings.CACHE_OPTIONS['GRID_SUBSETS'],
                "json_grid_subsets": json.dumps(settings.CACHE_OPTIONS['GRID_SUBSETS']),
                "formats": settings.CACHE_OPTIONS['FORMATS'],
                "tasks": tasks['long-array-array']
            }

            return render(request, 'layer_cache_config.html', response)

            """


    else:
        try:
            config = None
            tasks = None
            master_node = geographic_servers.get_instance().get_master_node(server.id)
            if layer.external:
                #config = geowebcache.get_instance().get_layer(None, layer, server, master_node.getUrl()).get('wmsLayer')
                tasks = geowebcache.get_instance().get_pending_and_running_tasks(None, layer, server, master_node.getUrl())
            else:
                #config = geowebcache.get_instance().get_layer(layer.datastore.workspace.name, layer, server, master_node.getUrl()).get('GeoServerLayer')
                tasks = geowebcache.get_instance().get_pending_and_running_tasks(layer.datastore.workspace.name, layer, server, master_node.getUrl())

            response = {
                "layer_id": layer_id,
                "max_zoom_level": list(range(settings.MAX_ZOOM_LEVEL + 1)),
                "grid_subsets": settings.CACHE_OPTIONS['GRID_SUBSETS'],
                "json_grid_subsets": json.dumps(settings.CACHE_OPTIONS['GRID_SUBSETS']),
                "formats": settings.CACHE_OPTIONS['FORMATS'],
                "tasks": tasks['long-array-array'],
                "latlong_extent": layer.latlong_extent
            }

            return render(request, 'layer_cache_config.html', response)
        except Exception as e:
            error_message = ugettext_lazy('Error accessing layer. Cause: {cause}.').format(cause=str(e))
            logger.exception(error_message)
            messages.error(request, error_message)
            return redirect('cache_list')

@login_required()
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def group_cache_config(request, group_id):
    layer_group = LayerGroup.objects.get(id=int(group_id))
    server = Server.objects.get(id=layer_group.server_id)
    if not utils.can_manage_layergroup(request.user, layer_group):
        return forbidden_view(request)
    if request.method == 'POST':
        format = request.POST.get('input_format')
        grid_set = request.POST.get('input_grid_set')
        min_x = request.POST.get('min_x')
        min_y = request.POST.get('min_y')
        max_x = request.POST.get('max_x')
        max_y = request.POST.get('max_y')
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
                group_list = utils.get_user_layergroups(request).filter(cached=True)
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

            #config = geowebcache.get_instance().get_group(layer_group, server, master_node.getUrl()).get('GeoServerLayer')
            tasks = geowebcache.get_instance().get_group_pending_and_running_tasks(layer_group, server, master_node.getUrl())

            response = {
                "message": message,
                "group_id": group_id,
                "max_zoom_level": list(range(settings.MAX_ZOOM_LEVEL + 1)),
                "grid_subsets": settings.CACHE_OPTIONS['GRID_SUBSETS'],
                "json_grid_subsets": json.dumps(settings.CACHE_OPTIONS['GRID_SUBSETS']),
                "formats": settings.CACHE_OPTIONS['FORMATS'],
                "tasks": tasks['long-array-array']
            }

            return render(request, 'group_cache_config.html', response)




    else:
        try:
            config = None
            tasks = None
            master_node = geographic_servers.get_instance().get_master_node(server.id)

            #config = geowebcache.get_instance().get_group(layer_group, server, master_node.getUrl()).get('GeoServerLayer')
            tasks = geowebcache.get_instance().get_group_pending_and_running_tasks(layer_group, server, master_node.getUrl())

            response = {
                "group_id": group_id,
                "max_zoom_level": list(range(settings.MAX_ZOOM_LEVEL + 1)),
                "grid_subsets": settings.CACHE_OPTIONS['GRID_SUBSETS'],
                "json_grid_subsets": json.dumps(settings.CACHE_OPTIONS['GRID_SUBSETS']),
                "formats": settings.CACHE_OPTIONS['FORMATS'],
                "tasks": tasks['long-array-array']
            }

            return render(request, 'group_cache_config.html', response)
        except Exception as e:
            error_message = ugettext_lazy('Error accessing layer group. Cause: {cause}.').format(cause=str(e))
            logger.exception(error_message)
            messages.error(request, error_message)
            return redirect('cache_list')

@login_required()
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

@login_required()
@require_POST
@staff_required
def get_group_cache_tasks(request):
    group_id = request.POST.get('group_id')
    layer_group = LayerGroup.objects.get(id=int(group_id))
    server = Server.objects.get(id=layer_group.server_id)
    master_node = geographic_servers.get_instance().get_master_node(server.id)

    tasks = geowebcache.get_instance().get_group_pending_and_running_tasks(layer_group, server, master_node.getUrl())

    return HttpResponse(json.dumps(tasks, indent=4), content_type='application/json')

@login_required()
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

@login_required()
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

@login_required()
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def update_thumbnail(request, layer_id):
    try:
        layer = Layer.objects.get(id=int(layer_id))
        if not utils.can_manage_layer(request, layer):
            return HttpResponse(json.dumps({'success': False}, indent=4), content_type='application/json')
        layer_group = LayerGroup.objects.get(id=layer.layer_group.id)
        server = Server.objects.get(id=layer_group.server_id)
        gs = geographic_servers.get_instance().get_server_by_id(server.id)
        layer = gs.updateThumbnail(layer, 'update')
        return HttpResponse(json.dumps({'success': True, 'updated_thumbnail': layer.thumbnail.url.replace(settings.BASE_URL, '')}, indent=4), content_type='application/json')
    except Exception as e:
        print(str(e))
        return HttpResponse(json.dumps({'success': False}, indent=4), content_type='application/json')


@login_required()
@require_safe
@superuser_required
def service_url_list(request):
    response = {
        'services': list(ServiceUrl.objects.values())
    }
    return render(request, 'service_url_list.html', response)

@login_required()
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

@login_required()
@require_POST
@superuser_required
def service_url_delete(request, svid):
    try:
        service_url = ServiceUrl.objects.get(id=svid)
        service_url.delete()
        return HttpResponseRedirect(reverse('service_url_list'))

    except Exception as e:
        print(str(e))
        return HttpResponseNotFound(str(e) )


@login_required()
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

@login_required()
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
                    'error': str(e),
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
        try:
            if workspace:
                layer = Layer.objects.get(name=layer_name, datastore__workspace__name=workspace)
            else:
                layer = Layer.objects.get(name=layer_name, external=True)

            if request.user.is_anonymous:
                action.send(layer, verb="gvsigol_services/layer_activate", action_object=layer)
            else:
                action.send(request.user, verb="gvsigol_services/layer_activate", action_object=layer)
        except:
            logger.exception(f"register action - layer: {layer_name} - ws: {workspace}")
        return HttpResponse(json.dumps({'success': True}, indent=4), content_type='application/json')

@login_required()
@staff_required
def db_field_delete(request):
    if request.method == 'POST':
        try:
            field = request.POST.get('field')
            #layer_name = request.POST['layer_name']
            layer_id = request.POST.get('layer_id')
            layer = Layer.objects.get(id=layer_id)
            if not utils.can_manage_layer(request, layer):
                return HttpResponseForbidden('{"response": "Not authorized"}', content_type='application/json')
            if (layer.datastore.type != 'v_PostGIS'):
                return utils.get_exception(400, 'Error in the input params')
            for ctrl_field in settings.CONTROL_FIELDS:
                if field == ctrl_field.get('name'):
                    return utils.get_exception(400, _('Control field "{0}" cannot be deleted').format(field))
            params = json.loads(layer.datastore.connection_params)
            con = Introspect(database=params['database'], host=params['host'], port=params['port'], user=params['user'], password=params['passwd'])
            schema = params.get('schema', 'public')
            con.delete_column(schema, layer.source_name, field)
            con.close()

            layer_conf = ast.literal_eval(layer.conf) if layer.conf else {}
            for f in layer_conf.get('fields', []):
                if f['name'] == field:
                    layer_conf.get('fields').remove(f)
            layer.conf = layer_conf
            layer.save()
            LayerFieldEnumeration.objects.filter(layer=layer, field=field).delete()
            triggers = Trigger.objects.filter(layer=layer, field=field)
            for trigger in triggers:
                trigger.drop()
            triggers.delete()


            gs = geographic_servers.get_instance().get_server_by_id(layer.datastore.workspace.server.id)
            gs.reload_featuretype(layer, nativeBoundingBox=False, latLonBoundingBox=False)
            gs.reload_nodes()
            return HttpResponse('{"response": "ok"}', content_type='application/json')
        except psycopg2.ProgrammingError as e:
            logger.exception(_('Error renaming field. Cause: {0}').format(str(e)))
            if e.pgcode == '42703':
                return utils.get_exception(400, _('Field does not exist. Probably, it was deleted or renamed concurrently by another user'))
        except Exception as e:
            logger.exception(_('Error deleting field. Cause: {0}').format(str(e)))
    return utils.get_exception(400, 'Error in the input params')

"""
@login_required()
@staff_required
def db_field_changetype(request):
    pass
"""

@login_required()
@staff_required
def db_field_rename(request):
    if request.method == 'POST':
        try:
            field = request.POST.get('field')
            new_field_name = request.POST.get('new_field_name').lower()
            if _valid_sql_name_regex.search(new_field_name) == None:
                utils.get_exception(400, 'Invalid field name: {fname}. Fields must begin with a letter or an underscore (_). Subsequent characters can be letters, underscores or numbers'.format(fname=new_field_name))
            layer_id = request.POST.get('layer_id')
            layer = Layer.objects.get(id=layer_id)
            if not utils.can_manage_layer(request, layer):
                return HttpResponseForbidden('{"response": "Not authorized"}', content_type='application/json')
            if not (layer.datastore.type == 'v_PostGIS'):
                return utils.get_exception(400, 'Error in the input params')
            for ctrl_field in settings.CONTROL_FIELDS:
                if field == ctrl_field.get('name'):
                    return utils.get_exception(400, _('Control field "{0}" cannot be renamed').format(field))
                elif new_field_name == ctrl_field.get('name'):
                    return utils.get_exception(400, _('The field name "{0}" is a reserved name').format(field))
            params = json.loads(layer.datastore.connection_params)
            con = Introspect(database=params['database'], host=params['host'], port=params['port'], user=params['user'], password=params['passwd'])
            schema = params.get('schema', 'public')
            con.rename_column(schema, layer.source_name, field, new_field_name)
            con.close()

            layer_conf = ast.literal_eval(layer.conf) if layer.conf else {}
            for f in layer_conf.get('fields', []):
                if f['name'] == field:
                    f['name'] = new_field_name
            layer.conf = layer_conf
            layer.save()

            for enumDef in LayerFieldEnumeration.objects.filter(layer=layer, field=field):
                enumDef.field = new_field_name
                enumDef.save()

            for triggerDef in Trigger.objects.filter(layer=layer, field=field):
                triggerDef.drop()
                triggerDef.field = new_field_name
                triggerDef.save()
                triggerDef.install()

            gs = geographic_servers.get_instance().get_server_by_id(layer.datastore.workspace.server.id)
            gs.reload_featuretype(layer, nativeBoundingBox=False, latLonBoundingBox=False)
            gs.reload_nodes()
            return HttpResponse('{"response": "ok"}', content_type='application/json')
        except psycopg2.ProgrammingError as e:
            logger.exception(_('Error renaming field. Cause: {0}').format(str(e)))
            if e.pgcode == '42703':
                return utils.get_exception(400, _('Field does not exist. Probably, it was deleted or renamed concurrently by another user'))
        except rest_geoserver.RequestError as e:
            logger.exception(_('Error renaming field. Cause: {0}').format(e.get_detailed_message()))
        except Exception as e:
            logger.exception(_('Error renaming field. Cause: {0}').format(str(e)))
    return utils.get_exception(400, 'Error in the input params')

@login_required()
@staff_required
def db_save_field_format(request):
    if request.method == 'POST':
        try:
            field_name = request.POST.get('field')
            layer_id = request.POST.get('layer_id')
            symbol = request.POST.get('symbol', '')
            symbol_position = request.POST.get('symbol_position', 'after')
            decimal_places = request.POST.get('decimal_places', '2')
            thousands_separator = request.POST.get('thousands_separator', '')
            decimal_separator = request.POST.get('decimal_separator', ',')
            
            layer = Layer.objects.get(id=layer_id)
            
            if not utils.can_manage_layer(request, layer):
                return HttpResponseForbidden('{"response": "Not authorized"}', content_type='application/json')
            
            field_format = {
                'symbol': symbol,
                'symbol_position': symbol_position,
                'decimal_places': int(decimal_places),
                'thousands_separator': thousands_separator,
                'decimal_separator': decimal_separator
            }
            
            try:
                if layer.conf:
                    if isinstance(layer.conf, dict):
                        current_conf = layer.conf
                    elif isinstance(layer.conf, str):
                        try:
                            current_conf = ast.literal_eval(layer.conf)
                        except (ValueError, SyntaxError):
                            try:
                                current_conf = json.loads(layer.conf)
                            except json.JSONDecodeError:
                                logger.warning(f"Could not parse layer.conf for field {field_name}: {layer.conf}")
                                current_conf = {}
                    else:
                        current_conf = {}
                else:
                    current_conf = {}
                
                fields = current_conf.get('fields', [])
                field_updated = False
                
                for i, field in enumerate(fields):
                    if field.get('name') == field_name:
                        field['field_format'] = field_format
                        fields[i] = field
                        field_updated = True
                        break
                
                if not field_updated:
                    new_field = {
                        'name': field_name,
                        'field_format': field_format
                    }
                    fields.append(new_field)
                
                current_conf['fields'] = fields
                
                try:
                    layer.conf = current_conf
                except:
                    try:
                        layer.conf = json.dumps(current_conf)
                    except TypeError:
                        def convert_for_json(obj):
                            if isinstance(obj, bool):
                                return obj
                            elif isinstance(obj, dict):
                                return {k: convert_for_json(v) for k, v in obj.items()}
                            elif isinstance(obj, list):
                                return [convert_for_json(item) for item in obj]
                            else:
                                return obj
                        
                        converted_conf = convert_for_json(current_conf)
                        layer.conf = json.dumps(converted_conf)
                
                layer.save()
                return HttpResponse('{"response": "ok"}', content_type='application/json')
                
            except Exception as e:
                logger.warning(f"Error saving field_format for field {field_name}: {str(e)}")
                return utils.get_exception(400, f'Error saving field format: {str(e)}')
                
        except Exception as e:
            logger.exception(_('Error saving field format. Cause: {0}').format(str(e)))
            return utils.get_exception(400, f'Error saving field format: {str(e)}')
    
    return utils.get_exception(400, 'Error in the input params')

@login_required()
@staff_required
def db_delete_field_format(request):
    if request.method == 'POST':
        try:
            field_name = request.POST.get('field')
            layer_id = request.POST.get('layer_id')
            
            layer = Layer.objects.get(id=layer_id)
            
            if not utils.can_manage_layer(request, layer):
                return HttpResponseForbidden('{"response": "Not authorized"}', content_type='application/json')
            
            try:
                if layer.conf:
                    if isinstance(layer.conf, dict):
                        current_conf = layer.conf
                    elif isinstance(layer.conf, str):
                        try:
                            current_conf = ast.literal_eval(layer.conf)
                        except (ValueError, SyntaxError):
                            try:
                                current_conf = json.loads(layer.conf)
                            except json.JSONDecodeError:
                                logger.warning(f"Could not parse layer.conf for field {field_name}: {layer.conf}")
                                current_conf = {}
                    else:
                        current_conf = {}
                else:
                    current_conf = {}
                
                fields = current_conf.get('fields', [])
                field_updated = False
                
                for i, field in enumerate(fields):
                    if field.get('name') == field_name:
                        field['field_format'] = {}
                        field_updated = True
                        break
                
                # Solo actualizar si se encontró y modificó el campo
                if field_updated:
                    current_conf['fields'] = fields
                    
                    try:
                        layer.conf = current_conf
                    except:
                        try:
                            layer.conf = json.dumps(current_conf)
                        except TypeError:
                            def convert_for_json(obj):
                                if isinstance(obj, bool):
                                    return obj
                                elif isinstance(obj, dict):
                                    return {k: convert_for_json(v) for k, v in obj.items()}
                                elif isinstance(obj, list):
                                    return [convert_for_json(item) for item in obj]
                                else:
                                    return obj
                            
                            converted_conf = convert_for_json(current_conf)
                            layer.conf = json.dumps(converted_conf)
                    
                    layer.save()
                    return HttpResponse('{"response": "ok"}', content_type='application/json')
                else:
                    return HttpResponse('{"response": "ok"}', content_type='application/json')
                    
            except Exception as e:
                logger.warning(f"Error deleting field_format for field {field_name}: {str(e)}")
                return utils.get_exception(400, f'Error deleting field format: {str(e)}')
                
        except Exception as e:
            logger.exception(_('Error deleting field format. Cause: {0}').format(str(e)))
            return utils.get_exception(400, f'Error deleting field format: {str(e)}')
    
    return utils.get_exception(400, 'Error in the input params')

@login_required()
@staff_required
def get_field_format(request):
    if request.method == 'GET':
        try:
            field_name = request.GET.get('field')
            layer_id = request.GET.get('layer_id')
            
            layer = Layer.objects.get(id=layer_id)
            
            if not utils.can_manage_layer(request, layer):
                return HttpResponseForbidden('{"response": "Not authorized"}', content_type='application/json')
            
            try:
                if layer.conf:
                    if isinstance(layer.conf, dict):
                        current_conf = layer.conf
                    elif isinstance(layer.conf, str):
                        try:
                            current_conf = ast.literal_eval(layer.conf)
                        except (ValueError, SyntaxError):
                            try:
                                current_conf = json.loads(layer.conf)
                            except json.JSONDecodeError:
                                logger.warning(f"Could not parse layer.conf for field {field_name}: {layer.conf}")
                                current_conf = {}
                    else:
                        current_conf = {}
                else:
                    current_conf = {}
                
                fields = current_conf.get('fields', [])
                field_format = {}
                
                for field in fields:
                    if field.get('name') == field_name:
                        field_format = field.get('field_format', {})
                        break
                
                response_data = {
                    'status': 'success',
                    'field_format': field_format,
                    'has_format': bool(field_format)
                }
                
                return HttpResponse(json.dumps(response_data), content_type='application/json')
                    
            except Exception as e:
                logger.warning(f"Error getting field_format for field {field_name}: {str(e)}")
                return utils.get_exception(400, f'Error getting field format: {str(e)}')
                
        except Exception as e:
            logger.exception(_('Error getting field format. Cause: {0}').format(str(e)))
            return utils.get_exception(400, f'Error getting field format: {str(e)}')
    
    return utils.get_exception(400, 'Error in the input params')

@login_required()
@staff_required
def db_add_field(request):
    if request.method == 'POST':
        layer = None
        try:
            field_name = request.POST.get('field').lower()
            if _valid_sql_name_regex.search(field_name) == None:
                utils.get_exception(400, 'Invalid field name: {fname}. Fields must begin with a letter or an underscore (_). Subsequent characters can be letters, underscores or numbers'.format(fname=field_name))
            field_type = request.POST.get('type')
            layer_id = request.POST.get('layer_id')
            enumkey = request.POST.get('enumkey')
            calculation = request.POST.get('calculation')
            gvsigol_type = request.POST.get('gvsigol_type', '')
            type_params = request.POST.get('type_params', '{}')
            field_format = request.POST.get('field_format', '{}')
            layer = Layer.objects.get(id=layer_id)

            for ctrl_field in settings.CONTROL_FIELDS:
                if field_name == ctrl_field.get('name'):
                    return utils.get_exception(400, _('The field name "{0}" is a reserved name').format(field_name))

            if not utils.can_manage_layer(request, layer):
                return HttpResponseForbidden('{"response": "Not authorized"}', content_type='application/json')
            if not (layer.datastore.type == 'v_PostGIS'):
                return utils.get_exception(400, 'Error in the input params')
            params = json.loads(layer.datastore.connection_params)
            schema = params.get('schema', 'public')
            gs = geographic_servers.get_instance().get_server_by_id(layer.datastore.workspace.server.id)
            iconn = Introspect(database=params['database'], host=params['host'], port=params['port'], user=params['user'], password=params['passwd'])
            with iconn as con:
                sql_type = gs.gvsigol_to_sql_type(field_type)
                if not sql_type:
                    return utils.get_exception(400, _('Field type not supported'))
                try:
                    con.add_column(schema, layer.source_name, field_name, sql_type)
                except psycopg2.ProgrammingError as e:
                    logger.exception("Error adding field")
                    return utils.get_exception(400, _('Error adding field. Probably the field "{0}" already exists. Database message: {1}').format(field_name, str(e)))

            if enumkey:
                field_enum = LayerFieldEnumeration()
                field_enum.layer = layer
                field_enum.field = field_name
                field_enum.enumeration_id = int(enumkey)
                field_enum.multiple = True if field_type == 'multiple_enumeration' else False
                field_enum.save()
            if calculation:
                try:
                    procedure = TriggerProcedure.objects.get(signature=calculation)
                    trigger = Trigger()
                    trigger.layer = layer
                    trigger.field = field_name
                    trigger.procedure = procedure
                    trigger.save()

                    trigger.install()
                except:
                    logger.exception("Error creating trigger for calculated field")

            expose_pks = gs.datastore_check_exposed_pks(layer.datastore)
            gs.reload_featuretype(layer, nativeBoundingBox=False, latLonBoundingBox=False)
            gs.reload_nodes()
            layer.get_config_manager().refresh_field_conf(include_pks=expose_pks)
            
            # Guardar gvsigol_type y type_params en la configuración del campo
            try:
                if layer.conf:
                    if isinstance(layer.conf, dict):
                        current_conf = layer.conf
                    elif isinstance(layer.conf, str):
                        try:
                            current_conf = ast.literal_eval(layer.conf)
                        except (ValueError, SyntaxError):
                            try:
                                current_conf = json.loads(layer.conf)
                            except json.JSONDecodeError:
                                logger.warning(f"Could not parse layer.conf for field {field_name}: {layer.conf}")
                                current_conf = {}
                    else:
                        current_conf = {}
                else:
                    current_conf = {}
                
                fields = current_conf.get('fields', [])
                field_updated = False
                
                for i, field in enumerate(fields):
                    if field.get('name') == field_name:
                        field['gvsigol_type'] = gvsigol_type
                        
                        if type_params != '{}':
                            try:
                                type_params_dict = json.loads(type_params)
                                field['type_params'] = type_params_dict
                            except json.JSONDecodeError:
                                logger.warning(f"Invalid JSON in type_params for field {field_name}: {type_params}")
                                field['type_params'] = {}
                        else:
                            field['type_params'] = {}                        

                        # Guardar field_format
                        if field_format != '{}':
                            try:
                                field_format_dict = json.loads(field_format)
                                field['field_format'] = field_format_dict
                            except json.JSONDecodeError:
                                logger.warning(f"Invalid JSON in field_format for field {field_name}: {field_format}")
                                field['field_format'] = {}
                        else:
                            field['field_format'] = {}

                        if gvsigol_type == 'link':
                            field['editable'] = False
                            field['editableactive'] = False
                        
                        fields[i] = field
                        field_updated = True
                        break
                
                # Si no se encontró el campo, añadirlo
                if not field_updated:
                    new_field = {
                        'name': field_name,
                        'gvsigol_type': gvsigol_type,
                        'type_params': {},
                        'field_format': {}
                    }
                    
                    if type_params != '{}':
                        try:
                            type_params_dict = json.loads(type_params)
                            new_field['type_params'] = type_params_dict
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid JSON in type_params for field {field_name}: {type_params}")
                    
                    # Guardar field_format
                    if field_format != '{}':
                        try:
                            field_format_dict = json.loads(field_format)
                            new_field['field_format'] = field_format_dict
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid JSON in field_format for field {field_name}: {field_format}")
                    
                    if gvsigol_type == 'link':
                        new_field['editable'] = False
                        new_field['editableactive'] = False
                    
                    fields.append(new_field)
                
                # Actualizar solo la sección de campos en la configuración
                current_conf['fields'] = fields
                
                try:
                    layer.conf = current_conf
                except:
                    try:
                        layer.conf = json.dumps(current_conf)
                    except TypeError:
                        def convert_for_json(obj):
                            if isinstance(obj, bool):
                                return obj
                            elif isinstance(obj, dict):
                                return {k: convert_for_json(v) for k, v in obj.items()}
                            elif isinstance(obj, list):
                                return [convert_for_json(item) for item in obj]
                            else:
                                return obj
                        
                        converted_conf = convert_for_json(current_conf)
                        layer.conf = json.dumps(converted_conf)
                
                layer.save()

                
            except Exception as e:
                logger.warning(f"Error saving gvsigol_type/type_params for field {field_name}: {str(e)}")
            
            layer.save()
            return HttpResponse('{"response": "ok"}', content_type='application/json')
        except Exception as e:
            logger.exception(_('Error creating field. Cause: {0}').format(str(e)))

            # clean potential half created field
            if layer:
                LayerFieldEnumeration.objects.filter(layer=layer, field=field_name).delete()
            iconn = Introspect(database=params['database'], host=params['host'], port=params['port'], user=params['user'], password=params['passwd'])
            with iconn as con:
                schema = params.get('schema', 'public')
                con.delete_column(schema, layer.source_name, field_name)

    return utils.get_exception(400, 'Error in the input params')

@login_required()
@require_safe
@staff_required
def sqlview_list(request):
    if request.user.is_superuser:
        sql_views = SqlView.objects.all().order_by('name')
    else:
        sql_views = SqlView.objects.filter(created_by=request.user.username).order_by('name')
    response = {
        'sqlviews': sql_views
    }
    return render(request, 'sqlview_list.html', response)

@login_required()
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def sqlview_update(request, view_id):
    sql_view = SqlView.objects.get(pk=view_id)
    return _sqlview_update(request, True, sql_view)

@login_required()
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def sqlview_add(request):
    return _sqlview_update(request, False)

def _check_join_field_types(from_def):
    table_aliases = {}
    for idx, from_table in enumerate(from_def):
        alias = from_table.get('alias', from_table.get('name'))
        table_aliases[alias] = from_table
        if idx > 0:
            join_field1 = from_table.get('join_field1')
            table_alias = join_field1.get('table_alias')
            t = table_aliases.get(table_alias)
            ds = Datastore.objects.get(pk=t.get('datastore_id'))
            i, params = ds.get_db_connection()
            join_field1_type = None
            join_field2_type = None
            with i as c:
                info = c.get_fields_info(t.get('name'), schema=t.get('schema'))
            for field in info:
                if field.get('name') == join_field1.get('name'):
                    join_field1_type = field.get('type')
            join_field2 = from_table.get('join_field2')
            table_alias = join_field2.get('table_alias')
            t = table_aliases.get(table_alias)
            ds = Datastore.objects.get(pk=t.get('datastore_id'))
            i, params = ds.get_db_connection()
            with i as c:
                info = c.get_fields_info(t.get('name'), schema=t.get('schema'))
            for field in info:
                if field.get('name') == join_field2.get('name'):
                    join_field2_type = field.get('type')
            if join_field1_type != join_field2_type:
                return ugettext("Join fields must have the same type: {field1}({type1}) - {field2}({type2})".format(field1=join_field1.get('name'), type1=join_field1_type, field2=join_field2.get('name'), type2=join_field2_type))
    return ""


def _sqlview_update(request, is_update, sql_view=None):
    view_id = ''
    if request.method == 'POST':
        if sql_view is None:
            sql_view = SqlView()
            sql_view.created_by = request.user.username
            form = SqlViewForm(request.user, request.POST)
        else:
            form = SqlViewForm(request.user, request.POST, instance=sql_view)
            if not request.user.is_superuser and sql_view.created_by != request.user.username:
                form.add_error(None, ugettext_lazy("The user can't manage this SQL view"))
                raise Exception
            view_id = sql_view.id
        if form.is_valid():
            try:
                sql_view.name = form.cleaned_data.get('name')
                sql_view.datastore = form.cleaned_data.get('datastore')
                target_datastore_params = json.loads(sql_view.datastore.connection_params)
                target_schema = target_datastore_params.get('schema', 'public')
                from_objs = []
                table_fields = {}
                field_aliases = {}
                pks = []
                main_table = None
                from_def = []
                for idx, table in enumerate(form.cleaned_data.get('from_tables')):
                    table_alias = table.get('alias')
                    table_name = table.get('name')
                    field_aliases[table_alias] = {}
                    ds = Datastore.objects.get(pk=int(table.get('datastore_id')))
                    if not utils.can_manage_datastore(request.user, ds):
                        return HttpResponseForbidden("The user can't manage this datastore: {}".format(table.get('datastore_id')))
                    i, params = ds.get_db_connection()
                    schema = params.get('schema', 'public')
                    with i as c:
                        if idx == 0:
                            pks = c.get_pk_columns(table_name, schema=schema)
                            if len(pks) == 0:
                                form.add_error(None, ugettext_lazy('The main table must have a primary key'))
                                raise Exception
                            main_table = table_alias
                        table_fields[table_alias] = c.get_fields(table_name, schema=schema)

                    if idx > 0:
                        join_field1 = table.get('join_field1')
                        join_field2 = table.get('join_field2')
                        join_fields = [
                            SqlJoinFields(
                                SqlField(join_field1.get('table_alias'), join_field1.get('name')),
                                SqlField(join_field2.get('table_alias'), join_field2.get('name'))
                            )
                        ]
                    else:
                        join_fields = None

                    ft_obj = SqlFrom(schema, table_name, table_alias, join_fields=join_fields)
                    ft_json = ft_obj.to_json()
                    ft_json['datastore_id'] = ds.id
                    ft_json['datastore_name'] = str(ds)
                    from_def.append(ft_json)
                    from_objs.append(ft_obj)

                field_objs = []
                for idx, field in enumerate(form.cleaned_data.get('fields')):
                    table_alias = field.get('table_alias')
                    field_name = field.get('name')
                    field_alias = field.get('alias')
                    if not field_name in table_fields[table_alias]:
                        form.add_error(None, ugettext_lazy('Field does not exist: {field}').format(field_name))
                        raise Exception

                    field_obj = SqlField(table_alias, field_name, field_alias)

                    field_objs.append(field_obj)
                    field_aliases[table_alias][field_name] = field_alias
                try:
                    pk_aliases = [ field_aliases[main_table][p] for p in pks]
                except:
                    form.add_error(None, ugettext_lazy('The field {field} is the primary key of main table and must be included').format(field=", ".join(pks)))
                    raise Exception
                field_defs = [ f.to_json() for f in field_objs]
                sql_view.json_def = {
                    'fields':field_defs,
                    'from': from_def,
                    'pks': pk_aliases
                }
                sql_view.save()
                view_id = sql_view.id
                # re-set the form in case there are some error after this point
                form.cleaned_data['from_tables'] = json.dumps(sql_view.json_def['from'])
                form.cleaned_data['fields'] = json.dumps(sql_view.json_def['fields'])
                try:
                    i, params = sql_view.datastore.get_db_connection()
                    with i as c:
                        if c.object_exists(target_schema, sql_view.name):
                            if is_update:
                                c.delete_view(target_schema, sql_view.name)
                            else:
                                form.add_error(None, ugettext_lazy('An object already exists with name: {}').format(sql_view.name))
                                raise Exception
                        if not c.create_view(target_schema, sql_view.name, from_objs, field_objs):
                            msg = _check_join_field_types(from_def)
                            if msg:
                                form.add_error(None, msg)
                            else:
                                form.add_error(None, ugettext_lazy('The view could not be created'))
                            raise Exception
                        if is_update: # delete and insert again in case the pk field has a new alias
                            c.delete_geoserver_view_pk_columns(target_schema, sql_view.name)
                        if not c.insert_geoserver_view_pk_columns(target_schema, sql_view.name, pk_aliases):
                            form.add_error(None, ugettext_lazy('Pk columns could not be inserted'))
                            raise Exception
                        # TODO: we should add indexes to the join fields to ensure optimal performance
                        # TODO: maybe we should warn the user if a view name is changed and some layer relies in the old name
                        # TODO: maybe we should warn the user if a view is deleted and some layer relies in the old name
                    return redirect('sqlview_list')
                except Exception as e:
                    logger.exception("error")
                    if len(form.errors) == 0:
                        form.add_error(None, str(e))
                    if not is_update:
                        i, params = sql_view.datastore.get_db_connection()
                        with i as c:
                            c.delete_view(target_schema, sql_view.name)
                            c.delete_geoserver_view_pk_columns(target_schema, sql_view.name)
                        sql_view.delete()
                        view_id = ''

            except Exception as e:
                logger.exception(str(e))
                if len(form.errors) == 0:
                    form.add_error(None, str(e))
    else:
        if sql_view is None:
            form = SqlViewForm(request.user)
        else:
            initial = {'from_tables': json.dumps(sql_view.json_def['from']), 'fields': json.dumps(sql_view.json_def['fields'])}
            form = SqlViewForm(request.user, initial=initial, instance=sql_view)
            view_id = sql_view.id
        if not request.user.is_superuser:
            form.fields['datastore'].queryset = (Datastore.objects.filter(created_by=request.user.username, type__startswith='v_') |
                  Datastore.objects.filter(defaultuserdatastore__username=request.user.username, type__startswith='v_')).order_by('name').distinct()
    return render(request, 'sqlview_add.html', {
            'form': form,
            'view_id': view_id,
            'is_update': is_update
        })

@login_required()
@require_http_methods(["POST", "HEAD"])
@staff_required
def sqlview_delete(request, view_id):
    if request.method == 'POST':
        try:
            view = SqlView.objects.get(pk=view_id)
            if not request.user.is_superuser and view.created_by != request.user.username:
                return HttpResponseForbidden(_('Not allowed'))
            i, params = view.datastore.get_db_connection()
            schema = params.get('schema', 'public')
            with i as c:
                c.delete_view(schema, view.name)
                c.delete_geoserver_view_pk_columns(schema, view.name)
            view.delete()
            return HttpResponseRedirect(reverse('sqlview_list'))
        except Exception as e:
            logger.exception(str(e))
            return HttpResponseBadRequest(_('Error deleting view: {0}').format(view_id))

@login_required()
@staff_required
def list_datastore_tables(request):
    """
    Lists the tables existing on a data store.
    """
    if 'id_datastore' in request.GET:
        id_ds = request.GET['id_datastore']
        ds = Datastore.objects.get(id=id_ds)
        if not utils.can_manage_datastore(request.user, ds):
            return HttpResponseForbidden(json.dumps([]))
        if ds:
            c, params = ds.get_db_connection()
            i = utils.get_db_connect_from_datastore(ds)
            with c as i:
                schema = params.get('schema', 'public')
                tables = sorted(i.get_tables(schema))
                return HttpResponse(json.dumps(tables))
    return HttpResponseBadRequest()

@login_required()
@staff_required
def list_table_columns(request):
    """
    Lists the column names of a given table.

    Parameters
    ----------
    id_datastore: str
        The id of the datastore that contains the table
    table : str
        The table name
    """
    if 'id_datastore' in request.GET:
        id_ds = request.GET['id_datastore']
        table = request.GET['table']
        ds = Datastore.objects.get(id=id_ds)
        if not utils.can_manage_datastore(request.user, ds):
            return HttpResponseForbidden(json.dumps([]))
        if ds:
            c, params = ds.get_db_connection()
            i = utils.get_db_connect_from_datastore(ds)
            with c as i:
                schema = params.get('schema', 'public')
                columns = sorted(i.get_fields(table, schema=schema))
                return HttpResponse(json.dumps(columns))
    return HttpResponseBadRequest()

@login_required()
@staff_required
def list_datastores_in_db(request):
    """
    Lists the datastores that belong to the same database
    as the provided datastore.
    """
    if 'id_datastore' in request.GET:
        id_ds = request.GET['id_datastore']
        ds = Datastore.objects.get(id=id_ds)
        if not utils.can_manage_datastore(request.user, ds):
            return HttpResponseForbidden(json.dumps([]))
        params = json.loads(ds.connection_params)
        host = params.get('host')
        port = params.get('port')
        database = params.get('database')
        if request.user.is_superuser:
            datastore_list = Datastore.objects.filter(type__startswith='v_').order_by('name')
        else:
            datastore_list =  (Datastore.objects.filter(created_by=request.user.username, type__startswith='v_') |
                  Datastore.objects.filter(defaultuserdatastore__username=request.user.username, type__startswith='v_')).order_by('name').distinct()
        filtered_datastores = []
        for datastore in datastore_list:
            params = json.loads(datastore.connection_params)
            if params.get('host') == host and \
               params.get('port') == port and \
                params.get('database') == database:
                    filtered_datastores.append({"id": datastore.id, "name": str(datastore)})

        return HttpResponse(json.dumps(filtered_datastores))
    return HttpResponseBadRequest()

def test_dnie(request):
    cert_s_dn = request.META.get('HTTP_X_SSL_CLIENT_S_DN')
    print(request.META.get('HTTP_X_SSL_CLIENT_VERIFY'))
    if cert_s_dn:
        nif = ''
        for i in cert_s_dn.split(","):
            if i.startswith("serialNumber="):
                nif = i[len("serialNumber="):]
                if len(nif) != 9:
                    if len(nif) == 15:
                        prefix = 'IDCES-' # prefijo FNMT
                        if nif.startswith(prefix):
                            nif = nif[len(prefix):]
        response = "DNI: {}<br>S_DN: {}".format(nif, cert_s_dn)
        return HttpResponse(response)
    return HttpResponse("No autenticado")

def test_dnie2(request):
    # este método debe mostrar no validado ya que se accede por una URL que no activa el certificado
    return test_dnie(request)

def test_dnie_external(request):
    response = ""
    for header, value in request.headers.items():
        response += "{}: {}<br>".format(header, value)
    return HttpResponse(response)

@never_cache
def download_layer_resources(request, workspace_name, layer_name):
    try:
        layer = Layer.objects.get(name=layer_name, datastore__workspace__name=workspace_name)
        gs = geographic_servers.get_instance().get_server_by_id(layer.datastore.workspace.server.id)
        authz = gs.getAuthorizationService()
        if not utils.can_read_layer(request, layer):
            return JsonResponse({"status": "error", "Error": "You are not allowed to read this layer"}, status=403)
        readable_ids = authz.get_readable_feature_ids(request, layer)
        if readable_ids is None:
            layer_resources = LayerResource.objects.all()
        else:
            layer_resources = LayerResource.objects.filter(feature__in=readable_ids)
        paths = []
        for resource in layer_resources:
            localpath = resource.get_abspath()
            if os.path.exists(localpath):
                respath = f"{layer.id}_{layer.name}/{resource.feature}_{os.path.basename(resource.path)}"
                paths.append({
                    "fs": localpath,
                    "n": respath
                })

        # using zipfly and StreamingHttpResponse to stream the zip on the fly instead of creating
        # the file and then sending it
        zfly = zipfly.ZipFly(paths=paths)
        z = zfly.generator()

        # django streaming
        response = StreamingHttpResponse(z, content_type='application/octet-stream')
        # response = StreamingHttpResponse(z, content_type='application/zip')
        response['Content-Disposition'] = f"attachment; filename={layer.id}_{layer.name}.zip"
        return response
    except Layer.DoesNotExist:
        return JsonResponse({"status": "error", "Error": 'Layer not found'}, status=404)
    except Exception as e:
        return JsonResponse({"status": "error", "Error": str(e)}, status=500)


@login_required
def get_topology_available_layers(request, layer_id):
    """
    Obtiene todas las capas disponibles de la misma base de datos que la capa actual.
    Solo devuelve capas que tengan geometría, en formato datastore:nombretabla.
    """
    if request.method == 'GET':
        try:
            # Obtener la capa actual
            current_layer = Layer.objects.get(pk=layer_id)
            current_datastore = current_layer.datastore
            
            # Obtener parámetros de conexión de la capa actual
            current_params = json.loads(current_datastore.connection_params)
            current_host = current_params.get('host')
            current_port = current_params.get('port')
            current_database = current_params.get('database')
            
            # Buscar todos los datastores con los mismos parámetros de conexión
            available_layers = []
            
            for datastore in Datastore.objects.all():
                try:
                    ds_params = json.loads(datastore.connection_params)
                    # Comparar host, port y database (excluyendo schema)
                    if (ds_params.get('host') == current_host and 
                        ds_params.get('port') == current_port and 
                        ds_params.get('database') == current_database):
                        
                        # Obtener conexión a la base de datos
                        i, params = datastore.get_db_connection()
                        schema = params.get('schema', 'public')
                        
                        # Obtener todas las tablas con geometría de este esquema
                        with i:
                            geom_tables_info = i.get_geometry_columns_info(schema=schema)
                            
                            for table_info in geom_tables_info:
                                table_schema, table_name, geom_column, coord_dimension, srid, geom_type, key_column, fields = table_info
                                
                                # Crear identificador único: datastore:tabla
                                layer_identifier = f"{datastore.name}:{table_name}"
                                
                                # Excluir la capa actual (comparar tanto por datastore:tabla como por nombre directo)
                                if (layer_identifier == f"{current_datastore.name}:{current_layer.source_name}" or 
                                    table_name == current_layer.source_name):
                                    continue
                                
                                # Usar formato datastore:nametable para el display
                                display_name = layer_identifier
                                
                                # Verificar si existe una capa Layer para esta tabla (para metadatos adicionales)
                                layer_title = None
                                try:
                                    existing_layer = Layer.objects.filter(
                                        datastore=datastore, 
                                        source_name=table_name
                                    ).first()
                                    if existing_layer:
                                        layer_title = existing_layer.title
                                except:
                                    pass
                                
                                available_layers.append({
                                    'id': layer_identifier,
                                    'name': display_name,  # datastore:nametable format
                                    'table_name': table_name,
                                    'schema': table_schema,
                                    'datastore': datastore.name,
                                    'geom_type': geom_type,
                                    'workspace': datastore.workspace.name,
                                    'layer_title': layer_title  # Título de la capa si existe
                                })
                                
                except Exception as e:
                    # Si hay error al procesar un datastore, continuar con el siguiente
                    logger.warning(f"Error procesando datastore {datastore.name}: {str(e)}")
                    continue
            
            # Ordenar por nombre para mejor experiencia de usuario
            available_layers.sort(key=lambda x: x['name'])
            
            return JsonResponse({
                'status': 'success',
                'layers': available_layers,
                'current_layer_id': layer_id,
                'current_layer_name': f"{current_datastore.name}:{current_layer.source_name}",
                'total': len(available_layers)
            })
            
        except Layer.DoesNotExist:
            return JsonResponse({
                'status': 'error', 
                'message': 'Layer not found'
            }, status=404)
        except Exception as e:
            logger.error(f"Error in get_topology_available_layers: {str(e)}")
            return JsonResponse({
                'status': 'error', 
                'message': 'Internal server error'
            }, status=500)
    
    return JsonResponse({
        'status': 'error', 
        'message': 'Method not allowed'
    }, status=405)



@login_required
def get_topology_rules(request, layer_id):
    """
    Obtiene las reglas topológicas existentes para una capa específica
    """
    if request.method == 'GET':
        try:
            # Obtener la capa
            layer = Layer.objects.get(pk=layer_id)
            
            # Valores por defecto
            rules_data = {
                'no_overlap': False,
                'no_gaps': False,
                'must_be_covered_by': False,
                'covered_by_layer': '',
                'must_not_overlap_with': False,
                'overlap_layers': [],
                'must_be_contiguous': False,
                'contiguous_tolerance': 1.0
            }
            
            active_rules_count = 0
            
            try:
                # Obtener la configuración de topología para esta capa
                topology_config = LayerTopologyConfiguration.objects.get(layer=layer)
                
                # Función auxiliar para convertir de schema.tabla a datastore:tabla
                def convert_to_display_format(layer_name):
                    """
                    Convierte de formato 'schema.tabla' a 'datastore:tabla' para mostrar en el frontend
                    """
                    if not layer_name or '.' not in layer_name:
                        return layer_name
                    
                    try:
                        schema, table_name = layer_name.split('.', 1)
                        # Buscar un datastore que use este schema
                        for datastore in Datastore.objects.all():
                            try:
                                params = json.loads(datastore.connection_params)
                                if params.get('schema', 'public') == schema:
                                    return f"{datastore.name}:{table_name}"
                            except:
                                continue
                        # Si no se encuentra, devolver el original
                        return layer_name
                    except Exception as e:
                        logger.warning(f"Error convirtiendo formato de visualización {layer_name}: {str(e)}")
                        return layer_name
                
                # Convertir covered_by_layer a formato de visualización
                covered_by_layer_display = convert_to_display_format(topology_config.covered_by_layer or '')
                
                # Convertir overlap_layers a formato de visualización
                overlap_layers_display = []
                for layer_name in topology_config.overlap_layers:
                    converted = convert_to_display_format(layer_name)
                    if converted:
                        overlap_layers_display.append(converted)
                
                # Actualizar con los datos guardados (convertidos para visualización)
                rules_data = {
                    'no_overlap': topology_config.no_overlap,
                    'no_gaps': topology_config.no_gaps,
                    'must_be_covered_by': topology_config.must_be_covered_by,
                    'covered_by_layer': covered_by_layer_display,
                    'must_not_overlap_with': topology_config.must_not_overlap_with,
                    'overlap_layers': overlap_layers_display,
                    'must_be_contiguous': topology_config.must_be_contiguous,
                    'contiguous_tolerance': topology_config.contiguous_tolerance
                }
                active_rules_count = topology_config.get_active_rules_count()
                
            except LayerTopologyConfiguration.DoesNotExist:
                # No hay configuración guardada, usar valores por defecto
                pass
            
            return JsonResponse({
                'status': 'success',
                'rules': rules_data,
                'layer_id': layer_id,
                'total_rules': active_rules_count
            })
            
        except Layer.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Layer not found'
            }, status=404)
        except Exception as e:
            logger.error(f"Error getting topology rules: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': 'Internal server error'
            }, status=500)
    
    return JsonResponse({
        'status': 'error',
        'message': 'Method not allowed'
    }, status=405)


@login_required()
@require_http_methods(["POST", "PUT"])
@staff_required
def update_topology_rules(request, layer_id):
    """
    Actualiza las reglas de topología para una capa específica
    """
    try:
        layer = Layer.objects.get(id=layer_id)
        if not utils.can_manage_layer(request, layer):
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        # Validar que es una request JSON (no formulario)
        if not request.body:
            return JsonResponse({'error': 'Request body is required'}, status=400)
        
        # Parsear y validar JSON básico
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        
        # Validar campos requeridos y tipos (solo para API JSON)
        required_fields = ['no_overlap', 'no_gaps', 'must_be_covered_by', 'must_not_overlap_with', 'must_be_contiguous']
        for field in required_fields:
            if field not in data:
                return JsonResponse({'error': f'Missing required field: {field}'}, status=400)
            if not isinstance(data[field], bool):
                return JsonResponse({'error': f'Field {field} must be boolean'}, status=400)
        
        # Validar campos opcionales
        if 'covered_by_layer' in data and not isinstance(data['covered_by_layer'], str):
            return JsonResponse({'error': 'covered_by_layer must be string'}, status=400)
        
        if 'overlap_layers' in data and not isinstance(data['overlap_layers'], list):
            return JsonResponse({'error': 'overlap_layers must be array'}, status=400)
        
        if 'contiguous_tolerance' in data:
            try:
                float(data['contiguous_tolerance'])
            except (ValueError, TypeError):
                return JsonResponse({'error': 'contiguous_tolerance must be numeric'}, status=400)
        
        # Guardar configuración de topología y aplicar triggers
        topology_config = _save_layer_topology_rules(request, layer)
        
        # Devolver la configuración actualizada
        response_data = {
            'status': 'success',
            'message': 'Topology rules updated successfully',
            'layer_id': layer.id,
            'configuration': {
                'no_overlap': topology_config.no_overlap,
                'no_gaps': topology_config.no_gaps,
                'must_be_covered_by': topology_config.must_be_covered_by,
                'covered_by_layer': topology_config.covered_by_layer,
                'must_not_overlap_with': topology_config.must_not_overlap_with,
                'overlap_layers': topology_config.overlap_layers,
                'must_be_contiguous': topology_config.must_be_contiguous,
                'contiguous_tolerance': topology_config.contiguous_tolerance,
                'active_rules_count': topology_config.get_active_rules_count()
            }
        }
        
        return JsonResponse(response_data)
        
    except Layer.DoesNotExist:
        return JsonResponse({'error': 'Layer not found'}, status=404)
    except ValueError as e:
        return JsonResponse({'error': f'Validation error: {str(e)}'}, status=400)
    except Exception as e:
        logger.error(f"Error updating topology rules for layer {layer_id}: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


def _get_topology_trigger_names(layer, rule_type):
    """
    Obtiene los nombres de función y trigger para eliminación sin necesidad de validar parámetros completos
    """
    try:
        # Obtener información básica de la capa
        i, source_name, schema = layer.get_db_connection()
        table_name = layer.name.replace(':', '_')
        
        # Nombres únicos para funciones y triggers
        function_name_simple = f"{rule_type}_{table_name.lower()}"
        function_name = f"{schema}.{function_name_simple}"
        trigger_name = f"trigger_{rule_type}_{table_name.lower()}"
        full_table_name = f"{schema}.{table_name}"
        
        return {
            'function_name': function_name,
            'function_name_simple': function_name_simple,
            'trigger_name': trigger_name,
            'table_name': full_table_name,
            'schema': schema
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo nombres de trigger {rule_type}: {str(e)}")
        return None

def _remove_topology_trigger(layer, rule_type, **kwargs):
    """
    Elimina un trigger topológico de una capa
    """
    try:
        # Para eliminación, solo necesitamos los nombres, no toda la generación de SQL
        trigger_info = _get_topology_trigger_names(layer, rule_type)
        if not trigger_info:
            return False
        
        # Obtener conexión a la base de datos
        i, source_name, schema = layer.get_db_connection()
        
        with i as conn:
            # Establecer search_path para asegurar el esquema correcto
            conn.cursor.execute(f"SET search_path TO {trigger_info['schema']}, public;")
            return _remove_topology_trigger_internal(conn, trigger_info)
            
    except Exception as e:
        logger.error(f"Error eliminando trigger {rule_type} para capa {layer.id}: {str(e)}")
        return False
    
@login_required()
@staff_required
def db_fill_link_field(request):
    if request.method == 'POST':
        try:
            layer_id = request.POST.get('layer_id')
            new_field_name = request.POST.get('new_field_name')
            related_field_name = request.POST.get('related_field_name')
            
            if not all([layer_id, new_field_name, related_field_name]):
                logger.error(f"Missing required parameters: layer_id={layer_id}, new_field_name={new_field_name}, related_field_name={related_field_name}")
                return utils.get_exception(400, 'Missing required parameters: layer_id, new_field_name, related_field_name')
            
            layer = Layer.objects.get(id=layer_id)
            
            if not utils.can_manage_layer(request, layer):
                return HttpResponseForbidden('{"response": "Not authorized"}', content_type='application/json')
            
            if not (layer.datastore.type == 'v_PostGIS'):
                return utils.get_exception(400, 'Only PostGIS layers are supported')
            
            params = json.loads(layer.datastore.connection_params)
            schema = params.get('schema', 'public')
            
            iconn = Introspect(database=params['database'], host=params['host'], port=params['port'], user=params['user'], password=params['passwd'])
            
            # Pequeño delay para asegurar que el campo recién creado esté disponible
            time.sleep(1)
            
            updated_records = 0
            with iconn as con:
                try:
                    fields_info = con.get_fields_info(layer.source_name, schema)
                    
                    related_field_exists = any(field['name'] == related_field_name for field in fields_info)
                    new_field_exists = any(field['name'] == new_field_name for field in fields_info)
                                  
                    if not related_field_exists:
                        return utils.get_exception(400, f'Related field "{related_field_name}" does not exist')
                    
                    if not new_field_exists:
                        return utils.get_exception(400, f'New field "{new_field_name}" does not exist')
                        
                except Exception as e:
                    logger.error(f'Error getting fields info: {str(e)}')
                    return utils.get_exception(500, f'Error getting table fields info: {str(e)}')
                
                try:
                    query = sql.SQL("""
                        SELECT ogc_fid, {related_field}
                        FROM {schema}.{table}
                        WHERE {related_field} IS NOT NULL AND {related_field} != ''
                    """).format(
                        related_field=sql.Identifier(related_field_name),
                        schema=sql.Identifier(schema),
                        table=sql.Identifier(layer.source_name)
                    )
                    
                    results = con.custom_query(query)
                    
                    if not results:
                        return HttpResponse(json.dumps({
                            'status': 'success',
                            'message': 'No records found with non-null related field values',
                            'updated_records': 0
                        }), content_type='application/json')
                        
                except Exception as e:
                    logger.error(f'Error executing query: {str(e)}')
                    return utils.get_exception(500, f'Error executing query: {str(e)}')
                
                try:
                    for row in results:
                        ogc_fid = row[0]
                        related_value = row[1]
                        
                        link_url = f'/api/v1/layers/{layer_id}/{ogc_fid}/linkurl/{new_field_name}/'
                        
                        update_query = sql.SQL("""
                            UPDATE {schema}.{table}
                            SET {new_field} = %s
                            WHERE ogc_fid = %s
                        """).format(
                            schema=sql.Identifier(schema),
                            table=sql.Identifier(layer.source_name),
                            new_field=sql.Identifier(new_field_name)
                        )
                        
                        try:
                            con.custom_no_return_query(update_query, (link_url, ogc_fid))
                            updated_records += 1
                        except Exception as e:
                            logger.warning(f'Error updating record {ogc_fid} for field {new_field_name}: {str(e)}')
                            continue
                            
                except Exception as e:
                    logger.error(f'Error in update loop: {str(e)}')
                    return utils.get_exception(500, f'Error in update loop: {str(e)}')
                
                # Recargar la capa para reflejar los cambios
                try:
                    gs = geographic_servers.get_instance().get_server_by_id(layer.datastore.workspace.server.id)
                    gs.reload_featuretype(layer, nativeBoundingBox=False, latLonBoundingBox=False)
                    gs.reload_nodes()
                except Exception as e:
                    logger.warning(f'Warning: Could not reload layer in GeoServer: {str(e)}')
            
            try:
                iconn.close()
            except Exception as e:
                logger.warning(f'Warning: Could not close database connection: {str(e)}')
            
            return HttpResponse(json.dumps({
                'status': 'success',
                'message': f'Successfully updated {updated_records} records',
                'updated_records': updated_records
            }), content_type='application/json')
            
        except Layer.DoesNotExist:
            logger.error(f'Layer with id {layer_id} not found')
            return utils.get_exception(404, f'Layer with id {layer_id} not found')
        except Exception as e:
            logger.exception(f'Error filling link field: {str(e)}')
            return utils.get_exception(500, f'Error filling link field: {str(e)}')
    
    logger.error(f'Invalid request method: {request.method}. Only POST is allowed.')
    return utils.get_exception(400, 'Only POST method is allowed')
