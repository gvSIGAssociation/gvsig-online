import importlib

try:
    from gvsigol import settings
    if settings.GVSIGOL_AUTH_BACKEND == 'gvsigol_auth':
        import gvsigol_auth
        auth_backend = gvsigol_auth.django_auth
    else:
        auth_backend = importlib.import_module(settings.GVSIGOL_AUTH_BACKEND)
except:
    auth_backend = importlib.import_module('gvsigol_auth.django_auth')

has_group = auth_backend.has_group
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

has_role = auth_backend.has_role
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

get_groups = auth_backend.get_groups
"""
Gets the list of the groups available in the system.

Returns
-------
list[str]
    The list of groups available on the system
"""

get_roles  = auth_backend.get_roles
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

get_all_groups  = auth_backend.get_all_groups
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

get_all_groups_details  = auth_backend.get_all_groups_details
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

get_all_roles  = auth_backend.get_all_roles
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

get_all_roles_details  = auth_backend.get_all_roles_details
"""
Gets the list of the roles and details (id, name and description)
available in the system. Note that id can be an integer or a string
depending on the backend in use.

Returns
-------
list[dict()]
    A list of dictionaries containing the role details. Example:
    [{"id": 1, "name": "role_name1", "description": "bla bla bla"},
    {"id": 2, "name": "role_name2", "description": "bla bla bla"}]
"""

add_user  = auth_backend.add_user
delete_user  = auth_backend.delete_user
add_group  = auth_backend.add_group
delete_group  = auth_backend.delete_group
add_role  = auth_backend.add_role
delete_role  = auth_backend.delete_role
set_groups  = auth_backend.set_groups
set_roles  = auth_backend.set_roles
add_to_group  = auth_backend.add_to_group
remove_from_group  = auth_backend.remove_from_group
add_to_role  = auth_backend.add_to_role
remove_from_role  = auth_backend.remove_from_role
get_users_details = auth_backend.get_users_details
get_role_details = auth_backend.get_role_details

def get_admin_role():
    return 'admin'