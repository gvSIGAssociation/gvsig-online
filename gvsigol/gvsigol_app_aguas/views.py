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
from gvsigol_core.models import Project
'''
@author: Javier Rodrigo <jrodrigo@scolab.es>
'''

from django.shortcuts import render_to_response, RequestContext, redirect

from gvsigol_services.backend_mapservice import backend as mapservice_backend
from gvsigol_services.models import LayerGroup, Workspace, Datastore
from gvsigol_core.models import ProjectLayerGroup, ProjectUserGroup
from gvsigol_auth.backend import backend as ldap_backend
from gvsigol_auth.utils import admin_required
from gvsigol_auth.models import UserGroup
from django.contrib.auth.decorators import login_required
from django.utils.translation import ugettext as _
import settings
import psycopg2
import re

def index(request):
    return redirect('home')
    
@login_required(login_url='/gvsigonline/')
@admin_required
def create_project_wizard(request):        
    if request.method == 'POST':
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        zoom = request.POST.get('zoom')
        extent = request.POST.get('extent')
        name = request.POST.get('project-name')
        description = request.POST.get('project-description')      
          
        image = None
        if 'project-image' in request.FILES:
            image = request.FILES['project-image']
            
        project = create_project(name, description, image, latitude, longitude, zoom, extent)
              
        # Create and assign user groups for project
        create_and_assign_usergroups(project)
        
        # Create and assign layer groups for project
        create_and_assign_layergroups(project)
        
        # Create workspace
        workspace = create_workspace(request, project)
        
        # Create datastore
        datastore = create_datastore(request, project, workspace)

        upload_layers(request, datastore, project)
        
        return redirect('project_list')
    
    else:
        return render_to_response('create_project_wizard.html', {}, context_instance=RequestContext(request))
    

def create_project(name, description, image, latitude, longitude, zoom, extent):
    if image is not None:
        project = Project(
            name = name,
            description = description,
            image = image,
            center_lat = latitude,
            center_lon = longitude,
            zoom = zoom,
            extent = extent
        )
    else:
        project = Project(
            name = name,
            description = description,
            center_lat = latitude,
            center_lon = longitude,
            zoom = zoom,
            extent = extent
        )
    project.save()
    
    return project
    
def create_and_assign_usergroups(project):
    group = UserGroup(
        name = project.name,
        description = 'Grupo de usuarios ' + project.name
    )
    group.save()        
    ldap_backend.add_group(group)
    
    project_usergroup = ProjectUserGroup(
        project = project,
        user_group = group
    )
    project_usergroup.save()
    
    admin_group = UserGroup.objects.get(name__exact='admin')
    project_admingroup = ProjectUserGroup(
        project = project,
        user_group = admin_group
    )
    project_admingroup.save()
    
def create_and_assign_layergroups(project):
    predefined_groups = [{
        'name': 'saneamiento_',
        'title': 'Saneamiento'
    },{
        'name': 'cartografia_',
        'title': 'Cartografía'
    },{
        'name': 'referencias_cartograficas_',
        'title': 'Referencias cartográficas'
    },{
        'name': 'red_riego_',
        'title': 'Red riego'
    },{
        'name': 'agua_potable_',
        'title': 'Agua potable'
    },{
        'name': 'otras_redes_',
        'title': 'Otras redes'
    }]
    
    for group in predefined_groups:
        layergroup_name = group['name'] + project.name.lower()
        
        exists = False
        layergroups = LayerGroup.objects.all()
        for lg in layergroups:
            if layergroup_name == lg.name:
                exists = True
        
        if not exists:        
            layergroup = LayerGroup(
                name = layergroup_name,
                title = group['title'],
                cached = True
            )
            layergroup.save()
        
            project_layergroup = ProjectLayerGroup(
                project = project,
                layer_group = layergroup
            )
            project_layergroup.save()
        
def create_workspace(request, project):
    normalized_name = re.sub('[^A-Za-z0-9]+', '', project.name.lower())    
    session = request.session
    name = normalized_name
    uri = mapservice_backend.getBaseUrl() + "/" + normalized_name
    description = 'Espacio de trabajo ' + project.name
    wms = mapservice_backend.getBaseUrl() + "/" + normalized_name + '/wms'
    wfs = mapservice_backend.getBaseUrl() + "/" + normalized_name + '/wfs'
    wcs = mapservice_backend.getBaseUrl() + "/" + normalized_name + '/wcs'
    cache = mapservice_backend.getBaseUrl() + '/gwc/service/wms'
    
    if mapservice_backend.createWorkspace(session, name, uri, description, wms, wfs, wcs, cache):       
        # save it on DB if successfully created
        workspace = Workspace(
            name = name,
            uri = uri,
            description = description,
            wms_endpoint = wms,
            wfs_endpoint = wfs,
            wcs_endpoint = wcs,
            cache_endpoint = cache
        )
        workspace.save()
        
        return workspace
    
def create_datastore(request, project, ws):
    
    normalized_name = re.sub('[^A-Za-z0-9]+', '', project.name.lower())
    session = request.session
    workspace = ws
    ds_type = 'v_PostGIS'
    name = normalized_name
    description = 'BBDD ' + normalized_name
    
    dbhost = settings.AGUAVAL_MUNI_DB['dbhost']
    dbport = settings.AGUAVAL_MUNI_DB['dbport']
    dbname = settings.AGUAVAL_MUNI_DB['dbname']
    dbuser = settings.AGUAVAL_MUNI_DB['dbuser']
    dbpassword = settings.AGUAVAL_MUNI_DB['dbpassword']
    connection_params = '{ "host": "' + dbhost + '", "port": "' + dbport + '", "database": "' + dbname + '", "schema": "' + normalized_name + '", "user": "' + dbuser + '", "passwd": "' + dbpassword + '", "dbtype": "postgis" }'
    
    if create_schema(normalized_name):
        if mapservice_backend.createDatastore(workspace, ds_type, name, description, connection_params, session=session):
            # save it on DB if successfully created
            datastore = Datastore(
                workspace = workspace, 
                type = ds_type, 
                name = name, 
                description = description, 
                connection_params = connection_params
            )
            datastore.save()
                
            return datastore
            
def create_schema(normalized_name):
    dbhost = settings.AGUAVAL_MUNI_DB['dbhost']
    dbport = settings.AGUAVAL_MUNI_DB['dbport']
    dbname = settings.AGUAVAL_MUNI_DB['dbname']
    dbuser = settings.AGUAVAL_MUNI_DB['dbuser']
    dbpassword = settings.AGUAVAL_MUNI_DB['dbpassword']
    
    connection = get_connection(dbhost, dbport, dbname, dbuser, dbpassword)
    cursor = connection.cursor()
    
    try:        
        create_schema = "CREATE SCHEMA IF NOT EXISTS " + normalized_name + " AUTHORIZATION " + dbuser + ";"       
        cursor.execute(create_schema)

    except StandardError, e:
        print "SQL Error", e
        if e.pgcode == '42710':
            return True
        else:
            return False
    
    close_connection(cursor, connection)
    return True
      
def get_connection(host, port, database, user, password):    
    try:
        conn = psycopg2.connect("host=" + host +" port=" + port +" dbname=" + database +" user=" + user +" password="+ password);
        conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        print "Connect ..."
        
    except StandardError, e:
        print "Failed to connect!", e
        return []
    
    return conn;

def close_connection(cursor, conn):
    #Close connection and exit
    cursor.close();
    conn.close();
    
def upload_layers(request, datastore, project):
    try:
        mapservice_backend.uploadMultiLayer(
            datastore,
            project,
            request.FILES['shapefile'],
            session=request.session,
            table_definition=settings.AGUAVAL_TABLE_DEFINITION
        )

    except Exception as e:
        print e