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

@author: Nacho Brodin <nbrodin@scolab.es>
'''

from django.urls import path, re_path, include
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import routers

from gvsigol_plugin_projectapi import api
from gvsigol_plugin_projectapi import api_info
from gvsigol import settings
from gvsigol_plugin_projectapi import views
import gvsigol_plugin_projectapi.settings as settings_local

#schema_view = get_swagger_view(title='Gvsigonline Rest API')
router = routers.DefaultRouter()


urlpatterns = [
    path('api/v1/user/', api.UserView.as_view(), name='user'),
    path('api/v1/projectconf/', api_info.ProjectConfView.as_view(), name='projectconf'),
    path('api/v1/platforminfo/', api.PlatformView.as_view(), name='platform_info'),
    
    path('api/v1/projects/', api.ProjectListView.as_view(), name='project_list'),
    path('api/v1/projects/<int:project_id>/', api.ProjectView.as_view(), name='get_project'),
    path('api/v1/projects/<int:project_id>/layers/', api.ProjectLayersView.as_view(), name='get_layers_from_project'),
    path('api/v1/projects/<int:project_id>/groups/', api.ProjectGroupsView.as_view(), name='get_groups_from_project'),
    path('api/v1/projects/<int:project_id>/data/', api.ProjectBaseLayerData.as_view(), name='get_base_layer_data'),
    path('api/v1/projects/shared_view/create/', api.CreateSharedViewAPI.as_view(), name='create_shared_view'),
    path('api/v1/projects/shared_view/save/', api.SaveSharedViewAPI.as_view(), name='save_shared_view'),
    path('api/v1/projects/shared_view/load/<str:view_name>/', api.LoadSharedViewAPI.as_view(), name='load_shared_view'),
    

    path('api/v1/groups/', api.LayerGroupsListView.as_view(), name='get_group_list'),
    path('api/v1/groups/<int:group_id>/', api.LayerGroupView.as_view(), name='get_group'),   
    path('api/v1/groups/<int:group_id>/layers/', api.LayerGroupLayersView.as_view(), name='get_layers_from_group'),

    path('api/v1/servers/', api.ServerView.as_view(), name='get_server'),
    

    #url(r'^api/v1/geoserverapikey/$', api.GeoserverAPIKey.as_view(), name='get_geoserver_api_key'),
    path('', include(router.urls)),



    path('api/v1/public/projects/', api.PublicProjectListView.as_view(), name='get_public_project_list'),
    path('api/v1/public/projectconf/', api_info.PublicProjectConfView.as_view(), name='get_public_project_configuration'),

    path('api/v1/applications/', api.ApplicationListView.as_view(), name='application_list'),
    path('api/v1/applicationconf/<str:name>/', api_info.ApplicationConfView.as_view(), name='applicationconf'),

    #Markers
    path('api/v1/markers/', api_info.MarkerView.as_view(), name='create_marker'),  
    path('api/v1/markers/project/<int:idProj>/', api_info.MarkerView.as_view(), name='get_markers_list_by_idProj'),  
    path('api/v1/markers/<int:pk>/', api_info.MarkerView.as_view(), name='delete_marker,update_marker'),


]


