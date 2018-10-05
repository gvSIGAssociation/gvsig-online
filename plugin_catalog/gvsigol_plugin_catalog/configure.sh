#!/bin/bash

echo "Running install script for catalog plugin ..."
mv settings_tpl.py settings.py

if [ -z "$GEONETWORK_HOST" ]; then
        if [ -n "$FRONTEND_URL" ]; then
                echo "WARNING: GEONETWORK_HOST is not defined, building using FRONTEND_URL."
                GEONETWORK_HOST=$FRONTEND_URL
        else
                echo "WARNING: GEONETWORK_HOST is not defined, building using GVSIGOL_HOST."
                GEONETWORK_HOST=$GVSIGOL_HOST
        fi
fi
grep -rl "##GEONETWORK_HOST##"  | xargs sed -i "s/##GEONETWORK_HOST##/$GEONETWORK_HOST/g"

if [ -z "$CATALOG_BASE_URL" ]; then
        echo "WARNING: CATALOG_BASE_URL is not defined, using HTTP_PROTOCOL and GEONETWORK_HOST ."
        CATALOG_BASE_URL="$HTTP_PROTOCOL://$GEONETWORK_HOST/geonetwork"
fi

if [ -z "$CATALOG_URL" ]; then
        echo "WARNING: CATALOG_URL is not defined, using HTTP_PROTOCOL and GEONETWORK_HOST ."
        CATALOG_URL="$HTTP_PROTOCOL://$GEONETWORK_HOST/geonetwork/srv/eng/"
fi

if [ -z "$CATALOG_API_VERSION" ]; then
        echo "WARNING: CATALOG_API_VERSION is not defined, using 'legacy3.2'."
        CATALOG_API_VERSION="legacy3.2"
fi

if [ -z "$GEONETWORK_USER" ]; then
        echo "WARNING: GEONETWORK_USER is not defined, using 'admin'."
        GEONETWORK_USER="admin"
fi
if [ -z "$GEONETWORK_PASS" ]; then
        if [ -n "$GVSIGOL_PASSWD" ]; then
                echo "WARNING: GEONETWORK_PASS is not defined, using GVSIGOL_PASSWD."
                GEONETWORK_PASS="$GVSIGOL_PASSWD"
        else
                echo "WARNING: GEONETWORK_PASS is not defined, using 'admin'."
                GEONETWORK_PASS="admin"
        fi
fi

# debugging...
echo "CATALOG_API_VERSION" $CATALOG_API_VERSION
echo "CATALOG_URL" $CATALOG_URL
echo "CATALOG_BASE_URL" $CATALOG_BASE_URL
echo "GEONETWORK_USER" $GEONETWORK_USER
echo "GEONETWORK_PASS" $GEONETWORK_PASS

grep -rl "##CATALOG_API_VERSION##"  | xargs sed -i "s ##CATALOG_API_VERSION## $CATALOG_API_VERSION g"
grep -rl "##CATALOG_URL##"  | xargs sed -i "s ##CATALOG_URL## $CATALOG_URL g"
grep -rl "##CATALOG_BASE_URL##" | xargs sed -i "s ##CATALOG_BASE_URL## $CATALOG_BASE_URL g" 
grep -rl "##GEONETWORK_USER##" | xargs sed -i "s/##GEONETWORK_USER##/$GEONETWORK_USER/g"
grep -rl "##GEONETWORK_PASS##" | xargs sed -i "s/##GEONETWORK_PASS##/$GEONETWORK_PASS/g"


