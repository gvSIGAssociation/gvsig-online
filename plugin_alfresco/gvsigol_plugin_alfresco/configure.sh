#!/bin/bash

echo "Running install script for alfresco ..."	
mv settings_tpl.py settings.py
grep -rl "##ALFRESCO_CMIS_REST_API_URL##" | xargs sed -i "s ##ALFRESCO_CMIS_REST_API_URL## $ALFRESCO_CMIS_REST_API_URL g" 


