# -*- coding: utf-8 -*-

'''
    gvSIG Online.
    Copyright (C) 2007-2015 gvSIG Association.

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

import os
import ldap
from django_auth_ldap.config import LDAPSearch
from django.utils.translation import ugettext_lazy as _
from django.core.files.storage import FileSystemStorage

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.9/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '##s#jx5ildpkavpi@tbtl0fvj#(np#hyckdg*q#1mu%ovr8$t_'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'gvsigol_auth',
    'gvsigol_services',
    'gvsigol_symbology',
    'gvsigol_filemanager',
    'gvsigol_core',
    'gvsigol_app_dev',
    #'gvsigol_app_pobla',
    #'gvsigol_app_benicarlo',
    'gvsigol_plugin_worldwind',
    'gvsigol_plugin_shps_folder',
    'gvsigol_plugin_geocoding',
    'gvsigol_plugin_sync',
    'gvsigol_plugin_catastro',
    'gvsigol_plugin_alfresco',
    'gvsigol_plugin_print',
    #'gvsigol_plugin_catalog',
]

MIDDLEWARE_CLASSES = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware', 
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.PersistentRemoteUserMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'gvsigol.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'gvsigol_auth/templates'),
            os.path.join(BASE_DIR, 'gvsigol_core/templates'),
            os.path.join(BASE_DIR, 'gvsigol_services/templates'),
            os.path.join(BASE_DIR, 'gvsigol_symbology/templates'),
            os.path.join(BASE_DIR, 'gvsigol_filemanager/templates')
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'gvsigol_core.context_processors.global_settings',
                'django.contrib.messages.context_processors.messages',
                'django.core.context_processors.i18n',
            ],
        },
    },
]

WSGI_APPLICATION = 'gvsigol.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.9/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        #'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'gvsigonline_v2',
        'USER': 'postgres',
        'PASSWORD': 'postgres',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
POSTGIS_VERSION = (2, 1, 2)

AUTH_WITH_REMOTE_USER = False

# Password validation
# https://docs.djangoproject.com/en/1.9/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

GVSIGOL_LDAP = {
    'ENABLED': False,
    'HOST':'devel.gvsigonline.com',
    'PORT': '389',
    'DOMAIN': 'dc=test,dc=gvsigonline,dc=com',
    'USERNAME': 'cn=admin,dc=test,dc=gvsigonline,dc=com',
    'PASSWORD': 'GE2wa8RE',
    'AD': ''
}

AUTHENTICATION_BACKENDS = (
    #'django.contrib.auth.backends.RemoteUserBackend',
    #'django_auth_ldap.backend.LDAPBackend',
    'django.contrib.auth.backends.ModelBackend',
)
AUTH_LDAP_SERVER_URI = "ldap://devel.gvsigonline.com:389"
AUTH_LDAP_ROOT_DN = "dc=test,dc=gvsigonline,dc=com"
AUTH_LDAP_USER_SEARCH = LDAPSearch("dc=test,dc=gvsigonline,dc=com", ldap.SCOPE_SUBTREE, "(uid=%(user)s)")


# Internationalization
# https://docs.djangoproject.com/en/1.9/topics/i18n/
LANGUAGE_CODE = 'es'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True
LANGUAGES = (
    ('es', _('Spanish')),
    ('ca', _('Catalan')), 
    ('en', _('English')),   
    
)
LOCALE_PATHS = (
    os.path.join(BASE_DIR, 'gvsigol/locale'),
    os.path.join(BASE_DIR, 'gvsigol_core/locale'),
    os.path.join(BASE_DIR, 'gvsigol_auth/locale'),
    os.path.join(BASE_DIR, 'gvsigol_services/locale'),
    os.path.join(BASE_DIR, 'gvsigol_symbology/locale'),
    os.path.join(BASE_DIR, 'gvsigol_filemanager/locale'),
    os.path.join(BASE_DIR, 'gvsigol_app_dev/locale'),
    os.path.join(BASE_DIR, 'gvsigol_app_pobla/locale'),
    os.path.join(BASE_DIR, 'gvsigol_app_benicarlo/locale'),
    os.path.join(BASE_DIR, 'gvsigol_plugin_worldwind/locale'),
    os.path.join(BASE_DIR, 'gvsigol_plugin_shps_folder/locale'),
)

SESSION_EXPIRE_AT_BROWSER_CLOSE = True
LOGOUT_PAGE_URL = '/gvsigonline/'

# Email settings
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_USE_TLS = True
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_HOST_USER = 'devel@scolab.es'
EMAIL_HOST_PASSWORD = 'ksiopa247'
EMAIL_PORT = 587
SITE_ID=1

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.9/howto/static-files/
BASE_URL = 'https://localhost'
MEDIA_ROOT = '/var/www/media/'
MEDIA_URL = 'https://localhost/media/'
STATIC_URL = '/gvsigonline/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'assets')
STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'gvsigol_core/static'),
    os.path.join(BASE_DIR, 'gvsigol_auth/static'),
    os.path.join(BASE_DIR, 'gvsigol_services/static'),
    os.path.join(BASE_DIR, 'gvsigol_symbology/static'),
    os.path.join(BASE_DIR, 'gvsigol_filemanager/static'),
    os.path.join(BASE_DIR, 'gvsigol_app_dev/static'),
    #os.path.join(BASE_DIR, 'gvsigol_app_pobla/static'),
    #os.path.join(BASE_DIR, 'gvsigol_app_benicarlo/static'),
    os.path.join(BASE_DIR, 'gvsigol_plugin_worldwind/static'),
    os.path.join(BASE_DIR, 'gvsigol_plugin_shps_folder/static'),
)
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    #'compressor.finders.CompressorFinder',
)

GVSIGOL_VERSION = '2.1.7'

GVSIGOL_USERS_CARTODB = {
    'dbhost': 'localhost',
    'dbport': '5432',
    'dbname': 'gvsigonline_v2',
    'dbuser': 'postgres',
    'dbpassword': 'postgres'
}

PUBLIC_VIEWER = True

GVSIGOL_SERVICES = {
    'ENGINE':'geoserver',
    'URL': 'https://localhost/gs-local',
    'USER': 'admin',
    'PASSWORD': 'geoserver',
    'CLUSTER_NODES':[],
    'SUPPORTED_TYPES': (
                        ('v_PostGIS', _('PostGIS vector')),
                        #('v_SHP', _('Shapefile folder')),                        
                        ('c_GeoTIFF', _('GeoTiff')),
                        ('e_WMS', _('Cascading WMS')),
    ),
    # if MOSAIC_DB entry is omitted, mosaic indexes will be stored as SHPs
    'MOSAIC_DB': {
                  'host': 'test.scolab.eu',
                  'port': '6433',
                  'database': 'carto',
                  'schema': 'public',
                  'user': 'postgres',
                  'passwd': 'postgres82'
    },
    # NOTE: we are migrating gdal_tools to the external library pygdaltools
    # OGR path is only necessary if different from the one defined on gdal_tools.OGR2OGR_PATH
    # In the future we will only need GDALTOOLS_BASEPATH variable
    'OGR2OGR_PATH': '/usr/bin/ogr2ogr',
    'GDALTOOLS_BASEPATH': '/usr/bin'
}

# Must be a valid iconv encoding name. Use iconv --list on Linux to see valid names 
SUPPORTED_ENCODINGS = [ "LATIN1", "UTF-8", "ISO-8859-15", "WINDOWS-1252"]
SUPPORTED_CRS = {
    '3857': {
        'code': 'EPSG:3857',
        'title': 'WGS 84 / Pseudo-Mercator',
        'definition': '+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext  +no_defs',
        'units': 'meters'
    },
    '900913': {
        'code': 'EPSG:900913',
        'title': 'Google Maps Global Mercator -- Spherical Mercator',
        'definition': '+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext  +no_defs',
        'units': 'meters'
    },
    '4326': {
        'code': 'EPSG:4326',
        'title': 'WGS84',
        'definition': '+proj=longlat +datum=WGS84 +no_defs',
        'units': 'degrees'
    },
    '4258': {
        'code': 'EPSG:4258',
        'title': 'ETRS89',
        'definition': '+proj=longlat +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +no_defs',
        'units': 'degrees'
    },
    '25830': {
        'code': 'EPSG:25830',
        'title': 'ETRS89 / UTM zone 30N',
        'definition': '+proj=utm +zone=30 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs',
        'units': 'meters'
    }
}

GVSIGOL_TOOLS = {
    'get_feature_info_control': {
        'private_fields_prefix': '_'
    },
    'attribute_table': {
        'private_fields_prefix': '_',
        'show_search': True
    }
}

GVSIGOL_ENABLE_ENUMERATIONS = True

GVSIGOL_BASE_LAYERS = {
    'bing': {
        'active': False,
        'key': 'Ak-dzM4wZjSqTlzveKz5u0d4IQ4bRzVI309GxmkgSVr1ewS6iPSrOvOKhA-CJlm3'
    }
}

#skin-blue
#skin-blue-light
#skin-red
#skin-red-light
#skin-black
#skin-black-light
#skin-green
#skin-green-light
#skin-purple
#skin-purple-light
#skin-yellow
#skin-yellow-light
GVSIGOL_SKIN = "skin-blue"

FILEMANAGER_DIRECTORY = os.path.join(MEDIA_ROOT, 'data')
FILEMANAGER_MEDIA_ROOT = os.path.join(MEDIA_ROOT, FILEMANAGER_DIRECTORY)
FILEMANAGER_MEDIA_URL = os.path.join(MEDIA_URL, FILEMANAGER_DIRECTORY)
FILEMANAGER_STORAGE = FileSystemStorage(location=FILEMANAGER_MEDIA_ROOT, base_url=FILEMANAGER_MEDIA_URL, file_permissions_mode=0o666)