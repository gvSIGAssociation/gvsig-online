"""gvsigol URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import include, url, i18n
from django.views.i18n import javascript_catalog
from django.contrib import admin

import settings

handler404 = 'gvsigol_core.views.not_found_view'

js_info_dict = {
    'packages': ('gvsigol_auth','gvsigol_core','gvsigol_services','gvsigol_symbology','gvsigol_plugin_print','gvsigol_plugin_etl','gvsigol_plugin_graphiccapture', 'gvsigol_plugin_picassa', 'gvsigol_plugin_catalog', 'gvsigol_plugin_worldwind', 'gvsigol_plugin_edition', 'gvsigol_plugin_print', 'gvsigol_plugin_geocoding', 'gvsigol_plugin_downloadman', 'gvsigol_plugin_importvector'),
}

urlpatterns = [
    url(r'^gvsigonline/i18n/', include(i18n)),
    #url(r'^gvsigonline/jsi18n/$', javascript_catalog, js_info_dict),   
    url(r'^gvsigonline/jsi18n/$', javascript_catalog, js_info_dict, name='javascript-catalog'),
    url(r'^gvsigonline/admin/', include(admin.site.urls)),
]

for app in settings.INSTALLED_APPS:
    if 'gvsigol_app_' in app:
        urlpatterns += [
            url(r'^gvsigonline/', include(app + '.urls')),
        ]
        
for plugin in settings.INSTALLED_APPS:
    if 'gvsigol_plugin_' in plugin:
        urlpatterns += [
            url(r'^gvsigonline/', include(plugin + '.urls')),
        ]
    
if 'gvsigol_core' in settings.INSTALLED_APPS:
    urlpatterns += [
        url(r'^gvsigonline/core/', include('gvsigol_core.urls')),
    ]
  
if 'gvsigol_auth' in settings.INSTALLED_APPS:
    urlpatterns += [
        url(r'^gvsigonline/auth/', include('gvsigol_auth.urls')),
    ]

if 'gvsigol_services' in settings.INSTALLED_APPS:
    urlpatterns += [
        url(r'^gvsigonline/services/', include('gvsigol_services.urls')),
    ]
    
if 'gvsigol_symbology' in settings.INSTALLED_APPS:
    urlpatterns += [
        url(r'^gvsigonline/symbology/', include('gvsigol_symbology.urls')),
    ]
    
if 'gvsigol_filemanager' in settings.INSTALLED_APPS:
    urlpatterns += [
        url(r'^gvsigonline/filemanager/', include('gvsigol_filemanager.urls', namespace='filemanager')),      
    ]

if 'gvsigol_statistics' in settings.INSTALLED_APPS:
    urlpatterns += [
        url(r'^gvsigonline/statistics/', include('gvsigol_statistics.urls', namespace='statistics')),
    ]
