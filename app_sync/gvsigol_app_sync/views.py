'''
    gvSIG Online.
    Copyright (C) 2016 gvSIG Association.

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
from gvsigol_services.backend_mapservice import backend as mapservice_backend

'''
@author: Cesar Martinez <cmartinez@scolab.es>
'''

# generic python modules
import json
import time, os

# django libs
from django.http.response import StreamingHttpResponse, FileResponse
from django.http import HttpResponseRedirect, HttpResponseBadRequest, HttpResponseNotFound, HttpResponse
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods, require_safe,require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import PermissionDenied




# gvsig online modules
from gvsigol_services.models import Workspace, Datastore, LayerGroup, Layer, LayerReadGroup, LayerWriteGroup, LayerLock
import tempfile
from gvsigol_services import gdal_tools
from gvsigol_services.gdal_tools import MODE_OVERWRITE, MODE_APPEND
from gvsigol_core import geom


#@login_required(login_url='/gvsigonline/auth/login_user/')
@require_GET
@csrf_exempt
def get_layerinfo(request):
    """
    For the moment return only writable layers, until we manage read-only layers
    in Geopaparazzi
    
    universallyReadableLayers = Layer.objects.exclude(layerreadgroup__layer__isnull=False)
    if not isinstance(request.user, AnonymousUser) :
        user = request.user
        readWriteLayers = Layer.objects.filter(layerwritegroup__group__usergroupuser__user=user)
        readOnlyLayers = Layer.objects.filter(layerreadgroup__group__usergroupuser__user=user).exclude(layerwritegroup__group__usergroupuser__user=user)
        layerJson = layersToJson(universallyReadableLayers, readOnlyLayers, readWriteLayers)
    else:
        layerJson = layersToJson(universallyReadableLayers)
    """
    if not isinstance(request.user, AnonymousUser) :
        user = request.user
        readWriteLayers = Layer.objects.filter(layerwritegroup__group__usergroupuser__user=user)
        layerJson = layersToJson([], [], readWriteLayers)
    else:
        layerJson = layersToJson([], [], [])
    return HttpResponse(layerJson, content_type='application/json')

#@login_required(login_url='/gvsigonline/auth/login_user/')
@require_GET
@csrf_exempt
def get_layerinfo_by_project(request, project):
    """
    For the moment return only writable layers, until we manage read-only layers
    in Geopaparazzi
    
    universallyReadableLayers = Layer.objects.exclude(layerreadgroup__layer__isnull=False).filter(layer_group__projectlayergroup__project=project)
    if not isinstance(request.user, AnonymousUser) :
        user = request.user
        readWriteLayers = Layer.objects.filter(layerwritegroup__group__usergroupuser__user=user).filter(layer_group__projectlayergroup__project=project)
        readOnlyLayers = Layer.objects.filter(layerreadgroup__group__usergroupuser__user=user).filter(layer_group__projectlayergroup__project=project).exclude(layerwritegroup__group__usergroupuser__user=user)
        layerJson = layersToJson(universallyReadableLayers, readOnlyLayers, readWriteLayers)
    else:
        layerJson = layersToJson(universallyReadableLayers)
    """
    if not isinstance(request.user, AnonymousUser) :
        user = request.user
        readWriteLayers = Layer.objects.filter(layerwritegroup__group__usergroupuser__user=user).filter(layer_group__projectlayergroup__project=project)
        layerJson = layersToJson([], [], readWriteLayers)
    else:
        layerJson = layersToJson([], [], [])
    return HttpResponse(layerJson, content_type='application/json')

    
def fill_layer_attrs(layer, permissions):
    row = {}
    geom_info = mapservice_backend.get_geometry_info(layer)
    srid = geom_info['srs']
    if srid is None:
        srid = 'unknown'
    geom_type = geom_info['geomtype']
    row['name'] = layer.get_qualified_name()
    row['title'] = layer.title
    row['abstract'] = layer.abstract
    row['geomtype'] = geom.toGeopaparazzi(geom_type)
    row['srid'] = srid
    row['permissions'] = permissions
    # last-modified excluded for the moment
    #row['last-modified'] = long(time.time())   #FIXME
    return row

def layersToJson(universallyReadableLayers, readOnlyLayers=[], readWriteLayers=[]):
    result = []
    # the queries get some layers repeated if the user has several groups,
    # so we use a set to keep them unique
    layerIds = set()
    for layer in readWriteLayers:
        if not layer.id in layerIds:
            row = fill_layer_attrs(layer, 'read-write')
            result.append(row)
            layerIds.add(layer.id)
            
    for layer in readOnlyLayers:
        if not layer.id in layerIds:
            row = fill_layer_attrs(layer, 'read-only')
            result.append(row)
            layerIds.add(layer.id)
    
    for layer in universallyReadableLayers:
        if not layer.id in layerIds:
            row = fill_layer_attrs(layer, 'read-only')
            result.append(row)
            layerIds.add(layer.id)
            
    layerStr = json.dumps(result)
    return layerStr 

#@login_required(login_url='/gvsigonline/auth/login_user/')
@csrf_exempt
def sync_download(request):
    locked_layers = []
    tables = []
    try:
        request_params = json.loads(request.body)
        layers = request_params["layers"]
        # we will ignore bbox for the moment
        bbox = request_params.get("bbox", None)
        for layer in layers:
            #FIXME: maybe we need to specify if we want the layer for reading or writing!!!! Assume we always want to write for the moment
            lock = add_layer_lock(layer, request.user)
            locked_layers.append(lock.layer.get_qualified_name())
            conn_params = lock.layer.datastore.connection_params
            params_dict = json.loads(conn_params)
            host = params_dict["host"]
            port = params_dict["port"]
            dbname = params_dict["database"]
            schema = params_dict["schema"]
            user = params_dict["user"]
            password = params_dict["passwd"]
            conn = gdal_tools.PgConnectionString(host, port, dbname, schema, user, password)
            tables.append({"layer": lock.layer.name, "connection": conn})
        
        (fd, file_path) = tempfile.mkstemp(suffix=".sqlite", prefix="syncdwld_")
        os.close(fd)
        os.remove(file_path)
        if len(tables)>0:
            gdal_tools.postgis2spatialite(tables[0]["layer"], file_path, tables[0]["connection"])
            for table in tables[1:]:
                gdal_tools.postgis2spatialite(table["layer"], file_path, table["connection"])
            
            file = TemporaryFileWrapper(file_path)
            response = FileResponse(file, content_type='application/spatialite')
            #response['Content-Disposition'] = 'attachment; filename=db.sqlite'
            #response['Content-Length'] = os.path.getsize(path)
            return response
        else:
            return HttpResponseBadRequest("Bad request")
        
    except LayerLockingException:
        for layer in locked_layers:
            remove_layer_lock(layer, request.user)
        raise
    except Exception:
        for layer in locked_layers:
            remove_layer_lock(layer, request.user)
        #FIXME: raise a specific exception
        raise
        return HttpResponseBadRequest("Bad request")

def add_layer_lock(qualified_layer_name, user):
    (ws_name, layer_name) = qualified_layer_name.split(":")
    layer_filter = Layer.objects.filter(name=layer_name, datastore__workspace__name=ws_name)
    #ugu = UserGroupUser.objects.filter(user=user)
    #lwg = LayerWriteGroup.objects.filter(group__usergroupuser__user=user)
    is_writable = (layer_filter.filter(layerwritegroup__group__usergroupuser__user=user).count()>0)
    
    if not is_writable:
        raise PermissionDenied
    layer = layer_filter[0]
    
    #is_locked = (LayerLock.objects.filter(layer__name=layer_name, layer__datastore__workspace__name=ws_name).count()>0)
    is_locked = (LayerLock.objects.filter(layer=layer).count()>0)
    if is_locked:
        raise LayerLocked
    new_lock = LayerLock()
    new_lock.layer = layer
    new_lock.created_by = user.username
    new_lock.save()
    return new_lock

def remove_layer_lock(qualified_layer_name, user):
    (ws_name, layer_name) = qualified_layer_name.split(":")
    layer_lock = LayerLock.objects.filter(layer__name=layer_name, layer__datastore__workspace__name=ws_name)
    if len(layer_lock)==1:
        if layer_lock.filter(created_by=user.username).count()!=1:
            # the layer was locked by a different user!!
            raise PermissionDenied()
        layer_filter = Layer.objects.filter(name=layer_name, datastore__workspace__name=ws_name)
        is_writable = (layer_filter.filter(layerwritegroup__group__usergroupuser__user=user).count()>0)
        if not is_writable:
            raise PermissionDenied()
        layer_lock.delete()
        return True
    raise LayerNotLocked()
    
    

  #layers:[ "cities", "roads"],
  #bbox: { xmin: 32.2, xmax: 33.2, ymin: 0.2, ymax: 0.4}

#@login_required(login_url='/gvsigonline/auth/login_user/')
@csrf_exempt
def sync_upload(request):
    if request.is_ajax():
        if request.method == 'POST':
            handle_uploaded_file_raw(request.body.read())
    elif 'fileupload' in request.FILES:
        tmpfile = handle_uploaded_file(request.FILES.get('fileupload'))    
    elif 'fileupload' in request.POST:
        try:
            zipcontents = request.POST.get('fileupload')
            tmpfile = handle_uploaded_file_base64(zipcontents)
        except:
            #syncLogger.exception("'zipfile' param missing or incorrect")
            return HttpResponseBadRequest("'zipfile' param missing or incorrect")
    else:
        #syncLogger.error("'zipfile' param missing or incorrect")
        return HttpResponseBadRequest("'zipfile' param missing or incorrect") 




def handle_uploaded_file(f):
    (destination, path) = tempfile.mkstemp(suffix='.sqlite', dir='/tmp')
    #destination = tempfile.TemporaryFile()
    for chunk in f.chunks():
        destination.write(chunk)
    destination.close()
    print path
    return path

def handle_uploaded_file_base64(fileupload):
    header="data:application/zip;base64,"
    if fileupload[0:len(header)]==header:
        fileupload = fileupload[len(header):].decode('base64')
    (destination, path) = tempfile.mkstemp(suffix='.sqlite', dir='/tmp')
    #destination = tempfile.TemporaryFile()
    asBytes = bytearray(fileupload, "unicode_internal")
    destination.write(asBytes)
    destination.close()
    print path
    return path

def handle_uploaded_file_raw(fileupload):
    #buf=f1.read(1024)
    (destination, path) = tempfile.mkstemp(suffix='.sqlite', dir='/tmp')
    destination.write(fileupload.read())
    destination.close()
    print path
    return path

class TemporaryFileWrapper(tempfile._TemporaryFileWrapper):
    """
    This wrapper opens a file in a way that it ensures the file is deleted when
    is closed (in the same way as it is done by tempfile Python module).
    
    The wrappers offers a file-like object interface, so it can be used as a
    replacement of file objects.
    
    TemporaryFileWrapper is useful in scenarios when the file has to be opened
    and closed several times before being deleted, so it can not be created
    using tempfile.NamedTemporaryFile().
    
    TemporaryFileWrapper is based on tempfile._TemporaryFileWrapper, but the
    constructor of the first one expects a file path as parameter,
    while the second one expects an open file
    
    :param file_path: The path to the file to be opened
    :param binary_mode: True for specifying binary mode, false for text mode.
            It defaults to True
    """
    def __init__(self, file_path, binary_mode=True):
        if binary_mode:
            file = open(file_path, "rb")
        else:
            file = open(file_path, "r")
        tempfile._TemporaryFileWrapper.__init__(self, file, file_path)
    
    def close(self):
        # we can't use os.O_TEMPORARY flag if we are not creating the file,
        # so we need to implement close() also for windows
        if not self.close_called:
            self.close_called = True
            try:
                self.file.close()
            finally:
                if self.delete:
                    self.unlink(self.name)
    
    def __del__(self):
        # we can't use os.O_TEMPORARY flag if we are not creating the file,
        # so we need to implement __del__() also for windows
        self.close()
    
    def __exit__(self, exc, value, tb):
        # we can't use os.O_TEMPORARY flag if we are not creating the file,
        # so we need to implement __exit__() also for windows
        result = self.file.__exit__(exc, value, tb)
        self.close()
        return result


class LayerLockingException(BaseException):
    pass


class LayerNotLocked(LayerLockingException):
    """The requested layer lock does not exist"""
    pass

class LayerLocked(LayerLockingException):
    """The layer already has a lock"""
    pass
