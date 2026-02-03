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

'''
import logging
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.http import require_safe
from django.apps import apps as django_apps
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from gvsigol_plugin_baseapi.apps import GvsigolBaseApiConfig
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

#logging.basicConfig()
logger = logging.getLogger(__name__) 


@require_safe
def get_csrftoken(request):
    """
    Exposes the CSRF token for Ajax requests. This is safe, since a different CSRFToken is generated for
    each session, so 3rd party sites requesting this method will get a different token (unless 
    credentials=yes is used and the 3rd party site is allowed in CORS configuration for authenticated
    requests).
    """
    return JsonResponse({
        'csrftoken': get_token(request)
    })


class PluginStatusView(APIView):
    """
    Template class to return plugin name and status. Subclasses should override the plugin_name attribute.

    Use it by subclassing and overriding the plugin_name attribute.

    Example:
    class PluginPyCStatusView(PluginStatusView):
        plugin_name = GvsigolPyCAPIConfig.name

    Then use it in the urls.py:
    path('status/', PluginPyCStatusView.as_view(), name='my-plugin-status'),
    """
    permission_classes = (AllowAny,)
    plugin_name = GvsigolBaseApiConfig.name

    @swagger_auto_schema(
        operation_summary="Plugin status",
        operation_description="Returns plugin name and status.",
        responses={
            200: openapi.Response(
                description="OK",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'name': openapi.Schema(type=openapi.TYPE_STRING),
                        'status': openapi.Schema(type=openapi.TYPE_STRING),
                    },
                    required=['name', 'status'],
                ),
                examples={
                    'application/json': {'name': 'gvsigol_plugin_baseapi', 'status': 'ok'}
                }
            )
        },
        tags=['status']
    )
    def get(self, request, *args, **kwargs):
        data = {
            'name': self.plugin_name,
            'status': 'ok'
        }
        return Response(data)