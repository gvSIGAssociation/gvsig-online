
import logging
from urllib.parse import urlencode
from django.urls import reverse
from gvsigol_plugin_oidc_mozilla.settings import OIDC_OP_LOGOUT_ENDPOINT

LOGGER = logging.getLogger(__name__)
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

def provider_logout(request):
    query_string = urlencode({
        "post_logout_redirect_uri": request.build_absolute_uri(reverse('index'))
    })
    url = "{}?{}".format(OIDC_OP_LOGOUT_ENDPOINT, query_string)
    print(url)
    return url

