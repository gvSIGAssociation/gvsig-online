*  Para acceder: https://localhost/gvsigonline/sampleapi/example/


* Para crear la migración

/docker-entrypoint.sh python manage.py makemigrations


* Para aplicarla

/docker-entrypoint.sh python manage.py migrate

* Para modificar el modelo, resetear las migraciones y disponer de una migración inicial.

TODO