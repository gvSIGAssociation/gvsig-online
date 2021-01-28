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
from geoserver.workspace import Workspace
from models import Provider
from gvsigol_services.models import Datastore
# from gvsigol import settings
from gvsigol_plugin_geocoding import settings as geocoding_settings

import psycopg2

import json
import xml.etree.cElementTree as ET
import xml.etree.ElementTree as ET2
import sys
import codecs
import os
import urllib2
import settings
import zipfile
import datetime
import tempfile
from subprocess import call
from dbfpy import dbf
import shutil
import logging
from __builtin__ import False

'''
@author: José Badía <jbadia@scolab.es>
'''

'''
http://localhost:8983/solr/cartociudad/dataimport2?_=1487864250477&command=status&indent=on&wt=json
'''
def status_solr_import(provider):
    url = geocoding_settings.URL_SOLR+'/'+geocoding_settings.SOLR_CORE_NAME+"/dataimport-"+str(provider.pk)+"?command=status&indent=on&wt=json"
    #url = geocoding_settings.URL_SOLR+'/'+geocoding_settings.SOLR_CORE_NAME+"/dataimport2?command=status&indent=on&wt=json"
    req = urllib2.urlopen(url)
    if req.code != 200:
        return None
    data = json.load(req)   
    return data


'''
http://localhost:8983/solr/admin/cores?action=RELOAD&core=<core_name>
'''
def reload_solr_config():
    url = geocoding_settings.URL_SOLR+"/admin/cores?action=RELOAD&core="+geocoding_settings.SOLR_CORE_NAME
    req = urllib2.urlopen(url)
    if req.code != 200:
        return False
    return True


'''
http://localhost:8983/solr/<core_name>/update?stream.body=<delete><query>table_name:<dataStoreID></query></delete>&commit=true
'''  
def remove_solr_data(provider):
    #resource = provider.type+"-"+str(provider.pk)
    resource = str(provider.pk)
    url = geocoding_settings.URL_SOLR+'/'+geocoding_settings.SOLR_CORE_NAME+"/update?stream.body=<delete><query>resource:*"+resource+"</query></delete>&commit=true"
    req = urllib2.urlopen(url)
    if req.code != 200:
        return False
    return True


'''
http://localhost:8983/solr/<core_name>/dataimport-<dataStoreID>?command=full-import
''' 
def full_import_solr_data(provider):
    url = geocoding_settings.URL_SOLR+'/'+geocoding_settings.SOLR_CORE_NAME+"/dataimport-"+str(provider.pk)+"?command=full-import&clean=false"
    req = urllib2.urlopen(url)
    if req.code != 200:
        return False
    return True


def delta_import_solr_data(provider):
    url = geocoding_settings.URL_SOLR+'/'+geocoding_settings.SOLR_CORE_NAME+"/dataimport-"+str(provider.pk)+"?command=delta-import"
    req = urllib2.urlopen(url)
    if req.code != 200:
        return False
    return True

'''
    <dataConfig>
            <dataSource name="DS1" type="JdbcDataSource" driver="org.postgresql.Driver" url="jdbc:postgresql://localhost:5432/<base_datos>" user="<usuario>" password="<contraseña>"/>
            <document>
            <entity dataSource="DS1" name="candidate" query="select *, <dataStoreID> as table_name, now() as last_modification from <tabla>"
            deltaImportQuery="select *, 'colegio-19-'||id as calculated_id, 'colegio-19' as table_name, now() as last_modification from public.colegio where id='${dataimporter.delta.id}'"
            deltaQuery="select id, 'colegio-19-'||id as calculated_id, 'colegio-19' as table_name, now() as last_modification from public.colegio WHERE last_modified > '${dataimporter.last_index_time}'" ">
                       <field column="id" name="id"/> 
                       <field column="id" name="obj_id"/> 
                        <field column="name" name="text" />
                        ...
                        <field column="last_modification" name="last_modification" />
            </entity>
            </document>
        </dataConfig>
        
'''
def create_XML_config(provider, has_soundex):
    params = json.loads(provider.params)
    datastore_id = params["datastore_id"]
    datastore = Datastore.objects.get(id=datastore_id)
    fname = geocoding_settings.DIR_SOLR_CONFIG + str(provider.pk)+"-"+geocoding_settings.FILE_DATE_CONFIG
    
    if os.path.isfile(fname):
        return False
     
    try:
        datastore_params = json.loads(datastore.connection_params)
        root = ET.Element("dataConfig")
        
        ET.SubElement(
            root, 
            "dataSource", 
            name="DS2", 
            type="JdbcDataSource", 
            driver="org.postgresql.Driver", 
            url="jdbc:postgresql://"+datastore_params["host"]+":"+datastore_params["port"]+"/"+datastore_params["database"], 
            user=datastore_params["user"], 
            password=datastore_params["passwd"])
        
        resource = provider.type+'-'+str(provider.pk)
        
        query_str="select "
        if has_soundex:
            query_str = query_str + "soundexesp2("+params["text_field"]+") as soundexesp, "
        query_str= query_str + params["id_field"]+" as obj_id, "+params["text_field"]+" as text, '" + resource + "-'||" + params["id_field"]+" as calculated_id, '" + resource + "' as resource, now() as last_modification, '" + params["resource"] +"' as table_name, '" + provider.category +"' as category, ST_X(ST_Transform(ST_Centroid("+params["geom_field"]+"), 4258)) as longitud, ST_Y(ST_Transform(ST_Centroid("+params["geom_field"]+"), 4258)) as latitud, 'user' as source  from " + datastore_params["schema"] + "." + params["resource"]
        delta_import_str= query_str + " where " + params["id_field"]+"='${dataimporter.delta.id}'"
        delta_str= query_str + " where "+ geocoding_settings.LAST_MODIFIED_FIELD_NAME +" > '${dataimporter.last_index_time}'"
        
        document = ET.SubElement(root, "document")
        entity = ET.SubElement(
                document, 
                "entity", 
                dataSource="DS2",
                name="candidate",
                query=query_str,
                deltaImportQuery=delta_import_str,
                deltaQuery=delta_str
                )
        
        ET.SubElement(entity, "field", column="calculated_id", name="id")
        ET.SubElement(entity, "field", column="obj_id", name="obj_id")
        ET.SubElement(entity, "field", column="text", name="text")
        if has_soundex:
            ET.SubElement(entity, "field", column="soundexesp", name="soundexesp")
        ET.SubElement(entity, "field", column="table_name", name="table_name")
        ET.SubElement(entity, "field", column="resource", name="tipo")
        ET.SubElement(entity, "field", column="last_modification", name="last_modification")
        ET.SubElement(entity, "field", column="longitud", name="longitud")     
        ET.SubElement(entity, "field", column="latitud", name="latitud")  
        ET.SubElement(entity, "field", column="source", name="source")   
        ET.SubElement(entity, "field", column="resource", name="resource")  
        ET.SubElement(entity, "field", column="category", name="category")    
        
        tree = ET.ElementTree(root)
        tree.write(fname)
    except Exception as e:
        logging.error('ERROR: writing Solr configuration ->' + str(e))

        return False

    return True

def configure_datastore(provider):
    params = json.loads(provider.params)
    datastore_id = params["datastore_id"]
    datastore = Datastore.objects.get(id=datastore_id)    
    datastore_params = json.loads(datastore.connection_params)

    
    command = "psql -h " + datastore_params['host'] + " -p " + datastore_params['port'] + " -U " + datastore_params['user'] +" -w -d "+ datastore_params['database']
    command4c = " -f " + os.path.join(os.path.dirname(geocoding_settings.BASE_DIR), "plugin_geocoding", "gvsigol_plugin_geocoding", "static", "sql", geocoding_settings.SQL_SOUNDEXESP_FILE_NAME)
    output = call(command + command4c, shell=True)
    
    if output == 0:
        return True
    
    return False
    
    
    

def create_cartociudad_config(provider, has_soundex):
    params = json.loads(provider.params)
    datastore_id = params["datastore_id"]
    datastore = Datastore.objects.get(id=datastore_id)
    fname = geocoding_settings.DIR_SOLR_CONFIG + str(provider.pk)+"-"+geocoding_settings.FILE_DATE_CONFIG
    
    if os.path.isfile(fname):
        return False
     
    try:
        datastore_params = json.loads(datastore.connection_params)
        
        root = ET.Element("dataConfig")
        ET.SubElement(
            root, 
            "dataSource", 
            name="DS2", 
            type="JdbcDataSource", 
            driver="org.postgresql.Driver", 
            url="jdbc:postgresql://"+datastore_params["host"]+":"+datastore_params["port"]+"/"+datastore_params["database"], 
            user=datastore_params["user"], 
            password=datastore_params["passwd"])
        
        
        
        query_str= "SELECT "
        query_str= query_str + "tv.id_vial as obj_id, "
        query_str= query_str + "tv.nom_via as text, "
        query_str= query_str + "'callejero' as table_name, "
        query_str= query_str + "tv.tipo_via as tipo_via_id, " 
        query_str= query_str + "tv.tip_via_in as tipo_via, "
        query_str= query_str + "mv.ine_mun as ine_mun, " 
        query_str= query_str + "m.nameunit as nom_muni, " 
        query_str= query_str + "substring(p.natcode from 5 for 2) as ine_prov, " 
        query_str= query_str + "p.nameunit as nom_prov, "
        if has_soundex:
            query_str= query_str + "soundexesp2(tv.nom_via) as soundexesp, " 
            query_str= query_str + "soundexesp2(m.nameunit) as soundexesp_municipio, "
            query_str= query_str + "soundexesp2(p.nameunit) as soundexesp_provincia, "
        query_str= query_str + "'cartociudad' as source, "
        query_str= query_str + "'" + provider.category +"' as category, "
        query_str= query_str + "'cartociudad-" + str(provider.pk) +"' as resource, "
        query_str= query_str + "now() as last_modified " 
        #query_str= query_str + "ST_AsEWKT(ST_Force2D(tv.wkb_geometry)) as geom " 
        query_str= query_str + "FROM "
        query_str= query_str + datastore_params["schema"]+".municipio_vial mv, " 
        query_str= query_str + "(SELECT DISTINCT(id_vial, nom_via, tipo_via, tipo_v_des), id_vial, nom_via, tipo_via, tip_via_in FROM "+datastore_params["schema"]+".tramo_vial) tv, "
        query_str= query_str + "(SELECT DISTINCT(id_vial, tipo_porta), id_vial, tipo_porta FROM "+datastore_params["schema"]+".portal_pk) pk,"
        query_str= query_str + datastore_params["schema"]+".municipio m, " 
        query_str= query_str + datastore_params["schema"]+".provincia p "
        query_str= query_str + "WHERE "
        query_str= query_str + "mv.id_vial = pk.id_vial "
        query_str= query_str + "AND mv.id_vial = tv.id_vial "
        query_str= query_str + "AND mv.ine_mun = substring(m.natcode from 7 for 11) "
        query_str= query_str + "AND substring(p.natcode from 0 for 7) = substring(m.natcode from 0 for 7)"
        query_str= query_str + "AND pk.tipo_porta = 1"
        
        document = ET.SubElement(root, "document")
        entity = ET.SubElement(
                document, 
                "entity", 
                dataSource="DS2",
                name="candidate",
                query=query_str
        )
        
        ET.SubElement(entity, "field", column="obj_id", name="id")
        ET.SubElement(entity, "field", column="obj_id", name="obj_id")
        ET.SubElement(entity, "field", column="text", name="text")
        ET.SubElement(entity, "field", column="table_name", name="table_name")
        ET.SubElement(entity, "field", column="resource", name="tipo")
        ET.SubElement(entity, "field", column="last_modification", name="last_modification")
        ET.SubElement(entity, "field", column="source", name="source")   
        ET.SubElement(entity, "field", column="resource", name="resource")   
        
        ET.SubElement(entity, "field", column="tipo_via_id", name="tipo_via_id")
        ET.SubElement(entity, "field", column="tipo_via", name="tipo_via")
        #ET.SubElement(entity, "field", column="id_pob", name="id_pob")
        #ET.SubElement(entity, "field", column="ent_pob", name="ent_pob")
        ET.SubElement(entity, "field", column="ine_mun", name="ine_mun")
        ET.SubElement(entity, "field", column="nom_muni", name="nom_muni")
        ET.SubElement(entity, "field", column="ine_prov", name="ine_prov")
        ET.SubElement(entity, "field", column="nom_prov", name="nom_prov")
        #ET.SubElement(entity, "field", column="cod_postal", name="cod_postal")
        if has_soundex:
            ET.SubElement(entity, "field", column="soundexesp", name="soundexesp")
            #ET.SubElement(entity, "field", column="soundexesp_ent_pob", name="soundexesp_ent_pob")
            ET.SubElement(entity, "field", column="soundexesp_municipio", name="soundexesp_municipio")
            ET.SubElement(entity, "field", column="soundexesp_provincia", name="soundexesp_provincia")
        ET.SubElement(entity, "field", column="category", name="category")  
        #ET.SubElement(entity, "field", column="geom", name="geom")  
        
        
        
        
        
        query_stra= "SELECT "
        query_stra= query_stra + "tv.id_vial as obj_id, "
        query_stra= query_stra + "tv.nom_via as text, "
        query_stra= query_stra + "'carretera' as table_name, "
        query_stra= query_stra + "tv.tipo_via as tipo_via_id, " 
        query_stra= query_stra + "tv.tip_via_in as tipo_via, "
        query_stra= query_stra + "mv.ine_mun as ine_mun, " 
        query_stra= query_stra + "m.nameunit as nom_muni, " 
        query_stra= query_stra + "substring(p.natcode from 5 for 2) as ine_prov, " 
        query_stra= query_stra + "p.nameunit as nom_prov, "
        if has_soundex:
            query_stra= query_stra + "soundexesp2(tv.nom_via) as soundexesp, " 
            query_stra= query_stra + "soundexesp2(m.nameunit) as soundexesp_municipio, "
            query_stra= query_stra + "soundexesp2(p.nameunit) as soundexesp_provincia, "
        query_stra= query_stra + "'cartociudad' as source, "
        query_stra= query_stra + "'" + provider.category +"' as category, "
        query_stra= query_stra + "'cartociudad-" + str(provider.pk) +"' as resource, "
        query_stra= query_stra + "now() as last_modified " 
        #query_stra= query_stra + "ST_AsEWKT(ST_Force2D(tv.wkb_geometry)) as geom " 
        query_stra= query_stra + "FROM "
        query_stra= query_stra + datastore_params["schema"]+".municipio_vial mv, " 
        query_stra= query_stra + "(SELECT DISTINCT(id_vial, nom_via, tipo_via, tipo_v_des), id_vial, nom_via, tipo_via, tip_via_in FROM "+datastore_params["schema"]+".tramo_vial) tv, "
        query_stra= query_stra + "(SELECT DISTINCT(id_vial, tipo_porta), id_vial, tipo_porta FROM "+datastore_params["schema"]+".portal_pk) pk,"
        query_stra= query_stra + datastore_params["schema"]+".municipio m, " 
        query_stra= query_stra + datastore_params["schema"]+".provincia p "
        query_stra= query_stra + "WHERE "
        query_stra= query_stra + "mv.id_vial = pk.id_vial "
        query_stra= query_stra + "AND mv.id_vial = tv.id_vial "
        query_stra= query_stra + "AND mv.ine_mun = substring(m.natcode from 7 for 11) "
        query_stra= query_stra + "AND substring(p.natcode from 0 for 7) = substring(m.natcode from 0 for 7)"
        query_stra= query_stra + "AND pk.tipo_porta = 2"
        
        documenta = ET.SubElement(root, "document")
        entitya = ET.SubElement(
                document, 
                "entity", 
                dataSource="DS2",
                name="candidate1a",
                query=query_stra
        )
        
        ET.SubElement(entitya, "field", column="obj_id", name="id")
        ET.SubElement(entitya, "field", column="obj_id", name="obj_id")
        ET.SubElement(entitya, "field", column="text", name="text")
        ET.SubElement(entitya, "field", column="table_name", name="table_name")
        ET.SubElement(entitya, "field", column="resource", name="tipo")
        ET.SubElement(entitya, "field", column="last_modification", name="last_modification")
        ET.SubElement(entitya, "field", column="source", name="source")  
        ET.SubElement(entitya, "field", column="resource", name="resource")    
        
        ET.SubElement(entitya, "field", column="tipo_via_id", name="tipo_via_id")
        ET.SubElement(entitya, "field", column="tipo_via", name="tipo_via")
        #ET.SubElement(entitya, "field", column="id_pob", name="id_pob")
        #ET.SubElement(entitya, "field", column="ent_pob", name="ent_pob")
        ET.SubElement(entitya, "field", column="ine_mun", name="ine_mun")
        ET.SubElement(entitya, "field", column="nom_muni", name="nom_muni")
        ET.SubElement(entitya, "field", column="ine_prov", name="ine_prov")
        ET.SubElement(entitya, "field", column="nom_prov", name="nom_prov")
        #ET.SubElement(entitya, "field", column="cod_postal", name="cod_postal")
        if has_soundex:
            ET.SubElement(entitya, "field", column="soundexesp", name="soundexesp")
            #ET.SubElement(entitya, "field", column="soundexesp_ent_pob", name="soundexesp_ent_pob")
            ET.SubElement(entitya, "field", column="soundexesp_municipio", name="soundexesp_municipio")
            ET.SubElement(entitya, "field", column="soundexesp_provincia", name="soundexesp_provincia")
        ET.SubElement(entitya, "field", column="category", name="category")  
        #ET.SubElement(entitya, "field", column="geom", name="geom")  
        
        
        
        
        
        query_strb= "SELECT "
        query_strb= query_strb + "tv.id_vial as obj_id, "
        query_strb= query_strb + "tv.nom_via as text, "
        query_strb= query_strb + "'callejero' as table_name, "
        query_strb= query_strb + "tv.tipo_via as tipo_via_id, " 
        query_strb= query_strb + "tv.tip_via_in as tipo_via, "
        query_strb= query_strb + "mv.ine_mun as ine_mun, " 
        query_strb= query_strb + "m.nameunit as nom_muni, " 
        query_strb= query_strb + "substring(p.natcode from 5 for 2) as ine_prov, " 
        query_strb= query_strb + "p.nameunit as nom_prov, "
        if has_soundex:
            query_strb= query_strb + "soundexesp2(tv.nom_via) as soundexesp, " 
            query_strb= query_strb + "soundexesp2(m.nameunit) as soundexesp_municipio, "
            query_strb= query_strb + "soundexesp2(p.nameunit) as soundexesp_provincia, "
        query_strb= query_strb + "'cartociudad' as source, "
        query_strb= query_strb + "'" + provider.category +"' as category, "
        query_strb= query_strb + "'cartociudad-" + str(provider.pk) +"' as resource, "
        query_strb= query_strb + "now() as last_modified "
        #query_strb= query_strb + "ST_AsEWKT(ST_Force2D(tv.wkb_geometry)) as geom " 
        query_strb= query_strb + "FROM "
        query_strb= query_strb + datastore_params["schema"]+".municipio_vial mv, " 
        query_strb= query_strb + "(SELECT DISTINCT(id_vial, nom_via, tipo_via, tipo_v_des), id_vial, nom_via, tipo_via, tip_via_in FROM "+datastore_params["schema"]+".tramo_vial) tv, "
        query_strb= query_strb + datastore_params["schema"]+".municipio m, " 
        query_strb= query_strb + datastore_params["schema"]+".provincia p "
        query_strb= query_strb + "WHERE "
        query_strb= query_strb + "mv.id_vial = tv.id_vial "
        query_strb= query_strb + "AND mv.ine_mun = substring(m.natcode from 7 for 11) "
        query_strb= query_strb + "AND substring(p.natcode from 0 for 7) = substring(m.natcode from 0 for 7)"
        query_strb= query_strb + "AND tv.id_vial NOT IN (SELECT DISTINCT(id_vial) FROM "+datastore_params["schema"]+".portal_pk)"
        
        documentb = ET.SubElement(root, "document")
        entityb = ET.SubElement(
                document, 
                "entity", 
                dataSource="DS2",
                name="candidate1b",
                query=query_strb
        )
        
        ET.SubElement(entityb, "field", column="obj_id", name="id")
        ET.SubElement(entityb, "field", column="obj_id", name="obj_id")
        ET.SubElement(entityb, "field", column="text", name="text")
        ET.SubElement(entityb, "field", column="table_name", name="table_name")
        ET.SubElement(entityb, "field", column="resource", name="tipo")
        ET.SubElement(entityb, "field", column="last_modification", name="last_modification")
        ET.SubElement(entityb, "field", column="source", name="source") 
        ET.SubElement(entityb, "field", column="resource", name="resource")     
        
        ET.SubElement(entityb, "field", column="tipo_via_id", name="tipo_via_id")
        ET.SubElement(entityb, "field", column="tipo_via", name="tipo_via")
        #ET.SubElement(entityb, "field", column="id_pob", name="id_pob")
        #ET.SubElement(entityb, "field", column="ent_pob", name="ent_pob")
        ET.SubElement(entityb, "field", column="ine_mun", name="ine_mun")
        ET.SubElement(entityb, "field", column="nom_muni", name="nom_muni")
        ET.SubElement(entityb, "field", column="ine_prov", name="ine_prov")
        ET.SubElement(entityb, "field", column="nom_prov", name="nom_prov")
        #ET.SubElement(entityb, "field", column="cod_postal", name="cod_postal")
        if has_soundex:
            ET.SubElement(entityb, "field", column="soundexesp", name="soundexesp")
            #ET.SubElement(entityb, "field", column="soundexesp_ent_pob", name="soundexesp_ent_pob")
            ET.SubElement(entityb, "field", column="soundexesp_municipio", name="soundexesp_municipio")
            ET.SubElement(entityb, "field", column="soundexesp_provincia", name="soundexesp_provincia")
        ET.SubElement(entityb, "field", column="category", name="category")  
        #ET.SubElement(entityb, "field", column="geom", name="geom")  
        
        
        query_str2= "SELECT "
        query_str2= query_str2 + "substring(m.natcode from 7 for 11) as obj_id, "
        query_str2= query_str2 + "m.nameunit as text, "
        query_str2= query_str2 + "'municipio' as table_name, "
        query_str2= query_str2 + "substring(m.natcode from 7 for 11) as ine_mun, " 
        query_str2= query_str2 + "m.nameunit as nom_muni, " 
        query_str2= query_str2 + "substring(p.natcode from 5 for 2) as ine_prov, " 
        query_str2= query_str2 + "p.nameunit as nom_prov, "
        if has_soundex:
            query_str2= query_str2 + "soundexesp2(m.nameunit) as soundexesp, " 
            query_str2= query_str2 + "soundexesp2(m.nameunit) as soundexesp_municipio, "
            query_str2= query_str2 + "soundexesp2(p.nameunit) as soundexesp_provincia, "
        query_str2= query_str2 + "'cartociudad' as source, "
        query_str2= query_str2 + "'" + provider.category +"' as category, "
        query_str2= query_str2 + "'cartociudad-" + str(provider.pk) +"' as resource, "
        query_str2= query_str2 + "now() as last_modified " 
        #query_str2= query_str2 + "ST_AsEWKT(ST_Force2D(m.wkb_geometry)) as geom " 
        query_str2= query_str2 + "FROM "
        query_str2= query_str2 + datastore_params["schema"]+".municipio m, " 
        query_str2= query_str2 + datastore_params["schema"]+".provincia p "
        query_str2= query_str2 + "WHERE "
        query_str2= query_str2 + "substring(p.natcode from 0 for 7) = substring(m.natcode from 0 for 7)"
               
        document2 = ET.SubElement(root, "document")
        entity2 = ET.SubElement(
                document, 
                "entity", 
                dataSource="DS2",
                name="candidate2",
                query=query_str2
        )
        
        ET.SubElement(entity2, "field", column="obj_id", name="id")
        ET.SubElement(entity2, "field", column="obj_id", name="obj_id")
        ET.SubElement(entity2, "field", column="text", name="text")
        ET.SubElement(entity2, "field", column="table_name", name="table_name")
        ET.SubElement(entity2, "field", column="resource", name="tipo")
        ET.SubElement(entity2, "field", column="last_modification", name="last_modification")
        ET.SubElement(entity2, "field", column="source", name="source") 
        ET.SubElement(entity2, "field", column="resource", name="resource")     
        
        ET.SubElement(entity2, "field", column="tipo_via_id", name="tipo_via_id")
        ET.SubElement(entity2, "field", column="tipo_via", name="tipo_via")
        #ET.SubElement(entity2, "field", column="id_pob", name="id_pob")
        #ET.SubElement(entity2, "field", column="ent_pob", name="ent_pob")
        ET.SubElement(entity2, "field", column="ine_mun", name="ine_mun")
        ET.SubElement(entity2, "field", column="nom_muni", name="nom_muni")
        ET.SubElement(entity2, "field", column="ine_prov", name="ine_prov")
        ET.SubElement(entity2, "field", column="nom_prov", name="nom_prov")
        #ET.SubElement(entity2, "field", column="cod_postal", name="cod_postal")
        if has_soundex:
            ET.SubElement(entity2, "field", column="soundexesp", name="soundexesp")
            #ET.SubElement(entity2, "field", column="soundexesp_ent_pob", name="soundexesp_ent_pob")
            ET.SubElement(entity2, "field", column="soundexesp_municipio", name="soundexesp_municipio")
            ET.SubElement(entity2, "field", column="soundexesp_provincia", name="soundexesp_provincia")   
        ET.SubElement(entity2, "field", column="category", name="category")  
        #ET.SubElement(entity2, "field", column="geom", name="geom") 
        
        
        
        '''
        query_str3= "SELECT "
        query_str3= query_str3 + "substring(p.natcode from 5 for 2) as obj_id, "
        query_str3= query_str3 + "p.nameunit as text, "
        query_str3= query_str3 + "'provincia' as table_name, "
        query_str3= query_str3 + "substring(p.natcode from 5 for 2) as ine_prov,  " 
        query_str3= query_str3 + "p.nameunit as nom_prov, "
        query_str3= query_str3 + "soundexesp2(p.nameunit) as soundexesp, " 
        query_str3= query_str3 + "soundexesp2(p.nameunit) as soundexesp_provincia, "
        query_str3= query_str3 + "'cartociudad' as source, "
        query_str3= query_str3 + "'" + provider.category +"' as category, "
        query_str3= query_str3 + "'cartociudad-" + str(provider.pk) +"' as resource, "
        query_str3= query_str3 + "now() as last_modified " 
        query_str3= query_str3 + "FROM "
        query_str3= query_str3 + datastore_params["schema"]+".provincia p "
               
        document3 = ET.SubElement(root, "document")
        entity3 = ET.SubElement(
                document, 
                "entity", 
                dataSource="DS2",
                name="candidate3",
                query=query_str3
        )
        
        ET.SubElement(entity3, "field", column="obj_id", name="id")
        ET.SubElement(entity3, "field", column="obj_id", name="obj_id")
        ET.SubElement(entity3, "field", column="text", name="text")
        ET.SubElement(entity3, "field", column="table_name", name="table_name")
        ET.SubElement(entity3, "field", column="resource", name="tipo")
        ET.SubElement(entity3, "field", column="last_modification", name="last_modification")
        ET.SubElement(entity3, "field", column="source", name="source")  
        ET.SubElement(entity3, "field", column="resource", name="resource")    
        
        ET.SubElement(entity3, "field", column="tipo_via_id", name="tipo_via_id")
        ET.SubElement(entity3, "field", column="tipo_via", name="tipo_via")
        #ET.SubElement(entity3, "field", column="id_pob", name="id_pob")
        #ET.SubElement(entity3, "field", column="ent_pob", name="ent_pob")
        ET.SubElement(entity3, "field", column="ine_mun", name="ine_mun")
        ET.SubElement(entity3, "field", column="nom_muni", name="nom_muni")
        ET.SubElement(entity3, "field", column="ine_prov", name="ine_prov")
        ET.SubElement(entity3, "field", column="nom_prov", name="nom_prov")
        #ET.SubElement(entity3, "field", column="cod_postal", name="cod_postal")
        ET.SubElement(entity3, "field", column="soundexesp", name="soundexesp")
        #ET.SubElement(entity3, "field", column="soundexesp_ent_pob", name="soundexesp_ent_pob")
        ET.SubElement(entity3, "field", column="soundexesp_municipio", name="soundexesp_municipio")
        ET.SubElement(entity3, "field", column="soundexesp_provincia", name="soundexesp_provincia") 
        ET.SubElement(entity3, "field", column="category", name="category")  
        '''
        
        
        '''
        
        query_str4= "SELECT "
        query_str4= query_str4 + "tv.id_topo as obj_id, "
        query_str4= query_str4 + "tv.texto as text, "
        query_str4= query_str4 + "'toponimo' as table_name, "
        query_str4= query_str4 + "tv.tipo_t_des as tipo, " 
        query_str4= query_str4 + "tv.subtipo as subtipo, "
        query_str4= query_str4 + "tv.ine_mun as ine_mun, " 
        query_str4= query_str4 + "m.nameunit as nom_muni, "
        query_str4= query_str4 + "substring(p.natcode from 5 for 2) as ine_prov, "
        query_str4= query_str4 + "p.nameunit as nom_prov, " 
        if has_soundex:
            query_str4= query_str4 + "soundexesp2(tv.texto) as soundexesp, "
            query_str4= query_str4 + "soundexesp2(m.nameunit) as soundexesp_municipio, "
            query_str4= query_str4 + "soundexesp2(p.nameunit) as soundexesp_provincia,  "
        query_str4= query_str4 + "'cartociudad' as source, "
        query_str4= query_str4 + "'" + provider.category +"' as category, "
        query_str4= query_str4 + "'cartociudad-" + str(provider.pk) +"' as resource, "
        query_str4= query_str4 + "now() as last_modified "
        #query_str4= query_str4 + "ST_AsEWKT(ST_Force2D(tv.wkb_geometry)) as geom " 
        query_str4= query_str4 + "FROM "
        query_str4= query_str4 + datastore_params["schema"]+".toponimo tv, "
        query_str4= query_str4 + datastore_params["schema"]+".municipio m, "
        query_str4= query_str4 + datastore_params["schema"]+".provincia p "
        query_str4= query_str4 + "WHERE "
        query_str4= query_str4 + "tv.ine_mun = substring(m.natcode from 7 for 11) AND "
        query_str4= query_str4 + "substring(p.natcode from 0 for 7) = substring(m.natcode from 0 for 7) "
               
        document4 = ET.SubElement(root, "document")
        entity4 = ET.SubElement(
                document, 
                "entity", 
                dataSource="DS2",
                name="candidate4",
                query=query_str4
        )
        
        ET.SubElement(entity4, "field", column="obj_id", name="id")
        ET.SubElement(entity4, "field", column="obj_id", name="obj_id")
        ET.SubElement(entity4, "field", column="text", name="text")
        ET.SubElement(entity4, "field", column="table_name", name="table_name")
        ET.SubElement(entity4, "field", column="resource", name="tipo")
        ET.SubElement(entity4, "field", column="last_modification", name="last_modification")
        ET.SubElement(entity4, "field", column="source", name="source")   
        ET.SubElement(entity4, "field", column="resource", name="resource")    
        
        ET.SubElement(entity4, "field", column="tipo_via_id", name="tipo_via_id")
        ET.SubElement(entity4, "field", column="tipo_via", name="tipo_via")
        #ET.SubElement(entity4, "field", column="id_pob", name="id_pob")
        #ET.SubElement(entity4, "field", column="ent_pob", name="ent_pob")
        ET.SubElement(entity4, "field", column="ine_mun", name="ine_mun")
        ET.SubElement(entity4, "field", column="nom_muni", name="nom_muni")
        ET.SubElement(entity4, "field", column="ine_prov", name="ine_prov")
        ET.SubElement(entity4, "field", column="nom_prov", name="nom_prov")
        #ET.SubElement(entity4, "field", column="cod_postal", name="cod_postal")
        if has_soundex:
            ET.SubElement(entity4, "field", column="soundexesp", name="soundexesp")
            #ET.SubElement(entity4, "field", column="soundexesp_ent_pob", name="soundexesp_ent_pob")
            ET.SubElement(entity4, "field", column="soundexesp_municipio", name="soundexesp_municipio")
            ET.SubElement(entity4, "field", column="soundexesp_provincia", name="soundexesp_provincia") 
        ET.SubElement(entity4, "field", column="tipo", name="tipo")
        ET.SubElement(entity4, "field", column="subtipo", name="subtipo") 
        ET.SubElement(entity4, "field", column="category", name="category")  
        #ET.SubElement(entity4, "field", column="geom", name="geom") 
        '''
        
        
        tree = ET.ElementTree(root)
        tree.write(fname)
    except Exception as e:
        #self.add_error('connection_params', _("Error: Invalid JSON format"))
        return False

    return True

def check_postgres_config_is_ok(provider):
    params = json.loads(provider.params)
    datastore_id = params["datastore_id"]
    datastore = Datastore.objects.get(id=datastore_id)
    datastore_params = json.loads(datastore.connection_params)
    
    dbhost = datastore_params['host']
    dbport = datastore_params['port']
    dbname = datastore_params['database']
    dbuser = datastore_params['user']
    dbpassword = datastore_params['passwd']
    dbschema = datastore.name
    
    provider.dbschema = dbschema
            
    #connection = get_connection(dbhost, dbport, dbname, dbuser, dbpassword)
    try:
        connection = psycopg2.connect("host=" + dbhost +" port=" + dbport +" dbname=" + dbname +" user=" + dbuser +" password="+ dbpassword);
        connection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        print "Connect ... "
    
    except StandardError, e:
        print "Failed to connect!", e
        return False
    cursor = connection.cursor()
    
    try:        
        test_ext_exists = "SELECT * FROM pg_extension WHERE extname ilike 'pg_trgm';"
        test_func_exists = "select 'immutable_unaccent'::regproc;"
        cursor.execute(test_ext_exists)
        if (cursor.rowcount == 0):
            print "NO existe la extensión pg_trgm en la base de datos. Intentamos crearla."
            return False
        
        cursor.execute(test_func_exists)
        if (cursor.rowcount == 0):
            print "NO existe la función immmutable_unaccent en la base de datos. Intentamos crearla."
            return False
    except Exception, e:
        return False
    return True
            
            

def create_postgres_config(provider, has_soundex):
    params = json.loads(provider.params)
    datastore_id = params["datastore_id"]
    datastore = Datastore.objects.get(id=datastore_id)
    try:
        datastore_params = json.loads(datastore.connection_params)
        
        dbhost = datastore_params['host']
        dbport = datastore_params['port']
        dbname = datastore_params['database']
        dbuser = datastore_params['user']
        dbpassword = datastore_params['passwd']
        dbtable = params['resource']
        dbfield = params['text_field']
        dbfieldGeom = params['geom_field']
        dbschema = datastore_params['schema']
        
        provider.dbschema = dbschema
                
        #connection = get_connection(dbhost, dbport, dbname, dbuser, dbpassword)
        try:
            connection = psycopg2.connect("host=" + dbhost +" port=" + dbport +" dbname=" + dbname +" user=" + dbuser +" password="+ dbpassword);
            connection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            print "Connect ... "
        
        except StandardError, e:
            print "Failed to connect!", e
            return False
        cursor = connection.cursor()
        
        try:        
            test_ext_exists = "SELECT * FROM pg_extension WHERE extname ilike 'pg_trgm';"
            test_func_exists = "select 'immutable_unaccent'::regproc;"
            cursor.execute(test_ext_exists)
            if (cursor.rowcount == 0):
                print "NO existe la extensión pg_trgm en la base de datos. Intentamos crearla."
                create_extension = "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
                
                create_function = ("CREATE OR REPLACE FUNCTION immutable_unaccent(text) \n"
                    "RETURNS text AS \n" 
                    "$func$ \n"
                    "SELECT unaccent('unaccent', $1)  -- schema-qualify function and dictionary \n"
                    "$func$  LANGUAGE sql IMMUTABLE;")
           
                cursor.execute(create_extension)
            
            cursor.execute(test_func_exists)
            if (cursor.rowcount == 0):
                print "NO existe la función immmutable_unaccent en la base de datos. Intentamos crearla."
                cursor.execute(create_function)
                
            
            # Trigram index
            index_name = "index_" + dbtable + "_on_" + dbfield + "_trigram" 
            create_index = ("CREATE INDEX IF NOT EXISTS " + 
                index_name + " ON " + dbschema + "." + dbtable + " USING gin (immutable_unaccent(" + 
                dbfield + ") gin_trgm_ops);")       
            cursor.execute(create_index)

            # Spatial index in srs 4326
            index_name = "index_" + dbtable + "_on_" + dbfieldGeom + "_spatial"
            create_spatial_index = ("CREATE INDEX IF NOT EXISTS " + index_name + " ON " +
                 dbschema + "." + dbtable + " USING GIST(st_transform(" + dbfieldGeom + ", 4326));")
            cursor.execute(create_spatial_index)
            #rows = cursor.fetchall()
    
        except StandardError, e:
            print "SQL Error", e
            cursor.close();
            connection.close();
            return False;

        
    except Exception as e:
        #self.add_error('connection_params', _("Error: Invalid JSON format"))
        return False

    provider.connection = connection
    return True



def delete_XML_config(provider):
    file_path = geocoding_settings.DIR_SOLR_CONFIG + str(provider.pk)+"-"+geocoding_settings.FILE_DATE_CONFIG
    if os.path.isfile(file_path):
        os.remove(file_path)
    else:
        return False
    file_path2 = geocoding_settings.DIR_SOLR_CONFIG + "dataimport-"+str(provider.pk)+".properties"
    if os.path.isfile(file_path2):
        os.remove(file_path2)
    
    return True

'''
        <requestHandler name="/dataimport-<dataStoreID>" class="solr.DataImportHandler">
            <lst name="defaults">
                <str name="config"><dataStoreID>-data-config.xml</str>
            </lst>
        </requestHandler>
'''

def add_solr_config(provider):
    params = json.loads(provider.params)
    datastore_id = params["datastore_id"]
    datastore = Datastore.objects.get(id=datastore_id)
    try:
        root = ET.Element("requestHandler", name="/dataimport-"+str(provider.pk))
        root.attrib['class'] = 'solr.DataImportHandler' 
        lst = ET.SubElement( 
            root,
            "lst", 
            name="defaults")
        
        data_config_file = str(provider.pk)+"-"+geocoding_settings.FILE_DATE_CONFIG
        ET.SubElement(
            lst, 
            "str", 
            name="config").text = data_config_file
        
        parser = PCParser()
        doc = ET.parse(geocoding_settings.DIR_SOLR_CONFIG + geocoding_settings.FILE_SOLR_CONFIG, parser=parser)
        xml = doc.getroot()
        add_config_node(xml, root)   
        
        tree = ET.ElementTree(xml)
        solr_file = geocoding_settings.DIR_SOLR_CONFIG + geocoding_settings.FILE_SOLR_CONFIG
        tree.write(solr_file)
    except Exception as e:
        #self.add_error('connection_params', _("Error: Invalid JSON format"))
        return False
    return True

def remove_solr_config(provider):
    try:
        parser = PCParser()
        doc = ET.parse(geocoding_settings.DIR_SOLR_CONFIG + geocoding_settings.FILE_SOLR_CONFIG, parser=parser)
        xml = doc.getroot()
        xml = remove_config_node(xml, "/dataimport-"+str(provider.pk))  
        
        tree = ET.ElementTree(xml)
        solr_file = geocoding_settings.DIR_SOLR_CONFIG + geocoding_settings.FILE_SOLR_CONFIG
        tree.write(solr_file)
    except Exception as e:
        #self.add_error('connection_params', _("Error: Invalid JSON format"))
        return False
    return True

def add_config_node(node, root):
    is_request_handler=False
    for child in node.getchildren():
        add_config_node(child, root)
        if child.tag == "requestHandler":
            is_request_handler=True
            break
    if is_request_handler:
        node.append(root)
        
def remove_config_node(node, text):
    is_request_handler=False
    for child in node.getchildren():
        add_config_node(child, text)
        if child.tag == "requestHandler" and child.attrib['name'] == text:
            node.remove(child)
    return node

def unzip_file(file, provider):
    zip_ref = zipfile.ZipFile(file, 'r')
    
    #now = datetime.datetime.now()
    #current_id = str(now.year) + '{:02d}'.format(now.month) + '{:02d}'.format(now.day) + '{:02d}'.format(now.hour) + '{:02d}'.format(now.minute) + '{:02d}'.format(now.second) + str(now.microsecond)
    current_id = str(provider.pk)
    newpath = os.path.join(tempfile.gettempdir(),'shp2psql',current_id + '_shp2psql')
    newpath_zip = os.path.join(newpath,'zip')
    if not os.path.exists(newpath_zip):
        os.makedirs(newpath_zip)
    zip_ref.extractall(newpath_zip)
    zip_ref.close()


'''
def export_shp_to_postgis(provider):
    current_id = str(provider.pk)
    path = os.path.join(tempfile.gettempdir(),'shp2psql',current_id + '_shp2psql')
    
    newpath_zip = os.path.join(path,'zip')
    command_export_shp_to_postgis(newpath_zip, geocoding_settings.CARTOCIUDAD_SHP_CODIGO_POSTAL, geocoding_settings.CARTOCIUDAD_DB_CODIGO_POSTAL, current_id)
    
    newpath_zip = os.path.join(newpath_zip, 'CARTOCIUDAD_CALLEJERO_VALENCIA')
    command_export_shp_to_postgis(newpath_zip, geocoding_settings.CARTOCIUDAD_SHP_TRAMO_VIAL, geocoding_settings.CARTOCIUDAD_DB_TRAMO_VIAL, current_id)
    command_export_shp_to_postgis(newpath_zip, geocoding_settings.CARTOCIUDAD_SHP_PORTAL_PK, geocoding_settings.CARTOCIUDAD_DB_PORTAL_PK, current_id)
    command_export_shp_to_postgis(newpath_zip, geocoding_settings.CARTOCIUDAD_SHP_TOPONIMO, geocoding_settings.CARTOCIUDAD_DB_TOPONIMO, current_id)
    #command_export_shp_to_postgis(newpath_zip, geocoding_settings.CARTOCIUDAD_SHP_MANZANA, geocoding_settings.CARTOCIUDAD_DB_MANZANA, current_id)
    #command_export_shp_to_postgis(newpath_zip, geocoding_settings.CARTOCIUDAD_SHP_LINEA_AUXILIAR, geocoding_settings.CARTOCIUDAD_DB_LINEA_AUXILIAR, current_id)
 
 
def export_shp_municipios_to_postgis(provider):
    current_id = str(provider.pk)
    path = os.path.join(tempfile.gettempdir(),'shp2psql',current_id + '_shp2psql')
    
    newpath_zip = os.path.join(path,'zip')
  
    
    newpath_zip2 = os.path.join(newpath_zip, 'recintos_municipales_inspire_peninbal_etrs89')
    command_export_shp_to_postgis(newpath_zip2, geocoding_settings.CARTOCIUDAD_SHP_MUNICIPIO, geocoding_settings.CARTOCIUDAD_DB_MUNICIPIO, current_id)
    
    newpath_zip2 = os.path.join(newpath_zip, 'recintos_provinciales_inspire_peninbal_etrs89')
    command_export_shp_to_postgis(newpath_zip2, geocoding_settings.CARTOCIUDAD_SHP_PROVINCIA, geocoding_settings.CARTOCIUDAD_DB_PROVINCIA, current_id)
   
 

def export_dbf_to_postgis(provider):
    current_id = str(provider.pk)
    path = os.path.join(tempfile.gettempdir(),'shp2psql',current_id + '_shp2psql')
    
    newpath_zip = os.path.join(path, 'zip', 'CARTOCIUDAD_CALLEJERO_VALENCIA')
    newpath_zip = os.path.join(newpath_zip, geocoding_settings.CARTOCIUDAD_DBF_MUNICIPIO_VIAL)
    
    command = "psql -h " + geocoding_settings.CARTOCIUDAD_DB_HOST + " -p " + geocoding_settings.CARTOCIUDAD_DB_PORT + " -U " + geocoding_settings.CARTOCIUDAD_DB_USER +" -w -d "+ geocoding_settings.CARTOCIUDAD_DB_DATABASE
    command2 = " -c 'CREATE TABLE "+ geocoding_settings.CARTOCIUDAD_DB_SCHEMA + "." + geocoding_settings.CARTOCIUDAD_DB_MUNICIPIO_VIAL + "_" + current_id +" (id_vial numeric, ine_mun character varying(50), alta_db date, CONSTRAINT "+ geocoding_settings.CARTOCIUDAD_DB_MUNICIPIO_VIAL + "_" + current_id +"_pkey PRIMARY KEY (id_vial, ine_mun)) WITH (OIDS=FALSE); ALTER TABLE "+ geocoding_settings.CARTOCIUDAD_DB_SCHEMA + "." + geocoding_settings.CARTOCIUDAD_DB_MUNICIPIO_VIAL + "_" + current_id +" OWNER TO postgres;'"
    call(command + command2, shell=True)  

    command3 = " -c 'CREATE INDEX " + geocoding_settings.CARTOCIUDAD_DB_MUNICIPIO_VIAL + "_" + current_id +"_id_vial_idx ON "+ geocoding_settings.CARTOCIUDAD_DB_SCHEMA + "." + geocoding_settings.CARTOCIUDAD_DB_MUNICIPIO_VIAL + "_" + current_id +" USING btree (id_vial);'"
    call(command + command3, shell=True) 
    
    command4 = " -c 'CREATE INDEX " + geocoding_settings.CARTOCIUDAD_DB_MUNICIPIO_VIAL + "_" + current_id +"_ine_mun_idx ON "+ geocoding_settings.CARTOCIUDAD_DB_SCHEMA + "." + geocoding_settings.CARTOCIUDAD_DB_MUNICIPIO_VIAL + "_" + current_id +" USING btree (ine_mun);'"
    call(command + command4, shell=True)
    
    command4c = " -f " + os.path.join(os.path.dirname(geocoding_settings.BASE_DIR), "plugin_geocoding", "gvsigol_plugin_geocoding", "static", "sql", geocoding_settings.SQL_SOUNDEXESP_FILE_NAME)
    call(command + command4c, shell=True)
    
    #command4b = " -c 'SELECT COUNT(*) FROM public.municipio_vial;'"
    #count = call(command + command4b, shell=True)
    
    db = dbf.Dbf(newpath_zip)
    for rec in db:
        command5 = " -c 'INSERT INTO "+ geocoding_settings.CARTOCIUDAD_DB_SCHEMA + "." + geocoding_settings.CARTOCIUDAD_DB_MUNICIPIO_VIAL + "_" + current_id +" (id_vial, ine_mun) VALUES ("+str(rec["ID_VIAL"])+",\'"+str(rec["INE_MUN"])+"\');'"
        call(command + command5, shell=True)
    
def command_export_shp_to_postgis(path, shp, table_name, pk):

    command1 = "shp2pgsql -I -s " + geocoding_settings.CARTOCIUDAD_SRID + " " + os.path.join(path, shp) + " " + geocoding_settings.CARTOCIUDAD_DB_SCHEMA + "." + table_name + "_" + str(pk)
    command2 = "psql -h " + geocoding_settings.CARTOCIUDAD_DB_HOST + " -p " + geocoding_settings.CARTOCIUDAD_DB_PORT + " -U " + geocoding_settings.CARTOCIUDAD_DB_USER +" -w -d "+ geocoding_settings.CARTOCIUDAD_DB_DATABASE
    
    return call(command1 + " | " + command2, shell=True)  

def cartociudad_full_import(provider):
    if create_cartociudad_config(provider):
        add_solr_config(provider)
        reload_solr_config()
    remove_solr_data(provider)
    full_import_solr_data(provider)
    return True
    
def remove_temp_files(provider):
    current_id = str(provider.pk)
    path = os.path.join(tempfile.gettempdir(),'shp2psql',current_id + '_shp2psql')
    shutil.rmtree(path)
'''    
    
       
class PCParser(ET2.XMLTreeBuilder):

   def __init__(self):
       ET2.XMLTreeBuilder.__init__(self)
       # assumes ElementTree 1.2.X
       self._parser.CommentHandler = self.handle_comment

   def handle_comment(self, data):
       self._target.start(ET2.Comment, {})
       self._target.data(data)
       self._target.end(ET2.Comment)