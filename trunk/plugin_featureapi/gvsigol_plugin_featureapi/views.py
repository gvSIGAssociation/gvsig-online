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

@author: Nacho Brodin <nbrodin@scolab.es>
'''
import json
import logging
import os

from django.contrib.auth.decorators import login_required
from django.http.response import HttpResponse

from gvsigol import settings as core_settings
from gvsigol import settings
from gvsigol_plugin_featureapi import util
from gvsigol_plugin_baseapi.validation import Validation, HttpException
from gvsigol_plugin_featureapi.models import FeatureVersions
from gvsigol_services import utils as servicesutils
from gvsigol_services.models import Layer, Datastore, LayerResource
from gvsigol_services import signals
from django.http import HttpResponseForbidden, HttpResponseNotFound
from django_sendfile import sendfile

logging.basicConfig()
logger = logging.getLogger(__name__) 

#Gestión de versión de features:
#Las operaciones de subir fichero, borrar fichero y actualizar feature se salva primero el 
#registro en el histórico y después se actualiza versión y fecha de versión. El resto de operaciones
#se hace al revés.
#A tener en cuenta: si se está haciend un create llamar feature_version_management después de crear la feature
#Si se está haciendo un delete llamar a feature_version_management antes del delete
#Operation: 1-Create feat, 2-Update feat, 3-Delete feat, 4-Upload file, 5-Delete file
@login_required()
def feature_version_management(request):
    if request.method == 'POST':
        try:
            layerid = request.POST.get('lyrid')
            workspace = request.POST.get('workspace')
            lyrname = request.POST.get('lyrname')
            featid = request.POST['featid']
            segments = featid.split(".")
            featid = segments[-1]
            operation = int(request.POST['operation'])
            resource_path = None
            lyr = util.get_layer(layerid, lyrname, workspace)
            layerid = lyr.id
            try:
                if operation == 4 or operation == 5:
                    print('Not managed here')
                    return HttpException(404, "Error en el versionado para la feature").get_exception()
                """
                    resourceid = request.POST['resourceid']
                    resource = LayerResource.objects.get(pk=resourceid)
                    resource_path = resource.path
                elif operation == 5:
                    #FIXME: there is no safe way to store the historic_resource path on resource deletion:
                    # - WE can't use the LayerResource id because the resource has been removed before calling feature_version_management
                    # - We can't trust the path provided by the client, since it can be used to inject arbitrary resources in history, providing
                    # access to any file in the filesystem.
                    # The proper way to solve this is to store the historic in the same view that handles the resource deletion
                    pass
                """
            except Exception:
                pass
            
            if(lyr is None):
                logger.info('No hay capa definida: Error en el versionado para la feature ' + str(featid) + " de la capa " + str(lyrname) + " operacion " + str(operation))
                return HttpResponse(json.dumps({'response':'OK'}, indent=4), content_type='application/json')  

            i, table, schema = servicesutils.get_db_connect_from_layer(lyr)
            with i as con: # connection will auoclose
                version = None
                date = None
                version, date = util.update_feat_version(con, schema, table, featid)
                util.save_version_history(con,  schema, table, layerid, featid, request.user, operation, resource_path)
                    
            response = {
                'feat_version_gvol': version, 
                'feat_date_gvol': str(date)
            }
            return HttpResponse(json.dumps(response, indent=4), content_type='application/json')
        except Exception as e:
            logger.exception('Error en el versionado para la feature ' + str(featid) + " de la capa " + str(layerid) + " operacion " + str(operation) + " ERROR:" + str(e))
            return HttpException(400, "Error en el versionado para la feature").get_exception()

def getResourceURL(request):
    name = request.POST['path']
    if(name.find("/") > 0):
        if("https://" in name or "http://" in name):
            return name
        else:
            return core_settings.MEDIA_URL + name
    type_ = util.getResourceType(name)
    abs_path = servicesutils.get_resources_dir(type_) + "/" + name
    rel_path = abs_path.replace(core_settings.MEDIA_ROOT, '')        
    return core_settings.MEDIA_URL + rel_path

def check_version(request):
    try:
        workspace = request.POST['workspace']
        lyrname = request.POST['lyrname']
        operation = int(request.POST['operation'])
        version = request.POST.get('version')
        featid = request.POST.get('featid')
        if featid:
            segments = featid.split(".")
            featid = segments[-1]

        validation = Validation(request)
        lyr = util.get_layer(None, lyrname, workspace)
        i, table, schema = servicesutils.get_db_connect_from_layer(lyr)
        with i as con: # connection will autoclose
            table_info = con.get_table_info(table, schema=schema)
            if operation == 1:
                use_versions = validation.check_version_and_date_columns(lyr, con, schema, table, table_info, default_version=0)
            else:
                use_versions = validation.check_version_and_date_columns(lyr, con, schema, table, table_info)
            code = 200
            msg = 'OK'
            
            if (use_versions and featid and version and operation != 1):
                validation.check_feature_version(con, schema, table, featid, version)
    except HttpException:
        raise
    except Exception:
        logger.exception("Error checking feature version")
        code = 400
        msg = 'Capa no válida'
    
    response = {
            'msg': msg,
            'code': code
        }
    return HttpResponse(json.dumps(response, indent=4), content_type='application/json')

#@login_required(login_url='/gvsigonline/auth/login_user/')
#@superuser_required
def create_feature(request):
    if request.method == 'POST':
        values = request.get_full_path().split("/")
        lyr_id = values[len(values) - 2]
             
        v = Validation(request)
        try:
            content = get_content(request)
            v.check_create_feature(lyr_id, content)
        except HttpException as e:
            return e.get_exception()
         
         
        print(content)
             
        #return HttpResponse(json.dumps({'response':'OK'}, indent=4), content_type='folder/json')   
        return HttpResponse(json.dumps({'response':'OK'}, indent=4), content_type='application/json')  
 
 
def update_feature(request):
    if request.method == 'PUT':
        values = request.get_full_path().split("/")
        feat_id = values[len(values) - 2]
        lyr_id = values[len(values) - 3]
         
        v = Validation(request)    
        try:
            content = get_content(request)
            v.check_update_feature(feat_id, lyr_id, content)
        except HttpException as e:
            return e.get_exception()
         
        print(content)
             
        #return HttpResponse(json.dumps({'response':'OK'}, indent=4), content_type='folder/json')   
        return HttpResponse(json.dumps({'response':'OK'}, indent=4), content_type='application/json') 
     

def test(request, id):
    return HttpResponse(json.dumps({'response':'OK'}, indent=4), content_type='application/json')
     
def get_content(request):
    try:
        body_unicode = request.body.decode('utf-8')
        return json.loads(body_unicode)
    except Exception:
        raise HttpException(400, "Feature malformed.")

def get_layer_historic_resource(request, layer_id, feat_id, version):
    try:
        lyr = Layer.objects.get(pk=layer_id)
        if not servicesutils.can_read_layer(request, lyr):
            return HttpResponseForbidden()
        feature_change = FeatureVersions.objects.get(layer=lyr, feat_id=feat_id, version=version)
        if not feature_change.resource:
            return HttpResponseNotFound()
        # return reverse('get_layer_historic_resource', args=[layer_id, feat_id, version])
        resource_path = os.path.join(settings.MEDIA_ROOT, feature_change.resource)
        return sendfile(request, resource_path, attachment=False)
    except Layer.DoesNotExist:
        return HttpResponseNotFound()
    except FeatureVersions.DoesNotExist:
        return HttpResponseNotFound()

def layerresource_deleted_handler(sender, **kwargs):
    try:
        layer = kwargs['layer']
        featid = kwargs['featid']
        historical_path = kwargs['historical_path']
        user = kwargs['user']
        operation = 5 # delete resource
        i, table, schema = servicesutils.get_db_connect_from_layer(layer)
        with i as con:
            util.save_version_history(con, schema, table, layer.pk, featid, user, operation, historical_path)
    except Exception as e:
        logger.exception("Error saving version history")

def layerresource_created_handler(sender, **kwargs):
    try:
        layer = kwargs['layer']
        featid = kwargs['featid']
        path = kwargs['path']
        user = kwargs['user']
        operation = 4 # create resource
        i, table, schema = servicesutils.get_db_connect_from_layer(layer)
        with i as con:
            util.save_version_history(con, schema, table, layer.pk, featid, user, operation, path)
    except Exception as e:
        logger.exception("Error saving version history")

signals.layerresource_deleted.connect(layerresource_deleted_handler)
signals.layerresource_created.connect(layerresource_created_handler)
