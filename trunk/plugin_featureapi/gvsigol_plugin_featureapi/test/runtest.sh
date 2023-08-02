#!/bin/bash
source Devel.golsecrets 2> /dev/null
newman run TestLayersgvSIGOnlineAPI.json -e Devel_environment.json --env-var "user=$GVSIGOL_USER" --env-var "password=$GVSIGOL_PASS"
