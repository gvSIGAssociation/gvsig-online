from django.urls import path, include
from rest_framework_jwt.views import obtain_jwt_token, refresh_jwt_token, verify_jwt_token
from gvsigol_auth import views as auth_views

from django.conf import settings
from django.utils.module_loading import import_string

LOGIN_VIEW = import_string(getattr(settings, "GVSIGOL_LOGIN_VIEW",  'gvsigol_auth.views.login_user'))
LOGOUT_VIEW = import_string(getattr(settings, "GVSIGOL_LOGOUT_VIEW", 'gvsigol_auth.views.logout_user'))
GVSIGOL_AUTH_BACKEND = getattr(settings, "GVSIGOL_AUTH_BACKEND",  'gvsigol_auth.django_auth')
if GVSIGOL_AUTH_BACKEND == 'gvsigol_auth.django':
    LOGIN_PATHS = [
        path('login_user/', LOGIN_VIEW, name='gvsigol_authenticate_user'),
        path('logout_user/', LOGOUT_VIEW, name='gvsigol_logout_user'),
    ]
else:
    LOGIN_PATHS = [path('', include(GVSIGOL_AUTH_BACKEND + '.urls'))]

urlpatterns = LOGIN_PATHS + [
    path('rest_session_login/', auth_views.rest_session_login, name='rest_session_login'),
    
    #path('password_change/done/', auth_views.password_change_done, name='password_change_done'),
    path('reset/<int:user_id>/<uid>/<token>/', auth_views.password_reset_confirmation, name='password_reset_confirmation'),
    path('reset/done/', auth_views.password_reset_complete, name='password_reset_confirmation_complete'),
    path('password_update/', auth_views.password_update, name='password_update'),
    path('password_reset/', auth_views.password_reset, name='password_reset'),
    path('password_reset_success/', auth_views.password_reset_success, name='password_reset_success'),
    
    path('user_list/', auth_views.user_list, name='user_list'),
    path('user_add/', auth_views.user_add, name='user_add'),
    path('user_update/<int:uid>/', auth_views.user_update, name='user_update'),
    path('user_delete/<int:uid>/', auth_views.user_delete, name='user_delete'),
    
    path('group_list/', auth_views.group_list, name='group_list'),
    path('group_add/', auth_views.group_add, name='group_add'),
    path('group_delete/<int:gid>/', auth_views.group_delete, name='group_delete'),

    path('api-token-auth/', obtain_jwt_token, name='api-token-auth'),
    path('api-token-refresh/', refresh_jwt_token, name='api-token-refresh'),
    path('api-token-verify/', verify_jwt_token, name='api-token-verify'),

    path('has-role/', auth_views.has_role, name='auth-has-role'),
    path('has-group/', auth_views.has_group, name='auth-has-group'),
    path('get-roles/', auth_views.get_roles, name='auth-get-roles'),
    path('get-groups/', auth_views.get_groups, name='auth-get-groups')
]