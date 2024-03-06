#!/bin/bash

echo "[INFO]: Start script configure.sh plugin_geoetl"

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

function configure() {

	if [ -z $ETL_URL ]; then
		echo "WARNING: ETL_URL is not defined, using default"					
		ETL_URL='/etlurl'
	fi	
	grep -rl "##ETL_URL##" | xargs sed -i "s ##ETL_URL## $ETL_URL g"

	echo "INFO: DB"	
	if [ -z $ETL_DB_HOST ]; then
		echo "WARNING: ETL_DB_HOST is not defined, using DB_HOST."					
		ETL_DB_HOST=$DB_HOST
	fi
	grep -rl "##ETL_DB_HOST##"  | xargs sed -i "s/##ETL_DB_HOST##/$ETL_DB_HOST/g"
	if [ -z $ETL_DB_NAME ]; then
		echo "WARNING: ETL_DB_NAME is not defined, using database name gvsigonline."					
		ETL_DB_NAME=$DB_NAME
	fi
	grep -rl "##ETL_DB_NAME##"  | xargs sed -i "s/##ETL_DB_NAME##/$ETL_DB_NAME/g"		
	if [ -z $ETL_DB_PORT ]; then
		echo "WARNING: ETL_DB_PORT is not defined, using 5432."					
		ETL_DB_PORT=$DB_PORT
	fi
	grep -rl "##ETL_DB_PORT##"  | xargs sed -i "s/##ETL_DB_PORT##/$ETL_DB_PORT/g"		
	if [ -z $ETL_DB_USER ]; then
		echo "WARNING: ETL_DB_USER is not defined, using gvsigonline"					
		ETL_DB_USER=$DB_USER
	fi
	grep -rl "##ETL_DB_USER##"  | xargs sed -i "s/##ETL_DB_USER##/$ETL_DB_USER/g"		
	if [ -z $ETL_DB_PASSWD ]; then
		echo "WARNING: ETL_DB_PASSWD is not defined, find and replace ##ETL_DB_PASSWD##"					
		ETL_DB_PASSWD=$DB_PASSWD
	fi
	grep -rl "##ETL_DB_PASSWD##"  | xargs sed -i "s/##ETL_DB_PASSWD##/$ETL_DB_PASSWD/g"
}

function move_template() {
	mv settings_tpl.py settings.py
}

move_to_working_dir
configure
move_template
back_from_working_dir
 

echo "[INFO]: End script configure.sh plugin_geoetl"
