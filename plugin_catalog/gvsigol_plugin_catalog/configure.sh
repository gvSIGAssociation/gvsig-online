#!/bin/bash

echo "Running install script for catalog plugin ..."
mv settings_tpl.py settings.py
grep -rl "##GEONETWORK_API_URL##" | xargs sed -i "s ##GEONETWORK_API_URL## $GEONETWORK_API_URL g" 
grep -rl "##GEONETWORK_USER##" | xargs sed -i "s/##GEONETWORK_USER##/$GEONETWORK_USER/g"
grep -rl "##GEONETWORK_PASS##" | xargs sed -i "s/##GEONETWORK_PASS##/$GVSIG_ONLINE_PASSWORD/g"





