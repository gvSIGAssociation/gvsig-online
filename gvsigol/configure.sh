#!/bin/bash

echo "[INFO]: Start script configure.sh gvsigol core"


function configure() {
	echo "INFO: Replace settings from variables ...."
	
	#echo "INFO: Replace DEBUG"
	if [ -z $DEBUG ]; then
		echo "WARNING: DEBUG is not defined, using default value True."
		DEBUG=True
	else
		if [ "$DEBUG" = "true" ]; then
			DEBUG=True
		else
			DEBUG=False
		fi
	fi	
	grep -rl "##DEBUG##"  | xargs sed -i "s/##DEBUG##/$DEBUG/g"		

	if [ -z $DEBUG_LEVEL ]; then
			if [ "$DEBUG" = True ] ; then
					echo "WARNING: DEBUG_LEVEL is not defined, using 'DEBUG'."
					DEBUG_LEVEL="DEBUG"
			else
					echo "WARNING: DEBUG_LEVEL is not defined, using 'INFO'."
					DEBUG_LEVEL="INFO"
			fi

	fi
	grep -rl "##DEBUG_LEVEL##"  | xargs sed -i "s/##DEBUG_LEVEL##/$DEBUG_LEVEL/g"	
	
	echo "INFO: Replace GVSIGOL_PATH"
	if [ -z $GVSIGOL_PATH ]; then
		echo "WARNING: GVSIGOL_PATH is not defined using, using gvsigonline."	
		GVSIGOL_PATH="gvsigonline"	
	fi
	echo "INFO: Replace GVSIGOL_NAME"
	if [ -z $GVSIGOL_NAME ]; then
		echo "WARNING: GVSIGOL_NAME is not defined using, using gvsig."	
		GVSIGOL_NAME="gvsig"	
	fi
	echo "INFO: Replace GVSIGOL_SURNAME"
	if [ -z $GVSIGOL_SURNAME ]; then
		echo "WARNING: GVSIGOL_SURNAME is not defined using, using OL."	
		GVSIGOL_SURNAME="OL"	
	fi
	echo "INFO: Replace GVSIGOL_NAME_SHORT"
	if [ -z $GVSIGOL_NAME_SHORT ]; then
		echo "WARNING: GVSIGOL_NAME_SHORT is not defined using, using g."	
		GVSIGOL_NAME_SHORT="g"	
	fi
	echo "INFO: Replace GVSIGOL_SURNAME_SHORT"
	if [ -z $GVSIGOL_SURNAME_SHORT ]; then
	echo "WARNING: GVSIGOL_SURNAME_SHORT is not defined using, using OL."	
		GVSIGOL_SURNAME_SHORT="OL"	
	fi
	echo "INFO: Replace GVSIGOL_CUSTOMER_NAME"
	if [ -z $GVSIGOL_CUSTOMER_NAME ]; then
		echo "WARNING: GVSIGOL_CUSTOMER_NAME is not defined using, using gvsig."	
		GVSIGOL_CUSTOMER_NAME=$GVSIGOL_NAME	
	fi

	grep -rl "##GVSIGOL_PATH##"  | xargs sed -i "s ##GVSIGOL_PATH## $GVSIGOL_PATH g"
	grep -rl "/gvsigonline/" | xargs sed -i "s /gvsigonline/ /$GVSIGOL_PATH/ g"
	grep -rl "\^gvsigonline/" | xargs sed -i "s \^gvsigonline/ \^$GVSIGOL_PATH/ g"
	grep -rl "##GVSIGOL_NAME##"  | xargs sed -i "s ##GVSIGOL_NAME## $GVSIGOL_NAME g"
	grep -rl "##GVSIGOL_SURNAME##"  | xargs sed -i "s ##GVSIGOL_SURNAME## $GVSIGOL_SURNAME g"
	grep -rl "##GVSIGOL_NAME_SHORT##"  | xargs sed -i "s ##GVSIGOL_NAME_SHORT## $GVSIGOL_NAME_SHORT g"
	grep -rl "##GVSIGOL_SURNAME_SHORT##"  | xargs sed -i "s ##GVSIGOL_SURNAME_SHORT## $GVSIGOL_SURNAME_SHORT g"
	grep -rl "##GVSIGOL_CUSTOMER_NAME##"  | xargs sed -i "s/##GVSIGOL_CUSTOMER_NAME##/$GVSIGOL_CUSTOMER_NAME/g"
	
	echo "INFO: Replace GVSIGOL_PLUGINS"
	if [ -z $GVSIGOL_PLUGINS ]; then
		echo "WARNING: GVSIGOL_PLUGINS is not defined."
	fi
	grep -rl "##GVSIGOL_PLUGINS##"  | xargs sed -i "s/##GVSIGOL_PLUGINS##/$GVSIGOL_PLUGINS/g"				
	
	echo "INFO: GVSIGOL_HOME"
	if [ -z $GVSIGOL_HOME ]; then
		echo "WARNING: GVSIGOL_HOME is not defined using, using /opt/gvsigonline."	
		GVSIGOL_HOME="/opt/gvsigonline"	
	fi
	grep -rl "##GVSIGOL_HOME##"  | xargs sed -i "s ##GVSIGOL_HOME## $GVSIGOL_HOME g"		



	echo "INFO: CRS_FROM_SETTINGS"
	if [ -z $CRS_FROM_SETTINGS ]; then
		echo "WARNING: CRS_FROM_SETTINGS is not defined, using default value False"					
		CRS_FROM_SETTINGS="False"
	fi
	grep -rl "##CRS_FROM_SETTINGS##"  | xargs sed -i "s/##CRS_FROM_SETTINGS##/$CRS_FROM_SETTINGS/g"
	grep -rl "##SUPPORTED_CRS##"  | xargs sed -i "s/##SUPPORTED_CRS##/$SUPPORTED_CRS/g" 		
																
	echo "INFO: AUTH_WITH_REMOTE_USER"																
	if [ -z $AUTH_WITH_REMOTE_USER ]; then
		echo "WARNING: AUTH_WITH_REMOTE_USER is not defined, using default value False"					
		AUTH_WITH_REMOTE_USER="False"
	else
		if [ "$AUTH_WITH_REMOTE_USER" = "true" ]; then
			AUTH_WITH_REMOTE_USER=True
		else
			AUTH_WITH_REMOTE_USER=False
		fi		
	fi
	grep -rl "##AUTH_WITH_REMOTE_USER##"  | xargs sed -i "s/##AUTH_WITH_REMOTE_USER##/$AUTH_WITH_REMOTE_USER/g"
	
	if [ -z $MEDIA_ROOT ]; then
		echo "WARNING: MEDIA_ROOT is not defined, using /var/www/media"					
		MEDIA_ROOT="/var/www/media/"
	else
		#Add trailing slash if needed
		length=${#MEDIA_ROOT}
		last_char=${MEDIA_ROOT:length-1:1}
		[[ $last_char != "/" ]] && MEDIA_ROOT="$MEDIA_ROOT/"
	fi	
	grep -rl "##MEDIA_ROOT##"  | xargs sed -i "s ##MEDIA_ROOT## $MEDIA_ROOT g"

	if [ -z $TEMP_ROOT ]; then
		echo "WARNING: TEMP_ROOT is not defined, using /var/tmp"					
		TEMP_ROOT="/var/tmp/"
	fi	
	grep -rl "##TEMP_ROOT##"  | xargs sed -i "s ##TEMP_ROOT## $TEMP_ROOT g"
																																																																																																																																																																																								
	if [ -z $FILEMANAGER_DIR ]; then
		echo "WARNING: FILEMANAGER_DIR is not defined, using /var/www/media/data"					
		FILEMANAGER_DIR="/var/www/media/data"
	fi												
	grep -rl "##FILEMANAGER_DIR##"  | xargs sed -i "s ##FILEMANAGER_DIR## $FILEMANAGER_DIR g"
	
	if [ -z $MEDIA_PATH ]; then
		echo "WARNING: MEDIA_PATH is not defined, using media"					
		MEDIA_PATH="media"
	fi												
	grep -rl "##MEDIA_PATH##"  | xargs sed -i "s ##MEDIA_PATH## $MEDIA_PATH g"

	if [ -z $STATIC_PATH ]; then
		echo "WARNING: STATIC_PATH is not defined, using static"					
		STATIC_PATH="static"
	fi
	grep -rl "##STATIC_PATH##"  | xargs sed -i "s ##STATIC_PATH## $STATIC_PATH g"

	if [ -z $GVSIGOL_DOCS_URL ]; then
		echo "WARNING: GVSIGOL_DOCS_URL is not defined, using /docs/"
		GVSIGOL_DOCS_URL="/docs/"
	fi
	grep -rl "##GVSIGOL_DOCS_URL##"  | xargs sed -i "s ##GVSIGOL_DOCS_URL## $GVSIGOL_DOCS_URL g"

	if [ -z $GVSIGOL_SKIN ]; then
		echo "WARNING: GVSIGOL_SKIN is not defined, using skin-blue"					
		GVSIGOL_SKIN="skin-blue"
	fi												
	grep -rl "##GVSIGOL_SKIN##"  | xargs sed -i "s/##GVSIGOL_SKIN##/$GVSIGOL_SKIN/g"
	
	if [ -z $CACHE_OPERATION_MODE ]; then
		echo "WARNING: CACHE_OPERATION_MODE is not defined, using ONLY_MASTER"					
		CACHE_OPERATION_MODE="ONLY_MASTER"
	fi
	grep -rl "##CACHE_OPERATION_MODE##"  | xargs sed -i "s/##CACHE_OPERATION_MODE##/$CACHE_OPERATION_MODE/g"
	
	if [ -z $GDALTOOLS_BASEPATH ]; then
		echo "WARNING: GDALTOOLS_BASEPATH is not defined, using /usr/bin"					
		GDALTOOLS_BASEPATH="/usr/bin"
	fi														
	grep -rl "##GDALTOOLS_BASEPATH##"  | xargs sed -i "s ##GDALTOOLS_BASEPATH## $GDALTOOLS_BASEPATH g"
	if [ -z $OGR2OGR_PATH ]; then
		echo "WARNING: OGR2OGR_PATH is not defined, using $GDALTOOLS_BASEPATH/ogr2ogr"					
		OGR2OGR_PATH="$GDALTOOLS_BASEPATH/ogr2ogr"
	fi														
	grep -rl "##OGR2OGR_PATH##"  | xargs sed -i "s ##OGR2OGR_PATH## $OGR2OGR_PATH g"
	if [ -z $GDAL_LIBRARY_PATH ]; then
		echo "WARNING: GDAL_LIBRARY_PATH is not defined, using /lib64/libgdal.so.1"					
		GDAL_LIBRARY_PATH="/lib64/libgdal.so.1"
	fi														
	grep -rl "##GDAL_LIBRARY_PATH##"  | xargs sed -i "s ##GDAL_LIBRARY_PATH## $GDAL_LIBRARY_PATH g"
	
	#TODO: hay que llevarlo a la app 	
	if [ -z $EMAIL_BACKEND_ACTIVE ]; then
		EMAIL_BACKEND_ACTIVE="True"
	else
		if [ "$EMAIL_BACKEND_ACTIVE" = "true" ]; then
			EMAIL_BACKEND_ACTIVE=True
		else
			EMAIL_BACKEND_ACTIVE=False
		fi		
	fi
	grep -rl "##EMAIL_BACKEND_ACTIVE##"  | xargs sed -i "s/##EMAIL_BACKEND_ACTIVE##/$EMAIL_BACKEND_ACTIVE/g"
	if [ -z $EMAIL_USE_TLS ]; then
		EMAIL_USE_TLS="True"
	else
		if [ "$EMAIL_USE_TLS" = "true" ]; then
			EMAIL_USE_TLS=True
		else
			EMAIL_USE_TLS=False
		fi		
	fi
	grep -rl "##EMAIL_USE_TLS##"  | xargs sed -i "s/##EMAIL_USE_TLS##/$EMAIL_USE_TLS/g"
	if [ -z $EMAIL_HOST ]; then
		echo "WARNING: EMAIL_HOST is not defined, assuming localhost"
		EMAIL_HOST="localhost"
	fi
	grep -rl "##EMAIL_HOST##"  | xargs sed -i "s ##EMAIL_HOST## $EMAIL_HOST g"
	if [ -z $EMAIL_HOST_USER ]; then
		echo "WARNING: EMAIL_HOST_USER is not defined, assuming 'gvsigol'"
		EMAIL_HOST="gvsigol"
	fi
	grep -rl "##EMAIL_HOST_USER##"  | xargs sed -i "s ##EMAIL_HOST_USER## $EMAIL_HOST_USER g"
	if [ -z $EMAIL_HOST_PASSWORD ]; then
		echo "WARNING: EMAIL_HOST_PASSWORD is not defined"
	fi
	grep -rl "##EMAIL_HOST_PASSWORD##"  | xargs sed -i "s ##EMAIL_HOST_PASSWORD## $EMAIL_HOST_PASSWORD g"
	if [ -z $EMAIL_TIMEOUT ]; then
		echo "WARNING: EMAIL_TIMEOUT is not defined, using 60 seconds"
		EMAIL_TIMEOUT=60
	fi
	grep -rl "##EMAIL_TIMEOUT##"  | xargs sed -i "s ##EMAIL_TIMEOUT## $EMAIL_TIMEOUT g"
	grep -rl "##EMAIL_PORT##"  | xargs sed -i "s ##EMAIL_PORT## $EMAIL_PORT g"
	
	
	#TODO: hay que llevarlo a la app 
	if [ "$LANGUAGES" = "" ]; then
		LANGUAGES="('en', _('English')), ('es', _('Spanish'))"
	fi
	grep -rl "##LANGUAGES##"  | xargs sed -i "s/##LANGUAGES##/$LANGUAGES/g"
	
	#TODO: deberia estar en el plugin (de momento shap_folder)
	if [ -z $CRONTAB_ACTIVE ]; then
		echo "WARNING: CRONTAB_ACTIVE is not defined, using default value False"					
		CRONTAB_ACTIVE="False"
	fi
	grep -rl "##CRONTAB_ACTIVE##"  | xargs sed -i "s/##CRONTAB_ACTIVE##/$CRONTAB_ACTIVE/g"
	

	if [ -z $LOGOUT_REDIRECT_URL ]; then
		echo "WARNING: LOGOUT_REDIRECT_URL is not defined, using default value 'index'"
		LOGOUT_REDIRECT_URL="index" # normally this is equivalent to /gvsigonline"
	fi
	grep -rl "##LOGOUT_REDIRECT_URL##"  | xargs sed -i "s ##LOGOUT_REDIRECT_URL## $LOGOUT_REDIRECT_URL g"

	if [ -z $CELERY_BROKER_URL ]; then
		echo "WARNING: CELERY_BROKER_URL is not defined, deriving one assuming localhost and GVSIGOL_PASSWD"
		if jq --version > /dev/null ; then
			RABBITMQ_PASS=`echo "$GVSIGOL_PASSWD" | jq -Rr @uri`
		else
			echo "WARNING: jq command is not available. RABBITMQ pass may not be correctly escaped"
			RABBITMQ_PASS="$GVSIGOL_PASSWD"
		fi
		CELERY_BROKER_URL="pyamqp://gvsigol:$RABBITMQ_PASS@localhost:5672/gvsigol"
	fi
	grep -rl "##CELERY_BROKER_URL##"  | xargs sed -i "s ##CELERY_BROKER_URL## $CELERY_BROKER_URL g"
	
	
	grep -rl "##GEOSERVER_CLUSTER_NODES##"  | xargs sed -i "s ##GEOSERVER_CLUSTER_NODES## $GEOSERVER_CLUSTER_NODES g"						
	grep -rl "##GVSIGOL_TOOLS##"  | xargs sed -i "s/##GVSIGOL_TOOLS##/$GVSIGOL_TOOLS/g" 
	grep -rl "##IP_FO##"  | xargs sed -i "s/##IP_FO##/$IP_FO/g" | true
	grep -rl "##IP_NODE0##"  | xargs sed -i "s/##IP_NODE0##/$IP_NODE0/g"  | true
	grep -rl "##IP_NODE1##"  | xargs sed -i "s/##IP_NODE1##/$IP_NODE1/g"  | true
	grep -rl "##SSL_CERTIFICATE_PATH##"  | xargs sed -i "s/##SSL_CERTIFICATE_PATH##/$SSL_CERTIFICATE_PATH/g"  | true
	if [ -z $GVSIGOL_ENABLE_ENUMERATIONS ]; then
		echo "WARNING: GVSIGOL_ENABLE_ENUMERATIONS is not defined, using default value True"					
		GVSIGOL_ENABLE_ENUMERATIONS="True"
	fi
	grep -rl "##GVSIGOL_ENABLE_ENUMERATIONS##"  | xargs sed -i "s/##GVSIGOL_ENABLE_ENUMERATIONS##/$GVSIGOL_ENABLE_ENUMERATIONS/g"
	grep -rl "##CONTEXT_PROCESSORS##"  | xargs sed -i "s/##CONTEXT_PROCESSORS##/$CONTEXT_PROCESSORS/g"  | true
	
	# sustituye nombre de la aplicacion
	grep -rl "##GVSIGOL_NAME##"  | xargs sed -i "s/##GVSIGOL_NAME##/$GVSIGOL_NAME/g"  | true
	grep -rl "##GVSIGOL_SURNAME##"  | xargs sed -i "s/##GVSIGOL_SURNAME##/$GVSIGOL_SURNAME/g"  | true
	grep -rl "##GVSIGOL_NAME_SHORT##"  | xargs sed -i "s/##GVSIGOL_NAME_SHORT##/$GVSIGOL_NAME_SHORT/g"  | true
	grep -rl "##GVSIGOL_SURNAME_SHORT##"  | xargs sed -i "s/##GVSIGOL_SURNAME_SHORT##/$GVSIGOL_SURNAME_SHORT/g"  | true

	# max zoom levels
	if [ -z $MAX_ZOOM_LEVELS ]; then
		echo "WARNING: MAX_ZOOM_LEVELS is not defined, using default value 21"					
		MAX_ZOOM_LEVELS="21"
	fi
	grep -rl "##MAX_ZOOM_LEVELS##"  | xargs sed -i "s/##MAX_ZOOM_LEVELS##/$MAX_ZOOM_LEVELS/g"  | true
	
	if [ -z $TEMPORAL_ADVANCED_PARAMETERS ]; then
		echo "WARNING: TEMPORAL_ADVANCED_PARAMETERS is not defined, using default value False"					
		TEMPORAL_ADVANCED_PARAMETERS="False"
	fi
	grep -rl "##TEMPORAL_ADVANCED_PARAMETERS##"  | xargs sed -i "s/##TEMPORAL_ADVANCED_PARAMETERS##/$TEMPORAL_ADVANCED_PARAMETERS/g"

	echo "INFO: Replace ALLOWED_HOST_NAMES"
	if [ -z $ALLOWED_HOST_NAMES ]; then
		echo "WARNING: ALLOWED_HOST_NAMES is not defined. Using BASE_URL"
		ALLOWED_HOST_NAMES="'${BASE_URL}'"
	fi
	grep -rl "##ALLOWED_HOST_NAMES##"  | xargs sed -i "s!##ALLOWED_HOST_NAMES##!$ALLOWED_HOST_NAMES!g"

	echo "INFO: Replace CSRF_TRUSTED_ORIGINS"
	if [ -z $CSRF_TRUSTED_ORIGINS ]; then
		echo "WARNING: CSRF_TRUSTED_ORIGINS is not defined. Using GVSIGOL_HOST"
		CSRF_TRUSTED_ORIGINS="'${GVSIGOL_HOST}'"
	fi
	grep -rl "##CSRF_TRUSTED_ORIGINS##"  | xargs sed -i "s!##CSRF_TRUSTED_ORIGINS##!$CSRF_TRUSTED_ORIGINS!g"
	echo "INFO: Replace CORS_ALLOWED_ORIGINS"
	if [ -z $CORS_ALLOWED_ORIGINS ]; then
		echo "WARNING: CORS_ALLOWED_ORIGINS is not defined. Using BASE_URL"
		CORS_ALLOWED_ORIGINS="'${BASE_URL}'"
	fi
	grep -rl "##CORS_ALLOWED_ORIGINS##"  | xargs sed -i "s!##CORS_ALLOWED_ORIGINS##!$CORS_ALLOWED_ORIGINS!g"

	echo "INFO: CHECK_TILELOAD_ERROR"																
	if [ -z $CHECK_TILELOAD_ERROR ]; then
		echo "WARNING: CHECK_TILELOAD_ERROR is not defined, using default value True"					
		CHECK_TILELOAD_ERROR=True
	else
		if [ "$CHECK_TILELOAD_ERROR" = "true" ]; then
			CHECK_TILELOAD_ERROR=True
		else
			CHECK_TILELOAD_ERROR=False
		fi		
	fi
	grep -rl "##CHECK_TILELOAD_ERROR##"  | xargs sed -i "s/##CHECK_TILELOAD_ERROR##/$CHECK_TILELOAD_ERROR/g"
	if [ -z $GVSIGOL_AUTH_BACKEND ]; then
		echo "WARNING: GVSIGOL_AUTH_BACKEND is not defined, using 'gvsigol_auth'"
		GVSIGOL_AUTH_BACKEND="gvsigol_auth"
	fi
	grep -rl "##GVSIGOL_AUTH_BACKEND##"  | xargs sed -i "s/##GVSIGOL_AUTH_BACKEND##/$GVSIGOL_AUTH_BACKEND/g"
	if [ $GVSIGOL_AUTH_BACKEND = "gvsigol_plugin_oidc_mozilla" ]; then
		if [ -z $DRF_DEFAULT_AUTHENTICATION_CLASSES ]; then
			echo "WARNING: DRF_DEFAULT_AUTHENTICATION_CLASSES is not defined and GVSIGOL_AUTH_BACKEND is 'gvsigol_plugin_oidc_mozilla' , using 'mozilla_django_oidc.contrib.drf.OIDCAuthentication','rest_framework.authentication.SessionAuthentication'"
			DRF_DEFAULT_AUTHENTICATION_CLASSES="'mozilla_django_oidc.contrib.drf.OIDCAuthentication','rest_framework.authentication.SessionAuthentication'"
		fi
		if [ -z $DJANGO_AUTHENTICATION_BACKENDS ]; then
			echo "WARNING: DJANGO_AUTHENTICATION_BACKENDS is not defined, using 'django.contrib.auth.backends.RemoteUserBackend',\n    'django_auth_ldap.backend.LDAPBackend',\n    'django.contrib.auth.backends.ModelBackend'"
			DJANGO_AUTHENTICATION_BACKENDS="'gvsigol_plugin_oidc_mozilla.oidc.GvsigolOIDCAuthenticationBackend',\n    'django.contrib.auth.backends.ModelBackend'"
		fi
	else
		if [ -z $DRF_DEFAULT_AUTHENTICATION_CLASSES ]; then
			echo "WARNING: DRF_DEFAULT_AUTHENTICATION_CLASSES is not defined and GVSIGOL_AUTH_BACKEND is $GVSIGOL_AUTH_BACKEND , using 'rest_framework_jwt.authentication.JSONWebTokenAuthentication'"
			DRF_DEFAULT_AUTHENTICATION_CLASSES="'rest_framework_jwt.authentication.JSONWebTokenAuthentication',\n        'rest_framework.authentication.SessionAuthentication',\n        'rest_framework.authentication.BasicAuthentication'"
		fi
		if [ -z $DJANGO_AUTHENTICATION_BACKENDS ]; then
			echo "WARNING: DJANGO_AUTHENTICATION_BACKENDS is not defined, using 'django.contrib.auth.backends.RemoteUserBackend',\n    'django_auth_ldap.backend.LDAPBackend'"
			DJANGO_AUTHENTICATION_BACKENDS="'django.contrib.auth.backends.RemoteUserBackend',\n    'django_auth_ldap.backend.LDAPBackend'"
		fi
	fi
	grep -rl "##DJANGO_AUTHENTICATION_BACKENDS##"  | xargs sed -i "s/##DJANGO_AUTHENTICATION_BACKENDS##/$DJANGO_AUTHENTICATION_BACKENDS/g"
	grep -rl "##DRF_DEFAULT_AUTHENTICATION_CLASSES##"  | xargs sed -i "s/##DRF_DEFAULT_AUTHENTICATION_CLASSES##/$DRF_DEFAULT_AUTHENTICATION_CLASSES/g"
	if [ -z $GVSIGOL_AUTH_MIDDLEWARE ]; then
		echo "WARNING: GVSIGOL_AUTH_MIDDLEWARE is not defined, using ''"
		GVSIGOL_AUTH_MIDDLEWARE=""
	fi
	grep -rl "##GVSIGOL_AUTH_MIDDLEWARE##"  | xargs sed -i "s/##GVSIGOL_AUTH_MIDDLEWARE##/$GVSIGOL_AUTH_MIDDLEWARE/g"
	if [ -z $AUTH_DASHBOARD_UI ]; then
		echo "WARNING: AUTH_DASHBOARD_UI is not defined, using 'True'"
		AUTH_DASHBOARD_UI="True"
	fi
	grep -rl "##AUTH_DASHBOARD_UI##"  | xargs sed -i "s/##AUTH_DASHBOARD_UI##/$AUTH_DASHBOARD_UI/g"
	if [ -z $AUTH_READONLY_USERS ]; then
		echo "WARNING: AUTH_READONLY_USERS is not defined, using 'False'"
		AUTH_READONLY_USERS="False"
	fi
	grep -rl "##AUTH_READONLY_USERS##"  | xargs sed -i "s/##AUTH_READONLY_USERS##/$AUTH_READONLY_USERS/g"
	if [ -z $USE_X_FORWARDED_HOST ]; then
		echo "WARNING: USE_X_FORWARDED_HOST is not defined, using 'False'"
		USE_X_FORWARDED_HOST="False"
	fi
	grep -rl "##USE_X_FORWARDED_HOST##"  | xargs sed -i "s/##USE_X_FORWARDED_HOST##/$USE_X_FORWARDED_HOST/g"
	if [ -z $SECURE_PROXY_SSL_HEADER ]; then
		echo "WARNING: SECURE_PROXY_SSL_HEADER is not defined, using None"
		SECURE_PROXY_SSL_HEADER="None"
	fi
	grep -rl "##SECURE_PROXY_SSL_HEADER##"  | xargs sed -i "s/##SECURE_PROXY_SSL_HEADER##/$SECURE_PROXY_SSL_HEADER/g"
	if [ -z $SHP_DOWNLOAD_DEFAULT_ENCODING ]; then
		echo "WARNING: SHP_DOWNLOAD_DEFAULT_ENCODING is not defined, using 'ISO-8859-1'"
		SHP_DOWNLOAD_DEFAULT_ENCODING="ISO-8859-1"
	fi
	grep -rl "##SHP_DOWNLOAD_DEFAULT_ENCODING##"  | xargs sed -i "s/##SHP_DOWNLOAD_DEFAULT_ENCODING##/$SHP_DOWNLOAD_DEFAULT_ENCODING/g"
	if [ -z $DATA_UPLOAD_MAX_MEMORY_SIZE ]; then
		echo "WARNING: DATA_UPLOAD_MAX_MEMORY_SIZE is not defined, using '26214400'"
		DATA_UPLOAD_MAX_MEMORY_SIZE="26214400"
	fi
	grep -rl "##DATA_UPLOAD_MAX_MEMORY_SIZE##"  | xargs sed -i "s/##DATA_UPLOAD_MAX_MEMORY_SIZE##/$DATA_UPLOAD_MAX_MEMORY_SIZE/g"


    ##################################
	# SPA frontend related variables #
	if [ -z $FRONTEND_BASE_URL ]; then
		echo "WARNING: FRONTEND_BASE_URL is not defined, using '/spa/'"
		FRONTEND_BASE_URL="/spa"
	fi
	grep -rl "##FRONTEND_BASE_URL##"  | xargs sed -i "s ##FRONTEND_BASE_URL## $FRONTEND_BASE_URL g"
	# redirect to new frontend
	if [ -z $FRONTEND_REDIRECT_URL ]; then
		echo "WARNING: FRONTEND_REDIRECT_URL is not defined, setting empty"
		FRONTEND_REDIRECT_URL=""
	fi
	grep -rl "##FRONTEND_REDIRECT_URL##"  | xargs sed -i "s ##FRONTEND_REDIRECT_URL## $FRONTEND_REDIRECT_URL g"
	if [ -z $USE_SPA_PROJECT_LINKS ]; then
		USE_SPA_PROJECT_LINKS=""
	fi
	grep -rl "##USE_SPA_PROJECT_LINKS##"  | xargs sed -i "s ##USE_SPA_PROJECT_LINKS## $USE_SPA_PROJECT_LINKS g"
	if [ -z $LANGUAGE_CODE ]; then
		echo "WARNING: LANGUAGE_CODE is not defined, using 'es'"
		LANGUAGE_CODE="es"
	fi
	grep -l "##LANGUAGE_CODE##" gvsigol/settings_tpl.py | xargs sed -i "s ##LANGUAGE_CODE## $LANGUAGE_CODE g"

	if [ -z $GEOSERVER_USE_KEEPALIVE ]; then
		echo "WARNING: GEOSERVER_USE_KEEPALIVE is not defined, using 'True'"
		GEOSERVER_USE_KEEPALIVE="True"
	fi
	grep -rl "##GEOSERVER_USE_KEEPALIVE##"  | xargs sed -i "s/##GEOSERVER_USE_KEEPALIVE##/$GEOSERVER_USE_KEEPALIVE/g"

}

function move_template() {	
	mv gvsigol/settings_tpl.py gvsigol/settings.py
}

function move_to_working_dir()
{
    DIR="$(dirname "$0")"
    pushd $DIR
    echo "[INFO]: Working dir $PWD"
}
function back_from_working_dir()
{
    popd
    echo "[INFO]: Back to $PWD"
}

move_to_working_dir
configure
move_template
back_from_working_dir

echo "[INFO]: End script configure.sh gvsigol core"
