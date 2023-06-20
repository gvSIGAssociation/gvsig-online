from mozilla_django_oidc.views import OIDCAuthenticationCallbackView
from django.shortcuts import resolve_url

class GvsigolOIDCAuthenticationCallbackView(OIDCAuthenticationCallbackView):
    @property
    def success_url(self):
        return resolve_url(super().success_url)
    @property
    def failure_url(self):
        return resolve_url(super().failure_url)