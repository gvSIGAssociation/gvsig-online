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
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from gvsigol_plugin_baseapi.validation import HttpException
from rest_framework.authentication import SessionAuthentication, BasicAuthentication

from gvsigol_services.models import ServiceUrl
import json

logger = logging.getLogger(__name__)


class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return  # To not perform the csrf check previously happening


class ServicesView(ListAPIView):
    serializer_class = None
    permission_classes = [AllowAny]
    authentication_classes = (CsrfExemptSessionAuthentication, BasicAuthentication)

    @swagger_auto_schema(operation_id='get_services', operation_summary='',
                         responses={404: "Database connection NOT found<br>User NOT found",
                                    403: "The project is not allowed to this user"})
    @action(detail=True, methods=['GET'])
    def get(self, request):
        try:
            wms_queryset = ServiceUrl.objects.filter(type='WMS')
            wfs_queryset = ServiceUrl.objects.filter(type='WFS')

            wms = []
            for wms_serv in wms_queryset:
                wms.append({
                    'title': wms_serv.title,
                    'url': wms_serv.url
                })

            wfs = []
            for wfs_serv in wfs_queryset:
                wfs.append({
                    'title': wfs_serv.title,
                    'url': wfs_serv.url
                })

            response = {
                'wms': wms,
                'wfs': wfs
            }
            return JsonResponse(response, safe=False)

        except HttpException as e:
            return e.get_exception()