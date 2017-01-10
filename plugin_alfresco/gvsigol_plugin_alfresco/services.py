'''
    gvSIG Online.
    Copyright (C) 2007-2015 gvSIG Association.

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
from django.utils.translation import ugettext_lazy as _
from django.http import HttpResponseBadRequest
from cmislib import CmisClient
import settings
import logging

logger = logging.getLogger(__name__)

class UnsupportedRequestError(Exception):
    pass
        
class AlfrescoRM():
    def __init__(self, alfresco_cmis_rest_api_url, alfresco_admin_user, alfresco_admin_password):
        self.alfresco_cmis_rest_api_url = alfresco_cmis_rest_api_url
        self.alfresco_admin_user = alfresco_admin_user
        self.alfresco_admin_password = alfresco_admin_password
        
        try:
            logger.info('Initializing alfresco resource manager ...')
            self.cmis_client = CmisClient(self.alfresco_cmis_rest_api_url, self.alfresco_admin_user, self.alfresco_admin_password)
            
        except Exception as e:
            return HttpResponseBadRequest('<h1>Failed to connect to Alfresco</h1>')
     
    def get_default_repository(self):
        default_repository = self.cmis_client.getRepository(self.cmis_client.defaultRepository.id)
        return default_repository
    
    def get_sites(self, repository):
        logger.info('Getting list of sites ...')
        sites = repository.query("select * from cmis:folder where cmis:objectTypeId='F:st:site'")
        return sites

def get_resource_manager():
    try:
        alfresco_cmis_rest_api_url = settings.ALFRESCO_CMIS_REST_API_URL
        alfresco_admin_user = settings.ALFRESCO_ADMIN_USER
        alfresco_admin_password = settings.ALFRESCO_ADMIN_PASSWORD
        rm = AlfrescoRM(alfresco_cmis_rest_api_url, alfresco_admin_user, alfresco_admin_password) 
    except:
        raise ImproperlyConfigured
    
    return rm

resource_manager = get_resource_manager()
