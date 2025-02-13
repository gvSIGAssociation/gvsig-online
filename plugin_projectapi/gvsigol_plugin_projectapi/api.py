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
from datetime import datetime
import datetime
import json
import os
from wsgiref.util import FileWrapper
import coreapi
from django.http.response import HttpResponse, JsonResponse
from django.utils.crypto import get_random_string
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import action
from rest_framework.filters import BaseFilterBackend
from rest_framework.generics import ListAPIView, CreateAPIView, RetrieveDestroyAPIView, ListCreateAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Q

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from gvsigol import settings as core_settings
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_control
from django.contrib.auth.models import User
from gvsigol_core import utils as core_utils
from gvsigol_core.models import Project, ProjectLayerGroup, Application, SharedView
from gvsigol_plugin_projectapi import settings
from gvsigol_plugin_projectapi.export import VectorLayerExporter
from gvsigol_plugin_projectapi.serializers import ProjectsSerializer, GsInstanceSerializer, ApplicationsSerializer
from gvsigol_plugin_featureapi.serializers import LayerSerializer
from gvsigol_plugin_baseapi.validation import Validation, HttpException
from gvsigol_services.models import Layer, LayerGroup, Server
from .serializers import ProjectSerializer, UserSerializer, SharedViewSerializer
from . import serializers
from . import util
from gvsigol.urls import urlpatterns
import psycopg2
from gvsigol_core.utils import get_user_projects

if core_settings.GVSIGOL_AUTH_BACKEND == 'gvsigol_plugin_oidc_mozilla':
    from gvsigol_plugin_oidc_mozilla.settings import OIDC_OP_BASE_URL, OIDC_OP_REALM_NAME, OIDC_RP_CLIENT_ID, \
        OIDC_MOBILE_CLIENT_ID, OIDC_OP_TOKEN_ENDPOINT, OIDC_OP_AUTHORIZATION_ENDPOINT, OIDC_OP_LOGOUT_ENDPOINT, \
        OIDC_OP_USER_ENDPOINT, OIDC_OP_JWKS_ENDPOINT

class DateFeatureFilter(BaseFilterBackend):
    def get_schema_fields(self, view):
        fields = [
            coreapi.Field(name="date", description="Modification date", required=False, location='query', example='2020-01-13 14:54'),
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

class LangFilter(BaseFilterBackend):
    def get_schema_fields(self, view):
        fields = [
            coreapi.Field(name="lang", description="Language (Ex: es, en, fr, val, etc). Default es", required=False, location='query', example='es'),
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

class Pagination():
    def __init__(self, request):
        self.request = request

    def get_pagination_params(self):
        self.max_ = settings.NUM_MAX_FEAT
        if 'max' in self.request.GET:
            try:
                self.max_ = int(self.request.GET['max'])
            except Exception:
                raise HttpException(400, "Bad parameter max_feat. The value must be an integer")
            
        self.page = 0
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
        path = path[:path.rfind('?')]
        
        if total > ((self.page + 1) * self.max_):
            links.append({
                "rel" : "next",
                "href": path + "?max=" + str(self.max_) + "&page=" + str(self.page + 1)
            }) 
        if self.page > 0:
            links.append({
                "rel" : "prev",
                "href": path + "?max=" + str(self.max_) + "&page=" + str(self.page - 1)
            }) 
        return links

#--------------------------------------------------
#                Platform
#--------------------------------------------------   
class PlatformView(ListAPIView):
    serializer_class = None
    permission_classes=[AllowAny]
    pagination_class = None

    #@swaggerdoc('test.yml')
    @swagger_auto_schema(operation_id='get_platform_info', operation_summary='Get information about the platform', 
                         responses={404: "Database connection NOT found<br>User NOT found"})
    @action(detail=True, methods=['GET'])
    def get(self, request):
        apps = core_settings.INSTALLED_APPS
        installed_apps = []
        for app in apps:
            if(not app.startswith("#")):
                installed_apps.append(app)

        api_calls = []
        #Se busca entre los módulos el del api rest y una vez encontrado se extraen las llamadas de este y se meten en un array
        for module in urlpatterns:
            if "gvsigol_plugin_projectapi" in str(module) or "gvsigol_plugin_featureapi" in str(module) or "gvsigol_plugin_layerpackaging" in str(module):#.urlconf_name):
                for pattern in module.url_patterns:
                    try:
                        if(pattern.name is not None):
                            if("," in pattern.name):
                                names = pattern.name.split(',')
                                for i in names:
                                    api_calls.append(i)
                            else:
                                api_calls.append(pattern.name)
                    except Exception as te:
                        pass
                        
        postres_plugins = []

        db = core_settings.DATABASES['default']
        
        dbhost = core_settings.DATABASES['default']['HOST']
        dbport = core_settings.DATABASES['default']['PORT']
        dbname = core_settings.DATABASES['default']['NAME']
        dbuser = core_settings.DATABASES['default']['USER']
        dbpassword = core_settings.DATABASES['default']['PASSWORD']
        
        try:
            connection = psycopg2.connect("host=" + dbhost +" port=" + dbport +" dbname=" + dbname +" user=" + dbuser +" password="+ dbpassword);
            connection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            sql = 'SELECT extname, extversion FROM pg_extension'
            cursor = connection.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            for row in rows:
                postres_plugins.append({'name' : row[0], 'version' : row[1]})
        except Exception as e:
            print("Failed to connect!", e)
        
        auth = {
            'type' : 'gvSIGOnline',
            'url' : core_settings.BASE_URL + "/" + core_settings.GVSIGOL_PATH + "/auth/api-token-auth/"
        }
        if core_settings.GVSIGOL_AUTH_BACKEND == 'gvsigol_plugin_oidc_mozilla':
            auth = {
                'type': 'OAuth',
                'url': OIDC_OP_BASE_URL,
                'oidc_rp_client_id': OIDC_RP_CLIENT_ID,
                'realm' : OIDC_OP_REALM_NAME,
                'mobile_client_id' : OIDC_MOBILE_CLIENT_ID,
                'auth_endpoint' : OIDC_OP_AUTHORIZATION_ENDPOINT,
                'token_endpoint' : OIDC_OP_TOKEN_ENDPOINT,
                'logout_endpoint' : OIDC_OP_LOGOUT_ENDPOINT,
                'user_endpoint' : OIDC_OP_USER_ENDPOINT,
                'jwk_endpoint' : OIDC_OP_JWKS_ENDPOINT
            }
        info = {
            'gvsigonline_version': core_settings.GVSIGOL_VERSION,
            'gvsigonline_plugins': installed_apps,
            'rest_api_calls': api_calls,
            'postgres_plugins' : postres_plugins,
            'authentication' : auth
        }
        result = {
            "content" : info,
            "links" : [
                {
                    "rel" : "self",
                    "href": request.get_full_path()
                }
            ]
        }
        return JsonResponse(result, safe=False)
        
#--------------------------------------------------
#                USERS
#--------------------------------------------------   
class UserView(ListAPIView):
    serializer_class = UserSerializer
    pagination_class = None
   
    #@swaggerdoc('test.yml')
    @swagger_auto_schema(operation_id='get_user', operation_summary='Get information about the user', 
                         responses={404: "Database connection NOT found<br>User NOT found"})
    @action(detail=True, methods=['GET'], permission_classes=[IsAuthenticated])
    def get(self, request):
        user = User.objects.get(id=request.user.id)
        serializer = UserSerializer(user)
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
#                GEOSERVER INSTANCES
#--------------------------------------------------   
class ServerView(ListAPIView):
    serializer_class = GsInstanceSerializer
    pagination_class = None
   
    #@swaggerdoc('test.yml')
    @swagger_auto_schema(operation_id='get_server', operation_summary='Get information about the user', 
                         responses={404: "Database connection NOT found<br>User NOT found"})
    @action(detail=True, methods=['GET'], permission_classes=[IsAuthenticated])
    def get(self, request):
        servers = Server.objects.all()
        servers = list(dict.fromkeys(servers))
        serializer = GsInstanceSerializer(servers, many=True)
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
#                PROJECTS
#--------------------------------------------------   

class ProjectListView(ListAPIView):
    serializer_class = ProjectsSerializer
    filter_backends = (ProjectFilter,)
    permission_classes = [AllowAny]
    pagination_class = None
   
    #@swaggerdoc('test.yml')
    @swagger_auto_schema(operation_id='get_project_list', operation_summary='Gets the list of projects', 
                         responses={404: "Database connection NOT found<br>User NOT found"})
    @action(detail=True, methods=['GET'], permission_classes=[AllowAny])
    def get(self, request):
        v = Validation(request)    
        try:
            v.check_get_project_list()
        except HttpException as e:
            return e.get_exception()

        try:
            label = self.request.GET.get('label')
        except Exception:
            raise HttpException(400, "Bad parameter lang")
        
        queryset = get_user_projects(request)
        if(label is not None): 
            queryset = queryset.filter(labels__contains=label)
        now = datetime.now()
        queryset = queryset.filter(Q(expiration_date__gte=now) | Q(expiration_date=None))

        serializer = ProjectsSerializer(queryset, many=True)
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
        

class ProjectView(ListAPIView):
    serializer_class = serializers.ProjectsSerializer
    pagination_class = None
        
    @swagger_auto_schema(operation_id='get_project', operation_summary='Gets a specific project using its ID', 
                         responses={404: "Database connection NOT found<br>User NOT found<br>Project NOT found", 
                                    403: "The project is not allowed to this user"})
    @action(detail=True, methods=['GET'], permission_classes=[IsAuthenticated])
    def get(self, request, project_id):
        v = Validation(request)    
        try:
            v.check_get_project(project_id)
        except HttpException as e:
            return e.get_exception()
        
        now = datetime.now()
        
        queryset = Project.objects.filter(id = project_id, expiration_date__gte=now) | Project.objects.filter(id = project_id, expiration_date=None)
        serializer = ProjectsSerializer(queryset, many=True)
        data = serializer.data
#         try:
#             extent = serializer.data['extent']  
#             if extent is not None:
#                 coords = extent.split(',')
#                 if len(coords) == 4:
#                     inProj = Proj(init='epsg:3857')
#                     outProj = Proj(init='epsg:4326')
#                     coords[0], coords[1] = transform(inProj,outProj, coords[0], coords[1])
#                     coords[2], coords[3] = transform(inProj,outProj, coords[2], coords[3])
#                     data['extent'] = str(coords[0]) + "," + str(coords[1]) + "," + str(coords[2]) + "," + str(coords[3])
#         except Exception:
#             #Si se produce una excepcion convirtiendo el extent lo devuelve en 3857 
#             #(que yo creo que mejor) y nos tragamos la excepcion
#             pass
        groupset = ProjectLayerGroup.objects.filter(project_id = project_id)
        res = None
        if len(data) > 0:
            data[0]['baselayerid'] = None
            for i in groupset:
                if(i.default_baselayer is not None):
                    data[0]['baselayerid'] = i.default_baselayer
            res = data[0]
                        
        result = {
            "content" : res,
            "links" : [
                {
                    "rel" : "self",
                    "href": request.get_full_path()
                } ,
                {
                    "rel" : "layers",
                    "href": request.get_full_path() + "layers/"
                } , 
                {
                    "rel" : "groups",
                    "href": request.get_full_path() + "groups/"
                }
            ]
        }
        return JsonResponse(result, safe=False) 




class PublicProjectListView(ListAPIView):
    serializer_class = ProjectsSerializer
    permission_classes = [AllowAny]
    filter_backends = (ProjectFilter,)
    pagination_class = None
   
    @swagger_auto_schema(operation_id='get_public_project_list', operation_summary='Gets the list of projects', 
                         responses={404: "Database connection NOT found<br>User NOT found"})
    @action(detail=True, methods=['GET'])
    def get(self, request):
        now = datetime.now()

        label = None
        if 'label' in self.request.GET:
            try:
                label = self.request.GET['label']
            except Exception:
                raise HttpException(400, "Bad parameter lang")

        if label is not None:
            queryset = Project.objects.filter(is_public=True, labels__contains=label, expiration_date__gte=now) | Project.objects.filter(is_public=True, labels__contains=label, expiration_date=None)
        else:
            queryset = Project.objects.filter(is_public=True, expiration_date__gte=now) | Project.objects.filter(is_public=True, expiration_date=None)
            
        serializer = ProjectsSerializer(queryset, many=True)
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
    
    
class ProjectLayersView(ListAPIView):
    serializer_class = LayerSerializer
    pagination_class = None
    
    @swagger_auto_schema(operation_id='get_layers_from_project', operation_summary='Gets the list of layers in a specific project',
                         responses={404: "Database connection NOT found<br>User NOT found<br>Project NOT found", 
                                    403: "The project is not allowed to this user"})
    @action(detail=True, methods=['GET'], permission_classes=[IsAuthenticated])
    def get(self, request, project_id):
        v = Validation(request)    
        try:
            v.check_get_project_layers(project_id)
        except HttpException as e:
            return e.get_exception()
        
        base_layer_id = None
        try:
            base_group = ProjectLayerGroup.objects.get(project_id = project_id, baselayer_group=True)
            base_layer_id = base_group.default_baselayer
        except Exception:
            pass #No hay capa base
        queryset = util.get_layerread_by_user_and_project(request, project_id)

        queryset.connections = util.get_pool_connection(queryset)
        serializer = LayerSerializer(queryset, many=True, context={'request': request, 'user': request.user.username})
        result = {
            "content" : serializer.data,
            "baselayerid" : base_layer_id,
            "links" : [
                {
                    "rel" : "self",
                    "href": request.get_full_path()
                }
            ]
        }
        util.destroy_pool_connection(queryset.connections)
        return JsonResponse(result, safe=False) 
    
    
class ProjectGroupsView(ListAPIView):
    serializer_class = serializers.LayerGroupSerializer
    pagination_class = None
    
    @swagger_auto_schema(operation_id='get_groups_from_project', operation_summary='Gets the list of groups in a specific project',
                         responses={404: "Database connection NOT found<br>User NOT found<br>Project NOT found", 
                                    403: "The project is not allowed to this user"})
    @action(detail=True, methods=['GET'], permission_classes=[IsAuthenticated])
    def get(self, request, project_id):
        v = Validation(request)    
        try:
            v.check_get_project_groups(project_id)
        except HttpException as e:
            return e.get_exception()
        
        resultset = util.get_layergroups_by_user_and_project(request, project_id)
        serializer = serializers.LayerGroupSerializer(resultset, many=True)
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
#                LAYERS
#--------------------------------------------------
    
      



def get_content(request):
    try:
        if(request.body != ''):
            body_unicode = request.body.decode('utf-8')
            return json.loads(body_unicode)
    except Exception as e:
        raise HttpException(400, "Feature malformed." + format(e))

 
class ProjectBaseLayerData(ListAPIView):
    serializer_class = LayerSerializer
    pagination_class = None
    
    @swagger_auto_schema(operation_id='get_base_layer_data', operation_summary='Gets the data of the base layer',
                         responses={404: "Database connection NOT found<br>User NOT found<br>Layer NOT found", 
                                    403: "The project is not allowed to this user"})
    @action(detail=True, methods=['GET'], permission_classes=[IsAuthenticated])
    def get(self, request, project_id):
        """
        This call gets a zip file which contains the base layer  
        """
        v = Validation(request)    
        try:
            v.check_get_project(project_id)
        except HttpException as e:
            return e.get_exception()
        
        base_layer_dir = VectorLayerExporter().get_layer_dir()
        if not os.path.exists(base_layer_dir):
            os.mkdir(base_layer_dir)
            return HttpException(404,  "The base layer required does not exists.").get_exception()
        
        prj = Project.objects.get(id=project_id)
        file_name = prj.name + '_prj_' + str(prj.baselayer_version) + '.zip'
        if not os.path.isfile(base_layer_dir + "/" + file_name):
            return HttpException(404, "Data NOT exists for this project").get_exception()
        
        zip_ = os.path.join(base_layer_dir, file_name)
        
        response = HttpResponse(FileWrapper(open(zip_,'rb')), content_type = 'application/zip')
        response['Content-Disposition'] = 'attachment; filename=' + file_name.replace(" ","_")
        
        return response
                
 
     
#--------------------------------------------------
#                GROUPS
#--------------------------------------------------   

 
class LayerGroupsListView(ListAPIView):
    serializer_class = serializers.LayerGroupSerializer
    pagination_class = None
    
    @swagger_auto_schema(operation_id='get_group_list', operation_summary='Gets the list of groups in the application',
                         responses={404: "Database connection NOT found<br>User NOT found"})
    @action(detail=True, methods=['GET'], permission_classes=[IsAuthenticated])
    def get(self, request):
        v = Validation(request)    
        try:
            v.check_get_group_list()
        except HttpException as e:
            return e.get_exception()
        
        queryset = util.get_layergroups_by_user(request)
        serializer = serializers.LayerGroupSerializer(queryset, many=True)
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
    
 
class LayerGroupView(ListAPIView):
    serializer_class = serializers.LayerGroupSerializer
    pagination_class = None
    
    @swagger_auto_schema(operation_id='get_group', operation_summary='Gets a specific group from its ID',
                         responses={404: "Database connection NOT found<br>User NOT found<br>Group NOT found", 
                                    403: "The group is not allowed to this user"})
    @action(detail=True, methods=['GET'], permission_classes=[IsAuthenticated])
    def get(self, request, group_id):
        v = Validation(request)    
        try:
            v.check_get_group(group_id)
        except HttpException as e:
            return e.get_exception()
        
        queryset = LayerGroup.objects.get(id = group_id)
        serializer = serializers.LayerGroupSerializer(queryset)
        result = {
            "content" : serializer.data,
            "links" : [
                {
                    "rel" : "self",
                    "href": request.get_full_path()
                } ,
                {
                    "rel" : "layers",
                    "href": request.get_full_path() + "layers/"
                } 
            ]
        }
        return JsonResponse(result, safe=False)
                  
class LayerGroupLayersView(ListAPIView):
    serializer_class = LayerSerializer
    pagination_class = None
    
    @swagger_auto_schema(operation_id='get_layers_from_group', operation_summary='Gets the list of layers of a specific group',
                         responses={404: "Database connection NOT found<br>User NOT found<br>Group NOT found", 
                                    403: "The group is not allowed to this user"})
    @action(detail=True, methods=['GET'], permission_classes=[IsAuthenticated])
    def get(self, request, group_id):
        v = Validation(request)    
        try:
            v.check_get_layers_by_group(group_id)
        except HttpException as e:
            return e.get_exception()
        
        #group = LayerGroup.objects.get(id = group_id)
        #queryset = Layer.objects.filter(layer_group_id=group.id).select_related('datastore')
        queryset = util.get_layerread_by_user_and_group(request, group_id)
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
       

def get_param_date(request):
        try:
            if 'date' in request.GET:
                datestr = request.GET['date']
                if(datestr is not None):
                    return datetime.strptime(datestr, '%d/%m/%Y %H:%M')
        except Exception:
            raise HttpException(400, "Bad parameter date. The format must be d/m/Y H:M")


class GeoserverAPIKey(ListAPIView):
    serializer_class = None 
    pagination_class = None

    @swagger_auto_schema(operation_id='get_geoserver_api_key', operation_summary='Gets the geoserver API Key',
                         responses={404: "User NOT found", 401: "API Key file not exists"})
    @action(detail=True, methods=['GET'], permission_classes=[IsAuthenticated])
    def get(self, request):
        validation = Validation(request)
        try:
            validation.user_exists()
            try:
                file1 = open(settings.GEOSERVER_API_KEY_FILE, 'r')
            except IOError:
                return HttpException(400, "API Key file not exists").get_exception()

            lines = file1.readlines()
            key = None
            for line in lines:
                line = line.strip()
                if not line.startswith('#'):
                    userkey = line.split('=')
                    if len(userkey) == 2:
                        if(request.user.username == userkey[1]):
                            key = userkey[0]
                            break
        
            if key is None:
                return HttpException(400, "User NOT found").get_exception()

            result = {
                "content" : {"geoserver_key":key},
                "links" : [{
                    "rel" : "self",
                    "href": self.request.build_absolute_uri()
                }]
            }
            return JsonResponse(result, safe=False)
        except HttpException as e:
            return e.get_exception()
        
#--------------------------------------------------
#                APPLICATIONS
#--------------------------------------------------   

class ApplicationListView(ListAPIView):
    serializer_class = ProjectsSerializer
    permission_classes = [AllowAny]
    pagination_class = None
   
    #@swaggerdoc('test.yml')
    @swagger_auto_schema(operation_id='get_application_list', operation_summary='Gets the list of applications', 
                         responses={404: "Database connection NOT found<br>User NOT found"})
    @action(detail=True, methods=['GET'], permission_classes=[AllowAny])
    def get(self, request):
        v = Validation(request)    
        try:
            v.check_get_application_list()
        except HttpException as e:
            return e.get_exception()
        
        applications_by_user = util.get_applications_ids_by_user(request)
        queryset = Application.objects.filter(id__in=applications_by_user)

        serializer = ApplicationsSerializer(queryset, many=True)
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
#                Shared View
#--------------------------------------------------   

class SharedViewManager:
    """
    Clase encargada de gestionar la creación y actualización de SharedView.
    """

    @staticmethod
    def save_shared_view(pid, description, view_state, expiration, user, internal=False, url=False):
        """
        Crea o actualiza una vista compartida.
        """
        if url:
            shared_url = url
            name = url.split('sharedView=')[-1]
        else:
            name = datetime.date.today().strftime("%Y%m%d") + get_random_string(length=32)
            shared_url = '/spa/viewer/'+pid +'?sharedView=' + name
            #shared_url = settings.BASE_URL + '/gvsigonline/core/load_shared_view/' + name

        try:
            # Se intenta obtener una vista compartida existente con el mismo nombre.
            shared_project = SharedView.objects.get(name=name)
            shared_project.expiration_date = expiration
        except SharedView.DoesNotExist:
            # Si no existe, se crea una nueva instancia.
            shared_project = SharedView(
                name=name,
                project_id=int(pid),
                description=description,
                url=shared_url,
                state=view_state,
                expiration_date=expiration,
                created_by=user.username,
                internal=internal
            )
        
        shared_project.save()
        return shared_project
    
class CreateSharedViewAPI(APIView):
    """
    API endpoint para crear una vista compartida.
    Devuelve un JSON con el shared_url generado.
    """
    def post(self, request, *args, **kwargs):
        pid = request.data.get('pid')
        name = datetime.date.today().strftime("%Y%m%d") + get_random_string(length=32)
        shared_url = '/spa/viewer/'+pid +'?sharedView=' + name
        return Response({'shared_url': shared_url}, status=status.HTTP_200_OK)

class SaveSharedViewAPI(APIView):
    """
    API endpoint para guardar una vista compartida.
    Procesa los datos recibidos por POST y devuelve el shared_url generado.
    """
    def post(self, request, *args, **kwargs):
        try:
            pid = request.data.get('pid')
        except (TypeError, ValueError):
            return Response({'result': 'illegal_operation', 'shared_url': ''}, status=status.HTTP_400_BAD_REQUEST)
        
        # Verificar permisos o si el usuario puede leer el proyecto
        # if not core_utils.can_read_project(request, pid):
        #    return Response({'result': 'illegal_operation', 'shared_url': ''}, status=status.HTTP_403_FORBIDDEN)
        
        description = request.data.get('description')
        view_state = request.data.get('view_state')
        
        if request.data.get('checked') == 'false':
            expiration_date = datetime.datetime.now() + datetime.timedelta(days=core_settings.SHARED_VIEW_EXPIRATION_TIME)
        else:
            expiration_date = datetime.datetime.max
        
        if request.data.get('shared_url'):
            shared_url = request.data.get('shared_url')
            SharedViewManager.save_shared_view(pid, description, view_state, expiration_date, request.user, False, shared_url)
        else:
            shared_view = SharedViewManager.save_shared_view(pid, description, view_state, expiration_date, request.user)
            shared_url = shared_view.shared_url
        
        return Response({'shared_url': shared_url}, status=status.HTTP_200_OK)
    
@method_decorator(cache_control(max_age=86400), name='dispatch')
class LoadSharedViewAPI(APIView):
    """
    API endpoint para cargar una vista compartida por nombre (view_name).
    """

    def get(self, request, view_name, *args, **kwargs):
        try:
            shared_view = get_object_or_404(SharedView, name=view_name)
        except SharedView.DoesNotExist:
            return Response({'error': 'Shared view not found'}, status=status.HTTP_404_NOT_FOUND)

        try:

            project = get_object_or_404(Project, id=shared_view.project_id)
        except Project.DoesNotExist:
            return Response({'error': 'Project not found'}, status=status.HTTP_404_NOT_FOUND)

        if shared_view.internal and not request.user.is_superuser:
            raise PermissionDenied("No tienes permiso para acceder a esta vista compartida.")

        if not (project.is_public or request.user.is_authenticated):
            return Response(
                {'error': 'El proyecto no es público y se requiere autenticación.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        shared_view_serializer = SharedViewSerializer(shared_view)

        response_data = {
            'shared_view': shared_view_serializer.data, 
            'project': {
                'id': project.id,
                'is_public': project.is_public,
                'logo_url': project.logo_url,
                'image_url': project.image_url,
                'viewer_default_crs': project.viewer_default_crs,
            },
            'plugins_config': core_utils.get_plugins_config(),
            'enabled_plugins': core_utils.get_enabled_plugins(project),
            'supported_crs': core_utils.get_supported_crs(),
            'extra_params': request.query_params.dict(), 
            'is_shared_view': True,
            'shared_view_name': shared_view.name,
            'main_page': settings.LOGOUT_REDIRECT_URL,
            'is_viewer_template': True,
        }

        response = Response(response_data, status=status.HTTP_200_OK)

        tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
        tomorrow = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
        expires = tomorrow.strftime("%a, %d-%b-%Y %H:%M:%S GMT")
        response.set_cookie('key', expires=expires)

        return response





