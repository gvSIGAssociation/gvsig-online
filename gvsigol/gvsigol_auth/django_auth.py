from rest_framework.request import Request
from django.http import HttpRequest
from django.db.utils import IntegrityError
from django.contrib.auth import get_user_model
from gvsigol_auth.models import Role
import gvsigol_auth.services as auth_services
from gvsigol_auth import signals
import logging
LOGGER = logging.getLogger('gvsigol')

def check_group_support():
    return False

def get_admin_role():
    """
    Gets the name of the admin role, that is, a role that is always
    assigned to superusers.
    """
    return 'admin'

def get_system_users():
    # TODO parametrize?
    return ['root']

def get_system_roles():
    # TODO parametrize?
    return ['admin']

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
    if isinstance(request_or_user, str):
        return Role.objects.filter( \
            name=role, users__username=request_or_user).exists()
    if isinstance(request_or_user, HttpRequest):
        user = request_or_user.user
    else:
        user = request_or_user
    if user.is_authenticated:
        return Role.objects.filter(name=role, users=user).exists()
    return False

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
    return has_role(request_or_user, group)

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
    if isinstance(request_or_user, str):
        query = Role.objects.filter(users__username=request_or_user)
    else:
        if isinstance(request_or_user, HttpRequest) or isinstance(request_or_user, Request): # FIXME OIDC CMI desde DRF se puede pasar request._request?
            user = request_or_user.user
        else:
            user = request_or_user
        if user.is_authenticated:
            query =  Role.objects.filter(users=user)
        else:
            return []
    return list(query.values_list("name", flat=True))
    

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
    return get_roles(request_or_user)

def get_all_groups():
    """
    Gets the list of the groups available in the system.

    Returns
    -------
    list[str]
        The list of groups available on the system
    """
    return get_all_roles()

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
    return get_all_roles_details()

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
    if exclude_system:
        return list(Role.objects.all().exclude(name__in=get_system_roles()) \
            .values_list("name", flat=True))
    return list(Role.objects.all().values_list("name", flat=True))

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
    if exclude_system:
        return list(Role.objects.all().exclude(name__in=get_system_roles()).values())
    return list(Role.objects.all().values())

def add_user(username,
        password,
        email,
        first_name,
        last_name,
        groups=None,
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
    [groups]: [str]
        Groups to assign to the user. Ignored by this backend.
    [roles]: [str]
        Roles to assign to the user. It is ignored if not provided.
    [superuser]: boolean
        Whether the user is superuser (default: False)
    [staff]: boolean
        Whether the user is staff (default: False)
    Returns
    -------
        User
        A Django User instance
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
    if roles is not None:
        if superuser:
            roles.append(get_admin_role())
        set_roles(username, roles)
    return user

def update_user(
        username,
        email=None,
        first_name=None,
        last_name=None,
        superuser=None,
        staff=None,
        groups=None,
        roles=None,
        password=None):
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
    User = get_user_model()
    user = User.objects.get(id=int(user_id))
    user.first_name = first_name
    user.last_name = last_name
    user.email = email
    user.is_superuser = superuser
    user.is_staff = staff
    if password:
        user.set_password(password)
        auth_services.get_services().ldap_change_user_password(user, password)
    user.save()
    if roles is not None:
        set_roles(username, roles)
    if superuser:
        add_to_role(username, get_admin_role())
    return user

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

def delete_user(user=None, user_id=None):
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
    if user_id:
        User = get_user_model()
        user_instance = User.objects.get(id=user_id)
    else:
        user_instance = _get_user(user)

    # TODO improve error handling and op reversion    
    for role in get_roles(user_instance):
        if auth_services.get_services().ldap_delete_group_member(user_instance, role) == False:
            return False

    if auth_services.get_services().ldap_delete_default_group_member(user_instance) == False:
        return False
    # TODO improve error handling and op reversion    
    auth_services.get_services().ldap_delete_user(user_instance)
    user_instance.delete()
    return True

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
    add_role(group_name, desc=desc)

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
    return delete_role(group)

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
    if auth_services.get_services().ldap_add_group(role_name, desc) == False:
        return False

    try:
        role = Role(
            name = role_name,
            description = desc
        )
        role.save()
    except IntegrityError: # ignore if already exists
        pass
    return True

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
    if isinstance(role, str):
        role_instance = Role.objects.get(name=role)
    else:
        role_instance = Role.objects.get(id=role)
    # TODO improve error handling
    auth_services.get_services().ldap_delete_group(role_instance.name)
    auth_services.get_services().delete_data_directory(role_instance.name)
    role_instance.delete()
    signals.role_deleted.send(sender=None, role=role)
    return True


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
    return set_roles(user, groups)

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
    old_roles = set(get_roles(user))
    roles = set(roles)
    to_remove = old_roles - roles
    #TODO: improve error handling and op reversion
    success = True
    for role in to_remove:
        if not remove_from_role(user, role):
            success = False
    to_add = roles - old_roles
    for role in to_add:
        if not add_to_role(user, role):
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
    return add_to_role(user, group)

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
    return remove_from_role(user, group)

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
    user = _get_user(user)
    if auth_services.get_services(). \
            ldap_add_group_member(user, role, ignore_existing=True) == False:
        return False
    role = Role.objects.get(name=role)
    role.users.add(user)
    return True

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
    # FIXME OIDC CMI puede recibir un username o userid
    user = _get_user(user)
    if auth_services.get_services().ldap_delete_group_member(user, role) == False:
        return False
    role = Role.objects.get(name=role)
    role.users.remove(user)
    return True

def _get_user_representation(user):
    user_repr = {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_superuser": user.is_superuser,
        "is_staff": user.is_staff,
        "email": user.email
    }
    user_repr["roles"] = user.role_set.all().values_list('name', flat=True)
    return user_repr

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
    User = get_user_model()
    if exclude_system:
        base_query = User.objects.exclude(username__in=get_system_users())
    else:
        base_query = User.objects.all()
    user_list = base_query.prefetch_related('role_set')
    
    users = []
    for user in user_list:
        users.append(_get_user_representation(user))
    return users


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
    User = get_user_model()
    try:
        users = None
        if user_id:
            users = User.objects.filter(id=user_id).prefetch_related('role_set')
        elif isinstance(user, str):
            users = User.objects.filter(username=user).prefetch_related('role_set')
        if users and len(users) > 0:
            return _get_user_representation(users[0])
        return _get_user_representation(user)
    except User.DoesNotExist:
        LOGGER.exception('requests error getting users details')

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
    try:
        if isinstance(role, str):
            roles = Role.objects.filter(name=role)
        else:
            roles = Role.objects.filter(id=role)
        return roles.values()[0]
    except:
        return None

def get_group_details(group):
    return get_role_details(group)

def get_primary_role(username):
    return 'ug_' + username.lower()

def to_provider_rolename(role, provider=None):
    # only used for Geoserver at the moment, ignoring provider
    return 'ROLE_' + role.upper()

def from_provider_rolename(role, provider=None):
    # only used for Geoserver at the moment, ignoring provider
    return role[5:].lower()
    
