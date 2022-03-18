from mozilla_django_oidc.auth import OIDCAuthenticationBackend

import json
import logging
from django.core.exceptions import SuspiciousOperation, ImproperlyConfigured
from django.utils.encoding import force_bytes
from mozilla_django_oidc.utils import absolutify
from django.urls import reverse

LOGGER = logging.getLogger(__name__)

class GvsigolOIDCAuthenticationBackend(OIDCAuthenticationBackend):
    def create_user(self, claims):
        user = super(GvsigolOIDCAuthenticationBackend, self).create_user(claims)
        user.username = claims.get('username', '')
        user.first_name = claims.get('first_name', '')
        user.last_name = claims.get('last_name', '')
        django_roles = claims.get('gvsigol_roles', [])
        user.is_superuser = ('GVSIGOL_DJANGO_SUPERUSER' in django_roles)
        user.is_staff = ('GVSIGOL_DJANGO_STAFF' in django_roles)
        user.save()

        return user

    def update_user(self, user, claims):
        user.username = claims.get('username', '')
        user.first_name = claims.get('first_name', '')
        user.last_name = claims.get('last_name', '')
        django_roles = claims.get('gvsigol_roles', [])
        user.is_superuser = ('GVSIGOL_DJANGO_SUPERUSER' in django_roles)
        user.is_staff = ('GVSIGOL_DJANGO_STAFF' in django_roles)
        user.save()

        return user

    def authenticate(self, request, **kwargs):
        """Authenticates a user based on the OIDC code flow."""

        self.request = request
        if not self.request:
            return None

        state = self.request.GET.get('state')
        code = self.request.GET.get('code')
        nonce = kwargs.pop('nonce', None)

        if not code or not state:
            return None

        reverse_url = self.get_settings('OIDC_AUTHENTICATION_CALLBACK_URL',
                                        'oidc_authentication_callback')

        token_payload = {
            'client_id': self.OIDC_RP_CLIENT_ID,
            'client_secret': self.OIDC_RP_CLIENT_SECRET,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': absolutify(
                self.request,
                reverse(reverse_url)
            ),
        }

        # Get the token
        token_info = self.get_token(token_payload)
        id_token = token_info.get('id_token')
        access_token = token_info.get('access_token')

        # Validate the token
        id_token_bytes = force_bytes(id_token)
        key = self._get_key(id_token_bytes)
        payload = self.verify_token(id_token_bytes, key, nonce=nonce)

        access_token_bytes = force_bytes(access_token)
        key = self._get_key(access_token_bytes)
        access_token_payload = self.verify_token(access_token_bytes, key, nonce=nonce)
        self.request.session['oidc_access_token_payload'] = access_token_payload
        self.request.session['oidc_id_token_payload'] = payload

        if payload:
            self.store_tokens(access_token, id_token)
            try:
                return self.get_or_create_user(access_token, id_token, payload)
            except SuspiciousOperation as exc:
                LOGGER.warning('failed to get or create user: %s', exc)
                return None

        return None

    def _get_key(self, token):
        if self.OIDC_RP_SIGN_ALGO.startswith('RS'):
            if self.OIDC_RP_IDP_SIGN_KEY is not None:
                key = self.OIDC_RP_IDP_SIGN_KEY
            else:
                key = self.retrieve_matching_jwk(token)
        else:
            key = self.OIDC_RP_CLIENT_SECRET
        return key

    def verify_token(self, token, key, **kwargs):
        """Validate the token signature."""
        nonce = kwargs.get('nonce')
        payload_data = self.get_payload_data(token, key)

        # The 'token' will always be a byte string since it's
        # the result of base64.urlsafe_b64decode().
        # The payload is always the result of base64.urlsafe_b64decode().
        # In Python 3 and 2, that's always a byte string.
        # In Python3.6, the json.loads() function can accept a byte string
        # as it will automagically decode it to a unicode string before
        # deserializing https://bugs.python.org/issue17909
        payload = json.loads(payload_data.decode('utf-8'))
        token_nonce = payload.get('nonce')

        if self.get_settings('OIDC_USE_NONCE', True) and nonce != token_nonce:
            msg = 'JWT Nonce verification failed.'
            raise SuspiciousOperation(msg)
        return payload
    """
    TODO: map claims to django permissions (if needed)
    def has_perm(self, user_obj: _AnyUser, perm: str, obj: Optional[Model] = ...) -> bool:
        return super().has_perm(user_obj, perm, obj)
    """
