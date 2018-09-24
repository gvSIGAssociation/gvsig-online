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

'''
from django.shortcuts import render_to_response, RequestContext, redirect, HttpResponse
from django.http import HttpResponseRedirect, HttpResponseBadRequest, HttpResponseNotFound, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods, require_safe,require_POST, require_GET
from django.shortcuts import render
import json
import ast
from django.views.decorators.csrf import csrf_exempt
from service import geonetwork_service

@require_http_methods(["GET"])
def metadata_form(request, metadata_id):
    
    if geonetwork_service!=None and request.method == 'GET':
        response = geonetwork_service.metadata_editor(metadata_id)
        return HttpResponse(response, content_type='text/plain')
        
    return HttpResponse(status=500)
    
'''