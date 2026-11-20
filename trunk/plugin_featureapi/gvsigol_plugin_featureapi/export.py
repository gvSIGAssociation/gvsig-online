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

from datetime import datetime, date
import json
import os
import shutil, errno
import urllib.request, urllib.parse, urllib.error
import zipfile

from PIL import Image
import requests
from resizeimage import resizeimage

from gvsigol import settings as core_settings
from gvsigol_services.models import Layer, LayerResource, Server
from gvsigol_symbology.models import StyleLayer, Style, Rule, Symbolizer


class VectorLayerExporter():
    
    def __init__(self):
        self.layers_dir = os.path.join(core_settings.MEDIA_ROOT, core_settings.LAYERS_ROOT)
    
    def get_layer_dir(self):
        return self.layers_dir
        
    def create_package_from_geojson(self, geojson, workspace, layer_name, idfield, resources, version = None):
        base_dir = layer_name + "_" + version
        layer_name_ = 'layer' #layer_name + "_" + str(dt.microsecond)
        project_dir, data_dir, resources_dir, symbols_dir, base_dir = self.create_directories(layer_name_, base_dir)
        
        #Si llega un array de geojson mete cada uno en un fichero
        if isinstance(geojson, list):
            i = 0
            for gjson in geojson:
                geojson_with_resources = self.get_resources(resources_dir, gjson, layer_name, workspace, idfield, resources)
                filename = layer_name_ + "_" + str(i)
                with open(os.path.join(data_dir, filename + '.json'), 'w') as outfile:  
                    json.dump(geojson_with_resources, outfile, indent = 4) 
                i = i + 1  
        else:
            geojson_with_resources = self.get_resources(resources_dir, geojson, layer_name, workspace, idfield, resources)
            with open(os.path.join(data_dir, layer_name_ + '.json'), 'w') as outfile:  
                json.dump(geojson_with_resources, outfile, indent = 4)
             
        outputfilename = "layer_symbology.json"
        self.create_geojson_symbology(data_dir, symbols_dir, layer_name, workspace, outputfilename)
        
        if(version is None):
            dt = datetime.now()
            zipname = self.layers_dir + "/" + layer_name + "_" + str(dt.microsecond)
        else:
            zipname = self.layers_dir + "/" + layer_name + "_" + version
        file  = self.compress_folder(layer_name_, project_dir, zipname)
        try:
            shutil.rmtree(base_dir)
        except Exception:
            pass
        return file[1]
        
    def create_geojson_files(self, layer_name, workspace, extent, time):
        project_dir, data_dir, resources_dir, symbols_dir = self.create_directories(layer_name)
        
        geojson = self.get_geojson(layer_name, workspace, extent, time)
        geojson_with_resources = self.get_resources_geoserver(resources_dir, geojson, layer_name, workspace)
        with open(os.path.join(data_dir, layer_name + '.json'), 'w') as outfile:  
            json.dump(geojson_with_resources, outfile, indent = 4)
             
        outputfilename = layer_name + '_symbology.json'
        self.create_geojson_symbology(data_dir, symbols_dir, layer_name, workspace, outputfilename)
        
        size, file  = self.compress_folder(layer_name, project_dir, project_dir)
        return size, file
     
    def create_directories(self, name, base_dir):

        if not os.path.exists(self.layers_dir):
            os.mkdir(self.layers_dir)

        base_dir = os.path.join(self.layers_dir, base_dir)
        if not os.path.exists(base_dir):
            os.mkdir(base_dir)

        project_dir = os.path.join(base_dir, name)
        if not os.path.exists(project_dir):
            os.mkdir(project_dir)
        
        data_dir = os.path.join(project_dir, 'data')
        resources_dir = os.path.join(data_dir, 'resources')
        symbols_dir = os.path.join(data_dir, 'symbols')
        if not os.path.exists(data_dir):
            os.mkdir(data_dir)
        if not os.path.exists(resources_dir):
            os.mkdir(resources_dir)
        if not os.path.exists(symbols_dir):
            os.mkdir(symbols_dir)
        
        return project_dir, data_dir, resources_dir, symbols_dir, base_dir
                
    def get_geojson(self, layer_name, workspace, extent, time):
        layer = Layer.objects.get(name=layer_name, datastore__workspace__name=workspace)
        wfs_url = layer.datastore.workspace.wfs_endpoint
            
        bbox = extent#",".join(map(str, extent))
        
        try:
            values = {
                'SERVICE': 'WFS',
                'VERSION': '1.0.0',
                'REQUEST': 'GetFeature',
                'TYPENAME': layer_name,
                'OUTPUTFORMAT': 'application/json',
                'MAXFEATURES': 10000,
                'SRSNAME': 'EPSG:4326'
            }

            if time is not None:
                splitted_time = time.split('/')
                if len(splitted_time) >= 2:
                    
                    present = datetime.utcnow()
                    present = str(present).replace(' ', 'T')
                    present_splitted = present.split('.')
                    present_valid = str(present_splitted[0]) + 'Z'
                        
                    if not splitted_time[0].startswith('P') and not splitted_time[1].startswith('P'):
                        values['CQL_FILTER'] = layer.time_enabled_field + ' > ' + str(splitted_time[0]) + ' AND ' + layer.time_enabled_field + ' < ' +  str(splitted_time[1]) + ' AND BBOX(wkb_geometry,' + bbox + ')'
                        
                    elif 'PRESENT' in splitted_time[0] and 'PRESENT' in splitted_time[1]:
                        values['CQL_FILTER'] = layer.time_enabled_field + ' = ' + str(present_valid) + ' AND BBOX(wkb_geometry,' + bbox + ')'
                        
                    else :  
                        if splitted_time[0].startswith('P'):
                            if 'PRESENT' in splitted_time[0]:
                                if splitted_time[1].startswith('P'):
                                    values['CQL_FILTER'] = layer.time_enabled_field + ' during ' + str(present_valid) + '/' + str(splitted_time[1]) + ' AND BBOX(wkb_geometry,' + bbox + ')'
                                else:
                                    values['CQL_FILTER'] = layer.time_enabled_field + ' during ' + str(present_valid) + '/' + str(splitted_time[1]) + 'T00:00:00Z' + ' AND BBOX(wkb_geometry,' + bbox + ')'
                            else:
                                if 'PRESENT' in splitted_time[1]:
                                    values['CQL_FILTER'] = layer.time_enabled_field + ' during ' + str(splitted_time[0]) + '/' + present_valid + ' AND BBOX(wkb_geometry,' + bbox + ')'
                                else:
                                    if splitted_time[1].startswith('P'):
                                        values['CQL_FILTER'] = layer.time_enabled_field + ' during ' + str(splitted_time[0]) + '/' + str(splitted_time[1]) + ' AND BBOX(wkb_geometry,' + bbox + ')'
                                    else:
                                        values['CQL_FILTER'] = layer.time_enabled_field + ' during ' + str(splitted_time[0]) + '/' +  str(splitted_time[1]) + 'T00:00:00Z' + ' AND BBOX(wkb_geometry,' + bbox + ')'
                                
                        else:
                            if 'PRESENT' in splitted_time[1]:
                                values['CQL_FILTER'] = layer.time_enabled_field + ' during ' + str(splitted_time[0]) + 'T00:00:00Z' + '/' +  present_valid + ' AND BBOX(wkb_geometry,' + bbox + ')'
                            else:
                                values['CQL_FILTER'] = layer.time_enabled_field + ' during ' + str(splitted_time[0]) + 'T00:00:00Z' + '/' +  str(splitted_time[1]) + ' AND BBOX(wkb_geometry,' + bbox + ')'
                
                else:
                    values['CQL_FILTER'] = layer.time_enabled_field + ' = ' + str(time) + ' AND BBOX(wkb_geometry,' + bbox + ')'
                    
            else:
                values['BBOX'] = bbox

            params = urllib.parse.urlencode(values)
            req = requests.Session()
            server = Server.objects.filter(default=True)
            if server is not None and len(server) > 0:
                req.auth = (server[0].user, server[0].password)
                    
            print(wfs_url + "?" + params)
            response = req.post(wfs_url, data=values, verify=False)
            jsonString = response.text
            geojson = json.loads(jsonString)

            return geojson      
        
        except Exception as e:
            print(str(e))
            return None
    
    def get_resources(self, resources_dir, geojson, layer_name, workspace, idfield, resources):
        if(resources is False):
            return geojson

        layer = Layer.objects.get(name = layer_name, datastore__workspace__name = workspace)
        for f in geojson.get('features'):
            fid = f['properties'][idfield]
            try:
                fid = int(fid)
            except Exception:
                return 
            resources = LayerResource.objects.filter(layer_id=layer.id).filter(feature=fid)
                
            string_resouces = ''
            for r in resources:
                try:
                    self.copy_resources(r.path, resources_dir)
                    res = r.path.split('/')[-1]
                    string_resouces += 'resources/' + res +';'
                except Exception:
                    pass #Si el recurso no existe se captura la excepcion y continua
            f['properties']['gvsigol_resources'] = string_resouces 
        
        return geojson 

    def get_resources_geoserver(self, resources_dir, geojson, layer_name, workspace):
        layer = Layer.objects.get(name = layer_name, datastore__workspace__name = workspace)
        for f in geojson.get('features'):
            fid = f.get('id').split('.')[1]
            try:
                fid = int(fid)
            except Exception:
                return 
            resources = LayerResource.objects.filter(layer_id=layer.id).filter(feature=fid)
                
            string_resouces = ''
            for r in resources:
                self.copy_resources(r.path, resources_dir)
                res = r.path.split('/')[-1]
                string_resouces += 'resources/' + res +';'
            f['properties']['gvsigol_resources'] = string_resouces 
        
        return geojson  
    
    
    def copy_resources(self, resource, resources_dir):
        file_name = resource.split('/')[-1]
        absolute_path = core_settings.MEDIA_ROOT + resource
        self.copy(absolute_path, os.path.join(resources_dir, file_name))
              
                
    def copy(self, src, dest):
        try:
            if os.path.isdir(src):
                shutil.copytree(src, dest, False, None)
            else:
                if dest.rfind('/') >= 0:
                    local_dir_url = dest[:dest.rfind('/')]
                    if not os.path.exists(local_dir_url):
                        os.mkdir(local_dir_url)
                shutil.copy2(src, dest)
        except OSError as e:
            # If the error was caused because the source wasn't a directory
            if e.errno == errno.ENOTDIR:
                shutil.copy(src, dest)
            else:
                print(('Directory not copied. Error: %s' % e))  
                
                
    def create_geojson_symbology(self, data_dir, symbols_dir, layer_name, workspace, outputfilename):
        layer = Layer.objects.get(name=layer_name, datastore__workspace__name=workspace)
        
        data = {}  
        data['rules'] = {}
        
        default_style = None
        styles_by_layer = StyleLayer.objects.filter(layer=layer)
        for s in styles_by_layer:
            if s.style.is_default:
                default_style = s.style
                
        style = Style.objects.get(id=default_style.id)
        rules = Rule.objects.filter(style_id=style.id)
        if style.type == 'US':
            r = rules[0]
            filter = '{}'
            if r.filter != '':
                filter = r.filter
            data['rules'][r.id] = {
                'name': r.name,
                'filter': json.loads(filter),
                'symbolizers': []
            }
            data = self.create_symbolizers(symbols_dir, r, data)
            
        elif style.type == 'UV':
            for r in rules:
                filter = '{}'
                if r.filter != '':
                    filter = r.filter
                data['rules'][r.id] = {
                    'name': r.name,
                    'filter': json.loads(filter),
                    'symbolizers': []
                }
                data = self.create_symbolizers(symbols_dir, r, data)
                        
        elif style.type == 'EX':
            for r in rules:
                filter = '{}'
                if r.filter != '':
                    filter = r.filter
                data['rules'][r.id] = {
                    'name': r.name,
                    'filter': json.loads(filter),
                    'symbolizers': []
                }
                data = self.create_symbolizers(symbols_dir, r, data)

        with open(os.path.join(data_dir, outputfilename), 'w') as outfile:  
            json.dump(data, outfile, indent=4)
            
            
    def create_symbolizers(self, symbols_dir, r, data):
        symbolizers = Symbolizer.objects.filter(rule_id=r.id)
        for sb in symbolizers:
            if hasattr(sb, 'marksymbolizer'):
                data['rules'][r.id]['geom'] = 'point'
                data['rules'][r.id]['type'] = 'symbol'
                data['rules'][r.id]['symbolizers'].append({
                    'opacity': sb.marksymbolizer.opacity,
                    'size': sb.marksymbolizer.size,
                    'rotation': sb.marksymbolizer.rotation,
                    'well_known_name': sb.marksymbolizer.well_known_name,
                    'fill_color': sb.marksymbolizer.fill,
                    'fill_opacity': sb.marksymbolizer.fill_opacity,
                    'stroke_color': sb.marksymbolizer.stroke,
                    'stroke_opacity': sb.marksymbolizer.stroke_opacity,
                    'stroke_width': sb.marksymbolizer.stroke_width,
                    'stroke_dash_array': sb.marksymbolizer.stroke_dash_array,
                    
                })
                
            elif hasattr(sb, 'linesymbolizer'):
                data['rules'][r.id]['geom'] = 'line'
                data['rules'][r.id]['type'] = 'symbol'
                data['rules'][r.id]['symbolizers'].append({
                    'stroke_color': sb.linesymbolizer.stroke,
                    'stroke_opacity': sb.linesymbolizer.stroke_opacity,
                    'stroke_width': sb.linesymbolizer.stroke_width,
                    'stroke_dash_array': sb.linesymbolizer.stroke_dash_array,
                    
                })
                
            elif hasattr(sb, 'polygonsymbolizer'):
                data['rules'][r.id]['geom'] = 'polygon'
                data['rules'][r.id]['type'] = 'symbol'
                data['rules'][r.id]['symbolizers'].append({
                    'fill_color': sb.polygonsymbolizer.fill,
                    'fill_opacity': sb.polygonsymbolizer.fill_opacity,
                    'stroke_color': sb.polygonsymbolizer.stroke,
                    'stroke_opacity': sb.polygonsymbolizer.stroke_opacity,
                    'stroke_width': sb.polygonsymbolizer.stroke_width,
                    'stroke_dash_array': sb.polygonsymbolizer.stroke_dash_array,
                    
                })
                
            elif hasattr(sb, 'externalgraphicsymbolizer'):
                local_path = sb.externalgraphicsymbolizer.online_resource.replace(core_settings.MEDIA_URL, '')
                image = local_path.split('/')[-1]
                data['rules'][r.id]['geom'] = 'point'
                data['rules'][r.id]['type'] = 'external_graphic'
                data['rules'][r.id]['symbolizers'].append({
                    'opacity': sb.externalgraphicsymbolizer.opacity,
                    'size': sb.externalgraphicsymbolizer.size,
                    'rotation': sb.externalgraphicsymbolizer.rotation,
                    'image': image
                    
                })
                self.copy_symbols(r, symbols_dir)
                
        return data
    
    
    def copy_symbols(self, symbol, symbols_dir):
        symbolizers = Symbolizer.objects.filter(rule = symbol)
        for symbolizer in symbolizers:
            if hasattr(symbolizer, 'externalgraphicsymbolizer'):
                local_path = symbolizer.externalgraphicsymbolizer.online_resource.replace(core_settings.MEDIA_URL, '')
                file_name = local_path.split('/')[-1]
                absolute_path = core_settings.MEDIA_ROOT + local_path
                #self.copy(absolute_path, os.path.join(symbols_dir, file_name))
                
                size = symbolizer.externalgraphicsymbolizer.size
                try:
                    with Image.open(absolute_path) as image:
                        cover = resizeimage.resize_cover(image, [size, size])
                        cover.save(os.path.join(symbols_dir, file_name), image.format)
                        
                except Exception as e:
                    if str(e).find("Image is too small") == -1:
                        pass
                    else:
                        self.copy(absolute_path, os.path.join(symbols_dir, file_name))
     
     
    def compress_folder(self, name, file_path, zip_path):           
        relroot = file_path
        zip_path = zip_path + '.zip'
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip:
            for root, dirs, files in os.walk(file_path):
                # add directory (needed for empty dirs)
                rel_path = os.path.relpath(root, relroot)
                if rel_path != ".":
                    zip.write(root, name + "/" + os.path.relpath(root, relroot))
                for file in files:
                    filename = os.path.join(root, file)
                    if os.path.isfile(filename): # regular files only
                        arcname = os.path.join(os.path.relpath(root, relroot), file)
                        zip.write(filename, name + "/" + arcname) 
                        
        return self.file_size(zip_path), zip_path    


    def file_size(self, file_path):
        """
        this function will return the file size
        """
        if os.path.isfile(file_path):
            file_info = os.stat(file_path)
            #return self.convert_bytes(file_info.st_size)
            return float(file_info.st_size)
        
        
    def convert_bytes(self, num):
        """
        this function will convert bytes to MB.... GB... etc
        """
        for x in ['bytes', 'KB', 'MB', 'GB', 'TB']:
            if num < 1024.0:
                return "%3.1f %s" % (num, x)
            num /= 1024.0