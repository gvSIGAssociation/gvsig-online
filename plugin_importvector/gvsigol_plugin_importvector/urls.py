# -*- coding: utf-8 -*-
from django.urls import path

from gvsigol_plugin_importvector import api

urlpatterns = [
    path(
        'api/v1/projects/<int:project_id>/layers/import-options/',
        api.ProjectLayerImportOptionsView.as_view(),
        name='project_layer_import_options',
    ),
    path(
        'api/v1/projects/<int:project_id>/layers/import/',
        api.ProjectLayerImportView.as_view(),
        name='project_layer_import',
    ),
    path(
        'api/v1/projects/<int:project_id>/layers/import/<uuid:job_id>/',
        api.ProjectLayerImportStatusView.as_view(),
        name='project_layer_import_status',
    ),
]
