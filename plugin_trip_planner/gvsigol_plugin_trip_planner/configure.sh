#!/bin/bash

echo "Running install script for trip-planner ..."	
mv settings_tpl.py settings.py

if [ -z "$GTFS_SCRIPT" ]; then
    echo "ERROR: GTFS_SCRIPT is not defined."
    exit -1  
else 
	echo "GTFS_SCRIPT: $GTFS_SCRIPT"		      
fi


grep -rl "##GTFS_SCRIPT##"  | xargs sed -i "s%##GTFS_SCRIPT##%$GTFS_SCRIPT%g"
