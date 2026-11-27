#!/bin/bash
#
# Reconstruye el grafo en un contenedor OTP remoto (docker/gvsigol-otp) llamando a su
# servicio de reconstrucción. Alternativa a gtfs_script.sh, que construye en este mismo
# contenedor/nodo.
#
# $1 URL del servicio de reconstrucción (p.ej. http://gvsigol-otp:8090/rebuild)
# $2 tiempo máximo de espera en segundos (opcional, 7200)
#
# El contenedor OTP lee los GTFS del directorio GTFS/ del plugin (volumen compartido).
# Sale con código distinto de 0 si el build falla; la salida del build se muestra en
# el plugin («Ver detalles»).

if [ -z "$1" ]; then
    echo "ERROR: gtfs_script_remote.sh rebuild URL not defined"
    exit 1
fi

echo "INFO: solicitando reconstrucción del grafo a $1"
curl -sS --fail-with-body --max-time "${2:-7200}" -X POST "$1"
RC=$?
if [ $RC -ne 0 ]; then
    echo "ERROR: la reconstrucción remota ha fallado (curl código $RC)"
    exit $RC
fi
