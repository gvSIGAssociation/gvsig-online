#!/bin/bash

echo "Running install script for print plugin ..."	
mv settings_tpl.py settings.py
if [ -z $PRINT_URL ]; then
	echo "WARNING: PRINT_URL is not defined, using GEOSERVER_HOST"					
	PRINT_URL="/print"
fi	
grep -rl "##PRINT_URL##" | xargs sed -i "s ##PRINT_URL## $PRINT_URL g" 
grep -rl "##PRINT_LEGAL_ADVICE##" | xargs sed -i "s/##PRINT_LEGAL_ADVICE##/$PRINT_LEGAL_ADVICE/g"

