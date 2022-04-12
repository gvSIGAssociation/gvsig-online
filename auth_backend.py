import importlib

from gvsigol_auth.django_auth import get_primary_role

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

delete_user  = auth_backend.delete_user
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

add_group  = auth_backend.add_group
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

delete_group  = auth_backend.delete_group
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

add_role  = auth_backend.add_role
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

delete_role  = auth_backend.delete_role
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

set_groups  = auth_backend.set_groups
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

set_roles  = auth_backend.set_roles
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

add_to_group  = auth_backend.add_to_group
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

remove_from_group  = auth_backend.remove_from_group
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

add_to_role  = auth_backend.add_to_role
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

remove_from_role  = auth_backend.remove_from_role
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

get_users_details = auth_backend.get_users_details
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

get_role_details = auth_backend.get_role_details
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

get_group_details = auth_backend.get_group_details
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

def get_admin_role():
    """
    Gets the name of the admin role, that is, a role that is always
    assigned to superusers.
    """
    return 'admin'

get_system_users = auth_backend.get_system_users
get_system_roles = auth_backend.get_system_roles
get_primary_role = auth_backend.get_primary_role
to_provider_rolename = auth_backend.to_provider_rolename
from_provider_rolename = auth_backend.from_provider_rolename