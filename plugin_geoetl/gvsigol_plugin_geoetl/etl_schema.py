# -*- coding: utf-8 -*-

import pandas as pd
import psycopg2
import cx_Oracle
#import base64
import requests
import json
import re
#from datetime import date
from django.contrib.gis.gdal import DataSource
from .models import database_connections
import os
import shutil
from zipfile import ZipFile
from gvsigol import settings
from psycopg2 import sql
from datetime import datetime
from hashlib import sha256
import base64
import pymssql
import xmltodict
from .settings import GEOETL_DB

def get_sheets_excel(excel, r):
    import warnings

    warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

    if r == 'single':
    
        xl = pd.ExcelFile(excel)
        return xl.sheet_names
    else:
        sheets_array = []
        for file in os.listdir(excel):
            if file.endswith(".xls") or file.endswith(".xlsx"):
                xl = pd.ExcelFile(excel+'//'+file)
                for sh in list(xl.sheet_names):
                    if sh not in sheets_array:
                        sheets_array.append(sh)
        return sheets_array
        

def get_schema_excel(dicc):
    import warnings

    warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

    if dicc['reading'] == 'single':
    
        xl = pd.read_excel(dicc["excel-file"], sheet_name=dicc["sheet-name"], header=int(dicc["header"]), usecols=dicc["usecols"])
        return list(xl.columns)
    
    else:
        column_array = []
        for file in os.listdir(dicc["excel-file"]):
            if file.endswith(".xls") or file.endswith(".xlsx"):
                xl = pd.read_excel(dicc["excel-file"]+'//'+file, sheet_name=dicc["sheet-name"], header=int(dicc["header"]), usecols=dicc["usecols"])
                for col in list(xl.columns):
                    if col not in column_array:
                        column_array.append(col)
        column_array.append('_filename')
        return column_array

def get_schema_kml(file):

    from .etl_tasks import get_temp_dir
    temp_dir = get_temp_dir()

    if file.endswith('.kmz'):
        kmz_file = file[7:]

        filename = kmz_file.split('/')[-1].split('.')[0]

        kmz_zip = '/'+os.path.join(temp_dir, filename+'.zip')

        shutil.copy(kmz_file, kmz_zip)

        with ZipFile(kmz_zip) as zf:
            zf.extractall('/'+os.path.join(temp_dir, filename))

        kml_file = '/'+os.path.join(temp_dir, filename, 'doc.kml')

    elif file.endswith('.kml'):
        kml_file = file[7:]
        
    dataSource = DataSource(kml_file)
            
    layer = dataSource[0]

    schema = ['ogc_fid']
    for x in layer.fields:
        schema.append(x.lower())

    if file.endswith('.kmz'):
        
        shutil.rmtree(temp_dir)

    return schema

def get_schema_shape(file):

    shp = file[7:]

    dataSource = DataSource(shp)
            
    layer = dataSource[0]

    schema = [x.lower() for x in layer.fields] 

    return schema

#test if connection postgres is valid
def test_oracle(dicc):
    try:
        conn = cx_Oracle.connect(
            dicc['username'],
            dicc['password'],
            dicc['dsn']
        )
        conn.close()
        return {"result": True}
    except Exception as e:
        print('Connection Oracle: ' + str(e))
        return {"result": False}

def test_postgres(dicc):
    try:
        conn = psycopg2.connect(user = dicc["user"], password = dicc["password"], host = dicc["host"], port = dicc["port"], database = dicc["database"])
        cur = conn.cursor()
        
        sql = "SELECT schema_name FROM information_schema.schemata"
        cur.execute(sql)
        conn.commit()
        
        conn.close()

        return {"result": True}
    except Exception as e:
        print ('Connection postgres: ' + str(e))
        return {"result": False}
    
def test_sqlserver(dicc):
    try:
        conn = pymssql.connect(dicc['server-sql-server'], dicc['username-sql-server'], dicc['password-sql-server'], dicc['db-sql-server'], tds_version = dicc["tds-version-sql-server"])
        conn.close()
        return {"result": True}
    except Exception as e:
        print('Connection SQL Server Failed: ' + str(e))
        return {"result": False}

def get_sharepoint_token(dicc):
    """Obtiene un token de acceso para SharePoint usando client credentials flow."""
    token_url = f"https://login.microsoftonline.com/{dicc['tenant-id']}/oauth2/v2.0/token"
    
    data = {
        "client_id": dicc['client-id'],
        "client_secret": dicc['client-secret'],
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials"
    }
    
    response = requests.post(token_url, data=data)
    
    if response.status_code == 200:
        return response.json().get("access_token")
    else:
        raise Exception(f"Error obteniendo token SharePoint: {response.status_code} - {response.text}")

def test_sharepoint(dicc):
    """Verifica la conexión a SharePoint obteniendo el token y el site ID."""
    try:
        # Obtener token
        access_token = get_sharepoint_token(dicc)
        
        # Verificar acceso al sitio
        headers = {"Authorization": f"Bearer {access_token}"}
        sharepoint_host = dicc['sharepoint-host']
        site_path = dicc['site-path']
        
        url = f"https://graph.microsoft.com/v1.0/sites/{sharepoint_host}:{site_path}"
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            return {"result": True}
        else:
            print(f'Connection SharePoint Failed: {response.status_code} - {response.text}')
            return {"result": False}
    except Exception as e:
        print('Connection SharePoint Failed: ' + str(e))
        return {"result": False}

def get_sharepoint_site_id(dicc):
    """Obtiene el ID del sitio de SharePoint."""
    access_token = get_sharepoint_token(dicc)
    headers = {"Authorization": f"Bearer {access_token}"}
    
    sharepoint_host = dicc['sharepoint-host']
    site_path = dicc['site-path']
    
    url = f"https://graph.microsoft.com/v1.0/sites/{sharepoint_host}:{site_path}"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json().get("id")
    else:
        raise Exception(f"Error obteniendo sitio SharePoint: {response.status_code} - {response.text}")

def get_sharepoint_drives(dicc):
    """Lista todas las bibliotecas de documentos (drives) del sitio SharePoint."""
    try:
        db = database_connections.objects.get(name=dicc['api'])
        params = json.loads(db.connection_params)
        
        access_token = get_sharepoint_token(params)
        site_id = get_sharepoint_site_id(params)
        
        headers = {"Authorization": f"Bearer {access_token}"}
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            drives = response.json().get("value", [])
            return [{"id": d.get("id"), "name": d.get("name")} for d in drives]
        else:
            print(f'Error getting SharePoint drives: {response.status_code} - {response.text}')
            return []
    except Exception as e:
        print('Error getting SharePoint drives: ' + str(e))
        return []

def get_sharepoint_folder_contents(dicc):
    """Lista el contenido de una carpeta en SharePoint (archivos y subcarpetas)."""
    from urllib.parse import quote
    
    # Extensiones de archivo soportadas por formato
    format_extensions = {
        'excel': ('.xls', '.xlsx'),
        'csv': ('.csv', '.txt'),
        'json': ('.json',)
    }
    
    try:
        db = database_connections.objects.get(name=dicc['api'])
        params = json.loads(db.connection_params)
        
        access_token = get_sharepoint_token(params)
        
        headers = {"Authorization": f"Bearer {access_token}"}
        drive_id = dicc['drive-id']
        folder_path = dicc.get('folder-path', '')
        file_format = dicc.get('format', 'excel')
        
        # Obtener extensiones para el formato seleccionado
        valid_extensions = format_extensions.get(file_format, format_extensions['excel'])
        
        if folder_path:
            encoded_path = quote(folder_path, safe='/')
            url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{encoded_path}:/children"
        else:
            url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root/children"
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            items = response.json().get("value", [])
            result = []
            for item in items:
                item_data = {
                    "name": item.get("name"),
                    "id": item.get("id"),
                    "is_folder": "folder" in item,
                    "size": item.get("size", 0)
                }
                # Incluir carpetas o archivos que coincidan con las extensiones del formato
                if item_data["is_folder"] or item_data["name"].lower().endswith(valid_extensions):
                    result.append(item_data)
            return result
        else:
            print(f'Error getting SharePoint folder contents: {response.status_code} - {response.text}')
            return []
    except Exception as e:
        print('Error getting SharePoint folder contents: ' + str(e))
        return []

def download_sharepoint_file(dicc, temp_dir):
    """Descarga un archivo de SharePoint al directorio temporal."""
    from urllib.parse import quote
    
    db = database_connections.objects.get(name=dicc['api'])
    params = json.loads(db.connection_params)
    
    access_token = get_sharepoint_token(params)
    site_id = get_sharepoint_site_id(params)
    
    headers = {"Authorization": f"Bearer {access_token}"}
    
    drive_id = dicc['drive-id']
    file_path = dicc['file-path']
    encoded_path = quote(file_path, safe='/')
    
    url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{encoded_path}:/content"
    
    response = requests.get(url, headers=headers, allow_redirects=True)
    
    if response.status_code == 200:
        # Extraer nombre del archivo de la ruta
        file_name = file_path.split('/')[-1]
        local_path = os.path.join(temp_dir, file_name)
        
        with open(local_path, "wb") as f:
            f.write(response.content)
        
        return local_path
    else:
        raise Exception(f"Error descargando archivo SharePoint: {response.status_code} - {response.text}")

def get_sharepoint_excel_sheets(dicc):
    """Obtiene las hojas de archivos Excel de SharePoint.
    
    Si hay múltiples archivos (file-paths), devuelve solo las hojas comunes a todos.
    Si hay un solo archivo (file-path), devuelve todas sus hojas.
    """
    import warnings
    from .etl_tasks import get_temp_dir
    
    warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')
    
    temp_dir = get_temp_dir()
    
    try:
        # Obtener lista de archivos
        file_paths = dicc.get('file-paths', [])
        if not file_paths:
            # Retrocompatibilidad: si viene file-path (singular), usarlo
            single_path = dicc.get('file-path')
            if single_path:
                file_paths = [single_path]
        
        if not file_paths:
            return []
        
        all_sheets = []
        
        for file_path in file_paths:
            download_params = {
                'api': dicc['api'],
                'drive-id': dicc['drive-id'],
                'file-path': file_path
            }
            local_file = download_sharepoint_file(download_params, temp_dir)
            xl = pd.ExcelFile(local_file)
            all_sheets.append(set(xl.sheet_names))
        
        # Si hay un solo archivo, devolver todas sus hojas
        if len(all_sheets) == 1:
            return list(all_sheets[0])
        
        # Si hay múltiples archivos, devolver la intersección (hojas comunes)
        common_sheets = all_sheets[0]
        for sheets_set in all_sheets[1:]:
            common_sheets = common_sheets.intersection(sheets_set)
        
        return list(common_sheets)
        
    finally:
        # Limpiar archivo temporal
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

def get_schema_sharepoint(dicc):
    """Obtiene el esquema (columnas) de archivos de SharePoint según su formato.
    
    Si hay múltiples archivos seleccionados (file-paths), devuelve la UNIÓN de todas las columnas.
    """
    file_format = dicc.get('format', 'excel')
    
    if file_format == 'excel':
        return get_schema_sharepoint_excel(dicc)
    # Future: CSV format
    # elif file_format == 'csv':
    #     return get_schema_sharepoint_csv(dicc)
    # Future: JSON format
    # elif file_format == 'json':
    #     return get_schema_sharepoint_json(dicc)
    else:
        # Default a Excel si el formato no es reconocido
        return get_schema_sharepoint_excel(dicc)


def get_schema_sharepoint_excel(dicc):
    """Obtiene el esquema (columnas) de archivos Excel de SharePoint.
    
    Si hay múltiples archivos (file-paths), devuelve la UNIÓN de todas las columnas (sin duplicados).
    Si hay un solo archivo (file-path), devuelve sus columnas.
    """
    import warnings
    from .etl_tasks import get_temp_dir
    
    warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')
    
    temp_dir = get_temp_dir()
    
    try:
        # Obtener lista de archivos
        file_paths = dicc.get('file-paths', [])
        if not file_paths:
            # Retrocompatibilidad: si viene file-path (singular), usarlo
            single_path = dicc.get('file-path')
            if single_path:
                file_paths = [single_path]
        
        if not file_paths:
            return []
        
        # Parámetros compartidos
        sheet_name = dicc.get("sheet-name")
        if not sheet_name or sheet_name == "":
            sheet_name = 0
        
        usecols = dicc.get("usecols")
        if usecols == "" or usecols is None:
            usecols = None
        
        header = int(dicc.get("header", 0))
        
        # Conjunto para almacenar todas las columnas (sin duplicados)
        all_columns = []
        seen_columns = set()
        
        for file_path in file_paths:
            download_params = {
                'api': dicc['api'],
                'drive-id': dicc['drive-id'],
                'file-path': file_path
            }
            local_file = download_sharepoint_file(download_params, temp_dir)
            
            # Verificar que la hoja existe
            xl_file = pd.ExcelFile(local_file)
            available_sheets = xl_file.sheet_names
            
            current_sheet = sheet_name
            if isinstance(current_sheet, str) and current_sheet not in available_sheets:
                # Buscar coincidencia aproximada
                sheet_name_clean = current_sheet.strip()
                for available in available_sheets:
                    if available.strip() == sheet_name_clean:
                        current_sheet = available
                        break
                else:
                    # Si sigue sin encontrarse, usar la primera hoja
                    current_sheet = 0
            
            xl = pd.read_excel(
                local_file, 
                sheet_name=current_sheet, 
                header=header, 
                usecols=usecols
            )
            
            # Añadir columnas manteniendo el orden de aparición
            for col in xl.columns:
                col_str = str(col)
                if col_str not in seen_columns:
                    seen_columns.add(col_str)
                    all_columns.append(col_str)
        
        # Añadir la columna _source_file que se añade automáticamente
        if '_source_file' not in seen_columns:
            all_columns.append('_source_file')
        
        return all_columns
        
    finally:
        # Limpiar archivo temporal
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


# Future: CSV schema function
# def get_schema_sharepoint_csv(dicc):
#     """Obtiene el esquema (columnas) de un archivo CSV de SharePoint."""
#     from .etl_tasks import get_temp_dir
#     
#     temp_dir = get_temp_dir()
#     
#     try:
#         local_file = download_sharepoint_file(dicc, temp_dir)
#         delimiter = dicc.get("delimiter", ",")
#         encoding = dicc.get("encoding", "utf-8")
#         header = int(dicc.get("header", 0))
#         
#         df = pd.read_csv(local_file, delimiter=delimiter, encoding=encoding, header=header, nrows=5)
#         return list(df.columns)
#     finally:
#         if os.path.exists(temp_dir):
#             shutil.rmtree(temp_dir)


# Future: JSON schema function
# def get_schema_sharepoint_json(dicc):
#     """Obtiene el esquema (columnas) de un archivo JSON de SharePoint."""
#     from .etl_tasks import get_temp_dir
#     
#     temp_dir = get_temp_dir()
#     
#     try:
#         local_file = download_sharepoint_file(dicc, temp_dir)
#         df = pd.read_json(local_file, nrows=5)
#         return list(df.columns)
#     finally:
#         if os.path.exists(temp_dir):
#             shutil.rmtree(temp_dir)

def get_schema_csv(dicc):
    # Determine header parameter for pandas
    skiprows = int(dicc.get("header", 0))  # Always respect skip header value
    if dicc.get('schema-option') == 'no-schema':
        header_param = None  # No schema row - pandas will use integer indices
    else:
        header_param = 0  # First row after skipped rows contains schema
    
    if dicc.get('reading') == 'multiple':
        column_array = []
        for file in os.listdir(dicc["csv-file"]):
            if file.endswith((".csv", ".txt",".CSV", ".TXT")):
                csvdata = pd.read_csv(dicc["csv-file"]+'/'+file, sep=dicc["separator"], 
                                    header=header_param, skiprows=skiprows)
                
                # Generate automatic column names if no schema
                if dicc.get('schema-option') == 'no-schema':
                    import string
                    num_cols = len(csvdata.columns)
                    csvdata.columns = [string.ascii_uppercase[i] if i < 26 else f"Column{i+1}" for i in range(num_cols)]
                
                for col in list(csvdata.columns):
                    if col not in column_array:
                        column_array.append(col)
        column_array.append('_filename')
        return column_array
    else:
        csvdata = pd.read_csv(dicc["csv-file"], sep=dicc["separator"], 
                            header=header_param, skiprows=skiprows)
        
        # Generate automatic column names if no schema
        if dicc.get('schema-option') == 'no-schema':
            import string
            num_cols = len(csvdata.columns)
            csvdata.columns = [string.ascii_uppercase[i] if i < 26 else f"Column{i+1}" for i in range(num_cols)]
        
    return list(csvdata.columns)

def get_owners_oracle(dicc):

    db  = database_connections.objects.get(name = dicc['db'])

    params = json.loads(db.connection_params)

    conn = cx_Oracle.connect(
        params['username'],
        params['password'],
        params['dsn']
    )

    c = conn.cursor()
    c.execute("select username as schema_name from sys.all_users order by username")

    owners = []
    for own in c:
        owners.append(own[0])

    conn.close()

    return owners

def get_tables_oracle(dicc):

    db  = database_connections.objects.get(name = dicc['db'])

    params = json.loads(db.connection_params)

    conn = cx_Oracle.connect(
        params['username'],
        params['password'],
        params['dsn']
    )

    c = conn.cursor()
    c.execute("SELECT table_name FROM all_tables WHERE owner = '"+dicc['owner-name']+"' ORDER BY table_name ")

    tables = []
    for tbl in c:
        tables.append(tbl[0])

    conn.close()

    return tables

def get_schema_oracle(dicc):

    db  = database_connections.objects.get(name = dicc['db'])

    params = json.loads(db.connection_params)

    conn = cx_Oracle.connect(
        params['username'],
        params['password'],
        params['dsn']
    )
    
    c = conn.cursor()

    if dicc['checkbox'] == "true":
        try:   
            create_type = "create type cols_name as table of varchar2(32767)"

            c.execute(create_type)
        except:
            print ('Existe el type cols_name')
        try:
            create_function = "CREATE OR REPLACE FUNCTION GET_COLUMNS_NAME(p_selectQuery IN VARCHAR2) RETURN cols_name PIPELINED IS "
            create_function+= "v_cursor_id integer; v_col_cnt integer; v_columns dbms_sql.desc_tab; "
            create_function+= "begin v_cursor_id := dbms_sql.open_cursor; dbms_sql.parse(v_cursor_id, p_selectQuery, dbms_sql.native); "
            create_function+= "dbms_sql.describe_columns(v_cursor_id, v_col_cnt, v_columns); "
            create_function+= "for i in 1 .. v_columns.count loop pipe row(v_columns(i).col_name); end loop; "
            create_function+= "dbms_sql.close_cursor(v_cursor_id); return; exception when others then "
            create_function+= "dbms_sql.close_cursor(v_cursor_id); raise; end;"
            
            c.execute(create_function)
        except:
            print ('Existe la función get_columns_name')
        
        raw_sql = dicc['sql']

        # Divide la SQL en SELECT ... FROM ...
        parts = re.split(r'\bFROM\b', raw_sql, maxsplit=1, flags=re.IGNORECASE)

        if len(parts) == 2:
            select_part, rest_of_query = parts
            # Eliminar variables con arrobas del SELECT, junto con comas opcionales alrededor
            select_cleaned = re.sub(r'(,\s*)?@@.*?@@(,\s*)?', lambda m: ',' if m.group(1) and m.group(2) else '', select_part)

            # Reemplazar variables en la parte restante (FROM y más allá) por 1
            rest_cleaned = re.sub(r"@@.*?@@", "1", rest_of_query)

            sanitized_sql = f"{select_cleaned.strip()} FROM {rest_cleaned.strip()}"
        else:
            # Fallback: no hay FROM → solo reemplazo genérico por 1
            sanitized_sql = re.sub(r"@@.*?@@", "1", raw_sql)

        # Escapar comillas simples
        sql_w = sanitized_sql.replace("'", "''")
            
        sql = "select * from TABLE(GET_COLUMNS_NAME('"+sql_w+"'))"
        
    else:
        sql = "SELECT column_name FROM ALL_TAB_COLUMNS WHERE table_name = '"+dicc['table-name']+"' AND owner = '"+dicc['owner-name']+"'"

    c.execute(sql)

    attrnames =[]
    for attr in c:
        attrnames.append(attr[0].lower())

    """if dicc['check'] == True:
        try:
            drop_type = "DROP TYPE cols_name FORCE"
            c.execute(drop_type)
        except:
            print("No se ha borrado el type cols_name")

        try:
            drop_func = "DROP FUNCTION GET_COLUMNS_NAME"
            c.execute(drop_func)
        except:
            print("No se ha borrado la función get_columns_name")"""

    conn.close()

    return attrnames

def get_proced_indenova(dicc):

    api  = database_connections.objects.get(name = dicc['api'])

    params_str = api.connection_params
    params = json.loads(params_str)

    domain = params['domain']
    api_key = params['api-key']

    url_list = domain + "//api/rest/process/v1/process/list?idsection=27"

    headers_list = {'esigna-auth-api-key': api_key}

    r_list = requests.get(url_list, headers = headers_list)
    
    listProd = []
    for i in json.loads(r_list.content.decode('utf8')):
        listProd.append([i['id'], i['name']])
    
    return listProd

def get_schema_postgres(dicc):
    
    db  = database_connections.objects.get(name = dicc['db'])

    params_str = db.connection_params

    params = json.loads(params_str)
   
    table_name = dicc['tablename']
    
    #postgres connection
    conn = psycopg2.connect(user = params["user"], password = params["password"], host = params["host"], port = params["port"], database = params["database"])
    cur = conn.cursor()

    sql_ = sql.SQL("SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = %s AND table_name   = %s;")

    cur.execute(sql_,[dicc['schema-name'], table_name])
    listSchema = []

    if "query" in dicc:
        attr_query = re.search('SELECT(.*)FROM', dicc['query'])
        attr_query = attr_query.group(1).replace(' ', '')
        list_attr_query = attr_query.split(',')
        for attr in list_attr_query:
            if attr == '*':
                
                for col in cur:
                    if col[1] == 'USER-DEFINED' or col[1] == 'geometry':
                        pass
                    else:
                        listSchema.append(col[0])

            elif attr[0] =='"' and attr[-1] == '"':
                listSchema.append(attr[1:-1])

            elif attr[0] =='"' and '"AS' in attr:

                at = attr.split('"AS')[-1]

                if at[0] =='"' and at[-1] == '"':
                    listSchema.append(at[1:-1])
                else:
                    listSchema.append(at)

            elif ')AS' in attr:

                at = attr.split(')AS')[-1]

                if at[0] =='"' and at[-1] == '"':
                    listSchema.append(at[1:-1])
                else:
                    listSchema.append(at)

            else:
                listSchema.append(attr)

    else:
        for col in cur:
            if col[1] == 'USER-DEFINED' or col[1] == 'geometry':
                pass
            else:
                listSchema.append(col[0])

    conn.commit()
    conn.close()
    cur.close()

    return listSchema


def get_schema_name_postgres(dicc):

    db  = database_connections.objects.get(name = dicc['db'])

    params_str = db.connection_params

    params = json.loads(params_str)

    conn = psycopg2.connect(user = params["user"], password = params["password"], host = params["host"], port = params["port"], database = params["database"])
    cur = conn.cursor()
    
    sql = "SELECT schema_name FROM information_schema.schemata"
    cur.execute(sql)
    conn.commit()
    listSchema = []
    for row in cur:
        listSchema.append(row[0])
    
    conn.close()

    return listSchema

def get_table_name_postgres(dicc):

    db  = database_connections.objects.get(name = dicc['db'])

    params_str = db.connection_params

    params = json.loads(params_str)

    conn = psycopg2.connect(user = params["user"], password = params["password"], host = params["host"], port = params["port"], database = params["database"])
    cur = conn.cursor()
    
    sql_ = "SELECT table_name FROM information_schema.tables WHERE table_schema = %s"
    cur.execute(sql_, [dicc['schema-name']])
    conn.commit()
    listSchema = []
    for row in cur:
        listSchema.append(row[0])
    
    conn.close()

    return listSchema

def getwsSegPass(psw):

    utc = datetime.utcnow()
    
    utcText = utc.strftime('%Y%m%d%H%M%S')

    hashInputString = utcText+psw

    hashInputBytes = hashInputString.encode('utf-8')

    hashBytes = sha256(hashInputBytes).digest()

    hashBase64 = base64.b64encode(hashBytes)

    wsSegPass = utcText+hashBase64.decode()

    return wsSegPass

def get_entities_segex(dicc):

    if dicc['domain'] == 'PRE':
        url = 'https://pre-02000.sedipualba.es/apisegex/'
    else:
        url = 'https://02000.sedipualba.es/apisegex/'

    listEntidades = 'Georef/ListEntidades'

    r = requests.get(url+listEntidades)

    print('listEntidades: ' + str(r.status_code))

    if r.status_code == 200:

        listEntities = []

        for i in r.json():
            listEntities.append([i['Id'], i['Descripcion']])
        
        return listEntities
    else:
        return []

def get_types_segex (dicc):

    api  = database_connections.objects.get(name = dicc['api'])

    params_str = api.connection_params
    params = json.loads(params_str)

    entity = params['entities-list'][0]

    if params['domain'] == 'PRE':
        url = 'https://pre-%s.sedipualba.es/apisegex/' % (entity)
    else:
        url = 'https://%s.sedipualba.es/apisegex/' % (entity)

    wsSegUser = params['user']

    wsSegPass = getwsSegPass(params['password'])

    listTipos = 'Georef/ListTiposGeoref?wsSegUser=%s&wsSegPass=%s&idEntidad=%s' % (wsSegUser, wsSegPass, entity)

    r = requests.get(url+listTipos)

    print('listTipos: '+str(r.status_code))

    if r.status_code == 200:

        listTypes = []

        for i in r.json():
            listTypes.append([i['Id'], i['Descripcion']])
        
        return listTypes
    else:
        return []


def get_schema_json(dicc):
    
    if dicc['api-rest'] == 'true':
        """if dicc['is-pag'] == 'true':
            start = dicc['init-pag']
            jsondata = pd.read_json(dicc['url']+'&'+dicc['pag-par']+'='+str(start))
        else:"""
        jsondata = pd.read_json(dicc['url'])
    else:
        jsondata = pd.read_json(dicc['json-file'])
    
    return list(jsondata.columns)


def get_schema_padron_alba(dicc):
    
    if dicc['service'] == 'PRE':
        url = "http://172.16.136.19/servicios/wp-json/mg-dbq2json/v1/services?s=pre_estadisticas_padron&u=fPqq2xHVQkix&pag=1"
    elif dicc['service'] == 'PRO':
        url = "http://172.16.136.19/servicios/wp-json/mg-dbq2json/v1/services?s=pro_estadisticas_padron&u=fPqq2xHVQkix&pag=1"

    jsondata = pd.read_json(url)
    
    return list(jsondata.columns)


def perf_func(dicc, level=0):
    if dicc:
        if isinstance(dicc, dict):
            for key in dicc.keys():
                tagList.append([level, key])
                perf_func(dicc[key], level+1)
        elif isinstance(dicc, list):
            for i in dicc:
                for key in i.keys():
                    tagList.append([level, key])
                    perf_func(i[key], level+1)

def get_xml_tags(f, r):

    tagList_cleaned = []
    
    if r == 'single':
        listXmlFile = [f.split('//')[1]]

    else:
        listXmlFile = []
        for file in os.listdir(f):
            if file.endswith(".xml"):
                listXmlFile.append(f +'//'+ file)

    
    for xmlFile in listXmlFile:

        xmlStr = open(xmlFile).read()

        xmlDict = xmltodict.parse(xmlStr)

        global tagList

        tagList = []

        perf_func(xmlDict, 0)

        count = 0
        for i in tagList:
            level = i[0]
            for j in tagList[count:]:
                if i == j:
                    pass
                elif j[0] == level+1:
                    j.append(i[1])
                elif j[0] == level:
                    break
            count+=1

        for k in tagList:
            if len(k) == 3:
                item = [str(k[0])+'-'+k[2], k[1]]
            else:
                item = [str(k[0]), k[1]]

            if item not in tagList_cleaned:

                pos = 0
                addItem = True

                for l in reversed(tagList_cleaned):
                    pos += -1
                    if item[0] == '0':
                        break
                    elif l[0] == item[0]:
                        tagList_cleaned.insert(pos, item)
                        addItem = False
                        break
                    elif item[0].split('-')[1] == l[1]:
                        tagList_cleaned.insert(pos, item)
                        addItem = False
                        break
                    
                if addItem:

                    tagList_cleaned.append(item)

    return tagList_cleaned[::-1]


def get_schemas_sqlserver(dicc):

    db  = database_connections.objects.get(name = dicc['db'])

    params = json.loads(db.connection_params)

    conn = pymssql.connect(params['server-sql-server'], params['username-sql-server'], params['password-sql-server'], params['db-sql-server'], tds_version = params["tds-version-sql-server"])
    
    cursor = conn.cursor(as_dict=True)
    
    cursor.execute("SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA  WHERE CATALOG_NAME  = '%s'" % (params['db-sql-server']) )

    schemas = []
    for row in cursor:
        schemas.append(row['SCHEMA_NAME'])

    conn.close()

    return schemas


def get_tables_sqlserver(dicc):

    db  = database_connections.objects.get(name = dicc['db'])

    params = json.loads(db.connection_params)

    conn = pymssql.connect(params['server-sql-server'], params['username-sql-server'], params['password-sql-server'], params['db-sql-server'], params['db-sql-server'], tds_version = '7.0')
    cursor = conn.cursor(as_dict=True)
    
    cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_CATALOG = '%s' AND TABLE_SCHEMA  = '%s' ORDER BY TABLE_NAME" % (params['db-sql-server'], dicc['schema-name']) )

    tables = []
    for row in cursor:
        tables.append(row['TABLE_NAME'])

    conn.close()

    return tables

def get_data_schemas_sqlserver(dicc):

    db  = database_connections.objects.get(name = dicc['db'])

    params = json.loads(db.connection_params)

    conn = pymssql.connect(params['server-sql-server'], params['username-sql-server'], params['password-sql-server'], params['db-sql-server'], tds_version = params["tds-version-sql-server"])    
    
    cursor = conn.cursor(as_dict=True)

    if dicc['checkbox'] == 'true':
        _sql = "SELECT name AS COLUMN_NAME, system_type_name AS DATA_TYPE FROM sys.dm_exec_describe_first_result_set ('%s', NULL, 0) ;" % (dicc['sql'].replace("'", "''"))

    else:
        _sql = "SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = '%s' AND TABLE_NAME  = '%s'" % (dicc['schema-name'], dicc['table-name']) 
    
    cursor.execute(_sql)

    columns = []
    for row in cursor:
        if row['DATA_TYPE'] != 'geometry' and row['DATA_TYPE'] != 'geography':
            columns.append(row['COLUMN_NAME'])

    conn.close()

    return columns


def get_schema_padron_atm(dicc):
    
    try:
        api = database_connections.objects.get(name=dicc['api'])
        credenciales = json.loads(api.connection_params)
    except Exception as e:
        print(f"Error al obtener credenciales de la API: {e}")
        return None
    
    url_auth = "https://pmcloudserver.atm-maggioli.es/api/auth/login" 
    first = True

    # Autenticación
    try:
        response = requests.post(url_auth, json=credenciales)
        response.raise_for_status()  # Lanza una excepción si el código no es 200
        data = response.json()
        token = data.get("accesstoken", {}).get("token")

        if not token:
            print("Error: No se obtuvo el token de autenticación.")
            return None
    except requests.RequestException as e:
        print(f"Error en la solicitud de autenticación: {e}")
        return None

    
    start = 0
    length = 20
        
    while length == 20:
        params = {
            "id": 1,
            "start": start,
            "length": 20,
            "sort": None,
            "order": None,
            "gettotal": True,
            "filtro": None,
            "columns": [
                {
                "name": None,
                "data": None
                }
            ]
            }
    
        headers = {"Authorization": f"Bearer {token}"}
        url_list = f"https://pmcloudserver.atm-maggioli.es/padron/api/habitante/GetList/"
        
        
        try:
            response_list = requests.post(url_list, headers=headers, json=params)
            response_list.raise_for_status()  
            habitantes = response_list.json()

            if "data" not in habitantes:
                print("Advertencia: No se encontró 'data' en la respuesta.")
                break

        except requests.RequestException as e:
            print(f"Error al obtener la lista de habitantes: {e}")
            break 
        
        for hab in habitantes['data']:
            
            if hab["bfechabaja"] == False:
                
                if hab['tipodocu'] == '1':
                    documento = hab.get('dni', '') + hab.get('nif', '')
                    
                elif hab['tipodocu'] == '2':
                    documento = hab.get('pasaporte', '')
                    
                elif hab['tipodocu'] == '3':
                    documento = hab.get('lextr', '') + hab.get('dni', '') + hab.get('nif', '')
                else:
                    documento = None

                # Consulta de datos del habitante
                try:
                    
                    if documento:
                        url_modelos = f"https://pmcloudserver.atm-maggioli.es/padron/api/habitante/GetPorDocumento/{documento}"
                        response_modelos = requests.get(url_modelos, headers=headers)
                        response_modelos.raise_for_status()

                        data = response_modelos.json()

                        habitante = data.get('habitante', {})
                        lastmovimiento = data.get('lastmovimiento', {})
                        vivienda = data.get('vivienda', {})
                        domicilio = data.get('domicilio', {})
                        
                        habitante.pop("tabla", None)
                        lastmovimiento.pop("tabla", None)
                        vivienda.pop("tabla", None)
                        domicilio.pop("tabla", None)

                        habitante_keys = list(habitante.keys()) 
                        lastmovimiento_keys = list(lastmovimiento.keys()) 
                        vivienda_keys = list(vivienda.keys()) 
                        domicilio_keys = list(domicilio.keys())
                        
                        all_keys = list(habitante.keys()) + list(lastmovimiento.keys()) + list(vivienda.keys()) + list(domicilio.keys())
                        duplicated_keys = {k for k in all_keys if all_keys.count(k) > 1 and not k.startswith("id")}

                        def agregar_sufijo_lista(keys, sufijo):
                            return [f"{k}{sufijo}" if k in duplicated_keys else k for k in keys]
                        
                        columns = habitante_keys + agregar_sufijo_lista(lastmovimiento_keys, "_lastmovimiento") + agregar_sufijo_lista(vivienda_keys, "_vivienda") + agregar_sufijo_lista(domicilio_keys, "_domicilio")
                        
                        return columns
                    
                except requests.RequestException as e:
                    print(f"Error al obtener datos del habitante: {e}")
        
        length = len(habitantes['data'])
        start += 20

