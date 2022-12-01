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

from gvsigol_plugin_featureapi import api_layer
from gvsigol_plugin_featureapi import api_feature
from gvsigol import settings
import gvsigol_plugin_featureapi.settings as settings_local
from gvsigol_plugin_featureapi import views


router = routers.DefaultRouter()

urlpatterns = [ 
    path('api/v1/layers/', api_layer.LayerListView.as_view(), name='get_layer_list,create_layer'),
    path('api/v1/layers/<int:lyr_id>/', api_layer.LayersView.as_view(), name='get_layer,delete_layer'), 
    path('api/v1/layers/<int:lyr_id>/data/', api_layer.LayersData.as_view(), name='get_layer_data'),
    path('api/v1/layers/<int:lyr_id>/style/', api_layer.LayersStyle.as_view(), name='get_layer_style'),
    path('api/v1/layers/<int:lyr_id>/description/', api_layer.LayerDescription.as_view(), name='get_layer_description'),
    path('api/v1/layers/<int:lyr_id>/capabilities/', api_layer.LayerCapabilities.as_view(), name='get_layer_capabilitiess'),
    path('api/v1/layers/<int:lyr_id>/features/', api_feature.FeaturesView.as_view(), name='get_feature_list,create_feature,update_feature'),
    path('api/v1/layers/<int:lyr_id>/featurelist/', api_feature.FeaturesExtentView.as_view(), name='get_feature_list_by_extent'),
    path('api/v1/layers/<int:lyr_id>/<int:feat_id>/', api_feature.FeaturesDeleteView.as_view(), name='get_feature,delete_feature'),
    path('api/v1/layers/<int:lyr_id>/<int:feat_id>/versions/', api_feature.FeatureVersionsView.as_view(), name='get_feature_versions'),
    path('api/v1/layers/<int:lyr_id>/feature/', api_feature.FeatureByPointView.as_view(), name='get_feature_by_point'),
    path('api/v1/layers/<int:lyr_id>/<int:feat_id>/resources/', api_feature.FileUploadView.as_view(), name='get_list_attached_files,add_resource'),
    path('api/v1/layers/<int:lyr_id>/<int:feat_id>/resources/<int:resource_id>/', api_feature.FileDeleteView.as_view(), name='delete_attached_file'),
    path('api/v1/layers/<int:lyr_id>/fieldoptions/', api_layer.LayerFieldOptions.as_view(), name='get_layer_field_options'),

    path('api/v1/layers/<int:lyr_id>/deletedfeatures/', api_feature.FeatureVersionsDeleted.as_view(), name='get_deleted_features'),
    path('api/v1/layers/<int:lyr_id>/updatedfeatures/', api_feature.FeatureVersionsUpdated.as_view(), name='get_updated_features'),
    path('api/v1/layers/<int:lyr_id>/createdfeatures/', api_feature.FeatureVersionsCreated.as_view(), name='get_created_features'),
    path('api/v1/layers/<int:lyr_id>/addedresources/', api_feature.FeatureVersionsAddedResources.as_view(), name='get_added_resources'),
    path('api/v1/layers/<int:lyr_id>/deletedresources/', api_feature.FeatureVersionsDeletedResources.as_view(), name='get_deleted_resources'),

    path('api/v1/layers/<int:lyr_id>/legend/', api_layer.Legend.as_view(), name='get_geoserver_legend'),
    path('api/v1/layers/<int:lyr_id>/checkchanges/', api_layer.LayerChanges.as_view(), name='check_changes'),

    path('api/v1/public/layers/<int:lyr_id>/feature/<int:feat_id>/', api_feature.FeatureGetView.as_view(), name='get_feature'),
    path('api/v1/public/layers/<int:lyr_id>/features/', api_feature.PublicFeaturesView.as_view(), name='get_feature_list'),
    path('api/v1/public/layers/<int:lyr_id>/feature/', api_feature.PublicFeatureByPointView.as_view(), name='get_feature_by_point'),
    path('api/v1/public/layers/<int:lyr_id>/<int:feat_id>/resources/', api_feature.ResourcesView.as_view(), name='get_list_public_attached_files'),
    path('api/v1/public/layers/<int:lyr_id>/fieldoptions/', api_layer.PublicLayerFieldOptions.as_view(), name='get_public_layer_field_options'),
    path('api/v1/public/layers/<int:lyr_id>/legend/', api_layer.PublicLegend.as_view(), name='get_geoserver_public_legend'),

    path('edition/feature_version_management/', views.feature_version_management, name='layers_group'),
    path('edition/check_feat_version/', views.check_version, name='check_feature_version'),

    # Deprecated urls since they have been moved under de fileserver prefix. See urls_fileserver.py    
    path('get_historic_resource/<int:layer_id>/<int:feat_id>/<int:version>/', views.get_layer_historic_resource, name='get_layer_historic_resource'),
]


