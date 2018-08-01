#!/bin/bash


echo "Running install script for cadastral plugin ..."	
mv settings_tpl.py settings.py
grep -rl "##URL_CATASTRO##" | xargs sed -i "s ##URL_CATASTRO## $URL_CATASTRO g"

