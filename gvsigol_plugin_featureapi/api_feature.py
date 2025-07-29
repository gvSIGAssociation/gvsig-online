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


import os
from wsgiref.util import FileWrapper
import coreapi
from django.http.response import HttpResponse, JsonResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import BaseFilterBackend
from rest_framework.generics import ListAPIView, CreateAPIView, RetrieveDestroyAPIView, ListCreateAPIView
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from gvsigol import settings as core_settings
from gvsigol_plugin_featureapi import settings
from gvsigol_plugin_featureapi.models import FeatureVersions
from gvsigol_plugin_featureapi.serializers import FeatureSerializer, FeatureChangeSerializer, FileUploadSerializer
from gvsigol_plugin_baseapi.validation import Validation, HttpException
from gvsigol_services.models import Layer, LayerResource
from . import serializers
from . import util
from os import path
from django.utils import timezone
from gvsigol_services.backend_resources import resource_manager
from gvsigol_services import utils as services_utils
from django_sendfile import sendfile
import json
import logging

LOGGER_NAME='gvsigol'

class CoordsFeatureFilter(BaseFilterBackend):
    def get_schema_fields(self, view):
        fields = [
            coreapi.Field(name="lat", description="Latitude", required=True, location='query', example='39.469350'),
            coreapi.Field(name="lon", description="Longitude", required=True, location='query', example='-0.390024'),
            coreapi.Field(name="buffer", description="Diameter around the point in grades", required=True, location='query', example='0.01'),
            coreapi.Field(name="geom", description="true to get the geometry. Default false", required=False, location='query', example='true'),
            coreapi.Field(name="lang", description="Language (Ex: es, en, fr, val, etc). Default es", required=False, location='query', example='es'),
            coreapi.Field(name="blank", description="True to get a blank registry. Default false", required=False, location='query', example='false'),
            coreapi.Field(name="getbuffer", description="True to get the buffer geometry. Default false", required=False, location='query', example='false'),
        ]
        return fields

class BBoxFeatureFilter(BaseFilterBackend):
    def get_schema_fields(self, view):
        fields = [
            coreapi.Field(name="minlat", description="Latitude", required=True, location='query', example='39.469350'),
            coreapi.Field(name="minlon", description="Longitude", required=True, location='query', example='-0.390024'),
            coreapi.Field(name="maxlat", description="Latitude", required=True, location='query', example='39.469350'),
            coreapi.Field(name="maxlon", description="Longitude", required=True, location='query', example='-0.390024'),
            coreapi.Field(name="zip", description="true to get a zip file. Default false", required=False, location='query', example='true'),
            coreapi.Field(name="resources", description="true to get the attached resources. Default false", required=False, location='query', example='true'),
            coreapi.Field(name="epsg", description="if empty the request will use EPSG 4326 by default", required=False, location='query', example='4326'),
            coreapi.Field(name="max", description="Maximum number of elements to return", required=False, location='query', example='100'),
            coreapi.Field(name="page", description="Number of page", required=False, location='query', example='1'),
        ]
        return fields



class PaginationFeatureFilter(BaseFilterBackend):
    def get_schema_fields(self, view):
        fields = [
            coreapi.Field(name="max", description="Maximum number of elements to return", required=False, location='query', example='100'),
            coreapi.Field(name="page", description="Number of page", required=False, location='query', example='1'),
            coreapi.Field(name="date", description="Modification date", required=False, location='query', example='2020-01-13 14:54'),
            coreapi.Field(name="onlyprops", description="True to get only the properties", required=False, location='query', example='true'),
            coreapi.Field(name="text", description="Search by text", required=False, location='query', example='my text'),
        ]
        return fields


class DateFeatureFilter(BaseFilterBackend):
    def get_schema_fields(self, view):
        fields = [
            coreapi.Field(name="date", description="Modification date", required=False, location='query', example='2020-01-13 14:54'),
        ]
        return fields


class Pagination():
    def __init__(self, request):
        self.request = request
        self.max_ = settings.NUM_MAX_FEAT
        self.page = 0

    def get_pagination_params(self):
        
        if 'max' in self.request.GET:
            try:
                self.max_ = int(self.request.GET['max'])
            except Exception:
                raise HttpException(400, "Bad parameter max_feat. The value must be an integer")
            
        if 'page' in self.request.GET:
            try:
                self.page = int(self.request.GET['page'])
            except Exception:
                raise HttpException(400, "Bad parameter page. The value must be an integer")
            
        return self.max_, self.page
    
    def get_links(self, total):
        links = [
            {
                "rel" : "self",
                "href": self.request.build_absolute_uri()
            }
        ]
        path = self.request.build_absolute_uri()
        
        extent = '?'
        if 'minlat' in path:
            extent = path[path.rfind('?'):path.rfind('&max=')]

        path = path[:path.rfind('?')]
        
        path += extent
        if extent != '?':
            path += '&'
        
        if total > ((self.page + 1) * self.max_):
            links.append({
                "rel" : "next",
                "href": path + "max=" + str(self.max_) + "&page=" + str(self.page + 1)
            }) 
        if self.page > 0:
            links.append({
                "rel" : "prev",
                "href": path + "max=" + str(self.max_) + "&page=" + str(self.page - 1)
            }) 
        return links


#--------------------------------------------------
#                FeaturesView
#--------------------------------------------------
class FeaturesView(CreateAPIView):
    serializer_class = FeatureSerializer
    filter_backends = (PaginationFeatureFilter,)
    permission_classes = [AllowAny]
    pagination_class = None
    
    @swagger_auto_schema(operation_id='get_feature_list', operation_summary='Gets the feature list of a layer',
                         responses={404: "Database connection NOT found<br>User NOT found<br>Layer NOT found<br>Page NOT found", 
                                    403: "The layer is not allowed to this user", 
                                    400: "Features cannot be obtained. Unexpected error:..."})
    @action(detail=True, methods=['GET'])
    def get(self, request, lyr_id):
        """
        This call returns a Geojson with a FeatureCollection. The maximum number of features is 100 but you can define this
        value using the 'max' parameter. Moreover, you can get the features in pages selecting the number of page
        in the 'page' parameter .
        """
        pagination = Pagination(request)
        validation = Validation(request)
          
        try:
            date = util.get_param_date(request) 
            onlyprops = False
            if 'onlyprops' in self.request.GET:
                try:
                    onlyprops = True if self.request.GET['onlyprops'] == 'true' else False
                except Exception:
                    raise HttpException(400, "Bad parameter onlyprops. The value must be a value true or false")

            text = None
            if 'text' in self.request.GET:
                try:
                    text = self.request.GET['text']
                except Exception:
                    raise HttpException(400, "Bad parameter text. The value must be a string")

            strict_search = False
            if 'strictsearch' in self.request.GET:
                try:
                    strict_search =  True if self.request.GET['strictsearch'] == 'true' else False
                except Exception:
                    raise HttpException(400, "Bad parameter strictsearch. The value must be a value true or false")

            filter = None
            if 'filter' in self.request.GET:
                try:
                    filter = json.loads(self.request.GET['filter'])
                except Exception:
                    raise HttpException(400, "Bad parameter filter. The value must be a string")
                    
            restrictions = validation.check_read_restrictions(lyr_id)
            result = serializers.FeatureSerializer().list(validation, lyr_id, pagination, 4326, date, strict_search, onlyprops, text, filter, restrictions.get('cql_filter_read'))
            return JsonResponse(result, safe=False)
        except HttpException as e:
            return e.get_exception()
        
    
    
    @swagger_auto_schema(operation_id='create_feature', operation_summary='Creates a new feature in a layer',
                         responses={404: "Database connection NOT found<br>User NOT found<br>Layer NOT found", 
                                    403: "The layer is not allowed to this user<br>The user does not have permission to edit this layer",
                                    400: "Feature malformed. Geometry is not properly<br>Feature malformed. Fields geometry, type and properties are needed<br>Error checking version column:<br>Feature malformed. Wrong feature type<br>Feature malformed. Wrong coordinates"}) 
    @action(detail=True, methods=['POST'], permission_classes=[IsAuthenticated])
    def post(self, request, lyr_id):
        try:
            content = util.get_content(request)
            validation = Validation(request)
            validation.check_create_feature(lyr_id, content)
            username = request.user.username
            feat = serializers.FeatureSerializer().create(validation, lyr_id, content, username)
            return JsonResponse(feat, safe=False)
        except HttpException as e:
            return e.get_exception()
    
    
    @swagger_auto_schema(operation_id='update_feature', operation_summary='Updates a feature',
                         responses={404: "Database connection NOT found<br>User NOT found<br>Layer NOT found", 
                                    403: "The layer is not allowed to this user<br>The user does not have permission to edit this layer",
                                    400: "Feature malformed. Fields geometry, type and properties are needed<br>Error checking version column: <br>Feature malformed. Field properties is needed<br>Feature malformed. The field feat_version_gvol is needed for this call<br>Feature malformed. The field PK is needed for this call",
                                    409: "Version conflict"})
    @action(detail=True, methods=['PUT'], permission_classes=[IsAuthenticated])
    def put(self, request, lyr_id):
        try:
            content = util.get_content(request)
            validation = Validation(request)
            override = False
            version_to_overwrite = -1
            
            if 'conflicts' in content and 'data' in content:
                if content['conflicts'] == 'override':
                    override = True
                    try:
                        if 'version' in content:
                            version_to_overwrite = int(content['version'])
                    except Exception as e:
                        print(e)
                data = content['data']
                while isinstance(data, str):
                    data = json.loads(data)
            else:
                data = content
            
            validation.check_update_feature(lyr_id, data)
            username = request.user.username
            feat = serializers.FeatureSerializer().update(validation, lyr_id, data, override, version_to_overwrite, username)
            return JsonResponse(feat, safe=False)
        except HttpException as e:
            # Interceptar errores de topología para extraer GeoJSON
            if hasattr(e, 'msg') and 'TOPOLOGY ERROR' in str(e.msg):
                try:
                    import re
                    import json
                    error_msg = str(e.msg)
                    
                    # Extraer el mensaje desde después de los dos puntos hasta el primer punto
                    topology_pattern = r'TOPOLOGY ERROR: (.*?)\.'
                    topology_match = re.search(topology_pattern, error_msg)
                    topology_message = topology_match.group(1) if topology_match else 'Unknown topology violation'
                    
                    # Extraer GeoJSON entre ##
                    geojson_pattern = r'##(.*?)##'
                    geojson_match = re.search(geojson_pattern, error_msg)
                    if geojson_match:
                        geojson_str = geojson_match.group(1)
                        try:
                            geojson_obj = json.loads(geojson_str)
                            # Devolver error estructurado con GeoJSON
                            return JsonResponse({
                                'topology_error': topology_message,
                                'geometry': geojson_obj
                            }, status=400)
                        except json.JSONDecodeError:
                            # Si el GeoJSON no es válido, devolver error normal
                            pass
                except Exception:
                    # Si hay algún error procesando, devolver error normal
                    pass
            
            # Para errores no topológicos o si falla el procesamiento
            return e.get_exception()


#--------------------------------------------------
#              FeaturesExtentView
#--------------------------------------------------
class FeaturesExtentView(ListAPIView):
    serializer_class = FeatureSerializer
    filter_backends = (BBoxFeatureFilter,)
    pagination_class = None
    
    @swagger_auto_schema(operation_id='get_feature_list_by_extent', operation_summary='Gets the feature list of a layer',
                         responses={404: "Database connection NOT found<br>User NOT found<br>Layer NOT found<br>Page NOT found", 
                                    403: "The layer is not allowed to this user", 
                                    400: "Features cannot be obtained. Unexpected error:..."})
    @action(detail=True, methods=['GET'], permission_classes=[IsAuthenticated])
    def get(self, request, lyr_id):

        validation = Validation(request)
        pagination = Pagination(request)

        try:
            minlon = 0
            if 'minlon' in self.request.GET:
                try:
                    minlon = float(self.request.GET['minlon'])
                except Exception:
                    raise HttpException(400, "Bad parameter lon. The value must be a float")

            minlat = 0
            if 'minlat' in self.request.GET:
                try:
                    minlat = float(self.request.GET['minlat'])
                except Exception:
                    raise HttpException(400, "Bad parameter lat. The value must be a float")

            maxlon = 0
            if 'maxlon' in self.request.GET:
                try:
                    maxlon = float(self.request.GET['maxlon'])
                except Exception:
                    raise HttpException(400, "Bad parameter lon. The value must be a float")

            maxlat = 0
            if 'maxlat' in self.request.GET:
                try:
                    maxlat = float(self.request.GET['maxlat'])
                except Exception:
                    raise HttpException(400, "Bad parameter lat. The value must be a float")

            zip = False
            if 'zip' in self.request.GET:
                try:
                    zip = True if self.request.GET['zip'] == 'true' else False
                except Exception:
                    raise HttpException(400, "Bad parameter zip. The value must be a value true or false")

             
            resources = False
            if 'resources' in self.request.GET:
                try:
                    resources = True if self.request.GET['resources'] == 'true' else False
                except Exception:
                    raise HttpException(400, "Bad parameter resources. The value must be a value true or false")

            epsg = 4326
            if 'epsg' in self.request.GET:
                try:
                    epsg = int(self.request.GET['epsg'])
                except Exception:
                    raise HttpException(400, "Bad parameter epsg. The value must be an integer")

            max_feat = None
            if 'max' in self.request.GET:
                try:
                    max_feat = int(self.request.GET['max'])
                except Exception:
                    raise HttpException(400, "Bad parameter max. The value must be an integer")

            page = None
            if 'page' in self.request.GET:
                try:
                    page = int(self.request.GET['page'])
                except Exception:
                    raise HttpException(400, "Bad parameter page. The value must be an integer")


            validation.check_feature_list(lyr_id)
            result = serializers.FeatureSerializer().list_by_extent(validation, lyr_id, epsg, minlat, minlon, maxlat, maxlon, zip, resources, max_feat, page, pagination)
            
            if(zip):
                response = HttpResponse(FileWrapper(open(result, 'rb')), content_type='application/zip')
                values = result.split("/")
                file_ = values[len(values) - 1]
                response['Content-Disposition'] = 'attachment; filename=' + file_
                response['Content-Type'] = 'application/zip'
                return response
            else:
                return JsonResponse(result, safe=False)
        except HttpException as e:
            return e.get_exception()


#--------------------------------------------------
#                PublicFeaturesView
#--------------------------------------------------
class PublicFeaturesView(CreateAPIView):
    serializer_class = FeatureSerializer
    filter_backends = (PaginationFeatureFilter,)
    permission_classes = [AllowAny]
    pagination_class = None
    
    @swagger_auto_schema(operation_id='get_feature_list', operation_summary='Gets the feature list of a layer',
                         responses={404: "Database connection NOT found<br>User NOT found<br>Layer NOT found<br>Page NOT found", 
                                    403: "The layer is not allowed to this user", 
                                    400: "Features cannot be obtained. Unexpected error:..."})
    @action(detail=True, methods=['GET'])
    def get(self, request, lyr_id):
        """
        This call returns a Geojson with a FeatureCollection. The maximum number of features is 100 but you can define this
        value using the 'max' parameter. Moreover, you can get the features in pages selecting the number of page
        in the 'page' parameter .
        """
        validation = Validation(request)
        validation.is_public_layer(lyr_id)
        pagination = Pagination(request)
        try:
            date = util.get_param_date(request) 
            onlyprops = False
            if 'onlyprops' in self.request.GET:
                try:
                    onlyprops = True if self.request.GET['onlyprops'] == 'true' else False
                except Exception:
                    raise HttpException(400, "Bad parameter onlyprops. The value must be a value true or false")

            text = None
            if 'text' in self.request.GET:
                try:
                    text = self.request.GET['text']
                except Exception:
                    raise HttpException(400, "Bad parameter text. The value must be a string")

            strict_search = False
            if 'strictsearch' in self.request.GET:
                try:
                    strict_search =  True if self.request.GET['strictsearch'] == 'true' else False
                except Exception:
                    raise HttpException(400, "Bad parameter strictsearch. The value must be a value true or false")

            filter = None
            if 'filter' in self.request.GET:
                try:
                    filter = json.loads(self.request.GET['filter'])
                except Exception as e:
                    print(e)
                    raise HttpException(400, "Bad parameter filter. The value must be a string")

            result = serializers.FeatureSerializer().list(None, lyr_id, pagination, 4326, date, strict_search, onlyprops, text, filter)
            return JsonResponse(result, safe=False)
        except HttpException as e:
            return e.get_exception()
        
    
    
    @swagger_auto_schema(operation_id='create_feature', operation_summary='Creates a new feature in a layer',
                         responses={404: "Database connection NOT found<br>User NOT found<br>Layer NOT found", 
                                    403: "The layer is not allowed to this user<br>The user does not have permission to edit this layer",
                                    400: "Feature malformed. Geometry is not properly<br>Feature malformed. Fields geometry, type and properties are needed<br>Error checking version column:<br>Feature malformed. Wrong feature type<br>Feature malformed. Wrong coordinates"}) 
    @action(detail=True, methods=['POST'], permission_classes=[IsAuthenticated])
    def post(self, request, lyr_id):
        try:
            content = util.get_content(request)
            validation = Validation(request)
            validation.check_create_feature(lyr_id, content)
            feat = serializers.FeatureSerializer().create(validation, lyr_id, content, None)
            return JsonResponse(feat, safe=False)
        except HttpException as e:
            return e.get_exception()
    
    
    @swagger_auto_schema(operation_id='update_feature', operation_summary='Updates a feature',
                         responses={404: "Database connection NOT found<br>User NOT found<br>Layer NOT found", 
                                    403: "The layer is not allowed to this user<br>The user does not have permission to edit this layer",
                                    400: "Feature malformed. Fields geometry, type and properties are needed<br>Error checking version column: <br>Feature malformed. Field properties is needed<br>Feature malformed. The field feat_version_gvol is needed for this call<br>Feature malformed. The field PK is needed for this call",
                                    409: "Version conflict"})
    @action(detail=True, methods=['PUT'], permission_classes=[IsAuthenticated])
    def put(self, request, lyr_id):
        try:
            content = util.get_content(request)
            validation = Validation(request)
            override = False
            version_to_overwrite = -1
            
            if 'conflicts' in content and 'data' in content:
                if content['conflicts'] == 'override':
                    override = True
                    try:
                        if 'version' in content:
                            version_to_overwrite = int(content['version'])
                    except Exception as e:
                        print(e)
                data = content['data']
            else:
                data = content
            
            validation.check_update_feature(lyr_id, data)
            feat = serializers.FeatureSerializer().update(validation, lyr_id, data, override, version_to_overwrite, None)
            return JsonResponse(feat, safe=False)
        except HttpException as e:
            return e.get_exception()




#--------------------------------------------------
#                FeaturesDeleteView
#--------------------------------------------------
class FeaturesDeleteView(RetrieveDestroyAPIView):
    serializer_class = FeatureSerializer
    pagination_class = None
    def get_permissions(self):
        if self.request._request.method in ['GET', 'HEAD', 'OPTIONS']:
            return [ AllowAny() ]
        return [ IsAuthenticated() ]
        
    @swagger_auto_schema(operation_id='get_feature', operation_summary='Gets a feature from a layer',
                         responses={404: "Database connection NOT found<br>User NOT found<br>Layer NOT found<br>Feature NOT found", 
                                    403: "The layer is not allowed to this user"})
    @action(detail=True, methods=['GET'])
    def get(self, request, lyr_id, feat_id):
        validation = Validation(request)
        try:
            validation.check_get_feature(lyr_id, feat_id)
            feat = serializers.FeatureSerializer().get(validation, lyr_id, feat_id, 4326)
            result = {
                "content" : feat,
                "links" : [{
                    "rel" : "self",
                    "href": self.request.build_absolute_uri()
                },
                {
                    "rel" : "versions",
                    "href": self.request.build_absolute_uri() + "versions"
                }
                ]
            }
            return JsonResponse(result, safe=False)
        except HttpException as e:
            return e.get_exception() 
    
    @swagger_auto_schema(operation_id='delete_feature', operation_summary='Deletes a feature of a layer',
                         responses={204: "Happy end",
                                    404: "Database connection NOT found<br>User NOT found<br>Layer NOT found<br>Feature NOT found", 
                                    403: "The layer is not allowed to this user<br>The user does not have permission to edit this layer",
                                    409: "Version conflict"})
    @action(detail=True, methods=['DELETE'])
    def delete(self, request, lyr_id, feat_id):
        validation = Validation(request)
        try:
            version = None
            content = None
            try:
                content = util.get_content(request)
            except Exception as e:
                pass

            if content and 'version' in content:
                try:
                    version = int(content['version'])
                except Exception as e:
                    pass

            validation.check_delete_feature(lyr_id, feat_id)
            serializers.FeatureSerializer().delete(validation, lyr_id, feat_id, version)
            return HttpException(204, "OK").get_exception()
        except HttpException as e:
            return e.get_exception() 


#--------------------------------------------------
#                FeatureGetView
#--------------------------------------------------
class FeatureGetView(RetrieveDestroyAPIView):
    serializer_class = FeatureSerializer
    permission_classes = [AllowAny]
    pagination_class = None
        
    @swagger_auto_schema(operation_id='get_feature', operation_summary='Gets a feature from a layer',
                         responses={404: "Database connection NOT found<br>User NOT found<br>Layer NOT found<br>Feature NOT found", 
                                    403: "The layer is not allowed to this user"})
    @action(detail=True, methods=['GET'])
    def get(self, request, lyr_id, feat_id):
        validation = Validation(request)
        validation.check_get_feature(lyr_id, feat_id)
        try:
            feat = serializers.FeatureSerializer().get(None, lyr_id, feat_id, 4326)
            result = {
                "content" : feat,
                "links" : [{
                    "rel" : "self",
                    "href": self.request.build_absolute_uri()
                },
                {
                    "rel" : "versions",
                    "href": self.request.build_absolute_uri() + "versions"
                }
                ]
            }
            return JsonResponse(result, safe=False)
            
        except HttpException as e:
            return e.get_exception()                          


#--------------------------------------------------
#                FeatureVersionsView
#--------------------------------------------------
class FeatureVersionsView(ListAPIView):
    serializer_class = FeatureChangeSerializer
    pagination_class = None    

    @swagger_auto_schema(operation_id='get_feature_versions', operation_summary='Gets the list of versions of a feature',
                         responses={404: "Database connection NOT found<br>User NOT found<br>Layer NOT found<br>Feature NOT found", 
                                    403: "The layer is not allowed to this user"})
    @action(detail=True, methods=['GET'], permission_classes=[IsAuthenticated])
    def get(self, request, lyr_id, feat_id):
        validation = Validation(request)
        try:
            validation.check_get_feature(lyr_id, feat_id)
            feat_changes = FeatureVersions.objects.filter(feat_id = feat_id, layer_id=lyr_id)
            serializer = FeatureChangeSerializer(feat_changes, many=True)
        
            result = {
                "content" : serializer.data,
                "links" : [{
                    "rel" : "self",
                    "href": self.request.build_absolute_uri()
                }]
            }
            return JsonResponse(result, safe=False)
        except HttpException as e:
            return e.get_exception() 


#--------------------------------------------------
#             FeatureVersionsDeleted
#--------------------------------------------------  
class FeatureVersionsDeleted(ListAPIView):
    serializer_class = FeatureChangeSerializer
    filter_backends = (DateFeatureFilter,)   
    pagination_class = None 

    @swagger_auto_schema(operation_id='get_deleted_features', operation_summary='Gets the list of deleted features',
                         responses={404: "Database connection NOT found<br>User NOT found<br>Layer NOT found", 
                                    403: "The layer is not allowed to this user"})
    @action(detail=True, methods=['GET'], permission_classes=[IsAuthenticated])
    def get(self, request, lyr_id):
        validation = Validation(request)
        try:
            validation.check_get_layer_features(lyr_id)
            date_ = util.get_param_date(request)
            if date_ is None:
                feat_changes = FeatureVersions.objects.filter(layer_id=lyr_id, operation=3)
            else:
                feat_changes = FeatureVersions.objects.filter(layer_id=lyr_id, operation=3, date__gte=date_)
            serializer = FeatureChangeSerializer(feat_changes, many=True)
        
            result = {
                "content" : serializer.data,
                "links" : [{
                    "rel" : "self",
                    "href": self.request.build_absolute_uri()
                }]
            }
            return JsonResponse(result, safe=False)
        except HttpException as e:
            return e.get_exception() 


#--------------------------------------------------
#             FeatureVersionsCreated
#--------------------------------------------------
class FeatureVersionsCreated(ListAPIView):
    serializer_class = FeatureChangeSerializer
    filter_backends = (DateFeatureFilter,)   
    pagination_class = None 

    @swagger_auto_schema(operation_id='get_created_features', operation_summary='Gets the list of created features',
                         responses={404: "Database connection NOT found<br>User NOT found<br>Layer NOT found", 
                                    403: "The layer is not allowed to this user"})
    @action(detail=True, methods=['GET'], permission_classes=[IsAuthenticated])
    def get(self, request, lyr_id):
        validation = Validation(request)
        try:
            validation.check_get_layer_features(lyr_id)
            date_ = util.get_param_date(request)
            if date_ is None:
                feat_changes = FeatureVersions.objects.filter(layer_id=lyr_id, operation=1)
            else:
                feat_changes = FeatureVersions.objects.filter(layer_id=lyr_id, operation=1, date__gte=date_)
            serializer = FeatureChangeSerializer(feat_changes, many=True)
        
            result = {
                "content" : serializer.data,
                "links" : [{
                    "rel" : "self",
                    "href": self.request.build_absolute_uri()
                }]
            }
            return JsonResponse(result, safe=False)
        except HttpException as e:
            return e.get_exception()
        

#--------------------------------------------------
#             FeatureVersionsUpdated
#--------------------------------------------------
class FeatureVersionsUpdated(ListAPIView):
    serializer_class = FeatureChangeSerializer
    filter_backends = (DateFeatureFilter,) 
    pagination_class = None  

    @swagger_auto_schema(operation_id='get_updated_features', operation_summary='Gets the list of updated features',
                         responses={404: "Database connection NOT found<br>User NOT found<br>Layer NOT found", 
                                    403: "The layer is not allowed to this user"})
    @action(detail=True, methods=['GET'], permission_classes=[IsAuthenticated])
    def get(self, request, lyr_id):
        validation = Validation(request)
        try:
            validation.check_get_layer_features(lyr_id)
            date_ = util.get_param_date(request)
            if date_ is None:
                feat_changes = FeatureVersions.objects.filter(layer_id=lyr_id, operation=2)
            else:
                feat_changes = FeatureVersions.objects.filter(layer_id=lyr_id, operation=2, date__gte=date_)
            serializer = FeatureChangeSerializer(feat_changes, many=True)
        
            result = {
                "content" : serializer.data,
                "links" : [{
                    "rel" : "self",
                    "href": self.request.build_absolute_uri()
                }]
            }
            return JsonResponse(result, safe=False)
        except HttpException as e:
            return e.get_exception()
        

#--------------------------------------------------
#           FeatureVersionsAddedResources
#--------------------------------------------------
class FeatureVersionsAddedResources(ListAPIView):
    serializer_class = FeatureChangeSerializer
    filter_backends = (DateFeatureFilter,)    
    pagination_class = None

    @swagger_auto_schema(operation_id='get_added_resources', operation_summary='Gets the list of resources added in the layer',
                         responses={404: "Database connection NOT found<br>User NOT found<br>Layer NOT found", 
                                    403: "The layer is not allowed to this user"})
    @action(detail=True, methods=['GET'], permission_classes=[IsAuthenticated])
    def get(self, request, lyr_id):
        validation = Validation(request)
        try:
            validation.check_get_layer_features(lyr_id)
            date_ = util.get_param_date(request)
            if date_ is None:
                feat_changes = FeatureVersions.objects.filter(layer_id=lyr_id, operation=4)
            else:
                feat_changes = FeatureVersions.objects.filter(layer_id=lyr_id, operation=4, date__gte=date_)
            serializer = FeatureChangeSerializer(feat_changes, many=True)
        
            result = {
                "content" : serializer.data,
                "links" : [{
                    "rel" : "self",
                    "href": self.request.build_absolute_uri()
                }]
            }
            return JsonResponse(result, safe=False)
        except HttpException as e:
            return e.get_exception()
        

#--------------------------------------------------
#         FeatureVersionsDeletedResources
#--------------------------------------------------
class FeatureVersionsDeletedResources(ListAPIView):
    serializer_class = FeatureChangeSerializer
    filter_backends = (DateFeatureFilter,)
    pagination_class = None

    @swagger_auto_schema(operation_id='get_deleted_resources', operation_summary='Gets the list of resources deleted in the layer',
                         responses={404: "Database connection NOT found<br>User NOT found<br>Layer NOT found", 
                                    403: "The layer is not allowed to this user"})
    @action(detail=True, methods=['GET'], permission_classes=[IsAuthenticated])
    def get(self, request, lyr_id):
        validation = Validation(request)
        try:
            validation.check_get_layer_features(lyr_id)
            date_ = util.get_param_date(request)
            if date_ is None:
                feat_changes = FeatureVersions.objects.filter(layer_id=lyr_id, operation=5)
            else:
                feat_changes = FeatureVersions.objects.filter(layer_id=lyr_id, operation=5, date__gte=date_)
            serializer = FeatureChangeSerializer(feat_changes, many=True)
        
            result = {
                "content" : serializer.data,
                "links" : [{
                    "rel" : "self",
                    "href": self.request.build_absolute_uri()
                }]
            }
            return JsonResponse(result, safe=False)
        except HttpException as e:
            return e.get_exception()



#--------------------------------------------------
#                FeatureByPointView
#--------------------------------------------------
class FeatureByPointView(ListAPIView):
    serializer_class = FeatureSerializer
    filter_backends = (CoordsFeatureFilter,)
    permission_classes = [AllowAny]
    pagination_class = None
        
    @swagger_auto_schema(operation_id='get_feature_by_point', operation_summary='Gets a feature from a pair of coordinates',
                         responses={404: "Database connection NOT found<br>User NOT found<br>Layer NOT found<br>Feature NOT found", 
                                    403: "The layer is not allowed to this user",
                                    400: "Bad parameter lon. The value must be a float<br>Bad parameter lat. The value must be a float"})
    @action(detail=True, methods=['GET'], permission_classes=[AllowAny])
    def get(self, request, lyr_id):
        """
        Gets the features in the coordinates (lan, lon)
        - buffer: Diameter of the buffer in degrees. This buffer will be used to intersect the layer and get the features
        - lang: Language of feature labels (es, val, en, and so on). Default 'es'
        - geom: true to get the geometry. Default false
        - blank: true to get an empty registry
        """
        validation = Validation(request)
        try:
            restrictions = validation.check_read_restrictions(lyr_id)

            lon = 0
            if 'lon' in self.request.GET:
                try:
                    lon = float(self.request.GET['lon'])
                except Exception:
                    raise HttpException(400, "Bad parameter lon. The value must be a float")

            lat = 0
            if 'lat' in self.request.GET:
                try:
                    lat = float(self.request.GET['lat'])
                except Exception:
                    raise HttpException(400, "Bad parameter lat. The value must be a float")

            buffer = 0
            if 'buffer' in self.request.GET:
                try:
                    buffer = float(self.request.GET['buffer'])
                except Exception:
                    raise HttpException(400, "Bad parameter buffer. The value must be a float")

            geom = False
            if 'geom' in self.request.GET:
                try:
                    geom = True if self.request.GET['geom'] == 'true' else False
                except Exception:
                    raise HttpException(400, "Bad parameter geom. The value must be a value true or false")

            lang = 'es'
            if 'lang' in self.request.GET:
                try:
                    lang = self.request.GET['lang']
                except Exception:
                    raise HttpException(400, "Bad parameter lang")

            blank = False
            if 'blank' in self.request.GET:
                try:
                    blank = True if self.request.GET['blank'] == 'true' else False
                except Exception:
                    raise HttpException(400, "Bad parameter blank")
                
            simplify = True
            if 'simplify' in self.request.GET:
                try:
                    simplify = True if self.request.GET['simplify'] == 'true' else False
                except Exception:
                    raise HttpException(400, "Bad parameter simplify")
                
            source_epsg = 'EPSG:4326'
            if 'source_epsg' in self.request.GET:
                try:
                    source_epsg = int(self.request.GET['source_epsg'].split(":")[1])
                except Exception:
                    raise HttpException(400, "Bad parameter source_epsg")

            getbuffer = False
            if 'getbuffer' in self.request.GET:
                try:
                    getbuffer = True if self.request.GET['getbuffer'] == 'true' else False
                except Exception:
                    raise HttpException(400, "Bad parameter getbuffer.")

            lyr = Layer.objects.get(id=lyr_id)
            if lyr is None:
                raise HttpException(404, "Layer not found")

            serializer = FeatureSerializer()
            result = None
            if simplify:
                result = serializer.info_by_point(validation, lyr, lat, lon, 4326, buffer, geom, lang, blank, getbuffer, cql_filter_read=restrictions.get('cql_filter_read'))
            else:
                result = serializer.info_by_point_without_simplify(validation, lyr, lat, lon, source_epsg, buffer, geom, lang, blank, getbuffer, cql_filter_read=restrictions.get('cql_filter_read'))
            result['infoFormat'] = 'application/geojson'
            result['layerId'] = lyr.id
            result['layerTitle'] = lyr.title

            result['actions'] = [{
                'componentName': 'OpenDetails',
                'componentPath': 'common',
                'componentProps': {}
            },{
                'componentName': 'CopyCoordinate',
                'componentPath': 'common',
                'componentProps': {}
            }, {
                'componentName': 'OpenInGoogleMaps',
                'componentPath': 'common',
                'componentProps': {}
            }]

            result = {
                "content" : result,
                "links" : [{
                    "rel" : "self",
                    "href": self.request.build_absolute_uri()
                }]
            }
            
            return JsonResponse(result, safe=False)
        except HttpException as e:
            logging.getLogger(LOGGER_NAME).exception("Error getting features")
            return e.get_exception() 


#--------------------------------------------------
#            PublicFeatureByPointView
#--------------------------------------------------
class PublicFeatureByPointView(ListAPIView):
    serializer_class = FeatureSerializer
    permission_classes=[AllowAny]
    filter_backends = (CoordsFeatureFilter,)
    pagination_class = None
        
    @swagger_auto_schema(operation_id='get_public_feature_by_point', operation_summary='Gets a feature from a pair of coordinates',
                         responses={404: "Database connection NOT found<br>User NOT found<br>Layer NOT found<br>Feature NOT found", 
                                    403: "The layer is not allowed to this user",
                                    400: "Bad parameter lon. The value must be a float<br>Bad parameter lat. The value must be a float"})
    @action(detail=True, methods=['GET'])
    def get(self, request, lyr_id):
        """
        Gets the features in the coordinates (lan, lon)
        - buffer: Diameter of the buffer in degrees. This buffer will be used to intersect the layer and get the features
        - lang: Language of feature labels (es, val, en, and so on). Default 'es'
        - geom: true to get the geometry. Default false
        - blank: true to get an empty registry
        """
        try:
            lon = 0
            if 'lon' in self.request.GET:
                try:
                    lon = float(self.request.GET['lon'])
                except Exception:
                    raise HttpException(400, "Bad parameter lon. The value must be a float")

            lat = 0
            if 'lat' in self.request.GET:
                try:
                    lat = float(self.request.GET['lat'])
                except Exception:
                    raise HttpException(400, "Bad parameter lat. The value must be a float")

            buffer = 0
            if 'buffer' in self.request.GET:
                try:
                    buffer = float(self.request.GET['buffer'])
                except Exception:
                    raise HttpException(400, "Bad parameter buffer. The value must be a float")

            geom = False
            if 'geom' in self.request.GET:
                try:
                    geom = True if self.request.GET['geom'] == 'true' else False
                except Exception:
                    raise HttpException(400, "Bad parameter geom. The value must be a value true or false")

            lang = 'es'
            if 'lang' in self.request.GET:
                try:
                    lang = self.request.GET['lang']
                except Exception:
                    raise HttpException(400, "Bad parameter lang")

            blank = False
            if 'blank' in self.request.GET:
                try:
                    blank = True if self.request.GET['blank'] == 'true' else False
                except Exception:
                    raise HttpException(400, "Bad parameter blank")

            getbuffer = False
            if 'getbuffer' in self.request.GET:
                try:
                    getbuffer = True if self.request.GET['getbuffer'] == 'true' else False
                except Exception:
                    raise HttpException(400, "Bad parameter getbuffer.")

            lyr = Layer.objects.get(id=lyr_id)
            if lyr is None:
                raise HttpException(404, "Layer not found")
            if not lyr.public:
                raise HttpException(403, "The user does not have permission to read this layer")

            serializer = FeatureSerializer()
            result = serializer.info_by_point(None, lyr, lat, lon, 4326, buffer, geom, lang, blank, getbuffer)

            result = {
                "content" : result,
                "links" : [{
                    "rel" : "self",
                    "href": self.request.build_absolute_uri()
                }]
            }
            
            return JsonResponse(result, safe=False)
        except HttpException as e:
            return e.get_exception() 


#--------------------------------------------------
#            FileUploadView
#--------------------------------------------------
class FileUploadView(ListCreateAPIView):
    parser_classes = (MultiPartParser,)
    serializer_class = FileUploadSerializer
    pagination_class = None

    def get_permissions(self):
        if self.request._request.method in ['GET', 'HEAD', 'OPTIONS']:
            return [ AllowAny() ]
        return [ IsAuthenticated() ]
    
    @swagger_auto_schema(operation_id='get_list_attached_files', operation_summary='Get the list of resources attached to the feature',
                          responses={404: "Database connection NOT found<br>User NOT found<br>Layer NOT found", 
                                    403: "The layer is not allowed to this user"})
    @action(detail=True, methods=['GET'])
    def get(self, request, lyr_id, feat_id):
        v = Validation(request)    
        try:
            v.check_get_resource_list(lyr_id, feat_id)
        except HttpException as e:
            return e.get_exception()
        resourceset = LayerResource.objects.filter(layer_id=lyr_id, feature=feat_id)
        serializer = serializers.LayerResourceSerializer(resourceset, many=True)
        result = {
            "content" : serializer.data,
            "links" : [
                {
                    "rel" : "self",
                    "href": request.get_full_path()
                }
            ]
        }
        return JsonResponse(result, safe=False)
    
    @swagger_auto_schema(operation_id='uploaded_attached_file', operation_summary='Upload a resource attached to the feature',
                          responses={404: "Database connection NOT found<br>User NOT found<br>Layer NOT found<br>File already exists", 
                                     403: "The layer is not allowed to this user<br>The user does not have permission to edit this layer",
                                     400: "Error in the input parameters. Image and title cannot be null<br>Error checking version column<br>Error saving the resource"})
    @action(detail=True, methods=['POST'])
    def post(self, request, lyr_id, feat_id):
        try:
            v = Validation(request)
            try:
                lyr = Layer.objects.get(id=lyr_id)
            except Exception as e:
                raise HttpException(400, "Layer NOT found")

            v.check_uploaded_image(request, lyr_id, feat_id)
            i, table, schema = services_utils.get_db_connect_from_layer(lyr_id)
            with i as con: # connection will auoclose
                table_info = con.get_table_info(table, schema=schema)
                use_versions = v.check_version_and_date_columns(lyr_id, con, schema, table, table_info)
                
                up_file = request.FILES['image']
                
                res_type = services_utils.get_resource_type(up_file.content_type)
                saved, rel_path = resource_manager.save_resource(up_file, lyr_id, res_type)
                if not saved:
                    raise HttpException(400, "Error saving resource")
                resource = LayerResource()
                resource.type = res_type
                resource.feature = feat_id
                resource.path = rel_path
                resource.title = request.POST['title']
                resource.created = timezone.now()
                resource.layer = lyr
                resource.save()
                url = os.path.join(core_settings.MEDIA_URL, rel_path)
                if use_versions:
                    util.update_feat_version(con, schema, table, feat_id)
                    util.save_version_history(con, schema, table, lyr_id, feat_id, v.usr, 4, url)
                external_url =  core_settings.BASE_URL + resource.get_url()
            return Response({'id': resource.id, 'title':request.POST['title'], 'image' : external_url}, status.HTTP_201_CREATED)
        except HttpException as e:
            return e.get_exception()


#--------------------------------------------------
#            ResourcesView
#--------------------------------------------------
class ResourcesView(ListCreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = serializers.LayerResourceSerializer
    pagination_class = None

    @swagger_auto_schema(operation_id='get_list_attached_files', operation_summary='Get the list of resources attached to the feature',
                          responses={404: "Database connection NOT found<br>User NOT found<br>Layer NOT found", 
                                    403: "The layer is not allowed to this user"})
    @action(detail=True, methods=['GET'])
    def get(self, request, lyr_id, feat_id):
        v = Validation(request)
        v.check_read_feature_permission(lyr_id, feat_id)
        resourceset = LayerResource.objects.filter(layer_id=lyr_id, feature=feat_id)
        serializer = serializers.LayerResourceSerializer(resourceset, many=True)
        result = {
            "content" : serializer.data,
            "links" : [
                {
                    "rel" : "self",
                    "href": request.get_full_path()
                }
            ]
        }
        return JsonResponse(result, safe=False)


#--------------------------------------------------
#            FileAttachedView
#-------------------------------------------------- 
class FileAttachedView(ListAPIView):
    parser_classes = (MultiPartParser,)
    serializer_class = FileUploadSerializer
    permission_classes = [AllowAny]
    pagination_class = None
    
    @swagger_auto_schema(operation_id='get_attached_file', operation_summary='Get the resource attached to the feature',
                          responses={
                                    400: "The layer does not have this resource.<br>Resource NOT found",
                                    404: "Database connection NOT found<br>User NOT found<br>Layer NOT found", 
                                    403: "The layer is not allowed to this user"})
    @action(detail=True, methods=['GET'], permission_classes=[IsAuthenticated])
    def get(self, request, resource_id):
        validation = Validation(request)
    
        try:
            lyr_resource = LayerResource.objects.get(id=resource_id)
            try:
                validation.check_read_feature_permission(lyr_resource.layer, lyr_resource.feature)
            except HttpException as e:
                return e.get_exception()
        except Exception as e:
            return HttpException(404, "Resource NOT found in database").get_exception()
        if(lyr_resource is None):
            return HttpException(404, "Resource NOT found in database").get_exception()
        resource_path = lyr_resource.path
        
        if not os.path.isabs(resource_path):
            resource_path = os.path.join(core_settings.MEDIA_ROOT, lyr_resource.path)
        if(path.exists(resource_path)):
            return sendfile(request, resource_path, attachment=False)
        return HttpException(404, "Resource NOT found in disk").get_exception()


#--------------------------------------------------
#            FileDeleteView
#--------------------------------------------------
class FileDeleteView(RetrieveDestroyAPIView):
    parser_classes = (MultiPartParser,)
    serializer_class = FileUploadSerializer
    permission_classes = [AllowAny]
    pagination_class = None
    
    @swagger_auto_schema(operation_id='get_attached_file_legacy', operation_summary='Get the resource attached to the feature',
                          responses={
                                    400: "The layer does not have this resource.<br>Resource NOT found",
                                    404: "Database connection NOT found<br>User NOT found<br>Layer NOT found", 
                                    403: "The layer is not allowed to this user"})
    @action(detail=True, methods=['GET'], permission_classes=[])
    def get(self, request, lyr_id, feat_id, resource_id):
        validation = Validation(request)
        try:
            validation.check_read_feature_permission(self, lyr_id, feat_id)
        except HttpException as e:
            return e.get_exception()
        try:
            lyr_resource = LayerResource.objects.get(id=resource_id)
        except Exception as e:
            return HttpException(404, "Resource NOT found in database").get_exception()
        if(lyr_resource is None):
            return HttpException(404, "Resource NOT found in database").get_exception()
        resource_path = lyr_resource.path
        
        if not os.path.isabs(resource_path):
            resource_path = os.path.join(core_settings.MEDIA_ROOT, lyr_resource.path)
        if(path.exists(resource_path)):
            return sendfile(request, resource_path, attachment=False)
        return HttpException(404, "Resource NOT found in disk").get_exception()
    
    @swagger_auto_schema(operation_id='delete_attached_file', operation_summary='Deletes an attached resource of a feature',
                         responses={204: "Happy end",
                                    400: "The layer does not have this resource.<br>Resource NOT found",
                                    404: "Database connection NOT found<br>User NOT found<br>Layer NOT found<br>Feature NOT found", 
                                    403: "The layer is not allowed to this user<br>The user does not have permission to edit this layer"})
    @action(detail=True, methods=['DELETE'], permission_classes=[IsAuthenticated])
    def delete(self, request, lyr_id, feat_id, resource_id):
        validation = Validation(request)
        try:
            resource = LayerResource.objects.get(id=resource_id)
        except Exception as e:
            return HttpException(400, "Resource NOT found").get_exception()
        try:
            path = resource.path
            validation.check_delete_image(lyr_id, feat_id, resource)
            
            url_historical = resource_manager.store_historical(resource.path, resource.layer.id, resource.feature)
            resource.delete()
            if not LayerResource.objects.filter(path=path).exists():
                # only deleted if there are no cloned resources that share the same path
                if not os.path.isabs(path):
                    path = os.path.join(core_settings.MEDIA_ROOT, path)
                if os.path.isfile(path):
                    os.remove(path)
            con = None
            i, table, schema = services_utils.get_db_connect_from_layer(lyr_id)
            with i as con: # connection will autoclose
                util.update_feat_version(con, schema, table, feat_id)
                util.save_version_history(con, schema, table, lyr_id, feat_id, validation.usr, 5, url_historical)
            return HttpException(204, "OK").get_exception()
        except HttpException as e:
            return e.get_exception()    
        
#--------------------------------------------------
#            FileAttachedFromLinkView
#-------------------------------------------------- 
class FileAttachedFromLinkView(ListAPIView):
    parser_classes = (MultiPartParser,)
    serializer_class = FileUploadSerializer
    permission_classes = [AllowAny]
    pagination_class = None
    
    @swagger_auto_schema(operation_id='get_attached_file_from_link', operation_summary='Get the resource attached to the feature from a link',
                          responses={
                                    400: "The layer does not have this resource.<br>Resource NOT found",
                                    404: "Database connection NOT found<br>User NOT found<br>Layer NOT found", 
                                    403: "The layer is not allowed to this user"})
    @action(detail=True, methods=['GET'], permission_classes=[IsAuthenticated])
    def get(self, request, layer_id, feat_id, field_name):
        validation = Validation(request)
    
        try:
            layer = Layer.objects.get(id=layer_id)
            lyr_conf = layer.conf
            
            if isinstance(lyr_conf, str):
                import ast
                try:
                    lyr_conf = ast.literal_eval(lyr_conf)
                except:
                    lyr_conf = None
            
            try:
                validation.check_read_feature_permission(layer, feat_id)
            except HttpException as e:
                return e.get_exception()
        except Exception as e:
            return HttpException(404, "Layer not found or Resource not found in database").get_exception()
        
        field_config = None
        if lyr_conf and isinstance(lyr_conf, dict) and 'fields' in lyr_conf:
            for field in lyr_conf['fields']:
                if field.get('name') == field_name and field.get('gvsigol_type') == 'link':
                    field_config = field
                    break
        
        if not field_config:
            return HttpException(404, "Field not found or is not a link type").get_exception()
        
        type_params = field_config.get('type_params', {})
        base_folder = type_params.get('base_folder')
        related_field = type_params.get('related_field')
        
        if not base_folder or not related_field:
            return HttpException(400, "Missing base_folder or related_field in type_params").get_exception()
        
        try:
            feature = serializers.FeatureSerializer().get(validation, layer_id, feat_id, 4326)
            if not feature or 'properties' not in feature:
                return HttpException(404, "Feature not found").get_exception()
            
            filename = feature['properties'].get(related_field)
            if not filename:
                return HttpException(404, f"Field {related_field} not found or is empty in feature").get_exception()
            
            file_path = os.path.join(base_folder, filename)

            if not os.path.isabs(file_path):
                file_path = os.path.join(core_settings.MEDIA_ROOT, file_path)
            if(path.exists(file_path)):
                return sendfile(request, file_path, attachment=False)
            return HttpException(404, "File NOT found in disk").get_exception()
         
        except HttpException as e:
            return e.get_exception()
        except Exception as e:
            return HttpException(500, f"Error getting feature: {str(e)}").get_exception()