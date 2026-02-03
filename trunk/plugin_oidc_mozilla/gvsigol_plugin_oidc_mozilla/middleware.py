from mozilla_django_oidc.middleware import SessionRefresh
import logging
from django.conf import settings
from django.urls import resolve, Resolver404, reverse
from rest_framework.views import APIView

from urllib.parse import urlparse

LOGGER = logging.getLogger(__name__)

class GvsigolSessionRefresh(SessionRefresh):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _is_drf_view(self, request):
        try:
            match = resolve(request.path_info)
        except Resolver404:
            return False
        view_func = match.func
        view_class = getattr(view_func, 'cls', None) or getattr(view_func, 'view_class', None)
        try:
            return view_class is not None and issubclass(view_class, APIView)
        except TypeError:
            return False
    
    def is_refreshable_url(self, request):
        if self._is_drf_view(request):
            LOGGER.debug('DRF view detected; skipping SessionRefresh')
            return False
        return super().is_refreshable_url(request)

    def process_request(self, request):
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            LOGGER.debug('XMLHttpRequest(s) must be exempt from SessionRefresh')
            return
        if self._is_drf_view(request):
            LOGGER.debug('DRF view; process_request short-circuit')
            return
        elif settings.DEBUG and request.headers.get('referer', '').endswith("swagger/"):
            url = request.headers.get('referer', '')
            parsed = urlparse(url)
            baseurl = parsed.scheme + "://" + parsed.netloc
            if parsed.port:
                baseurl += ":" + parsed.port
            if baseurl in settings.ALLOWED_HOST_NAMES and parsed.path == reverse('schema-swagger-ui'):
                LOGGER.debug('Swagger ajax requests must be exempt from SessionRefresh')
                return
        
        return super().process_request(request)
        