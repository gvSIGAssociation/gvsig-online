#!/bin/bash

echo "Running install script for sync plugin ..."	
mv settings_tpl.py settings.py
grep -rl "##GVSIGOL_APP_DOWNLOAD_LINK##" $PLUGIN_DIR | xargs sed -i "s ##GVSIGOL_APP_DOWNLOAD_LINK## $GVSIGOL_APP_DOWNLOAD_LINK g"

