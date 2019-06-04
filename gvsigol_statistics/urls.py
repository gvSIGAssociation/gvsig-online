import django
import actstream
from django.contrib.auth.views import login
from django.contrib import auth
from django.conf.urls import patterns, include, url
from actstream.views import *
import views

urlpatterns = [
    url(r'^activity/', include('actstream.urls')),
    url(r'^get-target-by-user/(?P<plugin_name>.*)/(?P<action_name>.*)/$', views.get_target_by_user, name='get_target_by_user'),
    #url(r'^get-user-by-target/(?P<plugin_name>.*)/(?P<action_name>.*)/$', views.get_user_by_target, name='get_user_by_target'),
    url(r'^get-targets-from-content-type/$', 'gvsigol_statistics.views.get_targets_from_content_type', name='get_targets_from_content_type'),

    url(r'^statistics_list/$', 'gvsigol_statistics.views.statistics_list', name='statistics_list'),

]