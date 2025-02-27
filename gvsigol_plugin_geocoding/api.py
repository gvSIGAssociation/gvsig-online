'''
    gvSIG Online.
    Copyright (C) 2024 SCOLAB.

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


import json
from wsgiref.util import FileWrapper
import ast
import coreapi
from django.http.response import HttpResponse, JsonResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import action
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny

from psycopg2 import sql as sqlbuilder
import re
from django.utils.translation import gettext_lazy as _

from gvsigol_plugin_geocoding.models import Logstashetl
from rest_framework import serializers, status
from gvsigol_services.models import Layer, LayerGroup, Server
from rest_framework.response import Response



#--------------------------------------------------
#              LogstashView
#--------------------------------------------------
class LogstashView(ListAPIView):
    serializer_class = None
    pagination_class = None
    #permission_classes = [AllowAny]
    
    @swagger_auto_schema(operation_id='get_geoserver_legend', operation_summary='Get the geoserver legend',
                          responses={
                                    404: "Resource NOT found"
                                    })
    @action(detail=True, methods=['GET'], permission_classes=[IsAuthenticated])
    def get(self, request):
        try:
            input = ""
            filters = ""
            output = ""
            result = None
            for etl in  Logstashetl.objects.all():
                if etl.type == 'INPUT':
                    input += ("\n" + etl.config)
                if etl.type == 'FILTER':
                    filters += ("\n" + etl.config)
                if etl.type == 'OUTPUT':
                    output += ("\n" + etl.config)
            result = "input {" + input + "\n}\n\n"
            result += "filter {" + filters + "\n}\n\n"
            result += "output {" + output + "\n}\n\n"
            return HttpResponse(result, content_type="text/plain")
        except Exception as e:
            return HttpException(404, "Error reading configuration").get_exception()


class HttpException(Exception):
    def __init__(self, code, msg):
        self.msg = msg
        self.code = code
        
    def get_message(self):
        return "<html><h3>" + str(self.code) + ": " + self.msg + "</h3></html>"
                    
    def get_exception(self):
        response = HttpResponse(self.get_message())
        response.status_code = self.code
        return response
    
class LogstashETLSerializer(serializers.ModelSerializer):
    class Meta:
        model = Logstashetl
        fields = '__all__'
