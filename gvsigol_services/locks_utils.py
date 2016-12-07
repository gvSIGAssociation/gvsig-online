
'''
    gvSIG Online.
    Copyright (C) 2016 gvSIG Association.

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
@author: Cesar Martinez Izquierdo - http://www.scolab.es
'''
# gvsig online modules

from django.core.exceptions import PermissionDenied

from gvsigol_services.models import Layer, LayerLock


def add_layer_lock(qualified_layer_name, user, lock_type=LayerLock.GEOPORTAL_LOCK):
    (ws_name, layer_name) = qualified_layer_name.split(":")
    layer_filter = Layer.objects.filter(name=layer_name, datastore__workspace__name=ws_name)
    #ugu = UserGroupUser.objects.filter(user=user)
    #lwg = LayerWriteGroup.objects.filter(group__usergroupuser__user=user)
    is_writable = (layer_filter.filter(layerwritegroup__group__usergroupuser__user=user).count()>0)
    
    if not is_writable:
        raise PermissionDenied
    layer = layer_filter[0]
    
    #is_locked = (LayerLock.objects.filter(layer__name=layer_name, layer__datastore__workspace__name=ws_name).count()>0)
    is_locked = (LayerLock.objects.filter(layer=layer).count()>0)
    if is_locked:
        raise LayerLocked(qualified_layer_name)
    new_lock = LayerLock()
    new_lock.layer = layer
    new_lock.created_by = user.username
    new_lock.type = lock_type
    new_lock.save()
    return new_lock

def is_locked(qualified_layer_name, user, check_writable=False):
    (ws_name, layer_name) = qualified_layer_name.split(":")
    layer_filter = Layer.objects.filter(name=layer_name, datastore__workspace__name=ws_name)
    
    if check_writable:
        is_writable = (layer_filter.filter(layerwritegroup__group__usergroupuser__user=user).count()>0)
        if not is_writable:
            raise PermissionDenied
    layer = layer_filter[0]
    return (LayerLock.objects.filter(layer=layer, created_by=user.username).count()>0)

def get_layer_lock(qualified_layer_name, user, check_writable=False, lock_type=None):
    name_parts = qualified_layer_name.split(":")
    if len(name_parts)==2:
        # only consider tables having a proper qualified name (e.g., using the schema: workspace:layer_name)
        (ws_name, layer_name) = name_parts
        layer_filter = Layer.objects.filter(name=layer_name, datastore__workspace__name=ws_name)
        
        if check_writable:
            is_writable = (layer_filter.filter(layerwritegroup__group__usergroupuser__user=user).count()>0)
            if not is_writable:
                raise PermissionDenied
        layer = layer_filter[0]
        locks = LayerLock.objects.filter(layer=layer, created_by=user.username)
        if lock_type:
            locks.filter(type=lock_type)
        if locks.count()>0:
            return locks[0]
        else:
            raise LayerNotLocked(qualified_layer_name)
    return None

def remove_layer_lock(layer, user, check_writable=False):
    layer_lock = LayerLock.objects.filter(layer=layer)
    if len(layer_lock)==1:
        if layer_lock.filter(created_by=user.username).count()!=1:
            # the layer was locked by a different user!!
            raise PermissionDenied()
        if check_writable:
            layer_filter = Layer.objects.filter(id=layer.id)
            is_writable = (layer_filter.filter(layerwritegroup__group__usergroupuser__user=user).count()>0)
            if not is_writable:
                raise PermissionDenied()
        layer_lock.delete()
        return True
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

