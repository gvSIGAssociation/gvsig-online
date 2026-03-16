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
from gvsigol_core.views import default_index
from gvsigol_core.models import Application, Project, UserHomeOrder
from urllib.parse import unquote
import datetime
import json


def _get_public_items_ordered():
    """Return public projects and public applications merged, applying the global UserHomeOrder if set."""
    query = (
        Project.objects.filter(is_public=True, expiration_date__gte=datetime.datetime.now()) |
        Project.objects.filter(is_public=True, expiration_date=None)
    )
    public_projects = []
    for p in query.order_by('title'):
        public_projects.append({
            'id': p.id,
            'title': p.title,
            'description': p.description or '',
            'image': unquote(p.image_url),
            'url': p.url,
            'item_type': 'public',
        })

    public_apps = []
    for app in Application.objects.filter(is_public=True).order_by('title'):
        public_apps.append({
            'id': app.id,
            'title': app.title or app.name,
            'description': app.description or '',
            'image': app.image_url,
            'url': app.absurl,
            'item_type': 'app',
        })

    all_items = sorted(public_projects + public_apps, key=lambda x: x['title'].lower())

    global_order = UserHomeOrder.objects.filter(user__isnull=True).first()
    if global_order and global_order.order_type == UserHomeOrder.ORDER_MANUAL and global_order.order_data:
        try:
            order_list = json.loads(global_order.order_data)
            lookup = {}
            for item in all_items:
                lookup[(item['item_type'], item['id'])] = item
            seen = set()
            ordered = []
            for entry in order_list:
                key = (entry.get('type'), entry['id'])
                if key in lookup and key not in seen:
                    ordered.append(lookup[key])
                    seen.add(key)
            ordered += [item for item in all_items if (item['item_type'], item['id']) not in seen]
            all_items = ordered
        except Exception:
            pass

    return all_items


def index(request):
    resp = {}
    
    if 'gvsigol_plugin_catalog' in settings.INSTALLED_APPS:
        from gvsigol_plugin_catalog import settings as catalog_settings
        resp['CATALOG_URL'] = catalog_settings.CATALOG_URL
        
    if 'gvsigol_plugin_sync' in settings.INSTALLED_APPS:
        from gvsigol_plugin_sync import settings as sync_settings
        resp['GVSIGOL_APP_DOWNLOAD_LINK'] = sync_settings.GVSIGOL_APP_DOWNLOAD_LINK

    resp['public_items'] = _get_public_items_ordered()

    return default_index(request, response=resp)

