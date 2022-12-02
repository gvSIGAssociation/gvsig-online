#!/bin/bash
newman run TestBasegvSIGOnlineAPI.json --global-var "user=$GVSIGOL_USER" --global-var "password=$GVSIGOL_PASS" -e Devel_environment.json 
