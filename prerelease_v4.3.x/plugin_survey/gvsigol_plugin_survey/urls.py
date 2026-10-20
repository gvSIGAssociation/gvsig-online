from django.urls import path, re_path
from gvsigol_plugin_survey import views

urlpatterns = [
    path('survey/survey_list/', views.survey_list, name='survey_list'),
    path('survey/survey_add/', views.survey_add, name='survey_add'),
    path('survey/survey_update/<int:survey_id>/', views.survey_update, name='survey_update'),
    path('survey/survey_delete/<int:survey_id>/', views.survey_delete, name='survey_delete'),
    path('survey/survey_section_add/<int:survey_id>/', views.survey_section_add, name='survey_section_add'),
    path('survey/survey_section_update/<int:survey_section_id>/', views.survey_section_update, name='survey_section_update'),
    path('survey/survey_section_delete/<int:survey_section_id>/', views.survey_section_delete, name='survey_section_delete'),
    
    path('survey/survey_definition/<int:survey_id>/', views.survey_definition, name='survey_definition'),
    path('survey/survey_update_project/<int:survey_id>/', views.survey_update_project, name='survey_update_project'),
    
    path('survey/survey_section_update_project/<int:section_id>/', views.survey_section_update_project, name='survey_section_update_project'),
    path('survey/survey_permissions/<int:survey_id>/', views.survey_permissions, name='survey_permissions'),
    path('surveys/upload/', views.survey_upload_db, name='survey_upload_db'),

    path('surveys/', views.surveys, name='surveys'),
    re_path(r'^surveys/(?P<survey_name>[a-zA-Z0-9_]+)/$', views.survey_definition_by_name, name='survey_definition_by_name'),
    path('surveys/upload_db/', views.survey_upload, name='survey_upload'),
]
