
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

@author: Cesar Martinez Izquierdo - http://www.scolab.es
'''

from django.core.exceptions import PermissionDenied
from gvsigol_services.models import Layer, LayerLock
from gvsigol_services.utils import can_write_layer

def add_layer_lock(layer_name, request, ws_name=None, lock_type=LayerLock.GEOPORTAL_LOCK):
    try:
        if not ws_name:
            (ws_name, layer_name) = layer_name.split(":")
        layer = Layer.objects.get(name=layer_name, datastore__workspace__name=ws_name)
        if not can_write_layer(request, layer):
            raise PermissionDenied
    except Layer.DoesNotExist:
        raise PermissionDenied
    locks = LayerLock.objects.filter(layer=layer)
    locked = (locks.count()>0)
    if locked:
        if lock_type != LayerLock.GEOPORTAL_LOCK:
            qualified_layer_name = layer.datastore.workspace.name + ":" + layer.name
            raise LayerLocked(qualified_layer_name)
        else:
            #We allow simultaneous editions from the Geoportal (WFS), even from different users
            for lock in locks:
                if lock.type != LayerLock.GEOPORTAL_LOCK:
                    qualified_layer_name = layer.datastore.workspace.name + ":" + layer.name
                    raise LayerLocked(qualified_layer_name)
                elif lock.created_by == request.user.username:
                    # if the user has the lock, we don't need to create a new one
                    return lock

    # The user is allowed to create a new lock
    new_lock = LayerLock()
    new_lock.layer = layer
    new_lock.created_by = request.user.username
    new_lock.type = lock_type
    new_lock.save()
    return new_lock

def get_layer_lock(workspace_name, layer_name, request, check_writable=False, lock_type=None):
    try:
        layer = Layer.objects.get(name=layer_name, datastore__workspace__name=workspace_name)
        if check_writable and not can_write_layer(layer, request):
            raise PermissionDenied    
    except Layer.DoesNotExist:
        raise PermissionDenied

    locks = LayerLock.objects.filter(layer=layer, created_by=request.user.username)
    if lock_type:
        locks.filter(type=lock_type)
    if locks.count()>0:
        return locks[0]
    else:
        raise LayerNotLocked(workspace_name + ":" + layer_name)

def remove_layer_lock(layer, request, check_writable=False):
    """
    Removes the locks created by the user on a layer.
    If user is None, remove all the locks on the layer.
    """
    layer_lock = LayerLock.objects.filter(layer=layer)
    all_locks_count = layer_lock.count()
    if request.user:
        layer_lock = layer_lock.filter(created_by=request.user.username)
    if layer_lock.count()>0:
        if check_writable and not can_write_layer(request, layer):
            raise PermissionDenied()
        layer_lock.delete()
        return True
    elif all_locks_count > 0:
        # the layer was locked by another user
        raise PermissionDenied()
    raise LayerNotLocked()

class LayerLockingException(Exception):
    pass


class LayerNotLocked(LayerLockingException):
    """The requested layer lock does not exist"""
    
    def __init__(self, layer=None):
        self.layer = layer


class LayerLocked(LayerLockingException):
    """The layer already has a lock"""

    def __init__(self, layer=None):
        self.layer = layer

