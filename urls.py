from django.urls import path, include
from rest_framework_jwt.views import obtain_jwt_token, refresh_jwt_token, verify_jwt_token
from gvsigol_auth import views as auth_views
import rest_framework_jwt

urlpatterns = [
    path('login_user/', auth_views.login_user, name='login_user'), 
    path('logout_user/', auth_views.logout_user, name='logout_user'),
    
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
    
    path('api-token-auth/', rest_framework_jwt.views.obtain_jwt_token, name='api-token-auth'),
    path('api-token-refresh/', rest_framework_jwt.views.refresh_jwt_token, name='api-token-refresh'),
    path('api-token-verify/', rest_framework_jwt.views.verify_jwt_token, name='api-token-verify'),
    
    path('api-token-auth/', obtain_jwt_token, name='api-token-auth'),
    path('api-token-refresh/', refresh_jwt_token, name='api-token-refresh'),
    path('api-token-verify/', verify_jwt_token, name='api-token-verify'), 
]