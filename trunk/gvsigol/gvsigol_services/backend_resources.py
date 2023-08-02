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
from gvsigol import settings
import logging
from . import utils
import os
import time
from os import path
from shutil import copyfile
import tempfile

logger = logging.getLogger(__name__)
from gvsigol_services.models import LayerResource

class UnsupportedRequestError(Exception):
    pass

class GvsigolRM():
    def __init__(self):
        logger.info('Initializing gvsigol resource manager')
    
    def save_resource(self, resource, layer_id, res_type):
        try:
            resource_dir = utils.get_resources_dir(layer_id, res_type)
            orig_res_name = os.path.basename(resource.name)
            prefix, suffix = os.path.splitext(orig_res_name)
            (fd, f) = tempfile.mkstemp(suffix=suffix, prefix=prefix+'_', dir=resource_dir)
            with os.fdopen(fd, "wb") as destination:
                for chunk in resource.chunks():
                    destination.write(chunk)
            relative_path = os.path.relpath(f, settings.MEDIA_ROOT)
            utils.set_default_permissions(f)
            return [True, relative_path]
         
        except Exception as e:
            return [False, '']
        
    def delete_resource(self, resource): 
        try:
            path = os.path.join(settings.MEDIA_ROOT, resource.path) 
            if os.path.exists(path):
                media_path = self.store_historical(path, resource.layer.id, resource.feature)
                if not LayerResource.objects.filter(path=resource.path).exists():
                    # only deleted if there are no cloned resources that share the same path
                    os.remove(path)
                return media_path
        except Exception as e:
            raise e
        
    def store_historical(self, path_, lyrid = None, featid = None):
        """
        Hace una copia del recurso para el historico y devuelve la url al fichero
        """
        name = os.path.basename(path_)
        millis = int(round(time.time() * 1000))
        
        if(lyrid is not None and featid is not None):
            suffix = "_" + str(lyrid) + "_" + str(featid) + "_" + str(millis)
        else:
            suffix = "_" + str(millis)    
            
        li = name.rsplit(".", 1)
        try:
            new_name = li[0] + suffix  + "." + li[1]
        except Exception:
            new_name = li[0] + suffix
        if not os.path.isabs(path_):
            path_ = os.path.join(settings.MEDIA_ROOT, path_)
        if(path.exists(path_)):
            target_dir = utils.get_historic_resources_dir(path_, lyrid)
            new_path = os.path.join(target_dir, new_name)
            copyfile(path_, new_path)
            utils.set_default_permissions(new_path)
            rel_path = os.path.relpath(new_path, settings.MEDIA_ROOT)
            return rel_path

resource_manager = GvsigolRM()
