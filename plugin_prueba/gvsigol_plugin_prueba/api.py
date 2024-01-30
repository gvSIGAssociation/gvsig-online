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

@author: Javier Rodrigo <jrodrigo@scolab.es>
'''
import logging
import json
from django.http.response import JsonResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import action
from rest_framework.decorators import api_view
from django.shortcuts import get_object_or_404
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAuthenticated
from gvsigol_plugin_baseapi.validation import HttpException
from rest_framework.authentication import SessionAuthentication, BasicAuthentication

from rest_framework.response import Response
import json
from django.contrib.gis.geos import GEOSGeometry

logger = logging.getLogger(__name__)


class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return  # To not perform the csrf check previously happening


class DataView(ListAPIView):
    serializer_class = None
    authentication_classes = (CsrfExemptSessionAuthentication, BasicAuthentication)

    @swagger_auto_schema(operation_id='get_data', operation_summary='',
                         responses={404: "Database connection NOT found<br>User NOT found",
                                    403: "The project is not allowed to this user"})
    @action(detail=True, methods=['GET'], permission_classes=[AllowAny])
    def get(self, request):
        try:
            response = {
                'success': True
            }
            return JsonResponse(response, safe=False)

        except HttpException as e:
            return e.get_exception()

    @swagger_auto_schema(operation_id='save_data', operation_summary='',
                         responses={404: "Database connection NOT found<br>User NOT found",
                                    403: "The project is not allowed to this user"})
    @action(detail=True, methods=['POST'], permission_classes=[AllowAny])
    def post(self, request):
        try:
            content = get_content(request)
            json_data = content.get('data')

            try:
                response = {
                    'success': True
                }
                return JsonResponse(response, safe=False)

            except Exception as e:
                print('EXCEPTION IN METHOD: save_data')
                print(str(e))

                response = {
                    'success': False
                }
                return JsonResponse(response, safe=False)

        except HttpException as e:
            return e.get_exception()

def get_content(request):
    try:
        if (request.body != ''):
            body_unicode = request.body.decode('utf-8')
            return json.loads(body_unicode)

    except Exception as e:
        raise HttpException(400, "Feature malformed." + format(e))
