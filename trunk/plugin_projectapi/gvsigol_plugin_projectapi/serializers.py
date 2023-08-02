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
import json
import math

from rest_framework import serializers

from django.contrib.auth.models import User
from gvsigol_core.models import Project, ProjectLayerGroup, ProjectZone, ZoneLayers, Application
from gvsigol_plugin_projectapi import util
from gvsigol_plugin_baseapi.validation import HttpException
from gvsigol_services.models import LayerGroup, Layer, Server
from gvsigol import settings
from datetime import datetime
import time
from gvsigol_services import utils as services_utils
from django.utils import timezone
from psycopg2 import sql as sqlbuilder
import logging
import ast
from gvsigol_plugin_projectapi.export import VectorLayerExporter
import sys
from gvsigol_auth import utils as auth_utils
from gvsigol_auth import auth_backend

logging.basicConfig()
logger = logging.getLogger(__name__)

class UserSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField('get_roles_')

    def get_roles_(self, obj):
        return auth_backend.get_roles(obj.username)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_staff', 'is_superuser', 'last_login', 'roles']


class ZoneLayersSerializer(serializers.ModelSerializer):
    class Meta:
        model = ZoneLayers
        fields = ['layer', 'levels', 'tilematrixset', 'format', 'extentid', 'version', 'bboxes', 'pkgassigned']


class ProjectZoneSerializer(serializers.ModelSerializer):
    zone_layers = serializers.SerializerMethodField('get_zone_layers_')

    def get_zone_layers_(self, obj):
        resultset = ZoneLayers.objects.filter(zone_id=obj.id)
        serializer = ZoneLayersSerializer(resultset, many=True)
        return serializer.data
        
    class Meta:
        model = ProjectZone
        fields = ['id', 'title', 'project', 'levels', 'extent4326_minx', 'extent4326_miny', 'extent4326_maxx', 'extent4326_maxy', 'zone_layers', 'pkgassigned']


class GsInstanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Server
        fields = ['name', 'title', 'frontend_url']

class ProjectsSerializer(serializers.ModelSerializer):
    #line1 = serializers.CharField(help_text='Field documentation!')
    image = serializers.SerializerMethodField('get_project_image')
    base_layer_groups = serializers.SerializerMethodField('get_baselayer_groups')
    project_zone = serializers.SerializerMethodField('get_project_zones')

    def get_project_image(self, obj):
        # FIXME: we should to consider HTTP_ORIGIN and ALLOWED_HOST_NAMES to build the URL
        # See gvsigol_core.utils.get_absolute_url method
        return settings.BASE_URL + obj.image_url

    def get_baselayer_groups(self, obj):
        queryset = ProjectLayerGroup.objects.filter(project_id=obj.id)
        baselayer_group_ids = []
        for i in queryset:
            if i.baselayer_group == True:
                baselayer_group_ids.append(i.layer_group_id)
        return baselayer_group_ids

    def get_project_zones(self, obj):
        resultset = ProjectZone.objects.filter(project_id=obj.id)
        serializer = ProjectZoneSerializer(resultset, many=True)
        return serializer.data

    class Meta:
        model = Project
        fields = ['id', 'name', 'title', 'description', 'image', 'center_lat', 'center_lon', 'zoom', 'extent', 'toc_mode', 'toc_order', 'created_by', 'is_public', 'baselayer_version', 'base_layer_groups', 'project_zone', 'extent4326_minx', 'extent4326_miny', 'extent4326_maxx', 'extent4326_maxy', 'expiration_date']
        #fields = '__all__'
        
class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['id', 'name', 'title', 'description', 'image', 'center_lat', 'center_lon', 'zoom', 'extent', 'toc_mode', 'toc_order', 'created_by', 'is_public', 'baselayer_version']

class LayerGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = LayerGroup
        fields = ['id', 'name', 'title', 'cached', 'created_by', 'visible']
        


class FileUploadSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=100, default='')
    image = serializers.FileField()
    


class LayerChangesSerializer(serializers.Serializer):
    
    def check_changes(self, timestamp, layer, ncolumns, layertype, zone):
        if(layertype == 'tiles'):
            return self.check_tiled_layer_changes(timestamp, layer, zone)

        try:
            i, table, schema = services_utils.get_db_connect_from_layer(layer)
            with i as con: # connection will autoclose
                if timestamp <= 0:
                    return 0
                
                sql = sqlbuilder.SQL("SELECT count(*) FROM {schema}.{table} WHERE (extract(epoch from feat_date_gvol) *  1000) > {timestamp}")
                query = sql.format(
                    schema=sqlbuilder.Identifier(schema),
                    table=sqlbuilder.Identifier(table),
                    timestamp=sqlbuilder.Literal(timestamp),
                )
                try:
                    con.cursor.execute(query)
                    result = con.cursor.fetchone()
                    if result[0] > 0:
                        return result[0]
                except Exception as e:
                    pass #Puede pasar que no exista feat_date_gvol y de un error

                sql = sqlbuilder.SQL("SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE table_schema={schema} AND table_name={table}")
                query = sql.format(
                    schema=sqlbuilder.Literal(schema),
                    table=sqlbuilder.Literal(table)
                )

                con.cursor.execute(query)
                result = con.cursor.fetchone()
                if result[0] != ncolumns:
                    return 1 # Si ha cambiado el num de columnas devolvemos una modificación para que la app se actualice

            return 0

        except Exception as e:
            if isinstance(e, HttpException):
                raise e
            raise HttpException(400, "Features cannot be queried. Unexpected error: " + format(e))


    def check_tiled_layer_changes(self, timestamp, layer, zone):
        lyrs = ZoneLayers.objects.filter(zone__title=zone, layer=layer)
        for lyr in lyrs:
            if lyr.version > timestamp:
                return lyr.version
        return 0
    
class ApplicationsSerializer(serializers.ModelSerializer):
    #line1 = serializers.CharField(help_text='Field documentation!')
    image = serializers.SerializerMethodField('get_application_image')

    def get_application_image(self, obj):
        # FIXME: we should to consider HTTP_ORIGIN and ALLOWED_HOST_NAMES to build the URL
        # See gvsigol_core.utils.get_absolute_url method
        return settings.BASE_URL + obj.image_url

    class Meta:
        model = Application
        fields = ['id', 'name', 'title', 'description', 'image', 'url', 'conf', 'created_by', 'is_public']
        #fields = '__all__'


