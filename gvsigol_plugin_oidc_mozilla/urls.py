from  mozilla_django_oidc.urls import OIDCAuthenticateClass
from django.urls import path, include
from mozilla_django_oidc.views import OIDCLogoutView
from gvsigol_plugin_oidc_mozilla import views

urlpatterns = [
    path('authenticate/', OIDCAuthenticateClass.as_view(), name='gvsigol_authenticate_user'),
    path('callback/', views.GvsigolOIDCAuthenticationCallbackView.as_view(), name='oidc_authentication_callback'),
    path('logout/', views.GvsigolOIDCLogoutView.as_view(), name='gvsigol_logout_user'),
    # not used, but required by SessionRefresh middleware
    path('oidc/authenticate/', OIDCAuthenticateClass.as_view(), name='oidc_authentication_init'),
    path('oidc/logout/', OIDCLogoutView.as_view(), name='oidc_logout'),
]