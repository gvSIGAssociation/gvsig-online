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
@author: Javi Rodrigo <jrodrigo@scolab.es>
'''

from models import Style, Library, Rule, LibraryRule, Symbolizer, PolygonSymbolizer, LineSymbolizer, MarkSymbolizer, TextSymbolizer, ExternalGraphicSymbolizer
from gvsigol_services.models import Layer
from gvsigol_services.backend_mapservice import backend as mapservice
from gvsigol_core import utils as core_utils
from gvsigol import settings
from django.utils.translation import ugettext as _
from django.http import HttpResponse
import utils, sld_utils, sld_builder
import tempfile, zipfile
import StringIO
import json
import re
import os

_valid_name_regex=re.compile("^[a-zA-Z_\s][a-zA-Z0-9_\s]*$")
_valid_title_regex=re.compile("^[a-zA-Z_\s][a-zA-Z0-9_\s]*$")

class RequestError(Exception):
    def __init__(self, status_code=-1, server_message=""):
        self.status_code = status_code
        self.server_message = server_message
        self.message = server_message
    
    def set_message(self, message):
        self.message = message
    
    def get_message(self):
        if self.message:
            return self.message
        else:
            return self.server_message

class InvalidValue(RequestError):
    pass

def add_symbol(request, json_rule, library_id, symbol_type):
    
    name = json_rule.get('name')
    title = json_rule.get('title')
    
    if _valid_name_regex.search(name) == None:
        raise InvalidValue(-1, _("Invalid name: '{value}'. Name should not contain any special characters").format(value=name))
        
    #if _valid_title_regex.search(title) == None:
    #    raise InvalidValue(-1, _("Invalid title: '{value}'. Title should not contain any special characters").format(value=title))
    
    style = Style(
        name = name,
        title = title,
        is_default = False,
        type = "US"
    )
    style.save()
    
    rule = Rule(
        style = style,
        name = name,
        title = title,
        abstract = "",
        filter = str(""),
        minscale = json_rule.get('minscale'),
        maxscale = json_rule.get('maxscale'),
        order = json_rule.get('order')
    )
    rule.save()
    
    library = Library.objects.get(id=int(library_id))
    
    library_rule = LibraryRule(
        library = library,
        rule = rule
    )
    library_rule.save()
    
    symbs = json_rule.get('symbolizers')
    for sym in symbs:
        json_sym = json.loads(sym.get('json'))
        if symbol_type == 'ExternalGraphicSymbolizer':
            library_path = utils.check_library_path(library)
            file_name = name + '.png'
            if utils.save_external_graphic(library_path, request.FILES['eg-file'], file_name):
                online_resource = utils.get_online_resource(library, file_name)
                json_sym['online_resource'] = json_sym['online_resource'].replace("online_resource_replace", online_resource)
                
                symbolizer = ExternalGraphicSymbolizer(
                    rule = rule,
                    order = json_rule.get('order'),
                    opacity = json_sym.get('opacity'),
                    size = json_sym.get('size'),
                    rotation = json_sym.get('rotation'),
                    online_resource = json_sym.get('online_resource'),
                    format = json_sym.get('format')
                )
                symbolizer.save()
                
        if symbol_type == 'PolygonSymbolizer':
            symbolizer = PolygonSymbolizer(
                rule = rule,
                order = json_sym.get('order'),
                fill = json_sym.get('fill'),
                fill_opacity = json_sym.get('fill_opacity'),
                stroke = json_sym.get('stroke'),
                stroke_width = json_sym.get('stroke_width'),
                stroke_opacity = json_sym.get('stroke_opacity'),
                stroke_dash_array = json_sym.get('stroke_dash_array')              
            )
            symbolizer.save()
        
        elif symbol_type == 'LineSymbolizer':
            symbolizer = LineSymbolizer(
                rule = rule,
                order = json_sym.get('order'),
                stroke = json_sym.get('stroke'),
                stroke_width = json_sym.get('stroke_width'),
                stroke_opacity = json_sym.get('stroke_opacity'),
                stroke_dash_array = json_sym.get('stroke_dash_array')                 
            )
            symbolizer.save()      
            
        elif symbol_type == 'MarkSymbolizer' or symbol_type == 'PointSymbolizer':
            symbolizer = MarkSymbolizer(
                rule = rule,
                order = json_sym.get('order'),
                opacity = json_sym.get('opacity'),
                size = json_sym.get('size'),
                rotation = json_sym.get('rotation'),
                well_known_name = json_sym.get('well_known_name'),
                fill = json_sym.get('fill'),
                fill_opacity = json_sym.get('fill_opacity'),
                stroke = json_sym.get('stroke'),
                stroke_width = json_sym.get('stroke_width'),
                stroke_opacity = json_sym.get('stroke_opacity'),
                stroke_dash_array = json_sym.get('stroke_dash_array')                  
            )
            symbolizer.save()  
            
    sld_body = sld_builder.build_library_symbol(rule)
    if mapservice.createStyle(style.name, sld_body): 
        return True
        
    else:
        mapservice.updateStyle(None, style.name, sld_body)
        return True
    
def update_symbol(request, json_rule, rule, library_rule):
    try:
        
        name = json_rule.get('name')
        title = json_rule.get('title')
        
        #if _valid_title_regex.search(title) == None:
        #    raise InvalidValue(-1, _("Invalid title: '{value}'. Title should not contain any special characters").format(value=title))
    
        rule.title = title
        rule.save()
        symbol_type = None
        eg_file = None
        
        if 'eg-file' in request.FILES:  
            file_name = json_rule.get('file_name').split('/')[-1]
            eg_file = request.FILES['eg-file']
        
        for s in Symbolizer.objects.filter(rule=rule):
            if get_ftype(s) == 'ExternalGraphicSymbolizer':
                symbol_type = get_ftype(s)
                if eg_file is not None:
                    utils.delete_external_graphic_img(library_rule.library, file_name)
            s.delete()
            
        for sym in json_rule.get('symbolizers'):

            json_sym = json.loads(sym.get('json'))
            if json_sym.get('type') == 'ExternalGraphicSymbolizer':
                library_path = utils.check_library_path(library_rule.library)
                file_name = name + '.png'
                if eg_file is not None:
                    if utils.save_external_graphic(library_path, eg_file, file_name):
                        online_resource = utils.get_online_resource(library_rule.library, file_name)
                        json_sym['online_resource'] = json_sym['online_resource'].replace("online_resource_replace", online_resource)
                    
                symbolizer = ExternalGraphicSymbolizer(
                    rule = rule,
                    order = json_rule.get('order'),
                    opacity = json_sym.get('opacity'),
                    size = json_sym.get('size'),
                    rotation = json_sym.get('rotation'),
                    online_resource = json_sym.get('online_resource'),
                    format = json_sym.get('format')
                )
                symbolizer.save()
                    
            if json_sym.get('type') == 'PolygonSymbolizer':
                symbolizer = PolygonSymbolizer(
                    rule = rule,
                    order = json_sym.get('order'),
                    fill = json_sym.get('fill'),
                    fill_opacity = json_sym.get('fill_opacity'),
                    stroke = json_sym.get('stroke'),
                    stroke_width = json_sym.get('stroke_width'),
                    stroke_opacity = json_sym.get('stroke_opacity'),
                    stroke_dash_array = json_sym.get('stroke_dash_array')                  
                )
                symbolizer.save()
            
            elif json_sym.get('type') == 'LineSymbolizer':
                symbolizer = LineSymbolizer(
                    rule = rule,
                    order = json_sym.get('order'),
                    stroke = json_sym.get('stroke'),
                    stroke_width = json_sym.get('stroke_width'),
                    stroke_opacity = json_sym.get('stroke_opacity'),
                    stroke_dash_array = json_sym.get('stroke_dash_array')                 
                )
                symbolizer.save()      
                
            elif json_sym.get('type') == 'MarkSymbolizer':
                symbolizer = MarkSymbolizer(
                    rule = rule,
                    order = json_sym.get('order'),
                    opacity = json_sym.get('opacity'),
                    size = json_sym.get('size'),
                    rotation = json_sym.get('rotation'),
                    well_known_name = json_sym.get('well_known_name'),
                    fill = json_sym.get('fill'),
                    fill_opacity = json_sym.get('fill_opacity'),
                    stroke = json_sym.get('stroke'),
                    stroke_width = json_sym.get('stroke_width'),
                    stroke_opacity = json_sym.get('stroke_opacity'),
                    stroke_dash_array = json_sym.get('stroke_dash_array')                  
                )
                symbolizer.save()
    
        style = Style.objects.get(id=rule.style.id)
        if mapservice.deleteStyle(style.name): 
            sld_body = sld_builder.build_library_symbol(rule)
            if not mapservice.createStyle(style.name, sld_body): 
                return False
            
        return True
    
    except Exception as e:
        raise e
    
def delete_symbol(rule, library_rule):
    try:
        symbolizers = Symbolizer.objects.filter(rule_id=rule.id)
        for symbolizer in symbolizers:
            if get_ftype(symbolizer) == 'ExternalGraphic':
                file_name = rule.name + '.png'
                utils.delete_external_graphic_img(library_rule.library, file_name)
            symbolizer.delete()
        library_rule.delete()

        style = Style.objects.get(id=rule.style.id)
        if mapservice.deleteStyle(style.name):            
            style.delete()
            
        rule.delete()
    
    except Exception as e:
        raise e
    
def get_symbol(r, ftype):
    if ftype == 'ExternalGraphicSymbolizer':       
        symbolizer = Symbolizer.objects.filter(rule=r)[0]
        symbol = {
            'id': r.id,
            'name': r.name,
            'title': r.title,
            'minscale': r.minscale,
            'maxscale': r.maxscale,
            'type': ftype,
            'symbolizer_format': symbolizer.externalgraphicsymbolizer.format,
            'symbolizer_size': symbolizer.externalgraphicsymbolizer.size,
            'symbolizer_online_resource': symbolizer.externalgraphicsymbolizer.online_resource,
        }
        
    
    else:
        symbolizers = []
        for s in Symbolizer.objects.filter(rule=r).order_by('order'):
            symbolizers.append(utils.symbolizer_to_json(s))
        symbol = {
            'id': r.id,
            'name': r.name,
            'title': r.title,
            'minscale': r.minscale,
            'maxscale': r.maxscale,
            'order': r.order,
            'type': ftype,
            'symbolizers': json.dumps(symbolizers)
        }
        
    return symbol
    
def get_ftype(s):
    ftype = None
    if hasattr(s, 'externalgraphicsymbolizer'):
        ftype = 'ExternalGraphicSymbolizer'
        
    elif hasattr(s, 'marksymbolizer'):
        ftype = 'MarkSymbolizer'
            
    elif hasattr(s, 'linesymbolizer'):
        ftype = 'LineSymbolizer'
        
    elif hasattr(s, 'polygonsymbolizer'):
        ftype = 'PolygonSymbolizer'
    
    return ftype

def export_library(library, library_rules):
    dir_path = tempfile.mkdtemp(suffix='', prefix='tmp-library-')
    resource_path = dir_path+"/resources/"
    os.makedirs(resource_path)
    i=0
    for library_rule in library_rules:
        try:
            file = open(dir_path+"/symbol-"+library_rule.rule.name+"-"+str(i)+".sld",'w+')
            file.write(sld_builder.build_library_symbol(library_rule.rule))
            file.close()
            
            sld_utils.copy_resources(library_rule.rule, resource_path)
            
        except Exception as e:
            raise e
            
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


def upload_library(name, description, file):
    
    library = Library(
        name = name,
        description = description
    )
    library.save()
            
    library_path = utils.check_library_path(library)
    file_path = utils.__get_uncompressed_file_upload_path(file)
    utils.copyrecursively(file_path+"/resources/", library_path)
    
    file_list = os.listdir(file_path)
    for file in file_list:
        if not os.path.isdir(file_path+"/"+file):
            f = open(file_path+"/"+file, 'r')
            sld = sld_builder.parse_sld(f)
            
            style_name = sld.NamedLayer[0].UserStyle[0].Name
            style_title = sld.NamedLayer[0].UserStyle[0].Title
            r = sld.NamedLayer[0].UserStyle[0].FeatureTypeStyle[0].Rule[0]
            
            style = Style(
                name = style_name,
                title = style_title,
                is_default = True,
                type = "US"
            )
            style.save()
            
            rule = Rule(
                style = style,
                name = r.Name,
                title = r.Title,
                abstract = '',
                filter = str(""),
                minscale = -1 if r.MinScaleDenominator is None else r.MinScaleDenominator,
                maxscale = -1 if r.MaxScaleDenominator is None else r.MaxScaleDenominator,
                order = 0
            )
            rule.save()
            
            library_rule = LibraryRule(
                library = library,
                rule = rule
            )
            library_rule.save()
            
            scount = 0
            for s in r.Symbolizer:
                if s.original_tagname_ == 'PointSymbolizer':
                    opacity = s.Graphic.Opacity.valueOf_
                    rotation = s.Graphic.Rotation.valueOf_
                    size = s.Graphic.Size.valueOf_
                    if len(s.Graphic.Mark) >= 1:
                        mark = s.Graphic.Mark[0]
                        
                        stroke = '#000000'
                        if mark.Stroke.CssParameter.__len__() > 0:
                            stroke = mark.Stroke.CssParameter[0].valueOf_
                            
                        stroke_width = 1
                        if mark.Stroke.CssParameter.__len__() > 1:
                            stroke_width = mark.Stroke.CssParameter[1].valueOf_
                            
                        stroke_opacity = 1
                        if mark.Stroke.CssParameter.__len__() > 2:
                            stroke_opacity = mark.Stroke.CssParameter[2].valueOf_
                            
                        stroke_dash_array = 'none'
                        if mark.Stroke.CssParameter.__len__() > 3:
                            stroke_dash_array = mark.Stroke.CssParameter[3].valueOf_
                            
                        symbolizer = MarkSymbolizer(
                            rule = rule,
                            order = scount,
                            opacity = opacity,
                            size = size,
                            rotation = rotation,
                            well_known_name = mark.WellKnownName,
                            fill = mark.Fill.CssParameter[0].valueOf_,
                            fill_opacity = mark.Fill.CssParameter[1].valueOf_,
                            stroke = stroke,
                            stroke_width = stroke_width,
                            stroke_opacity = stroke_opacity,
                            stroke_dash_array = stroke_dash_array 
                        )
                        symbolizer.save()
                        
                    if len(s.Graphic.ExternalGraphic) >= 1:
                        external_graphic = s.Graphic.ExternalGraphic[0]
                        online_resource = external_graphic.OnlineResource.href.split('/')
                        online_resource[-2] = library.name
                        new_online_resource = settings.MEDIA_URL + online_resource[-3]+'/'+ library.name + '/' + online_resource[-1]
                        symbolizer = ExternalGraphicSymbolizer(
                            rule = rule,
                            order = scount,
                            opacity = opacity,
                            size = size,
                            rotation = rotation,
                            online_resource = new_online_resource,
                            format = external_graphic.Format
                        )
                        symbolizer.save()
                        
                elif s.original_tagname_ == 'LineSymbolizer':
                    stroke = '#000000'
                    if s.Stroke.CssParameter.__len__() > 0:
                        stroke = s.Stroke.CssParameter[0].valueOf_
                        
                    stroke_width = 1
                    if s.Stroke.CssParameter.__len__() > 1:
                        stroke_width = s.Stroke.CssParameter[1].valueOf_
                        
                    stroke_opacity = 1
                    if s.Stroke.CssParameter.__len__() > 2:
                        stroke_opacity = s.Stroke.CssParameter[2].valueOf_
                        
                    stroke_dash_array = 'none'
                    if s.Stroke.CssParameter.__len__() > 3:
                        stroke_dash_array = s.Stroke.CssParameter[3].valueOf_
                        
                    symbolizer = LineSymbolizer(
                        rule = rule,
                        order = scount,
                        stroke = stroke,
                        stroke_width = stroke_width,
                        stroke_opacity = stroke_opacity,
                        stroke_dash_array =stroke_dash_array                 
                    )
                    symbolizer.save()
                        
                elif s.original_tagname_ == 'PolygonSymbolizer':
                    stroke = '#000000'
                    if s.Stroke.CssParameter.__len__() > 0:
                        stroke = s.Stroke.CssParameter[0].valueOf_
                        
                    stroke_width = 1
                    if s.Stroke.CssParameter.__len__() > 1:
                        stroke_width = s.Stroke.CssParameter[1].valueOf_
                        
                    stroke_opacity = 1
                    if s.Stroke.CssParameter.__len__() > 2:
                        stroke_opacity = s.Stroke.CssParameter[2].valueOf_
                        
                    stroke_dash_array = 'none'
                    if s.Stroke.CssParameter.__len__() > 3:
                        stroke_dash_array = s.Stroke.CssParameter[3].valueOf_
                    
                    
                    symbolizer = PolygonSymbolizer(
                        rule = rule,
                        order = scount,
                        fill = s.Fill.CssParameter[0].valueOf_,
                        fill_opacity = s.Fill.CssParameter[1].valueOf_,
                        stroke = stroke,
                        stroke_width = stroke_width,
                        stroke_opacity = stroke_opacity,
                        stroke_dash_array =stroke_dash_array                
                    )
                    symbolizer.save()
                    
                scount+= 1
                
            output = StringIO.StringIO()
            sld.export(output, 0)
            sld_body = output.getvalue()
            output.close()
                
            mapservice.createStyle(style.name, sld_body)
    mapservice.reload_nodes()
    utils.__delete_temporaries(file_path)

def upload_sld(file):
    rules = []             
    return rules


def get_sld(request, type, json_data, layer_id):

    layer = Layer.objects.get(id=layer_id)
    layer.name = layer.datastore.workspace.name+':'+layer.name
    style = Style(
        name = json_data.get('name'),
        title = json_data.get('title'),
        is_default = json_data.get('is_default'),
        type = type
    )
    style.save()
            
    for r in json_data.get('rules'):
        json_rule = r.get('rule') 
        
        filter_text = ""
        if json_rule.get('filter').__len__() != 0:
            filter_text = str(json.dumps(json_rule.get('filter')))
            
        rule = Rule(
            style = style,
            name = json_rule.get('name'),
            title = json_rule.get('title'),
            abstract = '',
            filter = filter_text,
            minscale = json_rule.get('minscale'),
            maxscale = json_rule.get('maxscale'),
            order = json_rule.get('order')
        )
        rule.save()
        
        for sym in r.get('symbolizers'): 
            if sym.get('type') == 'PolygonSymbolizer':
                json_sym = json.loads(sym.get('json'))
                symbolizer = PolygonSymbolizer(
                    rule = rule,
                    order = int(sym.get('order')),
                    fill = json_sym.get('fill'),
                    fill_opacity = json_sym.get('fill_opacity'),
                    stroke = json_sym.get('stroke'),
                    stroke_width = json_sym.get('stroke_width'),
                    stroke_opacity = json_sym.get('stroke_opacity'),
                    stroke_dash_array = json_sym.get('stroke_dash_array')
                )
                symbolizer.save()
            
            elif sym.get('type') == 'LineSymbolizer':
                json_sym = json.loads(sym.get('json'))
                symbolizer = LineSymbolizer(
                    rule = rule,
                    order = int(sym.get('order')),
                    stroke = json_sym.get('stroke'),
                    stroke_width = json_sym.get('stroke_width'),
                    stroke_opacity = json_sym.get('stroke_opacity'),
                    stroke_dash_array = json_sym.get('stroke_dash_array')
                )
                symbolizer.save()
                
            elif sym.get('type') == 'MarkSymbolizer':
                json_sym = json.loads(sym.get('json'))
                symbolizer = MarkSymbolizer(
                    rule = rule,
                    order = int(sym.get('order')),
                    opacity = json_sym.get('opacity'),
                    size = json_sym.get('size'),
                    rotation = json_sym.get('rotation'),
                    well_known_name = json_sym.get('well_known_name'),
                    fill = json_sym.get('fill'),
                    fill_opacity = json_sym.get('fill_opacity'),
                    stroke = json_sym.get('stroke'),
                    stroke_width = json_sym.get('stroke_width'),
                    stroke_opacity = json_sym.get('stroke_opacity'),
                    stroke_dash_array = json_sym.get('stroke_dash_array')
                )
                symbolizer.save()
                
            elif sym.get('type') == 'ExternalGraphicSymbolizer':
                json_sym = json.loads(sym.get('json'))
                symbolizer = ExternalGraphicSymbolizer(
                    rule = rule,
                    order = int(sym.get('order')),
                    opacity = json_sym.get('opacity'),
                    size = json_sym.get('size'),
                    rotation = json_sym.get('rotation'),
                    online_resource = json_sym.get('online_resource'),
                    format = json_sym.get('format')                 
                )
                symbolizer.save()
                
            elif sym.get('type') == 'TextSymbolizer':
                json_sym = json.loads(sym.get('json'))
                symbolizer = TextSymbolizer(
                    rule = rule,
                    order = int(sym.get('order')),
                    label = json_sym.get('label'),
                    font_family = json_sym.get('font_family'),
                    font_size = json_sym.get('font_size'),
                    font_weight = json_sym.get('font_weight'),
                    font_style = json_sym.get('font_style'),
                    halo_fill = json_sym.get('halo_fill'),
                    halo_fill_opacity = json_sym.get('halo_fill_opacity'),     
                    halo_radius = json_sym.get('halo_radius'),
                    fill = json_sym.get('fill'),
                    fill_opacity = json_sym.get('fill_opacity'),
                )
                symbolizer.save()
    
    sld_body = sld_builder.build_sld(layer, style)
    style.delete()
    return sld_body
