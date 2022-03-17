from gvsigol_auth.models import UserGroupUser, UserGroup

def has_role(request, role, user=None):
    """Checks whether the user has the provided role.

    Note that roles and groups may be equivalent for some authentication
    backends.

    Parameters
    ----------
    request: HttpRequest
        Django request object
    user : str | User
        The username or a User object instance
    role : str
        The role to check
    
    Returns
    -------
    boolean
        True if the user has the provided role, False otherwise
    """
    return has_group(request, role, user=user)

def has_group(request, group, user=None):
    """Checks whether the user has the provided group.

    Note that roles and groups may be equivalent for some authentication
    backends.

    Parameters
    ----------
    request: HttpRequest
        Django request object
    user : str | User
        The username or a User object instance
    group : str
        The group to check
    Returns
    -------
    boolean
        True if the user has the provided role, False otherwise
    """
    if isinstance(user, str):
        return UserGroupUser.objects.filter(user_group__name=group, user__username=user).exists()
    if user is None:
        user = request.user
    return UserGroupUser.objects.filter(user_group__name=group, user=user).exists()

def get_roles(request, user=None):
    """Gets the roles of the user.

    Note that roles and groups may be equivalent for some authentication
    backends.

    Parameters
    ----------
    request: HttpRequest
        Django request object
    user : str | User
        The username or a User object instance
    Returns
    -------
    list[str]
        The list of roles of the user
    """
    return get_groups(request, user=user)

def get_groups(request, user=None):
    """Gets the groups of the user.

    Note that roles and groups may be equivalent for some authentication
    backends.

    Parameters
    ----------
    request: HttpRequest
        Django request object
    user : str | User
        The username or a User object instance
    Returns
    -------
    list[str]
        The list of groups of the user
    """
    if isinstance(user, str):
        query = UserGroupUser.objects.filter(user__username=user)
    else:
        if user is None:
            user = request.user
        query =  UserGroupUser.objects.filter(user=user)
    return [ ugu.user_group.name for ugu in query]
