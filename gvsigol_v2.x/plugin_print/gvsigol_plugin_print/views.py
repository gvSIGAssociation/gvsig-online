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
@author: jrodrigo <jrodrigo@scolab.es>
'''

from django.shortcuts import HttpResponse
import settings
import json

def get_conf(request):
    if request.method == 'POST': 
        response = {
            'url': settings.PRINT_PROVIDER['url'],
            'legal_advice': settings.PRINT_PROVIDER['legal_advice'],
            'default_scales': settings.PRINT_PROVIDER['default_scales']
        }       
        return HttpResponse(json.dumps(response, indent=4), content_type='folder/json')           