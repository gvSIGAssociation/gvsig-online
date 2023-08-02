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
import json
import os
from wsgiref.util import FileWrapper
import ast
import coreapi
from django.http.response import HttpResponse, JsonResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import BaseFilterBackend
from rest_framework.generics import ListAPIView, CreateAPIView, RetrieveDestroyAPIView, \
    ListCreateAPIView
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_jwt.authentication import JSONWebTokenAuthentication
from django.db.models import Q


from gvsigol import settings as core_settings
from django.contrib.auth.models import User
from gvsigol_core.models import Project, ProjectLayerGroup, Application
from gvsigol_plugin_projectapi import settings
from gvsigol_plugin_baseapi.validation import Validation, HttpException
from gvsigol_services import geographic_servers
from gvsigol_services import utils as servicesutils
from gvsigol_services import views as serviceviews
from gvsigol_services.models import Layer, LayerGroup, Datastore, Workspace, \
    LayerResource
from gvsigol_symbology.models import StyleLayer
from .infoserializer import InfoSerializer, PublicInfoSerializer, AppInfoSerializer
import gvsigol_plugin_projectapi.serializers
import gvsigol_plugin_projectapi.util as util
from os import path
from django.utils import timezone
from gvsigol_services.backend_resources import resource_manager
from gvsigol_services import utils as services_utils
from psycopg2 import sql as sqlbuilder
from gvsigol_services import utils as services_utils

class CoordsFeatureFilter(BaseFilterBackend):
    def get_schema_fields(self, view):
        fields = [
            coreapi.Field(name="projectid", description="Id de proyecto. Si no está definido los trae todos", required=False, location='query', example='39'),
            coreapi.Field(name="mobile", description="true para descarga de proyectos móviles", required=False, location='query', example='true'),
            coreapi.Field(name="lang", description="Idioma para las traducciones de los campos. Default es", required=False, location='query', example='true'),
        ]
        return fields
          

class ProjectConfView(ListAPIView):
    serializer_class = InfoSerializer
    filter_backends = (CoordsFeatureFilter,)
    permission_classes = [AllowAny]
   
    #@swaggerdoc('test.yml')
    @swagger_auto_schema(operation_id='get_project_configuration', operation_summary='', 
                         responses={404: "Database connection NOT found<br>User NOT found",
                                    403: "The project is not allowed to this user"})
    @action(detail=True, methods=['GET'], permission_classes=[AllowAny])
    def get(self, request):
        v = Validation(request)   
        try:   
            projectid = 0
            if 'projectid' in self.request.GET:
                try:
                    projectid = int(self.request.GET['projectid'])
                except Exception:
                    raise HttpException(400, "Bad parameter project. The value must be a integer") 
            
            mobile = False
            if 'mobile' in self.request.GET:
                try:
                    mobile = bool(self.request.GET['mobile'])
                except Exception:
                    raise HttpException(400, "Bad parameter project. The value must be a boolean") 

            lang = 'es'
            if 'lang' in self.request.GET:
                try:
                    lang = self.request.GET['lang']
                except Exception:
                    raise HttpException(400, "Bad parameter lang.")

            try:
                v.check_get_project_list()
            except HttpException as e:
                return e.get_exception()
            
            
            now = datetime.now()

            queryset = None
            projects_by_user = util.get_projects_ids_by_user(request, mobile)
            if projectid != 0:
                if projectid in projects_by_user:
                    queryset = Project.objects.filter(id=projectid)
                else:
                    raise HttpException(403, "The project is not allowed to this user")  
            else:
                queryset = Project.objects.filter(id__in=projects_by_user)
            queryset = queryset.filter(Q(expiration_date__gte=now) | Q(expiration_date=None))
            serializer = InfoSerializer(queryset, many=True, context={'request': request, 'user': request.user.username, 'lang': lang})

            result = {
                "projects" : serializer.data,
            }
            return JsonResponse(result, safe=False)
        except HttpException as e:
            return e.get_exception()


class PublicProjectConfView(ListAPIView):
    serializer_class = PublicInfoSerializer
    permission_classes = [AllowAny]
    filter_backends = (CoordsFeatureFilter,)
   
    #@swaggerdoc('test.yml')
    @swagger_auto_schema(operation_id='get_public_project_configuration', operation_summary='', 
                         responses={404: "Database connection NOT found<br>User NOT found",
                                    403: "The project is not allowed to this user"})
    @action(detail=True, methods=['GET'])
    def get(self, request):  
        try:   
            projectid = 0
            if 'projectid' in self.request.GET:
                try:
                    projectid = int(self.request.GET['projectid'])
                except Exception:
                    raise HttpException(400, "Bad parameter project. The value must be a integer") 
            
            mobile = False
            if 'mobile' in self.request.GET:
                try:
                    mobile = bool(self.request.GET['mobile'])
                except Exception:
                    raise HttpException(400, "Bad parameter project. The value must be a boolean") 

            lang = 'es'
            if 'lang' in self.request.GET:
                try:
                    lang = self.request.GET['lang']
                except Exception:
                    raise HttpException(400, "Bad parameter lang.")
            now = datetime.now()

            queryset = Project.objects.filter(id=projectid, expiration_date__gte=now, is_public=True) | Project.objects.filter(id=projectid, expiration_date=None, is_public=True)

            serializer = PublicInfoSerializer(queryset, many=True, context={'lang': lang})

            result = {
                "projects" : serializer.data,
            }
            return JsonResponse(result, safe=False)
        except HttpException as e:
            return e.get_exception()
        
class ApplicationConfView(ListAPIView):
    serializer_class = AppInfoSerializer
    permission_classes = [AllowAny]
   
    #@swaggerdoc('test.yml')
    @swagger_auto_schema(operation_id='get_project_configuration', operation_summary='', 
                         responses={404: "Database connection NOT found<br>User NOT found",
                                    403: "The project is not allowed to this user"})
    @action(detail=True, methods=['GET'], permission_classes=[AllowAny])
    def get(self, request):
        v = Validation(request)   
        try:   
            applicationid = 0
            if 'applicationid' in self.request.GET:
                try:
                    applicationid = int(self.request.GET['applicationid'])
                except Exception:
                    raise HttpException(400, "Bad parameter project. The value must be a integer") 

            try:
                v.check_get_application_list()
            except HttpException as e:
                return e.get_exception()

            queryset = None
            applications_by_user = util.get_applications_ids_by_user(request, False)
            if applicationid != 0:
                if applicationid in applications_by_user:
                    queryset = Application.objects.filter(id=applicationid)
                else:
                    raise HttpException(403, "The application is not allowed to this user")  
            else:
                queryset = Application.objects.filter(id__in=applications_by_user)
            serializer = AppInfoSerializer(queryset, many=True, context={'request': request, 'user': request.user.username})

            result = {
                "applications" : serializer.data,
            }
            return JsonResponse(result, safe=False)
        except HttpException as e:
            return e.get_exception()
