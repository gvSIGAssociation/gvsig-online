from . import rest_geoserver
from .models import Layer, Trigger
from .backend_postgis import Introspect
from .exceptions import InvalidValue, BadFormat
import gdaltools
from dbfread import DBF
import json, re, os
import psycopg2.errors
from django.utils.translation import ugettext_lazy as _
import logging
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import ElementTree
import tempfile, shutil
from django.conf import settings

logger = logging.getLogger("gvsigol")

MODE_CREATE="CR"
MODE_APPEND="AP"
MODE_OVERWRITE="OW"

#_valid_sql_name_regex=re.compile("^[^\W\d][\w]*$")
_valid_sql_name_regex=re.compile("^[a-zA-Z_][a-zA-Z0-9_]*$")

def get_tmp_folder():
    try:
        fileman_dir = settings.FILEMANAGER_DIRECTORY
    except:
        logger.exception('Error getting FILEMANAGER_DIRECTORY')
        fileman_dir = os.path.join(settings.MEDIA_ROOT, 'data')
    basetmp_folder = os.path.join(fileman_dir, '_tmp_exports')
    try:
        os.makedirs(basetmp_folder)
    except FileExistsError:
        pass
    except Exception:
        basetmp_folder = os.path.join(tempfile.gettempdir(), '_tmp_exports')
    return tempfile.mkdtemp(prefix="exp_", dir=basetmp_folder)

def create_symlinks(src_path, target_dir):
    """
    Creates a symlink to the original file (e.g. layer.shp) in target_dir,
    to be used instead of the real path to avoid vsicurl, vsi*** or other kind of injenctions in ogr2ogr.
    It also creates symlinks to any commpanion files (e.g. layer.dbf, layer.cpg, lyr.shx, etc)

    Returns: the path of the created symlink
    """
    src_dir = os.path.dirname(src_path)
    src_basename = os.path.basename(src_path)
    src_name = os.path.splitext(src_basename)[0]
    with tempfile.NamedTemporaryFile(dir=target_dir) as target_tmp:
        target_name = target_tmp.name
    output_file = None
    for f in os.listdir(src_dir):
        f_path = os.path.join(src_dir, f)
        if os.path.isfile(f_path):
            if f.startswith(src_name):
                ext = f[len(src_name):]
                if ext == '' or ext[0] == '.':
                    dst_path = os.path.join(target_dir, target_name + ext)
                    os.symlink(f_path, dst_path)
                    if f == src_basename:
                        output_file = dst_path
    return output_file

def get_fields_from_shape(shp_path):
    file_name = os.path.splitext(shp_path)[0]
    dbf_file = file_name + ".dbf"
    if not os.path.isfile(dbf_file):
        dbf_file = file_name + ".DBF"
    with DBF(dbf_file) as table:
        return table.fields

def check_field_names(dbf_field_defs):
    for field in dbf_field_defs:
        if _valid_sql_name_regex.search(field.name) == None:
            raise InvalidValue(-1, _("Invalid field name: '{value}'. Identifiers must begin with a letter or an underscore (_). Subsequent characters can be letters, underscores or numbers").format(value=field.name))

def quote_identifier_ogr(field_name):
    return '"' + field_name.replace('\\', '\\\\').replace('"', '\\"') + '"'

def __quote_identifier_ogr_column_types(field_name):
    return field_name.replace('\\', '\\\\').replace('"', '\\"')

def config_pk_params(pk_name, pk_field_dbftype, default_creation_options, default_column_types):
    ogr = gdaltools.ogr2ogr()
    (major, minor, patch, prerelease) = ogr.get_version_tuple()
    major = int(major)
    minor = int(minor)
    default_creation_options["FID"] = pk_name
    if pk_name != 'ogc_fid':
        if major < 2 or (major == 2 and minor < 4): # not tested below version 2.4.x
            raise BadFormat(-1, _("gvSIG Online only supports overwriting/appending tables with primary key named ogc_fid due to the version of gdal/ogr installed on the server."))

    if pk_field_dbftype.type == 'N' and pk_field_dbftype.decimal_count == 0 and pk_field_dbftype.length > 9:
        default_creation_options["FID64"] = "TRUE"
        if major >= 2 or (major == 2 and minor >= 4):
            default_column_types[pk_name] = __quote_identifier_ogr_column_types(pk_name) + "=bigint"
            return 'CAST(' + quote_identifier_ogr(pk_name) + ' AS bigint) as ' + quote_identifier_ogr(pk_name)
        else:  # not working in v2.4.4 and not testend in versions < 3.4.x
            default_column_types[pk_name] = __quote_identifier_ogr_column_types(pk_name) + "=numeric(" + str(pk_field_dbftype.length) + "," + str(pk_field_dbftype.decimal_count) + ")"
            return 'CAST(' + quote_identifier_ogr(pk_name) + " AS numeric(" + str(pk_field_dbftype.length) + "," + str(pk_field_dbftype.decimal_count) + ") as " + quote_identifier_ogr(pk_name)

def config_geom_params(geom_cols, default_creation_options):
    if len(geom_cols)> 0 and (not 'wkb_geometry' in geom_cols):
        default_creation_options["GEOMETRY_NAME"] = geom_cols[0]

def get_cast(shp_field_def, default_column_types):
    if shp_field_def.type == 'N' and shp_field_def.decimal_count == 0:
        if shp_field_def.length <= 9:
            return 'CAST({quoted_name} AS integer) AS {quoted_name}'.format(quoted_name=quote_identifier_ogr(shp_field_def.name))
        elif shp_field_def.length > 9 and shp_field_def.length <= 19:
            return 'CAST({quoted_name} AS bigint) AS {quoted_name}'.format(quoted_name=quote_identifier_ogr(shp_field_def.name))
        else:
            default_column_types[shp_field_def.name] = __quote_identifier_ogr_column_types(shp_field_def.name) + "=numeric(" + str(shp_field_def.length) + "," + str(shp_field_def.decimal_count) + ")"
            return 'CAST({quoted_name} AS numeric({length},{decimal_count})) AS {quoted_name}'.format(quoted_name=quote_identifier_ogr(shp_field_def.name), length=shp_field_def.length, decimal_count=shp_field_def.decimal_count)
    else:
        return quote_identifier_ogr(shp_field_def.name)

def _creation_fieldmapping(shp_fields, default_creation_options, default_column_types, pk_column):
    fields = []
    for shp_field_def in shp_fields:
        if shp_field_def.name == pk_column:
            cast = config_pk_params(pk_column, shp_field_def, default_creation_options, default_column_types)
            if not cast:
                cast = get_cast(shp_field_def, default_column_types)
            fields.append(cast)
        else:
            cast = get_cast(shp_field_def, default_column_types)
            fields.append(cast)
    return fields

def _append_overwrite_fieldmapping(creation_mode, shp_fields, table_name, host, port, db, schema, user, password, default_creation_options, default_column_types, pk_column=None):
    """
    Field mapping for append or overwrite operations
    """
    i = Introspect(db, host=host, port=port, user=user, password=password)
    with i as c:
        try:
            db_fields = c.get_fields(table_name, schema=schema)
            db_pks = c.get_pk_columns(table_name, schema=schema)
            geom_cols = c.get_geometry_columns(table_name, schema=schema)
            config_geom_params(geom_cols, default_creation_options)
        except psycopg2.errors.UndefinedTable as e:
            raise rest_geoserver.RequestError(-1, _('Overwrite or append was specified but the table does not exist: {0}'.format(table_name)))

    if pk_column:
        db_pk = pk_column
    elif len(db_pks) == 1:
        db_pk = db_pks[0]
    else:
        db_pk = 'ogc_fid'

    fields = []
    pending = []
    for shp_field_def in shp_fields:
        if shp_field_def.name == db_pk:
            pk_cast = config_pk_params(db_pk, shp_field_def, default_creation_options, default_column_types)
            if pk_cast:
                fields.append(pk_cast)
            else:
                fields.append(quote_identifier_ogr(shp_field_def.name) + ' AS ' + quote_identifier_ogr(pk_column))
        elif shp_field_def.name in db_fields:
            ctrl_field = next((the_f for the_f in settings.CONTROL_FIELDS if the_f.get('name') == shp_field_def.name), None)
            if ctrl_field:
                if creation_mode==MODE_APPEND:
                    # skip control field in append mode
                    continue
                elif ctrl_field.get('type', '').startswith('timestamp'):
                    fields.append('CAST("' + shp_field_def.name + '" AS timestamp)')
                    continue
            fields.append(quote_identifier_ogr(shp_field_def.name))
        else:
            pending.append(shp_field_def)

    for shp_field_def in pending:
        # try to find a mapping
        db_mapped_field = None
        for db_field in db_fields:
            if db_field.startswith(shp_field_def.name):
                db_mapped_field = db_field
        if not db_mapped_field:
            for db_field in db_fields:
                if db_field.startswith(shp_field_def.name.rstrip('0123456789')):
                    # remove numbers in the right side of the field name to try to match with db
                    db_mapped_field = db_field
        if db_mapped_field:
            ctrl_field = next((the_f for the_f in settings.CONTROL_FIELDS if the_f.get('name') == db_mapped_field), None)
            if ctrl_field:
                if creation_mode==MODE_APPEND:
                    # skip control field in append mode
                    continue
                elif ctrl_field.get('type', '').startswith('timestamp'):
                    fields.append('CAST(' + quote_identifier_ogr(shp_field_def.name) + ' AS timestamp) as "' + db_mapped_field + '"')
                    db_fields.remove(db_mapped_field)
                    continue
            fields.append(quote_identifier_ogr(shp_field_def.name)  + ' as "' + db_mapped_field + '"')
            db_fields.remove(db_mapped_field)
        else:
            fields.append(quote_identifier_ogr(shp_field_def.name))
    return fields

def fieldmapping_sql(creation_mode, shp_path, shp_fields, table_name, host, port, db, schema, user, password, default_creation_options, default_column_types, pk_column):
    if creation_mode == MODE_CREATE:
        fields =  _creation_fieldmapping(shp_fields, default_creation_options, default_column_types, pk_column)
    else:
        # TODO: seguramente FID no funciona para el append
        # if creation_mode == MODE_OVERWRITE:
        #   fields = _append_overwrite_fieldmapping(creation_mode, shp_fields, table_name, host, port, db, schema, user, password, default_creation_options, default_column_types, pk_column)
        # else:
        #   fields = _append_overwrite_fieldmapping(creation_mode, shp_fields, table_name, host, port, db, schema, user, password, default_creation_options, default_column_types)
        fields = _append_overwrite_fieldmapping(creation_mode, shp_fields, table_name, host, port, db, schema, user, password, default_creation_options, default_column_types, pk_column)
    
    shp_name = os.path.splitext(os.path.basename(shp_path))[0]
    sql = "SELECT " + ",".join(fields) + " FROM " + shp_name
    return sql

def create_vrt_shp(shp_path, target_folder, pk_column, encoding, srs):
    lyr_basename = os.path.basename(shp_path)
    lyr_name = os.path.splitext(lyr_basename)[0]
    root = ET.Element('OGRVRTDataSource')
    lyr = ET.SubElement(root, 'OGRVRTLayer', attrib={
        "name": lyr_name
    })
    src_ds = ET.SubElement(lyr, 'SrcDataSource')
    src_ds.text = shp_path
    options = ET.SubElement(lyr, 'OpenOptions')
    option = ET.SubElement(options, 'OOI', attrib={
        "key": "ENCODING"
    })
    option.text = encoding
    src_layer = ET.SubElement(lyr, 'SrcLayer')
    src_layer.text = lyr_name
    src_srs = ET.SubElement(lyr, 'LayerSRS')
    src_srs.text = srs
    fid = ET.SubElement(lyr, 'FID')
    fid.text = pk_column
    tree = ElementTree(root)
    vrt_path = os.path.join(target_folder, lyr_name + ".vrt")
    with open(vrt_path, 'wb') as f:
        tree.write(f, encoding='utf-8')
    return vrt_path
    

def shp2postgis(shp_path, table_name, srs, host, port, dbname, schema, user, password, creation_mode=MODE_CREATE, encoding="autodetect", sql=None, preserve_fid=False, creation_options={}, config_options={}):
    ogr = gdaltools.ogr2ogr()
    if encoding != 'autodetect':
        ogr.set_encoding(encoding)
    ogr.set_input(shp_path, srs=srs)
    conn = gdaltools.PgConnectionString(host=host, port=port, dbname=dbname, schema=schema, user=user, password=password)
    ogr.set_output(conn, table_name=table_name)
    if preserve_fid:
        ogr.preserve_fid = preserve_fid
    config_options = {
        **{
            "OGR_TRUNCATE": "NO"
        },
        **config_options
    }
    if creation_mode == MODE_CREATE:
        ogr.set_output_mode(layer_mode=ogr.MODE_LAYER_CREATE, data_source_mode=ogr.MODE_DS_UPDATE)
    elif creation_mode == MODE_APPEND:
            ogr.set_output_mode(layer_mode=ogr.MODE_LAYER_APPEND, data_source_mode=ogr.MODE_DS_UPDATE)
    elif creation_mode == MODE_OVERWRITE:
            if config_options.get("OGR_TRUNCATE", "NO") == "YES":
                ogr.set_output_mode(layer_mode=ogr.MODE_LAYER_APPEND, data_source_mode=ogr.MODE_DS_UPDATE)
            else:
                ogr.set_output_mode(layer_mode=ogr.MODE_LAYER_OVERWRITE, data_source_mode=ogr.MODE_DS_UPDATE)
    ogr.layer_creation_options = {
        **{
            "LAUNDER": "YES",
            "PRECISION": "NO"
        },
        **creation_options
    }
    ogr.config_options = config_options
    ogr.set_sql(sql)
    ogr.set_dim("2")
    ogr.geom_type = "PROMOTE_TO_MULTI"
    try:
        ogr.execute()
    except:
        raise
    finally:
        print(" ".join(ogr.safe_args))
    return ogr.stderr if ogr.stderr is not None else ''


def read_encoding(shp_path):
    """
    Reads .cst files to guess encoding.
    Returns the encoding if found, None otherwise
    """
    try:
        name = os.path.splitext(shp_path)[0]
        with open(name + ".cst", "r") as f:
            enc = f.read(50) # encoding names are not expected to be longer
            if enc[-1] == '\n':
                enc = enc[:-1]
            return enc
    except:
        pass


def do_export_to_postgis(gs, name, datastore, creation_mode, shp_path, shp_fields, srs, encoding, pk_column=None, preserve_pk=None, truncate=None):
    tmp_folder = None
    try:
        tmp_folder = get_tmp_folder()
        ds_params = json.loads(datastore.connection_params) 
        db = ds_params.get('database')
        host = ds_params.get('host')
        port = ds_params.get('port')
        schema = ds_params.get('schema', "public")
        port = str(int(port))
        user = ds_params.get('user')
        password = ds_params.get('passwd')
        if _valid_sql_name_regex.search(name) == None:
            raise InvalidValue(-1, _("Invalid layer name: '{value}'. Identifiers must begin with a letter or an underscore (_). Subsequent characters can be letters, underscores or numbers").format(value=name))
        if _valid_sql_name_regex.search(db) == None:
            raise InvalidValue(-1, _("The connection parameters contain an invalid database name: {value}. Identifiers must begin with a letter or an underscore (_). Subsequent characters can be letters, underscores or numbers").format(value=db))
        if _valid_sql_name_regex.search(user) == None:
            raise InvalidValue(-1, _("The connection parameters contain an invalid user name: {value}. Identifiers must begin with a letter or an underscore (_). Subsequent characters can be letters, underscores or numbers").format(value=db))
        if _valid_sql_name_regex.search(schema) == None:
            raise InvalidValue(-1, _("The connection parameters contain an invalid schema: {value}. Identifiers must begin with a letter or an underscore (_). Subsequent characters can be letters, underscores or numbers").format(value=db)) 
        if not pk_column:
            pk_column = 'ogc_fid'

        creation_options = {}
        column_types = {}
        check_field_names(shp_fields)
        if (encoding == 'autodetect'):
            cst_encoding = read_encoding(shp_path)
            if cst_encoding:
                encoding = cst_encoding

        orig_shp_path = shp_path
        shp_path = create_symlinks(shp_path, tmp_folder)
        sql = fieldmapping_sql(creation_mode, shp_path, shp_fields, name, host, port, db, schema, user, password, creation_options, column_types, pk_column)
        column_types = ",".join(list(column_types.values()))
        creation_options['COLUMN_TYPES'] = column_types
        config_options = {}
        if creation_mode == MODE_OVERWRITE and truncate:
            config_options["OGR_TRUNCATE"] = "YES"
        if preserve_pk:
            if creation_mode == MODE_APPEND or (creation_mode == MODE_OVERWRITE and truncate):
                preserve_fid = True
                shp_path = create_vrt_shp(shp_path, tmp_folder, pk_column, encoding, srs)
            else:
                preserve_fid = False
        else:
            if creation_mode == MODE_APPEND:
                preserve_fid = False  # PKs are not kept in append by default
            else:
                # Note: -preserve_fid ogr2ogr flag will NOT keep PKs when exporting from SHP to postgres
                preserve_fid = True

        stderr = shp2postgis(shp_path, name, srs, host, port, db, schema, user, password, creation_mode, encoding, sql=sql, preserve_fid=preserve_fid, creation_options=creation_options, config_options=config_options)
        if stderr.startswith("ERROR"): # some errors don't return non-0 status so will not directly raise an exception
            raise rest_geoserver.RequestError(-1, stderr)
        with Introspect(db, host=host, port=port, user=user, password=password) as i:
            # add control fields
            db_fields = i.get_fields(name, schema=schema)
            for control_field in settings.CONTROL_FIELDS:
                has_control_field = False
                for field in db_fields:
                    if field == control_field['name']:
                        try:
                            i.set_field_default(schema, name, control_field['name'], control_field.get('default'))
                        except:
                            logger.exception("Error setting default value for control field: " + control_field['name'])
                        has_control_field = True
                if not has_control_field:
                    try:
                        i.add_column(schema, name, control_field['name'], control_field['type'], nullable=control_field.get('nullable', True), default=control_field.get('default'))
                    except:
                        logger.exception("Error adding control field: " + control_field['name'])
            i.update_pk_sequences(name, schema=schema)
        
        if creation_mode == MODE_OVERWRITE:
            # re-install triggers
            for trigger in Trigger.objects.filter(layer__datastore=datastore, layer__source_name=name):
                try:
                    trigger.drop()
                    trigger.install()
                except:
                    logger.exception("Failed to install trigger: " + str(trigger))
            
        for layer in Layer.objects.filter(datastore=datastore, source_name=name):
            gs.reload_featuretype(layer)
            expose_pks = gs.datastore_check_exposed_pks(datastore)
            layer.get_config_manager().refresh_field_conf(include_pks=expose_pks)
            layer.save()
        if not stderr:
            return True
    except rest_geoserver.RequestError as e:
        logger.exception(e)
        raise
    except gdaltools.GdalToolsError as e:
        logger.exception(str(e))
        if e.code > 0:
            if creation_mode == MODE_OVERWRITE:

                params = json.loads(datastore.connection_params)
                host = params['host']
                port = params['port']
                dbname = params['database']
                user = params['user']
                passwd = params['passwd']
                schema = params.get('schema', 'public')
                i = Introspect(database=dbname, host=host, port=port, user=user, password=passwd)
                i.delete_table(schema, name)
                i.close()
                try:
                    stderr = shp2postgis(shp_path, name, srs, host, port, db, schema, user, password, creation_mode, encoding)
                    if stderr:
                        raise rest_geoserver.RequestError(-1, stderr)
                    return True
                except gdaltools.GdalToolsError as e:
                    raise rest_geoserver.RequestError(e.code, str(e))
            elif e.message.decode("UTF-8").startswith("ERROR 1") and \
                ('pkey' in e.message.decode("UTF-8") or 'duplicate key' in e.message.decode("UTF-8") or 'lave duplicada' in e.message.decode("UTF-8")): # TODO no debería hacer el decode aqui
                msg = _("The export has failed because it would create duplicate values in the {pkfield} field, which does not allow duplicate values. Consider correcting the data or read the User Manual for the option 'Do not preserve primary key'. Details: {details}").format(pkfield=pk_column, details=str(e))
                raise rest_geoserver.RequestError(e.code, msg)
        raise rest_geoserver.RequestError(e.code, str(e))
    except Exception as e:
        logger.exception(str(e))
        message =  _("Error uploading the layer. Review the file format. Cause: ") + str(e)
        raise rest_geoserver.RequestError(-1, message)
    finally:
        if tmp_folder:
            try:
                shutil.rmtree(tmp_folder)
            except:
                pass
    raise rest_geoserver.RequestWarning(stderr)


