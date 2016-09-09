from django.conf.urls import url

urlpatterns = [
    url(r'^login_user/$', 'gvsigol_auth.views.login_user', name='login_user'), 
    url(r'^logout_user/$', 'gvsigol_auth.views.logout_user', name='logout_user'),
    
    url(r'^password_update/$', 'gvsigol_auth.views.password_update', name='password_update'),
    url(r'^password_reset/$', 'gvsigol_auth.views.password_reset', name='password_reset'),
    url(r'^password_reset_success/$', 'gvsigol_auth.views.password_reset_success', name='password_reset_success'),
    
    url(r'^user_list/$', 'gvsigol_auth.views.user_list', name='user_list'),
    url(r'^user_add/$', 'gvsigol_auth.views.user_add', name='user_add'),
    url(r'^user_update/(?P<uid>[0-9]+)/$', 'gvsigol_auth.views.user_update', name='user_update'),
    url(r'^user_delete/(?P<uid>[0-9]+)/$', 'gvsigol_auth.views.user_delete', name='user_delete'),
    
    url(r'^group_list/$', 'gvsigol_auth.views.group_list', name='group_list'),
    url(r'^group_add/$', 'gvsigol_auth.views.group_add', name='group_add'),
    url(r'^group_delete/(?P<gid>[0-9]+)/$', 'gvsigol_auth.views.group_delete', name='group_delete'),
]