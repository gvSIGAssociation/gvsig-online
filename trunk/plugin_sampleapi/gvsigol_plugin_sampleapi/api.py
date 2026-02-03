# -*- coding: utf-8 -*-

'''
    gvSIG Online.
    Copyright (C) 2010-2024 SCOLAB.

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
@author: <jvhigon@scolab.es>
'''

import logging
from rest_framework import status
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from django.utils.decorators import method_decorator

from rest_framework import viewsets
from .models import Example
from .serializers import ExampleSerializer
from . import settings
from gvsigol_plugin_baseapi.permissions import IsSuperUser


@method_decorator(name='list', decorator=swagger_auto_schema(
    operation_id='example_list',
    operation_description="List all objects",
    responses={
        401: "Not authenticated",
        403: "Not allowed",
        405: "Method not allowed ..."
    }
))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(
    operation_id='example_read',
    operation_description="Read example details",
    responses={
        401: "Not authenticated",
        403: "Not allowed",
        404: "Example id not found",
        405: "Method not allowed ..."
    }
))
@method_decorator(name='destroy', decorator=swagger_auto_schema(
    operation_id='example_delete',
    operation_description="Delete example",
    responses={
        401: "Not authenticated",
        403: "Not allowed",
        404: "Example id not found",
        405: "Method not allowed ..."
    }
))
class ExampleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for example object
    """
    permission_classes = (IsSuperUser,)
    queryset = Example.objects.all()
    serializer_class = ExampleSerializer

    @swagger_auto_schema(operation_id='example_create',
        operation_description="Create example ...",
        responses={
            400: "Invalid data provided",
            401: "Not authenticated",
            403: "Not allowed",
            405: "Method not allowed ...",
            409: "Example id already exists",
            500: "Error creating example"
    })
    def create(self, request, *args, **kwargs):
        name = request.data.get('name')
        title = request.data.get('title')


        if settings.THROW_ERROR:
            return Response({'status': "Method not allowed. Check settings ..."}, status.HTTP_405_METHOD_NOT_ALLOWED)
        
        if Example.objects.filter(name=name).exists():
            return Response({'status': "Example name already exists"}, status.HTTP_409_CONFLICT)

        try:
            #configure_city(code, name, zoom_level=zoom_level, map_center_lon=map_center_lon, map_center_lat=map_center_lat)
            logging.info("Probando la creación de nuevos elementos !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        except Exception as e:
            logging.exception('Error configuring operator')
            return Response({'status': "Error creating example"}, status.HTTP_500_INTERNAL_SERVER_ERROR)
        return super().create(request, *args, **kwargs)
    
    def perform_create(self, serializer):
         serializer.save(name=serializer.initial_data['name'],
                         title=serializer.initial_data['title'])

    #def list(self, request, *args, **kwargs):
    #    if settings.THROW_ERROR:
    #        return Response({'status': "Method not allowed. Check settings"}, status.HTTP_405_METHOD_NOT_ALLOWED)
    #    return super().list(request, *args, **kwargs)

    #def retrieve(self, request, *args, **kwargs):
    #    if settings.THROW_ERROR:
    #        return Response({'status': "Method not allowed. Check settings"}, status.HTTP_405_METHOD_NOT_ALLOWED)
    #    return super().retrieve(request, *args, **kwargs)

    #def destroy(self, request, *args, **kwargs):
    #    if settings.THROW_ERROR:
    #        return Response({'status': "Method not allowed. Check settings"}, status.HTTP_405_METHOD_NOT_ALLOWED)
    #    return super().destroy(request, *args, **kwargs)
    
