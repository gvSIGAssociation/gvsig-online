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
from gvsigol_core.models import Project, ProjectLayerGroup, Application
from gvsigol_plugin_projectapi import util
from gvsigol_services.models import LayerGroup, Layer
from gvsigol import settings
from datetime import datetime
import time
from gvsigol_services import utils as services_utils
from django.utils import timezone
from psycopg2 import sql as sqlbuilder
from pyproj import Proj, transform
import logging
import ast
from gvsigol_services import views as serviceviews
from gvsigol_core import utils as coreutils
from operator import itemgetter

#logging.basicConfig()
logger = logging.getLogger(__name__)

class LayerSerializer(serializers.ModelSerializer):
    icon = serializers.SerializerMethodField('get_layer_icon')
    last_change = serializers.SerializerMethodField('get_last_change_')
    external_url = serializers.SerializerMethodField('get_external_url_')
    external_layers = serializers.SerializerMethodField('get_external_layers_')
    image_type = serializers.SerializerMethodField('get_image_type_')
    external_tilematrixset = serializers.SerializerMethodField('get_external_tilematrixset_')
    workspace = serializers.SerializerMethodField('get_layer_workspace_')
    writable = serializers.SerializerMethodField('is_writable')
    public = serializers.SerializerMethodField('is_public')
    service_version = serializers.SerializerMethodField('get_external_service_version')
    description = serializers.SerializerMethodField('get_description_')
    wms_url = serializers.SerializerMethodField('get_wms_url_')
    wfs_url = serializers.SerializerMethodField('get_wfs_url_')
    cache_url = serializers.SerializerMethodField('get_cache_url_')
    legend_url = serializers.SerializerMethodField('get_legend_url_')
    baselayer = serializers.SerializerMethodField('get_baselayer_')
    default_baselayer = serializers.SerializerMethodField('get_default_baselayer_')
    order = serializers.SerializerMethodField('get_order_')
    external_params = serializers.SerializerMethodField('get_external_params_')

    def get_field_group(self, form_groups, lang):
        field_group = {}
        grouporder = 0
        if form_groups:
            for group in form_groups:
                fieldorder = 0
                for field in group['fields']:
                    prop_title = 'title-' + lang
                    if prop_title in group and group[prop_title] != '':
                        title = group[prop_title]
                    else:
                        title = group['name']
                    field_group[field] = {'groupname': title, 'grouporder': grouporder, 'fieldorder': fieldorder}
                    fieldorder = fieldorder + 1
                grouporder = grouporder + 1
        return field_group

    def add_fields_to_description(self, result, layer, lang):
        fields = None
        form_groups = None
        try:
            if(layer.conf):
                conf = ast.literal_eval(layer.conf)
                fields = conf.get('fields', [])
                form_groups = conf.get('form_groups', [])
        except Exception:
            return

        try:
            i, table, schema = services_utils.get_db_connect_from_layer(layer)
            with i as con: # connection will auoclose
                pks = con.get_pk_columns(table, schema=schema)

                field_group = self.get_field_group(form_groups, lang)

                for i in result['fields']:
                    #Se añade el check de "Obligatorio" de los campos de una capa
                    if fields is not None:
                        for field in fields:
                            if field['name'] == i['name']:
                                try:
                                    i['mandatory'] = field['mandatory']
                                except Exception:
                                    i['mandatory'] = False
                                try:
                                    i['editable'] = field['editable']
                                except Exception:
                                    i['editable'] = True
                                try:
                                    i['visible'] = field['visible']
                                except Exception:
                                    i['visible'] = True
                                try:
                                    i['editableactive'] = field['editableactive']
                                except Exception:
                                    i['editableactive'] = True
                                try:
                                    i['infovisible'] = field['infovisible']
                                except Exception:
                                    i['infovisible'] = True

                    #Se añade si el campo es PK o no
                    if pks is not None and len(pks) > 0:
                        for pk in pks:
                            if i['name'] == pk:
                                i['pk'] = 'YES'
                                break
                            else:
                                i['pk'] = 'NO'
                    
                    #Se añade la lista de valores que puede tomar el campo si este es enumerado
                    if i['type'].endswith('enumeration'):
                        items = services_utils.get_enum_item_list(layer, i['name'])
                        list_ = []
                        for j in items:
                            list_.append(j.name)
                        i['values'] = list_
                    
                    i['translate'] = self.translate(layer.conf, i['name'], lang)
                    if i['name'] in field_group:
                        i['groupname'] = field_group[i['name']]['groupname']
                        i['grouporder'] = field_group[i['name']]['grouporder']
                        i['fieldorder'] = field_group[i['name']]['fieldorder']  

            return result

        except Exception:
            return
    
    def translate(self, conf, fieldName, lang):
        try:
            result = fieldName
            conf = ast.literal_eval(conf)
            for j in conf['fields']:
                if fieldName == j['name']:
                    try:
                        result = j['title-' + lang]
                        break
                    except Exception:
                        result = fieldName
            return result
        except Exception:
            return result

    def get_description_(self, obj):
        if obj.datastore:
            result = serviceviews.describe_feature_type(obj.name, obj.datastore.workspace.name)
            result = self.add_fields_to_description(result, obj, self.context['lang'])
            return result

    def is_writable(self, obj):
        try:
            if(obj.external):
                return False  
            if self.context.get('request'):
                return services_utils.can_write_layer(self.context['request'], obj)
            else:
                return False
        except Exception:
            return False

    def is_public(self, obj):
        try:
            if(obj.public):
                return True  
            else:
                return False

        except Exception:
            return False

    def get_layer_workspace_(self, obj):
        try:
            #layer = Layer.objects.get(id=obj.id)
            if obj.datastore and obj.datastore.workspace:
                return obj.datastore.workspace.name
        except Exception:
            pass

    def get_external_tilematrixset_(self, obj):
        try:
            params = json.loads(obj.external_params)
            return params['matrixset']
        except Exception:
            pass
    def get_external_service_version(self, obj):
        try:
            params = json.loads(obj.external_params)
            return params['version']
        except Exception:
            pass
    def get_external_url_(self, obj):
        try:
            params = json.loads(obj.external_params)
            return params['url']
        except Exception:
            pass

    def get_external_layers_(self, obj):
        try:
            params = json.loads(obj.external_params)
            return params['layers']
        except Exception:
            pass

    def get_image_type_(self, obj):
        try:
            params = json.loads(obj.external_params)
            return params['format']
        except Exception:
            pass

    def get_layer_icon(self, obj):
        _, url = services_utils.get_layer_img(obj.id, None)
        return url 

    def get_last_change_(self, obj):
        try:
            #Si hay muchas capas se abren y cierran constantemente conexiones a la bd lo que ralentiza. 
            #Almacenamos en un array las conexiones y al acabar las consultas se cierran
            #De esta forma solo se abre una por datastore y no una por capa.
            if obj.datastore:
                con = self.root.instance.connections[obj.datastore.id]
                table = obj.source_name if obj.source_name else obj.name
                sql = "select max({date_col}) as max from {schema}.{table}"
                query = sqlbuilder.SQL(sql).format(
                    date_col=sqlbuilder.Identifier(settings.DATE_FIELD),
                    schema=sqlbuilder.Identifier(obj.datastore.name),
                    table=sqlbuilder.Identifier(table))
                con.cursor.execute(query, [])
                for r in con.cursor.fetchall():
                    return r[0]
        except Exception as e:
            pass
        return datetime(2000, 1, 1)

    def get_wms_url_(self, obj):
        try:
            workspace = obj.datastore.workspace
            url = workspace.wms_endpoint.replace(settings.BASE_URL, '')
            return url

        except Exception:
            pass

    def get_wfs_url_(self, obj):
        try:
            workspace = obj.datastore.workspace
            url = workspace.wfs_endpoint.replace(settings.BASE_URL, '')
            return url

        except Exception:
            pass

    def get_legend_url_(self, obj):
        try:
            workspace = obj.datastore.workspace
            url = workspace.wms_endpoint.replace(settings.BASE_URL, '') + '?SERVICE=WMS&VERSION=1.1.1&layer=' + obj.name + '&REQUEST=getlegendgraphic&FORMAT=image/png&LEGEND_OPTIONS=forceLabels:on'
            return url

        except Exception:
            pass

    def get_cache_url_(self, obj):
        try:
            workspace = obj.datastore.workspace
            url = workspace.wms_endpoint.replace(settings.BASE_URL, '')
            if obj.cached:
                if workspace.wmts_endpoint and workspace.wmts_endpoint.__len__() > 0:
                    url = workspace.wmts_endpoint.replace(settings.BASE_URL, '')
                else:
                    url = workspace.cache_endpoint.replace(settings.BASE_URL, '')
            return url               

        except Exception:
            pass

    def get_baselayer_ (self, obj):
        baselayer = False
        project_group = ProjectLayerGroup.objects.filter(layer_group=obj.layer_group, project=self.context['projectid']) 
        for i in project_group:
            if i.baselayer_group:
                return True
                    

        return False
    
    def get_default_baselayer_ (self, obj):
        project_group = ProjectLayerGroup.objects.filter(layer_group=obj.layer_group, project=self.context['projectid'])
        for i in project_group:
            if i.baselayer_group:
                if obj.id == i.default_baselayer:
                    return True

        return False

    def get_order_ (self, obj):
        project_group = ProjectLayerGroup.objects.filter(layer_group=obj.layer_group, project=self.context['projectid'])[0]
        project = Project.objects.get(id=project_group.project_id)
        if not project.toc_order:
            project.toc_order = "{}"
        toc = json.loads(project.toc_order)

        group_order = 0
        if toc.get(project_group.layer_group.name):
            group_order = toc.get(project_group.layer_group.name).get('order')

        order = group_order + obj.order
        return order

    def get_external_params_ (self, obj):
        external_params = {}
        if obj.external_params:
            external_params = json.loads(obj.external_params)
        
        if 'capabilities' in external_params:
            external_params.pop('capabilities')
        return external_params
        
    class Meta:
        model = Layer
        fields = ['id', 'name', 'title', 'abstract', 'type', 'visible', 'queryable', 'cached', 'single_image', 'real_time', 'vector_tile', 'created_by', 'thumbnail', 'layer_group_id', 'icon', 'last_change', 'latlong_extent', 'native_extent', 'external_layers', 'external_url', 'external_tilematrixset', 'workspace', 'image_type', 'writable', 'public', 'external', 'service_version', 'description', 'wms_url', 'wfs_url', 'cache_url', 'legend_url', 'baselayer', 'default_baselayer', 'order', 'external_params']


class LayerGroupSerializer(serializers.ModelSerializer):
    layers = serializers.SerializerMethodField('get_layers_')
    order = serializers.SerializerMethodField('get_order_')

    def get_layers_(self, obj):
        request = self.context['request']
        username = self.context.get('user')
        lang = self.context['lang']
        projectid = self.context['projectid']
        queryset = util.get_layerread_by_user_and_group(request, obj.id).order_by("-order")
        serializer = LayerSerializer(queryset, many=True, context={'request': request, 'user': username, 'lang': lang, 'projectid': projectid})
        return serializer.data

    def get_order_(self, obj):
        projectid = self.context['projectid']
        order = util.get_order_in_project(projectid, obj.name)
        return order

    class Meta:
        model = LayerGroup
        fields = ['id', 'name', 'title', 'cached', 'created_by', 'visible', 'server_id', 'layers', 'order']

class PublicLayerGroupSerializer(serializers.ModelSerializer):
    layers = serializers.SerializerMethodField('get_layers_')
    order = serializers.SerializerMethodField('get_order_')

    def get_layers_(self, obj):
        lang = self.context['lang']
        projectid = self.context['projectid']
        queryset = util.get_layerread_by_group(obj.id)
        serializer = LayerSerializer(queryset, many=True, context={'lang': lang, 'projectid': projectid})
        return serializer.data

    def get_order_(self, obj):
        projectid = self.context['projectid']
        order = util.get_order_in_project(projectid, obj.name)
        return order

    class Meta:
        model = LayerGroup
        fields = ['id', 'name', 'title', 'cached', 'created_by', 'visible', 'server_id', 'layers', 'order']


class InfoSerializer(serializers.ModelSerializer):
    #line1 = serializers.CharField(help_text='Field documentation!')
    image = serializers.SerializerMethodField('get_project_image')
    relative_image = serializers.SerializerMethodField('get_project_relative_image')
    base_layer_groups = serializers.SerializerMethodField('get_baselayer_groups')
    layer_groups = serializers.SerializerMethodField('get_project_layer_groups')
    default_baselayer = serializers.SerializerMethodField('get_default_baselayer_')
    gs_instances = serializers.SerializerMethodField('get_geoserver_instances')
    plugins = serializers.SerializerMethodField('get_plugins_')
    supported_crs = serializers.SerializerMethodField('get_supported_crs_')
    extent_array = serializers.SerializerMethodField('_get_extent')

    def get_project_layer_groups(self, obj):
        request = self.context['request']
        username = self.context.get('user')
        lang = self.context['lang']
        resultset = util.get_layergroups_by_user_and_project(request, obj.id)
        serializer = LayerGroupSerializer(resultset, many=True, context={'request': request, 'user': username, 'lang': lang, 'projectid': obj.id})
        ordered_layer_groups = sorted(serializer.data, key=itemgetter('order'), reverse=True)
        return ordered_layer_groups

    def get_project_image(self, obj):
        # FIXME: we should to consider HTTP_ORIGIN and ALLOWED_HOST_NAMES to build the URL
        # See gvsigol_core.utils.get_absolute_url method
        return settings.BASE_URL + obj.image_url

    def get_project_relative_image(self, obj):
        # FIXME: we should to consider HTTP_ORIGIN and ALLOWED_HOST_NAMES to build the URL
        # See gvsigol_core.utils.get_absolute_url method
        return obj.image_url

    def get_baselayer_groups(self, obj):
        queryset = ProjectLayerGroup.objects.filter(baselayer_group=True, project_id=obj.id)
        baselayer_group_ids = []
        for i in queryset:
            baselayer_group_ids.append(i.layer_group_id)
        return baselayer_group_ids

    def get_default_baselayer_ (self, obj):
        baselayer_group = ProjectLayerGroup.objects.filter(baselayer_group=True, project_id=obj.id)
        for i in baselayer_group:
            return i.default_baselayer

    def get_geoserver_instances (self, obj):
        request = self.context['request']
        lang = self.context['lang']
        resultset = util.get_layergroups_by_user_and_project(request, obj.id)
        instances = util.get_geoserver_instances(resultset)
        instances = list(dict.fromkeys(instances))
        return instances

    def get_plugins_ (self, obj):
        project_plugins = util.get_plugins(obj)
        return project_plugins

    def get_supported_crs_ (self, obj):
        supp_crs = coreutils.get_supported_crs()
        return supp_crs
    
    def _get_extent(self, obj):
        if obj.extent:
            extent = obj.extent.split(",")
            min_x = float(extent[0])
            min_y = float(extent[1])
            max_x = float(extent[2])
            max_y = float(extent[3])
            return [min_x, min_y , max_x , max_y]
        return None

    class Meta:
        model = Project
        fields = ['id', 'name', 'title', 'description', 'image', 'relative_image', 'center_lat', 'center_lon', 'zoom', 'extent', "extent_array", 'toc_mode', 'toc_order', 'created_by', 'is_public', 'baselayer_version', 'base_layer_groups', 'layer_groups', 'default_baselayer', 'gs_instances', 'plugins', 'supported_crs', 'expiration_date']
        #fields = '__all__'


class PublicInfoSerializer(serializers.ModelSerializer):
    #line1 = serializers.CharField(help_text='Field documentation!')
    image = serializers.SerializerMethodField('get_project_image')
    relative_image = serializers.SerializerMethodField('get_project_relative_image')
    base_layer_groups = serializers.SerializerMethodField('get_baselayer_groups')
    layer_groups = serializers.SerializerMethodField('get_project_layer_groups')
    default_baselayer = serializers.SerializerMethodField('get_default_baselayer_')
    gs_instances = serializers.SerializerMethodField('get_geoserver_instances')
    plugins = serializers.SerializerMethodField('get_plugins_')
    supported_crs = serializers.SerializerMethodField('get_supported_crs_')

    def get_project_layer_groups(self, obj):
        lang = self.context['lang']
        resultset = util.get_layergroups_by_project(obj.id)
        serializer = PublicLayerGroupSerializer(resultset, many=True, context={'lang': lang, 'projectid': obj.id})
        return serializer.data

    def get_project_image(self, obj):
        # FIXME: we should to consider HTTP_ORIGIN and ALLOWED_HOST_NAMES to build the URL
        # See gvsigol_core.utils.get_absolute_url method
        return settings.BASE_URL + obj.image_url

    def get_project_relative_image(self, obj):
        # FIXME: we should to consider HTTP_ORIGIN and ALLOWED_HOST_NAMES to build the URL
        # See gvsigol_core.utils.get_absolute_url method
        return obj.image_url

    def get_baselayer_groups(self, obj):
        queryset = ProjectLayerGroup.objects.filter(baselayer_group=True, project_id=obj.id)
        baselayer_group_ids = []
        for i in queryset:
            baselayer_group_ids.append(i.layer_group_id)
        return baselayer_group_ids

    def get_default_baselayer_ (self, obj):
        baselayer_group = ProjectLayerGroup.objects.filter(baselayer_group=True, project_id=obj.id)
        for i in baselayer_group:
            return i.default_baselayer

    def get_geoserver_instances (self, obj):
        resultset = util.get_layergroups_by_project(obj.id)
        instances = util.get_geoserver_instances(resultset)
        instances = list(dict.fromkeys(instances))
        return instances

    def get_plugins_ (self, obj):
        project_plugins = util.get_plugins(obj)
        return project_plugins

    def get_supported_crs_ (self, obj):
        supp_crs = coreutils.get_supported_crs()
        return supp_crs

    class Meta:
        model = Project
        fields = ['id', 'name', 'title', 'description', 'image', 'relative_image', 'center_lat', 'center_lon', 'zoom', 'extent', 'toc_mode', 'toc_order', 'created_by', 'is_public', 'baselayer_version', 'base_layer_groups', 'layer_groups', 'default_baselayer', 'gs_instances', 'plugins', 'supported_crs', 'expiration_date']
        #fields = '__all__'

class AppInfoSerializer(serializers.ModelSerializer):
    conf = serializers.SerializerMethodField('get_application_conf')
    image = serializers.SerializerMethodField('get_project_image')
    relative_image = serializers.SerializerMethodField('get_project_relative_image')

    def get_application_conf (self, obj):
        conf = json.loads(obj.conf)
        while isinstance(conf, str):
            conf = json.loads(obj.conf)

        return conf
    
    def get_project_image(self, obj):
        # FIXME: we should to consider HTTP_ORIGIN and ALLOWED_HOST_NAMES to build the URL
        # See gvsigol_core.utils.get_absolute_url method
        return settings.BASE_URL + obj.image_url

    def get_project_relative_image(self, obj):
        # FIXME: we should to consider HTTP_ORIGIN and ALLOWED_HOST_NAMES to build the URL
        # See gvsigol_core.utils.get_absolute_url method
        return obj.image_url

    class Meta:
        model = Application
        fields = ['conf', 'image', 'relative_image']
        


