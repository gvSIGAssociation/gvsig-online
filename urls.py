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

packages = [ app for app in settings.INSTALLED_APPS
                if app.startswith('gvsigol_plugin_')
                 or app.startswith('gvsigol_app_')
            ]

urlpatterns = [
    path('gvsigonline/i18n/', include(i18n)),
    path('gvsigonline/jsi18n/', JavaScriptCatalog.as_view(packages=packages), name='javascript-catalog'),
    path('gvsigonline/admin/', admin.site.urls) #,
    #path('gvsigonline/oidc/', include('mozilla_django_oidc.urls')),
]

for app in packages:
    if 'gvsigol_app_' in app:
        urlpatterns += [
            path('gvsigonline/', include(app + '.urls')),
        ]
        try:
            urlpatterns += [
                path('gvsigonline/fileserver/', include(app + '.urls_fileserver')),
            ]
        except:
            pass

        
for plugin in settings.INSTALLED_APPS:
    if 'gvsigol_plugin_' in plugin:
        urlpatterns += [
            path('gvsigonline/', include(plugin + '.urls')),
        ]
        try:
            urlpatterns += [
                path('gvsigonline/fileserver/', include((plugin + '.urls_fileserver', plugin), namespace=plugin)),
            ]
        except:
            pass
    
if 'gvsigol_core' in settings.INSTALLED_APPS:
    urlpatterns += [
        path('gvsigonline/core/', include('gvsigol_core.urls')),
    ]
  
if 'gvsigol_auth' in settings.INSTALLED_APPS:
    urlpatterns += [
        path('gvsigonline/auth/', include('gvsigol_auth.urls')),
    ]

if 'gvsigol_services' in settings.INSTALLED_APPS:
    urlpatterns += [
        path('gvsigonline/services/', include('gvsigol_services.urls')),
    ]
    urlpatterns += [
        path('gvsigonline/fileserver/', include('gvsigol_services.urls_fileserver')),
    ]
    
if 'gvsigol_symbology' in settings.INSTALLED_APPS:
    urlpatterns += [
        path('gvsigonline/symbology/', include('gvsigol_symbology.urls')),
    ]
    
if 'gvsigol_filemanager' in settings.INSTALLED_APPS:
    urlpatterns += [
        path('gvsigonline/filemanager/', include('gvsigol_filemanager.urls', namespace='filemanager')),
    ]
    urlpatterns += [
        path('gvsigonline/fileserver/filemanager/', include('gvsigol_filemanager.urls_fileserver', namespace='fsfilemanager')),
    ]

if 'gvsigol_statistics' in settings.INSTALLED_APPS:
    urlpatterns += [
        path('gvsigonline/statistics/', include('gvsigol_statistics.urls', namespace='statistics')),
    ]
