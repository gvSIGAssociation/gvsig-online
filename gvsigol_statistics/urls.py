import django
import actstream
from django.contrib.auth.views import login
from django.contrib import auth
from django.conf.urls import patterns, include, url
from actstream.views import *
import views

urlpatterns = [
    url(r'^activity/', include('actstream.urls')),
    url(r'^get_registered_actions/(?P<plugin_name>.*)/(?P<action_name>.*)/$', views.get_registered_actions, name='get_registered_actions'),
    url(r'^register_action/$', views.register_action, name='register_action'),

    url(r'^get-targets-from-content-type/$', 'gvsigol_statistics.views.get_targets_from_content_type', name='get_targets_from_content_type'),

    url(r'^statistics_list/$', 'gvsigol_statistics.views.statistics_list', name='statistics_list'),

]