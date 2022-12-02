#!/bin/bash
newman run TestLayersgvSIGOnlineAPI.json "--global-var user=$GVSIGOL_USER" "--global-var password=$GVSIGOL_PASS" -e Devel_environment.json 
