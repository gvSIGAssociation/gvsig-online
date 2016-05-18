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

from backend_symbology import get_layer_field_description
from gvsigol_services.models import Datastore, Workspace, Layer
from models import Style, Rule, StyleRule, Symbolizer
from django_ajax.decorators import ajax
from xml.sax.saxutils import escape
import gvsigol.settings
import json
import re

def parentesis_operation(operators, filter, auxTranslations, fields):
    if(operators.__len__() == 0):
        return filter;
    
    
    new_filter = filter[operators[1][0]:operators[1][1]]
    code = getSLDCodeFilter(new_filter, auxTranslations, fields)
    index = auxTranslations.__len__();
    auxTranslations.append(code);
    
    return {"filter": filter.replace("("+new_filter+")", "@@"+str(index)),
            "translations": auxTranslations};

def logical_not_operation(operators, filter, auxTranslations, fields):
    if operators.__len__() == 0:
        return "";
    if operators.__len__() < 2:
        return filter;
    new_filter0 = filter[operators[0][0]:operators[0][1]]
    new_filter1 = filter[operators[1][0]:operators[1][1]]
    
    auxTranslations.append("<Not>"+ getSLDCodeFilter(new_filter1, auxTranslations, fields) +"</Not>")
    
    index = auxTranslations.__len__()-1;
    return {"filter": filter.replace(new_filter0, "@@"+str(index)),
            "translations": auxTranslations};

def logical_and_operation(operators, filter, auxTranslations, fields):
    return logical_operation("And", operators, filter, auxTranslations, fields)

def logical_or_operation(operators, filter, auxTranslations, fields):
    return logical_operation("Or", operators, filter, auxTranslations, fields)
            
def logical_operation(tag, operators, filter, auxTranslations, fields):
    if operators.__len__() == 0:
        return "";
    if operators.__len__() < 3:
        return filter;
    new_filter0 = filter[operators[0][0]:operators[0][1]]
    new_filter1 = filter[operators[1][0]:operators[1][1]]
    new_filter2 = filter[operators[2][0]:operators[2][1]]
    
    auxTranslations.append("<"+tag+">"+ getSLDCodeFilter(new_filter1, auxTranslations, fields)+ getSLDCodeFilter(new_filter2, auxTranslations, fields)+ "</"+tag+">")
    
    index = auxTranslations.__len__()-1;
    return {"filter": filter.replace(new_filter0, "@@"+str(index)),
            "translations": auxTranslations};

def comparative_between_operation(operators, filter, auxTranslations, fields):
    if operators.__len__() == 0:
        return "";
    if operators.__len__() < 4:
        return filter;
    new_filter0 = filter[operators[0][0]:operators[0][1]]
    new_filter1 = filter[operators[1][0]:operators[1][1]]
    campo = filter[operators[2][0]:operators[2][1]]
    new_filter2 = filter[operators[3][0]:operators[3][1]]
    
    auxTranslations.append(
        "<ogc:PropertyIsBetween>"+
            getSLDCodeFilter(campo, auxTranslations, fields) +
        "<ogc:LowerBoundary>"+
            getSLDCodeFilter(new_filter1, auxTranslations, fields) + 
        "</ogc:LowerBoundary>"+
        "<ogc:UpperBoundary>"+
            getSLDCodeFilter(new_filter2, auxTranslations, fields) +
        "</ogc:UpperBoundary>"+
        "</ogc:PropertyIsBetween>")
    
    index = auxTranslations.__len__()-1;
    return {"filter": filter.replace(new_filter0, "@@"+str(index)),
            "translations": auxTranslations};

def comparative_null_operation(operators, filter, auxTranslations, fields):
    if operators.__len__() == 0:
        return filter;
    if operators.__len__() > 1:
        new_filter = filter[operators[1][0]:operators[1][1]]
    
    new_filter0 = filter[operators[0][0]:operators[0][1]]
    auxTranslations.append("<ogc:PropertyIsNull><PropertyName>"+ new_filter + "</PropertyName></ogc:PropertyIsNull>")
    
    index = auxTranslations.__len__()-1;
    return {"filter": filter.replace(new_filter0, "@@"+str(index)),
            "translations": auxTranslations};

def comparative_greaterthan_operation(operators, filter, auxTranslations, fields):
    return comparative_operation("PropertyIsGreaterThan", operators, filter, auxTranslations, fields)

def comparative_greaterthanorequal_operation(operators, filter, auxTranslations, fields):
    return comparative_operation("PropertyIsGreaterThanOrEqualTo", operators, filter, auxTranslations, fields)

def comparative_lessthan_operation(operators, filter, auxTranslations, fields):
    return comparative_operation("PropertyIsLessThan", operators, filter, auxTranslations, fields)

def comparative_lessthanorequal_operation(operators, filter, auxTranslations, fields):
    return comparative_operation("PropertyIsLessThanOrEqualTo", operators, filter, auxTranslations, fields)

def comparative_equal_operation(operators, filter, auxTranslations, fields):
    return comparative_operation("PropertyIsEqualTo", operators, filter, auxTranslations, fields)

def comparative_notequal_operation(operators, filter, auxTranslations, fields):
    return comparative_operation("PropertyIsNotEqualTo", operators, filter, auxTranslations, fields)

def comparative_operation(tag, operators, filter, auxTranslations, fields):
    if operators.__len__() == 0:
        return "";
    if operators.__len__() < 3:
        return filter;
    new_filter0 = filter[operators[0][0]:operators[0][1]]
    new_filter1 = filter[operators[1][0]:operators[1][1]]
    new_filter2 = filter[operators[2][0]:operators[2][1]]
    
    auxTranslations.append("<"+tag+">"+ getSLDCodeFilter(new_filter1, auxTranslations, fields)+ getSLDCodeFilter(new_filter2, auxTranslations, fields)+ "</"+tag+">")
    
    index = auxTranslations.__len__()-1;
    return {"filter": filter.replace(new_filter0, "@@"+str(index)),
            "translations": auxTranslations};


def arithmetic_add_operation(operators, filter, auxTranslations, fields):
    return arithmetic_operation("Add", operators, filter, auxTranslations, fields)

def arithmetic_sub_operation(operators, filter, auxTranslations, fields):
    return arithmetic_operation("Sub", operators, filter, auxTranslations, fields)

def arithmetic_mult_operation(operators, filter, auxTranslations, fields):
    return arithmetic_operation("Mul", operators, filter, auxTranslations, fields)

def arithmetic_div_operation(operators, filter, auxTranslations, fields):
    return arithmetic_operation("Div", operators, filter, auxTranslations, fields)
            
def arithmetic_operation(tag, operators, filter, auxTranslations, fields):
    if operators.__len__() == 0:
        return "";
    if operators.__len__() < 3:
        return filter;
    new_filter0 = filter[operators[0][0]:operators[0][1]]
    new_filter1 = filter[operators[1][0]:operators[1][1]]
    new_filter2 = filter[operators[2][0]:operators[2][1]]
    
    auxTranslations.append("<"+tag+">"+ getSLDCodeFilter(new_filter1, auxTranslations, fields)+ getSLDCodeFilter(new_filter2, auxTranslations, fields)+ "</"+tag+">")
    
    index = auxTranslations.__len__()-1;
    return {"filter": filter.replace(new_filter0, "@@"+str(index)),
            "translations": auxTranslations};

def function_area_operation(operators, filter, auxTranslations, fields):
    return function_operation("area", operators, filter, auxTranslations, fields)

def function_centroid_operation(operators, filter, auxTranslations, fields):
    return function_operation("centroid", operators, filter, auxTranslations, fields)

def function_convexhull_operation(operators, filter, auxTranslations, fields):
    return function_operation("convexhull", operators, filter, auxTranslations, fields)
    
def function_operation(operation, operators, filter, auxTranslations, fields):
    if operators.__len__() == 0:
        return filter;
    parameters = "";
    if operators.__len__() > 1:
        new_filter = filter[operators[1][0]:operators[1][1]]
        params = new_filter.split(",");
        for param in params:
            parameters = parameters + getSLDCodeFilter(param, auxTranslations, fields)
    
    new_filter0 = filter[operators[0][0]:operators[0][1]]
    auxTranslations.append("<ogc:Function name=\""+operation+"\">"+ parameters + "</ogc:Function>")
    
    index = auxTranslations.__len__()-1;
    return {"filter": filter.replace(new_filter0, "@@"+str(index)),
            "translations": auxTranslations};
            
            
def basic_literal_operations(operators, filter, auxTranslations, fields):
    if operators.__len__() == 0:
        return filter
    
    new_filter = filter[operators[1][0]:operators[1][1]].strip()
    if new_filter.startswith("@@"):
        index = new_filter.replace("@@", "")
        return auxTranslations[int(index)]
    
    new_filter0 = filter[operators[0][0]:operators[0][1]]
    for field in fields:
        if field["name"] == new_filter:
            auxTranslations.append("<PropertyName>"+ new_filter + "</PropertyName>")
            index = auxTranslations.__len__()-1;
            return {"filter": filter.replace(new_filter0, "@@"+str(index)),
            "translations": auxTranslations};
        
    auxTranslations.append("<Literal>"+ new_filter.replace('"', '') + "</Literal>")
    index = auxTranslations.__len__()-1;
    return {"filter": filter.replace(new_filter0, "@@"+str(index)),
            "translations": auxTranslations};


def get_sld_filter_operations():
    return {
        "parentesis":{
            "Parentesis":{
                "description": "Prioriza su contenido",
                "name": "Parentesis",
                "matchPercentage": 90,
                "usage": "(<operacion>)",
                "hidden": True,
                "regex": ["[^a-zA-Z0-9]+\\(([^()]+)\\)"],
                "genCodeFunc": parentesis_operation
            }
        },
        "Logical":{
             "Literal":{
                "description": "Valores constantes cadenas",
                "name": "Literal",
                "matchPercentage": 85,
                "hidden": True,
                "usage": "<valor>",
                "regex": ['[^"]*"([^"]+)'],
                "genCodeFunc": basic_literal_operations
            },
            "And":{
                "description": "Crea una operacion AND entre dos operadores",
                "name": "AND",
                "matchPercentage": 100,
                "usage": "<value_1> AND <value_2>",
                "regex": ["(.+) AND (.+)"],
                "genCodeFunc": logical_and_operation
            },
            "Or":{
                "description": "Crea una operacion OR entre dos operadores",
                "name": "OR",
                "matchPercentage": 100,
                "usage": "<value_1> OR <value_2>",
                "regex": ["(.+) OR (.+)"],
                "genCodeFunc": logical_or_operation
            },
            "Not":{
                "description": "Cambia un True en False y viceversa",
                "name": "NOT",
                "matchPercentage": 100,
                "usage": "NOT <value>",
                "regex": ["NOT (.+)"],
                "genCodeFunc": logical_not_operation
            }
        },
        "Comparative":{
            "PropertyIsGreaterThan":{
                "description": "Compara dos valores y devuelve True si el primero es mayor que el segundo",
                "name": "Mayor que...",
                "matchPercentage": 95,
                "usage": "<Campo> > <valor>",
                "regex": ["(.+)>(.+)"],
                "genCodeFunc": comparative_greaterthan_operation
            },
            "PropertyIsGreaterThanOrEqualTo":{
                "description": "Compara dos valores y devuelve True si el primero es mayor o igual que el segundo",
                "name": "Mayor o igual que...",
                "matchPercentage": 95,
                "usage": "<Campo> >= <valor>",
                "regex": ["(.+)>=(.+)"],
                "genCodeFunc": comparative_greaterthanorequal_operation
            },
            "PropertyIsLessThan":{
                "description": "Compara dos valores y devuelve True si el primero es menor que el segundo",
                "name": "Menor que...",
                "matchPercentage": 95,
                "usage": "<Campo> < <valor>",
                "regex": ["(.+)<(.+)"],
                "genCodeFunc": comparative_lessthan_operation
            },
            "PropertyIsLessThanOrEqualTo":{
                "description": "Compara dos valores y devuelve True si el primero es menor o igual que el segundo",
                "name": "Menor o igual que...",
                "matchPercentage": 95,
                "usage": "<Campo> <= <valor>",
                "regex": ["(.+)<=(.+)"],
                "genCodeFunc": comparative_lessthanorequal_operation
            },
            "PropertyIsEqualTo":{
                "description": "Compara dos valores y devuelve True si el primero y el segundo son iguales",
                "name": "Es igual que...",
                "matchPercentage": 95,
                "usage": "<Campo> == <valor>",
                "regex": ["(.+)==(.+)"],
                "genCodeFunc": comparative_equal_operation
            },
            "PropertyIsNotEqualTo":{
                "description": "Compara dos valores y devuelve True si el primero es distinto al segundo",
                "name": "Es distinto que...",
                "matchPercentage": 100,
                "usage": "<Campo> != <valor>",
                "regex": ["(.+)!=(.+)"],
                "genCodeFunc": comparative_notequal_operation
            },
            "PropertyIsNull":{
                "description": "Devuelve True si la propiedad no tiene valor",
                "name": "Tieen valor nulo",
                "matchPercentage": 100,
                "usage": "<Campo> == null",
                "regex": ["(.+) == null", "(.+) ==null"],
                "genCodeFunc": comparative_null_operation
            },
            "PropertyIsBetween":{
                "description": "Comprueba si el valor se encuentra entre dos valores",
                "name": "Valores entre...",
                "matchPercentage": 100,
                "usage": "<valor_1> <= <Campo> <= <valor_2>",
                "regex": ["(.+)<=(.+)<=(.+)", "(.+)<(.+)<=(.+)", "(.+)<(.+)<=(.+)", "(.+)<(.+)<(.+)"],
                "genCodeFunc": comparative_between_operation
            }
        },
        "Arithmetics":{
            "Add":{
                "description": "Suma dos valores",
                "name": "Suma",
                "matchPercentage": 80,
                "usage": "<valor_1> + <valor_2>",
                "regex": ["(.+)\+(.+)"],
                "genCodeFunc": arithmetic_add_operation
            },
            "Sub":{
                "description": "Resta dos valores",
                "name": "Resta",
                "matchPercentage": 80,
                "usage": "<valor_1> - <valor_2>",
                "regex": ["(.+)\-(.+)"],
                "genCodeFunc": arithmetic_sub_operation
            },
            "Mul":{
                "description": "Multiplica dos valores",
                "name": "Multiplicacion",
                "matchPercentage": 80,
                "usage": "<valor_1> * <valor_2>",
                "regex": ["(.+)\*(.+)"],
                "genCodeFunc": arithmetic_mult_operation
            },
            "Div":{
                "description": "Divide dos valores",
                "name": "Division",
                "matchPercentage": 80,
                "usage": "<valor_1> / <valor_2>",
                "regex": ["(.+)\/(.+)"],
                "genCodeFunc": arithmetic_div_operation
            }
        },
        "Functions":{
            "Area":{
                "description": "Obtiene el area de una geometria",
                "name": "Area",
                "matchPercentage": 100,
                "usage": "area(<campo_geometria>)",
                "regex": ["area\\(([^)]*)\\)"],
                "genCodeFunc": function_area_operation
            },
            "Centroid":{
                "description": "Obtiene el centroide de una geometria",
                "name": "Centroid",
                "matchPercentage": 100,
                "usage": "centroid(<campo_geometria>)",
                "regex": ["centroid\\(([^)]*)\\)"],
                "genCodeFunc": function_centroid_operation
            },
            "ConvexHull":{
                "description": "Obtiene el area de recubrimiento mínima de una geometria",
                "name": "ConvexHull",
                "matchPercentage": 100,
                "usage": "convexhull(<campo_geometria>)",
                "regex": ["convexhull\\(([^)]*)\\)"],
                "genCodeFunc": function_convexhull_operation
            }
        },
        "Básicos":{
            "Cadena":{
                "description": "Cadenas, fechas o geometrias (entre comillas)",
                "name": "Cadena",
                "matchPercentage": 99,
                "hidden": True,
                "usage": "\"<valor>\"",
                "regex": ['"([\\W\\wáéíóúÁÉÍÓÚàèìòùÀÈÌÒÙñÑüÜ\-\\.\\s]+)"'],
                "genCodeFunc": basic_literal_operations
            },
            "Literal":{
                "description": "Valores constantes numericos, booleanos, ...",
                "name": "Literal",
                "matchPercentage": 10,
                "hidden": True,
                "usage": "<valor>",
                "regex": ['(@@[0-9]+)', '"([\\W\\wáéíóúÁÉÍÓÚàèìòùÀÈÌÒÙñÑüÜ\-\\.\\s]+)"', '([\\W\\wáéíóúÁÉÍÓÚàèìòùÀÈÌÒÙñÑüÜ\-\.\\s]+)'],
                "genCodeFunc": basic_literal_operations
            }
        }
    }

def is_full_parsed(filter):
    filter = filter.strip()
    if len(filter) == 0:
        return True
    m = re.search(r'(@@[0-9]+)', filter)
    if m:
        if m.regs.__len__ > 1:
            if m.regs[1][0] == 0 and m.regs[1][1] == filter.__len__():
                return True
        
    return False
    
def get_sld_filter(filter, layer_id, session):
    auxTranslations = []
    
    resource = get_layer_field_description(layer_id, session)
    fields = []
    if resource != None:
        fields = resource.get('featureType').get('attributes').get('attribute')
        
    filter = getSLDCodeFilter(filter, auxTranslations, fields)
    
    m = re.search(r'(@@[0-9]+)', filter)
    while m:
        i = 0
        for reg in m.regs:
            if i==0:
                i = i + 1 
                continue
            label = filter[reg[0]:reg[1]]
            index = label.replace("@@", "")
            filter = filter.replace(label, auxTranslations[int(index)])
            
        m = re.search(r'(@@[0-9]+)', filter)
        
    return filter

def getSLDCodeFilter(filter, auxTranslations, fields):
    sldFilterValues = get_sld_filter_operations()
    
    sldParentesisOperation = sldFilterValues["parentesis"]["Parentesis"]
    regex = re.compile(sldParentesisOperation["regex"][0])
    while re.search(regex, filter):
        m = re.search(r''+sldParentesisOperation["regex"][0], filter)
        if m:
            funcion =  sldParentesisOperation["genCodeFunc"]
            result = funcion(m.regs, filter, auxTranslations, fields)
            filter = result["filter"]
            auxTranslations = result["translations"]
    
    while not is_full_parsed(filter):
        bestOperation = None
        bestPercentage = 0
        bestRegex = None
        
        for key in sldFilterValues:
            for i in sldFilterValues[key]:
                sldOperation = sldFilterValues[key][i]
                for j in sldOperation["regex"]:
                    regex = re.compile(j)
                    if re.search(regex, filter) and sldOperation["matchPercentage"] > bestPercentage:
                        bestPercentage = sldOperation["matchPercentage"]
                        bestOperation = sldOperation
                        bestRegex = j
                        break
        
        if bestPercentage > 0 and bestOperation != None and bestRegex != None:
            regex = re.compile(bestRegex)
            match = re.search(regex, filter)
            funcion = bestOperation["genCodeFunc"]
            if match:
                result = funcion(match.regs, filter, auxTranslations, fields)
                if isinstance(result, str) or isinstance(result, unicode):
                    return result
                filter = result["filter"]
                auxTranslations = result["translations"]
        #else:
            #return error
    
    return filter

def get_graphics_sld(filter):
    regex = re.compile(r'<ExternalGraphic>(.*)</ExternalGraphic>')
    match = re.search(regex, filter)
    if match:
        if match.regs.__len__() < 2:
            return filter;
        geom_op = filter[match.regs[1][0]:match.regs[1][1]]
        if len(geom_op) != 0:
                if geom_op.startswith("http://chart"):
                    type = ""
                    href = "xlink:href=\"" + geom_op +"\""
                    format = "application/chart"
                else:
                    type = "xlink:type=\"simple\" "
                    href = "xlink:href=\"file:"+"/"+"/" + gvsigol.settings.MEDIA_ROOT + geom_op +"\""
                    format = "image/png"
                
                new_filter = "<OnlineResource "+type+""+ href +" />"
                new_filter = new_filter + "<Format>"+format+"</Format>"
                filter = regex.sub("<ExternalGraphic>"+ new_filter+"</ExternalGraphic>", filter)
                regex2 = re.compile(r'<Mark>(.*)</Mark>')
                filter = regex2.sub("", filter)
            
        else:
            filter = regex.sub("", filter)
    
    return filter


def get_geometry_sld(layer_id, filter, session):
    regex = re.compile(r'<Geometry>(.+)</Geometry>')
    match = re.search(regex, filter)
    if match:
        if match.regs.__len__() < 2:
            return filter;
        geom_op = filter[match.regs[1][0]:match.regs[1][1]]
        new_filter = get_sld_filter(geom_op, layer_id, session)
        filter = regex.sub("<Geometry>"+new_filter+"</Geometry>", filter)
    else:
        filter = filter.replace("<Geometry></Geometry>", "")
    
    return filter

def get_sld_style(layer_id, style_id, session):
    sld = "<StyledLayerDescriptor version=\"1.0.0\" xmlns=\"http://www.opengis.net/sld\" xmlns:ogc=\"http://www.opengis.net/ogc\" "
    sld += "xmlns:sld=\"http://www.opengis.net/sld\"  xmlns:gml=\"http://www.opengis.net/gml\" " 
    sld +=   "xmlns:xlink=\"http://www.w3.org/1999/xlink\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" "
    sld +=   "xsi:schemaLocation=\"http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd\">"
    #sld = "<sld:StyledLayerDescriptor xmlns=\"http://www.opengis.net/sld\" xmlns:sld=\"http://www.opengis.net/sld\" xmlns:ogc=\"http://www.opengis.net/ogc\" xmlns:gml=\"http://www.opengis.net/gml\" version=\"1.0.0\">"
    sld += "<NamedLayer>"
    
    layer = Layer.objects.get(id=layer_id)
    style = Style.objects.get(id=style_id)
    datastore = Datastore.objects.get(id=layer.datastore_id)
    ws = Workspace.objects.get(id=datastore.workspace_id)
    if layer.name != None and layer.name != "":
        sld += "<Name>"+ ws.name + ":" + layer.name +"</Name>"
    
    sld += "<UserStyle>"
    if layer.name != None and layer.name != "":
        sld += "<Name>"+ ws.name + ":" + layer.name +"</Name>"
    if style.title != None and style.title != "":
        sld += "<Title>"+ escape(style.title) +"</Title>"
    if style.title != None and style.title != "":
        sld += "<Abstract>"+ escape(style.title) +"</Abstract>"
    sld += "<FeatureTypeStyle>"
    
    style_rules = StyleRule.objects.filter(style_id=style_id)
    for st in style_rules:
        rule = Rule.objects.get(id=st.rule.id)
        sld += "<Rule>"
        if rule.name != None and rule.name != "":
            sld += "<Name>"+ escape(rule.name) +"</Name>"
            sld += "<Title>"+ escape(rule.title) +"</Title>"
        if rule.filter != None and rule.filter != "":
            sld += "<Filter>"+ get_sld_filter(rule.filter, layer_id, session) +"</Filter>"
        if rule.minscale != None and rule.minscale != -1:
            sld += "<MinScaleDenominator>"+ str(rule.minscale) +"</MinScaleDenominator>"
        if rule.maxscale != None and rule.maxscale != -1:
            sld += "<MaxScaleDenominator>"+ str(rule.maxscale) +"</MaxScaleDenominator>"
        
        symbolizers = Symbolizer.objects.filter(rule = rule)
        for symbolizer in symbolizers:
            sld += symbolizer.sld
            '''
            clean_sld = get_clean_sld(symbol.sld_code, rule)
            symbs = get_symbolizers(clean_sld)
            for symb in symbs:
                symbol_sld = get_geometry_sld(layer_id, symb, session)                    
                sld += get_graphics_sld(symbol_sld) 
            '''
        sld += "</Rule>"
    
    sld += "</FeatureTypeStyle>"
    sld += "</UserStyle>"
    sld += "</NamedLayer>"
    sld += "</StyledLayerDescriptor>"
    
    return sld #.encode('utf8')

def get_style_from_library_symbol(style_id, session):
    sld = "<StyledLayerDescriptor version=\"1.0.0\" xmlns=\"http://www.opengis.net/sld\" xmlns:ogc=\"http://www.opengis.net/ogc\" "
    sld += "xmlns:sld=\"http://www.opengis.net/sld\"  xmlns:gml=\"http://www.opengis.net/gml\" " 
    sld +=   "xmlns:xlink=\"http://www.w3.org/1999/xlink\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" "
    sld +=   "xsi:schemaLocation=\"http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd\">"
    #sld = "<sld:StyledLayerDescriptor xmlns=\"http://www.opengis.net/sld\" xmlns:sld=\"http://www.opengis.net/sld\" xmlns:ogc=\"http://www.opengis.net/ogc\" xmlns:gml=\"http://www.opengis.net/gml\" version=\"1.0.0\">"
    sld += "<NamedLayer>"
    
    style = Style.objects.get(id=style_id)
    if style.name != None and style.name != "":
        sld += "<Name>"+ style.name +"</Name>"
    
    sld += "<UserStyle>"
    if style.name != None and style.name != "":
        sld += "<Name>"+ style.name +"</Name>"
    if style.title != None and style.title != "":
        sld += "<Title>"+ escape(style.title) +"</Title>"
    if style.title != None and style.title != "":
        sld += "<Abstract>"+ escape(style.title) +"</Abstract>"
    sld += "<FeatureTypeStyle>"
    
    style_rules = StyleRule.objects.filter(style_id=style_id)
    for st in style_rules:
        rule = Rule.objects.get(id=st.rule.id)
        sld += "<Rule>"
        if rule.name != None and rule.name != "":
            sld += "<Name>"+ escape(rule.name) +"</Name>"
            sld += "<Title>"+ escape(rule.title) +"</Title>"
        
        symbolizers = Symbolizer.objects.filter(rule = rule)
        for symbolizer in symbolizers:
            sld += symbolizer.sld

        sld += "</Rule>"
    
    sld += "</FeatureTypeStyle>"
    sld += "</UserStyle>"
    sld += "</NamedLayer>"
    sld += "</StyledLayerDescriptor>"
    
    return sld #.encode('utf8')

def get_sld_body(json_data):
    sld = "<StyledLayerDescriptor version=\"1.0.0\" xmlns=\"http://www.opengis.net/sld\" xmlns:ogc=\"http://www.opengis.net/ogc\" "
    sld += "xmlns:sld=\"http://www.opengis.net/sld\"  xmlns:gml=\"http://www.opengis.net/gml\" " 
    sld +=   "xmlns:xlink=\"http://www.w3.org/1999/xlink\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" "
    sld +=   "xsi:schemaLocation=\"http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd\">"
    sld += "<NamedLayer>"  
    sld +=      "<Name>"+ json_data.get('name') +"</Name>"  
    sld +=      "<UserStyle>"
    sld +=          "<Name>"+ json_data.get('name') +"</Name>" 
    sld +=          "<Title>"+ json_data.get('title') +"</Title>" 
    sld +=          "<Abstract>"+ json_data.get('title') +"</Abstract>" 
    sld +=          "<FeatureTypeStyle>"
    for rule in json_data.get('rules'):
        sld += "<Rule>"
        sld +=      "<Name>"+ rule.get('name') +"</Name>"
        sld +=      "<Title>"+ rule.get('title') +"</Title>"
        
        for symbolizer in rule.get('rule_symbolizers'):
            sld += symbolizer.get('sld')

        sld += "</Rule>"
    
    sld += "</FeatureTypeStyle>"
    sld += "</UserStyle>"
    sld += "</NamedLayer>"
    sld += "</StyledLayerDescriptor>"
    
    return sld #.encode('utf8')



def get_clean_sld(sld_code, symbol):
    sld = sld_code
    
    sld = sld.replace("<VendorOption/>", "")
    sld = sld.replace("<VendorOption></VendorOption>", "")
    sld = sld.replace("<CssParameter/>", "")
    
    e = re.compile('<CssParameter *[^>]*>.*</CssParameter>')
    cssparameters = e.findall(sld)
    for cssparameter in cssparameters:
        names = re.findall( 'name="(.*?)"', cssparameter)
        for name in names:
            regexp = re.compile(r'>'+name+'</CssParameter>')
            if regexp.search(cssparameter) is not None:
                sld = sld.replace('<CssParameter name="'+name+'">'+name+'</CssParameter>', '')
    sld = sld.replace("<Stroke></Stroke>", "")
    
    if symbol:
        symbol.sld_code = sld
        symbol.save()
    
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
    

@ajax
def get_sld_style2(request, layer_id, style_id):
    if request.method == 'POST': 
        data = request.POST.get('data')
        
        if data:
            datos = json.loads(data)
            sld = "<StyledLayerDescriptor version=\"1.0.0\" xmlns=\"http://www.opengis.net/sld\" xmlns:ogc=\"http://www.opengis.net/ogc\" "
            sld += "xmlns:sld=\"http://www.opengis.net/sld\"  xmlns:gml=\"http://www.opengis.net/gml\" " 
            sld +=   "xmlns:xlink=\"http://www.w3.org/1999/xlink\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" "
            sld +=   "xsi:schemaLocation=\"http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd\">"
            #sld = "<sld:StyledLayerDescriptor xmlns=\"http://www.opengis.net/sld\" xmlns:sld=\"http://www.opengis.net/sld\" xmlns:ogc=\"http://www.opengis.net/ogc\" xmlns:gml=\"http://www.opengis.net/gml\" version=\"1.0.0\">"
            sld += "<NamedLayer>"
            
            layer = Layer.objects.get(id=layer_id)
            style = Style.objects.get(id=style_id)
            datastore = Datastore.objects.get(id=layer.datastore_id)
            ws = Workspace.objects.get(id=datastore.workspace_id)
            if layer.name != None and layer.name != "":
                sld += "<Name>"+ ws.name + ":" + layer.name +"</Name>"
            
            sld += "<UserStyle>"
            if layer.name != None and layer.name != "":
                sld += "<Name>"+ ws.name + ":" + layer.name +"</Name>"
            if style.title != None and style.title != "":
                sld += "<Title>"+ escape(style.title) +"</Title>"
            if style.description != None and style.description != "":
                sld += "<Abstract>"+ escape(style.description) +"</Abstract>"
            sld += "<FeatureTypeStyle>"
            
            for aux in datos:
                rule = aux["rule"][0]
                sld += "<Rule>"
                if rule["fields"].get('name') and rule["fields"]["name"] != "":
                    sld += "<Name>"+ escape(str(rule["fields"]["name"])) +"</Name>"
                if rule["fields"].get('filter') and rule["fields"]["filter"] != "":
                    sld += "<Filter>"+ get_sld_filter(rule["fields"]["filter"], layer_id, request.session) +"</Filter>"
                if rule["fields"].get('minscale') and rule["fields"]["minscale"] != "":
                    sld += "<MinScaleDenominator>"+ str(rule["fields"]["minscale"]) +"</MinScaleDenominator>"
                if rule["fields"].get('maxscale') and rule["fields"]["maxscale"] != "":
                    sld += "<MaxScaleDenominator>"+ str(rule["fields"]["maxscale"]) +"</MaxScaleDenominator>"
                
                symbols = aux["symbols"]
                for symbol in symbols:
                    clean_sld = get_clean_sld(symbol["fields"]["sld_code"], None)
                    symbs = get_symbolizers(clean_sld)
                    for symb in symbs:
                        symbol_sld = get_geometry_sld(layer_id, symb, request.session)                    
                        sld += get_graphics_sld(symbol_sld)
                
                sld += "</Rule>"
            
            sld += "</FeatureTypeStyle>"
            sld += "</UserStyle>"
            sld += "</NamedLayer>"
            sld += "</StyledLayerDescriptor>"
            
            return {"sld_code": sld.encode('utf8')}