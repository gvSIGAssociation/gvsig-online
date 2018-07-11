from django.conf.urls import url, include
from rest_framework_jwt.views import obtain_jwt_token, refresh_jwt_token, verify_jwt_token

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
    
    url(r'^api-token-auth/$', 'rest_framework_jwt.views.obtain_jwt_token', name='api-token-auth'),
    url(r'^api-token-refresh/$', 'rest_framework_jwt.views.refresh_jwt_token', name='api-token-refresh'),
    url(r'^api-token-verify/$', 'rest_framework_jwt.views.verify_jwt_token', name='api-token-verify'),
    
    url(r'^api-token-auth/$', obtain_jwt_token, name='api-token-auth'),
    url(r'^api-token-refresh/$', refresh_jwt_token, name='api-token-refresh'),
    url(r'^api-token-verify/$', verify_jwt_token, name='api-token-verify'), 
]