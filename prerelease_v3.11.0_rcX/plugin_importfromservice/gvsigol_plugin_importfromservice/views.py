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

import json

from gvsigol_services.models import ServiceUrl

def get_conf(request):
    if request.method == 'POST':
        wms_queryset = ServiceUrl.objects.filter(type='WMS')
        wfs_queryset = ServiceUrl.objects.filter(type='WFS')

        wms = []
        for wms_serv in wms_queryset:
            wms.append({
                'title': wms_serv.title,
                'url': wms_serv.url
            })
        wfs = []
        for wfs_serv in wfs_queryset:
            wfs.append({
                'title': wfs_serv.title,
                'url': wfs_serv.url
            })
        response = {
            'wms': wms,
            'wfs': wfs
        }       
        return HttpResponse(json.dumps(response, indent=4), content_type='folder/json')              