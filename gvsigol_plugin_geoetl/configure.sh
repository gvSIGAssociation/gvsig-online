#!/bin/bash

echo "Running install script for etl plugin ..."	
mv settings_tpl.py settings.py
if [ -z $PRINT_URL ]; then
	echo "WARNING: ETL_URL is not defined, using default"					
	ETL_URL = '/etlurl'
fi	
grep -rl "##ETL_URL##" | xargs sed -i "s ##ETL_URL## $ETL_URL g"

