#!/bin/bash

echo "Running install script for catalog plugin ..."
mv settings_tpl.py settings.py

if [ -z "$DOWNLOADMANAGER_TMP_DIR" ]; then
        echo "WARNING: DOWNLOADMANAGER_TMP_DIR is not defined, using '/var/tmp/downloadman' ."
        DOWNLOADMANAGER_TMP_DIR="/var/tmp/downloadman"
fi

if [ -z "$DOWNLOADMANAGER_TARGET_ROOT" ]; then
        echo "WARNING: DOWNLOADMANAGER_TARGET_ROOT is not defined, using '/var/www/media/data/downloads'."
        DOWNLOADMANAGER_TARGET_ROOT="/var/www/media/data/downloads"
fi

if [ -z "$DOWNLOADMANAGER_TARGET_URL" ]; then
        echo "WARNING: DOWNLOADMANAGER_TARGET_URL is not defined, deriving from 'BASE_URL'."
        DOWNLOADMANAGER_TARGET_URL="$BASE_URL/media/data/downloads"
fi

if [ -z "$DOWNLOADMANAGER_DOWNLOADS_ROOT" ]; then
        echo "WARNING: DOWNLOADMANAGER_DOWNLOADS_ROOT is not defined, using '/var/www/media/data/downloads'."
        DOWNLOADMANAGER_DOWNLOADS_ROOT="/var/www/media/data/downloads"
fi

if [ -z "$DOWNLOADS_URL" ]; then
        echo "WARNING: DOWNLOADS_URL is not defined, deriving from 'BASE_URL'."
        DOWNLOADS_URL="$BASE_URL/media/data/downloads"
fi

if [ -z "$DOWNLOADMANAGER_LOCAL_PATHS_WHITELIST" ]; then
        echo "WARNING: DOWNLOADMANAGER_LOCAL_PATHS_WHITELIST is not defined, using DOWNLOADMANAGER_TARGET_ROOT."
        DOWNLOADMANAGER_LOCAL_PATHS_WHITELIST="$DOWNLOADMANAGER_TARGET_ROOT"
fi

if [ -z "$DOWNMAN_XSEND_BASEURL" ]; then
        echo "WARNING: DOWNMAN_XSEND_BASEURL is not defined, using empty string."
        DOWNMAN_XSEND_BASEURL=""
fi

# debugging...
echo "DOWNLOADMANAGER_TMP_DIR" $DOWNLOADMANAGER_TMP_DIR
echo "DOWNLOADMANAGER_TARGET_ROOT" $DOWNLOADMANAGER_TARGET_ROOT
echo "DOWNLOADMANAGER_TARGET_URL" $DOWNLOADMANAGER_TARGET_URL
echo "DOWNLOADMANAGER_DOWNLOADS_ROOT" $DOWNLOADMANAGER_DOWNLOADS_ROOT
echo "DOWNLOADS_URL" $DOWNLOADS_URL
echo "DOWNLOADMANAGER_LOCAL_PATHS_WHITELIST" $DOWNLOADMANAGER_LOCAL_PATHS_WHITELIST
echo "DOWNMAN_XSEND_BASEURL" $DOWNMAN_XSEND_BASEURL

grep -rl "##DOWNLOADMANAGER_TMP_DIR##"  | xargs sed -i "s ##DOWNLOADMANAGER_TMP_DIR## $DOWNLOADMANAGER_TMP_DIR g"
grep -rl "##DOWNLOADMANAGER_TARGET_ROOT##"  | xargs sed -i "s ##DOWNLOADMANAGER_TARGET_ROOT## $DOWNLOADMANAGER_TARGET_ROOT g"
grep -rl "##DOWNLOADMANAGER_TARGET_URL##" | xargs sed -i "s ##DOWNLOADMANAGER_TARGET_URL## $DOWNLOADMANAGER_TARGET_URL g"
grep -rl "##DOWNLOADMANAGER_DOWNLOADS_ROOT##"  | xargs sed -i "s ##DOWNLOADMANAGER_DOWNLOADS_ROOT## $DOWNLOADMANAGER_DOWNLOADS_ROOT g"
grep -rl "##DOWNLOADS_URL##" | xargs sed -i "s ##DOWNLOADS_URL## $DOWNLOADS_URL g" 
grep -rl "##DOWNLOADMANAGER_LOCAL_PATHS_WHITELIST##" | xargs sed -i "s[##DOWNLOADMANAGER_LOCAL_PATHS_WHITELIST##[$DOWNLOADMANAGER_LOCAL_PATHS_WHITELIST[g"
grep -rl "##DOWNMAN_XSEND_BASEURL##" | xargs sed -i "s[##DOWNMAN_XSEND_BASEURL##[$DOWNMAN_XSEND_BASEURL[g"
