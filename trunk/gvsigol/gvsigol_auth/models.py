
# -*- coding: utf-8 -*-

'''
    gvSIG Online.
    Copyright (C) 2010-2017 SCOLAB.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''
'''
@author: Javier Rodrigo <jrodrigo@scolab.es>
'''
from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.db.models import F, Func

class UserGroup(models.Model):
    name = models.CharField(max_length=250, unique=True)
    description = models.CharField(max_length=500, null=True, blank=True)
    
    def __str__(self):
        return self.name
    
    
class UserGroupUser(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    user_group = models.ForeignKey(UserGroup, on_delete=models.CASCADE)
    
    def __str__(self):
        return self.user.email + ' - ' + self.user_group.name

class Role(models.Model):
    name = models.CharField(max_length=250, unique=True)
    description = models.CharField(max_length=500, null=True, blank=True)
    users  = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True
    )
    """
    At the moment, the editable flag is only used in LIBRA for roles managed
    by GVCLAU sync scripts.
    """
    editable = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name

class UserProperties(models.Model):
    """
    User properties will be created when the user is created.
    In most environments, the editable flag will be set to True.
    When using GVLOGIN auth (GVA environments), editable will be set to False for
    GVLOGIN users (by GVLOGIN/GVCLAU sync scripts) and it will be set as True for
    local users (directly created in the Django User model for LIBRA apps such as
    VINYA, etc).

    For users created directly in Keycloak, GVLOGIN, etc., the UserProperties object
    will be created the first time the user logs in gvSIG Online.
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    editable = models.BooleanField(default=True)
    """
    Whether the user can be edited from gvSIG Online, or it is externally managed (e.g. Keycloak, GVLOGIN, etc.)
    and it is read-only. Read-only users will not be able to be edited from gvSIG Online at all.
    This is different from setting the AUTH_READONLY_USERS variable to True, which will not allow
    modifying user date but it will make possible to edit user's roles and groups, and superuser and staff flags.
    """


class Unaccent(Func):
    function = "unaccent"

class UserCache(models.Model):
    """
    Cache of user information for allowing complex search. The cache may also store remote users
    not available as Django User instances (e.g. users created directly in Keycloak).
    """
    user_id = models.TextField(unique=True)
    searchable_text = models.TextField(blank=True)
    searchable_data = models.TextField(blank=True)
    username = models.TextField(unique=True)
    first_name = models.TextField(blank=True)
    last_name = models.TextField(blank=True)
    email = models.EmailField(blank=True)
    is_superuser = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    roles = models.TextField(blank=True)
    editable = models.BooleanField(default=True)
    """
    GinIndex is created using a custom migration to use trigram if available.
    class Meta:
        indexes = (GinIndex(fields=["searchable_data"]),)
    """

    def update_searchable_data(self):
        """
        Updates the searchable data for the user
        """
        self.searchable_text = f"{self.username} {self.first_name} {self.last_name} {self.email} {self.roles}".lower()
        self.save()
        UserCache.objects.filter(pk=self.pk).update(
            searchable_data=Unaccent(F("searchable_text"))
        )