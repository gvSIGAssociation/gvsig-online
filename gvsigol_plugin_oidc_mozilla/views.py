from mozilla_django_oidc.views import OIDCAuthenticationCallbackView, OIDCLogoutView
from mozilla_django_oidc.views import OIDCLogoutView
from django.shortcuts import resolve_url

class GvsigolOIDCAuthenticationCallbackView(OIDCAuthenticationCallbackView):
    @property
    def success_url(self):
        return resolve_url(super().success_url)
    @property
    def failure_url(self):
        return resolve_url(super().failure_url)

class GvsigolOIDCLogoutView(OIDCLogoutView):
    @property
    def redirect_url(self):
        return resolve_url(super().redirect_url)