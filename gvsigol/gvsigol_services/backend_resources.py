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
from models import LayerResource
from gvsigol import settings
import logging
import utils
import os

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
                os.remove(path)  
        except Exception as e:
            raise e

resource_manager = GvsigolRM()
