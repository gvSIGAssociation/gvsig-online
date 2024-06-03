* Para acceder: https://localhost/gvsigonline/sampleapi/example/


* Para crear la migración

/docker-entrypoint.sh python manage.py makemigrations


* Para aplicarla

/docker-entrypoint.sh python manage.py migrate

* Para modificar el modelo, resetear las migraciones y disponer de una migración inicial.

- Vemos las migraciones aplicadas
/docker-entrypoint.sh python manage.py showmigrations
- Limpiamos el historial de migracioas
/docker-entrypoint.sh  python manage.py migrate --fake gvsigol_plugin_sampleapi zero
- Eliminamos las migraciones del plugin 
- Conectamos a la bbdd para eliminar las tablas 
 PGPASSWORD=$DB_PASS psql -h $DB_HOST -U $DB_USER -d $DB_NAME
- Ejecutamos SQL para eliminar tablas (adaptar al plugin)
DO
$do$
DECLARE
   _tbl text;
BEGIN
FOR _tbl  IN
    SELECT quote_ident(table_schema) || '.'
        || quote_ident(table_name)     
    FROM   information_schema.tables
    WHERE  table_name LIKE 'gvsigol_plugin_sampleapi' || '%'  -- MODIFICAR PREFIJO!!!
    AND    table_schema NOT LIKE 'pg\_%'   
LOOP
   RAISE NOTICE '%',                                          -- COMENTAR cuando se vea correcto!!!
-- EXECUTE                                                    -- DESCOMENTAR cuando se vea correcto!!
  'DROP TABLE ' || _tbl || ' CASCADE';  -- see below
END LOOP;
END
$do$;

- Creamos migraciones
/docker-entrypoint.sh python manage.py makemigrations
- Migramos
/docker-entrypoint.sh python manage.py migrate