#!/bin/bash

echo "[INFO]: Start script configure.sh plugin_sentilo"

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

	grep -rl "##MUNICIPALITY##" | xargs sed -i "s ##MUNICIPALITY## $MUNICIPALITY g"

}

function move_template() {
	mv settings_tpl.py settings.py
}

move_to_working_dir
configure
move_template
back_from_working_dir
 

echo "[INFO]: End script configure.sh plugin_sentilo"
