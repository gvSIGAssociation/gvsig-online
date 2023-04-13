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

import json
from django.http.response import JsonResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import action
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import AllowAny
from gvsigol_plugin_baseapi.validation import HttpException

import json

class TestView(ListAPIView):
    serializer_class = None
    permission_classes = [AllowAny]

    @swagger_auto_schema(operation_id='get_test', operation_summary='', 
                         responses={404: "Database connection NOT found<br>User NOT found",
                                    403: "The project is not allowed to this user"})
    @action(detail=True, methods=['GET'])
    def get(self, request):
        try: 
            param = request.query_params.get('param')
            
            response = {
                'success': False
            }
            return JsonResponse(response, safe=False)
            
        except HttpException as e:
            return e.get_exception()
    
    @swagger_auto_schema(operation_id='post_test', operation_summary='', 
                         responses={404: "Database connection NOT found<br>User NOT found",
                                    403: "The project is not allowed to this user"})
    @action(detail=True, methods=['POST'])
    def post(self, request):
        try:
            content = get_content(request)

            response = {
                'success': False
            }

            return JsonResponse(response, safe=False)

        except HttpException as e:
            return e.get_exception()


def get_content(request):
    try:
        if(request.body != ''):
            body_unicode = request.body.decode('utf-8')
            return json.loads(body_unicode)

    except Exception as e:
        raise HttpException(400, "Feature malformed." + format(e))
