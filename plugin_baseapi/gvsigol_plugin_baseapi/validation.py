# -*- coding: utf-8 -*-


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

@author: Nacho Brodin <nbrodin@scolab.es>
'''

import ast

from django.http.response import HttpResponse

from gvsigol import settings
from gvsigol_services import geographic_servers, utils as services_utils
from gvsigol_services.models import Layer, Datastore, LayerGroup
from gvsigol_auth.models import User
from gvsigol_core.models import Project
from . import util
from psycopg2 import sql as sqlbuilder
from datetime import datetime
import logging
logging.basicConfig()
logger = logging.getLogger(__name__)


class Validation():
    def __init__(self, request):
        self.request = request
        self.usr = str(self.request.user)
        
    def check_version_and_date_columns(self, lyr, con, schema, table, default_version = 1):
        addversioncol = self.check_version_column(con, schema, table, default_version)
        adddatecol = self.check_date_column(con, schema, table)
        if(addversioncol or adddatecol):
            gs = geographic_servers.get_instance().get_server_by_id(lyr.datastore.workspace.server.id)
            gs.reload_featuretype(lyr, nativeBoundingBox=False, latLonBoundingBox=False)
            gs.reload_nodes()
            expose_pks = gs.datastore_check_exposed_pks(lyr.datastore)
            lyr.get_config_manager().refresh_field_conf(include_pks=expose_pks)
            lyr.save()
        
    def check_version_column(self, con, schema, table, default_version = 1):
        """
        Checks if exists the version column in the table but add it 
        """
        sql = "SELECT column_name FROM information_schema.columns WHERE table_name=%s AND table_schema=%s AND column_name=%s"
        try:
            con.cursor.execute(sql, [table, schema, settings.VERSION_FIELD])
            if con.cursor.rowcount == 0:
                sql = "ALTER TABLE {schema}.{table} ADD COLUMN {version_field} INTEGER NOT NULL DEFAULT %s"
                query = sqlbuilder.SQL(sql).format(
                    schema=sqlbuilder.Identifier(schema),
                    table=sqlbuilder.Identifier(table),
                    version_field=sqlbuilder.Identifier(settings.VERSION_FIELD)
                    )
                    
                # print query.as_string(introspect_conn.conn)
                con.cursor.execute(query, [default_version])
                self.add_field_properties(schema, table, settings.VERSION_FIELD)
                return True
        except Exception as e:
            logger.exception("Error checking version column")
            raise HttpException(400, "Error checking version column: " + format(e))
        return False
        
    def check_date_column(self, con, schema, table):
        sql = "SELECT 1 FROM information_schema.columns WHERE table_name=%s AND table_schema=%s AND column_name=%s"
        try:
            con.cursor.execute(sql, [table, schema, settings.DATE_FIELD])
            if con.cursor.rowcount == 0:
                sql = "ALTER TABLE {schema}.{table} ADD COLUMN {date_field} timestamp with time zone NOT NULL DEFAULT now()"
                query = sqlbuilder.SQL(sql).format(
                    schema=sqlbuilder.Identifier(schema),
                    table=sqlbuilder.Identifier(table),
                    date_field=sqlbuilder.Identifier(settings.DATE_FIELD)
                    )
                con.cursor.execute(query, [])
                self.add_field_properties(schema, table, settings.DATE_FIELD)
                return True
        except Exception as e:
            logger.exception("Error checking date column")
            raise HttpException(400, "Error checking date column: " + format(e))
        return False
    
    def add_field_properties(self, schema, table, fieldname):
        try:
            lyr = Layer.objects.get(name=table, datastore__name=schema)
            conf = ast.literal_eval(lyr.conf)
            for i in conf['fields']:
                if i['name'] == fieldname:
                    return
            f = {
                'editable': False,
                'editableactive': False,
                'infovisible': False,
                'name': fieldname,
                'visible': False
            }
            for id, language in settings.LANGUAGES:
                f['title-'+id] = fieldname
            conf['fields'].append(f)
            lyr.conf = conf
            lyr.save()
        except Exception:
            pass
    
    def check_version_to_overwrite(self, con, schema, table, id_feat, version_to_override):
        idfield = util.get_layer_pk_name(con, schema, table)
        
        sql = "SELECT {versionfield} FROM {schema}.{table} WHERE {idfield} = %s"
        query = sqlbuilder.SQL(sql).format(
            versionfield=sqlbuilder.Identifier(settings.VERSION_FIELD),
            schema=sqlbuilder.Identifier(schema),
            table=sqlbuilder.Identifier(table),
            idfield=sqlbuilder.Identifier(idfield))
        con.cursor.execute(query, [id_feat])
        row = con.cursor.fetchall()
        if row is not None and len(row) > 0:
            feat_server_version = row[0][0]
            if int(feat_server_version) != int(version_to_override):
                raise HttpException(409, "The feature version does not match with the version number supplied.")
        else:
            raise HttpException(409, "The feature version does not match with the version number supplied.")
        
                
#     def check_feature_version(self, con, schema, table, feat):
#         """
#         Checks if exists the feature in database and checks if the feature version 
#         stored is greater than the passed
#         """
#         idfield = util.get_layer_pk_name(con, schema, table)
#         if not util.exists(con, schema + "." + table, idfield + "=" + str(feat['properties'][idfield])):
#             raise HttpException(404, "Feature NOT found in the table " + schema + "." + table)
#          
#         feat_server_version = self._get_feat_version(con, feat, schema, table)
#         feat_cli_version = feat['properties'][settings.VERSION_FIELD]
#         if int(feat_cli_version) <= int(feat_server_version):
#             raise HttpException(409, "Conflict between versions. The feature version sent is minor or equal than the version stored. Maybe other client modified the feature while you were editing.")
#  
#El número de versión se incrementa en servidor
    def check_feature_version(self, con, schema, table, feat_id, feat_version):
        """
        Checks if exists the feature in database 
        """
        idfield = util.get_layer_pk_name(con, schema, table)
        if util.count(con, schema, table, idfield, feat_id) == 0:
            raise HttpException(404, "Feature NOT found in the table " + schema + "." + table)

        feat_server_version = self._get_feat_version(con, schema, table, idfield, feat_id)
        if int(feat_version) != int(feat_server_version):
            raise HttpException(409, "Conflict between versions. The feature version sent (" + str(feat_version) + ") is different than the last version stored (" + str(feat_server_version) + "). Maybe other client modified the feature while you were editing.")
    
    def check_feat_exists(self, con, schema, table, feat_id, idfield=None):
        if not idfield:
            idfield = util.get_layer_pk_name(con, schema, table)
        if util.count(con, schema, table, idfield, feat_id) > 0:
            return None
        raise HttpException(404, "Feature NOT found")
    
    def _get_feat_version(self, con,  schema, table, idfield, fid):
        sql = "SELECT {version_field} FROM {schema}.{table} WHERE {idfield} = %s"
        query = sqlbuilder.SQL(sql).format(
            schema=sqlbuilder.Identifier(schema),
            table=sqlbuilder.Identifier(table),
            idfield=sqlbuilder.Identifier(idfield),
            version_field=sqlbuilder.Identifier(settings.VERSION_FIELD)
            )
        con.cursor.execute(query, [fid])
        row = con.cursor.fetchall()
        if row is not None and len(row) > 0:
            return row[0][0]    
        
    def check_edit_permission(self, lyr):
        try:
            if not services_utils.can_write_layer(self.request, lyr):
                raise HttpException(403, "The user does not have permission to edit this layer")
        except Layer.DoesNotExist:
            raise HttpException(404, "Layer NOT found")
        except User.DoesNotExist:
            raise HttpException(404, "User NOT found")
    
    def check_read_permission(self, lyr):
        try:
            if not services_utils.can_read_layer(self.request, lyr):
                raise HttpException(403, "The user does not have permission to read this layer")
        except Layer.DoesNotExist:
            raise HttpException(404, "Layer NOT found")
        except User.DoesNotExist:
            raise HttpException(404, "User NOT found")
        
    def user_exists(self):
        # FIXME OIDC. Los usuarios pueden no exisir en el modelo de
        # Django todavía (si nunca hicieron Login) pero son usuarios validos en Keycloak.
        if User.objects.filter(username=self.usr).count() == 0:
            raise HttpException(404, "User NOT found")
        
    def layer_exists(self, lyr_id):
        if Layer.objects.filter(id=lyr_id).count() == 0:
            raise HttpException(404, "Layer NOT found")
    
    def project_exists(self, prj_id):
        now = datetime.now()
        if Project.objects.filter(id=prj_id, expiration_date__gte=now).count() == 0 and Project.objects.filter(id=prj_id, expiration_date=None).count() == 0:
            raise HttpException(404, "Project NOT found")
    
    def group_exists(self, grp_id):
        if LayerGroup.objects.filter(id=grp_id).count() == 0:
            raise HttpException(404, "Group NOT found")
    
    def check_feature(self, feat):
        geom = feat['geometry']
        if (feat is None or feat['type'] is None or geom is None or feat['properties'] is None):
            raise HttpException(400, "Feature malformed. Fields geometry, type and properties are needed")
        
        if (not isinstance(geom['coordinates'], list) or len(geom['coordinates']) <= 0):
            raise HttpException(400, "Feature malformed. Geometry is not properly")
        
        type_ = geom['type'].upper()  
        if(type_ != 'POINT' and type_ != 'MULTIPOINT' and type_ != 'LINESTRING' and type_ != 'MULTILINESTRING' and type_ != 'POLYGON' and type_ != 'MULTIPOLYGON'):
            raise HttpException(400, "Feature malformed. Wrong feature type")
        
        if geom['coordinates'] is None:
            raise HttpException(400,  "Feature malformed. Wrong coordinates")

    def check_version_feature(self, feat, idfield):
        if 'properties' not in feat:
            raise HttpException(400,  "Feature malformed. Field properties is needed")
        if settings.VERSION_FIELD not in feat['properties']:
            raise HttpException(400,  "Feature malformed. The field feat_version_gvol is needed for this call")
        if idfield not in feat['properties']:
            raise HttpException(400,  "Feature malformed. The field " + idfield + " is needed for this call") 
    
    def check_project_allowed(self, prj_id):
        projects_by_user = util.get_projects_ids_by_user(self.request)
        if not int(prj_id) in projects_by_user:
            raise HttpException(403,  "The project is not allowed to this user")
        
    def check_group_allowed(self, grj_id):
        layergroups_by_user = util.get_layergroups_by_user(self.request)
        ids = [i.id for i in layergroups_by_user]
        if not int(grj_id) in ids:
            raise HttpException(403,  "The group is not allowed to this user")
    
    def check_layer_allowed(self, lyr_id):
        layers_by_user = services_utils.get_layerread_by_user(self.request)
        for i in layers_by_user:
            if int(i.id) == int(lyr_id):
                if i.datastore is None:
                    raise HttpException(404,  "The layer has not datastore. Maybe is a external layer or a raster layer")
                else:
                 return i.datastore.name, i.name
        raise HttpException(403,  "The layer is not allowed to this user")
                   
    def check_create_feature(self, lyr_id, content):
        self.check_edit_permission(lyr_id)
        self.check_feature(content)
        
    def check_update_feature(self, lyr_id, content):
        self.check_edit_permission(lyr_id)
        con, table, schema = services_utils.get_db_connect_from_layer(lyr_id)
        idfield = util.get_layer_pk_name(con, schema, table)
        con.close()
        self.check_version_feature(content, idfield)
        
    def check_get_feature(self, lyr_id):
        self.user_exists()
        self.layer_exists(lyr_id)
        self.check_layer_allowed(lyr_id)
        
    def check_delete_feature(self, lyr_id):
        self.check_edit_permission(lyr_id)
        
    def check_get_layer_data(self, lyr_id):
        self.user_exists()
        self.layer_exists(lyr_id)
        self.check_layer_allowed(lyr_id)
    
    def check_get_layer_description(self, lyr_id):
        return self.check_get_layer_data(lyr_id)
    
    def check_get_project(self, prj_id):
        self.user_exists()
        self.project_exists(prj_id)
        self.check_project_allowed(prj_id)
        
    def check_get_project_groups(self, prj_id):
        self.user_exists()
        self.project_exists(prj_id)
        self.check_project_allowed(prj_id)
    
    def check_get_project_layers(self, prj_id):
        self.user_exists()
        self.project_exists(prj_id)
        self.check_project_allowed(prj_id)
        
    def check_get_layers_by_group(self, grp_id):
        self.user_exists() 
        self.group_exists(grp_id)
        self.check_group_allowed(grp_id)
        
    def check_get_group(self, grp_id):
        self.user_exists()  
        self.group_exists(grp_id) 
        self.check_group_allowed(grp_id)
    
    def check_get_layer(self, lyr_id):
        self.check_read_permission(lyr_id)
        
    def check_get_project_list(self):
        pass
        #self.user_exists()
        
    def check_feature_list(self, lyr_id):
        self.check_get_layer(lyr_id) 
        
    def check_get_layer_list(self):
        self.user_exists() 
        
    def check_get_group_list(self):
        self.check_get_layer_list()
        
    def check_get_resource_list(self, lyr_id):
        self.check_get_layer(lyr_id)
        
    def check_uploaded_image(self, request, lyr_id):
        self.check_edit_permission(lyr_id)
        
        try:
            image = request.FILES['image']
            title = request.POST['title']
            if(image is None or title is None):
                HttpException(400, "Error in the input parameters. Image and title cannot be null")
        except Exception:
            raise HttpException(400, "Error in the input parameters.")
    
    def check_delete_image(self, lyr_id, resource):
        self.check_edit_permission(lyr_id)
        if(int(resource.layer_id) != int(lyr_id)):
            raise HttpException(400, "The layer does not have this resource.")

    def is_public_layer(self, lyr_id):
        layer = Layer.objects.get(id=lyr_id)
        if not layer.public:
            raise HttpException(403, "Layer is not public")

    def check_create_layer(self, username, datastoreid):
        try:
            if not services_utils.can_manage_datastore(username, datastoreid):
                raise HttpException(403, "The user does not have permission to create a layer in this datastore")
        except Exception:
            raise HttpException(403, "The user does not have permission to create a layer in this datastore")

class HttpException(Exception):
    def __init__(self, code, msg):
        self.msg = msg
        self.code = code
        
    def get_message(self):
        return "<html><h3>" + str(self.code) + ": " + self.msg + "</h3></html>"
                    
    def get_exception(self):
        response = HttpResponse(self.get_message())
        response.status_code = self.code
        return response
        
    
    

    