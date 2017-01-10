# -*- coding: utf-8 -*-
'''
    gvSIG Online.
    Copyright (C) 2007-2016 gvSIG Association.

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
@author: Javi Rodrigo <jrodrigo@scolab.es>
'''


from gvsigol_plugin_alfresco.services import resource_manager
from django.http import HttpResponse, HttpResponseBadRequest
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

import logging
import json

logger = logging.getLogger(__name__)

@login_required(login_url='/gvsigonline/auth/login_user/')
@csrf_exempt
def get_repository(request):    
    try:
        default_repo = resource_manager.get_default_repository() 
        sites = resource_manager.get_sites(default_repo)
        
        repository = {}
        for site in sites:
            obj = default_repo.getObject(site.id)
            # properties items are key-value TUPLES ..
            for key,val in obj.properties.items():
                if key=='cm:name' or key=='cm:title' or key=='cmis:path':
                    print key,'=',val
                    
        response = {
            'repository': repository
        }
        
        return HttpResponse(json.dumps(response, indent=4), content_type='application/json')
                    
    except Exception as e:
        return HttpResponseBadRequest('<h1>Failed to get respository</h1>')
