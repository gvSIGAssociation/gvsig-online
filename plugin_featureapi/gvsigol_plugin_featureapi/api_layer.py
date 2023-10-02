# -*- coding: utf-8 -*-

'''
    gvSIG Online.
    Copyright (C) 2010-2019 SCOLAB.

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
from wsgiref.util import FileWrapper
import ast
import coreapi
from django.http.response import HttpResponse, JsonResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.filters import BaseFilterBackend
from rest_framework.generics import ListAPIView, ListCreateAPIView, DestroyAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.parsers import FormParser
from gvsigol_plugin_featureapi.export import VectorLayerExporter
from gvsigol_plugin_featureapi.serializers import FeatureSerializer, LayerChangesSerializer, LayerCreateSerializer, StyleSerializer
from gvsigol_plugin_featureapi.serializers import LayerSerializer
from gvsigol_plugin_baseapi.validation import Validation, HttpException
from gvsigol_services import geographic_servers
from gvsigol_services import views as serviceviews
from gvsigol_services.models import Layer
from gvsigol_symbology.models import StyleLayer, Style
from . import serializers
from . import util
from gvsigol_services import utils as services_utils
from gvsigol_services import views as services_views
from psycopg2 import sql as sqlbuilder
from gvsigol_services.forms_geoserver import CreateFeatureTypeForm
from gvsigol_services.models import LayerFieldEnumeration, TriggerProcedure, Trigger
from gvsigol_services.tasks import refresh_layer_info
import re
from django.utils.translation import gettext_lazy as _

class LangFilter(BaseFilterBackend):
    def get_schema_fields(self, view):
        fields = [
            coreapi.Field(name="lang", description="Language (Ex: es, en, fr, val, etc). Default es", required=False, location='query', example='es'),
        ]
        return fields



class SearchFeatureFilter(BaseFilterBackend):
    def get_schema_fields(self, view):
        fields = [
            coreapi.Field(name="minlat", description="Latitude", required=True, location='query', example='39.469350'),
            coreapi.Field(name="minlon", description="Longitude", required=True, location='query', example='-0.390024'),
            coreapi.Field(name="maxlat", description="Latitude", required=True, location='query', example='39.469350'),
            coreapi.Field(name="maxlon", description="Longitude", required=True, location='query', example='-0.390024'),
            coreapi.Field(name="pagesize", description="Maximum number of features to send for each pages", required=False, location='query', example='32'),
            coreapi.Field(name="page", description="Number of page to send", required=False, location='query', example='1'),
            coreapi.Field(name="geom", description="true to get the geometry", required=False, location='query', example='true'),
            coreapi.Field(name="search", description="string to search", required=False, location='query', example='mystring'),
        ]
        return fields

class ProjectFilter(BaseFilterBackend):
    def get_schema_fields(self, view):
        fields = [
            coreapi.Field(name="label", description="Label (Ex: mobile, etc). Default null", required=False, location='query', example='mobile'),
        ]
        return fields

class FieldOptionsFilter(BaseFilterBackend):
    def get_schema_fields(self, view):
        fields = [
            coreapi.Field(name="fieldselected", description="Field selected", required=True, location='query', example='id'),
        ]
        return fields

class TimestampFilter(BaseFilterBackend):
    def get_schema_fields(self, view):
        fields = [
            coreapi.Field(name="timestamp", description="Timestamp", required=False, location='query', example='1581423697'),
            coreapi.Field(name="ncolumns", description="Number of columns", required=False, location='query', example='4'),
            coreapi.Field(name="layertype", description="Type of layer", required=False, location='query', example='features'),
            coreapi.Field(name="zone", description="Zone name", required=False, location='query', example='Mi zona'),
        
        ]
        return fields


#--------------------------------------------------
#              LayerFieldOptions
#--------------------------------------------------
class LayerFieldOptions(ListAPIView):
    serializer_class = FeatureSerializer
    filter_backends = (FieldOptionsFilter, )
    permission_classes=[AllowAny]
    
    @swagger_auto_schema(operation_id='get_layer_field_options', operation_summary='Gets the options list of a layer field',
                         responses={404: "Database connection NOT found<br>User NOT found<br>Layer NOT found<br>Page NOT found", 
                                    403: "The layer is not allowed to this user", 
                                    400: "Field options list cannot be obtained. Unexpected error:..."})
    @action(detail=True, methods=['GET'])
    def get(self, request, lyr_id):
        """
        This call returns a array with a options list of a selected layer field.
        """
        validation = Validation(request)
        validation.check_read_permission(lyr_id)
          
        try:
            if 'fieldselected' in self.request.GET:
                try:
                    fieldSelected = self.request.GET['fieldselected']
                except Exception:
                    raise HttpException(400, "Bad parameter fieldSelected. The value must be a layer field")

            result = serializers.FeatureSerializer().list_field_options(lyr_id, fieldSelected)
            return JsonResponse(result, safe=False)
        except HttpException as e:
            return e.get_exception()

    
#--------------------------------------------------
#              PublicLayerFieldOptions
#--------------------------------------------------
class PublicLayerFieldOptions(ListAPIView):
    serializer_class = FeatureSerializer
    filter_backends = (FieldOptionsFilter, )
    permission_classes=[AllowAny]
    
    @swagger_auto_schema(operation_id='get_layer_field_options', operation_summary='Gets the options list of a layer field',
                         responses={404: "Database connection NOT found<br>User NOT found<br>Layer NOT found<br>Page NOT found", 
                                    403: "The layer is not allowed to this user", 
                                    400: "Field options list cannot be obtained. Unexpected error:..."})
    @action(detail=True, methods=['GET'])
    def get(self, request, lyr_id):
        """
        This call returns a array with a options list of a selected layer field.
        """
        validation = Validation(request)
        validation.is_public_layer(lyr_id)
          
        try:
            if 'fieldselected' in self.request.GET:
                try:
                    fieldSelected = self.request.GET['fieldselected']
                except Exception:
                    raise HttpException(400, "Bad parameter fieldSelected. The value must be a layer field")

            result = serializers.FeatureSerializer().list_field_options(lyr_id, fieldSelected)
            return JsonResponse(result, safe=False)
        except HttpException as e:
            return e.get_exception()



#--------------------------------------------------
#                    Legend
#--------------------------------------------------
class Legend(ListAPIView):
    serializer_class = None
    
    @swagger_auto_schema(operation_id='get_geoserver_legend', operation_summary='Get the geoserver legend',
                          responses={
                                    404: "Resource NOT found"
                                    })
    @action(detail=True, methods=['GET'], permission_classes=[IsAuthenticated])
    def get(self, request, lyr_id):
        validation = Validation(request)
        try:
            validation.check_read_permission(lyr_id)
        except HttpException as e:
            return e.get_exception()
        try:
            lyr = Layer.objects.get(id=lyr_id)
            front_url = lyr.datastore.workspace.wms_endpoint #.server.frontend_url
            url = front_url + "?REQUEST=GetLegendGraphic&VERSION=1.0.0&FORMAT=image/png&LAYER=" + lyr.name
            return JsonResponse({"url" : url}, safe=False)
        except Exception as e:
            return HttpException(404, "Resource NOT found").get_exception()


#--------------------------------------------------
#                 PublicLegend
#--------------------------------------------------
class PublicLegend(ListAPIView):
    serializer_class = None
    permission_classes=[AllowAny]
    
    @swagger_auto_schema(operation_id='get_geoserver_public_legend', operation_summary='If the layer is public get the geoserver legend',
                          responses={
                                    404: "Resource NOT found"
                                    })
    @action(detail=True, methods=['GET'], permission_classes=[IsAuthenticated])
    def get(self, request, lyr_id):
        validation = Validation(request)
        try:
            validation.is_public_layer(lyr_id)
            validation.check_read_permission(lyr_id)
        except HttpException as e:
            return e.get_exception()
        try:
            lyr = Layer.objects.get(id=lyr_id)
            front_url = None
            if lyr.datastore is None:
                if lyr.external_params:
                    params = json.loads(lyr.external_params)
                    front_url = params['url']
                    lyr.name = params['layers']
            else:
                front_url = lyr.datastore.workspace.wms_endpoint #.server.frontend_url
            
            if front_url is not None:
                url = front_url + "?REQUEST=GetLegendGraphic&VERSION=1.0.0&FORMAT=image/png&LAYER=" + lyr.name
                return JsonResponse({"url" : url}, safe=False)
            else:
                return HttpException(404, "Resource NOT found").get_exception()
        except Exception as e:
            return HttpException(404, "Resource NOT found").get_exception()



#--------------------------------------------------
#                LayerChanges
#--------------------------------------------------
class LayerChanges(ListAPIView):
    serializer_class = LayerChangesSerializer
    filter_backends = (TimestampFilter,)
    
    @swagger_auto_schema(operation_id='check_changes', operation_summary='Checks if a layer has changes since the last update',
                         responses={404: "Database connection NOT found<br>User NOT found<br>Layer NOT found", 
                                    403: "The layer is not allowed to this user"})
    @action(detail=True, methods=['GET'], permission_classes=[IsAuthenticated])
    def get(self, request, lyr_id):
        """
        For vector layers returns 0 if there is not changes, returns the number of rows that have changed or returns 1 if the columns structure has changed. 
        For tiled layers returns 0 if there is not changes or the new version number if there is changes.
        - layertype: (it's not mandatory. Default features) features or tiles
        - ncolumns: (mandatory only for type 'features'). Gets the current number of columns of your layer to know if the columns structure has changed
        - timestamp: (mandatory). The version number of the layer to check
        - zone: (mandatory only for type 'tiles'). Zone name. It's useful to know the zone because a tile layer change when the package is replaced with a new version and this package
        is related with a zone layer.
        """
        v = Validation(request)    
        try:
            v.check_get_layer(lyr_id)

            timestamp = 0
            if 'timestamp' in self.request.GET:
                try:
                    timestamp = int(self.request.GET['timestamp'])
                except Exception:
                    raise HttpException(400, "Bad parameter timestamp. The value must be a integer")

            
            ncolumns = 0
            if 'ncolumns' in self.request.GET:
                try:
                    ncolumns = int(self.request.GET['ncolumns'])
                except Exception:
                    raise HttpException(400, "Bad parameter ncolumns. The value must be a integer")
            
            layertype = 'features'
            if 'layertype' in self.request.GET:
                try:
                    layertype = self.request.GET['layertype']
                except Exception:
                    raise HttpException(400, "Bad parameter layertype")

            #Las capas tileadas o con paquetes pregenerados pueden cambiar pero el paquete puede
            #estar asociado a una zona por lo que se comprobará si hay cambios para ese paquete (versión)
            #y esa zona
            zone = None
            if 'zone' in self.request.GET:
                try:
                    zone = self.request.GET['zone']
                except Exception:
                    raise HttpException(400, "Bad parameter zone")


            result = serializers.LayerChangesSerializer().check_changes(timestamp, lyr_id, ncolumns, layertype, zone)
            return JsonResponse({"nmodified" : result}, safe=False)

        except HttpException as e:
            return e.get_exception()

            result = serializers.LayerChangesSerializer().check_changes(timestamp, lyr_id)
            return JsonResponse({"nmodified" : result}, safe=False)

        except HttpException as e:
            return e.get_exception()



#--------------------------------------------------
#                LayerListView
#--------------------------------------------------
class LayerListView(ListCreateAPIView):
    parser_classes = (FormParser,)
    def get_serializer_class(self):
        if self.request._request.method in ['GET', 'HEAD', 'OPTIONS']:
            return LayerSerializer
        return LayerCreateSerializer

    def get_permissions(self):
        if self.request._request.method in ['GET', 'HEAD', 'OPTIONS']:
            return [ AllowAny() ]
        return [ IsAuthenticated() ]
    
    @swagger_auto_schema(operation_id='get_layer_list', operation_summary='Gets the list of layers in the application',
                         responses={404: "Database connection NOT found<br>User NOT found"})
    @action(detail=True, methods=['GET'])
    def get(self, request):
        # no need for validation since will get the layer visible for the user
        queryset = services_utils.get_layerread_by_user(request)

        queryset.connections = util.get_pool_connection(queryset)
        serializer = LayerSerializer(queryset, many=True, context={'request': request, 'user': request.user.username})
        result = {
            "content" : serializer.data,
            "links" : [
                {
                    "rel" : "self",
                    "href": request.get_full_path()
                }
            ]
        }
        util.destroy_pool_connection(queryset.connections)
        return JsonResponse(result, safe=False)

    @swagger_auto_schema(operation_id='create_layer', operation_summary='Creates a new layer',
                         responses={404: "Database connection NOT found<br>User NOT found<br>Layer NOT found", 
                                    403: "The user does not have permission to create this layer",
                                    400: "Error creating the layer"}) 
    @action(detail=True, methods=['POST'])
    def post(self, request):
        try:
            #content = util.get_content(request)
            geom_type = 'point'
            if 'geom_type' in self.request.POST:
                try:
                    geom_type = self.request.POST['geom_type']
                except Exception:
                    raise HttpException(400, "Bad parameter geom_type (Point,Linestring,Polygon)")

            datastore = None
            if 'datastore' in self.request.POST:
                try:
                    datastore = int(self.request.POST['datastore'])
                except Exception:
                    raise HttpException(400, "Bad parameter datastore. It must be a integer ID")

            name = None
            if 'name' in self.request.POST:
                try:
                    name = str(self.request.POST['name'])
                except Exception:
                    raise HttpException(400, "Bad parameter name")

            title = None
            if 'title' in self.request.POST:
                try:
                    title = self.request.POST['title']
                except Exception:
                    raise HttpException(400, "Bad parameter title")

            srs = None
            if 'srs' in self.request.POST:
                try:
                    srs = self.request.POST['srs']
                    if(not srs.startswith("EPSG:")):
                        raise Exception()
                except Exception:
                    raise HttpException(400, "Bad parameter srs")

            layer_group = None
            if 'layer_group' in self.request.POST:
                try:
                    layer_group = self.request.POST['layer_group']
                except Exception:
                    raise HttpException(400, "Bad parameter layer_group")

            fields = None
            if 'fields' in self.request.POST:
                try:
                    fields = self.request.POST['fields']
                except Exception:
                    raise HttpException(400, "Bad parameter fields. Ex: [{\"id\":\"klt01kb332\",\"name\":\"fieldName\",\"type\":\"character_varying\",\"calculation\":\"\",\"calculationLabel\":\"\"}]")

            md_abstract = None
            if 'md-abstract' in self.request.POST:
                try:
                    md_abstract = self.request.POST['md-abstract']
                except Exception:
                    raise HttpException(400, "Bad parameter md-abstract")

            validation = Validation(request)
            validation.check_create_layer(request.user.username, datastore)
            lyr_id = layer_create(request, layer_group)
            
            queryset = Layer.objects.select_related('datastore').get(id = lyr_id)
            queryset.connections = util.get_pool_connection(queryset)
            serializer = LayerSerializer(queryset, context={'request': request, 'user': request.user.username})
            result = {
                "content" : serializer.data
            }
            util.destroy_pool_connection(queryset.connections)

            return JsonResponse(result, safe=False)
        except HttpException as e:
            print(e)
            return e.get_exception()
        except Exception as e:
            print(e)
            return(e)
    
    
def layer_create(request, layer_group_id):

    layer_type = "gs_vector_layer"

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
    
    assigned_read_roles = []
    for key in request.POST:
        if 'read-usergroup-' in key:
            assigned_read_roles.append(key[len('read-usergroup-'):])

    assigned_write_roles = []
    for key in request.POST:
        if 'write-usergroup-' in key:
            assigned_write_roles.append(key[len('write-usergroup-'):])

    is_public = (request.POST.get('resource-is-public') is not None)

    try:
        maxFeatures = int(request.POST.get('max_features', 0))
    except:
        maxFeatures = 0

    form = CreateFeatureTypeForm(request.POST, request=request)
    if form.is_valid():
        try:
            _valid_name_regex=re.compile("^[a-zA-Z_][a-zA-Z0-9_]*$")
            datastore = form.cleaned_data['datastore']
            server = geographic_servers.get_instance().get_server_by_id(datastore.workspace.server.id)
            if _valid_name_regex.search(form.cleaned_data['name']) == None:
                msg = _("Invalid datastore name: '{value}'. Identifiers must begin with a letter or an underscore (_). Subsequent characters can be letters, underscores or numbers").format(value=form.cleaned_data['name'])
                form.add_error(None, msg)
            else:
                server.normalizeTableFields(form.cleaned_data['fields'])
                server.createTable(form.cleaned_data)
                extraParams = {}
                if datastore.type == 'v_PostGIS':
                    extraParams['maxFeatures'] = maxFeatures

                # first create the resource on the backend
                services_views.do_add_layer(server, datastore, form.cleaned_data['name'], form.cleaned_data['title'], is_queryable, extraParams)

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
                newRecord.time_enabled = False
                newRecord.layer_group.id = layer_group_id
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
                            raise HttpException(400, "Error creating trigger for calculated field")
                        
                featuretype = {
                    'max_features': maxFeatures
                }
                services_utils.set_layer_permissions(newRecord, is_public, assigned_read_roles, assigned_write_roles, [])
                services_views.do_config_layer(server, newRecord, featuretype)
                return newRecord.id
        except Exception as e:
            raise HttpException(400, "Error creating the layer: " + str(e))
    else:
        raise HttpException(400, "Error creating the layer. Form validation error: " + form.errors.as_text())


#--------------------------------------------------
#                  LayersView
#--------------------------------------------------
class LayersView(DestroyAPIView):
    serializer_class = FeatureSerializer
    def get_permissions(self):
        if self.request._request.method in ['GET', 'HEAD', 'OPTIONS']:
            return [ AllowAny() ]
        return [ IsAuthenticated() ]
    
    @swagger_auto_schema(operation_id='get_layer', operation_summary='Gets a specific layer from its ID',
                         responses={404: "Database connection NOT found<br>User NOT found<br>Layer NOT found", 
                                    403: "The layer is not allowed to this user"})
    @action(detail=True, methods=['GET'])
    def get(self, request, lyr_id):
        v = Validation(request)    
        try:
            v.check_get_layer(lyr_id)
        except HttpException as e:
            return e.get_exception()
        
        queryset = Layer.objects.select_related('datastore').get(id = lyr_id)
        queryset.connections = util.get_pool_connection(queryset)
        serializer = LayerSerializer(queryset, context={'request': request})
        result = {
            "content" : serializer.data,
            "links" : [
                {
                    "rel" : "self",
                    "href": request.get_full_path()
                } ,
                {
                    "rel" : "data",
                    "href": request.get_full_path() + "data/"
                } ,
                {
                    "rel" : "data",
                    "href": request.get_full_path() + "description/"
                } 
            ]
        }
        util.destroy_pool_connection(queryset.connections)
        return JsonResponse(result, safe=False)

    
    @swagger_auto_schema(operation_id='delete_layer', operation_summary='Delete a specific layer',
                         responses={404: "Database connection NOT found<br>User NOT found<br>Layer NOT found", 
                                    403: "The layer is not allowed to this user"})
    @action(detail=True, methods=['DELETE'])
    def delete(self, request, lyr_id):
        v = Validation(request)    
        try:
            v.check_get_layer(lyr_id)
        except HttpException as e:
            return e.get_exception()
        
        try:
            services_views.layer_delete(request, lyr_id)
        except Exception as e:
                raise HttpException(400, "Error deleting the layer")

        return JsonResponse({"result" : 'ok'}, safe=False)


#--------------------------------------------------
#                 LayersData
#--------------------------------------------------
class LayersData(ListAPIView):
    serializer_class = LayerSerializer
    
    @swagger_auto_schema(operation_id='get_layer_data', operation_summary='Gets the data of a layer',
                         responses={404: "Database connection NOT found<br>User NOT found<br>Layer NOT found", 
                                    403: "The layer is not allowed to this user"})
    @action(detail=True, methods=['GET'], permission_classes=[IsAuthenticated])
    def get(self, request, lyr_id):
        """
        This call gets a zip file which contains
        - A json file with the geometries
        - A json file with the symbology
        - A folder with linked resources
        - A folder with used symbols
        """
        v = Validation(request)    
        try:
            v.check_get_layer_data(lyr_id)
        except HttpException as e:
            return e.get_exception()
        
        layer = Layer.objects.get(id = int(lyr_id))
        if(layer.type == 'v_PostGIS'):
            workspace = layer.datastore.workspace
            i, table, schema = services_utils.get_db_connect_from_layer(lyr_id)
            with i as con: # connection will auoclose
                #bbox = layer.native_extent
                wkb_geometry = con.get_geometry_columns(table, schema=schema)[0]
                sql = "SELECT ST_EXTENT(wkb_geometry) FROM {schema}.{table}"
                query = sqlbuilder.SQL(sql).format(
                    wkb_geometry=sqlbuilder.Identifier(wkb_geometry),
                    schema=sqlbuilder.Identifier(schema),
                     table=sqlbuilder.Identifier(table)
                     )
                rows = con.custom_query(query)
            try: 
                bbox = rows[0][0]
                bbox = bbox.replace('BOX(', '')
                bbox = bbox.replace(')', '')
                bbox = bbox.replace(' ', ',')
            except Exception as e:
                return HttpException(404, "Data NOT exists for this layer").get_exception()

            exp = VectorLayerExporter()
            _, zip_path = exp.create_geojson_files(layer.name, workspace.name, bbox, None)
            response = HttpResponse(FileWrapper(open(zip_path, 'rb')), content_type='application/zip')
            values = zip_path.split("/")
            file_ = values[len(values) - 1]
            response['Content-Disposition'] = 'attachment; filename=' + file_
            response['Content-Type'] = 'application/zip'
            return response
        
        return HttpException(404, "Data NOT exists for this layer").get_exception()



#--------------------------------------------------
#                  LayersStyle
#--------------------------------------------------         
class LayersStyle(ListAPIView):
    permission_classes = [AllowAny]
    @swagger_auto_schema(operation_id='get_layer_style', operation_summary='Gets the style of the layer',
                         responses={400: "The layer is not in the user datastore",
                                    403: "The layer is not allowed to this user", 
                                    404: "Database connection NOT found<br>User NOT found<br>Layer NOT found"})
    @action(detail=True, methods=['GET'])
    def get(self, request, lyr_id):
        response = HttpResponse()
        response['Content-Type'] = 'text/xml; charset=utf-8'
        
        lyr = Layer.objects.get(id = lyr_id)
        try:
            workspace = lyr.datastore.workspace
        except Exception:
            return HttpException(400, "The layer is not in the user workspace").get_exception()
        
        gs = geographic_servers.get_instance().get_server_by_id(workspace.server.id)
        
        styles = StyleLayer.objects.filter(layer_id=lyr)
        if(styles is not None and len(styles) > 0):
            for style_layer in styles:
                if(style_layer.style.is_default):
                    style_sld = gs.getStyle(style_layer.style.name)
                    if style_sld is None:
                        return response
                    return HttpResponse(style_sld.sld_body, content_type='application/xml') 
        
        return response        


class LayersSymbStyle(ListAPIView):
    serializer_class = StyleSerializer
    permission_classes = [AllowAny]
    @swagger_auto_schema(operation_id='get_layer_symb_style', operation_summary='Gets the list of styles of the layer',
                         responses={400: "The layer is not in the user datastore",
                                    403: "The layer is not allowed to this user", 
                                    404: "Layer NOT found"})
    @action(detail=True, methods=['GET'])
    def get(self, request, lyr_id):
        v = Validation(request)    
        try:
            v.check_get_layer(lyr_id)
        except HttpException as e:
            return e.get_exception()

        
        sty = Style.objects.filter(stylelayer__layer_id=lyr_id)
        
        result = StyleSerializer(sty, many=True)
        
        return JsonResponse(result.data, safe=False)  
    
#--------------------------------------------------
#               LayerDescription
#--------------------------------------------------
class LayerDescription(ListAPIView): 
    serializer_class = FeatureSerializer
    filter_backends = (LangFilter,)

    @swagger_auto_schema(operation_id='get_layer_description', operation_summary='Gets the structure of the fields of a layer',
                         responses={404: "Database connection NOT found<br>User NOT found<br>Layer NOT found", 
                                    403: "The layer is not allowed to this user"})
    @action(detail=True, methods=['GET'], permission_classes=[IsAuthenticated])
    def get(self, request, lyr_id):
        v = Validation(request)    
        try:
            v.check_get_layer_description(lyr_id)
        except HttpException as e:
            return e.get_exception()

        lang = 'es'
        if 'lang' in self.request.GET:
            try:
                lang = self.request.GET['lang']
            except Exception:
                raise HttpException(400, "Bad parameter lang")
        
        layer = Layer.objects.get(id = lyr_id)
        fields = None
        try:
            conf = ast.literal_eval(layer.conf)
            fields = conf.get('fields', [])
            form_groups = conf.get('form_groups', [])
        except Exception:
            pass
        result = serviceviews.describe_feature_type(layer.name, layer.datastore.workspace.name)
        i, table, schema = services_utils.get_db_connect_from_layer(layer)
        with i as con: # connection will auoclose
            pks = con.get_pk_columns(table, schema=schema)
        for i in result['fields']:
            #Se añade el check de "Obligatorio" de los campos de una capa
            if fields is not None:
                for field in fields:
                    if field['name'] == i['name']:
                        try:
                            i['mandatory'] = field['mandatory']
                        except Exception:
                            i['mandatory'] = False

            #Se añade si el campo es PK o no
            if pks is not None and len(pks) > 0:
                for pk in pks:
                    if i['name'] == pk:
                        i['pk'] = 'YES'
                        break
                    else:
                        i['pk'] = 'NO'
            
            #Se añade la lista de valores que puede tomar el campo si este es enumerado
            if i['type'].endswith('enumeration'):
                items = services_utils.get_enum_item_list(layer, i['name'])
                list_ = []
                for j in items:
                    list_.append(j.name)
                i['values'] = list_

            i['translate'] = self.translate(layer.conf, i['name'], lang)
                
        result = {
            "content" : result['fields'],
            "links" : [
                {
                    "rel" : "self",
                    "href": request.get_full_path()
                } 
            ]
        }
        return JsonResponse(result, safe=False)


    def translate(self, conf, fieldName, lang):
        try:
            result = fieldName
            conf = ast.literal_eval(conf)
            for j in conf['fields']:
                if fieldName == j['name']:
                    try:
                        result = j['title-' + lang]
                        break
                    except Exception:
                        result = fieldName
            return result
        except Exception:
            return result


#--------------------------------------------------
#              LayerCapabilities
#--------------------------------------------------
class LayerCapabilities(ListAPIView):
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(operation_id='get_layer_capabilities', operation_summary='Gets capabilities of a layer',
                         responses={404: "Database connection NOT found<br>User NOT found<br>Layer NOT found", 
                                    403: "The layer is not allowed to this user"})
    @action(detail=True, methods=['GET'])
    def get(self, request, lyr_id):
        layer = Layer.objects.get(id = int(lyr_id))
        if layer.external:
            external_params = json.loads(layer.external_params)
            result = {
                "content" : external_params['capabilities'],
                "links" : [
                    {
                        "rel" : "self",
                        "href": request.get_full_path()
                    }
                ]
            }
            return JsonResponse(result, safe=False)
        
        return HttpException(404, "Data NOT exists for this layer").get_exception()


@swagger_auto_schema(operation_id='refresh_layer',
                    operation_summary='Refresh layer extent and thumbnail',
                    method='PUT',
                    responses={
                        200: 'Layer refresh has been scheduled',
                        404: "Layer NOT found", 
                        403: "The layer is not allowed to this user",
                        401: "The user is not authenticated"
                    })
@api_view(['PUT'])
@permission_classes([IsAdminUser])
def layer_refresh(request, lyr_id):
    try:
        layer = Layer.objects.get(pk=lyr_id)
    except Layer.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    if request.method == 'PUT':
        if not services_utils.can_write_layer(request, layer) and not services_utils.can_manage_layer(request, layer):
            return Response(status=status.HTTP_403_FORBIDDEN)
        refresh_layer_info.apply_async(args=[layer.id])
        return Response({'status': 'Layer refresh has been scheduled for execution'})
