#!/bin/bash

echo "[INFO]: Start script configure.sh plugin_vinya"


function configure() {
		grep -rl "##WSVINYA_URL##"  | xargs sed -i "s ##WSVINYA_URL## $WSVINYA_URL g"
		grep -rl "##DATASTORE_SIGPAC##"  | xargs sed -i "s ##DATASTORE_SIGPAC## $DATASTORE_SIGPAC g"
		grep -rl "##DATASTORE_CARTOEXTRA##"  | xargs sed -i "s ##DATASTORE_CARTOEXTRA## $DATASTORE_CARTOEXTRA g"
		grep -rl "##DATASTORE_RVCV##"  | xargs sed -i "s ##DATASTORE_RVCV## $DATASTORE_RVCV g"
		grep -rl "##LAYER_PARCELAS##"  | xargs sed -i "s ##LAYER_PARCELAS## $LAYER_PARCELAS g"
		grep -rl "##LAYER_RECINTOS##"  | xargs sed -i "s ##LAYER_RECINTOS## $LAYER_RECINTOS g"
		grep -rl "##LAYER_POLIGONOS##"  | xargs sed -i "s ##LAYER_POLIGONOS## $LAYER_POLIGONOS g"
		grep -rl "##LAYER_MUNICIPIOS##"  | xargs sed -i "s ##LAYER_MUNICIPIOS## $LAYER_MUNICIPIOS g"
}

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
function move_template() {
	mv settings_tpl.py settings.py
}

move_to_working_dir
configure
move_template
back_from_working_dir

echo "[INFO]: End script configure.sh plugin_vinya"
