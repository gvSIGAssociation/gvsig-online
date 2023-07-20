from django.db import models
from django.utils.translation import ugettext as _
from gvsigol_auth import auth_backend
from django.contrib.auth.models import User

class ETLworkspaces(models.Model):

    name = models.CharField(max_length=250)
    description = models.CharField(max_length=500, null=True, blank=True)
    workspace = models.TextField()
    username = models.CharField(max_length=250)
    parameters = models.TextField(null=True, blank=True)
    concat = models.BooleanField(default=False)
    
    def __str__(self):
        return self.name

    def can_execute(self, request_or_user):
        """
        Checks whether the user can execute this workspace.

        Parameters
        ----------
        request_or_user: Request | HttpRequest | User
            A Django Request object | A DRF HttpRequest object | A Django User object

        Returns
        -------
        True if the user can execute this workspace, False otherwise
        """
        if isinstance(request_or_user, User):
            user = request_or_user
        else:
            user = request_or_user.user
        if user.is_superuser or (user.is_staff and user.username == self.username):
            return True
        user_roles = auth_backend.get_roles(request_or_user)
        return self.etlworkspaceexecuterole_set.filter(role__in=user_roles).exists()
    
    def can_edit(self, request_or_user):
        """
        Checks whether the user can edit this workspace.

        Parameters
        ----------
        request_or_user: Request | HttpRequest | User
            A Django Request object | A DRF HttpRequest object | A Django User object

        Returns
        -------
        True if the user can edit this workspace, False otherwise
        """
        if isinstance(request_or_user, User):
            user = request_or_user
        else:
            user = request_or_user.user
        if user.is_superuser or (user.is_staff and user.username == self.username):
            return True

        user_roles = auth_backend.get_roles(request_or_user)
        return self.etlworkspaceeditrole_set.filter(role__in=user_roles).exists()

class ETLstatus(models.Model):

    name = models.CharField(max_length=250)
    message = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=50, null=True, blank=True)
    id_ws = models.IntegerField(null=True, blank=True)
    
    def __str__(self):
        return self.name
    
class database_connections(models.Model):

    type = models.CharField(max_length=250)
    name = models.CharField(max_length=250, unique=True)
    connection_params = models.TextField()
    
    def __str__(self):
        return self.name


class segex_FechaFinGarantizada(models.Model):
    entity = models.CharField(max_length=250)
    type = models.IntegerField(null=False)
    fechafingarantizada = models.DateTimeField(auto_now_add=False, null=False)

    def __str__(self):
        return self.name

class cadastral_requests(models.Model):
    name = models.CharField(max_length=20, default='cadastral_requests')
    requests = models.IntegerField(null=False, default=0)
    lastRequest = models.DateTimeField(auto_now_add=True, null=False)

    def __str__(self):
        return self.name

class EtlWorkspaceExecuteRole(models.Model):
    etl_ws = models.ForeignKey(ETLworkspaces, on_delete=models.CASCADE)
    role = models.TextField()

    class Meta:
        indexes = [
            models.Index(fields=['etl_ws', 'role']),
        ]

class EtlWorkspaceEditRole(models.Model):
    etl_ws = models.ForeignKey(ETLworkspaces, on_delete=models.CASCADE)
    role = models.TextField()

    class Meta:
        indexes = [
            models.Index(fields=['etl_ws', 'role']),
        ]