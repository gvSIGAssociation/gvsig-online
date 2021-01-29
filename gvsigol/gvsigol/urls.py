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
from django.urls import include, re_path, path
from django.conf.urls import i18n
from django.views.i18n import JavaScriptCatalog
from django.contrib import admin

from . import settings

handler404 = 'gvsigol_core.views.not_found_view'

packages = [ app for app in settings.INSTALLED_APPS
                if app.startswith('gvsigol_plugin_')
                 or app.startswith('gvsigol_app_')
            ]

urlpatterns = [
    re_path(r'^gvsigonline/i18n/', include(i18n)),
    re_path(r'^gvsigonline/jsi18n/$', JavaScriptCatalog.as_view(packages=packages), name='javascript-catalog'),
    re_path(r'^gvsigonline/admin/', admin.site.urls),
]

for app in packages:
    if 'gvsigol_app_' in app:
        urlpatterns += [
            path('gvsigonline/', include(app + '.urls')),
        ]

        
for plugin in settings.INSTALLED_APPS:
    if 'gvsigol_plugin_' in plugin:
        urlpatterns += [
            re_path(r'^gvsigonline/', include(plugin + '.urls')),
        ]
    
if 'gvsigol_core' in settings.INSTALLED_APPS:
    urlpatterns += [
        re_path(r'^gvsigonline/core/', include('gvsigol_core.urls')),
    ]
  
if 'gvsigol_auth' in settings.INSTALLED_APPS:
    urlpatterns += [
        path('gvsigonline/auth/', include('gvsigol_auth.urls')),
    ]

if 'gvsigol_services' in settings.INSTALLED_APPS:
    urlpatterns += [
        re_path(r'^gvsigonline/services/', include('gvsigol_services.urls')),
    ]
    
if 'gvsigol_symbology' in settings.INSTALLED_APPS:
    urlpatterns += [
        re_path(r'^gvsigonline/symbology/', include('gvsigol_symbology.urls')),
    ]
    
if 'gvsigol_filemanager' in settings.INSTALLED_APPS:
    urlpatterns += [
        re_path(r'^gvsigonline/filemanager/', include('gvsigol_filemanager.urls', namespace='filemanager')),      
    ]

if 'gvsigol_statistics' in settings.INSTALLED_APPS:
    urlpatterns += [
        re_path(r'^gvsigonline/statistics/', include('gvsigol_statistics.urls', namespace='statistics')),
    ]
