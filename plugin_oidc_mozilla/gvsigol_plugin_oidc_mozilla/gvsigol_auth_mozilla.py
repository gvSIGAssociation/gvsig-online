
import logging
from re import M
from this import d
from urllib.parse import urlencode
from django.urls import reverse
from django.db.utils import IntegrityError
from django.contrib.auth import get_user_model
from django.http import HttpRequest
from gvsigol.services_base import BackendNotAvailable
from gvsigol_plugin_oidc_mozilla.settings import OIDC_OP_LOGOUT_ENDPOINT
from gvsigol_plugin_oidc_mozilla.settings import KEYCLOAK_ADMIN_CLIENT_ID, KEYCLOAK_ADMIN_CLIENT_SECRET
from gvsigol_plugin_oidc_mozilla.settings import OIDC_OP_BASE_URL, OIDC_OP_REALM_NAME
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session
from requests.exceptions import RequestException, ConnectionError, Timeout, TooManyRedirects
from oauthlib.oauth2.rfc6749.errors import InvalidClientIdError, TokenExpiredError, InvalidGrantError
from gvsigol_auth import signals
try:
    import threading
except ImportError: # remove in python 3.7
    import dummy_threading as threading
LOGGER = logging.getLogger('gvsigol')
KEYCLOAK_TIMEOUT = 30


MAIN_SUPERUSER_ROLE = 'GVSIGOL_DJANGO_SUPERUSER'
STAFF_ROLE = 'GVSIGOL_DJANGO_STAFF'
SUPERUSER_ROLES = {MAIN_SUPERUSER_ROLE, 'ADMIN', 'ROLE_ADMIN'}

def get_admin_role():
    """
    Gets the name of the admin role, that is, a role that is always
    assigned to superusers.
    """
    return MAIN_SUPERUSER_ROLE

def get_system_users():
    # TODO parametrize?
    return {'root'}

def get_system_roles():
    # TODO parametrize?
    return SUPERUSER_ROLES | {STAFF_ROLE}

# we need to ensure that we get a different requests session for each
# thread, since requests is not thread safe
thread_local_data = threading.local()

def token_updater(new_token):
    s = getattr(thread_local_data, 'KC_ADMIN_SESSION', None)
    if s:
        s.token = new_token

def provider_logout(request):
    query_string = urlencode({
        "post_logout_redirect_uri": request.build_absolute_uri(reverse('index'))
    })
    url = "{}?{}".format(OIDC_OP_LOGOUT_ENDPOINT, query_string)
    print(url)
    return url



class OIDCSession():
    def __init__(self, client_id, client_secret, token_url, refresh_url=None) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = token_url
        if refresh_url:
            self.refresh_url = refresh_url
        else:
            self.refresh_url = token_url
        self.token = None
        self._session = None

    def _create_session(self):
        extra = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
        }
        client = BackendApplicationClient(client_id=self.client_id)
        self._session = OAuth2Session(
                client=client,
                token=self.token,
                auto_refresh_url=self.refresh_url,
                auto_refresh_kwargs=extra,
                token_updater=token_updater
                )
        self._session.fetch_token(
                token_url=self.token_url,
                client_id=self.client_id,
                client_secret=self.client_secret
                )
        return self._session
    
    def _get_session(self):
        if not self._session:
            return self._create_session()
        return self._session
    
    def get(self, url, params=None, retry=True):
        try:
            if not params:
                params = {}
            r = self._get_session().get(url, params=params, timeout=KEYCLOAK_TIMEOUT)
            if r.status_code == 401:
                self._create_session()
                return self.get(url, params=params, retry=False)
            return r
            
        except InvalidClientIdError as e:
            # No refresh token
            self._create_session()
            return self.get(url, params=params, retry=False)
        except TokenExpiredError as e:
            # (token_expired) cuando caduca access token y no se renueva
            self._create_session()
            return self.get(url, params=params, retry=False)
        except InvalidGrantError:
            # refresh token is expired (Keycloak session is expired)
            self._create_session()
            return self.get(url, params=params, retry=False)
    
    def post(self, url, data=None, json=None, retry=True):
        try:
            r = self._get_session().post(url, data=data, json=json, timeout=KEYCLOAK_TIMEOUT)
            if r.status_code == 401:
                self._create_session()
                return self.post(url, data=data, json=json, retry=False)
            return r
        except InvalidClientIdError as e:
            # No refresh token
            self._create_session()
            return self.post(url, data=data, json=json, retry=False)
        except TokenExpiredError as e:
            # (token_expired) cuando caduca access token y no se renueva
            self._create_session()
            return self.post(url, data=data, json=json, retry=False)
        except InvalidGrantError:
            # refresh token is expired (Keycloak session is expired)
            self._create_session()
            return self.post(url, data=data, json=json, retry=False)

    def put(self, url, data=None, json=None, retry=True):
        try:
            r = self._get_session().put(url, data=data, json=json, timeout=KEYCLOAK_TIMEOUT)
            if r.status_code == 401:
                self._create_session()
                return self.put(url, data=data, json=json, retry=False)
            return r
        except InvalidClientIdError as e:
            # No refresh token
            self._create_session()
            return self.put(url, data=data, json=json, retry=False)
        except TokenExpiredError as e:
            # (token_expired) cuando caduca access token y no se renueva
            self._create_session()
            return self.put(url, data=data, json=json, retry=False)
        except InvalidGrantError:
            # refresh token is expired (Keycloak session is expired)
            self._create_session()
            return self.put(url, data=data, json=json, retry=False)
    
    def delete(self, url,  data=None, json=None, retry=True):
        try:
            r = self._get_session().delete(url, data=data, json=json, timeout=KEYCLOAK_TIMEOUT)
            if r.status_code == 401:
                self._create_session()
                return self.delete(url, data=data, json=json, retry=False)
            return r
        except InvalidClientIdError as e:
            # No refresh token
            self._create_session()
            return self.delete(url, data=data, json=json, retry=False)
        except TokenExpiredError as e:
            # (token_expired) cuando caduca access token y no se renueva
            self._create_session()
            return self.delete(url, data=data, json=json, retry=False)
        except InvalidGrantError:
            # refresh token is expired (Keycloak session is expired)
            self._create_session()
            return self.delete(url, data=data, json=json, retry=False)

class KeycloakAdminSession(OIDCSession):
    def __init__(self, client_id, client_secret, base_url, realm) -> None:
        token_url = base_url + '/realms/' + realm + '/protocol/openid-connect/token'
        self.admin_url = base_url + '/admin/realms/' + realm
        super().__init__(client_id, client_secret, token_url)

    def _flatten_groups(self, group_list, subgroup=False):
        for g in group_list:
            if subgroup:
                # TODO OIDC CMI: decide how to deal with subgroups
                p = g.get('path')
                if p.startswith("/"):
                    yield p[1:]
                else:
                    yield p
            else:
                yield g.get('name')
            yield from self._flatten_groups(g.get('subGroups'), subgroup=True)

    def _get_user_name_from_id(self, user_id):
        repr = self.get_user_repr(user_id=user_id)
        if repr:
            return repr.get('username')
    
    def _get_group_details(self, g, subgroup=False):
        if subgroup:
            # TODO OIDC CMI: decide how to deal with subgroups
            p = g.get('path')
            if p.startswith("/"):
                name = p[1:]
            else:
                name = p
        else:
            name = g.get('name')
        return {
            'id': g.get('id'),
            'name': name,
            'description': g.get('attributes', {}).get('description', [''])[0]
        }

    def _flatten_group_details(self, group_list, subgroup=False):
        for g in group_list:
            yield self._get_group_details(g, subgroup=subgroup)
            yield from self._flatten_group_details(g.get('subGroups'), subgroup=True)

    def get_all_groups(self):
        try:
            response = self.get(self.admin_url + '/groups').json()
            return list(self._flatten_groups(response))
        except (ConnectionError, Timeout, TooManyRedirects) as e:
            raise BackendNotAvailable from e
        except RequestException:
            LOGGER.exception('requests error getting group')
        return []

    def get_all_groups_details(self):
        try:
            response = self.get(self.admin_url + '/groups', params={"briefRepresentation": False}).json()
            return list(self._flatten_group_details(response))
        except (ConnectionError, Timeout, TooManyRedirects) as e:
            raise BackendNotAvailable from e
        except RequestException:
            LOGGER.exception('requests error getting group')
        return []

    def get_all_roles(self, exclude_system=False):
        try:
            response = self.get(self.admin_url + '/roles').json()
            if exclude_system:
                system_roles = get_system_roles()
                return [r.get('name') for r in response if r.get('name') not in system_roles]
            return [r.get('name') for r in response]
        except (ConnectionError, Timeout, TooManyRedirects) as e:
            raise BackendNotAvailable from e
        except RequestException:
            LOGGER.exception('requests error getting roles')
        return []

    def get_all_roles_details(self, exclude_system=False):
        try:
            response = self.get(self.admin_url + '/roles').json()
            if exclude_system:
                system_roles = get_system_roles()
            else:
                system_roles = []
            return [
                {
                    'id': r.get('id'),
                    'name': r.get('name'),
                    'description': r.get('description', '')
                }
                for r in response if r.get('name') not in system_roles
            ]
        except (ConnectionError, Timeout, TooManyRedirects) as e:
            raise BackendNotAvailable from e
        except RequestException:
            LOGGER.exception('requests error getting roles')
        return []

    def add_user(self,
            username,
            password,
            email,
            first_name,
            last_name,
            roles=None,
            superuser=False,
            staff=False):
        try:
            if roles is None:
                roles = set()
            else:
                roles = set(roles) # remove duplicates
            if superuser:
                realm_roles = SUPERUSER_ROLES | {STAFF_ROLE} | roles
            elif staff:
                realm_roles = {STAFF_ROLE} | roles - SUPERUSER_ROLES
            else:
                realm_roles = roles - SUPERUSER_ROLES - {STAFF_ROLE}
            user_rep = {
                "credentials": [{"value": password}],
                "email": email,
                "enabled": True,
                "firstName": first_name,
                "lastName": last_name,
                "username": username
            }
            response = self.post(self.admin_url + '/users', json=user_rep)
            if response.status_code == 201:
                set_roles(username, list(realm_roles))
                User = get_user_model()
                try:
                    user = User(
                        username=username,
                        email=email,
                        password=password,
                        first_name=first_name,
                        last_name=last_name,
                        is_superuser=superuser,
                        is_staff=staff)
                    user.save()
                except IntegrityError:
                    # accept users already existing in Django to allow creating the user in Keycloak
                    LOGGER.exception('error creating user in django after keycloak creation')
                    user = User.objects.get(username=username)
                return user
        except (ConnectionError, Timeout, TooManyRedirects) as e:
            raise BackendNotAvailable from e
        except RequestException:
            LOGGER.exception('requests error adding user')

    def update_user(self,
            user_id,
            username,
            email,
            first_name,
            last_name,
            superuser,
            staff,
            roles=None,
            password=None):
        try:
            user_rep = {
                "email": email,
                "firstName": first_name,
                "lastName": last_name,
                "id": user_id
            }
            if password:
                user_rep["credentials"] =  [{"value": password}]
            url = "{base_url}/users/{user_id}".format(base_url=self.admin_url, user_id=user_id)
            response = self.put(url, json=user_rep)
            if response.status_code == 204:
                User = get_user_model()
                
                try:
                    user = User.objects.get(username=username)
                    user.first_name = first_name
                    user.last_name = last_name
                    user.email = email
                    user.is_staff = staff
                    user.is_superuser = superuser
                    if password:
                        user.set_password(password)
                    user.save()
                except User.DoesNotExist:
                    # accept non-existing Django users to allow updating users created in Keycloak
                    pass
                if roles is None:
                    roles = set()
                else:
                    roles = set(roles) # remove duplicates
                if superuser:
                    realm_roles = SUPERUSER_ROLES | {STAFF_ROLE} | roles
                elif staff:
                    realm_roles = {STAFF_ROLE} | roles - SUPERUSER_ROLES
                else:
                    realm_roles = roles - SUPERUSER_ROLES - {STAFF_ROLE}

                
                set_roles(username, list(realm_roles))
                """
                if superuser:
                    # ensure roles
                    for role in ["ADMIN", MAIN_SUPERUSER_ROLE, STAFF_ROLE]:
                        self.add_to_role(username, role)
                if staff:
                    self.add_to_role(username, STAFF_ROLE)
                """
                return True
        except (ConnectionError, Timeout, TooManyRedirects) as e:
            raise BackendNotAvailable from e
        except RequestException:
            LOGGER.exception('requests error adding user')

    def get_user_id(self, username):
        response = self.get(self.admin_url + '/users', params={"username": username, "exact": True})
        if response.status_code == 200:
            user_list = response.json()
            if len(user_list) > 0:
                return user_list[0].get('id')

    def _get_user_role_mappings_realm_composite(self, user_id):
        url = "{base_url}/users/{user_id}/role-mappings/realm/composite".format(base_url=self.admin_url, user_id=user_id)
        response = self.get(url)
        if response.status_code == 200:
            return response.json()

    def _get_user_role_mappings(self, user_id):
        url = "{base_url}/users/{user_id}/role-mappings".format(base_url=self.admin_url, user_id=user_id)
        response = self.get(url)
        if response.status_code == 200:
            return response.json()

    def get_group_id(self, group_name):
        response = self.get(self.admin_url + '/groups', params={"search": group_name}).json()
        if len(response) > 0:
            return response[0].get('id')

    def get_role_id(self, role_name):
        role_repr = self._get_role_repr(role_name)
        return role_repr.get('id')

    def delete_user(self, user=None, user_id=None):
        try:
            if not user_id:
                username = _get_user_name(user)
                user_id = self.get_user_id(username)
            else:
                username = self._get_user_name_from_id(user_id)
            url = "{base}/users/{id}".format(base=self.admin_url, id=user_id)
            response = self.delete(url)
            if response.status_code == 204:
                try:
                    User = get_user_model()
                    User.objects.get(username=username).delete()
                except User.DoesNotExist:
                    # ignore to allow deleting keycloak users that have not been localy created in Django
                    pass
                return True
        except (ConnectionError, Timeout, TooManyRedirects) as e:
            raise BackendNotAvailable from e
        except RequestException:
            LOGGER.exception('requests error deleting user')
        return False

    def add_group(self, group_name, desc=''):
        try:
            group_rep = {
                "attributes": {"description": [desc]},
                "name": group_name
            }
            response = self.post(self.admin_url + '/groups', json=group_rep)
            if response.status_code == 201:
                return True
        except (ConnectionError, Timeout, TooManyRedirects) as e:
            raise BackendNotAvailable from e
        except RequestException:
            LOGGER.exception('requests error adding group')
        return False

    def add_role(self, role_name, desc=''):
        try:
            role_rep = {
                "description": desc,
                "name": role_name
            }
            response = self.post(self.admin_url + '/roles', json=role_rep)
            if response.status_code == 201:
                return True
            LOGGER.error('requests error adding role. Status code: {}'.format(response.status_code))
        except (ConnectionError, Timeout, TooManyRedirects) as e:
            raise BackendNotAvailable from e
        except RequestException:
            LOGGER.exception('requests error adding role')
        return False

    def delete_group(self, group_name):
        try:
            group_id = self.get_group_id(group_name)
            url = "{base}/groups/{id}".format(base=self.admin_url, id=group_id)
            response = self.delete(url)
            if response.status_code == 204:
                return True
        except (ConnectionError, Timeout, TooManyRedirects) as e:
            raise BackendNotAvailable from e
        except RequestException:
            LOGGER.exception('requests error deleting group')
        return False

    def delete_role(self, role_name):
        try:
            url = "{base}/roles/{role_name}".format(base=self.admin_url, role_name=role_name)
            response = self.delete(url)
            if response.status_code == 204:
                return True
        except (ConnectionError, Timeout, TooManyRedirects) as e:
            raise BackendNotAvailable from e
        except RequestException:
            LOGGER.exception('requests error deleting role')
        return False

    def add_to_role(self, username, role_name):
        try:
            user_id = self.get_user_id(username)
            # TODO: we could handle client roles too
            url = "{base}/users/{user_id}/role-mappings/realm".format(base=self.admin_url, user_id=user_id)
            body = [{
                "id": self.get_role_id(role_name),
                "name": role_name
            }]
            response = self.post(url, json=body)
            if response.status_code == 204:
                return True
        except (ConnectionError, Timeout, TooManyRedirects) as e:
            raise BackendNotAvailable from e
        except RequestException:
            LOGGER.exception('requests error adding user to role')
        return False

    def remove_from_role(self, username, role_name):
        try:
            user_id = self.get_user_id(username)
            # TODO: we could handle client roles too
            url = "{base}/users/{user_id}/role-mappings/realm".format(base=self.admin_url, user_id=user_id)
            body = [{
                "id": self.get_role_id(role_name),
                "name": role_name
            }]
            response = self.delete(url, json=body)
            if response.status_code == 204:
                return True
        except (ConnectionError, Timeout, TooManyRedirects) as e:
            raise BackendNotAvailable from e
        except RequestException:
            LOGGER.exception('requests error removing user to role')
        return False

    def add_to_group(self, username, group_name):
        try:
            user_id = self.get_user_id(username)
            group_id = self.get_group_id(group_name)
            url = "{base}/users/{user_id}/groups/{group_id}".format(base=self.admin_url, user_id=user_id, group_id=group_id)
            response = self.put(url)
            if response.status_code == 204:
                return True
        except RequestException as e:
            LOGGER.exception('requests error adding user to role')
            print(str(e))
        return False

    def remove_from_group(self, username, group_name):
        try:
            user_id = self.get_user_id(username)
            group_id = self.get_group_id(group_name)
            url = "{base}/users/{user_id}/groups/{group_id}".format(base=self.admin_url, user_id=user_id, group_id=group_id)
            response = self.delete(url)
            if response.status_code == 204:
                return True
        except (ConnectionError, Timeout, TooManyRedirects) as e:
            raise BackendNotAvailable from e
        except RequestException:
            LOGGER.exception('requests error adding user to role')
        return False

    def _get_role_repr(self, role_name):
        url = "{base_url}/roles/{role_name}".format(base_url=self.admin_url, role_name=role_name)
        response = self.get(url)
        if response.status_code == 200:
            return response.json()

    def _get_group_repr(self, group_name):
        group_id = self.get_group_id(group_name)
        url = "{base_url}/groups/{group_id}".format(base_url=self.admin_url, group_id=group_id)
        response = self.get(url)
        if response.status_code == 200:
            return response.json()

    def get_group_details(self, group_name):
        try:
            group_repr = self._get_group_repr(group_name)
            if group_repr:
                desc = group_repr.get('attributes', {}).get('description', [''])[0]
                return {
                    "id": group_repr.get('name'),
                    "name": group_repr.get('name'),
                    "description": desc
                }
        except (ConnectionError, Timeout, TooManyRedirects) as e:
            raise BackendNotAvailable from e
        except RequestException:
            LOGGER.exception('requests error getting group details')

    def get_role_details(self, role_name):
        try:
            role_repr = self._get_role_repr(role_name)
            if role_repr:
                return {
                    "id": role_repr.get('name'),
                    "name": role_repr.get('name'),
                    "description": role_repr.get('description'),
                }
        except (ConnectionError, Timeout, TooManyRedirects) as e:
            raise BackendNotAvailable from e
        except RequestException:
            LOGGER.exception('requests error adding user to role')

    def get_user_repr(self, user_id):
        url = '{base_url}/users/{user_id}'.format(base_url=self.admin_url, user_id=user_id)
        response = self.get(url)
        if response.status_code == 200:
            return response.json()

    def _get_user_roles(self, user_id):
        # FIXME: we could also include client mappings
        role_mappings = self._get_user_role_mappings_realm_composite(user_id)
        return [r.get('name') for r in role_mappings]
    
    def get_roles(self, username):
        user_id = self.get_user_id(username)
        if user_id:
            return self._get_user_roles(user_id)
        return []

    def get_groups(self, username):
        try:
            user_id = self.get_user_id(username)
            url = "{base}/users/{user_id}/groups".format(base=self.admin_url, user_id=user_id)
            response = self.get(url)
            if response.status_code == 200:
                return [ g.get('name') for g in response.json() ]
        except RequestException as e:
            LOGGER.exception('requests error adding user to role')
        return []
        
    def get_users_details(self, exclude_system=False):
        users = []
        try:
            response = self.get(self.admin_url + '/users', params={"briefRepresentation": True})
            if response.status_code == 200:
                if exclude_system:
                    system_users = get_system_users()
                else:
                    system_users = []
                for user in response.json():
                    if user.get('username') not in system_users:
                        user_id = user.get('id')
                        roles = self._get_user_roles(user_id)
                        users.append({
                            "id": user.get('id'),
                            "username": user.get('username'),
                            "first_name": user.get('firstName', ''),
                            "last_name": user.get('lastName', ''),
                            "is_superuser": MAIN_SUPERUSER_ROLE in roles,
                            "is_staff": STAFF_ROLE in roles,
                            "email": user.get('email'),
                            "roles": roles
                        })
        except (ConnectionError, Timeout, TooManyRedirects) as e:
            raise BackendNotAvailable from e
        except RequestException:
            LOGGER.exception('requests error getting users details')
        return users

    def _get_user_details(self, user_id):
        user_repr = self.get_user_repr(user_id)
        if user_repr:
            roles = self._get_user_roles(user_id)
            return {
                "id": user_repr.get('id'),
                "username": user_repr.get('username'),
                "first_name": user_repr.get('firstName', ''),
                "last_name": user_repr.get('lastName', ''),
                "is_superuser": MAIN_SUPERUSER_ROLE in roles,
                "is_staff": STAFF_ROLE in roles,
                "email": user_repr.get('email'),
                "roles": roles
            }

    def get_user_details(self, user=None, user_id=None):
        try:
            if not user_id:
                username = _get_user_name(user)
                user_id = self.get_user_id(username)
            return self._get_user_details(user_id)
        except (ConnectionError, Timeout, TooManyRedirects) as e:
            raise BackendNotAvailable from e
        except RequestException:
            LOGGER.exception('requests error getting users details')


def _get_admin_session():
    s = getattr(thread_local_data, 'KC_ADMIN_SESSION', None)
    if s:
        return s
    thread_local_data.KC_ADMIN_SESSION = KeycloakAdminSession(KEYCLOAK_ADMIN_CLIENT_ID, KEYCLOAK_ADMIN_CLIENT_SECRET, OIDC_OP_BASE_URL, OIDC_OP_REALM_NAME)
    return thread_local_data.KC_ADMIN_SESSION

def has_group(request_or_user, group):
    """Checks whether the user has the provided group. Important: provide a
    Django HttpRequest object to check the groups from the user logged in
    the request session. Only provide a User object to check the groups of
    non logged in users.


    Note that roles and groups may be equivalent for some authentication
    backends.

    Parameters
    ----------
    request_or_user: HttpRequest|User|str
        Django request object (preferred to check the groups of the logged
        in user) | Django user object instance or username string (to check
        the groups of non logged in users)
    group : str
        The group to check
    Returns
    -------
    boolean
        True if the user has the provided group, False otherwise
    """
    return (group in get_groups(request_or_user))

def has_role(request_or_user, role):
    """Checks whether a user has the provided role. Important: provide a
    Django HttpRequest object to check the roles from the user logged in
    the request session. Only provide a User object to check the roles of
    non logged in users.

    Note that roles and groups may be equivalent for some authentication
    backends.

    Parameters
    ----------
    request_or_user: HttpRequest|User|str
        Django request object (preferred to check the roles of the logged
        in user) | Django user object instance or username string (to check
        the roles of non logged in users)
    role : str
        The role to check
    
    Returns
    -------
    boolean
        True if the user has the provided role, False otherwise
    """
    return (role in get_roles(request_or_user))

def get_groups(request_or_user):
    """Gets the groups of the user. Important: provide a Django HttpRequest
    object to get the groups from the user logged in the request session.
    Only provide a User object to get the groups of non logged in users.

    Note that roles and groups may be equivalent for some authentication
    backends.

    Parameters
    ----------
    request_or_user: HttpRequest|User|str
        Django request object (preferred to get the groups of the logged
        in user) | Django user object instance or username string (to get
        the groups of non logged in users)
    Returns
    -------
    list[str]
        The list of groups of the user
    """
    if isinstance(request_or_user, HttpRequest):
        claims = request_or_user.session.get('oidc_access_token_payload', {})
        return claims.get('groups', [])
    User = get_user_model()
    if isinstance(request_or_user, str):
        username = request_or_user
    else:
        if request_or_user.is_authenticated:
            username = request_or_user.username
        else:
            return []
    return _get_admin_session().get_groups(username)

def get_roles(request_or_user):
    """Gets the roles of the user. Important: provide a Django HttpRequest
    object to get the roles from the user logged in the request session.
    Only provide a User object to get the roles of non logged in users.

    Note that roles and groups may be equivalent for some authentication
    backends.

    Parameters
    ----------
    request_or_user: HttpRequest | User | str
        Django request object (preferred to get the roles of the logged
        in user) | Django user object instance or username string (to check
        the roles of non logged in users)
    Returns
    -------
    list[str]
        The list of roles of the user
    """
    if isinstance(request_or_user, HttpRequest):
        claims = request_or_user.session.get('oidc_access_token_payload', {})
        return claims.get('gvsigol_roles', [])
    User = get_user_model()
    if isinstance(request_or_user, str):
        username = request_or_user
    else:
        if request_or_user.is_authenticated:
            username = request_or_user.username
        else:
            return []
    return _get_admin_session().get_roles(username)

def get_all_groups():
    """
    Gets the list of the groups available in the system.

    Returns
    -------
    list[str]
        The list of groups available on the system
    """
    return _get_admin_session().get_all_groups()

def get_all_groups_details():
    """
    Gets the list of the groups and details (id, name and description)
    available in the system. Note that id can be an integer or a string
    depending on the backend in use.

    Returns
    -------
    list[dict()]
        A list of dictionaries containing the group details. Example:
        [{"id": 1, "name": "group_name1", "description": "bla bla bla"},
        {"id": 2, "name": "group_name2", "description": "bla bla bla"}]
    """
    return _get_admin_session().get_all_groups_details()

def get_all_roles(exclude_system=False):
    """
    Gets the list of roles available on the system.

    Parameters
    ----------
    exclude_system: boolean (default: False)
        Exclude system roles, as defined by get_system_roles()

    Returns
    -------
    list[str]
        The list of roles available on the system
    """
    return _get_admin_session().get_all_roles(exclude_system=exclude_system)


def get_all_roles_details(exclude_system=False):
    """
    Gets the list of the roles and details (id, name and description)
    available in the system. Note that id can be an integer or a string
    depending on the backend in use.

    Parameters
    ----------
    exclude_system: boolean (default: False)
        Exclude system roles, as defined by get_system_roles()

    Returns
    -------
    list[dict()]
        A list of dictionaries containing the role details. Example:
        [{"id": 1, "name": "role_name1", "description": "bla bla bla"},
        {"id": 2, "name": "role_name2", "description": "bla bla bla"}]
    """
    return _get_admin_session().get_all_roles_details(exclude_system=exclude_system)

def add_user(username,
        password,
        email,
        first_name,
        last_name,
        roles=None,
        superuser=False,
        staff=False):
    """
    Adds a user

    Parameters
    ----------
    username: str
        User name
    password: str
        Password
    first_name: str
        First name
    last_name: str
        Last name
    [superuser]: boolean
        Whether the user is superuser (default: False)
    [staff]: boolean
        Whether the user is staff (default: False)
    Returns
    -------
        User
        A Django User instance or None if an error happened
    """
    return _get_admin_session().add_user(username, password, email, first_name, last_name, roles=roles, superuser=superuser, staff=staff)

def _get_user_name(user):
    """
    Gets the Django User instance from username or user id

    Parameters
    ----------
    user: str|integer|User
        User name|User id|Django User object
    Returns
    -------
        User
        A Django User instance
    """
    User = get_user_model()
    if isinstance(user, User):
        return user.username
    elif isinstance(user, str):
        return user
    elif isinstance(user, int):
        return User.objects.get(id=user).username

def update_user(user_id,
            username,
            email,
            first_name,
            last_name,
            superuser,
            staff,
            roles=None,
            password=None):

    return _get_admin_session().update_user(user_id,
            username,
            email,
            first_name,
            last_name,
            superuser=superuser,
            staff=staff,
            roles=roles,
            password=password)

def delete_user(user=None, user_id=None):
    """
    Deletes a user

    Parameters
    ----------
    user: str | User
        User name | Django User object
    user_id: str | integer
        The user identifier. When 'user_id' is provided, then the 'user' parameter is ignored.
        Note that user_id can be a string or an integer depending on the auth backend implementation.
    
    Returns
    -------
        boolean
        True if the operation was successfull, False otherwise
    """
    return _get_admin_session().delete_user(user=user, user_id=user_id)

def add_group(group_name, desc=''):
    """
    Adds a group
    
    Parameters
    ----------
    group_name: str
        Group name
    [desc]: str
        Group description
    
    Returns
    -------
        boolean
        True if the operation was successfull, False otherwise
    """
    return _get_admin_session().add_group(group_name, desc=desc)

def delete_group(group):
    """
    Deletes a group

    Parameters
    ----------
    group: str
        Group name
    
    Returns
    -------
        boolean
        True if the operation was successfull, False otherwise
    """
    return _get_admin_session().delete_group(group)

def add_role(role_name, desc=''):
    """
    Adds a role
    
    Parameters
    ----------
    role_name: str
        Role name
    [desc]: str
        Role description
    
    Returns
    -------
        boolean
        True if the operation was successfull, False otherwise
    """
    return _get_admin_session().add_role(role_name, desc=desc)


def delete_role(role):
    """
    Deletes a role

    Parameters
    ----------
    role: str|integer
        Role name|Role id

    Returns
    -------
        boolean
        True if the operation was successfull, False otherwise
    """

    if _get_admin_session().delete_role(role):
        signals.role_deleted.send(sender=None, role=role)
        return True
    return False

def set_groups(user, groups):
    """
    Sets the groups of a user, replacing existing groups

    Parameters
    ----------
    user: str|integer|User
        User name|User id|Django User object
    roles: [str]
        List of roles

    Returns
    -------
        boolean
        True if the operation was successfull, False otherwise
    """
    pass

def set_roles(user, roles):
    """
    Sets the roles of a user, replacing existing roles

    Parameters
    ----------
    user: str|integer|User
        User name|User id|Django User object
    roles: [str]
        List of roles

    Returns
    -------
        boolean
        True if the operation was successfull, False otherwise
    """
    username = _get_user_name(user)
    old_roles = set(get_roles(username))
    roles = set(roles)
    to_remove = old_roles - roles
    #TODO: improve error handling and op reversion
    success = True
    for role in to_remove:
        if not remove_from_role(username, role):
            success = False
    to_add = roles - old_roles
    for role in to_add:
        if not add_to_role(username, role):
            success = False
    return success

def add_to_group(user, group):
    """
    Adds a user to a group

    Parameters
    ----------
    user: str|integer|User
        User name|User id|Django User object
    group: str
        Group name

    Returns
    -------
        boolean
        True if the operation was successfull, False otherwise
    """
    username = _get_user_name(user)
    if _get_admin_session().add_to_group(username, group):
        return True
    return False

def remove_from_group(user, group):
    """
    Remove a user from a group

    Parameters
    ----------
    user: str|integer|User
        User name|User id|Django User object
    group: str
        Group name

    Returns
    -------
        boolean
        True if the operation was successfull, False otherwise
    """
    username = _get_user_name(user)
    if _get_admin_session().remove_from_group(username, group):
        return True
    return False

def add_to_role(user, role):
    """
    Adds a role to the list of assigned roles of a user

    Parameters
    ----------
    user: str|integer|User
        User name|User id|Django User object
    role: str
        Role name

    Returns
    -------
        boolean
        True if the operation was successfull, False otherwise
    """
    username = _get_user_name(user)
    if _get_admin_session().add_to_role(username, role):
        return True
    return False

def remove_from_role(user, role):
    """
    Remove a role from the list of assigned roles of the user

    Parameters
    ----------
    user: str|integer|User
        User name|User id|Django User object
    role: str
        Role name

    Returns
    -------
        boolean
        True if the operation was successfull, False otherwise
    """
    username = _get_user_name(user)
    if _get_admin_session().remove_from_role(username, role):
        return True
    return False

def get_users_details(exclude_system=False):
    """
    Gets the list of the users and details (id, username, first_name, last_name
    is_superuser, is_staff, email, roles) available in the system.

    Parameters
    ----------
    exclude_system: boolean (default: False)
        Exclude system users, as defined by get_system_users()

    Returns
    -------
    list[dict()]
        A list of dictionaries containing the group details. Example:
        [{
            "id": 1,
            "username": "username1",
            "first_name": "Firstname1",
            "last_name": "Lastname1",
            "is_superuser": True,
            "is_staff": True,
            "email": "example1@example.com",
            roles": ["role1", "role2"]},
        },
        {
            "id": 2,
            "username": "username2",
            "first_name": "Firstname2",
            "last_name": "Lastname2",
            "is_superuser": False,
            "is_staff": True,
            "email": "example2@example.com",
            roles": ["role2", "role3"]},
        }]
    """
    return _get_admin_session().get_users_details(exclude_system=exclude_system)

def get_user_details(user=None, user_id=None):
    """
    Gets a dictionary of user attributes (id, username, first_name, last_name
    is_superuser, is_staff, email, roles) available in the system. The

    Parameters
    ----------
    user: str | User
        User name|Django User object
    user_id: str | int
        The user identifier. When 'user_id' is provided, then the 'user' parameter is ignored.
        Note that user_id can be a string or an integer depending on the auth backend implementation.

    Returns
    -------
    dict()
        A dictionary containing the user attributes or None if an invalid user is provided. Example:
        {
            "id": 1,
            "username": "username1",
            "first_name": "Firstname1",
            "last_name": "Lastname1",
            "is_superuser": True,
            "is_staff": True,
            "email": "example1@example.com",
            roles": ["role1", "role2"]},
        }
    """
    return _get_admin_session().get_user_details(user=user, user_id=user_id)

def get_role_details(role):
    """
    Gets a dictionary of role details (id, name and description).
    Note that id can be an integer or a string
    depending on the backend in use.

    Parameters
    ----------
    role: str | int
        A role name | A role id

    Returns
    -------
    dict()
        A dictionary containing the role details. Example:
        {"id": 1, "name": "role_name1", "description": "bla bla bla"}
    """
    return _get_admin_session().get_role_details(role)

def get_group_details(group):
    """
    Gets a dictionary of group details (id, name and description).
    Note that id can be an integer or a string
    depending on the backend in use.

    Parameters
    ----------
    group: str | int
        A group name | A group id

    Returns
    -------
    dict()
        A dictionary containing the group details. Example:
        {"id": 1, "name": "group_name1", "description": "bla bla bla"}
    """
    return _get_admin_session().get_group_details(group)

def get_primary_role(username):
    return 'ROLE_UG_' + username.upper()

def to_provider_rolename(role, provider=None):
    # only used for Geoserver at the moment, ignoring provider
    return role

def from_provider_rolename(role, provider=None):
    # only used for Geoserver at the moment, ignoring provider
    return role