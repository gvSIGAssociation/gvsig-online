# -*- coding: utf-8 -*-
from django.urls import path

from gvsigol_plugin_sysadmin import views

urlpatterns = [
    path('sysadmin/', views.sysadmin_home, name='sysadmin_home'),
    path('sysadmin/tests/', views.sysadmin_tests, name='sysadmin_tests'),
    path(
        'sysadmin/tests/discover/',
        views.tests_discover,
        name='sysadmin_tests_discover',
    ),
    path('sysadmin/tests/run/', views.tests_run, name='sysadmin_tests_run'),
    path(
        'sysadmin/tests/status/<int:run_id>/',
        views.tests_status,
        name='sysadmin_tests_status',
    ),
    path(
        'sysadmin/settings/db/',
        views.gol_settings,
        name='sysadmin_gol_settings',
    ),
    path(
        'sysadmin/settings/db/save/',
        views.gol_settings_save,
        name='sysadmin_gol_settings_save',
    ),
    path(
        'sysadmin/settings/db/delete/',
        views.gol_settings_delete,
        name='sysadmin_gol_settings_delete',
    ),
    path(
        'sysadmin/settings/db/create/',
        views.gol_settings_create,
        name='sysadmin_gol_settings_create',
    ),
]
