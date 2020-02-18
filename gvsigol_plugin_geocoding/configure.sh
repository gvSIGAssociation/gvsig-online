#!/bin/bash

echo "Running install script for geocoding ..."	
mv settings_tpl.py settings.py
if [ -z "$SOLR_URL" ]; then
	SOLR_URL="http:\/\/localhost:8983\/solr"
	echo "No se ha definido la url de Solr. Se pone una por defecto ... $SOLR_URL"
fi
if [ -z "$GEOCODER_URL" ];then
	GEOCODER_URL="http:\/\/localhost:8080\/geocodersolr"
	echo "No se ha definido la url del geocodificador. Se pone una por defecto ... $GEOCODER_URL"
fi

grep -rl "##SOLR_URL##" | xargs sed -i "s ##SOLR_URL## $SOLR_URL g" 
grep -rl "##GEOCODER_URL##" | xargs sed -i "s ##GEOCODER_URL## $GEOCODER_URL g"
grep -rl "##CARTOCIUDAD_INE_MUN##" | xargs sed -i "s/##CARTOCIUDAD_INE_MUN##/$CARTOCIUDAD_INE_MUN/g"
grep -rl "##GEOCODER_IDEUY_URL##" | xargs sed -i "s ##GEOCODER_IDEUY_URL## $GEOCODER_IDEUY_URL g"






