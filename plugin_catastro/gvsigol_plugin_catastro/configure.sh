#!/bin/bash


echo "Running install script for cadastral plugin ..."
mv settings_tpl.py settings.py

if [ -z $URL_CATASTRO ]; then
			URL_CATASTRO="https://ovc.catastro.meh.es/Cartografia/WMS/ServidorWMS.aspx"
			echo "WARNING: URL_CATASTRO is not defined, using default value $URL_CATASTRO"
fi

grep -rl "##URL_CATASTRO##" | xargs sed -i "s ##URL_CATASTRO## $URL_CATASTRO g"

if [ -z $URL_API_CATASTRO ]; then
			URL_API_CATASTRO="http://ovc.catastro.meh.es/ovcservweb/OVCSWLocalizacionRC"
			echo "WARNING: URL_API_CATASTRO is not defined, using default value $URL_API_CATASTRO"
fi

grep -rl "##URL_API_CATASTRO##" | xargs sed -i "s ##URL_API_CATASTRO## $URL_API_CATASTRO g"

