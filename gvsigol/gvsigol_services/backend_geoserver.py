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
from gvsigol_core.geom import RASTER
from __builtin__ import False
'''
@author: Cesar Martinez <cmartinez@scolab.es>
'''

from models import Layer, LayerGroup, Datastore, Workspace, DataRule, LayerReadGroup, LayerWriteGroup
from gvsigol_symbology.models import Symbolizer, Style, Rule, StyleLayer
from gvsigol_symbology import services as symbology_services
from django.utils.translation import ugettext_lazy as _
from backend_postgis import Introspect
import xml.etree.ElementTree as ET
import geoserver.catalog as gscat
from geoserver.support import DimensionInfo
from gvsigol_core import geom
from gvsigol import settings
from zipfile import ZipFile
import tempfile, zipfile
import sys, os, shutil
import forms_geoserver
import rest_geoserver
from rest_geoserver import RequestError
import signals
import requests
import gdal_tools
import logging
import urllib
import random
import string
import json
import re
import unicodedata
from dbfread import DBF
import time
import utils
from builtins import str as text
from django.utils.html import escape, strip_tags

logger = logging.getLogger("gvsigol")
DEFAULT_REQUEST_TIMEOUT = 5

class UnsupportedRequestError(Exception):
    pass

class BadFormat(rest_geoserver.UploadError):
    pass

class WrongElevationPattern(rest_geoserver.UploadError):
    pass

class WrongTimePattern(rest_geoserver.UploadError):
    pass

class InvalidValue(rest_geoserver.RequestError):
    pass

class UserInputError(rest_geoserver.UploadError):
    pass

#_valid_sql_name_regex=re.compile("^[^\W\d][\w]*$")
_valid_sql_name_regex=re.compile("^[a-zA-Z_][a-zA-Z0-9_]*$")

"""
Types that can be created from gvSIG Online
"""
SUPPORTED_SQL_CREATION_TYPES = [ "character varying", "integer", "double precision", "boolean", "date", "time", "timestamp" ]
OTHER_SUPPORTED_SQL_TYPES = ["character", "text", "numeric"]

class Geoserver():
    CREATE_TYPE_SQL_VIEW = "gs_sql_view"
    CREATE_TYPE_VECTOR_LAYER = "gs_vector_layer"
    def __init__(self, id, default, name, user, password, master_node, slave_nodes):
        self.id = id
        self.default = default
        self.name = name
        self.conf_url = master_node
        self.rest_url = master_node + "/rest"
        self.gwc_url = master_node + "/gwc/rest"
        self.slave_nodes = slave_nodes
        self.rest_catalog = rest_geoserver.Geoserver(self.rest_url, self.gwc_url)
        self.user = user
        self.password = password
        self.supported_types = (
            ('v_PostGIS', _('PostGIS vector')),
            ('c_GeoTIFF', _('GeoTiff')),
            ('e_WMS', _('Cascading WMS')),
            ('c_ImageMosaic', _('ImageMosaic')),
        )

        if settings.OGR2OGR_PATH is not None and settings.OGR2OGR_PATH != '':
            gdal_tools.OGR2OGR_PATH = settings.OGR2OGR_PATH
        if settings.GDALSRSINFO_PATH is not None and settings.GDALSRSINFO_PATH != '':
            gdal_tools.GDALSRSINFO_PATH = settings.GDALSRSINFO_PATH
        if settings.GDALINFO_PATH is not None and settings.GDALINFO_PATH != '':
            gdal_tools.GDALINFO_PATH = settings.GDALINFO_PATH
         

        
        self.supported_srs_plain = [ x[0] for x in forms_geoserver.supported_srs ]
        self.supported_encodings_plain = [ x[0] for x in forms_geoserver.supported_encodings ]
        self.supported_postgis_geom_types = [ x[0] for x in forms_geoserver.geometry_types ]
        self.raster_extensions = [".jpg", ".jpeg", ".jpe", ".png", ".tif"]
        
        self.layer_create_types = ((Geoserver.CREATE_TYPE_VECTOR_LAYER, _("Vector layer")),
                                   (Geoserver.CREATE_TYPE_SQL_VIEW, _("SQL View")))
    
    def getGsconfig(self):
        return gscat.Catalog(self.rest_url, self.user, self.password, validate_ssl_certificate=False)
    
    
    def getSupportedTypes(self):
        return self.supported_types
    
    def getSupportedVectorTypes(self):
        return (
            ('v_PostGIS', _('PostGIS vector')),
            #('v_SHP', _('Shapefile folder')),       
        )

    def getSupportedUploadTypes(self):
        return self.supported_upload_types
    
    def getSupportedEncodings(self):
        return self.supported_encodings
    
    def getSupportedSRSs(self):
        return self.supported_SRSs
    
    def getSupportedFonts(self):
        return self.rest_catalog.get_fonts(user=self.user, password=self.password)
    
    def reload_master(self):
        self.rest_catalog.reload(self.conf_url, user=self.user, password=self.password) 
        
    def reload_node(self, node_url):
        try:
            self.rest_catalog.reload(node_url, user=self.user, password=self.password) 
            return True
        
        except Exception as e:
            print str(e)
            return False
        
    def reload_nodes(self):
        try:
            # get sequence from master
            us_master = self.rest_catalog.get_update_sequence(self.conf_url, user=self.user, password=self.password)
            print "INFO: Reloading Geoserver all nodes except master configured with IP FO in Aapche. Update Sequence = " + str(us_master)
            # reload all nodes except master
            if len(self.slave_nodes) > 0:
                time.sleep(settings.RELOAD_NODES_DELAY)
                for node in self.slave_nodes:
                    us =  self.rest_catalog.get_update_sequence(node, user=self.user, password=self.password)
                    if us != us_master:
                        print  "INFO: Reloading ... " + node + " with updatedSequence " + str(us) 
                        self.rest_catalog.reload(node, user=self.user, password=self.password)
            return True
        
        except Exception as e:
            print str(e)
            return False

    def reload_all_nodes(self):
        print "DEBUG: Reloading Geoserver nodes ......"
        try:
            if len(self.slave_nodes) > 0:
                for node in self.slave_nodes:
                    self.rest_catalog.reload(node, user=self.user, password=self.password)
            return True
        except Exception as e:
            print str(e)
            return False

        
    def createWorkspace(self, name, uri):
        try:
            self.getGsconfig().create_workspace(name, uri)
            return True
        except Exception as e:
            logger.exception("Error creating workspace");
            return False
        
    def getWorkspace(self, name):
        try:
            ws = self.getGsconfig().get_workspace(name)
            if ws is None: 
                return False
            else:
                return True
        except Exception as e:
            print str(e)
            return False
        
    def deleteWorkspace(self, workspace):
        """
        Deletes a workspace and all its associated resources
        """
        try:
            catalog = self.getGsconfig() 
            ws = catalog.get_workspace(workspace.name)
            catalog.delete(ws, recurse=True)
            return True
        except Exception as e:
            print str(e)
            return False
        
    def getConfUrl(self):
        return self.conf_url

    def createDatastore(self, workspace, type, name, description, connection_params):
        """
        Some valid drivers:
        '' (shape), 'PostGIS', 'WorldImage', 'ArcGrid', 'ImageMosaic', 'GeoTIFF'
        """
        try:
            format_nature=type[:1]
            driver=type[2:]
            params_dict = json.loads(connection_params)
            catalog = self.getGsconfig()
            if format_nature == "v": # vector
                if driver == "SHP":
                    driver = None
                elif driver == 'PostGIS':
                    sch = params_dict.get('schema', 'public')
                    params_dict['schema'] = sch
                    params_dict['Support on the fly geometry simplification'] = params_dict.get('Support on the fly geometry simplification', 'true')
                    params_dict['Loose bbox'] = params_dict.get('Loose bbox', 'true')
                    params_dict['Estimated extends'] = params_dict.get('Estimated extends', 'true')
                    params_dict['encode functions'] = params_dict.get('encode functions', 'true')
                    params_dict['Expose primary keys'] = params_dict.get('Expose primary keys', 'true')
                utils.create_schema_for_datastore(params_dict)
                ds = catalog.create_datastore(name, workspace.name)
                ds.connection_parameters.update(params_dict)
                
            elif format_nature == "c": # coverage (raster)
                if driver == "GeoTIFF":
                    ds = catalog.create_coveragestore(name, workspace=workspace, path=params_dict.get('url'),create_layer=False)
                    #ds.url = params_dict.get('url')
                if driver == "ImageMosaic":
                    ele_regex = params_dict.get('ele_regex', '')
                    date_regex = params_dict.get('date_regex', '')
                    ele_format = params_dict.get('ele_format', '')
                    date_format = params_dict.get('date_format', '')
                    file_path = params_dict.get('url')
                    self.__process_image_mosaic_folder(name, file_path, date_regex, date_format, ele_regex, ele_format)
                    ds = catalog.create_coveragestore(name, workspace.name, path=file_path,create_layer=False)
                    ds.url = params_dict.get('url')
            elif format_nature == "e": # cascading wms
                wmsuser = params_dict.get('username')
                wmspassword = params_dict.get('password')
                self.rest_catalog.create_wmsstore(escape(workspace.name), escape(name), escape(params_dict.get('url')), escape(wmsuser), escape(wmspassword), self.user, self.password)
                return True
            
            else:
                # unsupported
                return False
            ds.description = description # description is ignored by gsconfig at the moment
            ds.type = driver
            response = catalog.save(ds) # FIXME: we should check response.status to ensure the operation was correct
            return True
        except Exception as e:
            logger.exception("Error creating datastore")
            print "Backend MapService - createDatastore Error", e
            return False
        
    def datastore_exists(self, workspace, name):
        try:
            if self.getGsconfig().get_store(name, workspace=workspace):
                return True
        except:
            pass
        return False
    
    def resource_exists(self, workspace, name):
        try:
            if self.getGsconfig().get_resource(name, None, workspace):
                return True
        except Exception as e:
            pass
        return False

    def updateDatastore(self, wsname, dsname, description, dstype, conn_params):
        try:
            format_nature=dstype[:1]
            driver=dstype[2:]
            catalog = self.getGsconfig()
            ds = catalog.get_store(dsname, wsname)
            params_dict = json.loads(conn_params)
            if format_nature == "v": # vector
                # directly updating connection_parameters won't work, we need to set the dict again
                params = ds.connection_parameters
                params.update(params_dict)
                ds.connection_parameters = params
                utils.create_schema_for_datastore(params_dict)
                
            elif format_nature == "c": # coverage (raster)
                if driver == "GeoTIFF":
                    ds.url = params_dict.get('url')
                if driver == "ImageMosaic":
                    ele_regex = params_dict.get('ele_regex', '')
                    date_regex = params_dict.get('date_regex', '')
                    ele_format = params_dict.get('ele_format', '')
                    date_format = params_dict.get('date_format', '')
                    file_path = params_dict.get('url')
                    self.__process_image_mosaic_folder(dsname, file_path, date_regex, date_format, ele_regex, ele_format)
                    ds.url = params_dict.get('url')
                
            elif format_nature == "e": # cascading wms
                self.rest_catalog.update_wmsstore(wsname,
                                                   dsname,
                                                   params_dict.get('url'),
                                                   params_dict.get('username', ''),
                                                   params_dict.get('password', ''),
                                                   self.user,
                                                   self.password)
                return True
            
            catalog.save(ds)
            return True
        except Exception as exc:
            logger.exception("Error updating wmsstore")
            print exc
            return False
    
    def deleteDatastore(self, workspace, datastore, delete_schema, purge=None):
        """
        Deletes a datastore and all its associated resources
        """
        catalog = self.getGsconfig()
        ds = catalog.get_store(datastore.name, workspace=workspace.name)
        if ds:
            if datastore.type=="c_ImageMosaic":
                try:
                    catalog.delete(ds, purge, recurse=True)
                except Exception as e:
                    pass
                return True
            else:
                catalog.delete(ds, purge, recurse=True)
                if delete_schema:
                    utils.delete_schema_for_datastore(json.loads(datastore.connection_params))
                
            return True
        else:
            return False
        
    def getStyles(self):
        try:                    
            styles = self.getGsconfig().get_styles(workspace=None)                   
            return styles
        
        except:
            e = sys.exc_info()[0]
            # FIXME: raise an exception
            return []
        
    def getStyle(self, style_name):
        try:
            style = self.getGsconfig().get_style(style_name, workspace=None)
            return style
        
        except:
            e = sys.exc_info()[0]
            pass
        
    def setLayerStyle(self, layer, style, is_default):
        """
        Set default style
        """
        try:
            layer_name = layer.datastore.workspace.name + ":" + layer.name
            catalog = self.getGsconfig()
            gs_layer = catalog.get_layer(layer_name)
            #styles = gs_layer._get_alternate_styles()
            #styles.append(style)
            self.addStyle(layer, layer_name, style)
            if is_default:
                gs_layer.default_style = style
            catalog.save(gs_layer)
            
            return True
        except Exception as e:
            logger.exception("error setting style", e)
            return False
        
    def get_geometry_type(self, layer):
        try:           
            datastore = Datastore.objects.get(id=layer.datastore_id)
            if layer.type == 'v_PostGIS' or layer.type == 'v_PostGIS_View':
                workspace = Workspace.objects.get(id=datastore.workspace_id)
                result = self.rest_catalog.get_feature_type(workspace.name, datastore.name, layer.name, user=self.user, password=self.password)
                attr_list = result['featureType']['attributes']['attribute']
                for attr in attr_list:
                    geom_type = geom.fromJTS(attr['binding'])
                    if geom_type != None:
                        return geom_type
            else:
                return 'raster'
        
        except Exception as e:
            logger.exception("error getting geometry type", e)
            return False
    
    def get_feature_type(self, workspace, datastore, name, title):
        """
        """
        try:           
            result = self.rest_catalog.get_feature_type(workspace, datastore, name, user=self.user, password=self.password)
            return result
        
        except Exception as e:
            logger.exception("Error retrieving geometry info")
            return None
    
    def get_geometry_info(self, layer, as_srid=True):
        """
        Returns an object containing the geometry the_type and the SRS of the layer.
        Example: {'geomtype': 'Polygon', 'srs': 4326} 
        
        :param layer: A Layer django object
        :param as_srid: If True, it returns a numeric EPSG code. If False, it returns
              an string SRS definition (exactly as defined in the map service). 
        """
        try:           
            datastore = Datastore.objects.get(id=layer.datastore_id)
            the_type = "unknown"
            if layer.type == 'v_PostGIS' or layer.type == 'v_PostGIS_View':
                workspace = Workspace.objects.get(id=datastore.workspace_id)
                result = self.rest_catalog.get_feature_type(workspace.name, datastore.name, layer.name, user=self.user, password=self.password)
                attr_list = result['featureType']['attributes']['attribute']
                for attr in attr_list:
                    geom_type = geom.fromJTS(attr['binding'])
                    if geom_type != None:
                        the_type = geom_type
                        break;
            else:
                the_type = 'raster'
            srs = result['featureType']['srs']
            if as_srid:
                srs = geom.epsgToSrid(srs)
            return {"geomtype": the_type, "srs": srs}
        
        except Exception as e:
            logger.error("Error retrieving geometry info")
            return None
    
    def createDefaultStyle(self, layer, style_name):
        geom_type = self.get_geometry_type(layer)
        logging.basicConfig(level=logging.INFO)
        logger.info('[backend_mapserver] Creando el estilo por defecto para layer: ' + layer.name + ' (' + str(geom_type) + ')')
        
        
        style_type = 'US'
        
        aux = None
        try:
            if geom_type == RASTER:
                style_type = 'CT'
            else:  
                params = json.loads(layer.datastore.connection_params)
                host = params['host']
                port = params['port']
                dbname = params['database']
                user = params['user']
                passwd = params['passwd']
                schema = params.get('schema', 'public')
                
                i = Introspect(database=dbname, host=host, port=port, user=user, password=passwd)
                count = i.get_estimated_count(schema, layer.name)
                aux = count[0]
                i.close()
                
            sld_body = symbology_services.create_default_style(layer.id, style_name, style_type, geom_type, aux)
        
        except Exception as ex:
                logger.exception('Creando el estilo por defecto para layer: ' + layer.name + ' (' + str(geom_type) + ')')
                print str(ex.message)
                return False
     
        try:
            catalog = self.getGsconfig()
            if catalog.get_style(style_name, workspace=None) == None:
                catalog.create_style(style_name, sld_body.encode('utf-8'), overwrite=False, workspace=None, style_format="sld10", raw=False)
                    
            return True
        
        except Exception as e:
            logger.exception('Creando el estilo por defecto para layer: ' + layer.name + ' (' + str(geom_type) + ')')
            return False
    
    def createOverwrittenStyle(self, name, data, overwrite):
        """
        Create new style
        """
        try:
            self.getGsconfig().create_style(name, data.encode('utf-8'), overwrite=overwrite, workspace=None, style_format="sld10", raw=False)
            return True
        
        except Exception as e:
            logger.exception('Sobreescribiendo estilo: ' + name)
            return False
    
    def createStyle(self, name, data):
        return self.createOverwrittenStyle(name, data, False)
        
    def addStyle(self, layer, layer_name, name):
        """
        Add new style to layer
        """
        self.rest_catalog.add_style(layer_name, name, user=self.user, password=self.password)
        if layer is not None:
            style_list = []
            default_style = ''
            style_layers = StyleLayer.objects.filter(layer=layer)
            for style_layer in style_layers:
                if not style_layer.style.name.endswith('_tmp'):
                    style_list.append(style_layer.style.name)
                if style_layer.style.is_default:
                    default_style = style_layer.style.name
                            
            self.rest_catalog.update_layer_styles_configuration(layer, name, default_style, style_list, user=self.user, password=self.password)
        
    def updateStyle(self, layer, style_name, sld_body):
        """
        Update a style
        """
            
        try:
            self.rest_catalog.update_style(style_name, sld_body, user=self.user, password=self.password)
            if layer is not None:
                style_list = []
                default_style = ''
                style_layers = StyleLayer.objects.filter(layer=layer)
                for style_layer in style_layers:
                    if not style_layer.style.name.endswith('_tmp'):
                        style_list.append(style_layer.style.name)
                    if style_layer.style.is_default:
                        default_style = style_layer.style.name
                                
                self.rest_catalog.update_layer_styles_configuration(layer, style_name, default_style, style_list, user=self.user, password=self.password)
                self.updateThumbnail(layer, 'update')
            return True
        except RequestError as e:
            logger.exception('Updating style: ' + style_name)
            logger.error(e.get_detailed_message())
        except Exception as e:
            logger.exception('Updating style: ' + style_name)
        return False
        
    def updateThumbnail(self, layer, mode='update'):
        if not 'no_thumbnail.jpg' in layer.thumbnail.name:
            if os.path.isfile(layer.thumbnail.path):
                os.remove(layer.thumbnail.path)
        
        try:   
            layer.thumbnail = self.getThumbnail(layer.datastore.workspace, layer.datastore, layer)
            layer.save()
            if mode == 'create':
                signals.layer_created.send(sender=None, layer=layer)
                
            elif mode == 'update':
                signals.layer_updated.send(sender=None, layer=layer)
                
            return layer
        
        except Exception as e:
            logger.exception('Actualizando thumbnail: ' + layer.name)
            pass
        
    def deleteStyle(self, name):
        try:
            catalog = self.getGsconfig()
            style = catalog.get_style(name, workspace=None)
            if style is None:
                logger.warn(u'gvsigol style was not found in Geoserver:' + text(name))
            else:
                catalog.delete(style, purge=True, recurse=True)
            return True
        except Exception as e:
            logger.exception('Borrando estilo: ' + name)
            raise
        
    def deleteLayerStyles(self, lyr):
        try:
            layer_styles = StyleLayer.objects.filter(layer=lyr)
    
            for layer_style in layer_styles:
                style = Style.objects.get(id=layer_style.style_id)
                catalog = self.getGsconfig()
                gs_style = catalog.get_style(style.name, workspace=None)
                catalog.delete(gs_style, purge=True, recurse=True)
                layer_style.delete()
                
                rules = Rule.objects.filter(style=style)
                for rule in rules:
                    symbolizers = Symbolizer.objects.filter(rule=rule)
                    for symbolizer in symbolizers:
                        if hasattr(symbolizer, 'rastersymbolizer'):
                            symbolizer.rastersymbolizer.color_map.delete()
                        symbolizer.delete()
                    rule.delete()
                
                style.delete()
                
            return True
        
        except Exception as e:
            logger.exception('Borrando estilos de capa: ' + lyr.name)
            return False
        
    def updateBoundingBoxFromData(self, layer):
        store = layer.datastore
        if store.type[0]=="v":
            self.rest_catalog.update_ft_bounding_box(layer.datastore.workspace.name, layer.datastore.name, layer.name, user=self.user, password=self.password)
        # not available/necessary for coverages

    def reload_featuretype(self, layer, attributes=True, nativeBoundingBox=True, latLonBoundingBox=True):
        """
        Reload the feature type config in Geoserver based on the table structure in the database and the data
        in the table.
        For the moment, the following elements are supported:
        - attributes
        - nativeBoundingBox
        - latLonBoundingBox
        """
        updated_params = {}
        conn, tablename, schema = utils.get_db_connect_from_layer(layer)
        if attributes:
            new_attrs = self._featuretype_attributes(conn, schema, tablename)
            updated_params['attributes'] = {'attribute': new_attrs}
        conn.close()
        self.rest_catalog.update_featuretype(layer.datastore.workspace.name, layer.datastore.name, layer.source_name, updated_params=updated_params, nativeBoundingBox=nativeBoundingBox, latLonBoundingBox=latLonBoundingBox, user=self.user, password=self.password)

    def getGeoserverBindings(self, sql_type):
        if sql_type in ["character varying", "character", "text", "cd_json"]:
            return "java.lang.String"
        elif sql_type in ["integer"]:
            return "java.lang.Integer"
        elif sql_type in ["double precision", "double"]:
            return "java.lang.Double"
        elif sql_type == "numeric":
            return "java.math.BigDecimal"
        elif sql_type == "boolean":
            return "java.lang.Boolean"
        elif sql_type == "date":
            return "java.sql.Date"
        elif sql_type in ["time without time zone", "time"]:
            return "java.sql.Time"
        elif sql_type in ["timestamp without time zone", "timestamp"]:
            return "java.sql.Timestamp"
        sql_type = sql_type.upper()
        if sql_type == "POINT":
            """
            Note: Geoserver 2.14 migrated from com.vividsolutions.jts.geom JTS packages to 
                    org.locationtech.jts.geom packages. However, the old namespace is still
                    accepted by the REST API.
            """
            return 'com.vividsolutions.jts.geom.Point'
        elif sql_type == "MULTIPOINT":
            return 'com.vividsolutions.jts.geom.MultiPoint'
        elif sql_type == "LINESTRING":
            return 'com.vividsolutions.jts.geom.LineString'
        elif sql_type == "MULTILINESTRING":
            return 'com.vividsolutions.jts.geom.MultiLineString'
        elif sql_type == "POLYGON":
            return 'com.vividsolutions.jts.geom.Polygon'
        elif sql_type == "MULTIPOLYGON":
            return 'com.vividsolutions.jts.geom.MultiPolygon'

    def createResource(self, workspace, store, name, title, extraParams={}):
        try:
            if store.type[0]=="v":
                return self.createFeaturetype(workspace, store, name, title, extraParams)
            elif store.type[0]=="e":
                return self.createWMSLayer(workspace, store, name, title)
            else:
                if store.type == 'c_ImageMosaic':
                    #got_params = json.loads(store.connection_params)
                    #mosaic_url = got_params["url"].replace("file://", "")
                    #split_mosaic_url = mosaic_url.split("/")
                    #coverage_name = split_mosaic_url[split_mosaic_url.__len__()-1]
                    coverage_name = store.name
                    return self.createImageMosaicLayer(workspace, store, name, title, coverage_name)
                else:    
                    return self.createCoverage(workspace, store, name, title)   
        except Exception as e:
            logger.exception('Creando capa: ' + name)
            raise rest_geoserver.FailedRequestError(-1, str(e.server_message))
        
    def getFeaturetype(self, workspace, datastore, name, title):
        return self.rest_catalog.get_feature_type(workspace.name, datastore.name, name, user=self.user, password=self.password)

    def createFeaturetype(self, workspace, datastore, name, title, extraParams={}):
        try:
            return self.rest_catalog.create_feature_type(name, title, datastore.name, workspace.name, user=self.user, password=self.password, extraParams=extraParams)
        except rest_geoserver.FailedRequestError as e:
            logger.exception('ERROR createFeatureType failed: ' + name)
            raise rest_geoserver.FailedRequestError(e.status_code, _("Error publishing the layer. Backend error: {msg}").format(msg=e.get_message()))
        except Exception as e:
            logger.exception('ERROR createFeatureType failed: ' + name)
            raise rest_geoserver.FailedRequestError(-1, _("Error: layer could not be published"))
        
    def createImageMosaic(self, workspace, store, name, title):
        try:
            params = json.loads(store.connection_params)
            file = params['url']
            split_mosaic_url = file.split("/")
            mosaic_name = split_mosaic_url[split_mosaic_url.__len__()-1]
            return self.rest_catalog.create_coveragestore(workspace.name, store.name, 'ImageMosaic', file, mosaic_name, user=self.user, password=self.password)
            #return self.rest_catalog.create_coverage(name, title, coveragestore.name, workspace.name, user=self.user, password=self.password)                                           
        except rest_geoserver.FailedRequestError as e:
            logger.exception('ERROR createImageMosaic failed: ' + name)
            raise rest_geoserver.FailedRequestError(e.status_code, _("Error publishing the layer. Backend error: {msg}").format(msg=e.get_message()))
        except Exception as e:
            logger.exception('ERROR createImageMosaic failed: ' + name)
            raise rest_geoserver.FailedRequestError(-1, _("Error: layer could not be published"))
        
    def createImageMosaicLayer(self, workspace, store, name, title, coverage_name):
        try:
            result = self.rest_catalog.create_coveragestore_layer(workspace.name, store.name, name, title, coverage_name, user=self.user, password=self.password)
            return result
            #return self.rest_catalog.create_coverage(name, title, coveragestore.name, workspace.name, user=self.user, password=self.password)                                           
        except rest_geoserver.FailedRequestError as e:
            logger.exception('ERROR createImageMosaicLayer failed. Name ' + name + ' - Store: ' + store.name)
            raise rest_geoserver.FailedRequestError(e.status_code, _("Error publishing the layer. Backend error: {msg}").format(msg=e.get_message()))
        except Exception as e:
            logger.exception('ERROR createImageMosaicLayer failed. Name ' + name + ' - Store: ' + store.name)
            raise rest_geoserver.FailedRequestError(-1, _("Error: layer could not be published") + ": Error " + str(e.status_code) + " - " + e.server_message)
    
    def updateImageMosaicTemporal(self, store, layer):
        try:
            self.createimagemosaic(store, layer)
        except rest_geoserver.FailedRequestError as e:
            logger.exception('ERROR updateImageMosaicTemporal failed. Layer ' + layer.name + ' - Store: ' + store.name)
            raise rest_geoserver.FailedRequestError(e.status_code, _("Error publishing the layer. Backend error: {msg}").format(msg=e.get_message()))
        except Exception as e:
            logger.exception('ERROR updateImageMosaicTemporal failed. Layer ' + layer.name + ' - Store: ' + store.name)
            raise rest_geoserver.FailedRequestError(-1, _("Error: layer could not be published"))
    
    
    def uploadImageMosaic(self, workspace, store):
        try:
            return self.rest_catalog.upload_coveragestore(workspace.name, store.name, user=self.user, password=self.password)
        except rest_geoserver.FailedRequestError as e:
            raise rest_geoserver.FailedRequestError(e.status_code, _("Error publishing the layer. Backend error: {msg}").format(msg=e.get_message()))
        except Exception as e:
            raise rest_geoserver.FailedRequestError(-1, _("Error: layer could not be published"))
    
    def createCoverage(self, workspace, coveragestore, name, title):
        try:
            return self.rest_catalog.create_coverage(name, title, coveragestore.name, workspace.name, user=self.user, password=self.password)
        except rest_geoserver.FailedRequestError as e:
            logger.exception('ERROR createCoverage failed. Layer: ' + name + ' - Store: ' + coveragestore.name)
            raise rest_geoserver.FailedRequestError(e.status_code, _("Error publishing the layer. Backend error: {msg}").format(msg=e.get_message()))
        except Exception as e:
            logger.exception('ERROR createCoverage failed. Layer: ' + name + ' - Store: ' + coveragestore.name)
            raise rest_geoserver.FailedRequestError(-1, _("Error: layer could not be published"))
    
    def createWMSLayer(self, workspace, store, name, title):
        try:   
            catalog = self.getGsconfig()
            ws = catalog.get_workspace(workspace.name)
            dst = catalog.get_store(store.name, ws)
            return catalog.create_wmslayer(ws, dst, name, name)

        except rest_geoserver.FailedRequestError as e:
            raise rest_geoserver.FailedRequestError(e.status_code, _("Error publishing the layer. Backend error: {msg}").format(msg=e.get_message()))
        except Exception as e:
            raise rest_geoserver.FailedRequestError(-1, _("Error: layer could not be published"))
        
    #TODO: este metodo recrea el grupo de capas en Geoserver a partir de la informacion que hay en el modelo. Se deberian implementar los metodos
    # que anyaden o borran capas de un grupo para ser mas eficiente.    
    def createOrUpdateGeoserverLayerGroup(self, layer_group):
        try:
            if layer_group.name != "__default__":
                return self.rest_catalog.create_or_update_gs_layer_group(layer_group.name, layer_group.title, user=self.user, password=self.password)
            return True
        except rest_geoserver.FailedRequestError as e:
            logger.exception('ERROR createOrUpdateGeoserverLayerGroup failed. Group name: ' + layer_group.name)
            raise rest_geoserver.FailedRequestError(e.status_code, _("Error publishing the layer group. Backend error: {msg}").format(msg=e.get_message()))
        except Exception as e:
            logger.exception('ERROR createOrUpdateGeoserverLayerGroup failed. Group name: ' + layer_group.name)
            raise rest_geoserver.FailedRequestError(-1, _("Error: layer group could not be published"))
        
    def createOrUpdateSortedGeoserverLayerGroup(self, toc):
        try:
            return self.rest_catalog.create_or_update_sorted_gs_layer_group(toc, user=self.user, password=self.password)
        except rest_geoserver.FailedRequestError as e:
            raise rest_geoserver.FailedRequestError(e.status_code, _("Error publishing the layer group. Backend error: {msg}").format(msg=e.get_message()))
        except Exception as e:
            logger.exception('ERROR createOrUpdateSortedGeoserverLayerGroup failed')
            raise rest_geoserver.FailedRequestError(-1, _("Error: layer group could not be published"))
        
    def deleteGeoserverLayerGroup(self, layer_group):
        try:
            return self.rest_catalog.delete_gs_layer_group(layer_group, user=self.user, password=self.password)
        except rest_geoserver.FailedRequestError as e:
            logger.exception('ERROR deleteGeoserverLayerGroup')
            raise rest_geoserver.FailedRequestError(e.status_code, _("Error publishing the layer group. Backend error: {msg}").format(msg=e.get_message()))
        except Exception as e:
            logger.exception('ERROR deleteGeoserverLayerGroup')
            raise rest_geoserver.FailedRequestError(-1, _("Error: layer group could not be published"))
    
    def deleteResource(self, workspace, datastore, layer, purge=None):
        try:
            catalog = self.getGsconfig()
            resource = catalog.get_resource(layer.name, datastore.name, workspace.name)
            # FIXME: should we purge the resource (i.e. delete the layer on disk/db)?
            if resource is not None:
                try:
                    catalog.delete(resource, purge, True)
                except Exception as e:
                    # only fail if layer exists but deletion failed
                    logger.exception('ERROR deleteResource. Layer:' + layer.name)
                    pass
        except Exception as e:
            # only fail if layer exists but deletion failed
            logger.exception('ERROR deleteResource. Layer:' + layer.name)
            pass
        
        return True

    def updateResource(self, workspace, ds_name, ds_type, name, updatedParams={}):
        try:
            if ds_type.startswith('v_'): # vector
                self.rest_catalog.update_featuretype(workspace, ds_name, name, updatedParams=updatedParams, user=self.user, password=self.password)
            else: # raster, external layer, etc
                title = updatedParams.get('title')
                if title:
                    catalog = self.getGsconfig()
                    resource = catalog.get_resource(name, ds_name, workspace)
                    resource.name = name
                    resource.title = title
                    catalog.save(resource)
            return True
        except:
            logger.exception('ERROR updateResource. Resource:' + name)
            return False
    
    def setQueryable(self, workspace, ds_name, ds_type, name, queryable):
        try:
            return self.rest_catalog.set_queryable(workspace, ds_name, ds_type, name, queryable, user=self.user, password=self.password)
        except rest_geoserver.FailedRequestError as e:
            print ("ERROR: setQueryable failedrequest exception: " + e.get_message())
            raise rest_geoserver.FailedRequestError(e.status_code, _("Error changing property. Backend error: {msg}").format(msg=e.get_message()))
        except Exception as e:
            print ("ERROR: failedrequest unknown exception: " + str(e))
            raise rest_geoserver.FailedRequestError(-1, _("Error: layer could not be updated"))
            
    def setTimeEnabled(self, workspace, ds_name, ds_type, name, time_enabled, time_field, time_endfield, presentation, resolution, default_value_mode, default_value):
        try:
            return self.rest_catalog.set_time_dimension(workspace, ds_name, ds_type, name, time_enabled, time_field, time_endfield, presentation, resolution, default_value_mode, default_value, user=self.user, password=self.password)
        except rest_geoserver.FailedRequestError as e:
            print ("ERROR: setQueryable failedrequest exception: " + e.get_message())
            raise rest_geoserver.FailedRequestError(e.status_code, _("Error changing property. Backend error: {msg}").format(msg=e.get_message()))
        except Exception as e:
            print ("ERROR: failedrequest unknown exception: " + str(e))
            raise rest_geoserver.FailedRequestError(-1, _("Error: layer could not be updated"))

    def _get_unique_resource_name(self, datastore, workspace):
        name = datastore
        i = 0
        while self.getGsconfig().get_resource(name, None, workspace):
            name = datastore + str(i)
            i = i + 1
        return name     
     
    def getDataStores(self, workspace):
        ws = self.getGsconfig().get_workspace(workspace.name)
        stores = self.getGsconfig().get_stores(workspaces=ws)
        resources = []
        for store in stores:
            resources.append(store.name)
        return resources

    def getResources(self, workspace, datastore, type):
        try:
            available = False
            if type == 'available' or type == 'available_with_geom':
                available = True
            store = self.getGsconfig().get_store(datastore.name, workspace.name)
            format_nature=datastore.type[0]
            if (format_nature=='v'):
                return self.rest_catalog.get_resources(workspace.name, datastore.name, type, self.user, self.password)
                #return store.get_resources(available=available)
            elif (format_nature=='c'):
                driver=datastore.type[2:]
                resources_obj = store.get_resources()
                # The API doesn't allow to retrieve the available coverages nor their names,
                # but these drivers allow a single coverage to be published on the coverage store
                if len(resources_obj) > 0:
                    # there is no available coverages if they is already one published coverage
                    return []
                else:
                    # we can't get the name of the coverage, so we just offer a sensible, non existing name
                    return [self._get_unique_resource_name(datastore.name, workspace.name)]
            elif (format_nature=='e'):
                return store.get_resources(available=available)
            
        except Exception as ex:
            logger.exception("Error getting resources")
            print str(ex)
            pass 
    
         
    def getResource(self, workspace, datastore, resource):
        resource_obj = self.getGsconfig().get_resource(resource, datastore, workspace)
        if resource_obj:
            return resource_obj.attributes
        
        return None

  
    def getResourceInfo(self, workspace, store, featureType, type):
        if type == None:
            type = "json"
            
        url = None
        if store.type == 'v_PostGIS':
            url = self.rest_catalog.service_url + "/workspaces/" + workspace + "/datastores/" + store.name + "/featuretypes/" + featureType +"."+type
            ds_type = 'featureType'
        elif store.type == 'e_WMS':
            url = self.rest_catalog.service_url + "/workspaces/" + workspace + "/wmsstores/" + store.name + "/wmslayers/" + featureType +"."+type
            ds_type = 'wmsLayer'
        elif store.type == 'c_GeoTIFF':
            url = self.rest_catalog.service_url + "/workspaces/" + workspace + "/coveragestores/" + store.name + "/coverages/" + featureType +"."+type
            ds_type = 'coverage'
        elif store.type == 'c_ImageMosaic':
            url = self.rest_catalog.service_url + "/workspaces/" + workspace + "/coveragestores/" + store.name + "/coverages/" + featureType +"."+type
            ds_type = 'imagemosaic'
        
        r = self.rest_catalog.session.get(url, auth=(self.user, self.password), timeout=DEFAULT_REQUEST_TIMEOUT)
        if r.status_code==200:
            content = r.content
            jsonData = json.loads(content)
            return [ds_type, jsonData]
        
        return None

    def getLayerCreateTypes(self):
        return self.layer_create_types
    
    def getLayerCreateForm(self, layer_type, user):
        if layer_type==Geoserver.CREATE_TYPE_SQL_VIEW:
            return (forms_geoserver.CreateSqlViewForm,  "layer_sql_view.html")
        if layer_type==Geoserver.CREATE_TYPE_VECTOR_LAYER:
            return (forms_geoserver.CreateFeatureTypeForm(user=user),  "layer_create.html")
        return (None, None)
    
    def getUploadForm(self, datastore_type, user):
        # ensure type is a supported data store type
        if datastore_type=="c_GeoTIFF":
            return forms_geoserver.RasterLayerUploadForm
        elif datastore_type=="c_ImageMosaic":
            return forms_geoserver.ImageMosaicUploadForm
        elif datastore_type=="v_PostGIS":
            return forms_geoserver.PostgisLayerUploadForm(user=user)
        
    def __is_raster_file(self, f):
        ext = os.path.splitext(f)[1].lower()
        return (ext in self.raster_extensions)
               
        
    def __gdal_info_stats(self, file_path):
        # if file_path is a folder:
        #     compute stats for each image found on the path
        # else:
        #     compute stats for file_path
        if os.path.isdir(file_path):
            # Compute stats for each image found on the path
            # and return the global min and max for each band
            # It is assumed that all the rasters have the same
            # number of bands!!
            global_stats = None
            for f in os.listdir(file_path):
                if self.__is_raster_file(f):
                    file_stats = self.__gdal_info_stats(os.path.join(file_path, f))
                    num_bands = len(file_stats)
                    if global_stats == None:
                        global_stats = [None for i in range(0, num_bands)]
                    for idx,band_stats in enumerate(file_stats):
                        if global_stats[idx] == None:
                            global_stats[idx] = (band_stats[0], band_stats[1], None, None)
                        else:
                            if band_stats[0] < global_stats[idx][0]:
                                minimum = band_stats[0]
                            else:
                                minimum =  global_stats[idx][0]
                            if band_stats[1] > global_stats[idx][1]:
                                maximum = band_stats[1]
                            else:
                                maximum = global_stats[idx][1]
                            global_stats[idx] = (minimum, maximum, None, None)
            return global_stats if global_stats else (None, None, None, None)
        elif os.path.isfile(file_path):
            try:
                return gdal_tools.get_raster_stats(file_path)
            except gdal_tools.GdalError as e:
                raise rest_geoserver.RequestError(e.code, e.message)    


    def __update_raster_stats(self, workspace, coveragestore, coverage, old_conf, stats):
        try:
            dimensions = old_conf["coverage"]["dimensions"]["coverageDimension"]
            for idx, d in enumerate(dimensions):
                #d["@class"] = "org.geoserver.catalog.CoverageDimensionInfo"
                d["description"] = "GridSampleDimension[" + str(stats[idx][0]) + "," + str(stats[idx][1]) + "]"
                d["range"] = {"min":stats[idx][0], "max": stats[idx][1]}
            #conf = { "coverage": { "dimensions": {"coverageDimension": dimensions }}}
            self.rest_catalog.update_coverage(workspace, coveragestore, coverage, old_conf, user=self.user, password=self.password)
            
        except rest_geoserver.RequestError as e:
            logging.error("__update_raster_stats failed!! Layer: " + coverage)
            logging.error(e.get_message())
        except Exception as e:
            logging.error("__update_raster_stats failed!! Layer: " + coverage)
            print "__update_raster_stats failed!!"
            print e
            pass
    
    def __do_upload_postgis(self, name, datastore, form_data, zip_path):
        tmp_dir = None
        try: 
            # get & sanitize parameters
            srs = form_data.get('srs')
            encoding = form_data.get('encoding')
            creation_mode = form_data.get('mode')
            if not encoding in self.supported_encodings_plain or not srs in self.supported_srs_plain:
                raise rest_geoserver.RequestError()
            # FIXME: sanitize connection parameters too!!!
            # We are going to perform a command line execution with them,
            # so we must be ABSOLUTELY sure that no code injection can be
            # performed
            ds_params = json.loads(datastore.connection_params) 
            db = ds_params.get('database')
            host = ds_params.get('host')
            port = ds_params.get('port')
            schema = ds_params.get('schema', "public")
            port = str(int(port))
            user = ds_params.get('user')
            password = ds_params.get('passwd')
            if _valid_sql_name_regex.search(name) == None:
                raise InvalidValue(-1, _("Invalid layer name: '{value}'. Identifiers must begin with a letter or an underscore (_). Subsequent characters can be letters, underscores or numbers").format(value=name))
            if _valid_sql_name_regex.search(db) == None:
                raise InvalidValue(-1, _("The connection parameters contain an invalid database name: {value}. Identifiers must begin with a letter or an underscore (_). Subsequent characters can be letters, underscores or numbers").format(value=db))
            if _valid_sql_name_regex.search(user) == None:
                raise InvalidValue(-1, _("The connection parameters contain an invalid user name: {value}. Identifiers must begin with a letter or an underscore (_). Subsequent characters can be letters, underscores or numbers").format(value=db))
            if _valid_sql_name_regex.search(schema) == None:
                raise InvalidValue(-1, _("The connection parameters contain an invalid schema: {value}. Identifiers must begin with a letter or an underscore (_). Subsequent characters can be letters, underscores or numbers").format(value=db)) 

            # extract SHP
            tmp_dir = tempfile.mkdtemp()
            with ZipFile(zip_path, 'r') as z:
                z.extractall(tmp_dir)
            files = [f for f in os.listdir(tmp_dir) if f.lower()[-4:]==".shp"]
            
            # import SHP to DB
            if len(files)==1:
                shp_abs = os.path.join(tmp_dir, files[0])
                gdal_tools.shp2postgis(shp_abs, name, srs, host, port, db, schema, user, password, creation_mode, encoding)
                return
        except (rest_geoserver.RequestError):
            raise 
        except gdal_tools.GdalError as e:
            raise rest_geoserver.RequestError(e.code, e.message)
        except Exception as e:
            logging.exception(e)
        finally:
            if tmp_dir:
                shutil.rmtree(tmp_dir, ignore_errors=True)
        raise rest_geoserver.RequestError(-1, _("Error uploading the layer. Review the file format."))
    
    def __do_export_to_postgis(self, name, datastore, form_data, shp_path):
        try: 
            # get & sanitize parameters
            srs = form_data.get('srs')
            encoding = form_data.get('encoding')
            creation_mode = form_data.get('mode')
            if not encoding in self.supported_encodings_plain or not srs in self.supported_srs_plain:
                raise rest_geoserver.RequestError()
            # FIXME: sanitize connection parameters too!!!
            # We are going to perform a command line execution with them,
            # so we must be ABSOLUTELY sure that no code injection can be
            # performed
            ds_params = json.loads(datastore.connection_params) 
            db = ds_params.get('database')
            host = ds_params.get('host')
            port = ds_params.get('port')
            schema = ds_params.get('schema', "public")
            port = str(int(port))
            user = ds_params.get('user')
            password = ds_params.get('passwd')
            if _valid_sql_name_regex.search(name) == None:
                raise InvalidValue(-1, _("Invalid layer name: '{value}'. Identifiers must begin with a letter or an underscore (_). Subsequent characters can be letters, underscores or numbers").format(value=name))
            if _valid_sql_name_regex.search(db) == None:
                raise InvalidValue(-1, _("The connection parameters contain an invalid database name: {value}. Identifiers must begin with a letter or an underscore (_). Subsequent characters can be letters, underscores or numbers").format(value=db))
            if _valid_sql_name_regex.search(user) == None:
                raise InvalidValue(-1, _("The connection parameters contain an invalid user name: {value}. Identifiers must begin with a letter or an underscore (_). Subsequent characters can be letters, underscores or numbers").format(value=db))
            if _valid_sql_name_regex.search(schema) == None:
                raise InvalidValue(-1, _("The connection parameters contain an invalid schema: {value}. Identifiers must begin with a letter or an underscore (_). Subsequent characters can be letters, underscores or numbers").format(value=db)) 

            gdal_tools.shp2postgis(shp_path, name, srs, host, port, db, schema, user, password, creation_mode, encoding)
            return True
        
        except (rest_geoserver.RequestError):
            raise 
        except gdal_tools.GdalError as e:
            if e.code == 1:
                params = json.loads(datastore.connection_params)
                host = params['host']
                port = params['port']
                dbname = params['database']
                user = params['user']
                passwd = params['passwd']
                schema = params.get('schema', 'public')
                i = Introspect(database=dbname, host=host, port=port, user=user, password=passwd)
                i.delete_table(schema, name)
                i.close()
                
            raise rest_geoserver.RequestError(e.code, e.message)
        except Exception as e:
            #logging.exception(e)
            message =  _("Error uploading the layer. Review the file format. Cause: ") + str(e)
            raise rest_geoserver.RequestError(-1, message)
        raise rest_geoserver.RequestError(-1, _("Error uploading the layer. Review the file format."))
    
    def prepare_string(self, s):
        return ''.join((c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')).replace (" ", "_").replace ("-", "_").lower()

    def check_if_shape_is_empty(self, dir_path, shp_path):
        shp = os.path.join(dir_path, shp_path)
        dbf_file = shp.replace('.shp', '.dbf').replace('.SHP', '.dbf')
        if not os.path.isfile(dbf_file):
            dbf_file = dbf_file.replace('.dbf', '.DBF')
        table = DBF(dbf_file)                
        return table.__len__() == 0

    def __do_shpdir2postgis(self, username, datastore, application, dir_path, layergroup, table_definition, creation_mode, defaults):
        try: 
            # get & sanitize parameters
            if 'srs' in defaults.keys():    
                srs = defaults['srs']
            else:
                srs = 'EPSG:4326'
            if 'encoding' in defaults.keys():            
                encoding = defaults['encoding']
            else:
                encoding = 'LATIN1'
            if creation_mode not in ('CR', 'OW'):
                raise
            
            if not encoding in self.supported_encodings_plain or not srs in self.supported_srs_plain:
                raise rest_geoserver.RequestError()
            # FIXME: sanitize connection parameters too!!!
            # We are going to perform a command line execution with them,
            # so we must be ABSOLUTELY sure that no code injection can be
            # performed
            ds_params = json.loads(datastore.connection_params) 
            db = ds_params.get('database')
            host = ds_params.get('host')
            port = ds_params.get('port')
            schema = ds_params.get('schema', "public")
            port = str(int(port))
            user = ds_params.get('user')
            password = ds_params.get('passwd')
        
            if _valid_sql_name_regex.search(db) == None:
                raise InvalidValue(-1, _("The connection parameters contain an invalid database name: {value}. Identifiers must begin with a letter or an underscore (_). Subsequent characters can be letters, underscores or numbers").format(value=db))
            if _valid_sql_name_regex.search(user) == None:
                raise InvalidValue(-1, _("The connection parameters contain an invalid user name: {value}. Identifiers must begin with a letter or an underscore (_). Subsequent characters can be letters, underscores or numbers").format(value=db))
            if _valid_sql_name_regex.search(schema) == None:
                raise InvalidValue(-1, _("The connection parameters contain an invalid schema: {value}. Identifiers must begin with a letter or an underscore (_). Subsequent characters can be letters, underscores or numbers").format(value=db)) 

            #rename files with special characters
            files = os.listdir(dir_path)
            under_score = ['(',')','[',']','-'] #Anything to be replaced with '_' put in this list.            
            for f in files:
                copy_f = f
                for char in copy_f:                    
                    if (char in under_score): copy_f = copy_f.replace(char,'_')
                if (f != copy_f):
                    os.rename(os.path.join(dir_path, f),os.path.join(dir_path, copy_f))
                    if f in table_definition:
                        table_definition[copy_f] = table_definition[f]
                        del table_definition[f]
            
            # load SHP       
            files = [f for f in os.listdir(dir_path) if f.lower()[-4:]==".shp"]
            
            for f in files:
                if not self.check_if_shape_is_empty(dir_path, f):
                    has_style = False
                    has_conf = False
                    conf = None
                    newf = self.prepare_string(f)
                    visible = False
    
                    if newf in table_definition:
                        table_def = table_definition[newf]
                        layer_name = self.prepare_string(table_def['name'].lower())
                        layer_title = table_def['title']
                        
                        if table_def.has_key('srs') and table_def['srs']:
                            srs = table_def['srs']
    
                        if table_def.has_key('visible') and table_def['visible']:
                            visible = table_def['visible']
                        
                        if table_def.has_key('conf') and table_def['conf']:
                            has_conf = True
                            conf = table_def['conf']
                            
                        try:
                            original_style_name = table_def['style']
                            has_style = True
                            
                        except Exception as e:
                            original_style_name = self.prepare_string(layer_name)
                            print e
                        #layer_group = table_def['group'] + '_' + application.name.lower()
                    else:
                        layer_name = self.prepare_string(os.path.splitext(os.path.basename(f))[0].lower())
                        layer_title = os.path.splitext(os.path.basename(f))[0]
                        original_style_name = layer_name
                    shp_abs = os.path.join(dir_path, f)
                    try:
                        gdal_tools.shp2postgis(shp_abs, layer_name, srs, host, port, db, schema, user, password, creation_mode, encoding)
                    except Exception as e:
                        print "ERROR en shp2postgis ... Algunos shapefiles puede que no hayan subido "
                        continue 
                    
                    layer_exists = False
                    try:
                        layer = Layer.objects.get(name=layer_name, datastore=datastore)
                        layer_exists = True
                    except:
                        # may me missing when creating a layer or when
                        # appending / overwriting a layer created outside gvsig online
                        layer = Layer()                
                        # TODO: si estamos en create mode es porque ha aparecido otro shape. Deberiamos borrar el proyecto y volverlo a crear  
                                
                    if not layer_exists: #or (creation_mode==forms_geoserver.MODE_OVERWRITE and not layer_exists):
                        
                        try:
                            result = self.getFeaturetype(datastore.workspace, datastore, layer_name, layer_title)
                            if not result:
                                self.createFeaturetype(datastore.workspace, datastore, layer_name, layer_title)
                        except:
                            print "ERROR en createFeaturetype"
                            raise
                    
                    if creation_mode==forms_geoserver.MODE_CREATE or (creation_mode==forms_geoserver.MODE_OVERWRITE and not layer_exists): 
                        layer.datastore = datastore
    
    
                    # Limpiar cache de la capa
                    datastore = Datastore.objects.get(id=layer.datastore.id)
                    workspace = Workspace.objects.get(id=datastore.workspace_id)
                    
                    if self.updateResource(workspace.name, datastore.name, layer_name, layer_title):
                        layer.name = layer_name
                        if not layer.source_name:
                            layer.source_name = layer.name
                        layer.visible = visible
                        layer.cached = True
                        layer.single_image = False
                        layer.layer_group = layergroup
                        layer.title = layer_title
                        layer.type = datastore.type
                        layer.created_by = username
        
                        if has_conf:
                            layer.conf = conf
                        layer.save()
                    

                    self.clearCache(workspace.name, layer)
    
                    self.setDataRules()                                        
                    
                        
                    if layer.layer_group.name != "__default__":
                        self.createOrUpdateGeoserverLayerGroup(layer.layer_group)
                    
                    # estilos: se ejecuta en modo create o update
                    # si esta definido en la conf y existe, se clona con el nombre del ws
                    # si no, se crea uno por defecto
                    # 
                    final_style_name = datastore.workspace.name + '_' + original_style_name                
                    style_from_library = self.getStyle(original_style_name)                
    
                    if has_style and style_from_library is not None :
                        print "DEBUG: has_style AND style_from_library"       
                        if creation_mode == 'CR':
                            if symbology_services.clone_style(self, layer, original_style_name, final_style_name) is False:
                                print "DEBUG: Creation mode CR. Clone style False. Creating default" 
                                self.createDefaultStyle(layer, final_style_name)
                                stylelayers = StyleLayer.objects.filter(layer=layer)  
                                for stylelayer in stylelayers:
                                    if stylelayer.style.name != final_style_name:
                                        stylelayer.style.is_default = False
                                        stylelayer.style.save()
                                self.setLayerStyle(layer, final_style_name, True)
                                newRecord2 = self.updateThumbnail(layer, 'create')
                                if newRecord2:
                                    newRecord2.save()  
                            else:
                                print "DEBUG: Creation mode CR. Clone style True"
                        else:
                            print "DEBUG: Has style and style_from_library. Creation mode UPDATE"
                            style_name = datastore.workspace.name + '_' + layer.name + '_default'
                            symbology_services.clone_style(self, layer, original_style_name, final_style_name)
                            stylelayers = StyleLayer.objects.filter(layer=layer)  
                            for stylelayer in stylelayers:
                                if stylelayer.style.name != final_style_name:
                                    stylelayer.style.is_default = False
                                    stylelayer.style.save()
                            self.setLayerStyle(layer, final_style_name, True)
                            newRecord2 = self.updateThumbnail(layer, 'create')
                            if newRecord2:
                                newRecord2.save()                      
                    else:
                        print "DEBUG: NO has_style or style_from_library " + original_style_name
                        style_name = datastore.workspace.name + '_' + layer.name + '_default'
                        stylelayers = StyleLayer.objects.filter(layer=layer)  
                        
                        if creation_mode == 'CR' or (creation_mode == 'OW' and ((not self.getStyle(style_name)) or stylelayers.__len__() == 0)):
                            for stylelayer in stylelayers:
                                if stylelayer.style.name != style_name:
                                    stylelayer.style.is_default = False
                                    stylelayer.style.save()
                            self.createDefaultStyle(layer, style_name)
                            self.setLayerStyle(layer, style_name, True)
                            newRecord2 = self.updateThumbnail(layer, 'create')
                            if newRecord2:
                                newRecord2.save()
                            
                    srs = defaults['srs']
                    
                    if layer.layer_group.name != "__default__":
                        self.createOrUpdateGeoserverLayerGroup(layer.layer_group)
                            
        except rest_geoserver.RequestError as ex:
            print "Error Request: " + str(ex)
            raise             
        except gdal_tools.GdalError as ex:
            print "Error Gdal: " + str(ex)
            raise rest_geoserver.RequestError(e.code, e.message)
        except Exception as e:
            logging.exception(e)
            raise rest_geoserver.RequestError(-1, _("Error creating the layer. Review the file format."))
    
    
    def get_fields_from_shape(self, shp_path):
        fields = {}
        fields['fields'] = {}
        
        dbf_file = shp_path.replace('.shp', '.dbf').replace('.SHP', '.dbf')
        if not os.path.isfile(dbf_file):
            dbf_file = dbf_file.replace('.dbf', '.DBF')
        table = DBF(dbf_file)                
        return table.fields  
        
        
    def exportShpToPostgis(self, form_data):
        name = form_data['name']
        ds = form_data['datastore']
        shp_path = form_data['file'] 
        
        
        fields = self.get_fields_from_shape(shp_path)
        for field in fields:
            if ' ' in field.name:
                raise InvalidValue(-1, _("Invalid layer fields: '{value}'. Layer can't have fields with whitespaces").format(value=field.name))
            
        
        if _valid_sql_name_regex.search(name) == None:
            raise InvalidValue(-1, _("Invalid layer name: '{value}'. Identifiers must begin with a letter or an underscore (_). Subsequent characters can be letters, underscores or numbers").format(value=name))
                    
        try:
            self.__do_export_to_postgis(name, ds, form_data, shp_path)
            return True

        except Exception as e:
            print e
            raise e
    
    def shpdir2postgis(self, request, datastore, application, dir_path, layergroup, table_definition,creation_mode, defaults):
        try:
            self.__do_shpdir2postgis(request, datastore, application, dir_path, layergroup, table_definition, creation_mode, defaults)        
        except Exception as e:
            print e
            raise e
    
    def __field_def_to_gs(self, field_def_array, geometry_type, pks):
        try:
            fields = []
            jts_type = self.getGeoserverBindings(geometry_type)
            if jts_type:
                fields.append({
                   "name": "geom",
                   "minOccurs": 0,
                   "maxOccurs": 1,
                   "nillable": False,
                   "binding": jts_type
                })
            else:
               raise rest_geoserver.RequestError(_("Invalid geometry type")) 
            
            for f in field_def_array:
                if len(filter(lambda existing: existing['name'] == f[0], fields))>0:
                    raise rest_geoserver.RequestError(_("Duplicated field name: {0}").format(f[0]))
                if f[0] == "geom" or f[0] == "name" or f[0] == "fid":
                    raise rest_geoserver.RequestError(_("Invalid field name. '{0}' is a reserved word").format(f[0]))
                field = {"minOccurs": 0, "maxOccurs": 1, "nillable": True}
                if f[0] in pks:
                    {"minOccurs": 1, "maxOccurs": 1, "nillable": False}
                else:
                    {"minOccurs": 0, "maxOccurs": 1, "nillable": True}
                field['name'] = f[0]
                sql_type = f[1]
                field['binding'] = self.getGeoserverBindings(sql_type)
                if not field['binding']:
                    raise rest_geoserver.RequestError(_("Unsupported field type: {0}").format(sql_type))
                fields.append(field)
                
            if len(fields)>1:
                return fields
            raise rest_geoserver.RequestError(_("At least one field must be defined"))
            
        except:
            raise rest_geoserver.RequestError(_("Invalid field definition"))
    
    def _featuretype_attributes(self, conn, schema, tablename):
        """
        Reads the database schema to get an updated definition of the featuretype fields,
        using the same syntax expected by Geoserver
        """
        field_info = conn.get_fields_info(tablename, schema)
        geometry_columns_info = conn.get_geometry_columns_info(table=tablename, schema=schema)
        pks = conn.get_pk_columns(tablename, schema)
        
        gs_fields = []
        geometry_columns = {}
        
        for f in geometry_columns_info:
            name = f[2]
            geometry_type = f[5]
            geometry_columns[name] = geometry_type
        
        for f in field_info:
            name = f["name"]
            if name in geometry_columns:
                sql_type = geometry_columns[name]
            else:
                sql_type = f['type']
            binding = self.getGeoserverBindings(sql_type)
            if not binding:
                raise rest_geoserver.RequestError(_("Unsupported field type: {0}").format(sql_type))
            nullable = True if f['nullable'] == 'YES' else False
            if name in pks:
                field = {"name": name, "binding": binding, "minOccurs": 1, "maxOccurs": 1, "nillable": False}
            else:
                field = {"name": name, "binding": binding, "minOccurs": 0, "maxOccurs": 1, "nillable": nullable}
            gs_fields.append(field)
        return gs_fields

    def createLayer(self, request, form_data, layer_type):
        name = form_data['name']

        if _valid_sql_name_regex.search(name) == None:
            raise InvalidValue(-1, _("Invalid layer name: '{value}'. Identifiers must begin with a letter or an underscore (_). Subsequent characters can be letters, underscores or numbers").format(value=name))
        
        datastore = form_data['datastore']
        workspace = datastore.workspace
        
        if self.resource_exists(workspace.name, name):
            raise InvalidValue(-1, _("A layer already exists with this name: '{value}'").format(value=name))
        
        title = form_data.get('title')
        
        geom_type = form_data.get('geom_type')
        srs = form_data.get('srs')
        if not srs in self.supported_srs_plain or not geom_type in self.supported_postgis_geom_types:
            raise rest_geoserver.RequestError()
            
        if layer_type==Geoserver.CREATE_TYPE_SQL_VIEW:
            #FIXME: should we try to sanitize the SQL statement??
            sql_statement = form_data['sql_statement']
            key_column = form_data.get('key_column')
            geom_column = form_data.get('geom_column')
            
            try:
                srid = srs.split(":")[1]
                self.rest_catalog.create_sql_view(workspace.name, datastore.name, name, sql_statement, key_column, geom_column, geom_type, srid, None, title=title, user=self.user, password=self.password)
            except rest_geoserver.FailedRequestError as e:
                if "Error occurred building feature type" in e.get_message():
                    e.message = _("Error occurred building the view. Review the SQL sentence")
                raise
        elif layer_type==Geoserver.CREATE_TYPE_VECTOR_LAYER:
            fields = key_column = self.__field_def_to_gs(form_data.get('fields'), geom_type)
            try:
                extraParams = {"nativeBoundingBox": {"minx": 0, "maxx": 1, "miny": 0, "maxy":1 , "crs":srs}}
                self.rest_catalog.create_feature_type(name, title, datastore.name, workspace.name, srs=srs, fields=fields, user=self.user, password=self.password, extraParams=extraParams)
            except rest_geoserver.FailedRequestError as e:
                if "Error occurred building feature type" in e.get_message():
                    e.message = _("Error occurred building the view. Review the SQL sentence")
                raise
            pass
        else:
            raise UnsupportedRequestError()
        l = Layer()
        l.datastore = datastore
        l.name =  name
        if not l.source_name:
            l.source_name = l.name
        l.visible = form_data.get('visible', False) # it will be missing on the form when false
        l.queryable = form_data.get('queryable', False) # it will be missing on the form when false
        l.cached = form_data.get('cached', False) # it will be missing on the form when false
        l.single_image = form_data.get('single_image', False) # it will be missing on the form when false
        l.layer_group = form_data.get('layer_group', LayerGroup.objects.get(name='__default__'))
        l.title = title
        l.type = 'v_PostGIS_View'
        l.created_by = request.user.username
        l.save()
        return l
    
    def createTable(self, form):
        datastore = form.get('datastore')
        name = form.get('name')
        geom_type = form.get('geom_type')
        srs = form.get('srs').split(':')[1]
        fields = form.get('fields')
        
        return self.createTableFromFields(datastore, name, geom_type, srs, fields)
        
    def createTableFromFields(self, datastore, name, geom_type, srs, fields):
        
        for control_field in settings.CONTROL_FIELDS:
            has_control_field = False
            
            for field in fields:
                if field['name'] == control_field['name']:
                    has_control_field = True
                
            if not has_control_field:
                fields.append(control_field)
                
        
        try:
            params = json.loads(datastore.connection_params)
            host = params['host']
            port = params['port']
            dbname = params['database']
            user = params['user']
            passwd = params['passwd']
            schema = params.get('schema', 'public')
            i = Introspect(database=dbname, host=host, port=port, user=user, password=passwd)
            i.create_table(schema, name, geom_type, srs, fields)
            i.close()
            
            return True
        
        except Exception as e:
            print str(e)
            raise
        
        
    
    def deleteTable(self, datastore, name):
        try:
            params = json.loads(datastore.connection_params)
            host = params['host']
            port = params['port']
            dbname = params['database']
            user = params['user']
            passwd = params['passwd']
            schema = params.get('schema', 'public')
            i = Introspect(database=dbname, host=host, port=port, user=user, password=passwd)
            i.delete_table(schema, name)
            i.close()
            
            return True
        
        except Exception as e:
            print str(e)
            raise
    
    def setDataRules(self):
        
        url = self.rest_catalog.get_service_url() + "/security/acl/layers.json"
        services_url = self.rest_catalog.get_service_url() + "/security/acl/services.json"

        rules = DataRule.objects.all()
        for r in rules:
            self.rest_catalog.get_session().delete(self.rest_catalog.get_service_url() + "/security/acl/layers/" + r.path, verify=False, auth=(self.user, self.password))
            r.delete()
        self.rest_catalog.get_session().delete(self.rest_catalog.get_service_url() + "/security/acl/services/wfs.Transaction", verify=False, auth=(self.user, self.password))
        
        layers = Layer.objects.filter(external=False)  
        transaction_roles = [] 
        for layer in layers:
            who_can_read = []
            who_can_write = []
            read_groups_query = LayerReadGroup.objects.filter(layer=layer)
            if read_groups_query.count()>0: # layer is not public
                who_can_read = [ "ROLE_"+ g.group.name.upper() for g in read_groups_query ]
            
            write_groups_query = LayerWriteGroup.objects.filter(layer=layer)
            if write_groups_query.count()>0:
                who_can_write = [ "ROLE_"+ g.group.name.upper() for g in write_groups_query ]
            transaction_roles += who_can_write
            
            datastore = Datastore.objects.get(id=layer.datastore_id)
            workspace = Workspace.objects.get(id=datastore.workspace_id)

            data = {}
            if len(who_can_read) > 0:
                read_rule_path = workspace.name + "." + layer.name + ".r"
                read_rule_roles = ",".join(who_can_read)
                read_rule = DataRule(
                    path = read_rule_path,
                    roles = read_rule_roles
                )
                data[read_rule_path] = read_rule_roles
                read_rule.save()
            if  len(who_can_write) > 0:
                write_rule_path = workspace.name + "." + layer.name + ".w"
                write_rule_roles =  ",".join(who_can_write)
                write_rule = DataRule(
                    path = write_rule_path,
                    roles = write_rule_roles
                )
                write_rule.save()
                data[write_rule_path] = write_rule_roles
                        
            self.rest_catalog.get_session().post(url, json=data, verify=False, auth=(self.user, self.password))
            
        if  len(transaction_roles) > 0:
            service = {}
            service_write_roles =  ",".join(transaction_roles)
            service['wfs.Transaction'] = service_write_roles
            self.rest_catalog.get_session().post(services_url, json=service, verify=False, auth=(self.user, self.password))
            

    def setLayerDataRules(self, layer, read_groups, write_groups):
        url = self.rest_catalog.get_service_url() + "/security/acl/layers.json"
        who_can_read = [ "ROLE_"+ g.name.upper() for g in read_groups ]
        who_can_write = [ "ROLE_"+ g.name.upper() for g in write_groups ]
        
        read_rule_path = layer.datastore.workspace.name + "." + layer.name + ".r"
        if len(who_can_read)>0:
            read_rule_roles = ",".join(who_can_read)
            read_rule = DataRule(
                path = read_rule_path,
                roles = read_rule_roles
                )
            read_rule.save()
            data = { read_rule_path: read_rule_roles}
            # try to modify the rule
            result = self.rest_catalog.get_session().put(url, json=data, verify=False, auth=(self.user, self.password))
            if result.status_code == 409:
                # If modifying failed, try to add the rule.
                # We could delete and then add, but it is safer in this way (the layer remains protected in every instant)
                # It also safe if the geoserver/gvsigol rules get incoherent
                result = self.rest_catalog.get_session().post(url, json=data, verify=False, auth=(self.user, self.password))
        else:
            self.rest_catalog.get_session().delete(self.rest_catalog.get_service_url() + "/security/acl/layers/" + read_rule_path, verify=False, auth=(self.user, self.password))
            rules = DataRule.objects.filter(path=read_rule_path)
            rules.delete()

        write_rule_path = layer.datastore.workspace.name + "." + layer.name + ".w"
        # now add the rule if necessary
        if len(who_can_write)>0:
            write_rule_roles =  ",".join(who_can_write)
            write_rule = DataRule(
                path = write_rule_path,
                roles = write_rule_roles
                )
            write_rule.save()
            data = { write_rule_path: write_rule_roles}
            # try to modify the rule
            result = self.rest_catalog.get_session().put(url, json=data, verify=False, auth=(self.user, self.password))
            if result.status_code == 409:
                # If modifying failed, try to add the rule.
                # We could delete and then add, but it is safer in this way (the layer remains protected in every instant)
                # It also safe if the geoserver/gvsigol rules get incoherent 
                result = self.rest_catalog.get_session().post(url, json=data, verify=False, auth=(self.user, self.password))
        else:
            # clean any existing write rule for the layer 
            self.rest_catalog.get_session().delete(self.rest_catalog.get_service_url() + "/security/acl/layers/" + write_rule_path, verify=False, auth=(self.user, self.password))
            rules = DataRule.objects.filter(path=write_rule_path)
            rules.delete()

        write_groups_query = LayerWriteGroup.objects.all()
        transaction_roles = [ "ROLE_"+ g.group.name.upper() for g in write_groups_query ]
        if  len(transaction_roles) > 0:
            services_url = self.rest_catalog.get_service_url() + "/security/acl/services.json"
            service = {}
            service_write_roles =  ",".join(transaction_roles)
            service['wfs.Transaction'] = service_write_roles
            result = self.rest_catalog.get_session().put(services_url, json=service, verify=False, auth=(self.user, self.password))
            if result.status_code == 409:
                self.rest_catalog.get_session().post(services_url, json=service, verify=False, auth=(self.user, self.password))

    def clearCache(self, ws, layer):
        try:
            self.rest_catalog.clear_cache(ws, layer, user=self.user, password=self.password)
            return True
        
        except Exception as e:
            logger.exception('ERROR clearCache. Layer:' + str(layer))
            return False
        
    def clearLayerGroupCache(self, name):
        try:
            self.rest_catalog.clear_layergroup_cache(name, user=self.user, password=self.password)
            return True
        
        except Exception as e:
            logger.exception('ERROR clearCache. Group:' + str(name))
            return False
        
    def addGridSubset(self, ws, layer):
        try:
            self.rest_catalog.add_grid_subset(ws, layer, user=self.user, password=self.password)
            return True
        
        except Exception as e:
            print e
            return False
        
    def getGeomColumns(self, datastore):
        """
        Gets the SRS of a PostGIS feature type by connecting directly to the database
        """
        try:
            params = json.loads(datastore.connection_params)
            host = params['host']
            port = params['port']
            dbname = params['database']
            user = params['user']
            passwd = params['passwd']
            schema = params.get('schema', 'public')
            i = Introspect(database=dbname, host=host, port=port, user=user, password=passwd)
            rows = i.get_geometry_columns_info(schema=schema)
            i.close()
            
            result = []
            for r in rows:
                srs = "EPSG:"+str(r[4])
                result.append({"schema": r[0], "name": r[1], "geom_column": r[2], "geom_type": r[5], "srs": srs, 'key_column': r[6], 'fields': r[7]})
            return result
        except Exception as e:
            print str(e)
            raise
        
    def getFeatureCount(self, request, url, layer_name, f):   
        if f == None:
            values = {
                'SERVICE': 'WFS',
                'VERSION': '1.1.0',
                'REQUEST': 'GetFeature',
                'TYPENAME': layer_name,
                'OUTPUTFORMAT': 'text/xml; subtype=gml/3.1.1',
                'RESULTTYPE': 'hits'
            }
            
        else:
            values = {
                'SERVICE': 'WFS',
                'VERSION': '1.1.0',
                'REQUEST': 'GetFeature',
                'TYPENAME': layer_name,
                'OUTPUTFORMAT': 'text/xml; subtype=gml/3.1.1',
                'RESULTTYPE': 'hits'
            }
            if f != '':
                values['CQL_FILTER'] = f.encode('utf-8')
            
        req = requests.Session()
        req.auth = (self.user, self.password)
        response = req.post(url, data=values, verify=False, proxies=settings.PROXIES)
        root = ET.fromstring(response.text)
        numberOfFeatures = int(root.attrib['numberOfFeatures'])
        
        return numberOfFeatures
    
    def getThumbnail(self, ws, ds, layer):
        (ds_type, layer_info) = self.getResourceInfo(ws.name, ds, layer.name, "json")
        
        if ds_type == 'featureType':
            params = json.loads(layer.datastore.connection_params)
            host = params['host']
            port = params['port']
            dbname = params['database']
            user = params['user']
            passwd = params['passwd']
            schema = params.get('schema', 'public')
            i = Introspect(database=dbname, host=host, port=port, user=user, password=passwd)
            count = i.get_estimated_count(schema, layer.name)
            aux = count[0]
            if aux < 10000:
                maxx = str(layer_info[ds_type]['latLonBoundingBox']['maxx'])
                maxy = str(layer_info[ds_type]['latLonBoundingBox']['maxy'])
                minx = str(layer_info[ds_type]['latLonBoundingBox']['minx'])
                miny = str(layer_info[ds_type]['latLonBoundingBox']['miny'])
                if layer_info[ds_type]['latLonBoundingBox']['minx'] > layer_info[ds_type]['latLonBoundingBox']['maxx']:
                    maxx = str(layer_info[ds_type]['latLonBoundingBox']['minx'] +1)
                if layer_info[ds_type]['latLonBoundingBox']['miny'] > layer_info[ds_type]['latLonBoundingBox']['maxy']:
                    maxy = str(layer_info[ds_type]['latLonBoundingBox']['miny'] +1)
                bbox = minx + "," + miny + "," + maxx + "," + maxy 
            else:
                bbox = i.get_bbox_firstgeom(schema, layer.name, 0.01)  
            i.close()
               
        else:
            if ds_type == 'imagemosaic':
                ds_type = 'coverage'
            maxx = str(layer_info[ds_type]['latLonBoundingBox']['maxx'])
            maxy = str(layer_info[ds_type]['latLonBoundingBox']['maxy'])
            minx = str(layer_info[ds_type]['latLonBoundingBox']['minx'])
            miny = str(layer_info[ds_type]['latLonBoundingBox']['miny'])
            if layer_info[ds_type]['latLonBoundingBox']['minx'] > layer_info[ds_type]['latLonBoundingBox']['maxx']:
                maxx = str(layer_info[ds_type]['latLonBoundingBox']['minx'] +1)
            if layer_info[ds_type]['latLonBoundingBox']['miny'] > layer_info[ds_type]['latLonBoundingBox']['maxy']:
                maxy = str(layer_info[ds_type]['latLonBoundingBox']['miny'] +1)
            bbox = minx + "," + miny + "," + maxx + "," + maxy
            
        
        values = {
            'SERVICE': 'WMS',
            'VERSION': '1.1.1',
            'REQUEST': 'GetMap',
            'LAYERS': ws.name + ":" + layer.name,
            'FORMAT': 'image/png',
            'SRS': 'EPSG:4326',
            'HEIGHT': '550',
            'WIDTH': '768',
            'BBOX': bbox
        }
                
        iname = ''.join(random.choice(string.ascii_uppercase) for i in range(8))
        iname += '.png'
        
        params = urllib.urlencode(values)
        
        req = requests.Session()
        req.auth = (self.user, self.password)
        print ws.wms_endpoint + "?" + params
        response = req.get(ws.wms_endpoint + "?" + params, verify=False, stream=True, proxies=settings.PROXIES)
        with open(settings.MEDIA_ROOT + "thumbnails/" + iname, 'wb') as f:
            for block in response.iter_content(1024):
                if not block:
                    break
                f.write(block)
                
        return os.path.join("thumbnails/", iname)        
    
    
        #
    # ImageMosaic methods
    #
    
    
    def createimagemosaic(self, store, layer):
        params = json.loads(store.connection_params)
        try:
            ele_regex = params.get('ele_regex', '')
            date_regex = params.get('date_regex', '')
            has_dimensions = date_regex != '' or ele_regex != ''
                
            if store.type=="c_ImageMosaic":
                # the coverage has been uploaded and created
                # now let's enable the dimensions
                if has_dimensions:
                    logging.error("get_resource: "+layer.name+", "+store.name+", "+store.workspace.name)
                    catalog = self.getGsconfig()
                    coverage = catalog.get_resource(layer.name, store.name, store.workspace.name)
                    md = dict(coverage.metadata)
                    if date_regex != "":
                        md['time'] = DimensionInfo(name='time',
                                                  enabled=layer.time_enabled,
                                                  presentation=layer.time_presentation,
                                                  resolution=None,
                                                  units="ISO8601",
                                                  unitSymbol=None,
                                                  strategy=layer.time_default_value_mode
                                                  )
                    if ele_regex!="":
                        #FIXME: we could have units different than meters
                        md['elevation'] = DimensionInfo(name='elevation',
                                                  enabled=layer.time_enabled,
                                                  presentation=layer.time_presentation,
                                                  resolution=None,
                                                  units="EPSG:5030",
                                                  unitSymbol= "m",
                                                  strategy=layer.time_default_value_mode
                                                  )
                    coverage.metadata = md
                    catalog.save(coverage)
        except Exception as e:
            logging.exception(str(e))
  
    
    def __process_image_mosaic_folder(self, name, zip_path, date_regex, date_format, ele_regex, ele_format):
        has_dimensions = date_regex != '' or ele_regex != ''
        if has_dimensions:
            folder_path = zip_path.replace('file://','')
            try: 
                try:
                    os.chmod(folder_path, 0775)
                except Exception:
                    pass
                filenames = os.listdir(folder_path)
                founded = False
                for filename in filenames:
                    try:
                        os.chmod(folder_path+"/"+filename, 0775)
                        if (date_regex != "" and re.search(date_regex, filename) != None) or (ele_regex != "" and re.search(ele_regex, filename) != None):
                            founded = True
                    except:
                        pass
                    
                if founded:
                    self.__create_mosaic_indexer(name, folder_path, date_regex, ele_regex)
                    #os.remove(indexer)
                    if date_regex != "":
                        self.__create_mosaic_time_regexp(folder_path, date_regex, date_format)
                        #z.write(regexp_file, "timeregex.properties")
                        #os.remove(regexp_file)
                    if ele_regex != "":
                        self.__create_mosaic_ele_regexp(folder_path, ele_regex, ele_format)
                        #z.write(regexp_file, "elevationregex.properties")
                        #os.remove(regexp_file)
                    self.__create_im_datastore_properties(folder_path)
                    
            except (WrongTimePattern, WrongElevationPattern) as exc:
                raise
            except Exception as exc:
                raise BadFormat()
    
        
    def __test_zip_structure(self, zip_path):
        z = zipfile.ZipFile(zip_path, "r")
        for n in z.namelist():
            if n.endswith("/"):
                z.close()
                raise BadFormat(-1, _("Bad file format. The provided zip file must not contain any subdirectory."))
        z.close()
    
    
    def __create_mosaic_indexer(self, name, folder_path, date_regex, ele_regex):
        '''
        he above will be sufficient in case the image mosaic can create the index table and perform normal indexing, using the directory name as the table name. In case a specific table name needs to be used, add an "indexer.properties" specifying the TypeName property, e.g.:

            TypeName=mymosaictype
        
        In case the index "table" already exists instead, then a "indexer.properties" file will be required, with the following contents:
        
            UseExistingSchema=true
            TypeName=nameOfTheFeatureTypeContainingTheIndex
            AbsolutePath=true
        
        The above assumes location attribute provides absolute paths to the mosaic granules, instead of ones relative to the mosaic configuration files directory.
        '''
        
        fd = open(folder_path + "/indexer.properties","w+")
        #fd.write("UseExistingSchema=true\nTypeName=prueba_tif_mes\nAbsolutePath=true\n")
        fd.write('Name='+name+'\n')
        schema = "Schema=*the_geom:Polygon,location:String"
        if date_regex != '':
            fd.write("TimeAttribute=date\n")
            schema = schema + ",date:java.util.Date"
            fd.write("PropertyCollectors=TimestampFileNameExtractorSPI[timeregex](date)\n") 
        if ele_regex != '':
            fd.write("ElevationAttribute=elevation\n")
            schema = schema + ",elevation:Integer"
        schema = schema + "\n"
        fd.write(schema)
        fd.close()
    
    def __create_mosaic_time_regexp(self, folder_path, pattern="(?<=_)[0-9]{8}", format=""):
        fd = open(folder_path + "/timeregex.properties","w+")
        reg_ex = "regex="+pattern
        if format != "":
            reg_ex = reg_ex + ",format="+format
        fd.write(reg_ex +"\n")
        fd.close()
    
    def __create_mosaic_ele_regexp(self, folder_path, pattern="(?<=_)(\\d{4}\\.\\d{3})", format=""):
        fd = open(folder_path + "/elevationregex.properties","w+")
        reg_ex = "regex="+pattern
        if format != "":
            reg_ex = reg_ex + ",format="+format
        fd.write(reg_ex +"\n")
        fd.close()
    
    def __create_im_datastore_properties(self, folder_path):
        mosaic_db = settings.MOSAIC_DB
        if mosaic_db is not None:
            fd = open(folder_path + "/datastore.properties","w+")
            fd.write("SPI=org.geotools.data.postgis.PostgisNGDataStoreFactory\n")
            '''
            fd.write("StoreName=ws_mendezt:ds_mendezt\n")
            
            '''
            fd.write("host={0}\n".format(mosaic_db.get('host')))
            fd.write("port={0}\n".format(mosaic_db.get('port')))
            fd.write("database={0}\n".format(mosaic_db.get('database')))
            fd.write("schema={0}\n".format(mosaic_db.get('schema')))
            fd.write("user={0}\n".format(mosaic_db.get('user')))
            fd.write("passwd={0}\n".format(mosaic_db.get('passwd')))
            fd.write("Loose\ bbox=true\n")
            fd.write("Estimated\ extends=false\n")
            fd.write("validate\ connections=true\n")
            fd.write("Connection\ timeout=10\n")
            fd.write("preparedStatements=true\n")
            
            
            fd.close()


    def is_supported_type(self, sql_type, for_creation=True):
        if sql_type in SUPPORTED_SQL_CREATION_TYPES:
            return True
        if not for_creation and sql_type in OTHER_SUPPORTED_SQL_TYPES:
            return True
        return False

    def gvsigol_to_sql_type(self, field_type):
        if field_type in ['cd_json', 'enumeration', 'multiple_enumeration']:
            field_type = 'character varying'
        elif field_type == 'double':
            return 'double precision'
        field_type = field_type.replace("_", " ")
        if self.is_supported_type(field_type):
            return field_type
        