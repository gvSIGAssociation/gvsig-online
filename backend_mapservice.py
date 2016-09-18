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

from models import Layer, LayerGroup, Datastore, Workspace, DataRule, LayerReadGroup, LayerWriteGroup
from gvsigol_symbology.models import Symbolizer, Style, Rule, StyleLayer
from gvsigol_symbology import services as symbology_services
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import ugettext_lazy as _
from gvsigol.settings import GVSIGOL_SERVICES
from gvsigol.settings import GVSIGOL_CATALOG
from backend_postgis import Introspect
import xml.etree.ElementTree as ET
import geoserver.catalog as gscat
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
    def __init__(self, base_url, user, password, cluster_nodes, supported_types=None):
        self.base_url = base_url
        self.rest_url = self.base_url+"/rest"
        self.gwc_url = base_url+"/gwc/rest"
        self.cluster_nodes = cluster_nodes
        self.rest_catalog = rest_geoserver.Geoserver(self.rest_url, self.gwc_url)
        self.supported_types = supported_types
        self.user = user
        self.password = password
        if supported_types is not None:
            self.supported_types = supported_types
        else:
            self.supported_types = (
                ('v_SHP', _('Shapefile folder')),
                ('v_PostGIS', _('PostGIS vector')),
                ('c_GeoTIFF', _('GeoTiff')),
                ('e_WMS', _('Cascading WMS')),
            )

        gdal_tools.OGR2OGR_PATH = GVSIGOL_SERVICES.get('OGR2OGR_PATH', gdal_tools.OGR2OGR_PATH)
        
        self.supported_srs_plain = [ x[0] for x in forms_geoserver.supported_srs ]
        self.supported_encodings_plain = [ x[0] for x in forms_geoserver.supported_encodings ]
        self.supported_postgis_geom_types = [ x[0] for x in forms_geoserver.geometry_types ]
        self.raster_extensions = [".jpg", ".jpeg", ".jpe", ".png", ".tif"]
        
        self.layer_create_types = ((Geoserver.CREATE_TYPE_VECTOR_LAYER, _("Vector layer")),
                                   (Geoserver.CREATE_TYPE_SQL_VIEW, _("SQL View")))
    
    def getGsconfig(self):
        return gscat.Catalog(self.rest_url, self.user, self.password, disable_ssl_certificate_validation=True)
    
    
    def getSupportedTypes(self):
        return self.supported_types
    
    def getSupportedVectorTypes(self):
        return (
            ('v_PostGIS', _('PostGIS vector')),
            ('v_SHP', _('Shapefile folder')),       
        )
    
    def getSupportedUploadTypes(self):
        return self.supported_upload_types
    
    def getSupportedEncodings(self):
        return self.supported_encodings
    
    def getSupportedSRSs(self):
        return self.supported_SRSs
    
    def getSupportedFonts(self):
        return self.rest_catalog.get_fonts(user=self.user, password=self.password)
    
    def reload_nodes(self):
        try:
            if len(self.cluster_nodes) > 0:
                for node in self.cluster_nodes:
                    self.rest_catalog.reload(node, user=self.user, password=self.password)
            return True
        except Exception as e:
            print str(e)
            return False
        
    def createWorkspace(self, name, uri, description=None,
                        wms_endpoint=None, wfs_endpoint=None,
                        wcs_endpoint=None, cache_endpoint=None):
        try:
            self.getGsconfig().create_workspace(name, uri)
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
        
    def getBaseUrl(self):
        return self.base_url

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
                    params_dict['schema'] = params_dict.get('schema', 'public')
                ds = catalog.create_datastore(name, workspace.name)
                ds.connection_parameters.update(params_dict)
            elif format_nature == "c": # coverage (raster)
                ds = catalog.create_coveragestore2(name, workspace.name)
                ds.url = params_dict.get('url')
            elif format_nature == "e": # cascading wms
                #user = None
                #password = None
                #if params_dict.get('user') != 'wmsuser':
                #    user = params_dict.get('user')
                #if params_dict.get('password') != 'wmspassword':
                #    password = params_dict.get('password')  
                ws = catalog.get_workspace(workspace.name)
                ds = catalog.create_wmsstore(name, ws, user=None, password=None)
                ds.capabilitiesURL = params_dict.get('url')
                
            else:
                # unsupported
                return False
            ds.description = description # description is ignored by gsconfig at the moment
            ds.type = driver
            response = catalog.save(ds) # FIXME: we should check response.status to ensure the operation was correct
            return True
        except Exception as e:
            print str(e)
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

    def updateDatastore(self, workspace, dsname, description, dstype, conn_params):
        try:
            format_nature=dstype[:1]
            catalog = self.getGsconfig()
            ds = catalog.get_store(dsname, workspace)
            params_dict = json.loads(conn_params)
            if format_nature == "v": # vector
                # directly updating connection_parameters won't work, we need to set the dict again
                params = ds.connection_parameters
                params.update(params_dict)
                ds.connection_parameters = params
            elif format_nature == "c": # coverage (raster)
                ds.url = params_dict.get('url')
            elif format_nature == "e": # cascading wms
                ds.capabilitiesURL = params_dict.get('url')
            catalog.save(ds)
            return True
        except Exception as exc:
            print exc
            return False
    
    def deleteDatastore(self, workspace, datastore, purge=None):
        """
        Deletes a datastore and all its associated resources
        """
        try:
            catalog = self.getGsconfig()
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
        
    def setLayerStyle(self, layer_name, style):
        """
        Set default style
        """
        try:
            catalog = self.getGsconfig()
            layer = catalog.get_layer(layer_name)
            layer.default_style = style
            catalog.save(layer)
            return True
        except Exception as e:
            return False     
        
    def get_geometry_type(self, layer):
        try:           
            datastore = Datastore.objects.get(id=layer.datastore_id)
            if layer.type == 'v_PostGIS' or layer.type == 'v_PostGIS_View':
                workspace = Workspace.objects.get(id=datastore.workspace_id)
                result = self.rest_catalog.get_feature_type(workspace.name, datastore.name, layer.name, user=self.user, password=self.password)
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
        
    def createDefaultStyle(self, layer, style_name):
        geom_type = self.get_geometry_type(layer)
        style_type = 'US'
        if geom_type == 'raster':
            style_type = 'CT'
            
        sld_body = symbology_services.create_default_style(layer.id, style_name, style_type, geom_type)
     
        try:
            catalog = self.getGsconfig()
            if catalog.get_style(style_name, workspace=None) == None:
                catalog.create_style(style_name, sld_body.encode('utf-8'), overwrite=False, workspace=None, style_format="sld10", raw=False)
                    
            return True
        
        except Exception as e:
            return False
        
    def createStyle(self, name, data):
        """
        Create new style
        """
        try:
            self.getGsconfig().create_style(name, data.encode('utf-8'), overwrite=False, workspace=None, style_format="sld10", raw=False)
            return True
        
        except Exception as e:
            return False
        
    def updateStyle(self, style_name, sld_body):
        """
        Update a style
        """
            
        try:
            self.rest_catalog.update_style(style_name, sld_body, user=self.user, password=self.password)
            return True
        
        except Exception as e:
            print e
            return False
        
    def deleteStyle(self, name):
        """
        Delete a style
        """
        try:
            catalog = self.getGsconfig()
            style = catalog.get_style(name, workspace=None)
            catalog.delete(style, purge=True, recurse=False)
            return True
        
        except Exception as e:
            return False
        
    def deleteLayerStyles(self, lyr):
        try:
            layer_styles = StyleLayer.objects.filter(layer=lyr)
    
            for layer_style in layer_styles:
                style = Style.objects.get(id=layer_style.style_id)
                catalog = self.getGsconfig()
                gs_style = catalog.get_style(style.name, workspace=None)
                catalog.delete(gs_style, purge=True, recurse=False)
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
            return False
        
    def updateBoundingBoxFromData(self, layer):
        store = layer.datastore
        if store.type[0]=="v":
            self.rest_catalog.update_ft_bounding_box(layer.datastore.workspace.name, layer.datastore.name, layer.name, user=self.user, password=self.password)
        # not available/necessary for coverages
            

    def createResource(self, workspace, store, name, title):
        if store.type[0]=="v":
            return self.createFeaturetype(workspace, store, name, title)
        elif store.type[0]=="e":
            return self.createWMSLayer(workspace, store, name, title)
        else:
            return self.createCoverage(workspace, store, name, title)   

    def createFeaturetype(self, workspace, datastore, name, title):
        try:
            return self.rest_catalog.create_feature_type(name, title, datastore.name, workspace.name, user=self.user, password=self.password)
        except rest_geoserver.FailedRequestError as e:
            print ("ERROR createFeatureType failedrequest exception: " + e.get_message())
            raise rest_geoserver.FailedRequestError(e.status_code, _("Error publishing the layer. Backend error: {msg}").format(msg=e.get_message()))
        except Exception as e:
            print ("ERROR createFeatureType unknown exception: " + e.get_message())
            raise rest_geoserver.FailedRequestError(-1, _("Error: layer could not be published"))
        
    def createCoverage(self, workspace, coveragestore, name, title):
        try:
            return self.rest_catalog.create_coverage(name, title, coveragestore.name, workspace.name, user=self.user, password=self.password)
        except rest_geoserver.FailedRequestError as e:
            raise rest_geoserver.FailedRequestError(e.status_code, _("Error publishing the layer. Backend error: {msg}").format(msg=e.get_message()))
        except Exception as e:
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
            raise rest_geoserver.FailedRequestError(e.status_code, _("Error publishing the layer group. Backend error: {msg}").format(msg=e.get_message()))
        except Exception as e:
            raise rest_geoserver.FailedRequestError(-1, _("Error: layer group could not be published"))
        
    def deleteGeoserverLayerGroup(self, layer_group):
        try:
            return self.rest_catalog.delete_gs_layer_group(layer_group, user=self.user, password=self.password)
        except rest_geoserver.FailedRequestError as e:
            raise rest_geoserver.FailedRequestError(e.status_code, _("Error publishing the layer group. Backend error: {msg}").format(msg=e.get_message()))
        except Exception as e:
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
                    return False
        except:
            # only fail if layer exists but deletion failed
            pass
        return True

    def updateResource(self, workspace, datastore, name, title):
        try:
            catalog = self.getGsconfig()
            resource = catalog.get_resource(name, datastore, workspace)
            resource.name = name
            resource.title = title
            catalog.save(resource)
            return True
        except Exception as exc:
            print exc
            return False
            
    def _get_unique_resource_name(self, datastore, workspace):
        name = datastore
        i = 0
        while self.getGsconfig().get_resource(name, None, workspace):
            name = datastore + str(i)
            i = i + 1
        return name     
    
    def getResources(self, workspace, datastore, dstype, available=False):
        try:
            store = self.getGsconfig().get_store(datastore, workspace)
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
                    return [self._get_unique_resource_name(datastore, workspace)]
            elif (format_nature=='e'):
                return store.get_resources(available=available)
            
        except:
            e = sys.exc_info()[0]
            pass
        
        
    def getResourceInfo(self, workspace, store, featureType, type):
        if type == None:
            type = "json"
        url = self.rest_catalog.service_url + "/workspaces/" + workspace + "/datastores/" + store + "/featuretypes/" + featureType +"."+type
        r = self.rest_catalog.session.get(url, auth=(self.user, self.password))
        if r.status_code==200:
            content = r.content
            jsonData = json.loads(content)
            return jsonData
        return None
    
    def getRasterResourceInfo(self, workspace, store, featureType, type):
        if type == None:
            type = "json"
        url = self.rest_catalog.service_url + "/workspaces/" + workspace + "/coveragestores/" + store + "/coverages/" + featureType +"."+type
        r = self.rest_catalog.session.get(url, auth=(self.user, self.password))
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
    
    def getUploadForm(self, datastore_type, request):
        # ensure type is a supported data store type
        if datastore_type=="c_GeoTIFF":
            return (forms_geoserver.RasterLayerUploadForm, "geoserver/layer_upload_raster.html", "image/tiff")
        elif datastore_type=="v_PostGIS":
            form = forms_geoserver.PostgisLayerUploadForm
            if not request.user.is_superuser:
                form.base_fields['datastore'].queryset = Datastore.objects.filter(created_by__exact=request.user.username)
                form.declared_fields['datastore'].queryset = Datastore.objects.filter(created_by__exact=request.user.username)
            return (form, "geoserver/layer_upload_postgis.html", "application/zip")
        return (None, None, None)
    
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

        
    def __test_zip_structure(self, zip_path):
        z = zipfile.ZipFile(zip_path, "r")
        for n in z.namelist():
            if n.endswith("/"):
                z.close()
                raise BadFormat(-1, _("Bad file format. The provided zip file must not contain any subdirectory."))
        z.close()
    
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
            raise rest_geoserver.RequestError(e.code, e.message)
        except Exception as e:
            logging.exception(e)

        raise rest_geoserver.RequestError(-1, _("Error uploading the layer. Review the file format."))
    
    def __do_shpdir2postgis(self, request, datastore, application, dir_path, layergroup, table_definition, creation_mode, defaults):
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
            
            # load SHP       
            files = [f for f in os.listdir(dir_path) if f.lower()[-4:]==".shp"]
            
            for f in files:
                has_style = False
                if f in table_definition:
                    table_def = table_definition[f]
                    layer_name = table_def['name']
                    layer_title = table_def['title']
                    try:
                        original_style_name = table_def['style']
                        has_style = True
                        
                    except Exception as e:
                        original_style_name = layer_name
                        print e
                    #layer_group = table_def['group'] + '_' + application.name.lower()
                else:
                    layer_name = os.path.splitext(os.path.basename(f))[0]
                    layer_title = os.path.splitext(os.path.basename(f))[0]
                    original_style_name = layer_name
                shp_abs = os.path.join(dir_path, f)
                try:
                    gdal_tools.shp2postgis(shp_abs, layer_name, srs, host, port, db, schema, user, password, creation_mode, encoding)
                except Exception as e:
                    print "ERROR en shp2postgis ... Algunos shapefiles puede que no hayan subido "
                    continue 
                
                try:
                    layer = Layer.objects.get(name=layer_name, datastore=datastore)
                except:
                    # may me missing when creating a layer or when
                    # appending / overwriting a layer created outside gvsig online
                    layer = Layer()                
                    # TODO: si estamos en create mode es porque ha aparecido otro shape. Deberiamos borrar el proyecto y volverlo a crear  
                            
                if creation_mode==forms_geoserver.MODE_CREATE:
                    
                    try:
                        self.createFeaturetype(datastore.workspace, datastore, layer_name, layer_title)
                    except:
                        print "ERROR en createFeaturetype"
                        raise
                    
                        
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
                    layer.created_by = request.user.username
                    layer.save()
    
                    self.setDataRules()                                        
                        
                        
                    if layer.layer_group.name != "__default__":
                        self.createOrUpdateGeoserverLayerGroup(layer.layer_group)
                #else:
                #    print "TODO: borrar la cache .."
                
                # estilos: se ejecuta en modo create o update
                # si esta definido en la conf y existe, se clona con el nombre del ws
                # si no, se crea uno por defecto
                # TODO: si el clonado existe, habria que eliminarlo
                final_style_name = datastore.workspace.name + '_' + original_style_name
                
                print "Depurando ... eliminando el estilo que habia ..." + final_style_name
                cloned_style = self.getStyle(final_style_name)
                to_delete = Style.objects.filter(name__exact=final_style_name)
                
                style_from_library = self.getStyle(original_style_name)
                if to_delete:
                    symbology_services.delete_style(to_delete[0].id, self)
                if has_style and style_from_library is not None :       
                    print "Depurando ... definido en la conf y existe ... Asi que clonamos: " +  final_style_name                       
                    symbology_services.clone_style(self, layer, original_style_name, final_style_name)
                else:
                    print "Depurando ... no existe en la conf o en la libreria ... Asi que creamos por defecto " + final_style_name   
                    if layer.id is None:
                        print "Houston tenemos un problema ...................................."                                          
                    self.createDefaultStyle(layer, final_style_name)
                    self.setLayerStyle(layer.name, final_style_name)
                            
        except rest_geoserver.RequestError as ex:
            print "Error Request: " + str(ex)
            raise             
        except gdal_tools.GdalError as ex:
            print "Error Gdal: " + str(ex)
            raise rest_geoserver.RequestError(e.code, e.message)
        except Exception as e:
            logging.exception(e)
            raise rest_geoserver.RequestError(-1, _("Error creating the layer. Review the file format."))
            
    def exportShpToPostgis(self, form_data):
        name = form_data['name']
        ds = form_data['datastore']
        shp_path = form_data['file'] 
        
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
    
    def setDataRules(self):
        
        url = self.rest_catalog.get_service_url() + "/security/acl/layers.json"
        services_url = self.rest_catalog.get_service_url() + "/security/acl/services.json"

        rules = DataRule.objects.all()
        for r in rules:
            self.rest_catalog.get_session().delete(self.rest_catalog.get_service_url() + "/security/acl/layers/" + r.path, verify=False, auth=(self.user, self.password))
            r.delete()
        self.rest_catalog.get_session().delete(self.rest_catalog.get_service_url() + "/security/acl/services/wfs.Transaction", verify=False, auth=(self.user, self.password))
        
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
                        
            self.rest_catalog.get_session().post(url, json=data, verify=False, auth=(self.user, self.password))
            
        if  len(transaction_roles) > 0:
            service = {}
            service_write_roles =  ",".join(transaction_roles)
            service['wfs.Transaction'] = service_write_roles
            self.rest_catalog.get_session().post(services_url, json=service, verify=False, auth=(self.user, self.password))
            
            
    def clearCache(self, ws, layer):
        try:
            self.rest_catalog.clear_cache(ws, layer, user=self.user, password=self.password)
            return True
        
        except Exception as e:
            print e
            return False
        
    def clearLayerGroupCache(self, name):
        try:
            self.rest_catalog.clear_layergroup_cache(name, user=self.user, password=self.password)
            return True
        
        except Exception as e:
            print e
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
        req.auth = (self.user, self.password)
    
        response = req.post(url, data=values, verify=False)
        root = ET.fromstring(response.text)
        numberOfFeatures = int(root.attrib['numberOfFeatures'])
        
        return numberOfFeatures

class Geonetwork():
    def __init__(self, service_url):
        self.rest_geonetwork = rest_geonetwork.Geonetwork(service_url)
        
    def metadata_insert(self, session, layer, abstract, ws, layer_info):
        self.rest_geonetwork.gn_auth(session['username'], session['password'])
        uuid = self.rest_geonetwork.gn_insert_metadata(layer, abstract, ws, layer_info)
        thumbnail_url = self.rest_geonetwork.get_thumbnail(session['username'], session['password'], layer, ws, layer_info)
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
        user = GVSIGOL_SERVICES['USER']
        password = GVSIGOL_SERVICES['PASSWORD']
        cluster_nodes = GVSIGOL_SERVICES['CLUSTER_NODES']
        supported_types = GVSIGOL_SERVICES.get('SUPPORTED_TYPES', None)
    except:
        raise ImproperlyConfigured

    if backend_str=='geoserver':
        backend = Geoserver(base_url, user, password, cluster_nodes, supported_types)
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
