
import logging
from urllib.parse import urlencode
from django.urls import reverse
from django.contrib.auth import get_user_model
from gvsigol_plugin_oidc_mozilla.settings import OIDC_OP_LOGOUT_ENDPOINT
from gvsigol_plugin_oidc_mozilla.settings import KEYCLOAK_ADMIN_CLIENT_ID, KEYCLOAK_ADMIN_CLIENT_SECRET
from gvsigol_plugin_oidc_mozilla.settings import OIDC_OP_BASE_URL, OIDC_OP_REALM_NAME
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2.rfc6749.errors import InvalidClientIdError, TokenExpiredError, InvalidGrantError
try:
    import threading
except ImportError: # remove in python 3.7
    import dummy_threading as threading
LOGGER = logging.getLogger('gvsigol')


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
            r = self._get_session().get(url, params=params)
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
    
    def post(self, url, data, retry=True):
        try:
            r = self._get_session().post(url, data=data)
            if r.status_code == 401:
                self._create_session()
                return self.post(url, data, retry=False)
            return r
        except InvalidClientIdError as e:
            # No refresh token
            self._create_session()
            return self.post(url, data, retry=False)
        except TokenExpiredError as e:
            # (token_expired) cuando caduca access token y no se renueva
            self._create_session()
            return self.post(url, data, retry=False)
        except InvalidGrantError:
            # refresh token is expired (Keycloak session is expired)
            self._create_session()
            return self.post(url, data, retry=False)

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
        response = self.get(self.admin_url + '/groups').json()
        return list(self._flatten_groups(response))

    def get_all_groups_details(self):
        response = self.get(self.admin_url + '/groups', params={"briefRepresentation": False}).json()
        return list(self._flatten_group_details(response))

    def get_all_roles(self, exclude_system=False):
        # FIXME OIDC CMI exclude_system
        response = self.get(self.admin_url + '/roles').json()
        return [r.get('name') for r in response]

    def get_all_roles_details(self, exclude_system=False):
        # FIXME OIDC CMI exclude_system
        response = self.get(self.admin_url + '/roles').json()
        return [
            {
                'id': r.get('id'),
                'name': r.get('name'),
                'description': ''
            }
            for r in response
        ]

def _get_admIn_session():
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
    claims = request_or_user.session.get('oidc_access_token_payload', {})
    groups = claims.get('groups', [])
    return (group in groups)

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
    claims = request_or_user.session.get('oidc_access_token_payload', {})
    roles = claims.get('gvsigol_roles', [])
    return (role in roles)

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
    claims = request_or_user.session.get('oidc_access_token_payload', {})
    return claims.get('groups', [])

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
    claims = request_or_user.session.get('oidc_access_token_payload', {})
    return claims.get('gvsigol_roles', [])

def get_all_groups():
    """
    Gets the list of the groups available in the system.

    Returns
    -------
    list[str]
        The list of groups available on the system
    """
    return _get_admIn_session().get_all_groups()

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
    return _get_admIn_session().get_all_groups_details()

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
    return _get_admIn_session().get_all_roles(exclude_system=exclude_system)


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
    return _get_admIn_session().get_all_roles_details(exclude_system=exclude_system)

def add_user(username,
        password,
        email,
        first_name,
        last_name,
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
        A Django User instance
    """

    """
    # TODO: error handling
    auth_services.get_services().ldap_add_user(username, first_name, password, superuser)
    User = get_user_model()
    user = User(
        username = username,
        first_name = first_name,
        last_name = last_name,
        email = email,
        is_superuser = superuser,
        is_staff = staff
    )
    user.set_password(password)
    user.save()
    return user
    """
    pass

def _get_user(user):
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
    if isinstance(user, str):
        user_instance = User.objects.get(username=user)
    elif isinstance(user, int):
        user_instance = User.objects.get(id=user)
    else:
        user_instance = user
    return user_instance

def delete_user(user):
    """
    Deletes a user

    Parameters
    ----------
    user: str|integer|User
        User name|User id|Django User object
    
    Returns
    -------
        boolean
        True if the operation was successfull, False otherwise
    """
    user_instance = _get_user(user)

    pass

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
    pass

def delete_group(group):
    """
    Deletes a group

    Parameters
    ----------
    group: str|integer
        Group name|Group id
    
    Returns
    -------
        boolean
        True if the operation was successfull, False otherwise
    """
    pass

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
    pass

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
    pass


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
    user = _get_user(user)
    old_roles = get_roles(user)
    
    #TODO: improve error handling and op reversion
    for role in old_roles:
        if not remove_from_role(user, role.name):
            return False
    for role in roles:
        if not add_to_role(user, role):
            return False
    return True

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
    pass

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
    pass

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
    pass

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
    pass

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
    pass

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
    pass
