from mozilla_django_oidc.middleware import SessionRefresh
import logging
from django.conf import settings
from django.shortcuts import reverse
from urllib.parse import urlparse

LOGGER = logging.getLogger(__name__)

class GvsigolSessionRefresh(SessionRefresh):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def process_request(self, request):
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            LOGGER.debug('XMLHttpRequest(s) must be exempt from SessionRefresh')
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
        