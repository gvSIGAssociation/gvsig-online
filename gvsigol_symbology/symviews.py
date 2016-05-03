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

'''
@author: Javier Rodrigo <jrodrigo@scolab.es>
'''

from django.shortcuts import render_to_response, RequestContext, redirect, HttpResponse
from django.core import serializers
from django.db.models import Max, Q
from django.contrib.auth.decorators import login_required
from gvsigol_services.models import Layer, Datastore, Workspace
from gvsigol_services.backend_mapservice import backend as mapservice_backend
from django.utils.translation import ugettext as _  
from django.views.decorators.csrf import csrf_exempt
import xml.etree.ElementTree as ET
import json, ast
from models import LayerStyle, RuleSymbol, Style, Rule, Symbol, Library, LibrarySymbol
from utils import get_distinct_query, get_minmax_query, sortFontsArray
from django_ajax.decorators import ajax
from sld_tools import get_sld_style, get_sld_filter_operations
from backend_symbology import get_layer_field_description, get_raster_layer_description, uploadLibrary, exportLibrary
import os.path
import gvsigol.settings
from django.views.decorators.http import require_http_methods
from gvsigol_auth.utils import admin_required

  
@login_required(login_url='/gvsigonline/auth/login_user/')
@admin_required
def style_layer_list(request):
    ls = []
    layers = Layer.objects.all()
    
    for lyr in layers:
        layerStyles = LayerStyle.objects.filter(layer=lyr).order_by('order')
        styles = []
        for layerStyle in layerStyles:
            styles.append(layerStyle.style)
    
        ls.append({'layer': lyr, 'styles': styles})
    
    response = {
        'layerStyles': ls
    }
    return render_to_response('layer_symbology_list.html', response, context_instance=RequestContext(request))

@login_required(login_url='/gvsigonline/auth/login_user/')
def style_layer_add(request, layer_id, style_id):
    lyr = Layer.objects.get(id=layer_id)
    is_vectorial = False
    if lyr.type == 'v_PostGIS':
        is_vectorial = True
        
    is_view = False
    if lyr.type == 'v_PostGIS_View':
        is_view = True
       
    layer = [
             {"layer": json.loads(serializers.serialize("json",[lyr]))}
             ]
    styles = []
    geostyles = mapservice_backend.getStyles(request.session)
    for geostyle in geostyles:
        styles.append({"name": geostyle.name, "sld_code": geostyle.sld_body})
    resource = get_layer_field_description(layer_id, request.session)
    fields = []
    if resource != None:
        fields = resource.get('featureType').get('attributes').get('attribute')
    
    style_num = ""
    max_order = 0
    
    layerStyles = LayerStyle.objects.filter(layer=lyr)
    if layerStyles:
        auxmax_order = layerStyles.aggregate(Max('order'))
        max_order = auxmax_order['order__max']
        max_order = max_order + 1
    
    if max_order > 0:
        style_num = "_" + str(max_order)
    
    style_title = ""
    if style_id:
        style = Style.objects.get(id=style_id)
        style_title = style.title
    
    response = {
        'layer': json.dumps(layer),
        'fields': json.dumps(fields),
        'style_name': lyr.name + style_num,
        'style_id': style_id,
        'is_vectorial': is_vectorial,
        'is_view': is_view,
        'style_title': style_title,
        'styles': styles
    }
    return render_to_response('layer_symbology_add.html', response, context_instance=RequestContext(request))


def create_sld_style(name, layer, sld_body, session):
    exists = False
    for s in mapservice_backend.getStyles(session):
        if s.name == name:
            exists = True
    
    if not exists:
        encoded_sld = unicode(sld_body, 'utf-8')
        mapservice_backend.createStyle(name, encoded_sld, session)
        #backend.setLayerStyle(layer.name, name, session)

@login_required(login_url='/gvsigonline/auth/login_user/')
def style_layer_change(request, layer_id, style_id):
    style = create_new_style(request)
    is_deleted = delete_obsolete_style(request, style_id)
    if style and is_deleted:
        layerStyles = LayerStyle.objects.filter(style_id=style.id)
        if len(layerStyles) > 0:
            return redirect('style_layer_update' , layer_id=layerStyles[0].layer_id, style_id=style.id)
    redirect('style_layer_list')

def create_style(request):
    style = create_new_style(request)
    if style:
        layerStyles = LayerStyle.objects.filter(style_id=style.id)
        if len(layerStyles) > 0:
            return redirect('style_layer_update' , layer_id=layerStyles[0].layer_id, style_id=style.id)
    redirect('style_layer_list')

def create_new_style(request):
    if request.method == "POST":
        saved_title = request.POST.get("symbology-title")
        saved_name = request.POST.get("symbology-name")
        save_type = request.POST.get("legend-type")
        layer_id = request.POST.get("layer-id")
        sld_code = request.POST.get("sld-code")
        lyr = Layer.objects.get(id=layer_id)
        
        stl = Style(title=saved_title, name=saved_name, description=saved_name, type=save_type)
        stl.save()
        
        layerStyles = LayerStyle.objects.filter(layer=lyr)
        max_order = 0
        if layerStyles:
            auxmax_order = layerStyles.aggregate(Max('order'))
            max_order = auxmax_order['order__max']
        lysStl = LayerStyle(title=saved_title, name=saved_name, description=saved_name, style=stl, layer=lyr, order=max_order+1)
        lysStl.save()
        if sld_code:
            create_sld_style(stl.name, lyr, str(sld_code), request.session)
            
        return stl
            
    return None

def delete_obsolete_style(request, style_id):
    stl = Style.objects.get(id=style_id)
    layerStyles = LayerStyle.objects.filter(style=stl)
    
    for layerStyle in layerStyles:
        lyr = Layer.objects.get(id=layerStyle.layer.id)
        count = LayerStyle.objects.filter(layer=lyr).count()
        if count==1:
            return False
    
    if stl.type == "IM" or stl.type == "IR":
        mapservice_backend.deleteStyle(stl.name, request.session)
    stl.delete()
    
    return True


@login_required(login_url='/gvsigonline/auth/login_user/')
def delete_style(request, style_id):
    if not delete_obsolete_style(request, style_id):
        return HttpResponse('ERROR: no se puede borrar ya que es el unico estilo de la capa')  
    return redirect('style_layer_list')



@login_required(login_url='/gvsigonline/auth/login_user/')
def save_style(request, layer_id, style_id):
    if request.method == 'POST':
        data = request.POST['datos']
        results = json.loads(data)
        
        style = Style.objects.get(id=style_id)
        layerStyle = LayerStyle.objects.get(layer=layer_id, style=style_id)
        # Borrar reglas anteriores
        xruls = Rule.objects.filter(style_id=style_id)
        for xrul in xruls:
            xrlsys = RuleSymbol.objects.filter(rule_id = xrul.id)
            for xrlsy in xrlsys:
                xsy = xrlsy.symbol_id
                xrlsy.delete()
                if RuleSymbol.objects.filter(symbol_id = xsy).count() == 0:
                    Symbol.objects.filter(id = xsy).delete()
            xrul.delete()
            
        # Crear las nuevas
        for result in results.get('data'):
            #Crear la regla
            rulejson = result.get('rule')[0]
            rupdates = rulejson.get('fields')
            if (rupdates.get('minscale') != None) and (len(str(rupdates['minscale'])) == 0):
                del rupdates['minscale']
            if (rupdates.get('maxscale') != None) and (len(str(rupdates['maxscale'])) == 0):
                del rupdates['maxscale']
            rul = Rule.objects.create(**rupdates)
            rid = rul.id
            
            #Crear todos los simbolos
            for symbols in result.get('symbols'):
                updates = symbols.get('fields')
                symid = symbols.get('pk')
                
                try:
                    sm = Symbol.objects.get(id=symid)
                    sm.update(**updates)
                except Symbol.DoesNotExist:
                    sm = Symbol.objects.create(**updates)
                    symid = sm.id 
                
                #Crear la relacion regla-simbolo
                RuleSymbol.objects.create(rule_id = rid, symbol_id = symid)
                
        sld_body = get_sld_style(layer_id, style_id, request.session)
        layer = Layer.objects.get(id=layer_id)
        datastore = Datastore.objects.get(id=layer.datastore_id) 
        workspace = Workspace.objects.get(id=datastore.workspace_id)
        print(sld_body.encode("utf-8"))
        
        response = {}
        if not mapservice_backend.createStyle(style.name, sld_body, request.session): 
            if not mapservice_backend.getStyle(style.name, request.session) or not mapservice_backend.updateStyle(style.name, sld_body.encode('utf-8'), request.session):
                    response = {'message': 'ERROR'}
        
        layerStyles = LayerStyle.objects.filter(layer=layer).order_by('order')
        if len(layerStyles) > 0 and str(layerStyles[0].style_id) == str(style_id):
            mapservice_backend.setLayerStyle(workspace.name+":"+layer.name, style.name, request.session)
            
        layer.style = style.name
        layer.save()
        return render_to_response('layer_symbology_list.html', response, context_instance=RequestContext(request))
      
    response = {}
    return render_to_response('layer_symbology_list.html', response, context_instance=RequestContext(request))


@ajax
@login_required(login_url='/gvsigonline/auth/login_user/')
def save_legend(request, layer_id, style_id):
    if request.method == 'POST': 
        stl = Style.objects.get(id=style_id)
        #stl.name = lyr.name
        stl.title = request.POST.get('title')
        stl.description = request.POST.get('description')
        stl.save()
        
    return {'message': 'OK'}


@ajax
@login_required(login_url='/gvsigonline/auth/login_user/')
def symbol_library_add(request, library_id, symbol_id):
    if request.method == 'POST': 
                
        title = request.POST.get('title')
        typ = request.POST.get('type')
        sld = request.POST.get('sld-code')
        
        if symbol_id:
            sym = LibrarySymbol.objects.get(id=symbol_id)
            sym.name = title
            sym.sld_code = sld
            sym.save()
        else:
            sym = LibrarySymbol(name=title, description="", sld_code=sld, type=typ, is_public=False, library_id=library_id)
            sym.save()
        
    return {'message': 'OK'}


@ajax
@login_required(login_url='/gvsigonline/auth/login_user/')
def set_default_style(request, layer_id, style_id):
    lyr = Layer.objects.get(id=layer_id)
    datastore = Datastore.objects.get(id=lyr.datastore_id) 
    workspace = Workspace.objects.get(id=datastore.workspace_id)
    stl = Style.objects.get(id=style_id)
    
    currentLayerStyle = LayerStyle.objects.get(layer=lyr, style=stl)
    layerStyles = LayerStyle.objects.filter(layer=lyr)
    
    for layerStyle in layerStyles:
        if layerStyle.order <= currentLayerStyle.order:
            layerStyle.order = layerStyle.order+1
            layerStyle.save()
    
    currentLayerStyle.order = 0
    currentLayerStyle.save()
    
    mapservice_backend.setLayerStyle(workspace.name+":"+lyr.name, stl.name, request.session)
    
    return {'message': 'OK'}

@ajax
@login_required(login_url='/gvsigonline/auth/login_user/')
def get_unique_values(request, layer_id, field):
    lyr = Layer.objects.get(id=layer_id)
    connection = ast.literal_eval(lyr.datastore.connection_params)
    #connection = json.loads(connectionStr)
    
    unique_fields = get_distinct_query(connection, lyr.name, field)
    
    return {'values': unique_fields}


@ajax
@login_required(login_url='/gvsigonline/auth/login_user/')
def get_minmax_values(request, layer_id, field):
    lyr = Layer.objects.get(id=layer_id)
    connection = ast.literal_eval(lyr.datastore.connection_params)
    
    result = get_minmax_query(connection, lyr.name, field)
    return result

@ajax
@login_required(login_url='/gvsigonline/auth/login_user/')
def get_minmax_rastervalues(request, layer_id, style_id):
    result = {"min": None, "max": None, "null": None}
    resource = get_raster_layer_description(layer_id, request.session)
    
    if resource and resource.get("coverage") and resource["coverage"].get("dimensions") and resource["coverage"]["dimensions"].get("coverageDimension"):
        aux_resource = resource["coverage"]["dimensions"]["coverageDimension"][0]
        if aux_resource.get("range") and aux_resource["range"].get("min") != None:  
            if str(aux_resource["range"]["min"]) == "-inf":
                result["min"] = None
            else:
                result["min"] = aux_resource["range"]["min"]
        if aux_resource.get("range") and aux_resource["range"].get("max") != None:
            if str(aux_resource["range"]["max"]) == "inf":
                result["max"] = None
            else:   
                result["max"] = aux_resource["range"]["max"]
        if aux_resource.get("nullValues"):   
            result["null"] = aux_resource["nullValues"]["double"][0]
            
    #if result["max"] == None or result["min"] == None:
        #style = Style.objects.get(id=style_id)
        #style.type = "IM"
        #style.save()
        
    return result


@ajax
@login_required(login_url='/gvsigonline/auth/login_user/')
def get_libraries(request):
    libraries = Library.objects.all()
        
    libraries_json = {}
    for library in libraries:
        libraries_json.update({str(library.id): library.name})
    return json.dumps(libraries_json)


@ajax
@login_required(login_url='/gvsigonline/auth/login_user/')
def symbol_library_update(request, symbol_library_id):
    if request.method == 'POST': 
        stl = LibrarySymbol.objects.get(id=symbol_library_id)
        #stl.name = lyr.name
        stl.name = request.POST.get('title')
        stl.description = request.POST.get('description')
        stl.save()
        
    return {'message': 'OK'}


@ajax
@login_required(login_url='/gvsigonline/auth/login_user/')
def symbol_library_delete(request, symbol_library_id):
    if request.method == 'POST': 
        stl = LibrarySymbol.objects.get(id=symbol_library_id)
        stl.delete()
        
    return {'message': 'OK'}


@ajax
@login_required(login_url='/gvsigonline/auth/login_user/')
def get_library_symbols(request, library_id):
    library = Library.objects.get(id=library_id)
    symbols = {}
    if library:
        symbols = LibrarySymbol.objects.filter(library_id=library.id)
    return json.loads(serializers.serialize('json',symbols))

@login_required(login_url='/gvsigonline/auth/login_user/')
@admin_required
def library_list(request):
    libraries = Library.objects.all()
    response = {
        'libraries': libraries
    }
    return render_to_response('symbol_library_list.html', response, context_instance=RequestContext(request))

@login_required(login_url='/gvsigonline/auth/login_user/')
def library_update(request, library_id):      
    response = {}
    return redirect('symbol_library_add.html', response, context_instance=RequestContext(request))

@login_required(login_url='/gvsigonline/auth/login_user/')
def library_add(request, library_id):
    if request.method == 'POST': 
        
        if not library_id:
            lib = Library(title=request.POST.get('library-title'), name=request.POST.get('library-title'), description=request.POST.get('library-description'),is_public=False)
        else:
            lib = Library.objects.get(id=library_id)
            lib.title = request.POST.get('library-title')
            lib.name = request.POST.get('library-title')
            lib.description = request.POST.get('library-description')
            lib.is_public = False
        
        lib.save()
        return redirect('library_list')
    
    library = []
    symbols = []
    is_new = True
    is_editable = True
    if library_id != None:
        lib = Library.objects.get(id=library_id)
        syms = LibrarySymbol.objects.filter(library_id=lib.id)
        is_new = False
        is_editable = not lib.is_public
        
        library = json.loads(serializers.serialize("json",[lib]))
        for sym in syms: 
            symbols.append(json.loads(serializers.serialize("json",[sym])))
    
    response = {
        'library_id': library_id,  
        'is_new': is_new,
        'is_editable': is_editable,
        'library': json.dumps(library),
        'symbols': json.dumps(symbols),
    }
    return render_to_response('symbol_library_add.html', response, context_instance=RequestContext(request))


@login_required(login_url='/gvsigonline/auth/login_user/')
def library_delete(request, library_id):
    symbols = LibrarySymbol.objects.filter(library_id=library_id)
    for symbol in symbols:
        symbol.delete()
    
    lib = Library.objects.get(id=library_id)
    lib.delete()
    return redirect('library_list')


    
def style_symbology_update(request, layer_id, style_id, is_label):
    ls = []
    lbs = []
    style = Style.objects.get(id=int(style_id))
    supportedfontsStr = mapservice_backend.getSupportedFonts(request.session)
    supportedfonts = json.loads(supportedfontsStr)
    sorted_fonts = sortFontsArray(supportedfonts.get("fonts"))
    sld_code = "{}"
    if style.type == "IM" or style.type == "IR":
        sld_object = mapservice_backend.getStyle(style.name, request.session)
        if sld_object:
            sld_code = {
                       "name": str(style.name),
                       "sld_code" : sld_object.sld_body
                       }
        else:
            sld_code = {
                        "name": str(style.name),
                        "sld_code" : ""
                       }
    
    rules = Rule.objects.filter(style_id=style.id)
    lyr = Layer.objects.get(id=layer_id)
    layer = [
             {"layer": json.loads(serializers.serialize("json",[lyr]))}
             ]
    datastore = Datastore.objects.get(id=lyr.datastore_id) 
    workspace = Workspace.objects.get(id=datastore.workspace_id)
    works = [
             {"workspace": json.loads(serializers.serialize("json",[workspace]))}
             ]
    layerStyle = LayerStyle.objects.get(layer=lyr, style=style)
    minLayerStyle = LayerStyle.objects.filter(layer=lyr).order_by('order')
    minOrder = minLayerStyle[0].order
    
    is_default = (layerStyle.order == minOrder)
    
    resource = get_layer_field_description(layer_id, request.session)
    fields = []
    if resource != None:
        fields = resource.get('featureType').get('attributes').get('attribute')
        
    for rl in rules:
        rulejson = json.loads(serializers.serialize('json',[rl]))
        rulefieldsjson = rulejson[0].get('fields')
        if rulefieldsjson.get('style') != None:
            rulefieldsjson['style_id'] = rulefieldsjson['style']
            del rulefieldsjson['style']
            
        ruleSymbols = RuleSymbol.objects.filter(rule=rl)
        symbols = []
        labelsymbols = []
        for ruleSymbol in ruleSymbols:
            symbol = Symbol.objects.get(id=ruleSymbol.symbol.id)
            if symbol.sld_code.startswith("<TextSymbolizer>"):
                labelsymbols.append(symbol)
            else:
                symbols.append(symbol)
        
        if symbols:
            ls.append({
                "rule": rulejson, 
                "symbols": json.loads(serializers.serialize('json',symbols))
            })
        if labelsymbols:
            lbs.append({
                "rule": rulejson, 
                "symbols": json.loads(serializers.serialize('json',labelsymbols))
            })
    
    if is_label:
        featureType = "TextSymbolizer"
    else:
        featureType = "PointSymbolizer"
        for field in fields:
            if field.get('binding').startswith('com.vividsolutions.jts.geom'):
                auxType = field.get('binding').replace('com.vividsolutions.jts.geom.', '')
                if auxType == "Point" or auxType == "MultiPoint":
                    featureType = "PointSymbolizer"
                if auxType == "Line" or auxType == "MultiLineString":
                    featureType = "LineSymbolizer"
                if auxType == "Polygon" or auxType == "MultiPolygon":
                    featureType = "PolygonSymbolizer"
    
    sldFilterValues = get_sld_filter_operations()
    for category in sldFilterValues:
        for oper in sldFilterValues[category]:
            sldFilterValues[category][oper]["genCodeFunc"] = ""
        
    response = {
        'username': request.session['username'],
        'password': request.session['password'],
        'supported_crs': json.dumps(gvsigol.settings.SUPPORTED_CRS),
        'is_default_style': is_default,
        'layerStyle': layerStyle,
        'layer': json.dumps(layer),
        'workspace': json.dumps(works),
        'style': style,
        'rules': json.dumps(ls),
        'labels': json.dumps(lbs),
        'fields': json.dumps(fields), 
        'sldFilterValues': json.dumps(sldFilterValues),
        'featureType': featureType,
        'sld_object': sld_code,
        'sorted_fonts': sorted_fonts
    }
    return response

@login_required(login_url='/gvsigonline/auth/login_user/')
def style_label_update(request, layer_id, style_id):
    response = style_symbology_update(request, layer_id, style_id, True)
    return render_to_response('layer_labelling_update.html', response, context_instance=RequestContext(request))
  
@login_required(login_url='/gvsigonline/auth/login_user/')
def style_layer_update(request, layer_id, style_id):
    response = style_symbology_update(request, layer_id, style_id, False)
    return render_to_response('layer_symbology_update.html', response, context_instance=RequestContext(request))

@csrf_exempt
@ajax
def load_rmf(request):        
    if request.method == 'POST':
        #file_name = request.FILES['rmf'].name
        #extension = file_name.split('.')[1]
        
        if True: #extension == 'rmf':
            string_rmf =  request.POST.get('data') #request.FILES['rmf'].read()
            
            rmf = ET.fromstring(string_rmf)
            
            color_map = []
            for childs in rmf:
                if childs.tag == 'ColorTable':
                    for child in childs:
                        if child.tag == 'Color':
                            color_map_entry = {}
                            rgb = child.attrib['rgb'].split(',')
                            color = '#'+''.join(map(chr, (int(rgb[0]), int(rgb[1]), int(rgb[2])))).encode('hex')
                            color_map_entry['color'] = color
                            color_map_entry['quantity'] = child.attrib['value']
                            color_map_entry['label'] = child.attrib['name']
                            color_map_entry['opacity'] = "1"
                            color_map.append(color_map_entry)
                            
                    for child in childs:
                        if child.tag == 'Alpha':
                            for cme in color_map:
                                if cme['quantity'] == child.attrib['value']:
                                    aux = float(child.attrib['alpha'])/256
                                    aux = float("{0:.2f}".format(aux))
                                    cme['opacity'] = str(aux)
    
                
            response = {
                'success': True,
                'color_map': color_map
            }               
            return response
        
        else:
            response = {
                'success': False
            }
            return response


@csrf_exempt
@ajax
def symbol_exists(request):        
    if request.method == 'POST':
        name = request.POST.get('name')
        url = "/var/www/media/" + name;
       
        if os.path.exists(url):
            response = {
                'success': False
            }
            return response
        else:
            response = {
                'success': True
            }
            return response
        
    response = {
        'success': False
    }
    return response 
       
       
@csrf_exempt
@ajax
def symbol_upload(request):        
    if request.method == 'POST':
        file = request.FILES['file']
        file_name = request.POST.get('name')
        extension = file.name.split('.')[1]
        if len(file_name) == 0:
            file_name = file.name
        if not file_name.endswith("." + extension):
            file_name = file_name + "." + extension
       
        if True: #extension == 'rmf':
            with open(gvsigol.settings.MEDIA_ROOT + file_name, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)     
            response = {
                'success': True,
                'main_url': "/media/",
                'filename': file_name
            }               
            return response
        
    response = {
        'success': False
    }
    return response

@require_http_methods(["GET", "POST", "HEAD"])
@login_required(login_url='/gvsigonline/auth/login_user/')
@admin_required
def library_upload(request, library_id):
    if request.method == 'POST':
        file = request.FILES['file']
        symbolizers = uploadLibrary(file)
        
        if library_id is None:
            library_name = request.POST.get('library-name')
            library_title = request.POST.get('library-title')
            library_description = request.POST.get('library-description')
            
            library = Library(title=library_title, name=library_name, description=library_description, is_public=False)
            library.save()
        else:
            library = Library.objects.get(id=library_id)
            
        for key in symbolizers:
            for symb in symbolizers[key]:
                sld = symb["sld_code"].replace("sld:", "")
                sld = sld.replace("ogc:", "")
                sym = LibrarySymbol(name=symb["name"], description="", sld_code=sld, type=key+"Symbolizer", is_public=False, library_id=library.id)
                sym.save()
            
        return redirect('library_list')
    else:
        libraries = Library.objects.all()
        libraries_serialize = json.loads(serializers.serialize('json',libraries))
            
        data = {
            'libraries': json.dumps(libraries_serialize)
        }
        return render_to_response('library_upload.html', data, context_instance=RequestContext(request))

@csrf_exempt
def library_export(request, library_id):
    library = Library.objects.get(id=library_id)
    simbols = LibrarySymbol.objects.filter(library_id=library.id)
    #file = request.POST.get('dest')

    response = exportLibrary(library, simbols)
                                 
    return response
     
