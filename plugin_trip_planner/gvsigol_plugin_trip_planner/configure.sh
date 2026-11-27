#!/bin/bash

echo "[INFO]: Start script configure.sh plugin_trip_planner"

function move_to_working_dir()
{
    DIR="$(dirname "$0")"
    pushd $DIR
    echo "[INFO]: Working dir $PWD"
}
function back_from_working_dir()
{
    popd
    echo "[INFO]: Back to $PWD"
}

function configure() {
    # settings.py reads GTFS_SCRIPT / GTFS_CRONTAB from the environment at runtime (django-environ)
    if [ -z "$GTFS_SCRIPT" ]; then
        echo "[WARNING]: GTFS_SCRIPT is not defined, the default from settings.py will be used."
    else
        echo "GTFS_SCRIPT: $GTFS_SCRIPT"
    fi
}

function move_template() {
	mv settings_tpl.py settings.py
}

move_to_working_dir
configure
move_template
back_from_working_dir
 

echo "[INFO]: End script configure.sh plugin_trip_planner"
