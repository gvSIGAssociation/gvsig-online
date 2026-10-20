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

@author: Nacho Brodin <nbrodin@scolab.es>
'''

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from gvsigol_services import views as services_views


class TopologyAvailableLayersView(APIView):
    """
    Get available layers for topology rules configuration.
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Get list of available layers that can be used in topology rules. Returns layers from the same database as the target layer.",
        responses={
            200: openapi.Response(
                description="List of available layers",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_STRING, example='success'),
                        'layers': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_STRING, example='datastore:table_name'),
                                    'name': openapi.Schema(type=openapi.TYPE_STRING, example='datastore:table_name'),
                                    'table_name': openapi.Schema(type=openapi.TYPE_STRING, example='table_name'),
                                    'schema': openapi.Schema(type=openapi.TYPE_STRING, example='schema_name'),
                                    'datastore': openapi.Schema(type=openapi.TYPE_STRING, example='datastore_name'),
                                    'geom_type': openapi.Schema(type=openapi.TYPE_STRING, example='POLYGON'),
                                    'workspace': openapi.Schema(type=openapi.TYPE_STRING, example='workspace_name'),
                                    'layer_title': openapi.Schema(type=openapi.TYPE_STRING, example='Layer Title')
                                }
                            )
                        ),
                        'current_layer_id': openapi.Schema(type=openapi.TYPE_INTEGER, example=123),
                        'current_layer_name': openapi.Schema(type=openapi.TYPE_STRING, example='datastore:table_name'),
                        'total': openapi.Schema(type=openapi.TYPE_INTEGER, example=5)
                    }
                )
            ),
            404: openapi.Response(description="Layer not found")
        }
    )
    def get(self, request, lyr_id):
        """
        Get list of available layers that can be used in topology rules.
        """
        return services_views.get_topology_available_layers(request, lyr_id)


class TopologyRulesView(APIView):
    """
    Get topology rules for a layer.
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Get current topology rules configuration for a layer.",
        responses={
            200: openapi.Response(
                description="Current topology rules configuration",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_STRING, example='success'),
                        'rules': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'no_overlap': openapi.Schema(type=openapi.TYPE_BOOLEAN, example=False),
                                'no_gaps': openapi.Schema(type=openapi.TYPE_BOOLEAN, example=False),
                                'must_be_covered_by': openapi.Schema(type=openapi.TYPE_BOOLEAN, example=False),
                                'covered_by_layer': openapi.Schema(type=openapi.TYPE_STRING, example=''),
                                'must_not_overlap_with': openapi.Schema(type=openapi.TYPE_BOOLEAN, example=True),
                                'overlap_layers': openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(type=openapi.TYPE_STRING),
                                    example=['datastore:table_name']
                                ),
                                'must_be_contiguous': openapi.Schema(type=openapi.TYPE_BOOLEAN, example=False),
                                'contiguous_tolerance': openapi.Schema(type=openapi.TYPE_NUMBER, example=1.0)
                            }
                        ),
                        'total_rules': openapi.Schema(type=openapi.TYPE_INTEGER, example=1)
                    }
                )
            ),
            404: openapi.Response(description="Layer not found")
        }
    )
    def get(self, request, lyr_id):
        """
        Get current topology rules configuration for a layer.
        """
        return services_views.get_topology_rules(request, lyr_id)


class TopologyRulesSaveView(APIView):
    """
    Update topology rules for a layer.
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Update topology rules configuration for a layer.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'no_overlap': openapi.Schema(
                    type=openapi.TYPE_BOOLEAN,
                    description='Geometries within the same layer cannot overlap with each other'
                ),
                'no_gaps': openapi.Schema(
                    type=openapi.TYPE_BOOLEAN,
                    description='The layer coverage must be continuous without empty spaces'
                ),
                'must_be_covered_by': openapi.Schema(
                    type=openapi.TYPE_BOOLEAN,
                    description='All geometries must be completely covered by geometries from another layer'
                ),
                'covered_by_layer': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Layer that must cover (format: datastore:table)',
                    example='datastore:table_name'
                ),
                'must_not_overlap_with': openapi.Schema(
                    type=openapi.TYPE_BOOLEAN,
                    description='Geometries cannot overlap with geometries from specified layers'
                ),
                'overlap_layers': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_STRING),
                    description='List of layers with which geometries must not overlap',
                    example=['datastore:table_name', 'datastore:table_name2']
                ),
                'must_be_contiguous': openapi.Schema(
                    type=openapi.TYPE_BOOLEAN,
                    description='Geometries must be connected to existing geometries'
                ),
                'contiguous_tolerance': openapi.Schema(
                    type=openapi.TYPE_NUMBER,
                    description='Tolerance distance in meters for contiguity check',
                    example=1.0
                )
            },
            required=['no_overlap', 'no_gaps', 'must_be_covered_by', 'must_not_overlap_with', 'must_be_contiguous']
        ),
        responses={
            200: openapi.Response(
                description="Topology rules updated successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_STRING, example='success'),
                        'message': openapi.Schema(type=openapi.TYPE_STRING, example='Topology rules updated successfully'),
                        'layer_id': openapi.Schema(type=openapi.TYPE_INTEGER, example=123),
                        'configuration': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'no_overlap': openapi.Schema(type=openapi.TYPE_BOOLEAN, example=False),
                                'no_gaps': openapi.Schema(type=openapi.TYPE_BOOLEAN, example=False),
                                'must_be_covered_by': openapi.Schema(type=openapi.TYPE_BOOLEAN, example=False),
                                'covered_by_layer': openapi.Schema(type=openapi.TYPE_STRING, example=''),
                                'must_not_overlap_with': openapi.Schema(type=openapi.TYPE_BOOLEAN, example=True),
                                'overlap_layers': openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(type=openapi.TYPE_STRING),
                                    example=['datastore.table_name']
                                ),
                                'must_be_contiguous': openapi.Schema(type=openapi.TYPE_BOOLEAN, example=False),
                                'contiguous_tolerance': openapi.Schema(type=openapi.TYPE_NUMBER, example=1.0),
                                'active_rules_count': openapi.Schema(type=openapi.TYPE_INTEGER, example=1)
                            }
                        )
                    }
                )
            ),
            400: openapi.Response(description="Validation error"),
            404: openapi.Response(description="Layer not found"),
            500: openapi.Response(description="Internal server error")
        }
    )
    def post(self, request, lyr_id):
        """
        Update topology rules configuration for a layer.
        """
        return services_views.update_topology_rules(request, lyr_id) 