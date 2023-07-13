from mozilla_django_oidc.auth import OIDCAuthenticationBackend

import importlib
import json
import logging
from django.core.exceptions import SuspiciousOperation, ImproperlyConfigured
from django.utils.encoding import force_bytes
from mozilla_django_oidc.utils import absolutify
from django.urls import reverse
from gvsigol_plugin_oidc_mozilla.gvsigol_auth_mozilla import MAIN_SUPERUSER_ROLE, STAFF_ROLE

LOGGER = logging.getLogger(__name__)

class GvsigolOIDCAuthenticationBackend(OIDCAuthenticationBackend):
    def describe_user_by_claims(self, claims):
            username = claims.get('username')
            return 'username {}'.format(username)

    def filter_users_by_claims(self, claims):
        """Return all users matching the specified email."""
        username = claims.get('username')
        if not username:
            return self.UserModel.objects.none()
        return self.UserModel.objects.filter(username=username)

    def verify_claims(self, claims):
        """Verify the provided claims to decide if authentication should be allowed."""

        # Verify claims required by default configuration
        scopes_str = self.get_settings('OIDC_RP_SCOPES', 'openid email username')
        scopes = scopes_str.split()
        if 'email' in scopes and 'username' in scopes:
            if 'email' not in claims:
                LOGGER.warning('email is required in claims')
                return False
            if 'username' not in claims:
                LOGGER.warning('username is required in claims')
                return False
        if self.get_settings('OIDC_GVSIGOL_CONFIG_MODULE', ''):
            try:
                gvsigol_oidc_config = importlib.import_module(self.get_settings('OIDC_GVSIGOL_CONFIG_MODULE'))
                if not gvsigol_oidc_config.verify_claims(claims):
                    LOGGER.warning('gvsigol_verify_claims check failed')
                    return False
            except Exception as e:
                LOGGER.exception('error configuring user using OIDC_GVSIGOL_CONFIG_MODULE.config_user')
                print(e)


        return True
            
    def create_user(self, claims):
        email = claims.get('email')
        username = claims.get('username', '')
        django_roles = claims.get('gvsigol_roles', [])
        user = self.UserModel.objects.create_user(username,
            email=email,
            first_name = claims.get('first_name', ''),
            last_name = claims.get('last_name', ''),
            is_superuser = (MAIN_SUPERUSER_ROLE in django_roles),
            is_staff = (STAFF_ROLE in django_roles)
        )
        
        if user.is_staff:
            from gvsigol_auth.utils import config_staff_user
            config_staff_user(user.username)
        if self.get_settings('OIDC_GVSIGOL_CONFIG_MODULE', ''):
            try:
                gvsigol_oidc_config = importlib.import_module(self.get_settings('OIDC_GVSIGOL_CONFIG_MODULE'))
                if not gvsigol_oidc_config.config_user(claims):
                    LOGGER.exception('error while configuring user using OIDC_GVSIGOL_CONFIG_MODULE.config_user')
                    return None
            except Exception as e:
                LOGGER.exception('unexpected error configuring user using OIDC_GVSIGOL_CONFIG_MODULE.config_user')
                print(e)

        return user
        

    def update_user(self, user, claims):
        user.email = claims.get('email')
        user.first_name = claims.get('first_name', '')
        user.last_name = claims.get('last_name', '')
        django_roles = claims.get('gvsigol_roles', [])
        user.is_superuser = (MAIN_SUPERUSER_ROLE in django_roles)
        user.is_staff = (STAFF_ROLE in django_roles)
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
        print(access_token_payload)
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
    def has_perm(self, user_obj, perm: str, obj) -> bool:
        print(user_obj)
        return super().has_perm(user_obj, perm, obj)
    """
