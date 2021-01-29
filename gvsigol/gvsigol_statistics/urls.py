from django.conf.urls import include, url
from gvsigol_statistics import views

app_name="gvsigol_statistics"
urlpatterns = [
    url(r'^activity/', include('actstream.urls')),
    url(r'^get_registered_actions/(?P<plugin_name>.*)/(?P<action_name>.*)/$', views.get_registered_actions, name='get_registered_actions'),
    url(r'^register_action/$', views.register_action, name='register_action'),

    url(r'^get-targets-from-content-type/$', views.get_targets_from_content_type, name='get_targets_from_content_type'),

    url(r'^statistics_list/$', views.statistics_list, name='statistics_list'),

]