#!/bin/bash

echo "Running install script for catalog plugin ..."
mv settings_tpl.py settings.py

if [ -z $GEONETWORK_HOST ]; then
        echo "WARNING: GEONETWORK_HOST is not defined, building using GVSIGOL_HOST ."
        GEONETWORK_HOST=$GVSIGOL_HOST
fi
grep -rl "##GEONETWORK_HOST##"  | xargs sed -i "s/##GEONETWORK_HOST##/$GEONETWORK_HOST/g"

if [ -z $GEONETWORK_BASE_URL ]; then
        echo "WARNING: GEONETWORK_BASE_URL is not defined, using HTTP_PROTOCOL and GEONETWORK_HOST ."
        GEONETWORK_BASE_URL="$HTTP_PROTOCOL://$GEONETWORK_HOST/geonetwork"
fi

if [ -z $GEONETWORK_URL ]; then
        echo "WARNING: GEONETWORK_URL is not defined, using HTTP_PROTOCOL and GEONETWORK_HOST ."
        GEONETWORK_URL="$HTTP_PROTOCOL://$GEONETWORK_HOST/geonetwork/srv/eng/"
fi

if [ -z $CATALOG_API_VERSION ]; then
        echo "WARNING: CATALOG_API_VERSION is not defined, using 'legacy3.2'."
        CATALOG_API_VERSION="legacy3.2"
fi
grep -rl "##CATALOG_API_VERSION##"  | xargs sed -i "s ##CATALOG_API_VERSION## $CATALOG_API_VERSION g"


grep -rl "##GEONETWORK_URL##"  | xargs sed -i "s ##GEONETWORK_URL## $GEONETWORK_URL g"
grep -rl "##GEONETWORK_BASE_URL##" | xargs sed -i "s ##GEONETWORK_BASE_URL## $GEONETWORK_BASE_URL g" 
grep -rl "##GEONETWORK_API_VERSION##" | xargs sed -i "s ##GEONETWORK_API_VERSION## $GEONETWORK_API_VERSION g" 
grep -rl "##GEONETWORK_USER##" | xargs sed -i "s/##GEONETWORK_USER##/$GEONETWORK_USER/g"
grep -rl "##GEONETWORK_PASS##" | xargs sed -i "s/##GEONETWORK_PASS##/$GVSIG_ONLINE_PASSWORD/g"





