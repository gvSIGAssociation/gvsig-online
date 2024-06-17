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

@author: Nacho Brodin <nbrodin@scolab.es>
'''

from django.urls import path, re_path, include
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import routers
from gvsigol_plugin_baseapi import views
from gvsigol import settings
import gvsigol_plugin_baseapi.settings as settings_local

#schema_view = get_swagger_view(title='Gvsigonline Rest API')
router = routers.DefaultRouter()

schema_view = get_schema_view(
    openapi.Info(
        title="GvsigOnline Rest API",
        version = '1.0',
        default_version='1.0',
        description="API Rest for GvsigOnline: Before use this API you have to get a token and validate it using the button 'Authorize'. To get the token call the API /auth/api-token-auth introducing a valid user and password in JSON format. After that, introduce the token with the prefix JWT and space. For example:  JWT eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9... ...2wXg6T1SNl4qo",
        terms_of_service="URL",
        contact=openapi.Contact(email="nbrodin@scolab.es"),
        license=openapi.License(name=""),
    ),
    url = settings.BASE_URL + "/" + settings.GVSIGOL_PATH + "/",
    #validators = ['ssv', 'flex'],
    public = False,
    #permission_classes = (permissions.AllowAny,),
)


urlpatterns = [
    re_path(r'^swagger(?P<format>.json|.yaml)$', schema_view.without_ui(cache_timeout=None), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=None), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=None), name='schema-redoc'),
    path('csrftoken/', views.get_csrftoken, name='get-csrftoken'),
]


