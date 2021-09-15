#!/bin/bash

echo "Running install script for streetview plugin ..."	

mv settings_tpl.py settings.py
if [ -z $STREETVIEW_API_KEY ]; then
	echo "WARNING: STREETVIEW_API_KEY is not defined"
fi	
grep -rl "##STREETVIEW_API_KEY##" | xargs sed -i "s ##STREETVIEW_API_KEY## $STREETVIEW_API_KEY g"