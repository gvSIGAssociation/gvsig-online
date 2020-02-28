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
import utils
import os
import time
from os import path
from shutil import copyfile

logger = logging.getLogger(__name__)

class UnsupportedRequestError(Exception):
    pass

class GvsigolRM():
    def __init__(self):
        logger.info('Initializing gvsigol resource manager')
    
    def save_resource(self, resource, type):
        try: 
            file_path = os.path.join(utils.get_resources_dir(type), resource.name)
            relative_path = file_path.replace(settings.MEDIA_ROOT, '')
            if os.path.exists(file_path):
                os.remove(file_path)
            with open(file_path, 'wb+') as destination:
                for chunk in resource.chunks():
                    destination.write(chunk)
            return [True, relative_path]
         
        except Exception as e:
            return [False, '']
        
    def delete_resource(self, resource): 
        try:
            path = os.path.join(settings.MEDIA_ROOT, resource.path) 
            if os.path.exists(path):
                url, media_path = self.store_historical(path, resource.layer.id, resource.feature)
                os.remove(path)  
                return url, media_path
        except Exception as e:
            raise e
        
    def store_historical(self, path_, lyrid = None, featid = None):
        """
        Hace una copia del recurso para el historico y devuelve la url al fichero
        """
        millis = int(round(time.time() * 1000))
        if(lyrid is not None and featid is not None):
            suffix = "_" + str(lyrid) + "_" + str(featid) + "_" + str(millis)
        else:
            suffix = "_" + str(millis)    
            
        if(not path.exists(path_)):
            path_ = settings.MEDIA_ROOT + path_
        li = path_.rsplit(".", 1)
        try:
            new_path = li[0] + suffix  + "." + li[1]
        except Exception:
            new_path = li[0] + suffix
        if(path.exists(path_)):
            copyfile(path_, new_path)
            rel_path = new_path.replace(settings.MEDIA_ROOT, '')
            url = settings.MEDIA_URL + rel_path
        return url, new_path

resource_manager = GvsigolRM()
