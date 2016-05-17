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
#from twisted.test.test_tcp_internals import resource
'''
@author: Jose Badia <jbadia@scolab.es>
'''

from gvsigol_services.backend_mapservice import backend as backend_mapservice
from gvsigol_services.models import Layer
from django.http import HttpResponse
from xml.sax.saxutils import escape
from gvsigol import settings
import tempfile, zipfile
import os, shutil, errno
import sld_tools
import StringIO
import re


def exportLibrary(library, symbols):
    dir_path = tempfile.mkdtemp(suffix='', prefix='tmp-library-')
    resource_path = dir_path+"/resources/"
    os.makedirs(resource_path)
    i=0
    for symbol in symbols:
        try:
            file = open(dir_path+"/symbol-"+symbol.name+"-"+str(i)+".sld",'w+')
            file.write(create_basic_sld(library, symbol, resource_path))
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
    
    __delete_temporaries(dir_path)
    
    return response


def create_basic_sld(library, symbol, resource_folder_path):
    sld = "<StyledLayerDescriptor version=\"1.0.0\" xmlns=\"http://www.opengis.net/sld\" xmlns:ogc=\"http://www.opengis.net/ogc\" "
    sld += "xmlns:sld=\"http://www.opengis.net/sld\"  xmlns:gml=\"http://www.opengis.net/gml\" " 
    sld +=   "xmlns:xlink=\"http://www.w3.org/1999/xlink\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" "
    sld +=   "xsi:schemaLocation=\"http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd\">"
    sld += "<NamedLayer>"
    
    sld += "<Name>"+ library.name +"</Name>"
    
    sld += "<UserStyle>"
    sld += "<Name>"+ library.name +"</Name>"
    sld += "<Title>"+ escape(library.title) +"</Title>"
    sld += "<Abstract>"+ escape(library.description) +"</Abstract>"
    sld += "<FeatureTypeStyle>"
    
    sld += "<Rule>"
    sld += "<Name>"+ escape(symbol.name) +"</Name>"
        
    symbs = get_symbolizers(symbol.sld_code)
    for symb in symbs:
        sld += get_graphics_sld(symb, resource_folder_path)
            
    sld += "</Rule>"
    
    sld += "</FeatureTypeStyle>"
    sld += "</UserStyle>"
    sld += "</NamedLayer>"
    sld += "</StyledLayerDescriptor>"
    
    return sld   

def get_symbolizers(sld):
    regex = re.compile('<\/[\\w]*Symbolizer>')
    symbs = []
    
    if re.search(regex, sld):
        while re.search(regex, sld):
            m = re.search(regex, sld)
            if m:
                symbs.append(sld[0:m.regs[0][1]])
                if sld.__len__ > m.regs[0][1]:
                    sld = sld[m.regs[0][1]:]
                else:
                    sld = ""
    else:
        symbs = [sld]   
    
    return symbs

def get_graphics_sld(filter, resource_folder_path):
    regex = re.compile(r'<ExternalGraphic>(.*)</ExternalGraphic>')
    match = re.search(regex, filter)
    if match:
        if match.regs.__len__() < 2:
            return filter;
        geom_op = filter[match.regs[1][0]:match.regs[1][1]]
        if len(geom_op) != 0:
            resource_path = None
            if not geom_op.startswith("<OnlineResource"):
                if geom_op.startswith("http://chart"):
                    type = ""
                    href = "xlink:href=\"" + geom_op +"\""
                    format = "application/chart"
                else:
                    type = "xmlns:xlink=\"http://www.w3.org/1999/xlink\" xlink:type=\"simple\" "
                    href = "xlink:href=\"file:"+"/"+"/" + settings.MEDIA_ROOT + geom_op +"\""
                    format = "image/png"
                    resource_path = settings.MEDIA_ROOT + geom_op
                
                new_filter = "<OnlineResource "+type+""+ href +" />"
                new_filter = new_filter + "<Format>"+format+"</Format>"
                filter = regex.sub("<ExternalGraphic>"+ new_filter+"</ExternalGraphic>", filter)
                regex2 = re.compile(r'<Mark>(.*)</Mark>')
                filter = regex2.sub("", filter)
            else:
                match2 = re.findall(r'xlink:href="([^"]*)"', geom_op)
                #match2 = re.search(regex2, geom_op)
                if match2.__len__>0 and match2[0].startswith("file:"):
                    resource_path =  match2[0].replace("file:", "")
                
            if resource_path:
                local_path = resource_path.replace(settings.MEDIA_ROOT, "")
                copy(resource_path, resource_folder_path + local_path)
            
        else:
            filter = regex.sub("", filter)
    
    return filter


def uploadLibrary(file_upload):
    file_path = __get_uncompressed_file_upload_path(file_upload)
    copyrecursively(file_path+"/resources/", settings.MEDIA_ROOT)
    symbolizers = {}
    
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
                            
                            if not type in symbolizers:
                                symbolizers[type] = []
                            
                            symbolizers[type].append({
                                'name' :  name,
                                'file' : file, 
                                'sld_code' : sld
                            })
                            
                            print "     Name: " + name
                            print "     File: " + file
                            print "     Code: " + sld
                            
                        else:
                            not_found = False
                        
                        match3 = re.search(r'<[sld:]?([^>]*)Symbolizer>(.*)</[sld:]?[^>]*Symbolizer>', aux_symbolizer, re.DOTALL)
                    
                    aux_sld = sld_text[:match.regs[0][0]]
                    aux_sld = aux_sld + sld_text[match.regs[0][1]:]
                    sld_text = aux_sld
                    
                match = re.search(r'<[sld:]?Rule>(.*)</[sld:]?Rule>', sld_text, re.DOTALL)
    
    __delete_temporaries(file_path)
    
    return symbolizers
    
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
    
def copyrecursively(source_folder, destination_folder):
    for root, dirs, files in os.walk(source_folder):
        for item in files:
            src_path = os.path.join(root, item)
            dst_path = os.path.join(destination_folder, src_path.replace(source_folder, ""))
            if os.path.exists(dst_path):
                if os.stat(src_path).st_mtime > os.stat(dst_path).st_mtime:
                    shutil.copyfile(src_path, dst_path)
            else:
                shutil.copyfile(src_path, dst_path)
        for item in dirs:
            src_path = os.path.join(root, item)
            dst_path = os.path.join(destination_folder, src_path.replace(source_folder, ""))
            if not os.path.exists(dst_path):
                os.mkdir(dst_path)

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
        print('Error: %s' % e)
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
    sldFilterValues = sld_tools.get_sld_filter_operations()
    for category in sldFilterValues:
        for oper in sldFilterValues[category]:
            sldFilterValues[category][oper]["genCodeFunc"] = ""
            
    return sldFilterValues

def get_raster_layer_description(layer_id, session):
    layer = Layer.objects.get(id=layer_id)
    datastore = layer.datastore
    workspace = datastore.workspace
    
    return backend_mapservice.getRasterResourceInfo(workspace.name, datastore.name, layer.name, "json", session)