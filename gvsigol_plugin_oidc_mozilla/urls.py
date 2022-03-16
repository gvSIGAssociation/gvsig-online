from  mozilla_django_oidc.urls import OIDCAuthenticateClass
from django.urls import path
from mozilla_django_oidc.views import OIDCLogoutView
from gvsigol_plugin_oidc_mozilla import views

urlpatterns = [
    path('authenticate/', OIDCAuthenticateClass.as_view(), name='gvsigol_authenticate_user'),
    path('callback/', views.GvsigolOIDCAuthenticationCallbackView.as_view(), name='oidc_authentication_callback'),
    path('logout/', OIDCLogoutView.as_view(), name='gvsigol_logout_user'),
]