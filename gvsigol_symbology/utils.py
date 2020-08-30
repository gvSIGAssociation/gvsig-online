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
'''
@author: Javier Rodrigo <jrodrigo@scolab.es>
'''

from gvsigol_symbology.models import  StyleLayer, Symbolizer, Style
from gvsigol_symbology import sld_builder
from gvsigol_services.backend_postgis import Introspect
from django.core import serializers
from gvsigol import settings
import tempfile, zipfile
import os, shutil, errno
import json
import re

def __get_uncompressed_file_upload_path(f):
    dir_path = tempfile.mkdtemp(suffix='', prefix='tmp-library-')
    z = zipfile.ZipFile(f, "r")
    z.extractall(dir_path)
    return dir_path

def __delete_temporaries(file_path):
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

def __compress_folder(file_path):
        #(fd, zip_path) = tempfile.mkstemp(prefix='tmp-library-', suffix=".zip")
        #os.close(fd)
        s = tempfile.TemporaryFile()
        
        relroot = file_path
        with zipfile.ZipFile(s, "w", zipfile.ZIP_DEFLATED) as zip:
            for root, dirs, files in os.walk(file_path):
                # add directory (needed for empty dirs)
                rel_path = os.path.relpath(root, relroot)
                if rel_path != ".":
                    zip.write(root, os.path.relpath(root, relroot))
                for file in files:
                    filename = os.path.join(root, file)
                    if os.path.isfile(filename): # regular files only
                        arcname = os.path.join(os.path.relpath(root, relroot), file)
                        zip.write(filename, arcname)

        return zip

def remove_accents(string):
    if type(string) is not unicode:
        string = unicode(string, encoding='utf-8')

    string = string.lower()

    string = re.sub(u"[àáâãäå]", 'a', string)
    string = re.sub(u"[èéêë]", 'e', string)
    string = re.sub(u"[ìíîï]", 'i', string)
    string = re.sub(u"[òóôõö]", 'o', string)
    string = re.sub(u"[ùúûü]", 'u', string)
    string = re.sub(u"[ýÿ]", 'y', string)
    
    string = re.sub('[^a-z0-9 \_\.]', '', string)
    string = string.replace(' ','_')

    return string
   
def copyrecursively(source_folder, destination_folder):
    for root, dirs, files in os.walk(source_folder):
        for item in files:
            item2 = remove_accents(item)
            src_path = os.path.join(root, item)
            src_path2 = os.path.join(root, item2)
            dst_path = os.path.join(destination_folder, src_path2.replace(source_folder, ""))
            if os.path.exists(dst_path):
                if os.stat(src_path).st_mtime > os.stat(dst_path).st_mtime:
                    shutil.copyfile(src_path, dst_path)
            else:
                if not os.path.exists(os.path.dirname(dst_path)):
                    try:
                        os.makedirs(os.path.dirname(dst_path))
                    except OSError as exc: # Guard against race condition
                        if exc.errno != errno.EEXIST:
                            raise
                shutil.copyfile(src_path, dst_path)
        for item in dirs:
            src_path = os.path.join(root, item)
            dst_path = os.path.join(destination_folder, src_path.replace(source_folder, ""))
            if not os.path.exists(dst_path):
                os.mkdir(dst_path)
                
def copy_resources(symbol, resource_path):
    symbolizers = Symbolizer.objects.filter(rule = symbol)
    for symbolizer in symbolizers:
        if hasattr(symbolizer, 'externalgraphicsymbolizer'):
            local_path = symbolizer.externalgraphicsymbolizer.online_resource.replace(settings.MEDIA_URL, '')
            file_name = local_path.split('/')[-1]
            absolute_path = settings.MEDIA_ROOT + local_path
            copy(absolute_path, resource_path + file_name)

def copy(src, dest):
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
            print('Directory not copied. Error: %s' % e)


def sortFontsArray(array):
    sortedArray = sorted(array)
    output = {}
    seen = set()
    for val in sortedArray:
        value = str(val)
        index = value.find(".") 
        
        if index != -1:
            value = value[0:index]
        
        if value not in seen:
            output[value] = value
            seen.add(value)
    return output

def create_style_name(layer):
    layer_styles = StyleLayer.objects.filter(layer=layer)
    index = len(layer_styles)
    style_name = layer.name + '_' + str(index)
    
    return style_name

def get_symbolizer_type(r):
    type = ''
    if r.PointSymbolizer is not None:
        type = 'PointSymbolizer'
    elif r.LineSymbolizer is not None:
        type = 'LineSymbolizer'
    elif r.PolygonSymbolizer is not None:
        type = 'PolygonSymbolizer'
    elif r.TextSymbolizer is not None:
        type = 'TextSymbolizer'
        
    return type
    
            
def check_library_path(library):
    library_path = settings.MEDIA_ROOT + "symbol_libraries/" + library.name + "/"
    try:        
        os.mkdir(library_path)
        return library_path
     
    except OSError as e:
        print('Info: %s' % e)
        return library_path
    
def check_custom_legend_path():
    legend_path = settings.MEDIA_ROOT + "custom_legends/"
    try:        
        os.mkdir(legend_path)
        return legend_path
     
    except OSError as e:
        print('Info: %s' % e)
        return legend_path
    
def save_custom_legend(legend_path, file, file_name):    
    try: 
        file_path = legend_path + file_name
        if os.path.exists(file_path):
            os.remove(file_path)
        with open(file_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
        
        legend_url = settings.MEDIA_URL + "custom_legends/" + file_name   
        return legend_url
     
    except Exception as e:
        return False
    
            
def save_external_graphic(library_path, file, file_name):    
    try: 
        file_path = library_path + file_name
        if os.path.exists(file_path):
            os.remove(file_path)
        with open(file_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
                
        return True
     
    except Exception:
        return False
    
def delete_external_graphic_img(library, file_name):    
    try: 
        library_path = settings.MEDIA_ROOT + "symbol_libraries/" + library.name + "/"
        file_path = library_path + file_name
        if os.path.exists(file_path):
            os.remove(file_path)
                
        return True
     
    except Exception as e:
        print('Error: %s' % e)
        return False
    
def delete_library_dir(library):    
    try: 
        library_path = settings.MEDIA_ROOT + "symbol_libraries/" + library.name
        if os.path.exists(library_path):
            shutil.rmtree(library_path)
                
        return True
     
    except Exception as e:
        print('Error: %s' % e)
        return False
    
def get_online_resource(library, file_name):
    return settings.MEDIA_URL + "symbol_libraries/" + library.name + "/" + file_name

def get_fields(resource):
    fields = None
    if resource != None:
        fields = resource.get('featureType').get('attributes').get('attribute')
        
    return fields

def get_alphanumeric_fields(fields):
    alphanumeric_fields = []
    for field in fields:
        if not 'jts.geom' in field.get('binding'):
            alphanumeric_fields.append(field)
            
    return alphanumeric_fields

def get_numeric_fields(fields):
    numeric_fields = []
    for field in fields:
        if (field.get('binding').startswith('java.math') or 
        field.get('binding') == ('java.lang.Number') or
        field.get('binding') == ('java.lang.Byte') or
        field.get('binding') == ('java.lang.Float') or
        field.get('binding') == ('java.lang.Integer') or
        field.get('binding') == ('java.lang.Long') or
        field.get('binding') == ('java.lang.Short') or
        field.get('binding') == ('java.lang.Double')):
            numeric_fields.append(field)
            
    return numeric_fields

def get_feature_type(fields):
    featureType = None
    for field in fields:
        if 'jts.geom' in field.get('binding'):
            auxType = field.get('binding').split('.')[-1]
            if auxType == "Point" or auxType == "MultiPoint":
                featureType = "PointSymbolizer"
            if auxType == "Line" or auxType == "MultiLineString":
                featureType = "LineSymbolizer"
            if auxType == "Polygon" or auxType == "MultiPolygon":
                featureType = "PolygonSymbolizer"
                
    return featureType

def symbolizer_to_json(symbolizer):
    json_symbolizer = {}
    
    if hasattr(symbolizer, 'polygonsymbolizer'):
        json_symbolizer['type'] = 'PolygonSymbolizer'
        json_symbolizer['order'] = symbolizer.order
        json_symbolizer['json'] = serializers.serialize('json', [ symbolizer.polygonsymbolizer, ])
        
    elif hasattr(symbolizer, 'linesymbolizer'):
        json_symbolizer['type'] = 'LineSymbolizer'
        json_symbolizer['order'] = symbolizer.order
        json_symbolizer['json'] = serializers.serialize('json', [ symbolizer.linesymbolizer, ])
        
    elif hasattr(symbolizer, 'marksymbolizer'):
        json_symbolizer['type'] = 'MarkSymbolizer'
        json_symbolizer['order'] = symbolizer.order
        json_symbolizer['json'] = serializers.serialize('json', [ symbolizer.marksymbolizer])
        
    elif hasattr(symbolizer, 'externalgraphicsymbolizer'):
        json_symbolizer['type'] = 'ExternalGraphicSymbolizer'
        json_symbolizer['order'] = symbolizer.order
        json_symbolizer['json'] = serializers.serialize('json', [ symbolizer.externalgraphicsymbolizer])
        
    elif hasattr(symbolizer, 'textsymbolizer'):
        json_symbolizer['type'] = 'TextSymbolizer'
        json_symbolizer['order'] = symbolizer.order
        json_symbolizer['json'] = serializers.serialize('json', [ symbolizer.textsymbolizer, ])
        
    return json_symbolizer

def entry_to_json(entry):
    json_entry = serializers.serialize('json', [ entry, ])       
    return json_entry

def filter_to_json(filter):
    json_filter = {}
    
    if filter.comparisonOps.original_tagname_ == 'PropertyIsEqualTo':
        json_filter['type'] = 'is_equal_to'
        json_filter['property_name'] = filter.comparisonOps.PropertyName
        json_filter['value1'] = filter.comparisonOps.Literal
        
    elif filter.comparisonOps.original_tagname_ == 'PropertyIsNull':
        json_filter['type'] = 'is_null'
        json_filter['property_name'] = filter.comparisonOps.PropertyName
        
    elif filter.comparisonOps.original_tagname_ == 'PropertyIsLike':
        json_filter['type'] = 'is_like'
        json_filter['property_name'] = filter.comparisonOps.PropertyName
        json_filter['value1'] = filter.comparisonOps.Literal
        
    elif filter.comparisonOps.original_tagname_ == 'PropertyIsNotEqualTo':
        json_filter['type'] = 'is_not_equal_to'
        json_filter['property_name'] = filter.comparisonOps.PropertyName
        json_filter['value1'] = filter.comparisonOps.Literal
        
    elif filter.comparisonOps.original_tagname_ == 'PropertyIsGreaterThan':
        json_filter['type'] = 'is_greater_than'
        json_filter['property_name'] = filter.comparisonOps.PropertyName
        json_filter['value1'] = filter.comparisonOps.Literal
        
    elif filter.comparisonOps.original_tagname_ == 'PropertyIsGreaterThanOrEqualTo':
        json_filter['type'] = 'is_greater_than_or_equal_to'
        json_filter['property_name'] = filter.comparisonOps.PropertyName
        json_filter['value1'] = filter.comparisonOps.Literal
        
    elif filter.comparisonOps.original_tagname_ == 'PropertyIsLessThan':
        json_filter['type'] = 'is_less_than'
        json_filter['property_name'] = filter.comparisonOps.PropertyName
        json_filter['value1'] = filter.comparisonOps.Literal
        
    elif filter.comparisonOps.original_tagname_ == 'PropertyIsLessThanOrEqualTo':
        json_filter['type'] = 'is_less_than_or_equal_to'
        json_filter['property_name'] = filter.comparisonOps.PropertyName
        json_filter['value1'] = filter.comparisonOps.Literal
        
    elif filter.comparisonOps.original_tagname_ == 'PropertyIsBetween':
        json_filter['type'] = 'is_between'
        json_filter['property_name'] = filter.comparisonOps.PropertyName
        json_filter['value1'] = filter.comparisonOps.LowerBoundary.expression
        json_filter['value2'] = filter.comparisonOps.UpperBoundary.expression
        
    else:
        json_filter = None
        
    return json_filter

    
def get_geometry_field(layer):
    if layer.type == 'v_PostGIS':
        params = json.loads(layer.datastore.connection_params)
        host = params['host']
        port = params['port']
        dbname = params['database']
        user = params['user']
        passwd = params['passwd']
        schema = params.get('schema', 'public')
        i = Introspect(database=dbname, host=host, port=port, user=user, password=passwd)
        
        layer_name_split = layer.name.split(':')
        layer_name = layer.name
        if layer_name_split.__len__() > 1: 
            layer_name = layer_name_split[1]
        if layer_name:
            geom_fields = i.get_geometry_columns_info(layer_name, schema)
            i.close()
            if geom_fields.__len__() > 0: 
                return {
                    'field_name': geom_fields[0][2],
                    'field_type': geom_fields[0][5],
                    } 
    return ''

def get_next_index(layer):
    index = len(StyleLayer.objects.filter(layer=layer))
    styleLayers = StyleLayer.objects.filter(layer=layer)
    for style_layer in styleLayers:
        aux_name = style_layer.style.name
        aux_name = aux_name.replace(layer.datastore.workspace.name + '_' + layer.name + '_' , '')
        
        try:
            aux_index = int(aux_name)
            if index < aux_index+1:
                index = aux_index + 1
        except ValueError:
            pass
    return index


def has_default_style(layer, style=None):
    layer_styles = StyleLayer.objects.filter(layer=layer)
    has_default_style = False
    for ls in layer_styles:
        s = Style.objects.get(id=ls.style.id)
        if s != style and s.is_default:
            return True
    return False

    
def set_not_default_styles(layer):
    layer_styles = StyleLayer.objects.filter(layer=layer)
    for ls in layer_styles:
        s = Style.objects.get(id=ls.style.id)
        s.is_default = False
        s.save()
    
def set_default_style(layer, gs, style=None, is_preview=False, is_default=False):
    if is_preview:
        is_default = False
    else:
        if is_default:
            set_not_default_styles(layer)
        elif not has_default_style(layer):
            is_default = True
        
        if is_default and style:
            if not gs.setLayerStyle(layer, style.name, style.is_default):
                # try to recover from inconsistent gvsigol - geoserver status
                if reset_geoserver_style(gs, layer, style):
                     gs.setLayerStyle(layer, style.name, style.is_default)
    return is_default

def reset_geoserver_style(gs, layer, style):
    sld_body = sld_builder.build_sld(layer, style)
    return gs.createStyle(style.name, sld_body)
    
