# -*- coding: utf-8 -*-
'''
    gvSIG Online.
    Copyright (C) 2020 SCOLAB.

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
from gvsigol.settings import BASE_URL, GVSIGOL_PATH
from psycopg2 import sql as sqlbuilder

'''
@author: Cesar Martinez <cmartinez@scolab.es>
'''

class CustomFunctionDef():
    def get_definition(self):
        pass

INVERSE_GEOCODER_CARTOCIUDAD_FUNCTION_SCHEMA = "public"
INVERSE_GEOCODER_CARTOCIUDAD_FUNCTION_NAME = "gol_geocoder_inverso_cartociudad"
INVERSE_GEOCODER_CARTOCIUDAD_FUNCTION_SIGNATURE = "public.gol_geocoder_inverso_cartociudad(text)"

INVERSE_GEOCODER_CARTOCIUDAD_DEF_GVSIGOL = """CREATE OR REPLACE FUNCTION public.gol_geocoder_inverso_cartociudad() RETURNS trigger AS $$
        # TODO: comprobar que no es tipo punto
        import requests
        timeout = 10
        geocoder_url = '{base_url}/{gvsigol_path}/geocoding/get_location_address/'
        try:
            column_name = TD["args"][0]
            plan = plpy.prepare("SELECT * FROM geometry_columns WHERE f_table_name = $1 AND f_table_schema = $2", ["text","text"])        
            rv = plpy.execute(plan,[TD["table_name"],TD["table_schema"]],1)
            geom_column = rv[0]["f_geometry_column"]
            
            plan = plpy.prepare("SELECT st_x(ST_GeometryN(ST_Transform($1,4326), 1)) || ',' ||st_y(ST_GeometryN(ST_Transform($1,4326), 1)) as coords", ["text"])
            rv = plpy.execute(plan,[TD["new"][geom_column]],1)
            coords= rv[0]["coords"]
            
            client = requests.session()
            _data = {{'coord': coords, 'type':'new_cartociudad'}}
            #plpy.log(str(_data))
            r = client.post(geocoder_url, data=_data, verify=False, timeout=timeout)
            response = r.json() 
            address = response.get('tip_via', '') + " " + response.get('address', '') + "," + str(response.get('portalNumber', ''))
            TD["new"][column_name] = address 
        except plpy.SPIError as e:
            TD["new"][column_name] = ''
            plpy.log("ERROR geocoder_inverso_cartociudad: " + str(e))
        except Exception as e:
            TD["new"][column_name] = ''
            plpy.log(str(e))
        finally:
            return "MODIFY"
    $$ LANGUAGE plpython2u;
    """
    
INVERSE_GEOCODER_CARTOCIUDAD_DEF = """CREATE OR REPLACE FUNCTION public.gol_geocoder_inverso_cartociudad() RETURNS trigger AS $$
        # TODO: comprobar que no es tipo punto
        import requests
        timeout = 10
        geocoder_url = 'http://www.cartociudad.es/geocoder/api/geocoder/reverseGeocode'
        try:
            column_name = TD["args"][0]
            plan = plpy.prepare("SELECT * FROM geometry_columns WHERE f_table_name = $1 AND f_table_schema = $2", ["text","text"])        
            rv = plpy.execute(plan,[TD["table_name"],TD["table_schema"]],1)
            geom_column = rv[0]["f_geometry_column"]
            
            plan = plpy.prepare("SELECT st_x(ST_GeometryN(ST_Transform($1,4326), 1)) as lon, st_y(ST_GeometryN(ST_Transform($1,4326), 1)) as lat", ["text"])
            rv = plpy.execute(plan,[TD["new"][geom_column]],1)
            lon = rv[0]["lon"]
            lat = rv[0]["lat"]
            
            _data = {'lon': lon, 'lat': lat}
            #plpy.log(str(_data))
            r = requests.get(geocoder_url, params=_data, timeout=timeout)
            response = r.json()
            #plpy.log(str(r.text)) 
            address = response.get('tip_via', '') + " " + response.get('address', '') + "," + str(response.get('portalNumber', ''))
            TD["new"][column_name] = address 
        except plpy.SPIError as e:
            TD["new"][column_name] = ''
            plpy.log("ERROR geocoder_inverso_cartociudad: " + str(e))
        except Exception as e:
            TD["new"][column_name] = ''
            plpy.log(str(e))
        finally:
            return "MODIFY"
    $$ LANGUAGE plpython2u;
    """
    

class InverseGeocoderCartociudad(CustomFunctionDef):
     def get_definition(self):
         return INVERSE_GEOCODER_CARTOCIUDAD_DEF


CUSTOM_PROCEDURES = {
    # Use the function signature to register CustomFunctionDef
    INVERSE_GEOCODER_CARTOCIUDAD_FUNCTION_SIGNATURE: InverseGeocoderCartociudad
    }

def install_procedure(procedure, cursor=None):
    """
    Installs the procedure on the database referenced by the cursor.
    If cursor is not provided, the procedure is installed in the database
    of all the available datastores
    """
    from gvsigol_services.models import TriggerProcedure, Datastore
    from gvsigol_services.utils import get_db_connect_from_datastore

    if not isinstance(procedure, TriggerProcedure):
        if isinstance(procedure, basestring):
            procedure = TriggerProcedure.objects.get(signature = procedure)
        else:
            procedure = TriggerProcedure.objects.get(id=int(procedure))
    definition = procedure.get_definition()
    if cursor:
        cursor.execute(definition)
    else:
        for store in Datastore.objects.filter(type='v_PostGIS'):
            (introspection, _) = get_db_connect_from_datastore(store)
            introspection.cursor.execute(definition)
            introspection.close()

def install_procedures():
    from gvsigol_services.models import TriggerProcedure, Datastore
    from gvsigol_services.utils import get_db_connect_from_datastore
    for store in Datastore.objects.filter(type='v_PostGIS'):
        introspection, _ = get_db_connect_from_datastore(store)
        for procedure in TriggerProcedure.objects.all():
            install_procedure(procedure, introspection.cursor)
        introspection.close()

def drop_procedure(procedure, cursor=None):
    """
    Installs the procedure on the database referenced by the cursor.
    If cursor is not provided, the procedure is installed in the database
    of all the available datastores
    """
    from gvsigol_services.models import TriggerProcedure, Datastore
    from gvsigol_services.utils import get_db_connect_from_datastore

    if not isinstance(procedure, TriggerProcedure):
        if isinstance(procedure, basestring):
            procedure = TriggerProcedure.objects.get(signature = procedure)
        else:
            procedure = TriggerProcedure.objects.get(id=int(procedure))

    sql = sqlbuilder.SQL("DROP FUNCTION IF EXISTS {function}").format(
        function=sqlbuilder.SQL(procedure.signature))
    if cursor:
        cursor.execute(sql)
    else:
        for store in Datastore.objects.filter(type='v_PostGIS'):
            introspection, _ = get_db_connect_from_datastore(store)
            introspection.cursor.execute(sql)
            introspection.close()
