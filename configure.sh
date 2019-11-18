#!/bin/bash

function configure() {
	echo "INFO: Replace settings from variables ..."
	
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
	
	
	echo "INFO: Replace GVSIGOL_PATH"
	if [ -z $GVSIGOL_PATH ]; then
		echo "WARNING: GVSIGOL_PATH is not defined using, using gvsigonline."	
		GVSIGOL_PATH="gvsigonline"	
	fi
	grep -rl "##GVSIGOL_PATH##"  | xargs sed -i "s ##GVSIGOL_PATH## $GVSIGOL_PATH g"
	grep -rl "/gvsigonline/" | xargs sed -i "s /gvsigonline/ /$GVSIGOL_PATH/ g"
	grep -rl "\^gvsigonline/" | xargs sed -i "s \^gvsigonline/ \^$GVSIGOL_PATH/ g"
	
	
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
	
	#TODO: hay que llevarlo a la app 	
	if [ -z $EMAIL_BACKEND_ACTIVE ]; then
		EMAIL_BACKEND_ACTIVE="False"
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
		echo "WARNING: EMAIL_HOST_PASSWORD is not defined, using GVSIGOL_PASSWD"
		EMAIL_HOST_PASSWORD="$GVSIGOL_PASSWD"
	fi
	grep -rl "##EMAIL_HOST_PASSWORD##"  | xargs sed -i "s ##EMAIL_HOST_PASSWORD## $EMAIL_HOST_PASSWORD g"
	if [ -z $EMAIL_TIMEOUT ]; then
		echo "WARNING: EMAIL_TIMEOUT is not defined, using 60 seconds"
		EMAIL_TIMEOUT=60
	fi
	grep -rl "##EMAIL_TIMEOUT##"  | xargs sed -i "s ##EMAIL_TIMEOUT## $EMAIL_TIMEOUT g"

	
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
	

	#TODO: Pendiente de revisar ...
	if [ -z $LOGOUT_PAGE_URL ]; then
		echo "WARNING: LOGOUT_PAGE_URL is not defined, using default value /gvsigonline"					
		LOGOUT_PAGE_URL="/gvsigonline/"
	fi
	grep -rl "##LOGOUT_PAGE_URL##"  | xargs sed -i "s ##LOGOUT_PAGE_URL## $LOGOUT_PAGE_URL g"

	if [ -z $CELERY_BROKER_URL ]; then
		echo "WARNING: CELERY_BROKER_URL is not defined, deriving one assuming localhost and GVSIGOL_PASSWD"
		CELERY_BROKER_URL="pyamqp://gvsigol:$GVSIGOL_PASSWD@localhost:5672/gvsigol"
	fi
	grep -rl "##CELERY_BROKER_URL##"  | xargs sed -i "s ##CELERY_BROKER_URL## $CELERY_BROKER_URL g"
	
	
	if [ -z $ELEVATION_URL ]; then
		echo "WARNING: ELEVATION_URL is not defined, using empty"					
		ELEVATION_URL=""
	fi												
	grep -rl "##ELEVATION_URL##"  | xargs sed -i "s/##ELEVATION_URL##/$ELEVATION_URL/g"
	
	if [ -z $ELEVATION_LAYER ]; then
		echo "WARNING: ELEVATION_LAYER is not defined, using empty"					
		ELEVATION_LAYER=""
	fi												
	grep -rl "##ELEVATION_LAYER##"  | xargs sed -i "s/##ELEVATION_LAYER##/$ELEVATION_LAYER/g"
	
	
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
}

function move_template() {
	mv gvsigol/settings_tpl.py gvsigol/settings.py
}

configure
move_template
