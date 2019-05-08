from django.conf.urls import url, include
from rest_framework_jwt.views import obtain_jwt_token, refresh_jwt_token, verify_jwt_token
from gvsigol_auth import views as auth_views
import rest_framework_jwt

urlpatterns = [
    url(r'^login_user/$', auth_views.login_user, name='login_user'), 
    url(r'^logout_user/$', auth_views.logout_user, name='logout_user'),
    
    #url(r'^password_change/done/$', auth_views.password_change_done, name='password_change_done'),
    url(r'^reset/(?P<user_id>[0-9]+)/(?P<uid>.+)/(?P<token>.+)/$', auth_views.password_reset_confirmation, name='password_reset_confirmation'),
    url(r'^reset/done/$', auth_views.password_reset_complete, name='password_reset_confirmation_complete'),
    url(r'^password_update/$', auth_views.password_update, name='password_update'),
    url(r'^password_reset/$', auth_views.password_reset, name='password_reset'),
    url(r'^password_reset_success/$', auth_views.password_reset_success, name='password_reset_success'),
    
    url(r'^user_list/$', auth_views.user_list, name='user_list'),
    url(r'^user_add/$', auth_views.user_add, name='user_add'),
    url(r'^user_update/(?P<uid>[0-9]+)/$', auth_views.user_update, name='user_update'),
    url(r'^user_delete/(?P<uid>[0-9]+)/$', auth_views.user_delete, name='user_delete'),
    
    url(r'^group_list/$', auth_views.group_list, name='group_list'),
    url(r'^group_add/$', auth_views.group_add, name='group_add'),
    url(r'^group_delete/(?P<gid>[0-9]+)/$', auth_views.group_delete, name='group_delete'),
    
    url(r'^api-token-auth/$', rest_framework_jwt.views.obtain_jwt_token, name='api-token-auth'),
    url(r'^api-token-refresh/$', rest_framework_jwt.views.refresh_jwt_token, name='api-token-refresh'),
    url(r'^api-token-verify/$', rest_framework_jwt.views.verify_jwt_token, name='api-token-verify'),
    
    url(r'^api-token-auth/$', obtain_jwt_token, name='api-token-auth'),
    url(r'^api-token-refresh/$', refresh_jwt_token, name='api-token-refresh'),
    url(r'^api-token-verify/$', verify_jwt_token, name='api-token-verify'), 
]