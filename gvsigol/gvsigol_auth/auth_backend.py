import importlib
import logging
from gvsigol_auth.django_auth import get_primary_role
from gvsigol_auth import signals
from gvsigol_auth.models import UserCache, UserProperties
from django.contrib.auth import get_user_model
from gvsigol_auth.settings import USE_USER_CACHE

LOGGER_NAME = 'gvsigol'
try:
    from gvsigol import settings
    if settings.GVSIGOL_ROLE_PROVIDER == 'gvsigol_auth':
        import gvsigol_auth
        auth_backend = gvsigol_auth.django_auth
    else:
        auth_plugin = importlib.import_module(settings.GVSIGOL_ROLE_PROVIDER)
        auth_backend = importlib.import_module(settings.GVSIGOL_ROLE_PROVIDER + '.' + auth_plugin.backend_implementation)
except:
    logging.getLogger(LOGGER_NAME).exception('Error importing GVSIGOL_ROLE_PROVIDER. Falling back to gvsigol_auth.django_auth')
    auth_backend = importlib.import_module('gvsigol_auth.django_auth')

def role_deleted_handler(sender, **kwargs):
    try:
        for user_cache in UserCache.objects.filter(roles__contains=kwargs['role']):
            update_userrole_cache(user_cache)
    except Exception as e:
        logging.getLogger(LOGGER_NAME).exception('error updating user cache')
        pass

def user_updated_handler(sender, **kwargs):
    try:
        update_user_cache(
            kwargs['username'],
            user_dict=kwargs.get('user_dict'),
            user_obj=kwargs.get('user_obj'),
            roles=kwargs.get('roles'))
    except Exception as e:
        logging.getLogger(LOGGER_NAME).exception('error updating user cache')
        pass

def user_roles_updated_handler(sender, **kwargs):
    try:
        update_userrole_cache(kwargs['username'], kwargs.get('roles'))
    except Exception as e:
        logging.getLogger(LOGGER_NAME).exception('error updating user cache')
        pass

def user_deleted_handler(sender, **kwargs):
    try:
        UserCache.objects.filter(username=kwargs['username']).delete()
    except Exception as e:
        logging.getLogger(LOGGER_NAME).exception('error updating user cache')
        pass

def connect_signals():
    signals.role_deleted.connect(role_deleted_handler)
    signals.user_updated.connect(user_updated_handler)
    signals.user_roles_updated.connect(user_roles_updated_handler)
    signals.user_deleted.connect(user_deleted_handler)
connect_signals()

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

update_user = auth_backend.update_user
"""
Updates a user, identified by username. Only the provided attributes
will be updated.

Parameters
----------
username: str
    User name

[first_name]: str
    First name
[last_name]: str
    Last name
[superuser]: boolean
    Whether the user is superuser
[staff]: boolean
    Whether the user is staff
[groups]: [str]
    Groups to assign to the user. The provided groups will replace
    the existing user groups
[roles]: [str]
    Roles to assign to the user. The provided roles will replace
    the existing user roles
[password]: str
    The new password
Returns
-------
    User
    A Django User instance or None if an error happened
"""

delete_user  = auth_backend.delete_user
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
    A list of dictionaries containing the user details. Example:
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


get_filtered_users_details = auth_backend.get_filtered_users_details
"""
Gets the list of the users and details (id, username, first_name, last_name
is_superuser, is_staff, email, roles) available in the system, potentially filtered
and paginated.

Parameters
----------
exclude_system: boolean (default: False)
    Exclude system users, as defined by get_system_users()
search: string (default: None)
    Search string to filter returned results
first: integer
    Pagination offset
max:
    Maximum number of results returned
Returns
-------
dict()
    A dictionary containing the number of matched users, the number returned and the
        list of dictionaries containing the user details. Example:
        {
        "numberMatched": 20,
        "numberReturned": 2,
        "users: [
        {
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
        }
    ]
"""

get_user_details = auth_backend.get_user_details
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

get_admin_role = auth_backend.get_admin_role
"""
Gets the name of the admin role, that is, a role that is always
assigned to superusers.

Returns
-------
str
    The name of the admin role

See also
--------
auth_backend.to_provider_rolename()
auth_backend.from_provider_rolename()
"""
get_system_users = auth_backend.get_system_users
get_system_roles = auth_backend.get_system_roles
get_primary_role = auth_backend.get_primary_role
to_provider_rolename = auth_backend.to_provider_rolename
"""
Converts a role name to the equivalent role name
in the target provider namespace.

The name of the roles may differ between gvSIG Online and some
providers (for instance Geoserver) when some authentication backend
are enabled. For instance, when the authentication backend is
based in Django + LDAP, the gvSIG Online role "ug_test"
is mapped as "ROLE_UG_TEST" in Geoserver. This method performs this
mapping according to the enabled authentication backend.

Parameters
----------
role: str
    A role name in the gvSIG Online namespace
provider: str
    A provider name (e.g. "geoserver")

Returns
-------
str
    The name of role in the provider namespace

Examples
--------
auth_backend.to_provider_rolename("test", "geoserver")
(example responses: "test" or "ROLE_TEST")
auth_backend.to_provider_rolename("ug_test", "geoserver")
(example responses: "test" or "ROLE_TEST") "ug_test" or "ROLE_UG_TEST" dep)
"""

from_provider_rolename = auth_backend.from_provider_rolename
"""
Converts a role name from the provider namespace to the equivalent
role in the gvSIG Online namespace.

The name of the roles may differ between gvSIG Online and some
providers (for instance Geoserver) when some authentication backend
are enabled. For instance, when the authentication backend is
based in Django + LDAP, the gvSIG Online role "ug_test"
is mapped as "ROLE_UG_TEST" in Geoserver. This method performs this
mapping according to the enabled authentication backend.

Parameters
----------
role: str
    A role name in the provider namespace
provider: str
    A provider name (e.g. "geoserver")

Returns
-------
str
    The name of role in the gvSIG Online namespace

Examples
--------
auth_backend.from_provider_rolename("ROLE_TEST", "geoserver")
(example responses: "test" or "ROLE_TEST")
auth_backend.from_provider_rolename("ROLE_UG_TEST", "geoserver")
(example responses: "ug_test" or "ROLE_UG_TEST") "ug_test" or "ROLE_UG_TEST" dep)
"""

check_group_support = auth_backend.check_group_support
"""
Checks whether this backend provides support for user groups.
All the backends provide support for user roles, but only some
backends support user groups.
"""

def update_user_cache(username, user_dict=None, user_obj=None, roles=None):
    """
    Updates the user cache for allowing complex search.

    Parameters
    ----------
    user: str | User
        User name | Django User object
    """
    if user_obj is None:
        user_obj = _get_user_instance(username)
    
    if user_obj is not None: 
        try:
            try:
                user_props = user_obj.userproperties
            except UserProperties.DoesNotExist:
                user_props = UserProperties.objects.create(user=user_obj, editable=True)
            editable = user_props.editable
        except:
            editable = True
    else:
        editable = True
        

    if USE_USER_CACHE:
        try:
            if roles is None:
                roles = get_roles(username)
            roles_str = "; ".join(roles)

            if user_obj is not None:
                user_id = user_obj.id
                email = user_obj.email
                first_name = user_obj.first_name
                last_name = user_obj.last_name
                is_superuser = user_obj.is_superuser
                is_staff = user_obj.is_staff
            elif user_dict is not None:
                user_id = user_dict.get('id')
                email = user_dict.get('email')
                first_name = user_dict.get('first_name')
                last_name = user_dict.get('last_name')
                is_superuser = user_dict.get('is_superuser')
                is_staff = user_dict.get('is_staff')
            else:
                logging.getLogger(LOGGER_NAME).error(f'No user_obj or user_dict provided for user {username}')
                return
            try:
                user_cache = UserCache.objects.get(username=username)
                user_cache.user_id = user_id
                user_cache.email = email
                user_cache.first_name = first_name
                user_cache.last_name = last_name
                user_cache.is_superuser = is_superuser
                user_cache.is_staff = is_staff
                user_cache.roles = roles_str
                user_cache.editable = editable
                user_cache.save()
                user_cache.update_searchable_data()
            except UserCache.DoesNotExist:
                user_cache = UserCache.objects.create(user_id=user_id, username=username, email=email, first_name=first_name, last_name=last_name, is_superuser=is_superuser, is_staff=is_staff, roles=roles_str, editable=editable)
                user_cache.update_searchable_data()
        except:
            logging.getLogger(LOGGER_NAME).exception('error updating user cache')

def update_userrole_cache(user, roles=None):
    """
    Updates the roles of the user cache.

    Parameters
    ----------
    user: str | UserCache
    """
    try:
        if isinstance(user, UserCache):
            username = user.username
            if roles is None:
                roles = get_roles(username)
            user_cache = user
        elif isinstance(user, str):
            if roles is None:
                roles = get_roles(user)
            user_cache = UserCache.objects.get(username=user)
        roles_str = "; ".join(roles)
        user_cache.roles = roles_str
        user_cache.save()
        user_cache.update_searchable_data()
    except UserCache.DoesNotExist:
        pass
    except:
        logging.getLogger(LOGGER_NAME).exception('error updating user cache')

def _get_user_instance(user):
    """
    Gets the Django User instance from username or user id

    Parameters
    ----------
    user: str|integer|User
        User name|User id|Django User object
    Returns
    -------
        User
        A Django User instance or None if the user does not exist
    """
    try:
        User = get_user_model()
        if isinstance(user, User):
            return user
        elif isinstance(user, str):
            return User.objects.get(username=user)
        elif isinstance(user, int):
            return User.objects.get(id=user)
    except:
        pass

