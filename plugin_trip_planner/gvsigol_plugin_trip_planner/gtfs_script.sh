#!/bin/bash
#
# Genera el grafo de OTP si se ejecuta en el nodo indicado y programa el reinicio de OTP.
# $1 host que debe crear el grafo
# $2 service del systemd a reiniciar
# $3 directorio base donde buscar gtfs ($3/GTFS) y crear grafo ($3/graphs/$5); logs en $3/logs
# $4 jar de otp
# $5 router OTP
# $6 delay para reiniciar servicios (formato de sleep: 30m, 10s...)
# $7 directorio lucene
#
# Sale con código distinto de 0 si algo falla, para que el plugin lo muestre como error.

if [ -z "$1" ]; then
    echo "ERROR: gtfs_script.sh host not defined"
    exit 1
fi
if [ -z "$2" ]; then
    echo "ERROR: gtfs_script.sh systemd OTP service not defined"
    exit 1
fi
if [ -z "$3" ]; then
    echo "ERROR: gtfs_script.sh base directory not defined"
    exit 1
fi
if [ -z "$4" ]; then
    echo "ERROR: gtfs_script.sh OTP jar path not defined"
    exit 1
fi
if [ -z "$5" ]; then
    echo "ERROR: gtfs_script.sh OTP router not defined"
    exit 1
fi
if [ -z "$6" ]; then
    echo "ERROR: gtfs_script.sh delay to restart OTP not defined"
    exit 1
fi
if [ -z "$7" ]; then
    echo "ERROR: gtfs_script.sh lucene directory not defined"
    exit 1
fi

HOST=$1
SERVICE=$2
BASE=$3
JAR=$4
ROUTER=$5
DELAY=$6
LUCENE=$7
GRAPH_DIR="$BASE/graphs/$ROUTER"
LOG_DIR="$BASE/logs"

mkdir -p "$LOG_DIR" || exit 1

if [ "$HOSTNAME" != "$HOST" ]; then
    echo "WARNING: No se va a regenerar el grafo porque $HOSTNAME es distinto a $HOST"
else
    if ! ls "$BASE"/GTFS/*.zip >/dev/null 2>&1; then
        echo "ERROR: no hay ficheros GTFS en $BASE/GTFS"
        exit 1
    fi
    if ! command -v java >/dev/null 2>&1; then
        echo "ERROR: java no está instalado en $HOSTNAME"
        exit 1
    fi
    if [ ! -f "$JAR" ]; then
        echo "ERROR: no se encuentra el jar de OTP: $JAR"
        exit 1
    fi

    echo "INFO: START OTP graph process on $HOSTNAME $(date)"
    mkdir -p "$GRAPH_DIR" || exit 1
    rm -f "$GRAPH_DIR"/*.zip
    cp "$BASE"/GTFS/*.zip "$GRAPH_DIR"/ || exit 1
    java -Xmx4G -jar "$JAR" --build "$GRAPH_DIR"
    RC=$?
    if [ $RC -ne 0 ]; then
        echo "ERROR: la generación del grafo ha fallado (código $RC)"
        exit $RC
    fi
    echo "INFO: STOP OTP graph process on $HOSTNAME $(date)"
fi

# Reinicio diferido de OTP (borrando el índice lucene). Se desacopla por completo
# (nohup + salida a fichero) para que quien lanza el script no espere al sleep.
if command -v sudo >/dev/null 2>&1 && command -v systemctl >/dev/null 2>&1; then
    echo "INFO: Lanzando reinicio de OTP ($SERVICE) para dentro de $DELAY"
    nohup bash -c "sleep $DELAY && sudo systemctl stop $SERVICE; rm -rf $LUCENE; sudo systemctl start $SERVICE; sudo systemctl status $SERVICE" \
        > "$LOG_DIR/$HOSTNAME-otp_status.log" 2>&1 < /dev/null &
else
    echo "WARNING: sudo/systemctl no disponibles en $HOSTNAME; reinicia OTP ($SERVICE) manualmente"
fi
exit 0
