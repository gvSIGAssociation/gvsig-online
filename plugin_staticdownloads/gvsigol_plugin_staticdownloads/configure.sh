#!/bin/bash

echo "Running install script for staticdownloads plugin ..."	
mv settings_tpl.py settings.py
grep -rl "##DOWNLOADS_URL##" | xargs sed -i "s ##DOWNLOADS_URL## $DOWNLOADS_URL g"