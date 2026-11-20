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
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponseBadRequest
from gvsigol_plugin_alfresco import settings
from cmislib.model import CmisClient
import logging

logger = logging.getLogger(__name__)

class UnsupportedRequestError(Exception):
    pass
        
class AlfrescoRM():
    def __init__(self, alfresco_repository_url, alfresco_cmis_rest_api_url, alfresco_admin_user, alfresco_admin_password):
        self.alfresco_repository_url = alfresco_repository_url
        self.alfresco_cmis_rest_api_url = alfresco_cmis_rest_api_url
        self.alfresco_admin_user = alfresco_admin_user
        self.alfresco_admin_password = alfresco_admin_password
        
        try:
            self.cmis_client = CmisClient(self.alfresco_cmis_rest_api_url, self.alfresco_admin_user, self.alfresco_admin_password)
            
        except:
            return HttpResponseBadRequest('<h1>Failed to connect to Alfresco</h1>')
     
    def get_repository_url(self):
        return self.alfresco_repository_url
    
    def get_default_repository(self):
        default_repository = self.cmis_client.getRepository(self.cmis_client.defaultRepository.id)
        return default_repository
    
    def get_sites(self, repository):
        alfresco_sites = repository.query("select * from cmis:folder where cmis:objectTypeId='F:st:site'")
        
        sites = []
        for s in alfresco_sites:
            obj = repository.getObject(s.id)
            s = {}
            s['isSite'] = True
            for key,val in list(obj.properties.items()):
                if key=='cmis:name' or key=='cmis:title' or key=='cmis:description' or key=='cmis:path' or key=='cmis:objectId' or key=='cmis:objectTypeId' or key=='cmis:parentId':
                    s[key] = val
            document_library = repository.getObjectByPath(s['cmis:path'] + '/documentLibrary')
            children = document_library.getChildren()  
            folders = []
            for child in children:
                if child.properties['cmis:objectTypeId'] == 'cmis:folder':
                    folder = {
                        'name': child.properties['cmis:name'],
                        'description': child.properties['cmis:description'],
                        'objectId': child.properties['cmis:objectId'],
                        'path': child.properties['cmis:path'],
                        'parent': child.properties['cmis:parentId'],
                        'url': self.alfresco_repository_url + '#filter=path|' + child.properties['cmis:path']
                    }
                    folders.append(folder)
            s['folders'] = folders
            sites.append(s)
            
        return sites
    
    def get_folder_content(self, repository, object_id):
        object_id = object_id.replace('workspace://SpacesStore/', '')
        f = repository.getObject(object_id)
        
        content = {}
        content['isSite'] = False
        for key,val in list(f.properties.items()):
            if key=='cmis:name' or key=='cmis:title' or key=='cmis:description' or key=='cmis:path' or key=='cmis:objectId' or key=='cmis:objectTypeId' or key=='cmis:parentId':
                content[key] = val
                    
        folderChildren = f.getChildren()
        
        folders = []
        for child in folderChildren:
            if child.properties['cmis:objectTypeId'] == 'cmis:folder':
                folder = {
                    'name': child.properties['cmis:name'],
                    'description': child.properties['cmis:description'],
                    'objectId': child.properties['cmis:objectId'],
                    'path': child.properties['cmis:path'],
                    'parent': child.properties['cmis:parentId'],
                    'url': self.alfresco_repository_url + '#filter=path|' + child.properties['cmis:path']
                }
                folders.append(folder)
        content['folders'] = folders
                    
        return content

def get_resource_manager():
    try:
        alfresco_repository_url = settings.ALFRESCO_REPOSITORY_URL
        alfresco_cmis_rest_api_url = settings.ALFRESCO_CMIS_REST_API_URL
        alfresco_admin_user = settings.ALFRESCO_ADMIN_USER
        alfresco_admin_password = settings.ALFRESCO_ADMIN_PASSWORD
        rm = AlfrescoRM(alfresco_repository_url, alfresco_cmis_rest_api_url, alfresco_admin_user, alfresco_admin_password) 
    except:
        raise ImproperlyConfigured
    
    return rm

resource_manager = get_resource_manager()
