'''
    gvSIG Online.
    Copyright (C) 2007-2015 gvSIG Association.

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

from __builtin__ import isinstance
from models import Layer, LayerGroup, Datastore, Workspace, DataRule, LayerReadGroup, LayerWriteGroup
from gvsigol_symbology.models import Symbolizer, Style, Rule, StyleLayer,\
    StyleRule
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import ugettext_lazy as _
from gvsigol.settings import GVSIGOL_SERVICES
from gvsigol.settings import GVSIGOL_CATALOG
from geoserver.support import DimensionInfo
from backend_postgis import Introspect
from owslib.wms import WebMapService
import xml.etree.ElementTree as ET
import geoserver.catalog as gscat
from django.db.models import Max
import forms_geoserver
import rest_geonetwork
import rest_geoserver
from zipfile import ZipFile
import tempfile, zipfile
import sys, os, shutil
import requests
import gdal_tools
import logging
import json
import re

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

class Geoserver():
    CREATE_TYPE_SQL_VIEW = "gs_sql_view"
    CREATE_TYPE_VECTOR_LAYER = "gs_vector_layer"
    def __init__(self, base_url, cluster_nodes, supported_types=None):
        self.base_url = base_url
        self.rest_url = self.base_url+"/rest"
        self.gwc_url = base_url+"/gwc/rest"
        self.cluster_nodes = cluster_nodes
        self.rest_catalog = rest_geoserver.Geoserver(self.rest_url, self.gwc_url)
        self.supported_types = supported_types
        if supported_types is not None:
            self.supported_types = supported_types
        else:
            self.supported_types = (
                        #('v_SHP', _('Shapefile folder')),
                        ('v_PostGIS', _('PostGIS vector')),
                        ('c_WorldImage', _('JPG, Tiff and PNG + world file')),
                        ('c_ArcGrid', _('ArcInfo ASCII Grid')),
                        ('c_GeoTIFF', _('GeoTiff')),
                        ('c_ImageMosaic', _('Image Mosaics, Time series or elevation series')),
                        )
                 
        # disable upload to Postgis datastores, as it is not currently supported by Geoserver
        # have a look to: http://boundlessgeo.com/2012/10/adding-layers-to-geoserver-using-the-rest-api/
        #all_upload_types = ['v_PostGIS', 'c_WorldImage', 'c_GeoTIFF', 'c_ImageMosaic']
        all_upload_types = ['c_WorldImage', 'c_GeoTIFF', 'c_ImageMosaic', 'v_SHP']

        gdal_tools.OGR2OGR_PATH = GVSIGOL_SERVICES.get('OGR2OGR_PATH', gdal_tools.OGR2OGR_PATH)
        if os.path.exists(gdal_tools.OGR2OGR_PATH):
            all_upload_types.append('v_PostGIS')
        
        self.supported_srs_plain = [ x[0] for x in forms_geoserver.supported_srs ]
        self.supported_encodings_plain = [ x[0] for x in forms_geoserver.supported_encodings ]
        self.supported_postgis_geom_types = [ x[0] for x in forms_geoserver.geometry_types ]
        self.raster_extensions = [".jpg", ".jpeg", ".jpe", ".png", ".tif"]
        
        self.supported_upload_types = []
        for x in self.supported_types:
            if x[0] in all_upload_types:
                self.supported_upload_types.append(x)
        
        self.layer_create_types = ((Geoserver.CREATE_TYPE_VECTOR_LAYER, _("Vector layer")),
                                   (Geoserver.CREATE_TYPE_SQL_VIEW, _("SQL View")))
        #self.layer_create_types = ((Geoserver.CREATE_TYPE_SQL_VIEW, _("SQL View")), )
    
    def getGsconfig(self, session):
        return gscat.Catalog(self.rest_url, session['username'], session['password'], disable_ssl_certificate_validation=True)
    
    
    def getSupportedTypes(self):
        return self.supported_types
    
    def getSupportedUploadTypes(self):
        return self.supported_upload_types
    
    def getSupportedEncodings(self):
        return self.supported_encodings
    
    def getSupportedSRSs(self):
        return self.supported_SRSs
    
    def getSupportedFonts(self, session):
        return self.rest_catalog.get_fonts(user=session['username'], password=session['password'])
    
    def reload_nodes(self, session):
        try:
            if len(self.cluster_nodes) > 0:
                for node in self.cluster_nodes:
                    self.rest_catalog.reload(node, user=session['username'], password=session['password'])
            return True
        except Exception as e:
            print str(e)
            return False
        
    def createWorkspace(self, session, name, uri, description=None,
                        wms_endpoint=None, wfs_endpoint=None,
                        wcs_endpoint=None, cache_endpoint=None):
        try:
            self.getGsconfig(session).create_workspace(name, uri)
            return True
        except Exception as e:
            print str(e)
            return False
        
    def deleteWorkspace(self, workspace, session):
        """
        Deletes a workspace and all its associated resources
        """
        try:
            catalog = self.getGsconfig(session) 
            ws = catalog.get_workspace(workspace.name)
            catalog.delete(ws, recurse=True)
            return True
        except Exception as e:
            return False
        
    def getBaseUrl(self):
        return self.base_url
    
    def getCapabilities(self, s):
        try:
            capabilities = WebMapService(self.base_url + "/wms", version='1.1.1', xml=None, username=s['username'], password=s['password'])
            return capabilities
        except Exception as e:
            print e
            return False
    
    def getCapabilities_without_auth(self):
        capabilities = WebMapService(self.base_url + "/wms", version='1.1.1')
        return capabilities

    def createDatastore(self, workspace, type, name, description, connection_params, session):
        """
        Some valid drivers:
        '' (shape), 'PostGIS', 'WorldImage', 'ArcGrid', 'ImageMosaic', 'GeoTIFF'
        """
        try:
            format_nature=type[:1]
            driver=type[2:]
            params_dict = json.loads(connection_params)
            catalog = self.getGsconfig(session)
            if format_nature == "v": # vector
                if driver == "SHP":
                    driver = None
                elif driver == 'PostGIS':
                    params_dict['schema'] = params_dict.get('schema', 'public')
                ds = catalog.create_datastore(name, workspace.name)
                ds.connection_parameters.update(params_dict)
            elif format_nature == "c": # coverage (raster)
                ds = catalog.create_coveragestore2(name, workspace.name)
                ds.url = params_dict.get('url')
            else:
                # unsupported
                return False
            ds.description = description # description is ignored by gsconfig at the moment
            ds.type = driver
            response = catalog.save(ds) # FIXME: we should check response.status to ensure the operation was correct
            return True
        except Exception as e:
            return False
        
    def datastore_exists(self, workspace, name, session):
        try:
            if self.getGsconfig(session).get_store(name, workspace=workspace):
                return True
        except:
            pass
        return False
    
    def resource_exists(self, workspace, name, session):
        try:
            if self.getGsconfig(session).get_resource(name, None, workspace):
                return True
        except Exception as e:
            pass
        return False

    def updateDatastore(self, workspace, dsname, description, dstype, conn_params, session):
        try:
            format_nature=dstype[:1]
            catalog = self.getGsconfig(session)
            ds = catalog.get_store(dsname, workspace)
            params_dict = json.loads(conn_params)
            if format_nature == "v": # vector
                # directly updating connection_parameters won't work, we need to set the dict again
                params = ds.connection_parameters
                params.update(params_dict)
                ds.connection_parameters = params
            elif format_nature == "c": # coverage (raster)
                ds.url = params_dict.get('url')
            catalog.save(ds)
            return True
        except Exception as exc:
            print exc
            return False
    
    def deleteDatastore(self, workspace, datastore, session, purge=None):
        """
        Deletes a datastore and all its associated resources
        """
        try:
            catalog = self.getGsconfig(session)
            ds = catalog.get_store(datastore.name, workspace=workspace.name)
            if datastore.type=="c_ImageMosaic":
                try:
                    catalog.delete(ds, purge="metadata", recurse=True)
                except:
                    # we need to catch the delete because we'll usually get an error:
                    # Database "xxxx" is being accessed by other users.
                    # Geoserver is probably accessing the DB on other threads
                    catalog.delete(ds, purge=None, recurse=True)
            else:
                catalog.delete(ds, purge, recurse=True)
            return True
        except Exception as e:
            return False
        
    def getStyles(self, session):
        try:                    
            styles = self.getGsconfig(session).get_styles(workspace=None)                   
            return styles
        
        except:
            e = sys.exc_info()[0]
            # FIXME: raise an exception
            return []
        
    def getStyle(self, style_name, session):
        try:
            style = self.getGsconfig(session).get_style(style_name, workspace=None)
            return style
        
        except:
            e = sys.exc_info()[0]
            pass
        
    def setLayerStyle(self, layer_name, style, session):
        """
        Set default style
        """
        try:
            catalog = self.getGsconfig(session)
            layer = catalog.get_layer(layer_name)
            layer.default_style = style
            catalog.save(layer)
            return True
        except Exception as e:
            return False
        
    def get_layer_properties(self, s, ws, layer):
        try:
            properties = WebMapService(self.base_url + "/wms", version='1.1.1', xml=None, username=s['username'], password=s['password'])
            layer_properties = properties[ws.name + ':' + layer.name]
            return layer_properties
        
        except Exception as e:
            raise e
        
        
    def get_geometry_type(self, layer, session):
        try:           
            datastore = Datastore.objects.get(id=layer.datastore_id)
            if layer.type == 'v_PostGIS' or layer.type == 'v_PostGIS_View':
                workspace = Workspace.objects.get(id=datastore.workspace_id)
                result = self.rest_catalog.get_feature_type(workspace.name, datastore.name, layer.name, user=session['username'], password=session['password'])
                attr_list = result['featureType']['attributes']['attribute']
                type = ''
                for attr in attr_list:
                    if 'com.vividsolutions.jts.geom' in attr['binding']:
                        geom = attr['binding']
                        if 'Polygon' in geom:
                            type = 'polygon'
                        elif 'LineString' in geom:
                            type = 'line'                           
                        elif 'Point' in geom:
                            type = 'point'
                
                return type
            
            else:
                return 'raster'
        
        except Exception as e:
            return False
        
    def createDefaultStyle(self, layer, name, session):
        """
        Create new style
        """
        data = ''
        symbolizer = ''
        
        geom_type = self.get_geometry_type(layer, session)
        symbol_type = None
        if geom_type == 'point':
            symbol_type = 'PointSymbolizer'           
        elif geom_type == 'line':
            symbol_type = 'LineSymbolizer'
        elif geom_type == 'polygon':
            symbol_type = 'PolygonSymbolizer'
        elif geom_type == 'raster':
            symbol_type = 'RasterSymbolizer'
        
        data += '<?xml version="1.0" encoding="ISO-8859-1"?>' 
        data += '<StyledLayerDescriptor version="1.0.0" xmlns="http://www.opengis.net/sld" xmlns:ogc="http://www.opengis.net/ogc" '
        data += 'xmlns:sld="http://www.opengis.net/sld"  xmlns:gml="http://www.opengis.net/gml" ' 
        data += 'xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
        data += 'xsi:schemaLocation="http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd">'
        data +=     '<NamedLayer>' 
        data +=         '<Name>Default Styler</Name>' 
        data +=         '<UserStyle>' 
        data +=             '<Name>' + name + '</Name>'
        data +=             '<Title>Style for: ' + layer.title + '</Title>' 
        data +=             '<FeatureTypeStyle>' 
        data +=                 '<Rule>' 
        
        if symbol_type == 'PolygonSymbolizer':
            symbolizer +=   '<PolygonSymbolizer>' 
            symbolizer +=       '<Fill>' 
            symbolizer +=           '<CssParameter name="fill">#383838</CssParameter>' 
            symbolizer +=           '<CssParameter name="fill-opacity">0.6</CssParameter>'
            symbolizer +=       '</Fill>' 
            symbolizer +=       '<Stroke>' 
            symbolizer +=           '<CssParameter name="stroke">#000000</CssParameter>' 
            symbolizer +=           '<CssParameter name="stroke-width">1</CssParameter>' 
            symbolizer +=       '</Stroke>' 
            symbolizer +=   '</PolygonSymbolizer>'
            
        elif symbol_type == 'LineSymbolizer':
            symbolizer +=   '<LineSymbolizer>' 
            symbolizer +=       '<Stroke>' 
            symbolizer +=           '<CssParameter name="stroke">#000000</CssParameter>' 
            symbolizer +=           '<CssParameter name="stroke-width">1</CssParameter>' 
            symbolizer +=       '</Stroke>' 
            symbolizer +=   '</LineSymbolizer>'
            
        elif symbol_type == 'PointSymbolizer':
            symbolizer +=   '<PointSymbolizer>' 
            symbolizer +=       '<Graphic>'
            symbolizer +=           '<Mark>'
            symbolizer +=               '<WellKnownName>circle</WellKnownName>'
            symbolizer +=               '<Fill>' 
            symbolizer +=                   '<CssParameter name="fill">#383838</CssParameter>' 
            symbolizer +=                   '<CssParameter name="fill-opacity">0.6</CssParameter>'
            symbolizer +=               '</Fill>' 
            symbolizer +=               '<Stroke>' 
            symbolizer +=                   '<CssParameter name="stroke">#000000</CssParameter>' 
            symbolizer +=                   '<CssParameter name="stroke-width">1</CssParameter>' 
            symbolizer +=               '</Stroke>' 
            symbolizer +=               '<Opacity>1.0</Opacity>'
            symbolizer +=               '<Size>6</Size>'
            symbolizer +=           '</Mark>'
            symbolizer +=       '</Graphic>'
            symbolizer +=   '</PointSymbolizer>'
            
        elif symbol_type == 'RasterSymbolizer':
            symbolizer +=   '<RasterSymbolizer>'
            symbolizer +=       '<Opacity>1.0</Opacity>'
            symbolizer +=   '</RasterSymbolizer>'
            
        data += symbolizer 
        data +=                 '</Rule>' 
        data +=             '</FeatureTypeStyle>' 
        data +=         '</UserStyle>' 
        data +=     '</NamedLayer>' 
        data += '</StyledLayerDescriptor>'
        
        try:
            catalog = self.getGsconfig(session)
            if catalog.get_style(name, workspace=None) == None:
                catalog.create_style(name, data.encode('utf-8'), overwrite=False, workspace=None, style_format="sld10", raw=False)
            tp = 'US'
            if geom_type == 'raster':
                tp = 'CT'
                
            style = Style(name=name, title=_('Style for: ') + layer.title, is_default=True, type=tp, order=0)
            style.save()

            style_layer = StyleLayer(style=style, layer=layer)
            style_layer.save()
            
            rule = Rule(
                name = _('Default symbol'),
                title = _('Default symbol'),
                type = symbol_type,
                order = 0,
                minscale = -1,
                maxscale = -1
            )
            rule.save()
            
            style_rule = StyleRule(
                style=style,
                rule=rule
            )
            style_rule.save()
            
            json = None
            if symbol_type == 'PointSymbolizer':
                json = {
                    "id":"pointsymbolizer0",
                    "type":"PointSymbolizer",
                    "name":"PointSymbolizer 0",
                    "shape": "circle",
                    "fill_color":"#383838",
                    "fill_opacity":0.6,
                    "border_color":"#000000",
                    "border_size":1,
                    "border_opacity":1,
                    "border_type":"solid",
                    "rotation":0,
                    "size":10,
                    "order":0
                }
                
            elif symbol_type == 'LineSymbolizer':
                json = {
                    "id":"linesymbolizer0",
                    "type":"LineSymbolizer",
                    "name":"LineSymbolizer 0",
                    "fill_color":"#383838",
                    "fill_opacity":0.5,
                    "border_color":"#000000",
                    "border_size":1,
                    "border_opacity":1,
                    "border_type":"solid",
                    "rotation":0,
                    "order":0
                }
                
            elif symbol_type == 'PolygonSymbolizer':
                json = {
                    "id":"polygonsymbolizer0",
                    "type":"PolygonSymbolizer",
                    "name":"PolygonSymbolizer 0",
                    "fill_color":"#383838",
                    "fill_opacity":0.5,
                    "border_color":"#000000",
                    "border_size":1,
                    "border_opacity":1,
                    "border_type":"solid",
                    "rotation":0,
                    "order":0
                }
            
            symb = Symbolizer(
                rule=rule,
                type=symbol_type,
                sld=symbolizer,
                json= str(json).replace("'", '"'),
                order=0
            )   
            symb.save()
                    
            return True
        
        except Exception as e:
            return False
        
    def createStyle(self, name, data, session):
        """
        Create new style
        """
        try:
            self.getGsconfig(session).create_style(name, data.encode('utf-8'), overwrite=False, workspace=None, style_format="sld10", raw=False)
            return True
        
        except Exception as e:
            return False
        
    def updateStyle(self, style_name, sld_body, session):
        """
        Update a style
        """
            
        try:
            self.rest_catalog.update_style(style_name, sld_body, user=session['username'], password=session['password'])
            return True
        
        except Exception as e:
            print e
            return False
        
    def deleteStyle(self, name, session):
        """
        Delete a style
        """
        try:
            catalog = self.getGsconfig(session)
            style = catalog.get_style(name, workspace=None)
            catalog.delete(style, purge=True, recurse=False)
            return True
        
        except Exception as e:
            return False
        
    def deleteLayerStyles(self, lyr, session):
        try:
            layer_styles = StyleLayer.objects.filter(layer=lyr)
    
            for layer_style in layer_styles:
                style = Style.objects.get(id=layer_style.style_id)
                catalog = self.getGsconfig(session)
                gs_style = catalog.get_style(style.name, workspace=None)
                catalog.delete(gs_style, purge=True, recurse=False)
                layer_style.delete()
                style_rules = StyleRule.objects.filter(style=style)
                for style_rule in style_rules:
                    rule = Rule.objects.filter(id=style_rule.rule.id)
                    symbolizers = Symbolizer.objects.filter(rule=rule)
                    for symbolizer in symbolizers:
                        symbolizer.delete()
                    rule.delete()
                    style_rule.delete()
                style.delete()
                
            return True
        
        except Exception as e:
            return False
        
    def updateBoundingBoxFromData(self, layer, session):
        store = layer.datastore
        if store.type[0]=="v":
            self.rest_catalog.update_ft_bounding_box(layer.datastore.workspace.name, layer.datastore.name, layer.name, user=session['username'], password=session['password'])
        # not available/necessary for coverages
            

    def createResource(self, workspace, store, name, title, session):
        if store.type[0]=="v":
            return self.createFeaturetype(workspace, store, name, title, session)
        else:
            return self.createCoverage(workspace, store, name, title, session)   

    def createFeaturetype(self, workspace, datastore, name, title, session):
        try:
            return self.rest_catalog.create_feature_type(name, title, datastore.name, workspace.name, user=session['username'], password=session['password'])
        except rest_geoserver.FailedRequestError as e:
            raise rest_geoserver.FailedRequestError(e.status_code, _("Error publishing the layer. Backend error: {msg}").format(msg=e.get_message()))
        except Exception as e:
            raise rest_geoserver.FailedRequestError(-1, _("Error: layer could not be published"))
        
    def createCoverage(self, workspace, coveragestore, name, title, session):
        try:
            return self.rest_catalog.create_coverage(name, title, coveragestore.name, workspace.name, user=session['username'], password=session['password'])
        except rest_geoserver.FailedRequestError as e:
            raise rest_geoserver.FailedRequestError(e.status_code, _("Error publishing the layer. Backend error: {msg}").format(msg=e.get_message()))
        except Exception as e:
            raise rest_geoserver.FailedRequestError(-1, _("Error: layer could not be published"))
        
    def createOrUpdateGeoserverLayerGroup(self, layer_group, session):
        try:
            if layer_group.name != "__default__":
                return self.rest_catalog.create_or_update_gs_layer_group(layer_group.name, layer_group.title, user=session['username'], password=session['password'])
            return True
        except rest_geoserver.FailedRequestError as e:
            raise rest_geoserver.FailedRequestError(e.status_code, _("Error publishing the layer group. Backend error: {msg}").format(msg=e.get_message()))
        except Exception as e:
            raise rest_geoserver.FailedRequestError(-1, _("Error: layer group could not be published"))
        
    def deleteGeoserverLayerGroup(self, layer_group, session):
        try:
            return self.rest_catalog.delete_gs_layer_group(layer_group, user=session['username'], password=session['password'])
        except rest_geoserver.FailedRequestError as e:
            raise rest_geoserver.FailedRequestError(e.status_code, _("Error publishing the layer group. Backend error: {msg}").format(msg=e.get_message()))
        except Exception as e:
            raise rest_geoserver.FailedRequestError(-1, _("Error: layer group could not be published"))
    
    def deleteResource(self, workspace, datastore, layer, session, purge=None):
        try:
            catalog = self.getGsconfig(session)
            resource = catalog.get_resource(layer.name, datastore.name, workspace.name)
            # FIXME: should we purge the resource (i.e. delete the layer on disk/db)?
            if resource is not None:
                try:
                    catalog.delete(resource, purge, True)
                except Exception as e:
                    # only fail if layer exists but deletion failed
                    return False
        except:
            # only fail if layer exists but deletion failed
            pass
        return True

    def updateResource(self, workspace, datastore, name, title, session):
        try:
            catalog = self.getGsconfig(session)
            resource = catalog.get_resource(name, datastore, workspace)
            resource.name = name
            resource.title = title
            catalog.save(resource)
            return True
        except Exception as exc:
            print exc
            return False
            
    def _get_unique_resource_name(self, datastore, workspace, session):
        name = datastore
        i = 0
        while self.getGsconfig(session).get_resource(name, None, workspace):
            name = datastore + str(i)
            i = i + 1
        return name     
    
    def getResources(self, workspace, datastore, dstype, session, available=False):
        try:
            store = self.getGsconfig(session).get_store(datastore, workspace)
            format_nature=dstype[0]
            if (format_nature=='v'):
                return store.get_resources(available=available)
            elif (format_nature=='c'):
                driver=dstype[2:]
                resources_obj = store.get_resources()
                # The API doesn't allow to retrieve the available coverages nor their names,
                # but these drivers allow a single coverage to be published on the coverage store
                if len(resources_obj) > 0:
                    # there is no available coverages if they is already one published coverage
                    return []
                else:
                    # we can't get the name of the coverage, so we just offer a sensible, non existing name
                    return [self._get_unique_resource_name(datastore, workspace, session)]
        except:
            e = sys.exc_info()[0]
            pass
        
        
    def getResourceInfo(self, workspace, store, featureType, type, session):
        if type == None:
            type = "json"
        url = self.rest_catalog.service_url + "/workspaces/" + workspace + "/datastores/" + store + "/featuretypes/" + featureType +"."+type
        r = self.rest_catalog.session.get(url, auth=(session['username'], session['password']))
        if r.status_code==200:
            content = r.content
            jsonData = json.loads(content)
            return jsonData
        return None
    
    def getRasterResourceInfo(self, workspace, store, featureType, type, session):
        if type == None:
            type = "json"
        url = self.rest_catalog.service_url + "/workspaces/" + workspace + "/coveragestores/" + store + "/coverages/" + featureType +"."+type
        r = self.rest_catalog.session.get(url, auth=(session['username'], session['password']))
        if r.status_code==200:
            content = r.content
            jsonData = json.loads(content)
            return jsonData
        return None

    def getLayerCreateTypes(self):
        return self.layer_create_types
    
    def getLayerCreateForm(self, layer_type):
        if layer_type==Geoserver.CREATE_TYPE_SQL_VIEW:
            return (forms_geoserver.CreateSqlViewForm,  "geoserver/create_layer_sql_view.html")
        if layer_type==Geoserver.CREATE_TYPE_VECTOR_LAYER:
            return (forms_geoserver.CreateFeatureTypeForm,  "geoserver/create_layer_feature_type.html")
        return (None, None)
    
    def getUploadForm(self, datastore_type):
        generic_raster = ["c_WorldImage", 'c_ArcGrid', 'c_GeoTIFF']
        generic_vector = ["v_PostGIS", 'v_SHP'] 
        
        # ensure type is a supported data store type
        if datastore_type=="c_ImageMosaic":
            return (forms_geoserver.ImageMosaicUploadForm,  "geoserver/layer_upload_imagemosaic.html", "application/zip")
        if datastore_type=="c_GeoTIFF":
            return (forms_geoserver.RasterLayerUploadForm, "geoserver/layer_upload_raster.html", "image/tiff")
        elif datastore_type=="v_PostGIS":
            return (forms_geoserver.PostgisLayerUploadForm, "geoserver/layer_upload_postgis.html", "application/zip")
        elif datastore_type in generic_vector:
            #return (forms_geoserver.VectorLayerUploadForm, "geoserver/layer_upload_vector.html", "application/zip,application/gml+xml")
            return (forms_geoserver.VectorLayerUploadForm, "geoserver/layer_upload_vector.html", "application/zip")
        elif datastore_type in generic_raster:
            return (forms_geoserver.RasterLayerUploadForm, "geoserver/layer_upload_raster.html", "application/zip")
        return (None, None, None)
    
    def __create_mosaic_indexer(self, date_regex, ele_regex):
        (fd, abspath) = tempfile.mkstemp()
        schema = "Schema=*the_geom:Polygon,location:String"
        if date_regex != '':
            os.write(fd, "TimeAttribute=date\n")
            schema = schema + ",date:java.util.Date"
            os.write(fd, "PropertyCollectors=TimestampFileNameExtractorSPI[timeregex](date)\n") 
        if ele_regex != '':
            os.write(fd, "ElevationAttribute=elevation\n")
            schema = schema + ",elevation:Integer"
        schema = schema + "\n"
        os.write(fd, schema)
        os.close(fd)
        return abspath
    
    def __create_mosaic_time_regexp(self, pattern="(?<=_)[0-9]{8}"):
        (fd, abspath) = tempfile.mkstemp()
        os.write(fd, "regex="+pattern+"\n")
        os.close(fd)
        return abspath
    
    def __create_mosaic_ele_regexp(self, pattern="(?<=_)(\\d{4}\\.\\d{3})"):
        (fd, abspath) = tempfile.mkstemp()
        os.write(fd, "regex="+pattern+"\n")
        os.close(fd)
        return abspath
    
    def __create_datastore_properties(self):
        mosaic_db = GVSIGOL_SERVICES.get('MOSAIC_DB')
        if mosaic_db is not None:
            (fd, abspath) = tempfile.mkstemp()
            os.write(fd, "SPI=org.geotools.data.postgis.PostgisNGDataStoreFactory\n")
            os.write(fd, "host={0}\n".format(mosaic_db.get('host')))
            os.write(fd, "port={0}\n".format(mosaic_db.get('port')))
            os.write(fd, "database={0}\n".format(mosaic_db.get('database')))
            os.write(fd, "schema={0}\n".format(mosaic_db.get('schema')))
            os.write(fd, "user={0}\n".format(mosaic_db.get('user')))
            os.write(fd, "passwd={0}\n".format(mosaic_db.get('passwd')))
            os.write(fd, "Loose\ bbox=true\n")
            os.write(fd, "Estimated\ extends=false\n")
            os.write(fd, "validate\ connections=true\n")
            os.write(fd, "Connection\ timeout=10\n")
            os.write(fd, "preparedStatements=true\n")
            os.close(fd)
            return abspath
    
    def __get_file_upload_path(self, f):
        try:
            # temporary upload handler
            return f.temporary_file_path()
        except:
            pass
        # memory upload handler, small file
        (destination, abspath) = tempfile.mkstemp(suffix='', prefix='tmp-golupld-')
        for chunk in f.chunks():
            os.write(destination, chunk)
        os.close(destination)
        return abspath
    
    def __is_raster_file(self, f):
        ext = os.path.splitext(f)[1].lower()
        return (ext in self.raster_extensions)
    
    def __rename_folder_contents(self, folder, layer_name):
        raster_files = [ f for f in os.listdir(folder) if self.__is_raster_file(f)]
        if len(raster_files)==1:
            root_name = os.path.splitext(raster_files[0])[0]
            root_length = len(root_name)
            for f in os.listdir(folder):
                if f[:root_length]==root_name:
                    # handle also cases such as img.jpg + img.jpg.aux.xml
                    ext = f[root_length:]
                    old_name = os.path.join(folder, f)
                    new_name = os.path.join(folder, layer_name+ext)
                try:
                    os.rename(old_name, new_name)
                except:
                    logging.error(u"Error renaming:  " + unicode(old_name) + " to " + unicode(new_name))                

    def __get_uncompressed_file_upload_path(self, f, store_type):
        if store_type!="c_GeoTIFF":
            dir_path = tempfile.mkdtemp(suffix='', prefix='tmp-golupld-')
            z = zipfile.ZipFile(f, "r")
            z.extractall(dir_path)
            return dir_path
        else:
            # individual file, return the file path
            try:
                # temporary upload handler
                return f.temporary_file_path()
            except:
                pass
            # memory upload handler, we need to extract it to a real file
            (destination, abspath) = tempfile.mkstemp(suffix='', prefix='tmp-golupld-')
            for chunk in f.chunks():
                os.write(destination, chunk)
            os.close(destination)
            return abspath
    
    def __delete_temporaries(self, file_path):
        try:
            # delete the whole dir if file_path is a dir
            # otherwise just delete file_path
            if os.path.isdir(file_path):
                shutil.rmtree(file_path)
            else:
                os.remove(file_path)
        except:
            # ignore any errors deleting temporaries
            pass
        
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
    
    def __compress_folder(self, file_path):
        (fd, zip_path) = tempfile.mkstemp(prefix='tmp-golupld-', suffix=".zip")
        os.close(fd)
        z = zipfile.ZipFile(zip_path, "w")
        for root, dirs, files in os.walk(file_path):
            for f in files:
                print os.path.join(root, f)
                z.write(os.path.join(root, f), f)
        z.close()
        return zip_path

    def __process_image_mosaic_zipfile(self, form_data, zip_path):
        ele_regex = form_data.get('ele_regex', '')
        date_regex = form_data.get('date_regex', '')
        has_dimensions = date_regex != '' or ele_regex != ''
        if has_dimensions:
            indexer = self.__create_mosaic_indexer(date_regex, ele_regex)
            try: 
                z = zipfile.ZipFile(zip_path, "a")
                samplename = z.namelist()[0]
                z.write(indexer, "indexer.properties")
                os.remove(indexer)
                if date_regex != "":
                    if re.search(date_regex, samplename) == None:
                        raise  WrongTimePattern()
                    regexp_file = self.__create_mosaic_time_regexp(date_regex)
                    z.write(regexp_file, "timeregex.properties")
                    os.remove(regexp_file)
                if ele_regex != "":
                    if re.search(ele_regex, samplename) == None:
                        raise  WrongElevationPattern()
                    regexp_file = self.__create_mosaic_ele_regexp(ele_regex)
                    z.write(regexp_file, "elevationregex.properties")
                    os.remove(regexp_file)
                ds_properties = self.__create_datastore_properties()
                if ds_properties is not None:
                    z.write(ds_properties, "datastore.properties")
                    os.remove(ds_properties)
            except (WrongTimePattern, WrongElevationPattern):
                raise
            except:
                raise BadFormat()
            z.close()
    
    def __enable_image_mosaic_dimensions(self, workspace_name, layer_name, date_regex, ele_regex, session):
        logging.error("get_resource: "+layer_name+", "+layer_name+", "+workspace_name)
        catalog = self.getGsconfig(session)
        coverage = catalog.get_resource(layer_name, layer_name, workspace_name)
        md = dict(coverage.metadata)
        if date_regex != "":
            md['time'] = DimensionInfo(name='time',
                                                      enabled=True,
                                                      presentation="LIST",
                                                      resolution=None,
                                                      units="ISO8601",
                                                      unitSymbol=None,
                                                      strategy="MINIMUM"
                                                      )
        if ele_regex!="":
            #FIXME: we could have units different than meters
            md['elevation'] = DimensionInfo(name='elevation',
                                              enabled=True,
                                              presentation="LIST",
                                              resolution=None,
                                              units="EPSG:5030",
                                              unitSymbol= "m",
                                              strategy="MINIMUM"
                                              )
        coverage.metadata = md
        catalog.save(coverage)
        
    def __test_zip_structure(self, zip_path):
        z = zipfile.ZipFile(zip_path, "r")
        for n in z.namelist():
            if n.endswith("/"):
                z.close()
                raise BadFormat(-1, _("Bad file format. The provided zip file must not contain any subdirectory."))
        z.close()
    
    def __update_raster_stats(self, workspace, coveragestore, coverage, old_conf, stats, session):
        try:
            dimensions = old_conf["coverage"]["dimensions"]["coverageDimension"]
            for idx, d in enumerate(dimensions):
                #d["@class"] = "org.geoserver.catalog.CoverageDimensionInfo"
                d["description"] = "GridSampleDimension[" + str(stats[idx][0]) + "," + str(stats[idx][1]) + "]"
                d["range"] = {"min":stats[idx][0], "max": stats[idx][1]}
            #conf = { "coverage": { "dimensions": {"coverageDimension": dimensions }}}
            self.rest_catalog.update_coverage(workspace, coveragestore, coverage, old_conf, user=session['username'], password=session['password'])
            
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
    
    def __do_shpdir2postgis(self, datastore, application, dir_path, layergroup, session, table_definition, creation_mode, defaults):
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

            # load SHP       
            files = [f for f in os.listdir(dir_path) if f.lower()[-4:]==".shp"]
            
            for f in files:
                if f in table_definition:
                    table_def = table_definition[f]
                    layer_name = table_def['name']
                    layer_title = table_def['title']
                    try:
                        layer_style = table_def['style']
                    except Exception as e:
                        layer_style = "Desconocido"
                        print e
                    #layer_group = table_def['group'] + '_' + application.name.lower()
                else:
                    layer_name = os.path.splitext(os.path.basename(f))[0]
                    layer_title = os.path.splitext(os.path.basename(f))[0]
                    layer_style = layer_name
                shp_abs = os.path.join(dir_path, f)
                gdal_tools.shp2postgis(shp_abs, layer_name, srs, host, port, db, schema, user, password, creation_mode, encoding)
                
                                
                if creation_mode==forms_geoserver.MODE_CREATE:
                    try:
                        self.createFeaturetype(datastore.workspace, datastore, layer_name, layer_title, session)
                    except:
                        raise
                    
                    try:
                        layer = Layer.objects.get(name=layer_name, datastore=datastore)
                    except:
                        # may me missing when creating a layer or when
                        # appending / overwriting a layer created outside gvsig online
                        layer = Layer()
                        
                    layer.datastore = datastore
                    layer.name = layer_name
                    layer.visible = False
                    layer.queryable = True
                    layer.cached = True
                    layer.single_image = False
                    layer.layer_group = layergroup
                    layer.title = layer_title
                    layer.type = datastore.type
                    layer.metadata_uuid = ''
                    layer.save()
    
                    self.setDataRules(session=session)
                    
                    # estilos                            
                    if self.getStyle(layer_style, session): 
                        self.setLayerStyle(layer.name, layer_style, session=session)
                    else:
                        style_name = layer_style + '_default'
                        self.createDefaultStyle(layer, style_name, session=session)
                        self.setLayerStyle(layer.name, style_name, session=session)                        
                        
                    if layer.layer_group.name != "__default__":
                        self.createOrUpdateGeoserverLayerGroup(layer.layer_group, session)
                else:
                    print "TODO: borrar la cache .."
                            
        except (rest_geoserver.RequestError):
            print "Error Request"
            raise             
        except gdal_tools.GdalError as e:
            print "Error Gdal"
            raise rest_geoserver.RequestError(e.code, e.message)
        except Exception as e:
            logging.exception(e)
            raise rest_geoserver.RequestError(-1, _("Error creating the layer. Review the file format."))
    
    def __do_multi_upload_postgis(self, datastore, application, zip_path, session, table_definition):
        tmp_dir = None
        try: 
            # get & sanitize parameters
            srs = 'EPSG:25830'
            encoding = 'LATIN1'
            creation_mode = 'CR'
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

            # extract SHP
            tmp_dir = tempfile.mkdtemp()
            with ZipFile(zip_path, 'r') as z:
                z.extractall(tmp_dir)
            files = [f for f in os.listdir(tmp_dir) if f.lower()[-4:]==".shp"]
            
            for f in files:
                if f in table_definition:
                    table_def = table_definition[f]
                    layer_name = table_def['name']
                    layer_title = table_def['title']
                    layer_group = table_def['group'] + '_' + application.name.lower()
                    shp_abs = os.path.join(tmp_dir, f)
                    gdal_tools.shp2postgis(shp_abs, layer_name, srs, host, port, db, schema, user, password, creation_mode, encoding)
                    
                    try:
                        # layer has been uploaded to postgis, now register the layer on GS
                        # we don't check the creation mode because the users sometimes choose the wrong one
                        self.createFeaturetype(datastore.workspace, datastore, layer_name, layer_title, session)
                    except:
                        if creation_mode==forms_geoserver.MODE_CREATE:
                            # assume the layer was created if mode is append or overwrite, so don't raise the exception 
                            raise
                        
                    try:
                        layer = Layer.objects.get(name=layer_name, datastore=datastore)
                    except:
                        # may me missing when creating a layer or when
                        # appending / overwriting a layer created outside gvsig online
                        layer = Layer()
                        
                    layer.datastore = datastore
                    layer.name = layer_name
                    layer.visible = False
                    layer.queryable = True
                    layer.cached = True
                    layer.single_image = False
                    layer.layer_group = LayerGroup.objects.get(name__exact=layer_group)
                    layer.title = layer_title
                    layer.type = datastore.type
                    layer.metadata_uuid = ''
                    layer.save()
                    
                    self.setDataRules(session=session)
                         
                    if self.getStyle(layer.name, session): 
                        self.setLayerStyle(layer.name, layer.name, session=session)
                    else:
                        style_name = layer.name + '_default'
                        self.createDefaultStyle(layer, style_name, session=session)
                        self.setLayerStyle(layer.name, style_name, session=session)                        
                        
                    if layer.layer_group.name != "__default__":
                        self.createOrUpdateGeoserverLayerGroup(layer.layer_group, session)
                            
                        
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
    
    
    def __check_prj_file(self, folder):
        """
        Ensures there is a .prj file on the folder
        """
        for f in os.listdir(folder):
            if os.path.splitext(f)[1].lower()==".prj":
                return True
        return False
        
    def uploadLayer(self, form_data, store_type, file_upload, session):
        format_nature=store_type[:1]
        driver=store_type[2:]
        name = form_data['name']
        file_path = None
        folder_path = None
        
        if _valid_sql_name_regex.search(name) == None:
            raise InvalidValue(-1, _("Invalid layer name: '{value}'. Identifiers must begin with a letter or an underscore (_). Subsequent characters can be letters, underscores or numbers").format(value=name))
                    
        try:
            creation_mode = form_data.get('mode', forms_geoserver.MODE_CREATE)
            if format_nature=="c":
                workspace = form_data['workspace']
                if self.datastore_exists(workspace.name, name, session):
                    raise UserInputError(-1, _("A data store exists with the same name: {0}. Choose a different layer name.").format(name))
                try:
                    file_path = self.__get_uncompressed_file_upload_path(file_upload, store_type)
                    if store_type=="c_WorldImage":
                        self.__rename_folder_contents(file_path, name)
                        if not self.__check_prj_file(file_path):
                            raise BadFormat(-1, _("Error: The .prj file is missing"))
                    stats = self.__gdal_info_stats(file_path)
                    if store_type!="c_GeoTIFF":
                        folder_path = file_path
                        file_path = self.__compress_folder(folder_path)
                finally:
                    if folder_path:
                        self.__delete_temporaries(folder_path)
                
                try:
                    if store_type=="c_ImageMosaic":
                        ele_regex = form_data.get('ele_regex', '')
                        date_regex = form_data.get('date_regex', '')
                        has_dimensions = date_regex != '' or ele_regex != ''
                        if has_dimensions:
                            self.__process_image_mosaic_zipfile(form_data, file_path)
                    response = self.rest_catalog.upload_coverage(workspace.name, name, driver.lower(), file_path, user=session['username'], password=session['password'])
                    self.getGsconfig(session).reload()
                    try:
                        conf = self.rest_catalog.get_coverage(workspace.name, name, name, user=session['username'], password=session['password'])
                        self.__update_raster_stats(workspace.name, name, name, conf, stats, session)
                    except:
                        logging.error("__update_raster_stats failed!! Layer: " + name)
                    if store_type=="c_ImageMosaic":
                        # the coverage has been uploaded and created
                        # now let's enable the dimensions
                        if has_dimensions:
                            self.__enable_image_mosaic_dimensions(workspace.name, name, date_regex, ele_regex, session)
                except Exception as e:
                    logging.exception(str(e))
                    if isinstance(e, rest_geoserver.UploadError):
                        if e.status_code==500:
                            try:
                                # sometimes a broken store is created on a failed upload. Ensure it gets deleted
                                self.rest_catalog.delete_coveragestore(workspace.name, name, rest_geoserver.PURGE_ALL, recurse=True, user=session['username'], password=session['password'])
                            except Exception as e:
                                pass
                            if store_type=="c_ImageMosaic":
                                e.set_message(_("Error uploading the layer. Review the file format and ensure the indexes database does not contain a table with the same name. Backend message: {0}").format(e.get_message()))
                                raise e
                        e.set_message(_("Error uploading the layer. Review the file format. Backend message: {0}").format(e.get_message()))
                    raise e
                finally:
                    if file_path:
                        os.remove(file_path)
                ds = Datastore()
                ds.name = name
                ds.workspace = form_data['workspace']
                ds.type = store_type
                try:
                    response_tree = ET.fromstring(response)
                    response_url = response_tree.find("url").text
                except:
                    response_url = "file:data/{0}/{1}".format(ds.workspace, ds.name)
                params = { 'url': response_url}
                ds.connection_params = json.dumps(params)
                ds.save()
            elif format_nature=="v":
                self.__test_zip_structure(file_upload)
                ds = form_data['datastore']
                title = form_data['title']
                if store_type=="v_PostGIS":
                    # GML not supported for the moment. We could support them by using ogr2ogr instead pf shp2pgslq 
                    #if file_upload.name[:-4].lower()==".gml":
                    #    content_type = "application/gml+xml"
                    self.__do_upload_postgis(name, ds, form_data, file_upload)
                        #os.remove(zip_path)
                    try:
                        # layer has been uploaded to postgis, now register the layer on GS
                        # we don't check the creation mode because the users sometimes choose the wrong one
                        self.createFeaturetype(ds.workspace, ds, name, title, session)
                    except:
                        if creation_mode==forms_geoserver.MODE_CREATE:
                            # assume the layer was created if mode is append or overwrite, so don't raise the exception 
                            raise
                else:                    
                    self.rest_catalog.upload_feature_type(ds.workspace.name, ds.name, name, driver.lower(), file_upload, user=session['username'], password=session['password'])
            else:
                raise UnsupportedRequestError()
            try:
                l = Layer.objects.get(name=name, datastore=ds)
            except:
                # may me missing when creating a layer or when
                # appending / overwriting a layer created outside gvsig online
                l = Layer()
            l.datastore = ds
            l.name = name
            l.visible = form_data.get('visible', False) # it will be missing on the form when false
            l.queryable = form_data.get('queryable', False) # it will be missing on the form when false
            l.cached = form_data.get('cached', False) # it will be missing on the form when false
            l.single_image = form_data.get('single_image', False) # it will be missing on the form when false
            l.layer_group = form_data.get('layer_group', LayerGroup.objects.get(name='__default__'))
            l.title = form_data['title']
            l.type = ds.type
            l.save()
            return l
        finally:
            if file_path:
                self.__delete_temporaries(file_path)
                
    def uploadMultiLayer(self, datastore, application, file_upload, session, table_definition):
        try:
            self.__test_zip_structure(file_upload)
            self.__do_multi_upload_postgis(datastore, application, file_upload, session, table_definition)
        
        except Exception as e:
            print e
    
    def shpdir2postgis(self, datastore, application, dir_path, layergroup, session, table_definition,creation_mode, defaults):
        try:
            self.__do_shpdir2postgis(datastore, application, dir_path, layergroup, session, table_definition, creation_mode, defaults)        
        except Exception as e:
            print e
            raise e
    
    
    def __field_def_to_gs(self, field_def_array, geometry_type):
        try:
            fields = []
            if geometry_type in ["Point", "MultiPoint", "LineString", "MultiLineString", "Polygon", "MultiPolygon"]:
                jts_type = 'com.vividsolutions.jts.geom.' + geometry_type
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
                field['name'] = f[0]
                sql_type = f[1]
                if sql_type == "integer":
                    field['binding'] = "java.lang.Integer"
                elif sql_type == "double":
                    field['binding'] = "java.lang.Double"
                elif sql_type == "text":
                    field['binding'] = "java.lang.String"
                elif sql_type == "date":
                    field['binding'] = "java.sql.Date"
                elif sql_type == "boolean":
                    field['binding'] = "java.lang.Boolean"
                else:
                    raise rest_geoserver.RequestError(_("Unsupported field type: {0}").format(sql_type))
                fields.append(field)
                
            if len(fields)>1:
                return fields
            raise rest_geoserver.RequestError(_("At least one field must be defined"))
            
        except:
            raise rest_geoserver.RequestError(_("Invalid field definition"))
        
    def createLayer(self, form_data, layer_type, session):
        name = form_data['name']

        if _valid_sql_name_regex.search(name) == None:
            raise InvalidValue(-1, _("Invalid layer name: '{value}'. Identifiers must begin with a letter or an underscore (_). Subsequent characters can be letters, underscores or numbers").format(value=name))
        
        datastore = form_data['datastore']
        workspace = datastore.workspace
        
        if self.resource_exists(workspace.name, name, session):
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
                self.rest_catalog.create_sql_view(workspace.name, datastore.name, name, sql_statement, key_column, geom_column, geom_type, srid, None, title=title, user=session['username'], password=session['password'])
            except rest_geoserver.FailedRequestError as e:
                if "Error occurred building feature type" in e.get_message():
                    e.message = _("Error occurred building the view. Review the SQL sentence")
                raise
        elif layer_type==Geoserver.CREATE_TYPE_VECTOR_LAYER:
            fields = key_column = self.__field_def_to_gs(form_data.get('fields'), geom_type)
            try:
                extraParams = {"nativeBoundingBox": {"minx": 0, "maxx": 1, "miny": 0, "maxy":1 , "crs":srs}}
                self.rest_catalog.create_feature_type(name, title, datastore.name, workspace.name, srs=srs, fields=fields, user=session['username'], password=session['password'], extraParams=extraParams)
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
        l.visible = form_data.get('visible', False) # it will be missing on the form when false
        l.queryable = form_data.get('queryable', False) # it will be missing on the form when false
        l.cached = form_data.get('cached', False) # it will be missing on the form when false
        l.single_image = form_data.get('single_image', False) # it will be missing on the form when false
        l.layer_group = form_data.get('layer_group', LayerGroup.objects.get(name='__default__'))
        l.title = title
        l.type = 'v_PostGIS_View'
        l.save()
        return l
    
    def setDataRules(self, session):
        
        url = self.rest_catalog.get_service_url() + "/security/acl/layers.json"
        services_url = self.rest_catalog.get_service_url() + "/security/acl/services.json"

        rules = DataRule.objects.all()
        for r in rules:
            self.rest_catalog.get_session().delete(self.rest_catalog.get_service_url() + "/security/acl/layers/" + r.path, verify=False, auth=(session['username'], session['password']))
            r.delete()
        self.rest_catalog.get_session().delete(self.rest_catalog.get_service_url() + "/security/acl/services/wfs.Transaction", verify=False, auth=(session['username'], session['password']))
        
        layers = Layer.objects.all()  
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
                        
            self.rest_catalog.get_session().post(url, json=data, verify=False, auth=(session['username'], session['password']))
            
        if  len(transaction_roles) > 0:
            service = {}
            service_write_roles =  ",".join(transaction_roles)
            service['wfs.Transaction'] = service_write_roles
            self.rest_catalog.get_session().post(services_url, json=service, verify=False, auth=(session['username'], session['password']))
            
            
    def clearCache(self, ws, layer, session):
        try:
            self.rest_catalog.clear_cache(ws, layer, user=session['username'], password=session['password'])
            return True
        
        except Exception as e:
            print e
            return False
        
    def clearLayerGroupCache(self, name, session):
        try:
            self.rest_catalog.clear_layergroup_cache(name, user=session['username'], password=session['password'])
            return True
        
        except Exception as e:
            print e
            return False
        
    def addGridSubset(self, ws, layer, session):
        try:
            self.rest_catalog.add_grid_subset(ws, layer, user=session['username'], password=session['password'])
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
            result = []
            for r in rows:
                srs = "EPSG:"+str(r[4])
                result.append({"schema": r[0], "name": r[1], "geom_column": r[2], "geom_type": r[5], "srs": srs, 'key_column': r[6], 'fields': r[7]})
            return result
        except Exception as e:
            print str(e)
            raise
        
    def getFeatureCount(self, request, url, layer_name, f):   
        if filter != '':
            values = {
                'SERVICE': 'WFS',
                'VERSION': '1.1.0',
                'REQUEST': 'GetFeature',
                'TYPENAME': layer_name,
                'OUTPUTFORMAT': 'text/xml; subtype=gml/3.1.1',
                'RESULTTYPE': 'hits',
                'FILTER': f.encode('utf-8')
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
            
        req = requests.Session()
        if 'username' in request.session and 'password' in request.session:
            req.auth = (request.session['username'], request.session['password'])
    
        response = req.post(url, data=values, verify=False)
        root = ET.fromstring(response.text)
        numberOfFeatures = int(root.attrib['numberOfFeatures'])
        
        return numberOfFeatures
        
            
"""
Resource json example:
{
  "featureType": {
    "name": "poly_landmarks",
    "nativeName": "poly_landmarks",
    "namespace": {
      "name": "tiger",
      "href": "http://localhost:8080/geoserver/rest/namespaces/tiger.json"
    },
    "title": "Manhattan (NY) landmarks",
    "abstract": "Manhattan landmarks, identifies water, lakes, parks, interesting buildilngs",
    "keywords": {
      "string": [
        "landmarks",
        "DS_poly_landmarks",
        "manhattan",
        "poly_landmarks"
      ]
    },
    "nativeCRS": "GEOGCS[\"GCS_WGS_1984\", \n  DATUM[\"WGS_1984\", \n    SPHEROID[\"WGS_1984\", 6378137.0, 298.257223563]], \n  PRIMEM[\"Greenwich\", 0.0], \n  UNIT[\"degree\", 0.017453292519943295], \n  AXIS[\"Longitude\", EAST], \n  AXIS[\"Latitude\", NORTH]]",
    "srs": "EPSG:4326",
    "nativeBoundingBox": {
      "minx": -74.047185,
      "maxx": -73.90782,
      "miny": 40.679648,
      "maxy": 40.882078,
      "crs": "EPSG:4326"
    },
    "latLonBoundingBox": {
      "minx": -74.047185,
      "maxx": -73.90782,
      "miny": 40.679648,
      "maxy": 40.882078,
      "crs": "EPSG:4326"
    },
    "projectionPolicy": "FORCE_DECLARED",
    "enabled": true,
    "metadata": {
      "entry": [
        {
          "@key": "indexingEnabled",
          "$": "false"
        },
        {
          "@key": "cacheAgeMax",
          "$": "3600"
        },
        {
          "@key": "cachingEnabled",
          "$": "true"
        },
        {
          "@key": "dirName",
          "$": "DS_poly_landmarks_poly_landmarks"
        },
        {
          "@key": "kml.regionateFeatureLimit",
          "$": "10"
        }
      ]
    },
    "store": {
      "@class": "dataStore",
      "name": "nyc",
      "href": "http://localhost:8080/geoserver/rest/workspaces/tiger/datastores/nyc.json"
    },
    "maxFeatures": 0,
    "numDecimals": 0,
    "overridingServiceSRS": false,
    "skipNumberMatched": false,
    "circularArcPresent": false,
    "attributes": {
      "attribute": [
        {
          "name": "the_geom",
          "minOccurs": 0,
          "maxOccurs": 1,
          "nillable": true,
          "binding": "com.vividsolutions.jts.geom.MultiPolygon"
        },
        {
          "name": "LAND",
          "minOccurs": 0,
          "maxOccurs": 1,
          "nillable": true,
          "binding": "java.lang.Double",
          "length": 32
        },
        {
          "name": "CFCC",
          "minOccurs": 0,
          "maxOccurs": 1,
          "nillable": true,
          "binding": "java.lang.String",
          "length": 3
        },
        {
          "name": "LANAME",
          "minOccurs": 0,
          "maxOccurs": 1,
          "nillable": true,
          "binding": "java.lang.String",
          "length": 30
        }
      ]
    }
  }
}
"""


class Geonetwork():
    def __init__(self, service_url):
        self.rest_geonetwork = rest_geonetwork.Geonetwork(service_url)
        
    def metadata_insert(self, session, layer, abstract, ws, properties):
        self.rest_geonetwork.gn_auth(session['username'], session['password'])
        uuid = self.rest_geonetwork.gn_insert_metadata(layer, abstract, ws, properties)
        thumbnail_url = self.rest_geonetwork.get_thumbnail(session['username'], session['password'], layer, ws, properties)
        self.rest_geonetwork.add_thumbnail(uuid, thumbnail_url)
        self.rest_geonetwork.set_metadata_privileges(uuid)
        self.rest_geonetwork.gn_unauth()
        return uuid
        
    def metadata_delete(self, session, layer):
        try:
            if layer.metadata_uuid != '':
                self.rest_geonetwork.gn_auth(session['username'], session['password'])
                self.rest_geonetwork.gn_delete_metadata(layer)
                self.rest_geonetwork.gn_unauth()
                return True
            else:
                return True
        
        except Exception as e:
            print e
            return False
        

def get_default_backend():
    try:
        backend_str = GVSIGOL_SERVICES.get('ENGINE', 'geoserver')
        base_url = GVSIGOL_SERVICES['URL']
        cluster_nodes = GVSIGOL_SERVICES['CLUSTER_NODES']
        supported_types = GVSIGOL_SERVICES.get('SUPPORTED_TYPES', None)
    except:
        raise ImproperlyConfigured

    if backend_str=='geoserver':
        backend = Geoserver(base_url, cluster_nodes, supported_types)
    else:
        raise ImproperlyConfigured
    return backend

def get_geonetwork_backend():
    try:
        service_url = GVSIGOL_CATALOG['URL']
        gn_backend = Geonetwork(service_url)
        
    except:
        raise ImproperlyConfigured

    return gn_backend

backend = get_default_backend()
gn_backend = get_geonetwork_backend()
