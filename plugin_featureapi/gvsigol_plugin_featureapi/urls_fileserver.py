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

@author: César Martinez <cmartinez@scolab.es>
'''

from django.urls import path
from gvsigol_plugin_featureapi import api_layer
from gvsigol_plugin_featureapi import api_feature
from gvsigol_plugin_featureapi import views

urlpatterns = [
    # fileserver URLs are managed by XSendfile and they are served under the /fileserver
    # prefix to simplify deployments
    path('api/v1/layers/features/resources/<int:resource_id>/', api_feature.FileAttachedView.as_view(), name='get_attached_file'),

    path('api/v1/layer_historic_resource/<int:layer_id>/<int:feat_id>/<int:version>/', views.get_layer_historic_resource, name='layer_historic_resource'),

]
