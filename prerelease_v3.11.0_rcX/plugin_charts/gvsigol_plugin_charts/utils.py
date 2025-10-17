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

from gvsigol_services.backend_postgis import Introspect
import json

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

def get_geometry_fields(fields):
    geom_fields = []
    for field in fields:
        if (field.get('binding').startswith('org.locationtech.jts.geom')):
            geom_fields.append(field)
            
    return geom_fields