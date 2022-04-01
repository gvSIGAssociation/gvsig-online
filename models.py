
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
    
    def __str__(self):
        return self.name