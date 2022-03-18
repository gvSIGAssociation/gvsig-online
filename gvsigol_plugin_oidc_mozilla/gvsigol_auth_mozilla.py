
import logging
from urllib.parse import urlencode
from django.urls import reverse
from gvsigol_plugin_oidc_mozilla.settings import OIDC_OP_LOGOUT_ENDPOINT

LOGGER = logging.getLogger(__name__)
def has_role(request, role):
    """Checks whether the user has the provided role.

    Note that roles and groups may be equivalent for some authentication
    backends.

    Parameters
    ----------
    request: HttpRequest
        Django request object
    role : str
        The role to check
    
    Returns
    -------
    boolean
        True if the user has the provided role, False otherwise
    """
    claims = request.session.get('oidc_access_token_payload', {})
    roles = claims.get('gvsigol_roles', [])
    return (role in roles)

def has_group(request, group):
    """Checks whether the user has the provided group.

    Note that roles and groups may be equivalent for some authentication
    backends.

    Parameters
    ----------
    request: HttpRequest
        Django request object
    group : str
        The group to check
    Returns
    -------
    boolean
        True if the user has the provided role, False otherwise
    """
    claims = request.session.get('oidc_access_token_payload', {})
    groups = claims.get('groups', [])
    return (group in groups)

def get_roles(request):
    """Gets the roles of the user.

    Note that roles and groups may be equivalent for some authentication
    backends.

    Parameters
    ----------
    request: HttpRequest
        Django request object
    Returns
    -------
    list[str]
        The list of roles of the user
    """
    claims = request.session.get('oidc_access_token_payload', {})
    return claims.get('gvsigol_roles', [])

def get_groups(request):
    """Gets the groups of the user.

    Note that roles and groups may be equivalent for some authentication
    backends.

    Parameters
    ----------
    request: HttpRequest
        Django request object
    Returns
    -------
    list[str]
        The list of groups of the user
    """
    claims = request.session.get('oidc_access_token_payload', {})
    return claims.get('groups', [])

def provider_logout(request):
    query_string = urlencode({
        "post_logout_redirect_uri": request.build_absolute_uri(reverse('index'))
    })
    url = "{}?{}".format(OIDC_OP_LOGOUT_ENDPOINT, query_string)
    print(url)
    return url

"""
GET /gvsigonline/auth/has-role/?role=rolename
returns {"response": true} or {"response": false} para el usuario actual
returns 401 si no está autenticado
returns 400 para otros errores (por ejemplo falta el parámetro role)

GET /gvsigonline/auth/has-role/?user=username&role=rolename
returns {"response": true} or {"response": false}
returns 401 si no está autenticado
returns 403 si no lo invoca un superusuario o username
returns 400 para otros errores (por ejemplo falta el parámetro role)

GET /gvsigonline/auth/has-group/?group=groupname
returns {"response": true} or {"response": false} para el usuario actual
returns 401 si no está autenticado
returns 400 para otros errores (por ejemplo falta el parámetro group)

GET /gvsigonline/auth/has-group/?user=username&group=groupname
returns {"response": true} or {"response": false}
returns 401 si no está autenticado
returns 403 si no lo invoca un superusuario o username
returns 400 para otros errores (por ejemplo falta el parámetro group)

GET /gvsigonline/auth/get-roles/
returns ["role1", "role2"] para el usuario actual
returns 401 si no está autenticado

GET /gvsigonline/auth/get-roles/?user=username
returns ["role1", "role2"]
returns 403 si no lo invoca un superusuario o username
returns 401 si no está autenticado

GET /gvsigonline/auth/get-groups/
returns ["group1", "group2"] para el usuario actual
returns 401 si no está autenticado

GET /gvsigonline/auth/get-groups/?user=username
returns ["group1", "group2"]
returns 403 si no lo invoca un superusuario o username
returns 401 si no está autenticado
"""