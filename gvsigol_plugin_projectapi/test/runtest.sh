#!/bin/bash
newman run TestBasegvSIGOnlineAPI.json -e Devel_environment.json --env-var "user=$GVSIGOL_USER" --env-var "password=$GVSIGOL_PASS"
