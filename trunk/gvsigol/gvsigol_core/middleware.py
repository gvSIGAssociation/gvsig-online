import re
from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
from django.utils.cache import get_max_age
from django.utils.translation import get_language
import datetime
from django.conf import settings

"""
Middleware to cache certain GET requests when the view being processed sets
response[GVSIGOL_SET_STATIC_CACHE_RESPONSE_KEY] = True  AND
request.get_full_path() is contained in CACHED_PATHS.

Caching is performed server-side (using Django's configured cache framework)
and optionally client-side (using Cache-Control headers).

To enable it, add:
EXTRA_MIDDLEWARE=":gvsigol_core.middleware.UpdateStaticCacheMiddleware:django.contrib.sessions.middleware.SessionMiddleware,django.middleware.locale.LocaleMiddleware:gvsigol_core.middleware.FetchStaticCacheMiddleware:"
to the settings environment.

Use:
settings.STATIC_CACHE_MIDDLEWARE_CACHED_PATHS to set CACHED_PATHS
settings.STATIC_CACHE_MIDDLEWARE_CLIENT_CACHE to enable client caching (server side caching
is always used regardless this setting)
"""

CACHE_TIMEOUT = 600 # seconds
GVSIGOL_SET_STATIC_CACHE_RESPONSE_KEY = '_gvsigol_set_public_cache'
USE_CLIENT_CACHE_DEFAULT = True
CACHED_PATHS=[
    '/gvsigonline/core/project_get_conf/?pid=17&shared_view=false'
]


def remove_vary_cookie(s):
    """
    Since the view has checked that there is no sensitive information and it is publicly cacheable,
    we remove Cookie from Vary header to avoid caching being prevented by load balancer cookies.
    """
    s = re.sub("[~ ,]*Cookie", "", s)
    return re.sub("^Cookie,?[ ]*", "", s)

def get_server_cache_key(request):
    LANGUAGE_CODE = getattr(request, "LANGUAGE_CODE", get_language())
    return "gvsigol_core.middleware.StaticCacheMiddleware.%s.%s" % (LANGUAGE_CODE, request.get_full_path())

def get_client_cache_key(request):
    LANGUAGE_CODE = getattr(request, "LANGUAGE_CODE", get_language())
    return "gvsigol_core.middleware.StaticCacheMiddleware.validity.%s.%s" % (LANGUAGE_CODE, request.get_full_path())

class FetchStaticCacheMiddleware(MiddlewareMixin):
    def __init__(self, get_response=None):
        self.get_response = get_response
        self.CACHED_PATHS = getattr(settings, 'STATIC_CACHE_MIDDLEWARE_CACHED_PATHS', CACHED_PATHS)

    def process_request(self, request):
        if request.method in ('GET', 'HEAD'):
            if request.get_full_path() in self.CACHED_PATHS:
                server_cache_key = get_server_cache_key(request)
                response = cache.get(server_cache_key)
                return response

class UpdateStaticCacheMiddleware(MiddlewareMixin):
    def __init__(self, get_response=None):
        self.get_response = get_response
    
    def process_response(self, request, response):
        if getattr(response, GVSIGOL_SET_STATIC_CACHE_RESPONSE_KEY, False):
            if request.method in ('GET', 'HEAD'):
                response['Vary'] = remove_vary_cookie(response['Vary'])
                server_cache_key = get_server_cache_key(request)
                use_client_cache = getattr(settings, 'STATIC_CACHE_MIDDLEWARE_CLIENT_CACHE', USE_CLIENT_CACHE_DEFAULT)
                if not cache.has_key(server_cache_key):
                    cache.set(server_cache_key, response, CACHE_TIMEOUT)
                    if use_client_cache:
                        max_age = CACHE_TIMEOUT
                        cache.set(get_client_cache_key(request), datetime.datetime.now() + datetime.timedelta(seconds=max_age), max_age)
                        response['Cache-Control'] = 'public, max-age=%d' % max_age
                elif use_client_cache:
                    client_cache_key = get_client_cache_key(request)
                    validity = cache.get(client_cache_key)
                    if validity:
                        # Cache the page only util the last set max-age expires,
                        # then force retrieving the page again, since
                        # we can't easily compute a real etag or last-modified value
                        max_age = (validity - datetime.datetime.now()).total_seconds()
                        if max_age > 0:
                            response['Cache-Control'] = 'public, max-age=%d' % max_age
        return response
