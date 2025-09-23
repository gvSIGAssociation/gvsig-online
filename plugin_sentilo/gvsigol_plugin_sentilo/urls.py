from django.urls import path
from django.views.i18n import JavaScriptCatalog
from gvsigol_plugin_sentilo import views

urlpatterns = [
    path('sentilo/sentilo_conf/', views.sentilo_conf, name='sentilo_conf'),
    path('sentilo/list/', views.list_sentilo_configs, name='list_sentilo_configs'),
    path('sentilo/delete/<int:config_id>/', views.delete_sentilo_config, name='delete_sentilo_config'),
    path('sentilo/manual-cleanup/', views.manual_cleanup, name='manual_cleanup'),
    path('sentilo/cleanup-orphaned-tasks/', views.cleanup_orphaned_tasks, name='cleanup_orphaned_tasks'),
]