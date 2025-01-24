from mozilla_django_oidc.middleware import SessionRefresh
import logging

LOGGER = logging.getLogger(__name__)

class GvsigolSessionRefresh(SessionRefresh):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def process_request(self, request):
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            LOGGER.debug('XMLHttpRequest(s) must be exempt from SessionRefresh')
            return
        
        return super().process_request(request)
        