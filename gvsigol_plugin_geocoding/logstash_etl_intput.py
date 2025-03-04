from .models import Logstashetl
from string import Template

def create_user_data_elt_input(params, schema, provider_id):
    entry = Logstashetl()
    config = """
    jdbc {
        jdbc_driver_library => "/usr/share/logstash/logstash-core/lib/jars/postgresql-42.7.5.jar"
        jdbc_driver_class => "org.postgresql.Driver"
        jdbc_connection_string => "jdbc:postgresql://172.16.0.10:5432/gvsigonline"
        jdbc_user => "$${PG_USER}"
        jdbc_password => "$${PG_PASS}"
        statement => "SELECT '$schema.$table' || c.ogc_fid as id, gsl.title as lyr_name, 
            '$table'::varchar as table, '$schema'::varchar as schema, ST_GeometryType(c.$geometry)::varchar as element_type, 
            '$search'::varchar as search_label, c.$search as search, '$search_alt'::varchar as search_label_alt, c.modified_by as user, 
            c.feat_date_gvol as modif_date, c.$search_alt::varchar as search_alt, st_astext(c.$geometry) as geom, feat_date_gvol, 'userdata' as index_dst 
            FROM $schema.$table c 
            LEFT JOIN gvsigol_services_layer gsl ON gsl.name = '$table' WHERE feat_date_gvol > :sql_last_value"
        use_column_value => true
        tracking_column => "feat_date_gvol"
        tracking_column_type => "timestamp" 
        last_run_metadata_path => "/usr/share/logstash/temporary/logstash_jdbc_last_run"
        schedule => "*/10 * * * *"  # Ejecutar cada 2 minutos
        jdbc_validate_connection => true
        jdbc_validation_timeout => 50
    }
    """

    settings = {
        "schema": schema,
        "table": params['resource'],
        "geometry": params['geom_field'],
        "search": params['text_field'],
        "search_alt": params['textalt_field'],
    }
    config = Template(config).substitute(**settings)

    entry.type = "INPUT"
    entry.config = config
    entry.provider_id = provider_id
    entry.save()