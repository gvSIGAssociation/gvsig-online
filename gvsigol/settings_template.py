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
DEBUG = ##DEBUG##

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
    ##GVSIG_ONLINE_APPS##
]

MIDDLEWARE_CLASSES = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.RemoteUserMiddleware',
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
            os.path.join(BASE_DIR, 'gvsigol_filemanager/templates'),            
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
# https://docs.djangoproject.com/en/1.8/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'gvsigonline',
        'USER': '##DATABASE_USER##',
        'PASSWORD': '##DATABASE_PASSWORD##',
        'HOST': '##DATABASE_HOST##',
        'PORT': '##DATABASE_PORT##',
    }
}
POSTGIS_VERSION = (2, 1, 2)


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
    'ENABLED': True,
    'HOST':'##LDAP_HOSTNAME##',
    'PORT': '##LDAP_PORT##',
    'DOMAIN': '##LDAP_DN##',
    'USERNAME': '##LDAP_BIND_USER##',
    'PASSWORD': '##LDAP_BIND_PASSWORD##',
    'AD': '##LDAP_AD_SUFFIX##'
}

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.RemoteUserBackend',
    'django_auth_ldap.backend.LDAPBackend',
    #'django.contrib.auth.backends.ModelBackend',
)
AUTH_LDAP_SERVER_URI = "ldap://##LDAP_HOSTNAME##:##LDAP_PORT##"
AUTH_LDAP_ROOT_DN = "##LDAP_DN##"
AUTH_LDAP_USER_SEARCH = LDAPSearch("##LDAP_DN##", ldap.SCOPE_SUBTREE, "(uid=%(user)s)")


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
    '##GVSIG_ONLINE_HOME##/gvsigol/gvsigol_core/locale',
    '##GVSIG_ONLINE_HOME##/gvsigol/gvsigol_services/locale',
    '##GVSIG_ONLINE_HOME##/gvsigol/gvsigol_symbology/locale',
    '##GVSIG_ONLINE_HOME##/gvsigol/gvsigol_auth/locale',
    '##GVSIG_ONLINE_HOME##/gvsigol/gvsigol_filemanager/locale',
)

SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Email settings
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_USE_TLS = True
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_HOST_USER = 'gvsigonline@scolab.es'
EMAIL_HOST_PASSWORD = 'Ohp2leej'
EMAIL_PORT = 587
SITE_ID=1

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.9/howto/static-files/
MEDIA_ROOT = '/var/www/media/'
MEDIA_URL = '##BASE_URL##/media/'
STATIC_URL = '/static/'
STATIC_ROOT = '##GVSIG_ONLINE_HOME##/gvsigol/assets'
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    #'compressor.finders.CompressorFinder',
)

GVSIGOL_VERSION = '2.1.0'

GVSIGOL_USERS_CARTODB = {
    'dbhost': '##DATABASE_HOST##',
    'dbport': '##DATABASE_PORT##',
    'dbname': 'gvsigonline',
    'dbuser': '##DATABASE_USER##',
    'dbpassword': '##DATABASE_PASSWORD##'
}

PUBLIC_VIEWER = True
CATALOG_MODULE = ##CATALOG_IS_ACTIVE##
GVSIGOL_CATALOG = {
    'URL': '##GEONETWORK_API_URL##'
}

GVSIGOL_SERVICES = {
    'ENGINE':'geoserver',
    'URL': '##GEOSERVER_BASE_URL##',
    'CLUSTER_NODES':[##GEOSERVER_CLUSTER_NODES##],
    'SUPPORTED_TYPES': (
                        ('v_PostGIS', _('PostGIS vector')),
                        ('v_SHP', _('Shapefile folder')),                        
                        ('c_GeoTIFF', _('GeoTiff')),
                        ('e_WMS', _('Cascading WMS')),
    ),
    # if MOSAIC_DB entry is omitted, mosaic indexes will be stored as SHPs
    'MOSAIC_DB': {
                  'host': '##DATABASE_HOST##',
                  'port': '##DATABASE_PORT##',
                  'database': 'gvsigonline',
                  'schema': 'mosaic',
                  'user': '##DATABASE_USER##',
                  'passwd': '##DATABASE_PASSWORD##'
    },
    # OGR path is only necessary if different from the one defined on gdal_tools.OGR2OGR_PATH
    'OGR2OGR_PATH': '/usr/bin/ogr2ogr'
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
    ##SUPORTED_CRS## 
}

GVSIGOL_SEARCH = {
    'nominatim': {
        'url': '##NOMINATIM_URL##',
        'country_codes': '##NOMINATIM_COUNTRY_CODES##'
    }
}

GVSIGOL_TOOLS = {
    ##GVSIGOL_TOOLS##
    'get_feature_info_control': {
        'private_fields_prefix': '_'
    },
    'attribute_table': {
        'private_fields_prefix': '_',
        'show_search': False
    }    
}

GVSIGOL_BASE_LAYERS = {
    'bing': {
        'active': ##BING_IS_ACTIVE##,
        'key': '##BING_API_KEY##'
    }
}

FILEMANAGER_DIRECTORY = os.path.join(MEDIA_ROOT, 'data')
FILEMANAGER_MEDIA_ROOT = os.path.join(MEDIA_ROOT, FILEMANAGER_DIRECTORY)
FILEMANAGER_MEDIA_URL = os.path.join(MEDIA_URL, FILEMANAGER_DIRECTORY)
FILEMANAGER_STORAGE = FileSystemStorage(location=FILEMANAGER_MEDIA_ROOT, base_url=FILEMANAGER_MEDIA_URL, file_permissions_mode=0o666)