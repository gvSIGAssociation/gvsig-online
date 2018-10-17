#!/bin/bash


echo "Running install script for cadastral plugin ..."	
mv settings_tpl.py settings.py

if [ -z $URL_CATASTRO ]; then
			URL_CATASTRO="https://ovc.catastro.meh.es/Cartografia/WMS/ServidorWMS.aspx"
			echo "WARNING: URL_CATASTRO is not defined, using default value $URL_CATASTRO"					
fi	

grep -rl "##URL_CATASTRO##" | xargs sed -i "s ##URL_CATASTRO## $URL_CATASTRO g"

