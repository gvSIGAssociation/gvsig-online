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
@author: Cesar Martinez Izquierdo - http://www.scolab.es
'''

from io import BytesIO
import io
import json
import logging
import shutil
import sqlite3
import tempfile
import time, os

from PIL import Image
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect, HttpResponseBadRequest, HttpResponseNotFound, HttpResponse
from django.http import JsonResponse
from django.http.response import StreamingHttpResponse, FileResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_safe, require_POST, require_GET
import gdaltools
from spatialiteintrospect import introspect as sq_introspect

from gvsigol import settings
from gvsigol_auth import auth_backend
from gvsigol_core import geom
from gvsigol_services import utils
from gvsigol_services import geographic_servers
from gvsigol_services import backend_postgis as pg_introspect
from gvsigol_services.models import Workspace, Datastore, LayerGroup, Layer, LayerLock, \
    LayerResource
from gvsigol_services.locks_utils import *

DEFAULT_BUFFER_SIZE = 1048576

## 2xx: upload errors
SYNCERROR_UPLOAD="ERROR_GOL_200-Error on sync ulpoad"
SYNCERROR_LAYER_NOT_LOCKED="ERROR_GOL_201-Layer is not locked: {0}"
SYNCERROR_FILEPARAM_MISSING="ERROR_GOL_202-'fileupload' param missing or incorrect"
SYNCERROR_FILE_MISSING='ERROR_GOL_203-No valid file was provided'
SYNCERROR_INCONSISTENT_LAYER_STATUS="ERROR_GOL_204-Inconsistent status for layer: {0}"
SYNCERROR_INVALID_DB="ERROR_GOL_205-The file is not a valid Sqlite3 db"
SYNCERROR_UNREADABLE_LAYER="ERROR_GOL_206-The layer can't be read: {0}"

logger = logging.getLogger(__name__)


@require_safe
def get_layerinfo(request):
    if not isinstance(request.user, AnonymousUser) :
        roles = auth_backend.get_roles(request)
        readWriteLayers = Layer.objects.filter(layerwriterole__role__in=roles, layerlock__isnull=True)
        layerJson = layersToJson([], [], readWriteLayers)
    else:
        layerJson = layersToJson([], [], [])
    return HttpResponse(layerJson, content_type='application/json')


@require_GET
def get_layerinfo_by_project(request, project):
    if not isinstance(request.user, AnonymousUser) :
        roles = auth_backend.get_roles(request)
        readWriteLayers = Layer.objects.filter(layerwriterole__role__in=roles, layerlock__isnull=True).filter(layer_group__projectlayergroup__project=project)
        layerJson = layersToJson([], [], readWriteLayers)
    else:
        layerJson = layersToJson([], [], [])
    return HttpResponse(layerJson, content_type='application/json')

    
def fill_layer_attrs(layer, permissions):
    row = {}
    gs = geographic_servers.get_instance().get_server_by_id(layer.datastore.workspace.server.id)
    geom_info = gs.get_geometry_info(layer)
    if geom_info:
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
            if row:
                result.append(row)
                layerIds.add(layer.id)
            
    for layer in readOnlyLayers:
        if not layer.id in layerIds:
            row = fill_layer_attrs(layer, 'read-only')
            if row:
                result.append(row)
                layerIds.add(layer.id)
    
    for layer in universallyReadableLayers:
        if not layer.id in layerIds:
            row = fill_layer_attrs(layer, 'read-only')
            if row:
                result.append(row)
                layerIds.add(layer.id)
            
    layerStr = json.dumps(result)
    return layerStr

@login_required()
@require_POST
def sync_download(request):
    locks = []
    prepared_tables = []
    try:
        request_params = json.loads(request.body)
        layers = request_params["layers"]
        # we will ignore bbox for the moment
        bbox = request_params.get("bbox", None)
        for layer in layers:
            #FIXME: maybe we need to specify if we want the layer for reading or writing!!!! Assume we always want to write for the moment
            lock = add_layer_lock(layer, request, lock_type=LayerLock.SYNC_LOCK)
            locks.append(lock)
            conn = _get_layer_conn(lock.layer)
            if not conn:
                raise HttpResponseBadRequest("Bad request")
            prepared_tables.append({"layer": lock.layer, "connection": conn})
        
        (fd, file_path) = tempfile.mkstemp(suffix=".sqlite", prefix="syncdwld_")
        os.close(fd)
        os.remove(file_path)
        if len(prepared_tables)>0:
            ogr = gdaltools.ogr2ogr()
            ogr.set_output_mode(
                    layer_mode=ogr.MODE_LAYER_CREATE,
                    data_source_mode=ogr.MODE_DS_CREATE_OR_UPDATE)
            for table in prepared_tables:
                if table["connection"].schema:
                    in_tbl_name = table["connection"].schema + "." + table["layer"].name
                else:
                    in_tbl_name = table["layer"].name
                ogr.set_input(
                        table["connection"],
                        table_name=in_tbl_name
                ).set_output(
                        file_path,
                        table_name=table["layer"].get_qualified_name()
                ).execute()

            gdaltools.ogrinfo(file_path, sql="SELECT UpdateLayerStatistics()")
            locked_layers = [ lock.layer for lock in locks]
            _copy_images(locked_layers, file_path)
            file = TemporaryFileWrapper(file_path)
            response = FileResponse(file, content_type='application/spatialite')
            #response['Content-Disposition'] = 'attachment; filename=db.sqlite'
            #response['Content-Length'] = os.path.getsize(path)
            return response
        else:
            return HttpResponseBadRequest("Bad request")

    except Exception as exc:
        for layer in locks:
            remove_layer_lock(lock.layer, request)
        logger.exception("sync_download error")
        return HttpResponseBadRequest("Bad request")


@login_required()
@require_POST
def sync_commit(request):
    return sync_upload(request, False)

@login_required()
@require_POST
def sync_upload(request, release_locks=True):
    tmpfile = None

    if 'fileupload' in request.FILES:
        tmpfile = handle_uploaded_file(request.FILES.get('fileupload'))
    elif 'fileupload' in request.POST:
        try:
            zipcontents = request.POST.get('fileupload')
            tmpfile = handle_uploaded_file_base64(zipcontents)
        except:
            logger.exception(SYNCERROR_FILEPARAM_MISSING)
            return HttpResponseBadRequest(SYNCERROR_FILEPARAM_MISSING)
    elif request.method == 'POST':
        tmpfile = handle_uploaded_file_raw(request)
    else:
        logger.error(SYNCERROR_FILE_MISSING)
        return HttpResponseBadRequest(SYNCERROR_FILE_MISSING)
    if tmpfile:
        # 1 - check if the file is a spatialite database
        # 2 - check if the included tables are locked and writable by the user
        # 3 - overwrite the tables in DB using the uploaded tables
        # 4 - remove the table locks
        # 5 - handle images
        # 6 - remove the temporal file
        try:
            db = sq_introspect.Introspect(tmpfile)
            try:
                tables = db.get_geometry_tables()
                locks = []
                for t in tables:
                    # first check all the layers are properly locked and writable
                    layer_parts = t.split(":")
                    if len(layer_parts) == 2:
                        ws_name, layer_name = layer_parts
                    lock = get_layer_lock(ws_name, layer_name, request, check_writable=True, lock_type=LayerLock.SYNC_LOCK)
                    locks.append(lock)
                for lock in locks:
                    ogr = gdaltools.ogr2ogr()
                    qualified_layer_name = lock.layer.get_qualified_name()
                    geom_info = db.get_geometry_columns_info(qualified_layer_name)
                    if len(geom_info)>0 and len(geom_info[0])==7:
                        srs = "EPSG:"+str(geom_info[0][3])
                        ogr.set_input(tmpfile, table_name=qualified_layer_name, srs=srs)
                        conn = _get_layer_conn(lock.layer)
                        if not conn:
                            raise HttpResponseBadRequest(SYNCERROR_INCONSISTENT_LAYER_STATUS)
                        if conn.schema:
                            tbl_name = conn.schema + "." + lock.layer.name
                        else:
                            tbl_name = lock.layer.name
                        ogr.set_output(conn, table_name=tbl_name)
                        ogr.set_output_mode(ogr.MODE_LAYER_OVERWRITE, ogr.MODE_DS_UPDATE)
                        ogr.execute()

                        # workaround ogr2ogr behaviour which does not update the associated pk serial sequence
                        pgdb = pg_introspect.Introspect(conn.dbname, conn.host, conn.port, conn.user, conn.password)
                        schema = conn.schema if conn.schema else 'public'
                        pgdb.update_pk_sequences(lock.layer.name, schema)
                        pgdb.close()

                        gs = geographic_servers.get_instance().get_server_by_id(lock.layer.datastore.workspace.server.id)
                        gs.updateBoundingBoxFromData(lock.layer)
                    else:
                        raise HttpResponseBadRequest(SYNCERROR_UNREADABLE_LAYER.format(lock.layer.get_qualified_name())) 
            finally:
                db.close()
            
            #import time
            # approach 1
            #t1 = time.clock()
            layers = [ lock.layer for lock in locks]
            replacer = ResourceReplacer(tmpfile, layers)
            replacer.process()
            #t2 = time.clock()
            
            # approach 2
            #_remove_existing_images(layers)
            #_extract_images(tmpfile)
            
            #t3 = time.clock()
            #print "Time approach 1: " + str(t2-t1)
            #print "Time approach 2: " + str(t3-t2)
            

            if release_locks:
                for lock in locks:
                    # everything was fine, release the locks now
                    lock.delete()
        except sq_introspect.InvalidSqlite3Database:
            logger.exception(SYNCERROR_INVALID_DB)
            return HttpResponseBadRequest(SYNCERROR_INVALID_DB)
        except LayerNotLocked as e:
            logger.exception(SYNCERROR_LAYER_NOT_LOCKED.format(e.layer))
            return HttpResponseBadRequest(SYNCERROR_LAYER_NOT_LOCKED.format(e.layer))
        except:
            logger.exception(SYNCERROR_UPLOAD)
            return HttpResponseBadRequest(SYNCERROR_UPLOAD)
        finally:
            os.remove(tmpfile)
    return JsonResponse({'response': 'OK'})

def _remove_existing_images(tables):
    resources = LayerResource.objects.filter(layer__name__in=tables, type=LayerResource.EXTERNAL_IMAGE)
    for r in resources:
        img_path = r.path
        if os.path.isfile(img_path):
            os.remove(img_path)
    resources.delete()
    for r in resources:
        # should print nothing as we have removed all the resources
        print(r)

def _extract_images(db_path):
    """
    Extracts images from the sqlite database to the server side (LayerResource
    table + file system images)
    """
    conn = sqlite3.connect(db_path)
    image_dir = utils.get_resources_dir(LayerResource.EXTERNAL_IMAGE)
    try:
        cursor = conn.cursor()
        sql = "SELECT id, restable, rowidfk, resblob, resname FROM geopap_resource WHERE type = 'BLOB_IMAGE'"
        result = cursor.execute(sql)
        for row in result:
            (ws_name, layer_name) = row[1].split(":")
            layer = Layer.objects.get(name=layer_name, datastore__workspace__name=ws_name)
            (fd, f) = tempfile.mkstemp(suffix=".JPG", prefix="img-gol-", dir=image_dir)
            output_file = os.fdopen(fd, "wb")
            try:
                output_file.write(row[3])
                server_path = os.path.relpath(f, settings.MEDIA_ROOT)
                res = LayerResource()
                res.id = row[0]
                res.feature = row[2]
                res.layer = layer
                res.path = server_path
                res.title = row[4]
                res.type = LayerResource.EXTERNAL_IMAGE
                res.created = timezone.now()
                res.save()
            finally:
                output_file.close()


    finally:
        conn.close()


def _copy_images(layers, db_path):
    """
    Copies images for the provided layers from LayerResource to a SpatialiteDb
    """
    server_resources = LayerResource.objects.filter(layer__name__in=layers, type=LayerResource.EXTERNAL_IMAGE)
    conn = sqlite3.connect(db_path)
    sql_create = """CREATE TABLE geopap_resource (id integer PRIMARY KEY NOT NULL, restable text, type integer, resname TEXT, rowidfk TEXT, respath TEXT, resblob BLOB, resthumb BLOB)"""
    conn.execute(sql_create)
    # some PRAMA for faster inserts
    conn.execute("PRAGMA synchronous = OFF")
    conn.execute("PRAGMA journal_mode = MEMORY")
    try:
        cursor = conn.cursor()
        sql = "INSERT INTO geopap_resource (id, restable, type, resname, rowidfk, respath, resblob, resthumb) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
        for r in server_resources:
            # FIXME: we are loading in memory the whole image
            # We should investigate if we can pass an iterable to cursor.execute.
            # It seems to NOT be supported for the moment, but we can check again in future versions 
            thumb_buffer = BytesIO()
            abs_path = os.path.join(settings.MEDIA_ROOT, r.path)
            img = Image.open(abs_path)
            img.thumbnail([100, 100])
            img.save(thumb_buffer, "JPEG")
            
            img = open(abs_path, mode='rb')
            img_bytes = img.read()
            img_buffer = buffer(img_bytes)
            img.close()

            # NOTE: we insert r.path in the sqlite, as it is useful for selectively replacing images when uploading again 
            cursor.execute(sql, (r.id, r.layer.get_qualified_name(), 'BLOB_IMAGE', r.title, r.feature, r.path, img_buffer, buffer(thumb_buffer.getvalue())))
            img.close()
            thumb_buffer.close()
        conn.commit()

    finally:
        conn.close()


def _get_layer_conn(layer):
    try:
        conn_params = layer.datastore.connection_params
        params_dict = json.loads(conn_params)
        host = params_dict["host"]
        port = params_dict["port"]
        dbname = params_dict["database"]
        schema = params_dict["schema"]
        user = params_dict["user"]
        password = params_dict["passwd"]
        return gdaltools.PgConnectionString(host, port, dbname, schema, user, password)
    except:
        pass


def handle_uploaded_file(f):
    (destination, path) = tempfile.mkstemp(suffix='.sqlite', dir='/tmp')
    for chunk in f.chunks():
        destination.write(chunk)
    destination.close()
    print(path)
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
    print(path)
    return path


def handle_uploaded_file_raw(request):
    (fd_dest, path) = tempfile.mkstemp(suffix='.sqlite', dir='/tmp')
    destination = os.fdopen(fd_dest, "w", DEFAULT_BUFFER_SIZE)
    shutil.copyfileobj(request, destination, DEFAULT_BUFFER_SIZE)
    destination.close()
    print(path)
    return path

class ResourceReplacer():
    """
    Compares existing resources with the uploaded ones and performs and efficient
    update of the LayerResources tables, considering only deletions and insertions.
    """
    
    def __init__(self, db_path, layers):
        self.db_path = db_path
        self.layers = layers
        self.sqlite_conn = None
        self.image_dir = utils.get_resources_dir(LayerResource.EXTERNAL_IMAGE)
    
    def _get_sqlite_iterator(self):
        self.sqlite_conn = sqlite3.connect(self.db_path)
        cursor = self.sqlite_conn.cursor()
        sql = "SELECT id, restable, rowidfk, resblob, resname, respath FROM geopap_resource WHERE type = 'BLOB_IMAGE' ORDER BY id"
        return cursor.execute(sql)

    def process(self):
        """
        The strategy to follow is:
        - any resource id present in the sqlite and missing in the server is
        considered an insert
        - any resource id present in the server and missing in the sqlite is
        considered a deletion
        - if the ids are present in both sides, we consider this to be a
        replacement (deletion + insert) if the path field differs. Otherwise we
        consider to be the same resource and we ignore it. Note that it is not
        possible to have a collision with the ids caused by a new server side
        image, because the layer is locked by the tablet so it is not possible
        to add new resources on the server in the meantime.
        """
        try:
            sqlite_resources = self._get_sqlite_iterator()
            server_resources = LayerResource.objects.filter(layer__in=self.layers, type=LayerResource.EXTERNAL_IMAGE).order_by("id").iterator()

            sq_res = self._get_next(sqlite_resources)
            srv_res = self._get_next(server_resources)
            while sq_res or srv_res:
                if sq_res and srv_res:
                    if sq_res[0] == srv_res.id:
                        if sq_res[5] != srv_res.path:
                            self._remove_resource(srv_res)
                            self._insert(sq_res)
                        sq_res = self._get_next(sqlite_resources)
                        srv_res = self._get_next(server_resources)
                    elif sq_res[0] > srv_res.id:
                        self._remove_resource(srv_res)
                        srv_res = self._get_next(server_resources)
                    else:
                        self._insert(sq_res)
                        sq_res = self._get_next(sqlite_resources)
                elif sq_res:
                    self._insert(sq_res)
                    sq_res = self._get_next(sqlite_resources)
                else:
                    self._remove_resource(srv_res)
                    srv_res = self._get_next(server_resources)
        finally:
            if self.sqlite_conn:
                self.sqlite_conn.close()

    def _remove_resource(self, resource):
        if os.path.isfile(resource.path):
            os.remove(resource.path)
        resource.delete()

    def _insert(self, newres):
        # FIXME: maybe we should process the resources by layer to avoid
        # getting the layer object again and again
        (ws_name, layer_name) = newres[1].split(":")
        layer = Layer.objects.get(name=layer_name, datastore__workspace__name=ws_name)
        
        (fd, f) = tempfile.mkstemp(suffix=".JPG", prefix="img-gol-", dir=self.image_dir)
        output_file = os.fdopen(fd, "wb")
        try:
            output_file.write(newres[3])
            server_path = os.path.relpath(f, settings.MEDIA_ROOT)
            res = LayerResource()
            res.feature = newres[2]
            res.layer = layer
            res.path = server_path
            res.title = newres[4]
            res.type = LayerResource.EXTERNAL_IMAGE
            res.save()
        finally:
            output_file.close()

    def _get_next(self, iterator):
        """
        Returns the next object in the iterable or None if we have finished
        """
        try:
            return next(iterator)
        except StopIteration:
            return None


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

