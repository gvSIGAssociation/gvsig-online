# -*- coding: utf-8 -*-

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
from gvsigol_symbology.models import Rule
'''
@author: Jose Badia <jbadia@scolab.es>
'''

from gvsigol_services.backend_mapservice import backend as backend_mapservice
from gvsigol_services.models import Layer
from django.http import HttpResponse
from models import Rule, Symbolizer
from gvsigol import settings
import tempfile, zipfile
import os, shutil
import sld_utils
import StringIO
import utils
import json
import re


def export_library(library, symbols):
    dir_path = tempfile.mkdtemp(suffix='', prefix='tmp-library-')
    resource_path = dir_path+"/resources/"
    os.makedirs(resource_path)
    i=0
    for symbol in symbols:
        try:
            file = open(dir_path+"/symbol-"+symbol.name+"-"+str(i)+".sld",'w+')
            file.write(sld_utils.create_basic_sld(library, symbol, resource_path))
            file.close()
        except:
            print('Something went wrong creating SLD file for symbol nº'+str(i))
            
        i=i+1
   
    
    buffer = StringIO.StringIO()
    z = zipfile.ZipFile(buffer, "w")
    relroot = dir_path
    for root, dirs, files in os.walk(dir_path):
            rel_path = os.path.relpath(root, relroot)
            if rel_path != ".":
                z.write(root, os.path.relpath(root, relroot))
            for file in files:
                filename = os.path.join(root, file)
                if os.path.isfile(filename): 
                    arcname = os.path.join(os.path.relpath(root, relroot), file)
                    z.write(filename, arcname)
    z.close()
    buffer.seek(0)
    response = HttpResponse(content_type='application/zip; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename='+library.name+'.zip'
    response.write(buffer.read())
    
    utils.__delete_temporaries(dir_path)
    
    return response


def upload_library(file, library):
    library_path = check_library_path(library)
    file_path = utils.__get_uncompressed_file_upload_path(file)
    utils.copyrecursively(file_path+"/resources/", library_path)
    rules = []
    
    file_list = os.listdir(file_path)
    for file in file_list:
        if not os.path.isdir(file_path+"/"+file):
            f = open(file_path+"/"+file, 'r')
            sld_text = f.read()
            sld_text = " ".join(sld_text.split())
            sld_text = sld_text.replace("> <", "><")
            
            i=0
            name = "símbolo"
            
            match = re.search(r'<[sld:]?Rule>(.*)</[sld:]?Rule>', sld_text, re.DOTALL)
            while match:
                if match.regs and match.regs.__len__ > 1:
                    aux_symbolizer = sld_text[match.regs[1][0]:match.regs[1][1]]
                    
                    match2 = re.search(r'<[sld:]?Name>([^<]*)</[sld:]?Name>', aux_symbolizer, re.DOTALL)
                    if match2 and match2.regs and match2.regs.__len__ > 1:
                        name = aux_symbolizer[match2.regs[1][0]:match2.regs[1][1]]
                    
                    match3 = re.search(r'<[sld:]?([^>]*)Symbolizer>.*</[sld:]?\1Symbolizer>', aux_symbolizer, re.DOTALL)
                    
                    not_found = True
                    while match3 and not_found:
                        if match3.regs and match3.regs.__len__ > 2:
                            type = aux_symbolizer[match3.regs[1][0]:match3.regs[1][1]]
                            sld = aux_symbolizer[match3.regs[0][0]:match3.regs[0][1]]
                            aux_symbolizer = aux_symbolizer[match3.regs[0][1]:]
                            if i>0:
                                name = name +"-"+str(i)
                            i = i + 1
                            
                            rule = Rule(
                                name = name,
                                title = name,
                                type = '',
                                minscale = -1,
                                maxscale = -1
                            )
                            rule.save()
                            
                            symbolizers = sld_utils.get_json_from_sld(sld, name, library)
                            for s in symbolizers:
                                scount = 0
                                stype = s['type']
                                rule.type = stype
                                rule.save()
                                s = json.dumps(s).replace("'", '"')
                                symbolizer = Symbolizer(
                                    rule = rule,
                                    type = stype,
                                    sld = sld,
                                    json = s.encode('utf-8'),
                                    order = scount
                                )
                                symbolizer.save()
                                scount += 1
                                
                            rules.append(rule)
                            
                        else:
                            not_found = False
                        
                        match3 = re.search(r'<[sld:]?([^>]*)Symbolizer>(.*)</[sld:]?[^>]*Symbolizer>', aux_symbolizer, re.DOTALL)
                    
                    aux_sld = sld_text[:match.regs[0][0]]
                    aux_sld = aux_sld + sld_text[match.regs[0][1]:]
                    sld_text = aux_sld
                    
                match = re.search(r'<[sld:]?Rule>(.*)</[sld:]?Rule>', sld_text, re.DOTALL)
    
    utils.__delete_temporaries(file_path)
    
    return rules


    
            
def check_library_path(library):
    library_path = settings.MEDIA_ROOT + "symbol_libraries/" + library.name + "/"
    try:        
        os.mkdir(library_path)
        return library_path
     
    except OSError as e:
        print('Info: %s' % e)
        return library_path
    
            
def save_external_graphic(library_path, file, file_name):    
    try: 
        file_path = library_path + file_name
        if os.path.exists(file_path):
            os.remove(file_path)
        with open(file_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
                
        return True
     
    except Exception as e:
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

def get_layer_field_description(layer_id, session):
    layer = Layer.objects.get(id=layer_id)
    datastore = layer.datastore
    workspace = datastore.workspace
    
    return backend_mapservice.getResourceInfo(workspace.name, datastore.name, layer.name, "json", session)

def get_fields(layer_id, session):
    resource = get_layer_field_description(layer_id, session)
    fields = None
    if resource != None:
        fields = resource.get('featureType').get('attributes').get('attribute')
        
    return fields

def get_alphanumeric_fields(fields):
    alphanumeric_fields = []
    for field in fields:
        if not field.get('binding').startswith('com.vividsolutions.jts.geom'):
            alphanumeric_fields.append(field)
            
    return alphanumeric_fields

def get_feature_type(fields):
    featureType = None
    for field in fields:
        if field.get('binding').startswith('com.vividsolutions.jts.geom'):
            auxType = field.get('binding').replace('com.vividsolutions.jts.geom.', '')
            if auxType == "Point" or auxType == "MultiPoint":
                featureType = "PointSymbolizer"
            if auxType == "Line" or auxType == "MultiLineString":
                featureType = "LineSymbolizer"
            if auxType == "Polygon" or auxType == "MultiPolygon":
                featureType = "PolygonSymbolizer"
                
    return featureType

def get_sld_filter_values():
    sldFilterValues = sld_utils.get_sld_filter_operations()
    for category in sldFilterValues:
        for oper in sldFilterValues[category]:
            sldFilterValues[category][oper]["genCodeFunc"] = ""
            
    return sldFilterValues

def get_raster_layer_description(layer_id, session):
    layer = Layer.objects.get(id=layer_id)
    datastore = layer.datastore
    workspace = datastore.workspace
    
    return backend_mapservice.getRasterResourceInfo(workspace.name, datastore.name, layer.name, "json", session)