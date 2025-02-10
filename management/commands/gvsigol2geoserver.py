# -*- coding: utf-8 -*-

'''
    gvSIG Online.
    Copyright (C) 2023 SCOLAB.

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
@author: Cesar Martinez <cmartinez@scolab.es>
'''

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
import logging
import ast

from gvsigol_services.models import Workspace, Datastore, Layer, LayerGroup, Server
from gvsigol_services import utils, geographic_servers
from gvsigol_symbology.models import Style, StyleLayer
from gvsigol_symbology import sld_builder

LOGGER_NAME = 'gvsigol'


def process_layer_symbol(lyr, style):
    if not style.name.endswith('__tmp'):
        #    styles.append(layerStyle.style)
        gs = geographic_servers.get_instance().get_server_by_id(lyr.datastore.workspace.server.id)
        sld_body = sld_builder.build_sld(lyr, style)
        try:
            gs.createStyle(style.name, sld_body)
        except:
            pass
        gs.setLayerStyle(lyr, style.name, style.is_default)

def create_symbology():
    for lyr in Layer.objects.filter(external=False):
        layerStyles = StyleLayer.objects.filter(layer=lyr)
        for layerStyle in layerStyles:
            try:
                process_layer_symbol(lyr, layerStyle.style)
            except:
                logging.getLogger(LOGGER_NAME).exception(f"Error creating layer styles: {lyr.id} - {lyr.name}")

def create_layer(l):
    server = geographic_servers.get_instance().get_server_by_id(l.datastore.workspace.server.id)
    extraParams = {}
    if l.type.startswith('v_'):
        # ensure we get a value for max_features
        try:
            layerConf = ast.literal_eval(l.conf)
        except:
            layerConf = {}
        layerConf['featuretype'] = layerConf.get('featuretype', {})
        layerConf['featuretype']['max_features'] = layerConf['featuretype'].get('max_features', 0)
        extraParams['maxFeatures'] = layerConf['featuretype'].get('max_features', 0)
    server.createResource(
        l.datastore.workspace,
        l.datastore,
        l.name,
        l.title,
        extraParams=extraParams
    )

    if l.datastore.type != 'e_WMS' and l.datastore.type != 'c_ImageMosaic':
        server.setQueryable(
            l.datastore.workspace.name,
            l.datastore.name,
            l.datastore.type,
            l.name,
            l.queryable
        )
    #do_config_layer(server, newRecord, featuretype)
    #layer_autoconfig(layer, featuretype)
    ds_type = l.datastore.type
    if ds_type == 'c_ImageMosaic':
        server.updateImageMosaicTemporal(l.datastore, l)
    elif ds_type[0:2] == 'v_':
        utils.set_time_enabled(server, l)
    #if ds_type != 'e_WMS':
    #    create_symbology(server, l)

    server.createOrUpdateGeoserverLayerGroup(l.layer_group)

def create_layers():
    for l in Layer.objects.filter(external=False):
        try:
            print(f"Creating layer: {l.id} - {l.name}")
            create_layer(l)
            print(f"Layer created: {l.id} - {l.name}")
        except:
            logging.getLogger(LOGGER_NAME).exception(f"Error creating layer: {l.id} - {l.name}")

def create_datastores():
    for ds in Datastore.objects.all():
        gs = geographic_servers.get_instance().get_server_by_id(ds.workspace.server.id)
        try:
            if gs.createDatastore(ds.workspace,
                          ds.type,
                          ds.name,
                          ds.description,
                          ds.connection_params):
                print(f"Datastore created: {ds.id} - {ds.name}")
            else:
                print(f"Datastore not created: {ds.id} - {ds.name}")
        except:
            logging.getLogger(LOGGER_NAME).exception("Error creating datastore")

def create_workspaces():
    for ws in Workspace.objects.all():
        gs = geographic_servers.get_instance().get_server_by_id(ws.server.id)
        try:
            if gs.createWorkspace(ws.name, ws.uri):
                print(f"Worksace created: {ws.id} - {ws.name}")
            else:
                    print(f"Worksace not created: {ws.id} - {ws.name}")
        except:
            logging.getLogger(LOGGER_NAME).exception("Error creating workspace")


def create_geoserver_conf():
    create_workspaces()
    create_datastores()
    create_layers()
    create_symbology()

    for s in Server.objects.all():
        gs = geographic_servers.get_instance().get_server_by_id(s.id)
        gs.reload_nodes()
        gs.setDataRules()
        gs.reload_nodes()

class Command(BaseCommand):
    """
    Creates Geoserver configuration from existing gvSIG Online database configuration.
    """
    help = "Creates Geoserver configuration from existing gvSIG Online database configuration"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


    def handle(self, *args, **options):
        create_geoserver_conf()

        self.stdout.write(
            self.style.SUCCESS('Command completed')
        )
