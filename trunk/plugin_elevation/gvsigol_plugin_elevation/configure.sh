#!/bin/bash

echo "Running install script for elevation plugin ..."	
if [ -z $ELEVATION_URL ]; then
	echo "WARNING: ELEVATION_URL is not defined, using empty"					
	ELEVATION_URL=""
fi												
grep -rl "##ELEVATION_URL##"  | xargs sed -i "s ##ELEVATION_URL## $ELEVATION_URL g"

if [ -z $ELEVATION_LAYER ]; then
	echo "WARNING: ELEVATION_LAYER is not defined, using empty"					
	ELEVATION_LAYER=""
fi												
grep -rl "##ELEVATION_LAYER##"  | xargs sed -i "s/##ELEVATION_LAYER##/$ELEVATION_LAYER/g"
