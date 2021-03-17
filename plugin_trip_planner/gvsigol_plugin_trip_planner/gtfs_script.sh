#!/bin/bash
#
# Genera el grafo de otp si se encuentra en el nodo indicado
# $1 host que debe crear el grafo
# $2 service del systemd a reiniciar
# $3 directorio base donde buscar gtfs y crear grafo
# $4 jar de otp
# $5 ruter OTP
# $6 delay para reiniciar servicios

if [ -z "$1" ]; then
    echo "ERROR: gtfs_script.sh host not defined"
    exit -1
fi
if [ -z "$2" ]; then
    echo "ERROR: gtfs_script.sh systemd OTP service not defined"
    exit -1 
fi
if [ -z "$3" ]; then
    echo "ERROR: gtfs_script.sh base directory not defined"
    exit -1
fi
if [ -z "$4" ]; then
    echo "ERROR: gtfs_script.sh OTP jar path not defined"
    exit -1
fi
if [ -z "$5" ]; then
    echo "ERROR: gtfs_script.sh OTP router not defined"
    exit -1
fi
if [ -z "$6" ]; then
    echo "ERROR: gtfs_script.sh delay to restart OTP not defined"
    exit -1
fi


# reiniciamos el servicio de otp a los 30 minutos
sleep $6 && (sudo systemctl stop $2;sudo systemctl start $2) &

if [ "$HOSTNAME" != "$1" ]; then
	echo "WARNING: No se va a regenerar el grafo porque $HOSTNAME es distinto a $1"
else
	echo "INFO: START OTP graph process on $HOSTNAME $(date)"
    rm -f $3/graphs/$5/*.zip
    cp $3/GTFS/*.zip $3/graphs/$5/
    #cp /pre_datos_gvinterbus/*.zip /datos_apl/gvsigol_gvenruta/data/graphs/gva/
    java -Xmx4G -jar $4 --build $3/graphs/$5
    echo "INFO: STOP OTP graph process on $HOSTNAME $(date)"
fi  



