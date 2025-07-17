from mozilla_django_oidc.auth import OIDCAuthenticationBackend
#from mozilla_django_oidc.contrib.drf import OIDCAuthentication

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
    def __init__(self, *args, **kwargs):
        if self.get_settings('OIDC_GVSIGOL_CONFIG_MODULE', ''):
            try:
                self.gvsigol_oidc_config = importlib.import_module(self.get_settings('OIDC_GVSIGOL_CONFIG_MODULE'))
            except Exception as e:
                LOGGER.exception('unexpected error importing OIDC_GVSIGOL_CONFIG_MODULE')
                print(e)
                self.gvsigol_oidc_config = None
        else:
            self.gvsigol_oidc_config = None
        super().__init__(*args, **kwargs)

    def describe_user_by_claims(self, claims):
            username = claims.get('username')
            return 'username {}'.format(username)

    def filter_users_by_claims(self, claims):
        """Return all users matching the specified email."""
        username = claims.get('username')
        if not username:
            return self.UserModel.objects.none()
        return self.UserModel.objects.filter(username=username)

    def verify_claims(self, claims, token_payload=None):
        """Verify the provided claims to decide if authentication should be allowed."""
        """ TODO: submit 'sub' check to mozilla-django-oidc and remove this method """

        if token_payload: # checking id token sub against userinfo sub is recommended by OIDC spec
            if token_payload.get('sub') != claims.get('sub'):
                 return False
        # Verify claims required by default configuration
        scopes_str = self.get_settings('OIDC_RP_SCOPES', 'openid email username')
        scopes = scopes_str.split()
        if 'username' in scopes and 'username' not in claims:
            LOGGER.warning('username is required in claims')
            return False

        if 'email' in scopes and not claims.get('username', '').startswith('service-account'): # FIXME: buscar exclusion mas robusta para service account
            if 'email' not in claims:
                LOGGER.warning('email is required in claims')
                return False
        if self.gvsigol_oidc_config:
            if not self.gvsigol_oidc_config.verify_claims(claims):
                    LOGGER.warning('gvsigol_verify_claims check failed')
                    return False

        return True

    def get_or_create_user(self, access_token, id_token, payload):
        """Returns a User instance if 1 user is found. Creates a user if not found
        and configured to do so. Returns nothing if multiple users are matched."""

        user_info = self.get_userinfo(access_token, id_token, payload)

        claims_verified = self.verify_claims(user_info, payload)
        if not claims_verified:
            msg = "Claims verification failed"
            raise SuspiciousOperation(msg)

        # email based filtering
        users = self.filter_users_by_claims(user_info)

        if len(users) == 1:
            return self.update_user(users[0], user_info)
        elif len(users) > 1:
            # In the rare case that two user accounts have the same email address,
            # bail. Randomly selecting one seems really wrong.
            msg = "Multiple users returned"
            raise SuspiciousOperation(msg)
        elif self.get_settings("OIDC_CREATE_USER", True):
            user = self.create_user(user_info)
            return user
        else:
            LOGGER.debug(
                "Login failed: No user with %s found, and " "OIDC_CREATE_USER is False",
                self.describe_user_by_claims(user_info),
            )
            return None
         
    def create_user(self, claims):
        email = claims.get('email')
        username = claims.get('username', '')
        django_roles = claims.get('gvsigol_roles', [])
        user = self.UserModel.objects.create_user(username,
            email=email,
            first_name = claims.get('given_name', ''),
            last_name = claims.get('family_name', ''),
            is_superuser = (MAIN_SUPERUSER_ROLE in django_roles),
            is_staff = (STAFF_ROLE in django_roles or MAIN_SUPERUSER_ROLE in django_roles)
        )
        
        if self.gvsigol_oidc_config:
            try:
                if not self.gvsigol_oidc_config.config_user(user, claims):
                    LOGGER.exception('error while configuring user using OIDC_GVSIGOL_CONFIG_MODULE.config_user')
                    return None
            except Exception as e:
                LOGGER.exception('unexpected error configuring user using OIDC_GVSIGOL_CONFIG_MODULE.config_user')
                print(e)
        else:
            if user.is_staff:
                from gvsigol_auth.utils import config_staff_user
                try:
                    config_staff_user(user.username)
                except:
                    LOGGER.exception("Error configuring staff user: {user.username}")

        return user

    def default_update_user(self, user, claims):
        user.email = claims.get('email', '')
        user.first_name = claims.get('given_name', '')
        user.last_name = claims.get('family_name', '')
        django_roles = claims.get('gvsigol_roles', [])
        was_staff = user.is_staff or user.is_superuser
        user.is_superuser = (MAIN_SUPERUSER_ROLE in django_roles)
        user.is_staff = (STAFF_ROLE in django_roles or MAIN_SUPERUSER_ROLE in django_roles)
        user.save()
        if user.is_staff and not was_staff:
            from gvsigol_auth.utils import config_staff_user
            try:
                config_staff_user(user.username)
            except Exception as e:
                LOGGER.exception("Error configuring staff user: %s", user.username)
                print(e)
        return user


    def update_user(self, user, claims):
        if self.gvsigol_oidc_config and hasattr(self.gvsigol_oidc_config, 'update_user'):
            return self.gvsigol_oidc_config.update_user(user, claims, self)
        return self.default_update_user(user, claims)

    def _store_tokens(self, id_token, id_token_payload, nonce, token_info):
        session = self.request.session
        if self.get_settings('OIDC_STORE_ID_TOKEN', False):
            session["oidc_id_token"] = id_token
            session['oidc_id_token_payload'] = id_token_payload

        if self.get_settings('OIDC_STORE_ACCESS_TOKEN', False):
            access_token = token_info.get('access_token')
            access_token_bytes = force_bytes(access_token)
            key = self._get_key(access_token_bytes)
            access_token_payload = self.verify_token(access_token_bytes, key)
            LOGGER.debug(access_token_payload)
            session['oidc_access_token'] = access_token
            session['oidc_access_token_payload'] = access_token_payload

        self.store_tokens(access_token, id_token)
        if self.get_settings('OIDC_STORE_REFRESH_TOKEN', False):
            # get refresh token
            refresh_token = token_info.get('refresh_token')
            #not_before_policy =  token_info.get('not-before-policy')
            session['oidc_refresh_token'] = refresh_token


    def authenticate(self, request, **kwargs):
        """Authenticates a user based on the OIDC code flow."""

        self.request = request
        if not self.request:
            return None

        state = self.request.GET.get('state')
        code = self.request.GET.get('code')
        nonce = kwargs.pop('nonce', None)
        code_verifier = kwargs.pop("code_verifier", None)

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
        # Send code_verifier with token request if using PKCE
        if code_verifier is not None:
            token_payload.update({"code_verifier": code_verifier})

        # Get the token
        token_info = self.get_token(token_payload)
        id_token = token_info.get('id_token')
        access_token = token_info.get("access_token")
        # Validate the token
        id_token_bytes = force_bytes(id_token)
        key = self._get_key(id_token_bytes)
        payload = self.verify_token(id_token_bytes, key, nonce=nonce)

        if payload:
            try:
                return self.get_or_create_user(access_token, id_token, payload)
            except SuspiciousOperation as exc:
                LOGGER.warning('failed to get or create user: %s', exc)
                return None
            finally:
                self._store_tokens(id_token, payload, nonce, token_info)
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

        if nonce is not None: # nonce is not relevant for access token and is not included in KC >= 25, so skip test when not provided
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

"""
Example in case a custom OIDCAuthentication is needed for DRF:

class GvsigOIDCAuthentication(OIDCAuthentication):
    def __init__(self, backend=None):
        super().__init__(backend=backend)

    def authenticate(self, request):
        try:
            return super().authenticate(request)
        except Exception as e:
            LOGGER.exception('Error authenticating')
            print(e)
            raise
"""
