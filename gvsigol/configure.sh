#!/bin/bash

function configure() {
	echo "INFO: Replace settings from variables ..."
	#cd $WORKSPACE
	echo "INFO: Replace DEBUG"
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
	
	echo "INFO: Replace HTTP_PROTOCOL"											
	if [ -z $HTTP_PROTOCOL ]; then
		echo "WARNING: HTTP_PROTOCOL is not defined, using https."
		HTTP_PROTOCOL="https"
	fi
	
	echo "INFO: Replace GVSIGOL_PATH"
	if [ -z $GVSIGOL_PATH ]; then
		echo "WARNING: GVSIGOL_PATH is not defined using, using gvsigonline."	
		GVSIGOL_PATH="gvsigonline"	
	fi
	grep -rl "##GVSIGOL_PATH##"  | xargs sed -i "s ##GVSIGOL_PATH## $GVSIGOL_PATH g"
	grep -rl "/gvsigonline/" | xargs sed -i "s /gvsigonline/ /$GVSIGOL_PATH/ g"
	grep -rl "\^gvsigonline/" | xargs sed -i "s \^gvsigonline/ \^$GVSIGOL_PATH/ g"
	
	echo "INFO: Replace GVSIGOL_HOST"
	if [ -z $GVSIGOL_HOST ]; then
		echo "ERROR: GVSIGOL_HOST is not defined."
		exit -1 
	else
		grep -rl "##GVSIGOL_HOST##"  | xargs sed -i "s/##GVSIGOL_HOST##/$GVSIGOL_HOST/g"			
		BASE_URL="$HTTP_PROTOCOL:\/\/$GVSIGOL_HOST"
		grep -rl "##BASE_URL##"  | xargs sed -i "s ##BASE_URL## $BASE_URL g"	
	fi	
	
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

	echo "INFO: GVSIGOL_PASSWD"		
	if [ -z $GVSIGOL_PASSWD ]; then
		echo "WARNING: GVSIGOL_PASSWD is not defined, find and replace ##GVSIGOL_PASSWD##"
		GVSIGOL_PASSWD="##GVSIGOL_PASSWD##"
	else
		grep -rl "##GVSIGOL_PASSWD##"  | xargs sed -i "s/##GVSIGOL_PASSWD##/$GVSIGOL_PASSWD/g"								
	fi	
	
	echo "INFO: FRONTEND_URL"
	if [ -z $FRONTEND_URL ]; then
		echo "WARNING: FRONTEND_URL is not defined, using externo.gva.es ..."
		FRONTEND_URL="externo.gva.es"
	fi
	grep -rl "##FRONTEND_URL##"  | xargs sed -i "s ##FRONTEND_URL## $FRONTEND_URL g"								

	echo "INFO: GEOSERVER_HOST "		
	if [ -z $GEOSERVER_HOST ]; then
		echo "WARNING: GEOSERVER_HOST is not defined, using GVSIGOL_HOST ."
		GEOSERVER_HOST=$GVSIGOL_HOST
	fi
	grep -rl "##GEOSERVER_HOST##"  | xargs sed -i "s/##GEOSERVER_HOST##/$GEOSERVER_HOST/g"

	if [ -z $GEOSERVER_DATA_DIR ]; then
		echo "WARNING: GEOSERVER_DATA_DIR is not defined, using '/var/lib/geoserver_data' ."
		GEOSERVER_DATA_DIR=/var/lib/geoserver_data
	fi
	grep -rl "##GEOSERVER_DATA_DIR##"  | xargs sed -i "s/##GEOSERVER_DATA_DIR##/$GEOSERVER_DATA_DIR/g"
	
	echo "INFO: GEOSERVER_REST_URL"	
	if [ -z $GEOSERVER_REST_URL ]; then
		echo "WARNING: GEOSERVER_REST_URL is not defined, using HTTP_PROTOCOL and GEOSERVER_HOST ."
		GEOSERVER_REST_URL="$HTTP_PROTOCOL://$GEOSERVER_HOST/geoserver/rest"
	fi
	GEOSERVER_BASE_URL="$HTTP_PROTOCOL://$GVSIGOL_HOST/geoserver"
	GEOWEBCACHE_REST_URL="$HTTP_PROTOCOL://$GVSIGOL_HOST/geoserver/gwc/rest"
	grep -rl "##GEOSERVER_BASE_URL##"  | xargs sed -i "s ##GEOSERVER_BASE_URL## $GEOSERVER_BASE_URL g"
	grep -rl "##GEOWEBCACHE_REST_URL##"  | xargs sed -i "s ##GEOWEBCACHE_REST_URL## $GEOWEBCACHE_REST_URL g"
	
	echo "INFO: GEOSERVER_PASSWD"
	if [ -z $GEOSERVER_PASSWD ]; then
		echo "WARNING: GEOSERVER_PASSWD is not defined, find and replace ##GEOSERVER_PASSWD##."
		GEOSERVER_PASSWD="##GEOSERVER_PASSWD##"
	fi
	grep -rl "##GEOSERVER_PASSWD##"  | xargs sed -i "s/##GEOSERVER_PASSWD##/$GEOSERVER_PASSWD/g"

	echo "INFO: LDAP"		
	if [ -z $LDAP_HOST ]; then
		echo "WARNING: LDAP_HOST is not defined, using GVSIGOL_HOST."		
		LDAP_HOST=$GVSIGOL_HOST
	fi
	grep -rl "##LDAP_HOST##"  | xargs sed -i "s/##LDAP_HOST##/$LDAP_HOST/g"	
		
	if [ -z $LDAP_PORT ]; then
		echo "WARNING: LDAP_PORT is not defined, using 389"					
		LDAP_PORT="389"
	fi
	grep -rl "##LDAP_PORT##"  | xargs sed -i "s/##LDAP_PORT##/$LDAP_PORT/g"				
	if [ -z $LDAP_ROOT_DN ]; then
		echo "WARNING: LDAP_ROOT_DN is not defined, using dc=local,dc=gvsigonline,dc=com"					
		LDAP_ROOT_DN="dc=local,dc=gvsigonline,dc=com"
	fi
	grep -rl "##LDAP_ROOT_DN##"  | xargs sed -i "s/##LDAP_ROOT_DN##/$LDAP_ROOT_DN/g"						
	if [ -z $LDAP_BIND_USER ]; then
		echo "WARNING: LDAP_BIND_USER is not defined, using cn=admin,$LDAP_ROOT_DN."					
		LDAP_BIND_USER="cn=admin,$LDAP_ROOT_DN"
	fi
	grep -rl "##LDAP_BIND_USER##"  | xargs sed -i "s/##LDAP_BIND_USER##/$LDAP_BIND_USER/g"		
	if [ -z $LDAP_BIND_PASSWD ]; then
		echo "WARNING: LDAP_BIND_PASSWD is not defined, find and replace ##LDAP_BIND_PASSWD##."					
		LDAP_BIND_PASSWD="##LDAP_BIND_PASSWD##"
	fi
	grep -rl "##LDAP_BIND_PASSWD##"  | xargs sed -i "s/##LDAP_BIND_PASSWD##/$LDAP_BIND_PASSWD/g"		
	
	grep -rl "##LDAP_AD_SUFFIX##"  | xargs sed -i "s/##LDAP_AD_SUFFIX##/$LDAP_AD_SUFFIX/g" 
	
	echo "INFO: DB"	
	if [ -z $DB_HOST ]; then
		echo "WARNING: DB_HOST is not defined, using GVSIGOL_HOST."					
		DB_HOST=$GVSIGOL_HOST
	fi
	grep -rl "##DB_HOST##"  | xargs sed -i "s/##DB_HOST##/$DB_HOST/g"
	if [ -z $DB_NAME ]; then
		echo "WARNING: DB_NAME is not defined, using database name gvsigonline."					
		DB_NAME="gvsigonline"
	fi
	grep -rl "##DB_NAME##"  | xargs sed -i "s/##DB_NAME##/$DB_NAME/g"		
	if [ -z $DB_PORT ]; then
		echo "WARNING: DB_PORT is not defined, using 5432."					
		DB_PORT="5432"
	fi
	grep -rl "##DB_PORT##"  | xargs sed -i "s/##DB_PORT##/$DB_PORT/g"		
	if [ -z $DB_USER ]; then
		echo "WARNING: DB_USER is not defined, using gvsigonline"					
		DB_USER="gvsigonline"
	fi
	grep -rl "##DB_USER##"  | xargs sed -i "s/##DB_USER##/$DB_USER/g"		
	if [ -z $DB_PASSWD ]; then
		echo "WARNING: DB_PASSWD is not defined, find and replace ##DB_PASSWD##"					
		DB_PASSWD="##DB_PASSWD##"
	fi
	grep -rl "##DB_PASSWD##"  | xargs sed -i "s/##DB_PASSWD##/$DB_PASSWD/g"		

	if [ -z $DB_SCHEMA ]; then
		echo "WARNING: DB_SCHEMA is not defined, using public"					
		DB_SCHEMA="public"
	fi
	grep -rl "##DB_SCHEMA##"  | xargs sed -i "s/##DB_SCHEMA##/$DB_SCHEMA/g"		

	echo "INFO: CRS_FROM_SETTINGS"
	if [ -z $CRS_FROM_SETTINGS ]; then
		echo "WARNING: CRS_FROM_SETTINGS is not defined, using default value False"					
		CRS_FROM_SETTINGS="False"
	fi
	grep -rl "##CRS_FROM_SETTINGS##"  | xargs sed -i "s/##CRS_FROM_SETTINGS##/$CRS_FROM_SETTINGS/g"
	grep -rl "##SUPORTED_CRS##"  | xargs sed -i "s/##SUPORTED_CRS##/$SUPORTED_CRS/g" 		
																
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
		MEDIA_PATH="static"
	fi												
	grep -rl "##STATIC_PATH##"  | xargs sed -i "s ##STATIC_PATH## $STATIC_PATH g"

	
	if [ -z $GVSIGOL_SKIN ]; then
		echo "WARNING: GVSIGOL_SKIN is not defined, using skin-blue"					
		GVSIGOL_SKIN="skin-blue"
	fi												
	grep -rl "##GVSIGOL_SKIN##"  | xargs sed -i "s/##GVSIGOL_SKIN##/$GVSIGOL_SKIN/g"
	
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
	grep -rl "##GEOSERVER_CLUSTER_NODES##"  | xargs sed -i "s/##GEOSERVER_CLUSTER_NODES##/$GEOSERVER_CLUSTER_NODES/g"						
	grep -rl "##LOGOUT_PAGE_URL##"  | xargs sed -i "s ##LOGOUT_PAGE_URL## $LOGOUT_PAGE_URL g"
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
			
}

function move_template() {
	mv gvsigol/settings_tpl.py gvsigol/settings.py
}

configure
move_template
