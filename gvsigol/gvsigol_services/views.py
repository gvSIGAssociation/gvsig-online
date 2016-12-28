'''
    gvSIG Online.
    Copyright (C) 2007-2016 gvSIG Association.

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
from gvsigol_services.rest_geoserver import FailedRequestError

'''
@author: Cesar Martinez <cmartinez@scolab.es>
'''
from models import Workspace, Datastore, LayerGroup, Layer, LayerReadGroup, LayerWriteGroup, Enumeration, EnumerationItem,\
    LayerLock
from forms_services import WorkspaceForm, DatastoreForm, LayerForm, LayerUpdateForm, DatastoreUpdateForm
from django.http import HttpResponseRedirect, HttpResponseBadRequest, HttpResponseNotFound, HttpResponse
from django.views.decorators.http import require_http_methods, require_safe,require_POST, require_GET
from django.shortcuts import render_to_response, redirect, RequestContext
from backend_mapservice import gn_backend, backend as mapservice_backend
from gvsigol_auth.utils import superuser_required, staff_required
from gvsigol_core.models import ProjectLayerGroup, PublicViewer
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import PermissionDenied
from gvsigol.settings import FILEMANAGER_DIRECTORY
from django.utils.translation import ugettext as _
from gvsigol_services.models import LayerResource
from gvsigol.settings import GVSIGOL_SERVICES
from django.core.urlresolvers import reverse
from gvsigol_core import utils as core_utils
from gvsigol_auth.models import UserGroup
from django.shortcuts import render
from django.utils import timezone
from gvsigol import settings
import locks_utils
import requests
import logging
import urllib
import utils
import json
import re
import os
logger = logging.getLogger(__name__)


_valid_name_regex=re.compile("^[a-zA-Z_][a-zA-Z0-9_]*$")

@login_required(login_url='/gvsigonline/auth/login_user/')
@require_safe
@superuser_required
def workspace_list(request):
    response = {
        'workspaces': Workspace.objects.values()
    }
    return render_to_response('workspace_list.html', response, context_instance=RequestContext(request))

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
                # first create the ws on the backend
                if mapservice_backend.createWorkspace(form.cleaned_data['name'],
                    form.cleaned_data['uri'],
                    form.cleaned_data['description'],
                    form.cleaned_data['wms_endpoint'],
                    form.cleaned_data['wfs_endpoint'],
                    form.cleaned_data['wcs_endpoint'],
                    form.cleaned_data['cache_endpoint']):
                        
                    # save it on DB if successfully created
                    newWs = Workspace(**form.cleaned_data)
                    newWs.created_by = request.user.username
                    newWs.save()
                    mapservice_backend.reload_nodes()
                    return HttpResponseRedirect(reverse('workspace_list'))
                else:
                    # FIXME: the backend should raise an exception to identify the cause (e.g. workspace exists, backend is offline)
                    form.add_error(None, _("Error: workspace could not be created"))
                
    else:
        form = WorkspaceForm()
            
    return render(request, 'workspace_add.html', {'form': form, 'service_base_url': mapservice_backend.getBaseUrl()})

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
        workspaces = mapservice_backend.get_workspaces()
        workspace_names = [n for n in workspaces['name']]
        querySet = Workspace.objects.all().exclude(name__in=workspace_names)
        response = {
            'workspaces': querySet.values()
        }
        return render_to_response('workspace_import.html', response, context_instance=RequestContext(request))
    
    
@login_required(login_url='/gvsigonline/auth/login_user/')
@require_POST
@superuser_required
def workspace_delete(request, wsid):
    try:
        ws = Workspace.objects.get(id=wsid)
        if mapservice_backend.deleteWorkspace(ws):
            datastores = Datastore.objects.filter(workspace_id=ws.id)
            for ds in datastores:
                layers = Layer.objects.filter(datastore_id=ds.id)
                for l in layers:
                    mapservice_backend.deleteLayerStyles(l)
            ws.delete()
            mapservice_backend.reload_nodes()
            return HttpResponseRedirect(reverse('workspace_list'))
        else:
            return HttpResponseBadRequest()
    except:
        return HttpResponseNotFound('<h1>Workspace not found{0}</h1>'.format(ws.name)) 
    
    
@login_required(login_url='/gvsigonline/auth/login_user/')
@require_safe
@staff_required
def datastore_list(request):
    
    datastore_list = None
    if request.user.is_superuser:
        datastore_list = Datastore.objects.all()
    else:
        datastore_list = Datastore.objects.filter(created_by__exact=request.user.username)
        
    response = {
        'datastores': datastore_list
    }
    return render_to_response('datastore_list.html', response, context_instance=RequestContext(request))

@login_required(login_url='/gvsigonline/auth/login_user/')
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def datastore_add(request):
    if request.method == 'POST':
        post_dict = request.POST.copy()
        type = request.POST.get('type')
        if type == 'c_GeoTIFF':
            file = post_dict.get('file')
            post_dict['connection_params'] = post_dict.get('connection_params').replace('url_replace', file)
        form = DatastoreForm(post_dict)
        if form.is_valid():
            name = form.cleaned_data['name']
            if _valid_name_regex.search(name) == None:
                form.add_error(None, _("Invalid datastore name: '{value}'. Identifiers must begin with a letter or an underscore (_). Subsequent characters can be letters, underscores or numbers").format(value=name))
            else:
                # first create the datastore on the backend
                if mapservice_backend.createDatastore(form.cleaned_data['workspace'],
                                                      form.cleaned_data['type'],
                                                      form.cleaned_data['name'],
                                                      form.cleaned_data['description'],
                                                      form.cleaned_data['connection_params']):
                    # save it on DB if successfully created
                    newRecord = Datastore(
                        workspace=form.cleaned_data['workspace'],
                        type=form.cleaned_data['type'],
                        name=form.cleaned_data['name'],
                        description=form.cleaned_data['description'],
                        connection_params=form.cleaned_data['connection_params'],
                        created_by=request.user.username
                    )
                    newRecord.save()
                    mapservice_backend.reload_nodes()
                    return HttpResponseRedirect(reverse('datastore_list'))
                else:
                    # FIXME: the backend should raise an exception to identify the cause (e.g. datastore exists, backend is offline)
                    form.add_error(None, _('Error: Data store could not be created'))
            
    else:
        form = DatastoreForm()
        if not request.user.is_superuser:
            form.fields['workspace'].queryset = Workspace.objects.filter(created_by__exact=request.user.username)
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
                if mapservice_backend.updateDatastore(datastore.workspace.name, datastore.name,
                                                      description, dstype, connection_params):
                    # REST API does not allow to can't change the workspace or name of a datastore 
                    #datastore.workspace = workspace
                    #datastore.name = name
                    datastore.description = description
                    datastore.connection_params = connection_params
                    datastore.save()
                    mapservice_backend.reload_nodes()
                    return HttpResponseRedirect(reverse('datastore_list'))
                else:
                    form.add_error(None, _("Error updating datastore"))
    else:
        form = DatastoreUpdateForm(instance=datastore)
    return render(request, 'datastore_update.html', {'form': form, 'datastore_id': datastore_id, 'workspace_name': datastore.workspace.name})

@login_required(login_url='/gvsigonline/auth/login_user/')
@require_POST
@staff_required
def datastore_delete(request, dsid):
    try:
        ds = Datastore.objects.get(id=dsid)
        if mapservice_backend.deleteDatastore(ds.workspace, ds):
            layers = Layer.objects.filter(datastore_id=ds.id)
            for l in layers:
                mapservice_backend.deleteLayerStyles(l)
            Datastore.objects.all().filter(name=ds.name).delete()
            mapservice_backend.reload_nodes()
            return HttpResponseRedirect(reverse('datastore_list'))
        else:
            return HttpResponseBadRequest()
    except:
        return HttpResponseNotFound('<h1>Datastore not found{0}</h1>'.format(ds.name)) 

@login_required(login_url='/gvsigonline/auth/login_user/')
@require_safe
@staff_required
def layer_list(request):
    
    layer_list = None
    if request.user.is_superuser:
        layer_list = Layer.objects.all()
    else:
        layer_list = Layer.objects.filter(created_by__exact=request.user.username)
        
    response = {
        'layers': layer_list
    }
    return render_to_response('layer_list.html', response, context_instance=RequestContext(request))
    
@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def layer_delete(request, layer_id):
    try:
        layer = Layer.objects.get(pk=layer_id)
        mapservice_backend.deleteGeoserverLayerGroup(layer.layer_group)
        if mapservice_backend.deleteResource(layer.datastore.workspace, layer.datastore, layer):
            mapservice_backend.deleteLayerStyles(layer)
            if settings.CATALOG_MODULE:
                gn_backend.metadata_delete(layer)
            if os.path.isfile(layer.thumbnail.path):
                os.remove(layer.thumbnail.path)
            Layer.objects.all().filter(pk=layer_id).delete()
            mapservice_backend.setDataRules()
            core_utils.toc_remove_layer(layer)
            mapservice_backend.createOrUpdateGeoserverLayerGroup(layer.layer_group)
            mapservice_backend.reload_nodes()
            return HttpResponseRedirect(reverse('datastore_list'))
        else:
            return HttpResponseBadRequest()
        
    except Exception as e:
        return HttpResponseNotFound('<h1>Layer not found: {0}</h1>'.format(layer_id)) 

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
            resources = mapservice_backend.getResources(ds.workspace.name, ds.name, ds.type, available=True)
            return HttpResponse(json.dumps(resources))
    return HttpResponseBadRequest()
    

@login_required(login_url='/gvsigonline/auth/login_user/')
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def layer_add(request):
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
        
        if form.is_valid():
            try:
                # first create the resource on the backend
                mapservice_backend.createResource(form.cleaned_data['datastore'].workspace,
                                      form.cleaned_data['datastore'],
                                      form.cleaned_data['name'],
                                      form.cleaned_data['title'])
                # save it on DB if successfully created
                newRecord = Layer(**form.cleaned_data)
                newRecord.created_by = request.user.username
                newRecord.type = form.cleaned_data['datastore'].type
                newRecord.visible = is_visible
                newRecord.queryable = is_queryable
                newRecord.cached = cached
                newRecord.single_image = single_image
                newRecord.abstract = abstract
                newRecord.save()
                
                if form.cleaned_data['datastore'].type != 'e_WMS':
                    datastore = Datastore.objects.get(id=newRecord.datastore.id)
                    workspace = Workspace.objects.get(id=datastore.workspace_id)
                    
                    style_name = workspace.name + '_' + newRecord.name + '_default'
                    mapservice_backend.createDefaultStyle(newRecord, style_name)
                    mapservice_backend.setLayerStyle(newRecord, style_name)
                    
                    mapservice_backend.updateThumbnail(newRecord)
                 
                    #mapservice_backend.addGridSubset(workspace, newRecord)
                    newRecord.metadata_uuid = ''
                    try:
                        if settings.CATALOG_MODULE:
                            layer_info = mapservice_backend.getResourceInfo(workspace.name, datastore.name, newRecord.name, "json")
                            muuid = gn_backend.metadata_insert(newRecord, abstract, workspace, layer_info)
                            newRecord.metadata_uuid = muuid
                    except Exception as exc:
                        logging.exception(exc)
                        newRecord.save()
                        return HttpResponseRedirect(reverse('layer_update', kwargs={'layer_id': newRecord.id}))
                    newRecord.save()
                    
                core_utils.toc_add_layer(newRecord)
                mapservice_backend.createOrUpdateGeoserverLayerGroup(newRecord.layer_group)
                mapservice_backend.reload_nodes()
                return HttpResponseRedirect(reverse('layer_permissions_update', kwargs={'layer_id': newRecord.id}))
            
            except Exception as e:
                try:
                    msg = e.get_message()
                except:
                    msg = _("Error: layer could not be published")
                # FIXME: the backend should raise more specific exceptions to identify the cause (e.g. layer exists, backend is offline)
                form.add_error(None, msg)
    else:
        form = LayerForm()
        if not request.user.is_superuser:
            form.fields['datastore'].queryset = Datastore.objects.filter(created_by__exact=request.user.username)
            form.fields['layer_group'].queryset = LayerGroup.objects.filter(created_by__exact=request.user.username)
    return render(request, 'layer_add.html', {'form': form})


@login_required(login_url='/gvsigonline/auth/login_user/')
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def layer_update(request, layer_id):
    if request.method == 'POST':
        layer = Layer.objects.get(id=int(layer_id))
        workspace = request.POST.get('workspace')
        datastore = request.POST.get('datastore')
        name = request.POST.get('name')
        title = request.POST.get('title')
        #style = request.POST.get('style')
        layer_group_id = request.POST.get('layer_group')
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
        if not layer.metadata_uuid:
            layer.metadata_uuid = request.POST.get('metadata_uuid')
                
        old_layer_group = LayerGroup.objects.get(id=layer.layer_group_id)
        
        if mapservice_backend.updateResource(workspace, datastore, name, title):
            layer.title = title
            layer.cached = cached
            layer.visible = is_visible
            layer.queryable = is_queryable 
            layer.single_image = single_image 
            layer.layer_group_id = layer_group_id
            layer.save()
            
            new_layer_group = LayerGroup.objects.get(id=layer.layer_group_id)
            
            if old_layer_group.id != new_layer_group.id:
                core_utils.toc_move_layer(layer, old_layer_group)
                mapservice_backend.createOrUpdateGeoserverLayerGroup(old_layer_group)
                mapservice_backend.createOrUpdateGeoserverLayerGroup(new_layer_group)
                                
            mapservice_backend.reload_nodes()   
            return HttpResponseRedirect(reverse('layer_permissions_update', kwargs={'layer_id': layer_id}))
            
    else:
        layer = Layer.objects.get(id=int(layer_id))
        datastore = Datastore.objects.get(id=layer.datastore.id)
        workspace = Workspace.objects.get(id=datastore.workspace_id)
        form = LayerUpdateForm(instance=layer)
        return render(request, 'layer_update.html', {'layer': layer, 'workspace': workspace, 'form': form, 'layer_id': layer_id})
    
    
@login_required(login_url='/gvsigonline/auth/login_user/')
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def layer_config(request, layer_id):
    if request.method == 'POST':
        layer = Layer.objects.get(id=int(layer_id))
        
        conf = {}
        fields = []
        counter = int(request.POST.get('counter'))
        for i in range(1, counter+1):
            field = {}
            field['name'] = request.POST.get('field-name-' + str(i))
            field['title'] = request.POST.get('field-title-' + str(i))
            field['visible'] = False
            if 'field-visible-' + str(i) in request.POST:
                field['visible'] = True
            fields.append(field)
        conf['fields'] = fields
        
        json_conf = json.dumps(conf)
        layer.conf = json_conf
        layer.save()
        
        return redirect('layer_list')
            
    else:
        layer = Layer.objects.get(id=int(layer_id))
        fields = []
        
        try:
            conf = json.loads(layer.conf)
            for f in conf['fields']:
                field = {}
                field['name'] = f['name']
                field['title'] = f['title']
                field['visible'] = f['visible']
                fields.append(field)
                
        except: 
            datastore = Datastore.objects.get(id=layer.datastore_id)
            workspace = Workspace.objects.get(id=datastore.workspace_id)
            resource = mapservice_backend.getResourceInfo(workspace.name, datastore.name, layer.name, "json")
            resource_fields = utils.get_alphanumeric_fields(utils.get_fields(resource))
            for f in resource_fields:
                field = {}
                field['name'] = f['name']
                field['title'] = f['name']
                field['visible'] = True
                fields.append(field)
    
        return render(request, 'layer_config.html', {'layer': layer, 'layer_id': layer.id, 'fields': fields})
    

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
        layer_query_set = Layer.objects.filter(name=layer_name, datastore__workspace=workspace)
        layer = layer_query_set[0]
        mapservice_backend.updateBoundingBoxFromData(layer)   
        mapservice_backend.clearCache(workspace.name, layer)
        mapservice_backend.updateThumbnail(layer)
        mapservice_backend.reload_nodes()
        return HttpResponse('{"response": "ok"}', content_type='application/json')
    
    except Exception as e:
        return HttpResponseNotFound('<h1>Layer not found: {0}</h1>'.format(layer.id))

@login_required(login_url='/gvsigonline/auth/login_user/')
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def cache_clear(request, layer_id):
    if request.method == 'GET':
        layer = Layer.objects.get(id=int(layer_id)) 
        datastore = Datastore.objects.get(id=layer.datastore.id)
        workspace = Workspace.objects.get(id=datastore.workspace_id)
        mapservice_backend.clearCache(workspace.name, layer)
        mapservice_backend.reload_nodes()
        return redirect('layer_list')
    
@login_required(login_url='/gvsigonline/auth/login_user/')
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def layergroup_cache_clear(request, layergroup_id):
    if request.method == 'GET':
        layergroup = LayerGroup.objects.get(id=int(layergroup_id)) 
        mapservice_backend.clearLayerGroupCache(layergroup.name)
        mapservice_backend.reload_nodes()
        return redirect('layergroup_list')
    

@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def layer_permissions_update(request, layer_id):
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
        
        # clean existing groups and assign them again
        LayerReadGroup.objects.filter(layer=layer).delete()
        for group in assigned_read_roups:
            try:
                group = UserGroup.objects.get(id=group)
                lrg = LayerReadGroup()
                lrg.layer = layer
                lrg.group = group
                lrg.save()
            except:
                pass
        
        LayerWriteGroup.objects.filter(layer=layer).delete()
        agroup = UserGroup.objects.get(name__exact='admin')
        lwag = LayerWriteGroup()
        lwag.layer = layer
        lwag.group = agroup
        lwag.save()
        for group in assigned_write_groups:
            try:
                group = UserGroup.objects.get(id=group)
                lwg = LayerWriteGroup()
                lwg.layer = layer
                lwg.group = group
                lwg.save()
            except:
                pass
                
        mapservice_backend.setDataRules()
        mapservice_backend.reload_nodes()
        return redirect('layer_list')
    else:
        try:
            layer = Layer.objects.get(pk=layer_id)
            groups = utils.get_all_user_groups_checked_by_layer(layer)   
            return render_to_response('layer_permissions_add.html', {'layer_id': layer.id, 'name': layer.name, 'groups': groups}, context_instance=RequestContext(request))
        except Exception as e:
            return HttpResponseNotFound('<h1>Layer not found: {0}</h1>'.format(layer_id))
   
def get_resources_from_workspace(request):
    # FIXME
    if request.method == 'POST':
        wid = request.POST.get('workspace_id')
        layer_list = Layer.objects.all()
        
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
    layers = Layer.objects.all()
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
            layergroups.append(layergroup)
                      
    response = {
        'layergroups': layergroups
    }     
    return render_to_response('layergroup_list.html', response, context_instance=RequestContext(request))


@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def layergroup_add(request):
    if request.method == 'POST':
        name = request.POST.get('layergroup_name') + '_' + request.user.username
        title = request.POST.get('layergroup_title')
        
        cached = False
        if 'cached' in request.POST:
            cached = True
        
        if name != '':
            if _valid_name_regex.search(name) == None:
                message = _("Invalid layer group name: '{value}'. Identifiers must begin with a letter or an underscore (_). Subsequent characters can be letters, underscores or numbers").format(value=name)
                return render_to_response('layergroup_add.html', {'message': message}, context_instance=RequestContext(request))
        
            exists = False
            layergroups = LayerGroup.objects.all()
            for lg in layergroups:
                if name == lg.name:
                    exists = True
                    
            if not exists:
                layergroup = LayerGroup(
                    name = name,
                    title = title,
                    cached = cached,
                    created_by = request.user.username
                )
                layergroup.save()
            
            else:
                message = _(u'Layer group name already exists')
                return render_to_response('layergroup_add.html', {'message': message}, context_instance=RequestContext(request))
            
        else:
            message = _(u'You must enter a name for layer group')
            return render_to_response('layergroup_add.html', {'message': message}, context_instance=RequestContext(request))
            
        mapservice_backend.reload_nodes()
        return redirect('layergroup_list')
    
    else:
        return render_to_response('layergroup_add.html', {}, context_instance=RequestContext(request))
    
    
@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def layergroup_update(request, lgid):
    if request.method == 'POST':
        name = request.POST.get('layergroup_name')
        title = request.POST.get('layergroup_title')
        
        cached = False
        if 'cached' in request.POST:
            cached = True
        
        layergroup = LayerGroup.objects.get(id=int(lgid))
        mapservice_backend.deleteGeoserverLayerGroup(layergroup)
        
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
            layergroup.save()   
            core_utils.toc_update_layer_group(layergroup, old_name, name)
            mapservice_backend.createOrUpdateGeoserverLayerGroup(layergroup)
            mapservice_backend.reload_nodes()
            return redirect('layergroup_list')
             
        else:      
            if not exists:   
                if _valid_name_regex.search(name) == None:
                    message = _("Invalid layer group name: '{value}'. Identifiers must begin with a letter or an underscore (_). Subsequent characters can be letters, underscores or numbers").format(value=name)
                    return render_to_response('layergroup_add.html', {'message': message}, context_instance=RequestContext(request))
                
                layergroup.name = name
                layergroup.title = title
                layergroup.cached = cached
                layergroup.save()
                core_utils.toc_update_layer_group(layergroup, old_name, name)
                mapservice_backend.createOrUpdateGeoserverLayerGroup(layergroup)
                mapservice_backend.reload_nodes()
                return redirect('layergroup_list')
                
            else:
                message = _(u'Layer group name already exists')
                return render_to_response('layergroup_update.html', {'message': message, 'layergroup': layergroup}, context_instance=RequestContext(request))

    else:
        layergroup = LayerGroup.objects.get(id=int(lgid))
        
        return render_to_response('layergroup_update.html', {'lgid': lgid, 'layergroup': layergroup}, context_instance=RequestContext(request))
    
    
@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def layergroup_delete(request, lgid):        
    if request.method == 'POST':
        layergroup = LayerGroup.objects.get(id=int(lgid))
        layers = Layer.objects.filter(layer_group_id=layergroup.id)    
        projects_by_layergroup = ProjectLayerGroup.objects.filter(layer_group_id=layergroup.id)
        for p in projects_by_layergroup:
            p.project.toc_order = core_utils.toc_remove_layergroups(p.project.toc_order, [layergroup.id])
            p.project.save()
            
        if len(PublicViewer.objects.all()) == 1:
            public_viewer = PublicViewer.objects.all()[0]
            public_viewer.toc_order = core_utils.toc_remove_layergroups(public_viewer.toc_order, [layergroup.id])
            public_viewer.save()
            
        for layer in layers:  
            if mapservice_backend.deleteResource(layer.datastore.workspace, layer.datastore, layer):
                layer.delete()       
        mapservice_backend.deleteGeoserverLayerGroup(layergroup)
        layergroup.delete()
        mapservice_backend.setDataRules()
        mapservice_backend.reload_nodes()
        response = {
            'deleted': True
        }     
        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')

@require_http_methods(["GET", "POST", "HEAD"])
@login_required(login_url='/gvsigonline/auth/login_user/')
@superuser_required
def layer_create(request):
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
            
        (form_class, template) = mapservice_backend.getLayerCreateForm(layer_type)
        if form_class is not None:
            form = form_class(request.POST)
            if form.is_valid():
                try:
                    mapservice_backend.createTable(form.cleaned_data)

                    # first create the resource on the backend
                    mapservice_backend.createResource(form.cleaned_data['datastore'].workspace,
                                          form.cleaned_data['datastore'],
                                          form.cleaned_data['name'],
                                          form.cleaned_data['title'])
                    # save it on DB if successfully created
                    newRecord = Layer(
                        datastore = form.cleaned_data['datastore'],
                        layer_group = form.cleaned_data['layer_group'],
                        name = form.cleaned_data['name'],
                        title = form.cleaned_data['title'],
                        abstract = abstract,
                        created_by = request.user.username,
                        type = form.cleaned_data['datastore'].type,
                        visible = is_visible,
                        queryable = is_queryable,
                        cached = cached,
                        single_image = single_image   
                    )
                    newRecord.save()
                    
                    if form.cleaned_data['datastore'].type != 'e_WMS':
                        datastore = Datastore.objects.get(id=newRecord.datastore.id)
                        workspace = Workspace.objects.get(id=datastore.workspace_id)
                        
                        style_name = workspace.name + '_' + newRecord.name + '_default'
                        mapservice_backend.createDefaultStyle(newRecord, style_name)
                        mapservice_backend.setLayerStyle(newRecord, style_name)
                        mapservice_backend.updateThumbnail(newRecord)
                     
                        mapservice_backend.addGridSubset(workspace, newRecord)
                        newRecord.metadata_uuid = ''
                        try:
                            if settings.CATALOG_MODULE:
                                layer_info = mapservice_backend.getResourceInfo(workspace.name, datastore.name, newRecord.name, "json")
                                muuid = gn_backend.metadata_insert(newRecord, abstract, workspace, layer_info)
                                newRecord.metadata_uuid = muuid
                        except Exception as exc:
                            logging.exception(exc)
                            newRecord.save()
                            return HttpResponseRedirect(reverse('layer_update', kwargs={'layer_id': newRecord.id}))
                        newRecord.save()
                        
                    core_utils.toc_add_layer(newRecord)
                    mapservice_backend.createOrUpdateGeoserverLayerGroup(newRecord.layer_group)
                    mapservice_backend.reload_nodes()
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
                        'layer_type': layer_type
                    }
                    return render(request, template, data)
                    
            else:
                data = {
                    'form': form,
                    'layer_type': layer_type
                }
                return render(request, template, data)
        
    else:
        (form_class, template) = mapservice_backend.getLayerCreateForm(layer_type)
        if form_class is not None:
            data = {
                'form': form_class(),
                'layer_type': layer_type,
                'enumerations': Enumeration.objects.all()
            }
            return render(request, template, data)
        
    return HttpResponseBadRequest()


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
    return render_to_response('enumeration_list.html', response, context_instance=RequestContext(request))


@login_required(login_url='/gvsigonline/auth/login_user/')
@staff_required
def enumeration_add(request):
    if request.method == 'POST':
        name = request.POST.get('enumeration_name')
        title = request.POST.get('enumeration_title')
        
        aux_title = ''.join(title.encode('ASCII', 'ignore').split())[:4]
        aux_title = aux_title.lower()
        
        name = name + '_' + re.sub("[!@#$%^&*()[]{};:,./<>?\|`~-=_+ ]", "", aux_title)
                
        if title != '':
            enum = Enumeration(
                name = name,
                title = title,
                created_by = request.user.username
            )
            enum.save()
            
            for key in request.POST:
                if 'item-content' in key:
                    item = EnumerationItem(
                        enumeration = enum,
                        name = request.POST.get(key),
                        selected = False,
                        order = 0
                    )
                    item.save()
            
        else:
            index = len(Enumeration.objects.all())
            enum_name = '_enm' + str(index)
            message = _(u'You must enter a title for enumeration')
            return render_to_response('enumeration_add.html', {'message': message, 'enum_name': enum_name}, context_instance=RequestContext(request))

        return redirect('enumeration_list')
    
    else:
        index = len(Enumeration.objects.all())
        enum_name = '_enm' + str(index)
        return render_to_response('enumeration_add.html', {'enum_name': enum_name}, context_instance=RequestContext(request))
    
    
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
                item = EnumerationItem(
                    enumeration = enum,
                    name = request.POST.get(key),
                    selected = False,
                    order = 0
                )
                item.save()
        
        return redirect('enumeration_list')
            
    else:
        enum = Enumeration.objects.get(id=int(eid))
        items = EnumerationItem.objects.filter(enumeration_id=enum.id).order_by('name')
        
        return render_to_response('enumeration_update.html', {'eid': eid, 'enumeration': enum, 'items': items, 'count': len(items) + 1}, context_instance=RequestContext(request))
   

@login_required(login_url='/gvsigonline/auth/login_user/')
@csrf_exempt
def get_enumeration(request):
    if request.method == 'POST':
        enum_name = request.POST.get('enum_name')
        enum = Enumeration.objects.get(name__exact=enum_name)
        enum_items = EnumerationItem.objects.filter(enumeration_id=enum.id)
        
        items = []
        for i in enum_items:
            item = {}
            item['name'] = i.name
            item['selected'] = i.selected
            items.append(item)
            
        response = {
            'title': enum.title,
            'items': items
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
            tables = mapservice_backend.getGeomColumns(ds)
            data = { 'tables': tables}
            return render(request, 'geom_table_list.html', data)
        except:
            pass
    return HttpResponseBadRequest()

@csrf_exempt
def get_feature_info(request):
    if request.method == 'POST':      
        url = request.POST.get('url')
        query_layer = request.POST.get('query_layer')
        ws = request.POST.get('workspace')

        req = requests.Session()
        if 'username' in request.session and 'password' in request.session:
            if request.session['username'] is not None and request.session['password'] is not None:
                req.auth = (request.session['username'], request.session['password'])
                #req.auth = ('admin', 'geoserver')
                
        features = None           
        try:
            w = Workspace.objects.get(name__exact=ws)
            logger.debug("Feature info - ws" + str(w.name))
            ds = Datastore.objects.get(workspace=w)
            logger.debug("Feature info - ws" + str(ds.name))
            layers = Layer.objects.filter(name__exact=query_layer)
            
            layer = None
            for l in layers:
                if l.datastore.id == ds.id:
                    layer = l

            response = req.get(url, verify=False)
            geojson = json.loads(response.text)
            if layer:
                logger.debug("Feature info - layer name:" + str(layer.name))
                logger.debug("Feature info - layer id:" + str(layer.id))
                
            if layer.conf is not None:
                layer_conf = json.loads(layer.conf)
                fields = layer_conf.get('fields')
                for i in range(0, len(geojson['features'])):
                    logger.debug("Feature info - parsing fid")
                    logger.debug(str(geojson))
                    fid = geojson['features'][i].get('id').split('.')[1]
                    logger.debug("Feature info - resources - feature id: " + str(fid))
                    layer_resources = LayerResource.objects.filter(layer_id=layer.id).filter(feature=fid)
                    resources = []
                    for lr in layer_resources:
                        logger.debug("Feature info - resources - lr.path: " + str(lr.path))
                        abs_server_path = os.path.join(settings.MEDIA_URL, lr.path)
                        logger.debug("Feature info - resources - abspath: " + abs_server_path)
                        type = 'image' 
                        resource = {
                            'type': type,
                            'url': abs_server_path
                        }
                        resources.append(resource)
                    geojson['features'][i]['resources'] = resources
                        
                    formated_properties = {}
                    for p in geojson['features'][i].get('properties'):
                        for f in fields:
                            if f.get('name') == p:
                                if f.get('visible'):
                                    formated_properties[f.get('title')] = geojson['features'][i].get('properties')[p]
                    geojson['features'][i]['properties'] = formated_properties
                    
                features = geojson['features']
                    
            else: 
                for i in range(0, len(geojson['features'])):
                    logger.debug("Feature info - parsing fid")
                    logger.debug(str(geojson))
                    fid = geojson['features'][i].get('id').split('.')[1]
                    logger.debug("Feature info - resources - feature id: " + str(fid))
                    layer_resources = LayerResource.objects.filter(layer_id=layer.id).filter(feature=fid)
                    resources = []
                    for lr in layer_resources:
                        logger.debug("Feature info - resources - lr.path: " + str(lr.path))
                        abs_server_path = os.path.join(settings.MEDIA_URL, lr.path)
                        logger.debug("Feature info - resources - abspath: " + abs_server_path)
                        type = 'image' 
                        resource = {
                            'type': type,
                            'url': abs_server_path
                        }
                        resources.append(resource)
                    geojson['features'][i]['resources'] = resources
                    
                features = geojson['features']
            
        except Exception as e:
            logger.exception("get_feature_info")
            response = req.get(url, verify=False)
            geojson = json.loads(response.text)
            features = geojson['features']
                
        response = {
            'features': features
        }

        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')

@csrf_exempt
def get_datatable_data(request):
    if request.method == 'POST':      
        layer_name = request.POST.get('layer_name')
        workspace = request.POST.get('workspace')     
        wfs_url = request.POST.get('wfs_url')
        if len(GVSIGOL_SERVICES['CLUSTER_NODES']) >= 1:
            wfs_url = GVSIGOL_SERVICES['CLUSTER_NODES'][0] + '/' + workspace + '/wfs'
        property_name = request.POST.get('property_name')
        properties_with_type = request.POST.get('properties_with_type')
        start_index = request.POST.get('start')
        max_features = request.POST.get('length')
        draw = request.POST.get('draw')
        search_value = request.POST.get('search[value]')
        
        values = None
        recordsTotal = 0
        recordsFiltered = 0
        
        encoded_property_name = property_name.encode('utf-8')
        
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
            recordsTotal = mapservice_backend.getFeatureCount(request, wfs_url, layer_name, None)
            recordsFiltered = recordsTotal
            
        else:
            properties = properties_with_type.split(',')
            encoded_value = search_value.encode('ascii', 'replace')
            
            filter = '<Filter>'
            filter += '<Or>'
            for p in properties:
                if p.split('|')[1] == 'xsd:string':
                    filter += '<PropertyIsLike matchCase="false" wildCard="*" singleChar="." escape="!">'
                    filter += '<PropertyName>' + p.split('|')[0] + '</PropertyName>'
                    filter += '<Literal>*' + encoded_value.replace('?', '.') + '*' + '</Literal>'
                    filter += '</PropertyIsLike>'
                elif p.split('|')[1] == 'xsd:double' or p.split('|')[1] == 'xsd:decimal' or p.split('|')[1] == 'xsd:integer' or p.split('|')[1] == 'xsd:int' or p.split('|')[1] == 'xsd:long':
                    if search_value.isdigit():
                        filter += '<PropertyIsEqualTo>'
                        filter += '<PropertyName>' + p.split('|')[0] + '</PropertyName>'
                        filter += '<Literal>' + search_value + '</Literal>'
                        filter += '</PropertyIsEqualTo>'
            filter += '</Or>'
            filter += '</Filter>'
            
            values = {
                'SERVICE': 'WFS',
                'VERSION': '1.1.0',
                'REQUEST': 'GetFeature',
                'TYPENAME': layer_name,
                'OUTPUTFORMAT': 'application/json',
                'MAXFEATURES': max_features,
                'STARTINDEX': start_index,
                'PROPERTYNAME': encoded_property_name,
                'filter': filter
            }
            recordsTotal = mapservice_backend.getFeatureCount(request, wfs_url, layer_name, None)
            recordsFiltered = mapservice_backend.getFeatureCount(request, wfs_url, layer_name, filter)

        params = urllib.urlencode(values)
        req = requests.Session()
        if 'username' in request.session and 'password' in request.session:
            if request.session['username'] is not None and request.session['password'] is not None:
                req.auth = (request.session['username'], request.session['password'])
                #req.auth = ('admin', 'geoserver')
                
        print wfs_url + "?" + params
        response = req.post(wfs_url, data=values, verify=False)
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
    return render_to_response('lock_list.html', response, context_instance=RequestContext(request))

@login_required(login_url='/gvsigonline/auth/login_user/')
@require_http_methods(["GET", "POST", "HEAD"])
@staff_required
def unlock_layer(request, lock_id):
    lock = LayerLock.objects.get(id=int(lock_id))
    lock.delete()
    return redirect('lock_list')

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
            (saved, path) = utils.save_resource(request.FILES['resource'])
            if saved:
                res = LayerResource()
                res.feature = int(fid)
                res.layer = layer
                res.path = path
                res.title = ''
                res.type = LayerResource.EXTERNAL_IMAGE
                res.created = timezone.now()
                res.save()
                response = {'success': True}
                
            else:
                response = {'success': False}
            
    return HttpResponse(json.dumps(response, indent=4), content_type='application/json')
    
@login_required(login_url='/gvsigonline/auth/login_user/')
@csrf_exempt
def delete_resource(request, rid):
    response = {
        'success': True
    }
    return HttpResponse(json.dumps(response, indent=4), content_type='application/json')