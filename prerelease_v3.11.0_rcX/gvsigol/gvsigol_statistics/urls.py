from django.urls import include, path
from gvsigol_statistics import views

app_name="gvsigol_statistics"
urlpatterns = [
    path('activity/', include('actstream.urls')),
    path('get_registered_actions/<plugin_name>/<action_name>/', views.get_registered_actions, name='get_registered_actions'),
    path('register_action/', views.register_action, name='register_action'),

    path('get-targets-from-content-type/', views.get_targets_from_content_type, name='get_targets_from_content_type'),

    path('statistics_list/', views.statistics_list, name='statistics_list'),

]