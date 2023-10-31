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
@author: Javier Rodrigo <jrodrigo@scolab.es>
'''

from contextlib import redirect_stderr
from django.shortcuts import render
from django.shortcuts import redirect
from gvsigol import settings


def index(request):
    resp = {}
    
    if 'gvsigol_plugin_catalog' in settings.INSTALLED_APPS:
        from gvsigol_plugin_catalog import settings as catalog_settings
        resp['CATALOG_URL'] = catalog_settings.CATALOG_URL
        
    if 'gvsigol_plugin_sync' in settings.INSTALLED_APPS:
        from gvsigol_plugin_sync import settings as sync_settings
        resp['GVSIGOL_APP_DOWNLOAD_LINK'] = sync_settings.GVSIGOL_APP_DOWNLOAD_LINK
    
    return render(request, 'index.html', resp)
