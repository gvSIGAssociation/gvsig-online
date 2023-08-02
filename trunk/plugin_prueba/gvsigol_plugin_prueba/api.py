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
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.core.serializers import serialize
# from .serializers import PoiSerializer
from gvsigol_plugin_prueba.models import Poi
import json
from django.contrib.gis.geos import GEOSGeometry

logger = logging.getLogger(__name__)


class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return  # To not perform the csrf check previously happening


class PoiView(ListAPIView):
    serializer_class = None
    permission_classes = [AllowAny]
    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    @swagger_auto_schema(operation_id='get_pois', operation_summary='',
                         responses={404: "Database connection NOT found<br>User NOT found",
                                    403: "The project is not allowed to this user"})
    @action(detail=True, methods=['GET'])
    def get(self, request):
        try:
            pois = serialize('geojson', Poi.objects.all(
            ), geometry_field='geometry', fields=('uid', 'name', 'description'))

            response = {
                'pois': pois
            }
            return JsonResponse(response, safe=False)

        except HttpException as e:
            return e.get_exception()

    @swagger_auto_schema(operation_id='save_pois', operation_summary='',
                         responses={404: "Database connection NOT found<br>User NOT found",
                                    403: "The project is not allowed to this user"})
    @action(detail=True, methods=['POST'], permission_classes=[AllowAny])
    def post(self, request):
        try:
            content = get_content(request)
            json_pois = content.get('pois')

            try:
                Poi.objects.all().delete()
                count=1
                for p in json_pois:
                    geom_4326 = GEOSGeometry(p['wkt'], srid=4326)
                    count = count + 1
                    poi = Poi(
                        uid= count,
                        name=p['name'],
                        description=p['description'],
                        geometry=geom_4326
                    )
                    poi.save()

                response = {
                    'success': True
                }
                return JsonResponse(response, safe=False)

            except Exception as e:
                print('EXCEPTION IN METHOD: save_pois')
                print(str(e))

                response = {
                    'success': False
                }
                return JsonResponse(response, safe=False)

        except HttpException as e:
            return e.get_exception()

    @swagger_auto_schema(operation_id='update_pois', operation_summary='',
                         responses={404: "Database connection NOT found<br>User NOT found",
                                    403: "The project is not allowed to this user"})
    @action(detail=True, methods=['PUT'], permission_classes=[AllowAny])
    def put(self, request, pk):

        try:
            poi = Poi.objects.get(id=pk)
            content = get_content(request)
            properties = content.get('properties')
            poi.name = properties['name']
            poi.description = properties['description']
            poi.save()

            response = {
                'success': True
            }
            return JsonResponse(response, safe=False)

        except Exception as e:
         print('EXCEPTION IN METHOD: update_pois')
         print(str(e))

        response = {
            'success': False
        }
        return JsonResponse(response, safe=False)
      

    @swagger_auto_schema(operation_id='delete_pois', operation_summary='',
                         responses={404: "Database connection NOT found<br>User NOT found",
                                    403: "The project is not allowed to this user"})
    @action(detail=True, methods=['DELETE'], permission_classes=[AllowAny])
    def delete(self, request, pk):

        try:
            poi = Poi.objects.get(id=pk)
            poi.delete()
            response = {
                'success': True
            }
            return JsonResponse(response, safe=False)

        except Exception as e:
         print('EXCEPTION IN METHOD: delete_pois')
         print(str(e))

        response = {
            'success': False
        }
        return JsonResponse(response, safe=False)

def get_content(request):
    try:
        if (request.body != ''):
            body_unicode = request.body.decode('utf-8')
            return json.loads(body_unicode)

    except Exception as e:
        raise HttpException(400, "Feature malformed." + format(e))


class SearchPoiView(ListAPIView):
    serializer_class = None
    permission_classes = [AllowAny]
    authentication_classes = (
        CsrfExemptSessionAuthentication, BasicAuthentication)

    @swagger_auto_schema(operation_id='search_pois', operation_summary='',
                         responses={404: "Database connection NOT found<br>User NOT found",
                                    403: "The project is not allowed to this user"})
    @action(detail=True, methods=['GET'])
    def get(self, request):
        try:
            # Se Obtienen los parámetros de la solicitud HTTP

            #   logger.info("Recibiendo solicitud de búsqueda de Pois...")

            latitude = request.query_params.get('latitude')
            longitude = request.query_params.get('longitude')
            radius = request.query_params.get('radius')

            # logger.info(f"Parámetros de búsqueda: latitude={latitude}, longitude={longitude}, radius={radius}")

            # Se Convierten las coordenadas a un objeto Point
            location = Point(float(longitude), float(latitude))

            # Se Buscan los Pois que se encuentran dentro del radio especificado
            pois = Poi.objects.annotate(distance=Distance(
                'geometry', location)).filter(distance__lte=radius)

            # Se Serializan los Pois encontrados como GeoJSON y devolverlos en una respuesta HTTP
            serialize_pois = serialize(
                'geojson', pois, geometry_field='geometry', fields=('name', 'description'))
            response = {
                'pois': serialize_pois
            }

            return Response(response)

        except HttpException as e:
            return e.get_exception()
