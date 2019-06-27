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

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.9/howto/deployment/checklist/

import os
import ldap
import django.conf.locale
from django.conf import settings
from django_auth_ldap.config import LDAPSearch
from django.utils.translation import ugettext_lazy as _
from django.core.files.storage import FileSystemStorage

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
if '__file__' in globals():
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
else:
    BASE_DIR = os.path.join(os.path.abspath(os.getcwd()), "gvsigol")

# Eliminando warnings molestos  
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'q-#1q+!^2@4#3@hgmrgne%1nh4q4(@wpi-x(y^1^1cqnz^7d(g'
if len(SECRET_KEY) == 14:
    # It has not been replaced by deployment scripts
    # Generate a random one
    SECRET_FILE = os.path.join(BASE_DIR, 'gvsigol', 'secret.txt')
    try:
        SECRET_KEY = open(SECRET_FILE).read().strip()
    except IOError:
        try:
            try:
                # available since Django 1.10.x
                from django.core.management.utils import get_random_secret_key
            except:
                from django.utils.crypto import get_random_string
                def get_random_secret_key():
                    chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
                    return get_random_string(50, chars) 
            from django.core.management import utils
            import os
            SECRET_KEY = get_random_secret_key()
            secret = file(SECRET_FILE, 'w')
            secret.write(SECRET_KEY)
            secret.close()
            os.chmod(SECRET_FILE, 0o400)
        except IOError:
            Exception('Please create a %s file with random characters to generate your secret key!' % SECRET_FILE)

try:
    from gvsigol import settings_passwords
except:
    # Store your passwords for local development in 'settings_passwds.py'
    # Do not write any password here!!!!
    pw_file = file(os.path.join(BASE_DIR, 'gvsigol', 'settings_passwords.py'), 'w')
    pw_file.write("BING_KEY_DEVEL='yourbingkey'\n")
    pw_file.write("DB_USER_DEVEL='yourdbuser'\n")
    pw_file.write("DB_PW_DEVEL='yourdbkey'\n")
    pw_file.write("LDAP_USER_DEVEL='yourldapuser'\n")
    pw_file.write("LDAP_PW_DEVEL='yourldapkey'\n")
    pw_file.write("GEOSERVER_USER_DEVEL='admin'\n")
    pw_file.write("GEOSERVER_PW_DEVEL='geoserver'\n")
    pw_file.close()
    from gvsigol import settings_passwords
finally:
    # Store your passwords for local development in 'settings_passwords.py'
    # Do not write any password here!!!!
    BING_KEY_DEVEL = settings_passwords.BING_KEY_DEVEL
    DB_USER_DEVEL = settings_passwords.DB_USER_DEVEL
    DB_PW_DEVEL = settings_passwords.DB_PW_DEVEL
    LDAP_USER_DEVEL = settings_passwords.LDAP_USER_DEVEL
    LDAP_PW_DEVEL = settings_passwords.LDAP_PW_DEVEL
    GEOSERVER_USER_DEVEL = settings_passwords.GEOSERVER_USER_DEVEL
    GEOSERVER_PW_DEVEL = settings_passwords.GEOSERVER_PW_DEVEL


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']

#GEOS_LIBRARY_PATH = 'C:\\Python27\\Lib\\site-packages\\osgeo\\geos_c.dll'
#GDAL_LIBRARY_PATH = 'C:\\Python27\\Lib\\site-packages\\osgeo\\gdal202.dll'



# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',
    'django.contrib.sites',
    'gvsigol_statistics',
    'gvsigol_auth',
    'gvsigol_services',
    'gvsigol_symbology',
    'gvsigol_filemanager',
    'gvsigol_core',
    'gvsigol_app_test',
    'gvsigol_plugin_worldwind',
    'gvsigol_plugin_print',
    'gvsigol_plugin_geocoding',
    'gvsigol_plugin_catalog',
    'actstream'
]

ACTSTREAM_SETTINGS = {
    'FETCH_RELATIONS': True,
    'USE_JSONFIELD': True,
}


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

CRONTAB_ACTIVE = True
ROOT_URLCONF = 'gvsigol.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'gvsigol_statistics/templates'),
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
                'django.template.context_processors.media',
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
        'USER': DB_USER_DEVEL, # WARNING: Do not write any password here!!!! Store them in 'settings_passwords.py' for local development
        'PASSWORD': DB_PW_DEVEL, # WARNING: Do not write any password here!!!! Store them in 'settings_passwords.py' for local development
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
POSTGIS_VERSION = (2, 3, 3)

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
    'USERNAME': LDAP_USER_DEVEL, # WARNING: Do not write any password here!!!! Store them in 'settings_passwords.py' for local development
    'PASSWORD': LDAP_PW_DEVEL, # WARNING: Do not write any password here!!!! Store them in 'settings_passwords.py' for local development
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

EXTRA_LANG_INFO = {
    'va': {
        'bidi': False,
        'code': u'va',
        'name': u'Valencian',
        'name_local': u'Valencian'
    },
}

# Add custom languages not provided by Django
LANG_INFO = dict(django.conf.locale.LANG_INFO.items() + EXTRA_LANG_INFO.items())
django.conf.locale.LANG_INFO = LANG_INFO

LANGUAGES = (
    ('es', _('Spanish')),
    ('va', _('Valencian')),
    ('ca', _('Catalan')), 
    ('en', _('English')),
    ('pt-br', _('Portuguese')),
)
LOCALE_PATHS = (
    os.path.join(BASE_DIR, 'gvsigol/locale'),
    os.path.join(BASE_DIR, 'gvsigol_core/locale'),
    os.path.join(BASE_DIR, 'gvsigol_auth/locale'),
    os.path.join(BASE_DIR, 'gvsigol_services/locale'),
    os.path.join(BASE_DIR, 'gvsigol_symbology/locale'),
    os.path.join(BASE_DIR, 'gvsigol_statistics/locale'),
    os.path.join(BASE_DIR, 'gvsigol_filemanager/locale'),
    os.path.join(BASE_DIR, 'gvsigol_app_test/locale'),
    os.path.join(BASE_DIR, 'gvsigol_plugin_worldwind/locale'),
    os.path.join(BASE_DIR, 'gvsigol_plugin_geocoding/locale'),
    os.path.join(BASE_DIR, 'gvsigol_plugin_edition/locale'),
    os.path.join(BASE_DIR, 'gvsigol_plugin_catalog/locale'),
    os.path.join(BASE_DIR, 'gvsigol_plugin_print/locale')
)

SESSION_EXPIRE_AT_BROWSER_CLOSE = True
LOGOUT_PAGE_URL = '/gvsigonline/'

# Email settings
EMAIL_BACKEND_ACTIVE = False
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_USE_TLS = True
EMAIL_HOST = 'smtp.yourdomain.org'
EMAIL_HOST_USER = 'gvsigonline@yourdomain.org'
EMAIL_HOST_PASSWORD = 'yourpass'
EMAIL_PORT = 587
SITE_ID=1

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.9/howto/static-files/
BASE_URL = 'https://localhost'
MEDIA_ROOT = '/usr/local/var/www/media/'
MEDIA_URL = 'https://localhost/media/'
STATIC_URL = '/gvsigonline/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'assets')

STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'gvsigol_core/static'),
    os.path.join(BASE_DIR, 'gvsigol_auth/static'),
    os.path.join(BASE_DIR, 'gvsigol_services/static'),
    os.path.join(BASE_DIR, 'gvsigol_symbology/static'),
    os.path.join(BASE_DIR, 'gvsigol_filemanager/static'),
    os.path.join(BASE_DIR, 'gvsigol_statistics/static'),
    os.path.join(BASE_DIR, 'gvsigol_app_dev/static')
)
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    #'compressor.finders.CompressorFinder',
)

GVSIGOL_VERSION = '2.3.4'

GVSIGOL_USERS_CARTODB = {
    'dbhost': 'localhost',
    'dbport': '5432',
    'dbname': 'gvsigonline_v2',
    'dbuser': DB_USER_DEVEL, # WARNING: Do not write any password here!!!! Store them in 'settings_passwords.py' for local development
    'dbpassword': DB_PW_DEVEL # WARNING: Do not write any password here!!!! Store them in 'settings_passwords.py' for local development
}

MOSAIC_DB = {
    'host': 'localhost',
    'port': '5432',
    'database': 'gvsigonline_v2',
    'schema': 'imagemosaic',
    'user': DB_USER_DEVEL, # WARNING: Do not write any password here!!!! Store them in 'settings_passwords.py' for local development
    'passwd': DB_PW_DEVEL # WARNING: Do not write any password here!!!! Store them in 'settings_passwords.py' for local development
},

OGR2OGR_PATH = '/usr/local/bin/ogr2ogr'
GDALTOOLS_BASEPATH = '/usr/local/bin'

TILE_SIZE = 256
MAX_ZOOM_LEVEL = 18 

# Must be a valid iconv encoding name. Use iconv --list on Linux to see valid names 
SUPPORTED_ENCODINGS = [ "LATIN1", "UTF-8", "ISO-8859-15", "WINDOWS-1252"]
USE_DEFAULT_SUPPORTED_CRS = True
SUPPORTED_CRS = {
    '3857': {
        'code': 'EPSG:3857',
        'title': 'WGS 84 / Pseudo-Mercator',
        'definition': '+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext  +no_defs',
        'units': 'meters'
    },
    '4326': {
        'code': 'EPSG:4326',
        'title': 'WGS84',
        'definition': '+proj=longlat +datum=WGS84 +no_defs +axis=neu',
        'units': 'degrees'
    },
    '4258': {
        'code': 'EPSG:4258',
        'title': 'ETRS89',
        'definition': '+proj=longlat +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +no_defs +axis=neu',
        'units': 'degrees'
    },
    '25830': {
        'code': 'EPSG:25830',
        'title': 'ETRS89 / UTM zone 30N',
        'definition': '+proj=utm +zone=30 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs',
        'units': 'meters'
    },
    '25829': {
        'code': 'EPSG:25829',
        'title': 'ETRS89 / UTM zone 29N',
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
        'key': BING_KEY_DEVEL # WARNING: Do not write any password here!!!! Store them in 'settings_passwords.py' for local development
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

GVSIGOL_NAME = 'gvsig'
GVSIGOL_SURNAME = 'OL'
GVSIGOL_NAME_SHORT = 'g'
GVSIGOL_SURNAME_SHORT = 'OL'

FILEMANAGER_DIRECTORY = os.path.join(MEDIA_ROOT, 'data')
FILEMANAGER_MEDIA_ROOT = os.path.join(MEDIA_ROOT, FILEMANAGER_DIRECTORY)
FILEMANAGER_MEDIA_URL = os.path.join(MEDIA_URL, FILEMANAGER_DIRECTORY)
FILEMANAGER_STORAGE = FileSystemStorage(location=FILEMANAGER_MEDIA_ROOT, base_url=FILEMANAGER_MEDIA_URL, file_permissions_mode=0o666)

CONTROL_FIELDS = [{
                'name': 'modified_by',
                'type': 'character_varying'
                },{
                'name': 'last_modification',
                'type': 'date'
                }]

EXTERNAL_LAYER_SUPPORTED_TYPES = ['WMS', 'WMTS', 'XYZ', 'Bing', 'OSM']

WMTS_MAX_VERSION = '1.0.0'
WMS_MAX_VERSION = '1.3.0'
BING_LAYERS = ['Road','Aerial','AerialWithLabels']

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
        },
        'gvsigol': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}

TEMPORAL_ADVANCED_PARAMETERS = False

LEGACY_GVSIGOL_SERVICES = {
    'ENGINE':'geoserver',
    'URL': 'https://localhost/geoserver',
    'USER': GEOSERVER_USER_DEVEL, # WARNING: Do not write any password here!!!! Store them in 'settings_passwords.py' for local development
    'PASSWORD': GEOSERVER_PW_DEVEL, # WARNING: Do not write any password here!!!! Store them in 'settings_passwords.py' for local development
}

SHARED_VIEW_EXPIRATION_TIME=1 #EN DIAS

CACHE_OPTIONS = {
    'GRID_SUBSETS': ['EPSG:3857', 'EPSG:4326'],
    'FORMATS': ['image/png']
}
