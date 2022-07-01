#!/bin/bash

echo "[INFO]: Running configure.sh plugin_trip_planner"

function configure() {
    if [ -z "$GTFS_SCRIPT" ]; then
        echo "ERROR: GTFS_SCRIPT is not defined."
        exit -1  
    else 
	    echo "GTFS_SCRIPT: $GTFS_SCRIPT"		      
    fi
    grep -rl "##GTFS_SCRIPT##"  | xargs sed -i "s%##GTFS_SCRIPT##%$GTFS_SCRIPT%g"
}

function move_template() {
	DIR="$(dirname "$0")"
	mv $DIR/settings_tpl.py $DIR/settings.py
}

configure
move_template

