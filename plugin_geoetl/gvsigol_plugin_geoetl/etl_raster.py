# -*- coding: utf-8 -*-
"""
Nodos predictivos / ráster de geoetl.

Contrato con el motor (tasks.py): cada nodo recibe un dict de parámetros y
devuelve una lista de strings, una por puerto de salida. Las tablas viajan como
nombre de tabla PostGIS; los ráster y los modelos viajan como RUTA ABSOLUTA de
fichero (.tif / .joblib) dentro del directorio de artefactos (ver artifacts_root).
Cada artefacto puede tener un fichero auxiliar "<ruta>.meta.json".

Las funciones núcleo (sample_raster_pixels, train_model, predict_raster_file,
polygonize_raster_file) no dependen de la BD ni de Django para poder probarse
con datos sintéticos. rasterio y scikit-learn se importan al usarlos.
"""

import json
import os
import re
import shutil
import tempfile
import time
import unicodedata
import uuid

import numpy as np
import pandas as pd
from sqlalchemy import create_engine

from . import settings as plugin_settings
from .settings import GEOETL_DB

# Valores por defecto (los diálogos del canvas los muestran como "avanzado")
DEFAULT_N_ESTIMATORS = 100
DEFAULT_MIN_SAMPLES_LEAF = 1
DEFAULT_TEST_PERCENT = 20
DEFAULT_SEED = 42
MIN_TRAIN_ROWS = 10
# Un objetivo entero con pocos valores distintos se considera clasificación
MAX_CLASSES_AS_INTEGER = 20
RASTER_EXTENSIONS = ('.tif', '.tiff')
MODEL_EXTENSION = '.joblib'
PREDICT_BLOCK = 512
REGRESSION_NODATA = -9999.0
# Columnas auxiliares que añade Muestrear ráster (posición y polígono de origen de cada píxel).
# Sirven para la validación espacial; nunca se usan como variables predictoras.
AUX_X, AUX_Y, AUX_POLY = '__x', '__y', '__poly_id'
AUX_COLUMNS = (AUX_X, AUX_Y, AUX_POLY)
VALIDATION_MODES = ('auto', 'random', 'polygon', 'block')
# Variables que prueba cada división: 'auto' = √p en clasificación y p/3 en regresión (Breiman, 2001)
MAX_FEATURES_OPTIONS = ('auto', 'sqrt', 'third', 'all')
PERMUTATION_MAX_ROWS = 20000
PERMUTATION_REPEATS = 5
DEFAULT_FOLDS = 5
MAX_FOLDS = 10

# Filtro de mayoría / tamaño mínimo de parche
MAJORITY_WINDOWS = (3, 5, 7)
MAX_ITERATIONS = 5
MAX_SIEVE_PIXELS = 150000000   # sieve necesita el ráster entero en memoria

# Índices espectrales: papel de cada banda (en el orden de los parámetros band-1, band-2, band-3)
INDEX_DEFS = {
    'ndvi': {'roles': ('nir', 'red')},
    'ndwi': {'roles': ('green', 'nir')},
    'ndbi': {'roles': ('swir', 'nir')},
    'savi': {'roles': ('nir', 'red')},
    'evi': {'roles': ('nir', 'red', 'blue')},
    'brightness': {'roles': ()},
    'nd': {'roles': ('a', 'b')},
}
DEFAULT_SAVI_L = 0.5
# Conversión de los valores de la imagen a reflectancia: reflectancia = (valor + offset) / escala.
# Los índices normalizados solo son independientes de la escala si el offset es 0.
REFLECTANCE_PRESETS = {
    'none': (1.0, 0.0),                                   # se usan los valores tal cual
    'uint8': (255.0, 0.0),                                # imágenes de 8 bits (0-255), p. ej. ortofotos
    'sentinel2_l2a': (10000.0, -1000.0),                  # Sentinel-2 L2A, línea base 04.00 (desde el 25-01-2022)
    'sentinel2_l2a_pre2022': (10000.0, 0.0),              # Sentinel-2 L2A anterior a 2022
    'landsat_c2_l2': (1.0 / 0.0000275, -0.2 / 0.0000275),  # Landsat Colección 2 nivel 2: DN * 0.0000275 - 0.2
}
# Rango físico de los índices; fuera de él el valor es ruido (agua, nubes, datos que no son reflectancia)
INDEX_VALID_RANGE = {'evi': (-1.0, 1.0)}

ARTIFACTS_SUBDIR = 'artifacts'


# --------------------------------------------------------------------------
# Artefactos (ráster y modelos) en disco
# --------------------------------------------------------------------------

def ensure_dir(path, mode=0o755, owner_from=None):
    """
    Crea un directorio (y los que falten). Si quien lo crea es root, por ejemplo un administrador que lanza
    un comando dentro del contenedor, cada directorio nuevo pasa a ser del dueño de su directorio padre
    o, si se indica ``owner_from``, del dueño de esa ruta: los procesos del ETL corren como otro usuario
    (www-data) y, si no, no podrían escribir en él. ``owner_from`` hace falta cuando el padre es de root,
    como /tmp.
    """
    missing, probe = [], path
    while probe and not os.path.isdir(probe):
        missing.append(probe)
        probe = os.path.dirname(probe)
    os.makedirs(path, mode=mode, exist_ok=True)
    if hasattr(os, 'geteuid') and os.geteuid() == 0:
        owner = None
        if owner_from:
            try:
                owner = os.stat(owner_from)
            except OSError:
                owner = None
        for created in reversed(missing):
            try:
                ref = owner or os.stat(os.path.dirname(created))
                os.chown(created, ref.st_uid, ref.st_gid)
            except OSError:
                pass


def service_owner_path():
    """
    Ruta cuyo dueño es el usuario con el que corre el ETL (el directorio del gestor de ficheros, o
    MEDIA_ROOT). Sirve para dar a ese usuario los directorios que crea root en zonas de root como /tmp.
    """
    try:
        from django.conf import settings
        for name in ('FILEMANAGER_DIRECTORY', 'MEDIA_ROOT'):
            value = getattr(settings, name, None)
            if value and os.path.isdir(value):
                return value
    except Exception:
        pass
    return None


def output_profile(src):
    """
    Perfil base para escribir un GeoTIFF a partir de otro ráster: solo lo que describe su malla
    (tamaño, georreferenciación, tipo y sin dato). NO se copia la compresión ni la interpretación del
    color del original: un GeoTIFF comprimido en JPEG con color YCbCr (típico del PNOA) no se puede
    reescribir con otra compresión, ni con un número de bandas o un tipo de dato distintos.
    """
    return {'driver': 'GTiff', 'width': src.width, 'height': src.height, 'count': src.count,
            'dtype': src.dtypes[0], 'crs': src.crs, 'transform': src.transform, 'nodata': src.nodata}


def artifacts_root():
    """Directorio donde se guardan los artefactos de las ejecuciones."""
    try:
        from django.conf import settings
        temp_root = getattr(settings, 'TEMP_ROOT', None)
    except Exception:
        temp_root = None
    base = os.path.join(temp_root or tempfile.gettempdir(), 'plugin_geoetl', ARTIFACTS_SUBDIR)
    owner_from = service_owner_path()
    ensure_dir(base, owner_from=owner_from)
    if hasattr(os, 'geteuid') and os.geteuid() == 0 and owner_from:
        # Repara directorios que root dejó suyos con versiones anteriores (solo los dos del plugin).
        _hand_over_if_root(os.path.dirname(base), owner_from)
        _hand_over_if_root(base, owner_from)
    if not os.access(base, os.W_OK | os.X_OK):
        raise PermissionError(
            'El directorio de trabajo del ETL %s no es escribible por el usuario del proceso. '
            'Un administrador debe darlo al usuario del servicio (p. ej. chown www-data).' % base)
    return base


def _hand_over_if_root(path, owner_from):
    try:
        current, owner = os.stat(path), os.stat(owner_from)
        if current.st_uid == 0 and owner.st_uid != 0:
            os.chown(path, owner.st_uid, owner.st_gid)
    except OSError:
        pass


def new_artifact_path(node_id, extension):
    """Ruta nueva y única para un artefacto de un nodo."""
    safe_id = re.sub(r'[^A-Za-z0-9_-]', '_', str(node_id))
    return os.path.join(artifacts_root(), '%s_%s%s' % (safe_id, uuid.uuid4().hex[:8], extension))


def is_artifact_ref(value):
    """True si un resultado de nodo es la ruta de un fichero y no una tabla."""
    return isinstance(value, str) and os.path.isabs(value)


def is_raster_ref(value):
    return is_artifact_ref(value) and value.lower().endswith(RASTER_EXTENSIONS)


def is_model_ref(value):
    return is_artifact_ref(value) and value.lower().endswith(MODEL_EXTENSION)


def meta_path(path):
    return path + '.meta.json'


def read_meta(path):
    try:
        with open(meta_path(path), 'r', encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def write_meta(path, meta):
    with open(meta_path(path), 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False)


def remove_artifact(path):
    """
    Borra un artefacto (y su .meta.json) al terminar la ejecución. Solo borra ficheros que estén
    dentro del directorio de artefactos: una ruta ajena no se toca. Si es un enlace (entrada
    ráster), se borra el enlace y nunca el fichero original. Devuelve True si borró algo.
    """
    if not is_artifact_ref(path):
        return False
    root = os.path.realpath(artifacts_root())
    # realpath de la CARPETA, no del fichero: así un enlace se identifica por su propia ruta
    parent = os.path.realpath(os.path.dirname(path))
    if parent != root:
        return False
    removed = False
    for candidate in (path, meta_path(path)):
        try:
            if os.path.lexists(candidate):
                os.remove(candidate)
                removed = True
        except OSError:
            continue
    return removed


def clean_old_artifacts(max_age_hours):
    """Borra los artefactos más antiguos que el TTL. Devuelve cuántos ficheros borró."""
    root = artifacts_root()
    limit = time.time() - max_age_hours * 3600
    removed = 0
    for name in os.listdir(root):
        path = os.path.join(root, name)
        try:
            if os.path.lexists(path) and os.lstat(path).st_mtime < limit:
                os.remove(path)
                removed += 1
        except OSError:
            continue
    return removed


# --------------------------------------------------------------------------
# Límites de recursos (configurables en settings.py / variables de entorno ETL_RASTER_*)
# --------------------------------------------------------------------------

def _limit(name, default):
    """Valor entero de un límite del plugin; si no está definido o no es válido, el valor por defecto."""
    try:
        return int(getattr(plugin_settings, name, default))
    except (TypeError, ValueError):
        return default


def n_jobs():
    """Procesos para entrenar y evaluar (-1 = todos los núcleos)."""
    value = _limit('ETL_RASTER_N_JOBS', -1)
    return value if value != 0 else 1


def check_raster_size(width, height, what='El ráster'):
    """Falla con un mensaje claro si el ráster supera el máximo de píxeles configurado (0 = sin límite)."""
    maximum = _limit('ETL_RASTER_MAX_PIXELS', 4000000000)
    if maximum > 0 and width * height > maximum:
        raise ValueError('%s tiene %s píxeles y el máximo permitido es %s. Recórtalo o reduce su resolución '
                         'antes de procesarlo (o pide al administrador que suba ETL_RASTER_MAX_PIXELS).'
                         % (what, format(width * height, ',d').replace(',', '.'),
                            format(maximum, ',d').replace(',', '.')))


def check_free_space(width, height, count, itemsize, directory=None):
    """
    Comprueba que hay espacio para el ráster que se va a escribir. Los GeoTIFF se comprimen, así
    que solo se exige la mitad del tamaño sin comprimir más el margen mínimo configurado.
    """
    directory = directory or artifacts_root()
    needed = int(width) * int(height) * int(count) * int(itemsize) // 2
    margin = _limit('ETL_RASTER_MIN_FREE_MB', 200) * 1024 * 1024
    try:
        free = shutil.disk_usage(directory).free
    except OSError:
        return          # no se puede medir: no bloquea
    if free < needed + margin:
        raise ValueError('No hay espacio suficiente en el directorio temporal del servidor: hacen falta unos '
                         '%d MB y quedan %d MB libres.' % ((needed + margin) // 2**20, free // 2**20))


def subsample_training_rows(df, target, max_rows, seed=DEFAULT_SEED):
    """
    Reduce una tabla de entrenamiento demasiado grande. En clasificación se reparte por clase
    conservando todas las filas de las clases pequeñas; en regresión es un muestreo aleatorio.
    Devuelve (tabla, filas_originales) y filas_originales es None si no se tocó nada.
    """
    original = len(df)
    if not max_rows or max_rows <= 0 or original <= max_rows:
        return df, None
    classification = detect_problem(df[target].dropna()) == 'classification'
    if classification:
        fraction = max_rows / float(original)
        parts = []
        for _, group in df.groupby(target, sort=True, dropna=True):
            keep = len(group) if len(group) <= 1000 else max(1000, int(len(group) * fraction))
            parts.append(group.sample(n=min(len(group), keep), random_state=seed))
        reduced = pd.concat(parts)
        # Si las clases pequeñas ya ocupan casi todo el cupo, se recorta el resto por igual
        if len(reduced) > max_rows * 1.5:
            reduced = reduced.sample(n=int(max_rows * 1.5), random_state=seed)
    else:
        reduced = df.sample(n=max_rows, random_state=seed)
    return reduced.sort_index().reset_index(drop=True), original


# --------------------------------------------------------------------------
# Utilidades
# --------------------------------------------------------------------------

def _identifier(text):
    """Nombre válido y estable para columna SQL a partir de un alias libre."""
    text = unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'[^0-9a-zA-Z_]+', '_', text).strip('_').lower()
    if not text or text[0].isdigit():
        text = 'b_' + text
    return text


def parse_band_names(raw, count):
    """
    Nombres de banda: lista o texto separado por comas. Lo que falte se completa con
    b1..bn; se hacen únicos y válidos como columna.
    """
    if isinstance(raw, str):
        raw = [x for x in raw.split(',')]
    raw = list(raw or [])
    names = []
    for i in range(count):
        base = raw[i] if i < len(raw) and str(raw[i]).strip() else 'b%d' % (i + 1)
        name = _identifier(base)
        candidate, n = name, 2
        while candidate in names:
            candidate = '%s_%d' % (name, n)
            n += 1
        names.append(candidate)
    return names


def _to_float(value, default=None):
    try:
        if value is None or str(value).strip() == '':
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value, default):
    try:
        if value is None or str(value).strip() == '':
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _engine():
    conn_string = (
        'postgresql://' + GEOETL_DB['user'] + ':' + GEOETL_DB['password']
        + '@' + GEOETL_DB['host'] + ':' + str(GEOETL_DB['port']) + '/' + GEOETL_DB['database']
    )
    return create_engine(conn_string)


def _write_table(df, table_name):
    engine = _engine()
    try:
        with engine.connect() as conn:
            df.to_sql(table_name, con=conn, schema=GEOETL_DB['schema'],
                      if_exists='replace', index=False, chunksize=5000)
    finally:
        engine.dispose()


def _read_samples_table(table_name, class_attr, geom_attr='wkb_geometry'):
    """Lee la tabla de muestras (polígonos + clase) con su CRS."""
    import geopandas as gpd
    from .etl_tasks import get_type_n_srid

    srid, _ = get_type_n_srid(table_name, geom=geom_attr)
    engine = _engine()
    try:
        query = 'SELECT "%s", "%s" FROM "%s"."%s"' % (
            class_attr.replace('"', '""'), geom_attr.replace('"', '""'),
            GEOETL_DB['schema'], table_name.replace('"', '""'))
        with engine.connect() as conn:
            gdf = gpd.read_postgis(query, conn, geom_col=geom_attr,
                                   crs=('EPSG:%d' % srid) if srid else None)
    finally:
        engine.dispose()
    return gdf


# --------------------------------------------------------------------------
# Núcleo: muestreo de píxeles
# --------------------------------------------------------------------------

def resolve_raster_path(path):
    """
    Ruta real de un GeoTIFF indicado por el usuario. Quita el prefijo file:// del selector
    de ficheros y exige que quede dentro del directorio del gestor de ficheros, para que el
    ETL no pueda leer ni enlazar ficheros arbitrarios del servidor.
    """
    if not path or not isinstance(path, str):
        raise ValueError('Selecciona un fichero GeoTIFF.')
    if path.startswith('file://'):
        path = path[7:]
    real = os.path.realpath(path)
    try:
        from django.conf import settings
        root = getattr(settings, 'FILEMANAGER_DIRECTORY', None)
    except Exception:
        root = None
    if root:
        root = os.path.realpath(root)
        if os.path.commonpath([root, real]) != root:
            raise ValueError('El fichero debe estar en el gestor de ficheros.')
    if not real.lower().endswith(RASTER_EXTENSIONS):
        raise ValueError('El fichero debe ser un GeoTIFF (.tif / .tiff).')
    if not os.path.isfile(real):
        raise ValueError('No se encuentra el fichero ráster "%s".' % os.path.basename(real))
    return real


def raster_schema(params):
    """
    Datos que necesita el diálogo de Entrada Ráster: nombres de banda (con los alias
    del usuario), CRS y tamaño.
    """
    real = resolve_raster_path(params.get('raster-file'))
    info = raster_summary(real)
    return {'bands': parse_band_names(params.get('band-names'), info['bands']),
            'crs': info['crs'], 'width': info['width'], 'height': info['height']}


def raster_summary(path):
    """Resumen del ráster: nº de bandas, CRS y nodata."""
    import rasterio
    with rasterio.open(path) as src:
        return {
            'bands': src.count,
            'crs': src.crs.to_string() if src.crs else None,
            'nodata': src.nodata,
            'width': src.width,
            'height': src.height,
        }


def sample_raster_pixels(raster_path, gdf, class_attr, band_names=None,
                         max_per_class=None, seed=DEFAULT_SEED):
    """
    Extrae los píxeles que caen dentro de cada polígono.
    Devuelve un DataFrame con una columna por banda más la columna de clase.
    El nombre de la columna de clase es el de class_attr.
    """
    import rasterio
    import rasterio.transform
    from rasterio.mask import mask as rio_mask

    if class_attr not in gdf.columns:
        raise ValueError('La tabla de muestras no tiene la columna de clase "%s".' % class_attr)

    with rasterio.open(raster_path) as src:
        names = band_names or parse_band_names(None, src.count)
        if class_attr in names:
            raise ValueError('La columna de clase "%s" coincide con el nombre de una banda; '
                             'renombra la banda o la clase.' % class_attr)
        if src.crs is None:
            raise ValueError('El ráster no tiene sistema de coordenadas.')
        if gdf.crs is None:
            raise ValueError('La tabla de muestras no tiene sistema de coordenadas.')
        samples = gdf.to_crs(src.crs)
        nodata = src.nodata
        chunks = []
        for poly_id, (geom, label) in enumerate(zip(samples.geometry, samples[class_attr])):
            if geom is None or geom.is_empty or label is None or (isinstance(label, float) and np.isnan(label)):
                continue
            try:
                data, transform = rio_mask(src, [geom], crop=True, filled=False)
            except ValueError:
                # El polígono no intersecta el ráster
                continue
            # data: (bandas, alto, ancho) enmascarado; descarta píxeles fuera o con nodata
            invalid = np.ma.getmaskarray(data).any(axis=0)
            values = np.ma.getdata(data).astype('float64')
            invalid |= np.isnan(values).any(axis=0)
            if nodata is not None:
                invalid |= (values == nodata).any(axis=0)
            pixels = values[:, ~invalid].T
            if pixels.shape[0] == 0:
                continue
            frame = pd.DataFrame(pixels, columns=names)
            frame[class_attr] = label
            # Centro de cada píxel (CRS del ráster) y polígono de origen, para validar por zonas
            rows_idx, cols_idx = np.nonzero(~invalid)
            xs, ys = rasterio.transform.xy(transform, rows_idx, cols_idx, offset='center')
            frame[AUX_X] = np.asarray(xs, dtype='float64')
            frame[AUX_Y] = np.asarray(ys, dtype='float64')
            frame[AUX_POLY] = poly_id
            chunks.append(frame)

    if not chunks:
        raise ValueError('Ningún polígono de muestra intersecta con el ráster, '
                         'o todos sus píxeles son nodata. Revisa los sistemas de coordenadas.')

    df = pd.concat(chunks, ignore_index=True)
    if max_per_class:
        df = (df.groupby(class_attr, group_keys=False)
                .apply(lambda g: g.sample(n=min(len(g), max_per_class), random_state=seed))
                .reset_index(drop=True))
    return df


# --------------------------------------------------------------------------
# Núcleo: entrenamiento
# --------------------------------------------------------------------------

def detect_problem(target, forced='auto'):
    """'classification' o 'regression' según el tipo de la variable objetivo."""
    if forced in ('classification', 'regression'):
        return forced
    if pd.api.types.is_bool_dtype(target) or not pd.api.types.is_numeric_dtype(target):
        return 'classification'
    if pd.api.types.is_integer_dtype(target) and target.nunique() <= MAX_CLASSES_AS_INTEGER:
        return 'classification'
    values = target.dropna()
    if (values == values.round()).all() and values.nunique() <= MAX_CLASSES_AS_INTEGER:
        return 'classification'
    return 'regression'


def _clean_class_label(value):
    """Etiquetas serializables y estables (enteros sin '.0')."""
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)) and float(value).is_integer():
        return int(value)
    if isinstance(value, np.generic):
        return value.item()
    return value


def _validation_groups(data, mode, block_size):
    """
    Grupo espacial de cada fila para la validación cruzada: el polígono de muestra de
    origen o la celda de una cuadrícula de lado block_size (unidades del CRS del ráster).
    """
    if mode == 'polygon':
        if AUX_POLY not in data.columns:
            raise ValueError('La validación por polígono necesita la tabla que genera "Muestrear ráster" '
                             '(no encuentra el polígono de origen de cada píxel).')
        return pd.factorize(data[AUX_POLY])[0]
    if AUX_X not in data.columns or AUX_Y not in data.columns:
        raise ValueError('La validación por bloques necesita la tabla que genera "Muestrear ráster" '
                         '(no encuentra las coordenadas de cada píxel).')
    if not block_size or block_size <= 0:
        raise ValueError('Indica el tamaño del bloque (mayor que 0) para la validación por bloques.')
    cells = (np.floor(data[AUX_X].to_numpy() / block_size).astype('int64').astype(str).astype(object)
             + ':' + np.floor(data[AUX_Y].to_numpy() / block_size).astype('int64').astype(str).astype(object))
    return pd.factorize(cells)[0]


def _check_groups(y, groups, folds, mode, classification):
    """Comprueba que hay grupos suficientes y devuelve el número de particiones a usar."""
    what = 'polígonos de muestra' if mode == 'polygon' else 'bloques'
    n_groups = len(np.unique(groups))
    if n_groups < 2:
        raise ValueError('Solo hay %d %s: no se puede validar por zonas. Usa más muestras, un bloque '
                         'más pequeño o la validación aleatoria.' % (n_groups, what))
    if classification:
        for c in pd.unique(y):
            g = len(np.unique(groups[y == c]))
            if g < 2:
                raise ValueError('La clase "%s" solo tiene muestras en 1 de los %s: no se puede validar '
                                 'por zonas. Añade más %s de esa clase o usa la validación aleatoria.'
                                 % (c, what, what))
    return max(2, min(folds, n_groups))


def _classification_report(y_true, y_pred, classes, report):
    """Añade al informe exactitud, kappa, métricas por clase y matriz de confusión; devuelve la matriz ancha."""
    from sklearn.metrics import (accuracy_score, balanced_accuracy_score, cohen_kappa_score,
                                 confusion_matrix, f1_score, precision_recall_fscore_support)

    import warnings
    with warnings.catch_warnings():
        # Normal al evaluar: puede haber clases predichas que no están en la referencia (y al revés)
        warnings.simplefilter('ignore')
        report.append(('metric', 'accuracy', float(accuracy_score(y_true, y_pred))))
        report.append(('metric', 'balanced_accuracy', float(balanced_accuracy_score(y_true, y_pred))))
        report.append(('metric', 'f1_weighted',
                       float(f1_score(y_true, y_pred, average='weighted', zero_division=0))))
        report.append(('metric', 'kappa', float(cohen_kappa_score(y_true, y_pred))))
        prec, rec, f1, support = precision_recall_fscore_support(
            y_true, y_pred, labels=classes, zero_division=0)
    for c, p, r, f, n in zip(classes, prec, rec, f1, support):
        report.append(('per_class', '%s:precision' % c, float(p)))
        report.append(('per_class', '%s:recall' % c, float(r)))
        report.append(('per_class', '%s:f1' % c, float(f)))
        report.append(('per_class', '%s:support' % c, float(n)))

    cm = confusion_matrix(y_true, y_pred, labels=classes)
    for i, real in enumerate(classes):
        for j, pred in enumerate(classes):
            report.append(('confusion', '%s -> %s' % (real, pred), float(cm[i, j])))

    columns = []
    for c in classes:
        base = 'pred_' + _identifier(c)
        name, n = base, 2
        while name in columns:
            name = '%s_%d' % (base, n)
            n += 1
        columns.append(name)
    matrix = pd.DataFrame(cm.astype('int64'), columns=columns)
    matrix.insert(0, 'real', [str(c) for c in classes])
    matrix['total'] = cm.sum(axis=1).astype('int64')
    matrix['recall'] = [float(cm[i, i] / cm[i].sum()) if cm[i].sum() else 0.0 for i in range(len(classes))]
    return matrix


def _empty_matrix(classes):
    columns = ['real'] + ['pred_' + _identifier(c) for c in classes] + ['total', 'recall']
    return pd.DataFrame({c: pd.Series(dtype='object' if c == 'real' else 'float64') for c in columns})


def _resolve_max_features(option, classification):
    """Valor de max_features de scikit-learn para la opción elegida."""
    option = 'auto' if option in (None, '') else option
    if option == 'auto':
        return 'sqrt' if classification else 1.0 / 3.0
    if option == 'sqrt':
        return 'sqrt'
    if option == 'third':
        return 1.0 / 3.0
    if option == 'all':
        return 1.0
    try:
        fraction = float(option)
    except (TypeError, ValueError):
        raise ValueError('Valor no válido para las variables por división: %s.' % option)
    if not 0 < fraction <= 1:
        raise ValueError('La fracción de variables por división debe estar entre 0 y 1.')
    return fraction


def _auto_validation(data, y, classification):
    """'polygon' si la tabla trae el polígono de origen y todas las clases tienen 2 polígonos o más; si no, 'random'."""
    if AUX_POLY not in data.columns:
        return 'random'
    groups = pd.factorize(data[AUX_POLY])[0]
    try:
        _check_groups(y, groups, 2, 'polygon', classification)
    except ValueError:
        return 'random'
    return 'polygon'


class PermutationImportance(object):
    """
    Importancia por permutación (Breiman, 2001) medida con los datos de evaluación, no con los de entrenamiento:
    cuánto empeora la nota (exactitud equilibrada o R²) al desordenar cada variable. Es menos sesgada que la
    importancia por impureza (Strobl et al., 2007). Se promedia entre rondas, ponderada por filas.
    """

    def __init__(self, features, classification, seed):
        self.features, self.classification, self.seed = features, classification, seed
        self.total, self.weight = np.zeros(len(features)), 0

    def add(self, model, X, y):
        import warnings
        from sklearn.inspection import permutation_importance
        if len(y) < 2:
            return
        if len(y) > PERMUTATION_MAX_ROWS:
            keep = np.random.RandomState(self.seed).choice(len(y), PERMUTATION_MAX_ROWS, replace=False)
            X, y = X[keep], y[keep]
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            result = permutation_importance(model, X, y, n_repeats=PERMUTATION_REPEATS, random_state=self.seed,
                                            scoring='balanced_accuracy' if self.classification else 'r2', n_jobs=1)
        self.total += result.importances_mean * len(y)
        self.weight += len(y)

    def rows(self):
        if not self.weight:
            return []
        values = self.total / self.weight
        return [('importance_permutation', f, float(v)) for f, v in sorted(zip(self.features, values), key=lambda t: -t[1])]


def train_model(df, target, features, problem='auto', n_estimators=DEFAULT_N_ESTIMATORS,
                max_depth=None, min_samples_leaf=DEFAULT_MIN_SAMPLES_LEAF,
                test_percent=DEFAULT_TEST_PERCENT, seed=DEFAULT_SEED,
                validation='random', folds=DEFAULT_FOLDS, block_size=None, max_features='auto'):
    """
    Entrena un Random Forest con filas que tienen valor en el objetivo.

    max_features: variables que prueba cada división. 'auto' sigue a Breiman (2001): √p en clasificación
    y p/3 en regresión; 'sqrt', 'third' (p/3), 'all' (todas: equivale a bagging de árboles) o una fracción.
    'auto' en validation: por polígonos si la tabla viene de Muestrear ráster y cada clase tiene al
    menos 2 polígonos; si no, reserva aleatoria. El modo usado queda en el informe (sección validation).

    validation: 'random' (hold-out aleatorio de test_percent %), 'polygon' (validación
    cruzada dejando fuera polígonos de muestra enteros) o 'block' (dejando fuera bloques de
    una cuadrícula de lado block_size). Las dos últimas necesitan las columnas auxiliares de
    Muestrear ráster y estiman mejor la calidad real, porque los píxeles vecinos se parecen.

    Devuelve (bundle, report, matrix): bundle es el dict del modelo; report un DataFrame
    (section, name, value) con balance de clases, métricas, matriz y importancia; matrix la
    matriz de confusión en formato ancho (clasificación) o las métricas (regresión).
    """
    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    from sklearn.model_selection import GroupKFold, StratifiedGroupKFold, train_test_split

    if validation not in VALIDATION_MODES:
        raise ValueError('Tipo de validación desconocido: %s.' % validation)
    if target not in df.columns:
        raise ValueError('La variable objetivo "%s" no existe en la tabla.' % target)
    features = [f for f in features if f != target and f not in AUX_COLUMNS]
    if not features:
        raise ValueError('Selecciona al menos una variable predictora.')
    missing = [f for f in features if f not in df.columns]
    if missing:
        raise ValueError('Variables predictoras que no existen en la tabla: %s' % ', '.join(missing))

    aux = [c for c in AUX_COLUMNS if c in df.columns]
    data = df[features + [target] + aux].replace([np.inf, -np.inf], np.nan)
    data = data.dropna(subset=[target])
    # Las predictoras deben ser numéricas; filas con valores no numéricos o nulos se descartan
    for f in features:
        data[f] = pd.to_numeric(data[f], errors='coerce')
        if len(data) and data[f].isna().all():
            raise ValueError('La variable predictora "%s" no es numérica; quítala de la selección.' % f)
    data = data.dropna(subset=features).reset_index(drop=True)
    if len(data) < MIN_TRAIN_ROWS:
        raise ValueError('Hay %d filas válidas para entrenar y se necesitan al menos %d.'
                         % (len(data), MIN_TRAIN_ROWS))

    problem = detect_problem(data[target], problem)
    classification = problem == 'classification'
    X = data[features].to_numpy(dtype='float64')
    report = []
    split_features = _resolve_max_features(max_features, classification)

    def new_model():
        if classification:
            return RandomForestClassifier(
                n_estimators=n_estimators, max_depth=max_depth, min_samples_leaf=min_samples_leaf,
                max_features=split_features, random_state=seed, n_jobs=n_jobs(), class_weight='balanced')
        return RandomForestRegressor(
            n_estimators=n_estimators, max_depth=max_depth, min_samples_leaf=min_samples_leaf,
            max_features=split_features, random_state=seed, n_jobs=n_jobs())

    if classification:
        y_raw = data[target].map(_clean_class_label)
        classes = sorted(y_raw.unique().tolist(), key=lambda v: (str(type(v)), v))
        if len(classes) < 2:
            raise ValueError('Se necesitan al menos 2 clases distintas y solo hay: %s.' % classes)
        y = y_raw.to_numpy()
        for c in classes:
            report.append(('class_balance', str(c), float((y_raw == c).sum())))
    else:
        classes = None
        y = pd.to_numeric(data[target], errors='coerce').to_numpy(dtype='float64')

    report.append(('training', 'rows', float(len(data))))
    if validation == 'auto':
        validation = _auto_validation(data, y, classification)
    report.append(('validation', validation, 1.0))

    # --- Evaluación: pares (real, predicho) fuera de muestra ---
    y_true = y_pred = None
    fold_scores = []
    permutation = PermutationImportance(features, classification, seed)
    if validation == 'random':
        test_fraction = max(0, min(50, test_percent)) / 100.0
        if test_fraction > 0 and len(data) >= 2 * MIN_TRAIN_ROWS:
            stratify = None
            if classification:
                counts = pd.Series(y).value_counts()
                if counts.min() >= 2 and int(round(len(y) * test_fraction)) >= len(counts):
                    stratify = y
            try:
                X_tr, X_te, y_tr, y_te = train_test_split(
                    X, y, test_size=test_fraction, random_state=seed, stratify=stratify)
            except ValueError:
                X_tr = None
            if X_tr is not None:
                model = new_model()
                model.fit(X_tr, y_tr)
                y_true, y_pred = y_te, model.predict(X_te)
                report.append(('training', 'test_rows', float(len(y_te))))
                permutation.add(model, X_te, y_te)
    else:
        groups = _validation_groups(data, validation, block_size)
        n_folds = _check_groups(y, groups, min(max(2, folds or DEFAULT_FOLDS), MAX_FOLDS),
                                validation, classification)
        splitter = (StratifiedGroupKFold(n_splits=n_folds, shuffle=True, random_state=seed)
                    if classification else GroupKFold(n_splits=n_folds))
        true_parts, pred_parts = [], []
        for k, (tr, te) in enumerate(splitter.split(X, y, groups), start=1):
            model = new_model()
            model.fit(X[tr], y[tr])
            pred = model.predict(X[te])
            permutation.add(model, X[te], y[te])
            true_parts.append(y[te])
            pred_parts.append(pred)
            score = (float((pred == y[te]).mean()) if classification else float(r2_score(y[te], pred)))
            fold_scores.append(score)
            report.append(('fold', 'fold_%d' % k, score))
        y_true, y_pred = np.concatenate(true_parts), np.concatenate(pred_parts)
        report.append(('training', 'folds', float(n_folds)))
        report.append(('training', 'groups', float(len(np.unique(groups)))))
        report.append(('training', 'test_rows', float(len(y_true))))
        report.append(('metric', 'fold_score_std', float(np.std(fold_scores))))

    matrix = _empty_matrix(classes) if classification else pd.DataFrame(
        {'metric': pd.Series(dtype='object'), 'value': pd.Series(dtype='float64')})
    if y_true is not None:
        if classification:
            matrix = _classification_report(y_true, y_pred, classes, report)
        else:
            rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
            r2 = float(r2_score(y_true, y_pred))
            mae = float(mean_absolute_error(y_true, y_pred))
            report += [('metric', 'r2', r2), ('metric', 'rmse', rmse), ('metric', 'mae', mae)]
            matrix = pd.DataFrame({'metric': ['r2', 'rmse', 'mae'], 'value': [r2, rmse, mae]})

    # El modelo final se reentrena con todos los datos
    model = new_model()
    model.fit(X, y)

    for name, value in sorted(zip(features, model.feature_importances_), key=lambda t: -t[1]):
        report.append(('importance', name, float(value)))
    report += permutation.rows()

    bundle = {
        'model': model,
        'features': features,
        'problem': problem,
        'classes': classes,
        'target': target,
    }
    return bundle, pd.DataFrame(report, columns=['section', 'name', 'value']), matrix


def summarize_report(report):
    """Texto legible del informe para el log de ejecución."""
    lines = []
    for section, title in (('metric', 'Metricas'), ('training', 'Entrenamiento'),
                           ('assessment', 'Evaluacion'), ('class_balance', 'Muestras por clase')):
        part = report[report['section'] == section]
        if len(part):
            lines.append('%s: ' % title + ', '.join('%s=%.4g' % (r['name'], r['value'])
                                                    for _, r in part.iterrows()))
    per_class = report[(report['section'] == 'per_class') & report['name'].str.endswith(':f1')]
    if len(per_class):
        worst = per_class.sort_values('value').iloc[0]
        lines.append('Clase peor clasificada: %s (F1=%.3f)' % (worst['name'][:-3], worst['value']))
    ci = report[report['section'] == 'ci']
    low, high = ci[ci['name'] == 'accuracy:low']['value'], ci[ci['name'] == 'accuracy:high']['value']
    if len(low) and len(high):
        lines.append('Exactitud global, intervalo del 95 %%: %.3f - %.3f' % (low.iloc[0], high.iloc[0]))
    imp = report[report['section'] == 'importance_permutation'].head(5)
    title = 'Variables mas importantes (permutacion)'
    if not len(imp):
        imp, title = report[report['section'] == 'importance'].head(5), 'Variables mas importantes (impureza)'
    if len(imp):
        lines.append(title + ': ' + ', '.join('%s=%.3f' % (r['name'], r['value']) for _, r in imp.iterrows()))
    return '\n'.join(lines)


# --------------------------------------------------------------------------
# Núcleo: predicción sobre ráster
# --------------------------------------------------------------------------

def load_model_bundle(path):
    """Carga el modelo de un artefacto del flujo (generado por este servidor) con mensajes claros si falla."""
    import joblib
    try:
        bundle = joblib.load(path)
    except Exception as e:
        raise Exception('No se ha podido cargar el modelo (%s). Si se guardó con otra versión de scikit-learn, '
                        'vuelve a entrenarlo.' % type(e).__name__)
    if not isinstance(bundle, dict) or not {'model', 'features', 'problem'} <= set(bundle):
        raise Exception('El fichero del modelo no tiene el formato esperado; vuelve a entrenarlo.')
    return bundle


def predict_arrays(model, X, classification, want_confidence=True):
    """
    Aplica el modelo a una matriz (n, variables) de valores válidos.
    Clasificación: devuelve (índice de clase en model.classes_, probabilidad de esa clase).
    Regresión: devuelve (valor estimado, desviación típica entre árboles o None si no se pide).
    """
    if classification:
        proba = model.predict_proba(X)
        best = proba.argmax(axis=1)
        return best, proba[np.arange(len(best)), best].astype('float32')
    if not want_confidence:
        return model.predict(X).astype('float32'), None
    # Una sola pasada por árbol: media (= predicción) y desviación típica
    X32 = X.astype('float32')
    total = np.zeros(len(X32), dtype='float64')
    total_sq = np.zeros(len(X32), dtype='float64')
    for tree in model.estimators_:
        p = tree.predict(X32)
        total += p
        total_sq += p * p
    n_trees = len(model.estimators_)
    mean = total / n_trees
    return mean.astype('float32'), np.sqrt(np.maximum(total_sq / n_trees - mean * mean, 0.0)).astype('float32')


def predict_raster_file(raster_path, bundle, out_path, block=PREDICT_BLOCK, confidence_path=None):
    """
    Aplica el modelo a todo el ráster por bloques.
    Clasificación: GeoTIFF uint16 con códigos 1..N (0 = sin dato); el mapa código→clase
    se devuelve (y se guarda en el .meta.json). Regresión: float32 con nodata REGRESSION_NODATA.

    confidence_path: si se indica, escribe además un GeoTIFF float32 (nodata REGRESSION_NODATA)
    con la confianza de cada píxel. Clasificación: probabilidad de la clase elegida (0-1, la
    fracción de árboles que la votan). Regresión: desviación típica entre árboles (incertidumbre,
    en las unidades de la variable). Se calcula en el mismo recorrido, sin leer el ráster dos veces.
    """
    import rasterio
    from rasterio.windows import Window

    features = bundle['features']
    model = bundle['model']
    classification = bundle['problem'] == 'classification'
    classes = bundle['classes'] or []
    code_of = {c: i + 1 for i, c in enumerate(classes)}
    if classification:
        # Código de ráster de cada clase del modelo, en el orden de predict_proba
        class_codes = np.array([code_of[_clean_class_label(c)] for c in model.classes_], dtype='uint16')

    with rasterio.open(raster_path) as src:
        meta = read_meta(raster_path)
        names = meta.get('band_names') or parse_band_names(None, src.count)
        if len(names) != src.count:
            names = parse_band_names(names, src.count)
        missing = [f for f in features if f not in names]
        if missing:
            raise ValueError('El ráster no tiene las bandas con las que se entrenó el modelo: %s. '
                             'Bandas del ráster: %s.' % (', '.join(missing), ', '.join(names)))
        idx = [names.index(f) for f in features]
        check_raster_size(src.width, src.height)
        check_free_space(src.width, src.height, 2 if confidence_path else 1, 4)

        profile = output_profile(src)
        profile.update(count=1, tiled=True, blockxsize=256, blockysize=256, compress='deflate')
        conf_profile = dict(profile, dtype='float32', nodata=REGRESSION_NODATA)
        if classification:
            profile.update(dtype='uint16', nodata=0)
        else:
            profile.update(dtype='float32', nodata=REGRESSION_NODATA)

        dst = rasterio.open(out_path, 'w', **profile)
        conf_dst = rasterio.open(confidence_path, 'w', **conf_profile) if confidence_path else None
        try:
            for row in range(0, src.height, block):
                for col in range(0, src.width, block):
                    window = Window(col, row, min(block, src.width - col), min(block, src.height - row))
                    arr = src.read(window=window, masked=True)  # (bandas, h, w)
                    invalid = np.ma.getmaskarray(arr).any(axis=0)
                    values = np.ma.getdata(arr).astype('float64')
                    invalid |= ~np.isfinite(values).all(axis=0)
                    h, w = invalid.shape
                    flat = values[idx, :, :].reshape(len(idx), -1).T
                    valid_flat = ~invalid.reshape(-1)
                    if classification:
                        out = np.zeros(h * w, dtype='uint16')
                    else:
                        out = np.full(h * w, REGRESSION_NODATA, dtype='float32')
                    conf = np.full(h * w, REGRESSION_NODATA, dtype='float32')
                    if valid_flat.any():
                        values, confidence = predict_arrays(model, flat[valid_flat], classification,
                                                            want_confidence=conf_dst is not None)
                        out[valid_flat] = class_codes[values] if classification else values
                        if confidence is not None:
                            conf[valid_flat] = confidence
                    dst.write(out.reshape(h, w), 1, window=window)
                    if conf_dst is not None:
                        conf_dst.write(conf.reshape(h, w), 1, window=window)
        finally:
            dst.close()
            if conf_dst is not None:
                conf_dst.close()

    class_map = {str(code_of[c]): str(c) for c in classes} if classification else {}
    write_meta(out_path, {'problem': bundle['problem'], 'class_map': class_map,
                          'features': features, 'source': os.path.basename(raster_path)})
    if confidence_path:
        write_meta(confidence_path, {'kind': 'confidence' if classification else 'uncertainty',
                                     'source': os.path.basename(raster_path)})
    return class_map


# --------------------------------------------------------------------------
# Núcleo: recortar un ráster con una máscara vectorial
# --------------------------------------------------------------------------

CLIP_MODES = ('polygon', 'bbox')
CLIP_RESAMPLING = ('average', 'bilinear', 'nearest')


def _default_nodata(dtype):
    """Valor de sin dato para un ráster que no lo declara: 0 en enteros sin signo (lo habitual en ortofotos)."""
    kind = np.dtype(dtype).kind
    if kind == 'u':
        return 0
    if kind == 'i':
        return int(np.iinfo(dtype).min)
    return REGRESSION_NODATA


def clip_raster_file(raster_path, geometries, out_path, mode='polygon', pixel_size=None,
                     resampling='average', block=PREDICT_BLOCK):
    """
    Recorta un ráster con polígonos (en el sistema de coordenadas del ráster).

    mode: 'polygon' deja sin dato lo que queda fuera de los polígonos; 'bbox' solo recorta a su rectángulo.
    pixel_size: tamaño de píxel del resultado en unidades del sistema de coordenadas (None = el del original,
    con la malla alineada a sus píxeles). Con otro tamaño se remuestrea con `resampling`, salvo en un ráster
    clasificado, que siempre usa vecino más próximo para no mezclar clases.
    Conserva el tipo de dato y el número de bandas (una ortofoto de 8 bits sigue siendo de 8 bits).
    Devuelve (ancho, alto, píxeles dentro de la máscara, si se ha añadido un valor de sin dato).
    """
    import math
    import rasterio
    from affine import Affine
    from rasterio.enums import Resampling
    from rasterio.features import geometry_mask
    from rasterio.windows import Window, from_bounds
    from shapely.ops import unary_union

    if mode not in CLIP_MODES:
        raise ValueError('Modo de recorte desconocido: %s.' % mode)
    if resampling not in CLIP_RESAMPLING:
        raise ValueError('Método de remuestreo desconocido: %s.' % resampling)
    if pixel_size is not None and not pixel_size > 0:
        raise ValueError('El tamaño de píxel debe ser mayor que 0.')
    geometries = [g for g in geometries if g is not None and not g.is_empty]
    if not geometries:
        raise ValueError('La máscara no tiene ningún polígono.')
    union = unary_union(geometries)

    classified = bool(read_meta(raster_path).get('class_map'))
    method = Resampling.nearest if classified else {
        'average': Resampling.average, 'bilinear': Resampling.bilinear, 'nearest': Resampling.nearest}[resampling]

    with rasterio.open(raster_path) as src:
        if src.crs is None:
            raise ValueError('El ráster no tiene sistema de coordenadas.')
        check_raster_size(src.width, src.height)
        left, bottom, right, top = src.bounds
        bx0, by0, bx1, by1 = union.bounds
        x0, y0, x1, y1 = max(bx0, left), max(by0, bottom), min(bx1, right), min(by1, top)
        if x0 >= x1 or y0 >= y1:
            raise ValueError('La máscara no se solapa con el ráster. Revisa que estén en la misma zona '
                             'y que la máscara tenga sistema de coordenadas.')

        if pixel_size is None:
            win = from_bounds(x0, y0, x1, y1, transform=src.transform)
            col0, row0 = max(0, int(math.floor(win.col_off + 1e-6))), max(0, int(math.floor(win.row_off + 1e-6)))
            col1 = min(src.width, int(math.ceil(win.col_off + win.width - 1e-6)))
            row1 = min(src.height, int(math.ceil(win.row_off + win.height - 1e-6)))
            out_w, out_h = col1 - col0, row1 - row0
            out_transform = src.window_transform(Window(col0, row0, out_w, out_h))
        else:
            ps = float(pixel_size)
            origin_x, origin_y = math.floor(x0 / ps) * ps, math.ceil(y1 / ps) * ps
            out_w, out_h = int(math.ceil((x1 - origin_x) / ps - 1e-9)), int(math.ceil((origin_y - y0) / ps - 1e-9))
            out_transform = Affine(ps, 0, origin_x, 0, -ps, origin_y)
        if out_w < 1 or out_h < 1:
            raise ValueError('La zona de recorte es más pequeña que un píxel.')
        check_raster_size(out_w, out_h, 'El resultado del recorte')
        check_free_space(out_w, out_h, src.count, np.dtype(src.dtypes[0]).itemsize)

        nodata = src.nodata
        added_nodata = False
        if nodata is None and (mode == 'polygon' or pixel_size is not None):
            nodata = _default_nodata(src.dtypes[0])
            added_nodata = True
        profile = output_profile(src)
        profile.update(width=out_w, height=out_h, transform=out_transform, nodata=nodata,
                       tiled=True, blockxsize=256, blockysize=256, compress='deflate')
        inside_pixels = 0
        with rasterio.open(out_path, 'w', **profile) as dst:
            for row in range(0, out_h, block):
                for col in range(0, out_w, block):
                    bw, bh = min(block, out_w - col), min(block, out_h - row)
                    window = Window(col, row, bw, bh)
                    block_transform = rasterio.windows.transform(window, out_transform)
                    if pixel_size is None:
                        data = src.read(window=Window(col0 + col, row0 + row, bw, bh), masked=True)
                    else:
                        b = rasterio.windows.bounds(window, out_transform)
                        data = src.read(window=from_bounds(*b, transform=src.transform), out_shape=(src.count, bh, bw),
                                        resampling=method, boundless=True, masked=True)
                    values = np.ma.getdata(data)
                    invalid = np.ma.getmaskarray(data)
                    if mode == 'polygon':
                        outside = geometry_mask([union], out_shape=(bh, bw), transform=block_transform, all_touched=False)
                        inside_pixels += int((~outside).sum())
                        invalid = invalid | outside[None, :, :]
                    else:
                        inside_pixels += bh * bw
                    if nodata is not None:
                        values = np.where(invalid, np.asarray(nodata, dtype=values.dtype), values)
                    dst.write(values, window=window)
    if inside_pixels == 0:
        os.remove(out_path)
        raise ValueError('La máscara es más pequeña que un píxel del ráster: no queda ningún píxel dentro. '
                         'Usa el modo "solo el rectángulo" o un polígono mayor.')
    meta = dict(read_meta(raster_path))
    if pixel_size is not None:
        meta['pixel_size'] = float(pixel_size)
    write_meta(out_path, meta)
    return out_w, out_h, inside_pixels, added_nodata


# --------------------------------------------------------------------------
# Núcleo: extraer una banda
# --------------------------------------------------------------------------

def extract_band(raster_path, band, out_path, block=PREDICT_BLOCK):
    """
    Copia una banda (por su nombre o por su número, desde 1) a un GeoTIFF de una banda, con el mismo
    tipo, sin dato y georreferenciación. Se conservan las clases del ráster si las tiene.
    """
    import rasterio
    from rasterio.windows import Window

    with rasterio.open(raster_path) as src:
        names = read_meta(raster_path).get('band_names') or parse_band_names(None, src.count)
        if len(names) != src.count:
            names = parse_band_names(names, src.count)
        text = str(band).strip()
        if text in names:
            index = names.index(text) + 1
        elif text.isdigit() and 1 <= int(text) <= src.count:
            index = int(text)
        else:
            raise ValueError('El ráster no tiene la banda "%s". Bandas: %s.' % (band, ', '.join(names)))
        check_raster_size(src.width, src.height)
        check_free_space(src.width, src.height, 1, np.dtype(src.dtypes[index - 1]).itemsize)
        profile = output_profile(src)
        profile.update(count=1, tiled=True, blockxsize=256, blockysize=256, compress='deflate')
        with rasterio.open(out_path, 'w', **profile) as dst:
            for row in range(0, src.height, block):
                for col in range(0, src.width, block):
                    window = Window(col, row, min(block, src.width - col), min(block, src.height - row))
                    dst.write(src.read(index, window=window), 1, window=window)
    meta = dict(read_meta(raster_path))
    meta['band_names'] = [names[index - 1]]
    write_meta(out_path, meta)


# --------------------------------------------------------------------------
# Núcleo: aplicar un modelo a una tabla
# --------------------------------------------------------------------------

TABLE_PREDICT_CHUNK = 200000


def predict_dataframe(df, bundle, chunk=TABLE_PREDICT_CHUNK):
    """
    Aplica el modelo a las filas de una tabla. Devuelve (predicción, confianza) como arrays
    de la longitud de df: las filas con alguna variable nula, no numérica o infinita no se
    predicen (None / NaN). Confianza: probabilidad de la clase elegida o, en regresión, la
    desviación típica entre árboles.
    """
    features = bundle['features']
    missing = [f for f in features if f not in df.columns]
    if missing:
        raise ValueError('La tabla no tiene las columnas con las que se entrenó el modelo: %s. Columnas de la tabla: %s.'
                         % (', '.join(missing), ', '.join(str(c) for c in df.columns)))
    classification = bundle['problem'] == 'classification'
    model = bundle['model']
    labels = [_clean_class_label(c) for c in model.classes_] if classification else None

    values = df[features].apply(pd.to_numeric, errors='coerce').replace([np.inf, -np.inf], np.nan)
    valid = values.notna().all(axis=1).to_numpy()
    predicted = np.full(len(df), None, dtype=object) if classification else np.full(len(df), np.nan)
    confidence = np.full(len(df), np.nan)
    positions = np.flatnonzero(valid)
    matrix = values.to_numpy(dtype='float64')
    for start in range(0, len(positions), chunk):
        part = positions[start:start + chunk]
        result, conf = predict_arrays(model, matrix[part], classification)
        predicted[part] = [labels[i] for i in result] if classification else result
        confidence[part] = conf
    return predicted, confidence


# --------------------------------------------------------------------------
# Núcleo: combinar varios ráster en uno
# --------------------------------------------------------------------------

STACK_RESAMPLING = ('nearest', 'bilinear')
STACK_MAX_INPUTS = 4


def stack_rasters(paths, out_path, band_names, prefixes=None, resampling='bilinear', block=PREDICT_BLOCK):
    """
    Combina varios ráster en un GeoTIFF multibanda alineado con el PRIMERO (su sistema de
    coordenadas, extensión y tamaño de píxel). Los demás se reproyectan y remuestrean al vuelo.

    band_names: lista con los nombres de banda de cada ráster. prefixes: prefijo opcional de cada uno
    (evita colisiones de nombres). Resultado: float32, sin dato = REGRESSION_NODATA. Donde algún
    ráster no tiene cobertura, sus bandas quedan sin dato. Devuelve los nombres de banda finales.
    """
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.vrt import WarpedVRT
    from rasterio.warp import transform_bounds
    from rasterio.windows import Window

    if len(paths) < 2:
        raise ValueError('Conecta al menos dos ráster para combinarlos.')
    if len(paths) > STACK_MAX_INPUTS:
        raise ValueError('Se pueden combinar como máximo %d ráster.' % STACK_MAX_INPUTS)
    if resampling not in STACK_RESAMPLING:
        raise ValueError('Método de remuestreo desconocido: %s.' % resampling)
    method = Resampling.nearest if resampling == 'nearest' else Resampling.bilinear
    prefixes = list(prefixes or []) + [''] * len(paths)

    sources, vrts, labels = [], [], []
    try:
        for path in paths:
            sources.append(rasterio.open(path))
        ref = sources[0]
        if ref.crs is None:
            raise ValueError('El primer ráster (el de referencia) no tiene sistema de coordenadas.')
        check_raster_size(ref.width, ref.height, 'El ráster de referencia')
        total = sum(src.count for src in sources)
        check_free_space(ref.width, ref.height, total, 4)

        for i, src in enumerate(sources):
            names = band_names[i] if i < len(band_names) and band_names[i] else parse_band_names(None, src.count)
            if len(names) != src.count:
                names = parse_band_names(names, src.count)
            prefix = str(prefixes[i] or '').strip()
            labels += [('%s_%s' % (prefix, n)) if prefix else n for n in names]
            if i == 0:
                vrts.append(src)
                continue
            if src.crs is None:
                raise ValueError('El ráster %d no tiene sistema de coordenadas.' % (i + 1))
            left, bottom, right, top = transform_bounds(src.crs, ref.crs, *src.bounds)
            r = ref.bounds
            if left >= r.right or right <= r.left or bottom >= r.top or top <= r.bottom:
                raise ValueError('El ráster %d no se solapa con el ráster de referencia (el primero).' % (i + 1))
            same_grid = (src.crs == ref.crs and src.transform.almost_equals(ref.transform)
                         and src.width == ref.width and src.height == ref.height)
            if same_grid:
                vrts.append(src)
            else:
                vrts.append(WarpedVRT(src, crs=ref.crs, transform=ref.transform, width=ref.width,
                                      height=ref.height, resampling=method, nodata=REGRESSION_NODATA,
                                      src_nodata=src.nodata))
        out_names = parse_band_names(labels, total)

        profile = output_profile(ref)
        profile.update(count=total, dtype='float32', nodata=REGRESSION_NODATA,
                       tiled=True, blockxsize=256, blockysize=256, compress='deflate')
        with rasterio.open(out_path, 'w', **profile) as dst:
            for row in range(0, ref.height, block):
                for col in range(0, ref.width, block):
                    window = Window(col, row, min(block, ref.width - col), min(block, ref.height - row))
                    parts = []
                    for vrt in vrts:
                        arr = vrt.read(window=window, masked=True)
                        data = np.ma.getdata(arr).astype('float32')
                        bad = np.ma.getmaskarray(arr) | ~np.isfinite(data)
                        parts.append(np.where(bad, REGRESSION_NODATA, data).astype('float32'))
                    dst.write(np.concatenate(parts, axis=0), window=window)
    finally:
        for v in vrts[1:]:
            if v not in sources:
                v.close()
        for src in sources:
            src.close()
    return out_names


# --------------------------------------------------------------------------
# Núcleo: filtro de mayoría sobre un ráster clasificado
# --------------------------------------------------------------------------

def _majority_step(a, size):
    """
    Un paso del filtro de mayoría sobre una matriz de códigos (0 = sin dato): cada píxel
    toma la clase más frecuente de su ventana size x size, sin contar el sin dato. En empate
    se conserva su propia clase si es una de las más frecuentes. El sin dato no se rellena.
    """
    from scipy.ndimage import uniform_filter

    area = float(size * size)
    best_count = np.zeros(a.shape, dtype='float32')
    best_code = np.zeros(a.shape, dtype=a.dtype)
    own_count = np.zeros(a.shape, dtype='float32')
    for code in np.unique(a):
        if code == 0:
            continue
        mask = a == code
        counts = np.rint(uniform_filter(mask.astype('float32'), size=size, mode='constant', cval=0.0) * area)
        own_count = np.where(mask, counts, own_count)
        better = counts > best_count
        best_code = np.where(better, code, best_code)
        best_count = np.where(better, counts, best_count)
    result = np.where(own_count >= best_count, a, best_code).astype(a.dtype)
    result[a == 0] = 0
    return result


def majority_filter_file(raster_path, out_path, size=3, iterations=1, block=PREDICT_BLOCK):
    """
    Aplica el filtro de mayoría a un ráster clasificado, por bloques con un margen igual al
    alcance del filtro para que el resultado no dependa del tamaño del bloque.
    """
    import rasterio
    from rasterio.windows import Window

    if size not in MAJORITY_WINDOWS:
        raise ValueError('La ventana debe ser 3, 5 o 7 píxeles.')
    if not 1 <= iterations <= MAX_ITERATIONS:
        raise ValueError('Las repeticiones deben estar entre 1 y %d.' % MAX_ITERATIONS)
    halo = (size // 2) * iterations

    with rasterio.open(raster_path) as src:
        if src.count != 1:
            raise ValueError('El filtro de mayoría necesita un ráster clasificado de una banda.')
        check_raster_size(src.width, src.height)
        check_free_space(src.width, src.height, 1, 2)
        profile = output_profile(src)
        profile.update(tiled=True, blockxsize=256, blockysize=256, compress='deflate')
        with rasterio.open(out_path, 'w', **profile) as dst:
            for row in range(0, src.height, block):
                for col in range(0, src.width, block):
                    h, w = min(block, src.height - row), min(block, src.width - col)
                    r0, c0 = max(0, row - halo), max(0, col - halo)
                    r1, c1 = min(src.height, row + h + halo), min(src.width, col + w + halo)
                    a = src.read(1, window=Window(c0, r0, c1 - c0, r1 - r0))
                    for _ in range(iterations):
                        a = _majority_step(a, size)
                    dst.write(a[row - r0:row - r0 + h, col - c0:col - c0 + w], 1,
                              window=Window(col, row, w, h))


def sieve_file(raster_path, out_path, min_pixels, connectivity=4):
    """Elimina los parches de menos de min_pixels píxeles (los absorbe el vecino mayor)."""
    import rasterio
    from rasterio.features import sieve

    if min_pixels < 2:
        raise ValueError('El tamaño mínimo del parche debe ser de al menos 2 píxeles.')
    if connectivity not in (4, 8):
        raise ValueError('La conectividad debe ser 4 u 8.')
    with rasterio.open(raster_path) as src:
        if src.count != 1:
            raise ValueError('El filtro necesita un ráster clasificado de una banda.')
        check_raster_size(src.width, src.height)
        sieve_max = _limit('ETL_RASTER_SIEVE_MAX_PIXELS', MAX_SIEVE_PIXELS)
        if sieve_max > 0 and src.width * src.height > sieve_max:
            raise ValueError('El ráster es demasiado grande para el modo "tamaño mínimo de parche" '
                             '(%d píxeles, máximo %d). Usa el filtro de mayoría, que trabaja por bloques.'
                             % (src.width * src.height, sieve_max))
        check_free_space(src.width, src.height, 1, 2)
        a = src.read(1)
        cleaned = sieve(a, min_pixels, connectivity=connectivity, mask=(a != 0))
        profile = output_profile(src)
        profile.update(tiled=True, blockxsize=256, blockysize=256, compress='deflate')
        with rasterio.open(out_path, 'w', **profile) as dst:
            dst.write(cleaned.astype(a.dtype), 1)


# --------------------------------------------------------------------------
# Núcleo: índices espectrales
# --------------------------------------------------------------------------

def _normalized_difference(a, b):
    with np.errstate(divide='ignore', invalid='ignore'):
        return (a - b) / (a + b)


def compute_index(index, bands, scale=1.0, savi_l=DEFAULT_SAVI_L):
    """
    Calcula un índice con matrices float64 (ya divididas por la escala de reflectancia).
    bands: dict papel -> matriz, o lista de todas las matrices si es 'brightness'.
    """
    with np.errstate(divide='ignore', invalid='ignore'):
        if index == 'ndvi':
            return _normalized_difference(bands['nir'], bands['red'])
        if index == 'ndwi':
            return _normalized_difference(bands['green'], bands['nir'])
        if index == 'ndbi':
            return _normalized_difference(bands['swir'], bands['nir'])
        if index == 'nd':
            return _normalized_difference(bands['a'], bands['b'])
        if index == 'savi':
            nir, red = bands['nir'], bands['red']
            return (1.0 + savi_l) * (nir - red) / (nir + red + savi_l)
        if index == 'evi':
            nir, red, blue = bands['nir'], bands['red'], bands['blue']
            return 2.5 * (nir - red) / (nir + 6.0 * red - 7.5 * blue + 1.0)
        if index == 'brightness':
            return np.mean(bands['all'], axis=0)
    raise ValueError('Índice desconocido: %s.' % index)


def reflectance_conversion(params):
    """(escala, offset) a partir del preset 'reflectance' o de los campos 'scale' y 'offset' (personalizado)."""
    preset = (params.get('reflectance') or 'custom').strip()
    if preset in REFLECTANCE_PRESETS:
        return REFLECTANCE_PRESETS[preset]
    if preset != 'custom':
        raise ValueError('Conversión a reflectancia desconocida: %s.' % preset)
    return _to_float(params.get('scale'), 1.0), _to_float(params.get('offset'), 0.0)


def add_index_file(raster_path, out_path, index, band_names, selected, output_name=None,
                   scale=1.0, savi_l=DEFAULT_SAVI_L, block=PREDICT_BLOCK, offset=0.0):
    """
    Escribe un ráster float32 con las bandas del original más una banda con el índice.

    selected: nombres de las bandas, en el orden de INDEX_DEFS[index]['roles'].
    scale, offset: conversión a reflectancia, reflectancia = (valor + offset) / scale, que se aplica a
    todas las bandas antes de calcular el índice (ver REFLECTANCE_PRESETS). Con offset 0 los índices
    normalizados no cambian con la escala; SAVI y EVI sí la necesitan porque mezclan constantes.
    EVI: los valores fuera de [-1, 1] (rango físico) se marcan como sin dato.
    Devuelve los nombres de banda del ráster resultante.
    """
    import rasterio
    from rasterio.windows import Window

    if index not in INDEX_DEFS:
        raise ValueError('Índice desconocido: %s.' % index)
    roles = INDEX_DEFS[index]['roles']
    if len(selected) < len(roles) or any(not x for x in selected[:len(roles)]):
        raise ValueError('Indica la banda de cada papel del índice (%s).' % ', '.join(roles))
    if not scale or scale <= 0:
        raise ValueError('La escala de reflectancia debe ser mayor que 0.')
    missing = [x for x in selected[:len(roles)] if x not in band_names]
    if missing:
        raise ValueError('El ráster no tiene las bandas: %s. Bandas del ráster: %s.'
                         % (', '.join(missing), ', '.join(band_names)))
    idx = {role: band_names.index(name) for role, name in zip(roles, selected)}
    out_names = parse_band_names(list(band_names) + [output_name or index], len(band_names) + 1)

    with rasterio.open(raster_path) as src:
        if src.count != len(band_names):
            raise ValueError('El número de nombres de banda no coincide con el del ráster.')
        check_raster_size(src.width, src.height)
        check_free_space(src.width, src.height, src.count + 1, 4)
        profile = output_profile(src)
        profile.update(count=src.count + 1, dtype='float32', nodata=REGRESSION_NODATA,
                       tiled=True, blockxsize=256, blockysize=256, compress='deflate')
        with rasterio.open(out_path, 'w', **profile) as dst:
            for row in range(0, src.height, block):
                for col in range(0, src.width, block):
                    window = Window(col, row, min(block, src.width - col), min(block, src.height - row))
                    arr = src.read(window=window, masked=True)
                    raw = np.ma.getdata(arr).astype('float64')
                    bad = np.ma.getmaskarray(arr) | ~np.isfinite(raw)
                    values = (raw + offset) / scale
                    if index == 'brightness':
                        used = {'all': values}
                        invalid = bad.any(axis=0)
                    else:
                        used = {role: values[i] for role, i in idx.items()}
                        invalid = np.any([bad[i] for i in idx.values()], axis=0)
                    result = compute_index(index, used, savi_l=savi_l)
                    invalid |= ~np.isfinite(result)
                    if index in INDEX_VALID_RANGE:
                        lo, hi = INDEX_VALID_RANGE[index]
                        with np.errstate(invalid='ignore'):
                            invalid |= (result < lo) | (result > hi)
                    new = np.where(invalid, REGRESSION_NODATA, result).astype('float32')
                    original = np.where(bad, REGRESSION_NODATA, raw).astype('float32')
                    dst.write(np.concatenate([original, new[None, :, :]], axis=0), window=window)

    return out_names


# --------------------------------------------------------------------------
# Núcleo: evaluación de una clasificación con muestras independientes
# --------------------------------------------------------------------------

BOOTSTRAP_REPLICATES = 1000


def cluster_bootstrap_ci(y_true, y_pred, units, labels, replicates=BOOTSTRAP_REPLICATES, level=0.95, seed=DEFAULT_SEED):
    """
    Intervalos de confianza de la exactitud global y de la precisión y el recall de cada clase, por bootstrap
    de UNIDADES de muestreo: se remuestrean muestras enteras (cada polígono o cada punto), no píxeles, porque
    los píxeles de un mismo polígono no son independientes. Supone que las unidades se eligieron al azar.
    Devuelve filas (section, name, value) en la sección 'ci'; vacía si hay menos de 2 unidades.
    """
    ids, unit_index = np.unique(units, return_inverse=True)
    n_units, k = len(ids), len(labels)
    rows = [('assessment', 'sample_units', float(n_units))]
    if n_units < 2:
        return rows
    position = {label: i for i, label in enumerate(labels)}
    t = np.array([position[v] for v in y_true])
    p = np.array([position[v] for v in y_pred])
    per_unit = np.zeros((n_units, k * k))
    np.add.at(per_unit, (unit_index, t * k + p), 1)
    rng = np.random.RandomState(seed)
    draws = rng.randint(0, n_units, (replicates, n_units))
    weights = np.zeros((replicates, n_units), dtype='float32')
    for b in range(replicates):
        weights[b] = np.bincount(draws[b], minlength=n_units)
    matrices = (weights @ per_unit).reshape(replicates, k, k)          # filas: real, columnas: predicho
    lo_q, hi_q = 100 * (1 - level) / 2, 100 * (1 - (1 - level) / 2)
    diag = np.einsum('bii->bi', matrices)
    with np.errstate(invalid='ignore', divide='ignore'):
        accuracy = diag.sum(axis=1) / matrices.sum(axis=(1, 2))
        precision = diag / matrices.sum(axis=1)
        recall = diag / matrices.sum(axis=2)
    rows += [('assessment', 'bootstrap_replicates', float(replicates)),
             ('ci', 'accuracy:low', float(np.nanpercentile(accuracy, lo_q))),
             ('ci', 'accuracy:high', float(np.nanpercentile(accuracy, hi_q)))]
    for i, label in enumerate(labels):
        for name, values in (('precision', precision[:, i]), ('recall', recall[:, i])):
            if np.isfinite(values).any():
                rows.append(('ci', '%s:%s:low' % (label, name), float(np.nanpercentile(values, lo_q))))
                rows.append(('ci', '%s:%s:high' % (label, name), float(np.nanpercentile(values, hi_q))))
    return rows


def assess_classification(raster_path, gdf, class_attr):
    """
    Compara un ráster clasificado (salida de Predecir ráster) con muestras de validación
    independientes: polígonos (todos sus píxeles) o puntos (el píxel que los contiene).

    Devuelve (report, matrix): el informe en formato largo (section, name, value) con exactitud,
    kappa, métricas por clase (precision = exactitud del usuario, recall = exactitud del productor)
    y matriz, y la matriz de confusión en tabla ancha. Los píxeles sin clasificar (código 0) no
    cuentan en las métricas pero se informan.
    """
    import rasterio
    from rasterio.mask import raster_geometry_mask

    class_map = read_meta(raster_path).get('class_map')
    if not class_map:
        raise ValueError('El ráster no es una clasificación: evalúa la salida de "Predecir ráster" '
                         '(o de "Limpiar ráster") de un modelo de clasificación.')
    if class_attr not in gdf.columns:
        raise ValueError('La tabla de validación no tiene la columna de clase "%s".' % class_attr)

    true_labels, pred_labels, units = [], [], []      # units: muestra (polígono o punto) de cada píxel
    unclassified = ignored = outside = 0
    unit = 0
    with rasterio.open(raster_path) as src:
        check_raster_size(src.width, src.height)
        if src.crs is None:
            raise ValueError('El ráster no tiene sistema de coordenadas.')
        if gdf.crs is None:
            raise ValueError('La tabla de validación no tiene sistema de coordenadas.')
        samples = gdf.to_crs(src.crs)
        for geom, label in zip(samples.geometry, samples[class_attr]):
            if geom is None or geom.is_empty or label is None or (isinstance(label, float) and np.isnan(label)):
                ignored += 1
                continue
            label = str(_clean_class_label(label))
            if geom.geom_type in ('Point', 'MultiPoint'):
                points = [geom] if geom.geom_type == 'Point' else list(geom.geoms)
                left, bottom, right, top = src.bounds
                inside = [p for p in points if left <= p.x < right and bottom < p.y <= top]
                outside += len(points) - len(inside)
                # Sin enmascarar: el nodata del ráster es "sin clasificar" (código 0), no "fuera"
                codes = np.array([v[0] for v in src.sample([(p.x, p.y) for p in inside])], dtype='int64')
                # Cada punto es una unidad de muestreo propia
                for code in codes:
                    unit += 1
                    if code == 0:
                        unclassified += 1
                        continue
                    name = class_map.get(str(int(code)))
                    if name is not None:
                        true_labels.append(label)
                        pred_labels.append(name)
                        units.append(unit)
                continue
            elif geom.geom_type in ('Polygon', 'MultiPolygon'):
                try:
                    geom_mask, _, window = raster_geometry_mask(src, [geom], crop=True)
                except ValueError:
                    outside += 1
                    continue
                codes = src.read(1, window=window)[~geom_mask]
            else:
                ignored += 1
                continue
            if codes.size == 0:
                continue
            unit += 1                                     # todos los píxeles de un polígono son la misma unidad
            unclassified += int((codes == 0).sum())
            codes = codes[codes != 0]
            for code in np.unique(codes):
                name = class_map.get(str(int(code)))
                if name is None:
                    continue
                count = int((codes == code).sum())
                true_labels.extend([label] * count)
                pred_labels.extend([name] * count)
                units.extend([unit] * count)

    if not true_labels:
        raise ValueError('Ninguna muestra de validación cae sobre píxeles clasificados del ráster. '
                         'Revisa que se solapen y que tengan el mismo sistema de coordenadas.')

    y_true, y_pred = np.array(true_labels, dtype=object), np.array(pred_labels, dtype=object)
    labels = sorted(set(true_labels) | set(pred_labels))
    report = [('assessment', 'validation_pixels', float(len(y_true))),
              ('assessment', 'unclassified_pixels', float(unclassified)),
              ('assessment', 'ignored_samples', float(ignored)),
              ('assessment', 'samples_outside_raster', float(outside))]
    unknown = sorted(set(true_labels) - set(class_map.values()))
    if unknown:
        report.append(('assessment', 'classes_not_in_model', float(len(unknown))))
    for label in labels:
        report.append(('class_balance', label, float((y_true == label).sum())))
    matrix = _classification_report(y_true, y_pred, labels, report)
    report += cluster_bootstrap_ci(y_true, y_pred, np.asarray(units), labels)
    return pd.DataFrame(report, columns=['section', 'name', 'value']), matrix, unknown


# --------------------------------------------------------------------------
# Núcleo: muestreo estratificado y estimación de superficies con intervalo de confianza
# (Olofsson et al., 2014, "Good practices for estimating area and assessing accuracy of land change")
# --------------------------------------------------------------------------

DEFAULT_SAMPLES_PER_CLASS = 50
CONFIDENCE_Z = {'0.90': 1.6449, '0.95': 1.96, '0.99': 2.5758}


def stratified_sample_points(raster_path, per_class=DEFAULT_SAMPLES_PER_CLASS, seed=DEFAULT_SEED, block=PREDICT_BLOCK):
    """
    Muestra aleatoria estratificada por clase del mapa: `per_class` píxeles al azar de cada clase (todos si hay
    menos), con la misma probabilidad para todos los píxeles de la clase. Recorre el ráster por bloques
    (muestreo por reserva), así que no lo carga entero. Devuelve [(código, x, y)] con el centro de cada píxel.
    """
    import rasterio
    from rasterio.windows import Window

    if per_class < 2:
        raise ValueError('Hacen falta al menos 2 muestras por clase (se recomiendan 50 o más).')
    class_map = read_meta(raster_path).get('class_map')
    if not class_map:
        raise ValueError('El muestreo estratificado necesita un ráster clasificado (salida de "Predecir ráster" o "Limpiar ráster").')
    rng = np.random.RandomState(seed)
    keep = {}                                           # código -> (claves aleatorias, filas, columnas)
    with rasterio.open(raster_path) as src:
        check_raster_size(src.width, src.height)
        transform = src.transform
        for row in range(0, src.height, block):
            for col in range(0, src.width, block):
                window = Window(col, row, min(block, src.width - col), min(block, src.height - row))
                band = src.read(1, window=window)
                for code in np.unique(band):
                    if code == 0 or str(int(code)) not in class_map:
                        continue
                    rr, cc = np.nonzero(band == code)
                    keys = rng.random_sample(len(rr))
                    old = keep.get(int(code))
                    if old is not None:
                        keys, rr, cc = np.r_[old[0], keys], np.r_[old[1], rr + row], np.r_[old[2], cc + col]
                    else:
                        rr, cc = rr + row, cc + col
                    if len(keys) > per_class:
                        best = np.argpartition(keys, per_class - 1)[:per_class]
                        keys, rr, cc = keys[best], rr[best], cc[best]
                    keep[int(code)] = (keys, rr, cc)
    points = []
    for code in sorted(keep):
        keys, rr, cc = keep[code]
        order = np.argsort(keys)
        for r, c in zip(rr[order], cc[order]):
            x, y = transform * (c + 0.5, r + 0.5)
            points.append((code, float(x), float(y)))
    return points


def map_class_areas(raster_path, block=PREDICT_BLOCK):
    """Píxeles de cada clase del mapa y superficie de un píxel (en unidades del sistema de coordenadas al cuadrado)."""
    import rasterio
    from rasterio.windows import Window
    class_map = read_meta(raster_path).get('class_map')
    if not class_map:
        raise ValueError('La estimación de superficies necesita un ráster clasificado (salida de "Predecir ráster" o "Limpiar ráster").')
    counts = {}
    with rasterio.open(raster_path) as src:
        if src.crs is None:
            raise ValueError('El ráster no tiene sistema de coordenadas.')
        if src.crs.is_geographic:
            raise ValueError('El ráster está en coordenadas geográficas (grados): reproyéctalo a un sistema proyectado '
                             '(por ejemplo UTM) para que las superficies salgan en metros cuadrados.')
        check_raster_size(src.width, src.height)
        t = src.transform
        pixel_area = abs(t.a * t.e - t.b * t.d)
        for row in range(0, src.height, block):
            for col in range(0, src.width, block):
                band = src.read(1, window=Window(col, row, min(block, src.width - col), min(block, src.height - row)))
                values, n = np.unique(band, return_counts=True)
                for v, k in zip(values, n):
                    if v != 0 and str(int(v)) in class_map:
                        counts[class_map[str(int(v))]] = counts.get(class_map[str(int(v))], 0) + int(k)
    return counts, pixel_area


def estimate_areas(map_pixels, pixel_area, samples, z=1.96):
    """
    Estimador estratificado de superficies y exactitudes (Olofsson et al., 2014, ecuaciones 2-10).

    map_pixels: {clase del mapa: píxeles}; samples: [(clase del mapa, clase real)] de una muestra aleatoria
    estratificada por clase del mapa. Devuelve (filas por clase, resumen). Las superficies van en las unidades
    de pixel_area; los intervalos son ± z * error típico.
    """
    strata = [c for c in sorted(map_pixels) if map_pixels[c] > 0]
    if not strata:
        raise ValueError('El mapa no tiene píxeles clasificados.')
    n_i = {c: sum(1 for m, _ in samples if m == c) for c in strata}
    few = [c for c in strata if n_i[c] < 2]
    if few:
        raise ValueError('Hacen falta al menos 2 muestras de referencia en cada clase del mapa (se recomiendan 50); '
                         'tienen menos: %s. Genera las muestras con "Muestreo estratificado".' % ', '.join(few))
    categories = sorted(set(strata) | {r for _, r in samples})
    total_pixels = float(sum(map_pixels[c] for c in strata))
    total_area = total_pixels * pixel_area
    W = {c: map_pixels[c] / total_pixels for c in strata}
    n = {(i, j): 0 for i in strata for j in categories}
    for m, r in samples:
        if m in W:
            n[(m, r)] += 1
    q = {(i, j): n[(i, j)] / float(n_i[i]) for i in strata for j in categories}     # proporción dentro del estrato
    p = {(i, j): W[i] * q[(i, j)] for i in strata for j in categories}              # proporción de superficie

    rows = []
    overall = sum(p[(c, c)] for c in strata if c in categories)
    var_overall = sum(W[i] ** 2 * q[(i, i)] * (1 - q[(i, i)]) / (n_i[i] - 1) for i in strata)
    for j in categories:
        p_j = sum(p[(i, j)] for i in strata)
        var_pj = sum(W[i] ** 2 * q[(i, j)] * (1 - q[(i, j)]) / (n_i[i] - 1) for i in strata)
        area, se = total_area * p_j, total_area * np.sqrt(var_pj)
        users = q[(j, j)] if j in W else None
        users_ci = z * np.sqrt(users * (1 - users) / (n_i[j] - 1)) if j in W else None
        if j in W and p_j > 0:
            producers = p[(j, j)] / p_j
            N = {i: float(map_pixels[i]) for i in strata}
            n_hat_j = sum(N[i] * q[(i, j)] for i in strata)
            term = N[j] ** 2 * (1 - producers) ** 2 * users * (1 - users) / (n_i[j] - 1)
            term += producers ** 2 * sum(N[i] ** 2 * q[(i, j)] * (1 - q[(i, j)]) / (n_i[i] - 1) for i in strata if i != j)
            producers_ci = z * np.sqrt(term) / n_hat_j
        else:
            producers, producers_ci = (0.0 if p_j > 0 else None), None
        rows.append({
            'class': j, 'map_area': float(map_pixels.get(j, 0) * pixel_area), 'estimated_area': float(area),
            'se_area': float(se), 'ci_low': float(area - z * se), 'ci_high': float(area + z * se),
            'users_accuracy': users, 'users_ci': users_ci, 'producers_accuracy': producers, 'producers_ci': producers_ci,
            'samples': int(n_i.get(j, 0)), 'reference_samples': int(sum(n[(i, j)] for i in strata)),
        })
    summary = {'overall_accuracy': float(overall), 'overall_ci': float(z * np.sqrt(var_overall)),
               'total_area': float(total_area), 'samples': int(sum(n_i.values())), 'z': float(z)}
    return rows, summary


# --------------------------------------------------------------------------
# Núcleo: vectorización de un ráster clasificado
# --------------------------------------------------------------------------

def _polygonize_setup(raster_path, classes, connectivity):
    """Valida el ráster clasificado y las clases pedidas. Devuelve (class_map, códigos a conservar o None)."""
    meta = read_meta(raster_path)
    class_map = meta.get('class_map')
    if not class_map:
        raise ValueError('El ráster no es una clasificación: no tiene clases que vectorizar '
                         '(un ráster de regresión no se puede poligonizar).')
    if connectivity not in (4, 8):
        raise ValueError('La conectividad debe ser 4 u 8.')
    keep = None
    if classes:
        wanted = {str(c) for c in classes}
        unknown = wanted - set(class_map.values())
        if unknown:
            raise ValueError('Clases que no existen en el ráster: %s. Disponibles: %s.'
                             % (', '.join(sorted(unknown)), ', '.join(class_map.values())))
        keep = [int(code) for code, label in class_map.items() if label in wanted]
    return class_map, keep


def iter_polygon_chunks(raster_path, classes=None, min_area=0.0, simplify=0.0, connectivity=4,
                        strip_pixels=None, chunk_size=5000):
    """
    Vectoriza un ráster clasificado por franjas de filas para no cargarlo entero en memoria.

    Los polígonos de cada franja se calculan en coordenadas de píxel (enteras, exactas); los que
    tocan una costura entre franjas se unen con los de la franja vecina de su misma clase, así
    que un polígono grande no queda partido. Con conectividad 8, dos píxeles unidos solo por una
    esquina justo en una costura se quedan en polígonos distintos que se tocan en un vértice.
    El filtro de área mínima y la simplificación se aplican a los polígonos ya unidos.

    Devuelve un generador de listas de filas (class_name, class_code, area, geometry).
    """
    import rasterio
    from rasterio.features import shapes
    from rasterio.windows import Window
    from affine import Affine
    from shapely.affinity import affine_transform, translate
    from shapely.geometry import shape
    from shapely.ops import unary_union

    class_map, keep = _polygonize_setup(raster_path, classes, connectivity)
    strip_pixels = strip_pixels or _limit('ETL_RASTER_POLYGONIZE_STRIP_PIXELS', 25000000)

    with rasterio.open(raster_path) as src:
        if src.crs is None:
            raise ValueError('El ráster no tiene sistema de coordenadas.')
        check_raster_size(src.width, src.height)
        t = src.transform
        # Con el ráster girado las costuras no son horizontales: se procesa de una vez
        rotated = abs(t.b) > 1e-12 or abs(t.d) > 1e-12
        rows_per_strip = src.height if rotated else max(1, min(src.height, strip_pixels // max(1, src.width)))
        to_world = [t.a, t.b, t.d, t.e, t.c, t.f]

        def finish(code, poly, out):
            world = affine_transform(poly, to_world)
            if simplify and simplify > 0:
                world = world.simplify(simplify, preserve_topology=True)
            if world.is_empty or world.area < (min_area or 0):
                return
            if world.geom_type == 'MultiPolygon':     # la simplificación puede partir un polígono
                parts = list(world.geoms)
            else:
                parts = [world]
            for part in parts:
                if part.is_empty or part.area < (min_area or 0):
                    continue
                out.append({'class_name': class_map[str(code)], 'class_code': int(code),
                            'area': float(part.area), 'geometry': part})

        def flush(out):
            while len(out) >= chunk_size:
                chunk = out[:chunk_size]
                del out[:chunk_size]
                yield chunk

        out = []
        carry = {}            # código -> polígonos (píxeles) que tocan el final de la franja anterior
        for row0 in range(0, src.height, rows_per_strip):
            row1 = min(src.height, row0 + rows_per_strip)
            band = src.read(1, window=Window(0, row0, src.width, row1 - row0))
            valid = band != 0
            if keep is not None:
                valid &= np.isin(band, keep)
            found = {}
            for geom, value in shapes(band, mask=valid, transform=Affine.identity(), connectivity=connectivity):
                found.setdefault(int(value), []).append(translate(shape(geom), yoff=row0))
            del band, valid

            next_carry = {}
            for code in set(found) | set(carry):
                polys = found.get(code, [])
                previous = carry.get(code)
                if previous:
                    # Lo que toca la costura de arriba se une con lo que arrastra la franja anterior
                    top = [g for g in polys if g.bounds[1] == row0]
                    rest = [g for g in polys if g.bounds[1] != row0]
                    if top:
                        merged = unary_union(previous + top)
                        pieces = list(merged.geoms) if merged.geom_type == 'MultiPolygon' else [merged]
                    else:
                        pieces = list(previous)
                    polys = pieces + rest
                for g in polys:
                    if row1 < src.height and g.bounds[3] == row1:
                        next_carry.setdefault(code, []).append(g)
                    else:
                        finish(code, g, out)
            carry = next_carry
            for chunk in flush(out):
                yield chunk
        for code, polys in carry.items():           # franja final (no debería quedar nada)
            for g in polys:
                finish(code, g, out)
        if out:
            yield out


def polygonize_raster_file(raster_path, classes=None, min_area=0.0, simplify=0.0, connectivity=4,
                           strip_pixels=None):
    """
    Vectoriza un ráster clasificado (salida de Predecir ráster) en polígonos.

    classes: etiquetas de clase a conservar (None o vacío = todas).
    min_area: descarta polígonos con menos área (unidades del CRS al cuadrado).
    simplify: tolerancia de simplificación en unidades del CRS (0 = sin simplificar).
    Devuelve un GeoDataFrame con class_name, class_code, area y geometría.
    """
    import geopandas as gpd
    import rasterio

    rows = []
    for chunk in iter_polygon_chunks(raster_path, classes, min_area, simplify, connectivity, strip_pixels):
        rows.extend(chunk)
    with rasterio.open(raster_path) as src:
        crs = src.crs
    return gpd.GeoDataFrame(rows, columns=['class_name', 'class_code', 'area', 'geometry'],
                            geometry='geometry', crs=crs)


# --------------------------------------------------------------------------
# Nodos (reciben el dict de parámetros del motor)
# --------------------------------------------------------------------------

def input_Raster(dicc):
    """
    Entrada de un GeoTIFF. Devuelve [ruta]. Crea en el directorio de artefactos un enlace
    al fichero original (o copia si no se puede enlazar) y guarda los nombres de banda.
    """
    source = resolve_raster_path(dicc.get('raster-file') or dicc.get('file') or '')

    info = raster_summary(source)  # valida que rasterio lo abre
    check_raster_size(info['width'], info['height'])
    names = parse_band_names(dicc.get('band-names'), info['bands'])

    target = new_artifact_path(dicc['id'], '.tif')
    try:
        os.symlink(os.path.abspath(source), target)
    except OSError:
        shutil.copyfile(source, target)
    write_meta(target, {'band_names': names, 'crs': info['crs']})
    print('Ráster %s: %d bandas (%s), CRS %s' % (os.path.basename(source), info['bands'],
                                                 ', '.join(names), info['crs']))
    return [target]


def _split_inputs(data):
    """Separa las entradas de un nodo en (ráster, modelo, tabla) según su tipo."""
    raster = next((d for d in data if is_raster_ref(d)), None)
    model = next((d for d in data if is_model_ref(d)), None)
    table = next((d for d in data if not is_artifact_ref(d)), None)
    return raster, model, table


def trans_RasterSample(dicc):
    """Ráster + polígonos de muestra con clase -> tabla de píxeles (bandas + clase)."""
    raster, _, table = _split_inputs(dicc.get('data', []))
    if not raster or not table:
        raise Exception('Conecta un ráster y una tabla de polígonos de muestra.')
    class_attr = dicc.get('class-attr')
    if not class_attr:
        raise Exception('Indica la columna que contiene la clase de cada muestra.')

    names = read_meta(raster).get('band_names')
    gdf = _read_samples_table(table, class_attr, dicc.get('geom-attr') or 'wkb_geometry')
    df = sample_raster_pixels(
        raster, gdf, class_attr, band_names=names,
        max_per_class=_to_int(dicc.get('max-per-class'), None),
        seed=_to_int(dicc.get('seed'), DEFAULT_SEED))

    table_name = dicc['id']
    _write_table(df, table_name)
    print('Muestreados %d píxeles de %d polígonos.' % (len(df), len(gdf)))
    return [table_name]


def trans_RandomForest(dicc):
    """Tabla con variable objetivo + predictoras -> [tabla de informe, ruta del modelo]."""
    import joblib
    table = next((d for d in dicc.get('data', []) if not is_artifact_ref(d)), None)
    if not table:
        raise Exception('Conecta una tabla con la variable objetivo y las predictoras.')
    target = dicc.get('target')
    if not target:
        raise Exception('Indica la variable objetivo.')
    features = dicc.get('features') or []
    if isinstance(features, str):
        features = [f for f in features.split(',') if f.strip()]

    engine = _engine()
    try:
        with engine.connect() as conn:
            df = pd.read_sql('SELECT * FROM "%s"."%s"' % (GEOETL_DB['schema'], table.replace('"', '""')), conn)
    finally:
        engine.dispose()
    if not features:
        # Por defecto: todas las columnas numéricas que no son el objetivo
        features = [c for c in df.columns
                    if c != target and pd.api.types.is_numeric_dtype(df[c])
                    and c != 'ogc_fid' and c not in AUX_COLUMNS]

    df, original_rows = subsample_training_rows(
        df, target, _limit('ETL_RASTER_MAX_TRAIN_ROWS', 2000000), _to_int(dicc.get('seed'), DEFAULT_SEED))
    if original_rows:
        print('AVISO: hay %d filas de entrenamiento y el máximo configurado es %d; se entrena con una muestra de %d '
              '(conserva todas las filas de las clases pequeñas). Usa "Máximo de píxeles por clase" en Muestrear ráster '
              'para controlar la muestra.' % (original_rows, _limit('ETL_RASTER_MAX_TRAIN_ROWS', 2000000), len(df)))

    max_depth = _to_int(dicc.get('max-depth'), None)
    validation = dicc.get('validation') or 'random'
    bundle, report, matrix = train_model(
        df, target, features, problem=dicc.get('problem') or 'auto',
        n_estimators=_to_int(dicc.get('n-estimators'), DEFAULT_N_ESTIMATORS),
        max_depth=max_depth,
        min_samples_leaf=_to_int(dicc.get('min-samples-leaf'), DEFAULT_MIN_SAMPLES_LEAF),
        test_percent=_to_int(dicc.get('test-percent'), DEFAULT_TEST_PERCENT),
        seed=_to_int(dicc.get('seed'), DEFAULT_SEED),
        validation=validation,
        folds=_to_int(dicc.get('folds'), DEFAULT_FOLDS),
        block_size=_to_float(dicc.get('block-size')),
        max_features=dicc.get('max-features') or 'auto')
    used = report[report['section'] == 'validation']['name']
    if len(used):
        if validation == 'auto':
            print('Validación automática: %s.' % {'polygon': 'dejando fuera polígonos de muestra',
                                                   'random': 'reserva aleatoria (la tabla no permite validar por polígonos)'}
                  .get(used.iloc[0], used.iloc[0]))
        validation = used.iloc[0]

    if original_rows:
        report = pd.concat([report, pd.DataFrame([('training', 'subsampled_from', float(original_rows))],
                                                 columns=report.columns)], ignore_index=True)
    report_table = dicc['id'] + '_0'
    matrix_table = dicc['id'] + '_2'
    _write_table(report, report_table)
    _write_table(matrix, matrix_table)
    model_path = new_artifact_path(dicc['id'], MODEL_EXTENSION)
    joblib.dump(bundle, model_path)
    metrics = {r['name']: float(r['value']) for _, r in report[report['section'] == 'metric'].iterrows()
               if r['name'] != 'fold_score_std'}
    rows = report[(report['section'] == 'training') & (report['name'] == 'rows')]['value']
    write_meta(model_path, {
        'problem': bundle['problem'], 'features': features, 'target': bundle['target'],
        'classes': [str(c) for c in (bundle['classes'] or [])], 'metrics': metrics,
        'rows': int(rows.iloc[0]) if len(rows) else None,
        'params': {'n_estimators': _to_int(dicc.get('n-estimators'), DEFAULT_N_ESTIMATORS), 'max_depth': max_depth,
                   'min_samples_leaf': _to_int(dicc.get('min-samples-leaf'), DEFAULT_MIN_SAMPLES_LEAF),
                   'seed': _to_int(dicc.get('seed'), DEFAULT_SEED), 'validation': validation,
                   'max_features': dicc.get('max-features') or 'auto'}})
    print('Random Forest (%s):\n%s' % (bundle['problem'], summarize_report(report)))
    return [report_table, model_path, matrix_table]


def trans_RasterPredict(dicc):
    """Ráster + modelo -> [ráster clasificado (o de valores, si es regresión), ráster de confianza]."""
    raster, model_path, _ = _split_inputs(dicc.get('data', []))
    if not raster or not model_path:
        raise Exception('Conecta un ráster y un modelo entrenado.')
    bundle = load_model_bundle(model_path)
    out_path = new_artifact_path(dicc['id'], '.tif')
    conf_path = new_artifact_path(dicc['id'] + '_conf', '.tif')
    class_map = predict_raster_file(raster, bundle, out_path, confidence_path=conf_path)
    print('Ráster predicho (%s)%s' % (bundle['problem'],
                                      ': ' + ', '.join('%s=%s' % kv for kv in class_map.items()) if class_map else ''))
    return [out_path, conf_path]


def trans_RasterMajority(dicc):
    """Ráster clasificado -> ráster clasificado sin ruido (filtro de mayoría o tamaño mínimo de parche)."""
    raster, _, _ = _split_inputs(dicc.get('data', []))
    if not raster:
        raise Exception('Conecta un ráster clasificado.')
    if not read_meta(raster).get('class_map'):
        raise Exception('El filtro solo se aplica a un ráster clasificado (salida de "Predecir ráster").')
    mode = dicc.get('mode') or 'majority'
    out_path = new_artifact_path(dicc['id'], '.tif')
    if mode == 'sieve':
        sieve_file(raster, out_path, _to_int(dicc.get('min-pixels'), 4),
                   connectivity=_to_int(dicc.get('connectivity'), 4))
        print('Parches de menos de %s píxeles eliminados.' % _to_int(dicc.get('min-pixels'), 4))
    elif mode == 'majority':
        size = _to_int(dicc.get('window'), 3)
        iterations = _to_int(dicc.get('iterations'), 1)
        majority_filter_file(raster, out_path, size=size, iterations=iterations)
        print('Filtro de mayoría %dx%d aplicado %d vez/veces.' % (size, size, iterations))
    else:
        raise Exception('Modo de filtrado desconocido: %s.' % mode)
    write_meta(out_path, read_meta(raster))
    return [out_path]


def trans_RasterIndex(dicc):
    """Ráster multibanda -> el mismo ráster con una banda más (índice espectral)."""
    raster, _, _ = _split_inputs(dicc.get('data', []))
    if not raster:
        raise Exception('Conecta un ráster.')
    index = dicc.get('index')
    if index not in INDEX_DEFS:
        raise Exception('Elige el índice que quieres calcular.')
    import rasterio
    with rasterio.open(raster) as src:
        count = src.count
    names = read_meta(raster).get('band_names') or parse_band_names(None, count)
    if len(names) != count:
        names = parse_band_names(names, count)
    selected = [dicc.get('band-%d' % (i + 1)) for i in range(len(INDEX_DEFS[index]['roles']))]
    scale, offset = reflectance_conversion(dicc)
    out_path = new_artifact_path(dicc['id'], '.tif')
    out_names = add_index_file(
        raster, out_path, index, names, selected,
        output_name=(dicc.get('name') or '').strip() or index,
        scale=scale, offset=offset,
        savi_l=_to_float(dicc.get('savi-l'), DEFAULT_SAVI_L))
    meta = dict(read_meta(raster))
    meta['band_names'] = out_names
    write_meta(out_path, meta)
    print('Índice %s añadido como banda "%s".' % (index, out_names[-1]))
    return [out_path]


def trans_ClassAssess(dicc):
    """Ráster clasificado + muestras de validación -> [informe, matriz de confusión]."""
    raster, _, table = _split_inputs(dicc.get('data', []))
    if not raster or not table:
        raise Exception('Conecta un ráster clasificado y una tabla con las muestras de validación.')
    class_attr = dicc.get('class-attr')
    if not class_attr:
        raise Exception('Indica la columna que contiene la clase real de cada muestra de validación.')
    gdf = _read_samples_table(table, class_attr, dicc.get('geom-attr') or 'wkb_geometry')
    report, matrix, unknown = assess_classification(raster, gdf, class_attr)
    report_table, matrix_table = dicc['id'] + '_0', dicc['id'] + '_1'
    _write_table(report, report_table)
    _write_table(matrix, matrix_table)
    if unknown:
        print('AVISO: las clases de validación %s no existen en el modelo: se cuentan como errores.' % ', '.join(unknown))
    print('Evaluación con muestras independientes:\n%s' % summarize_report(report))
    return [report_table, matrix_table]


def trans_RasterStack(dicc):
    """Varios ráster -> un ráster multibanda alineado con el primero que se conecte."""
    rasters = [d for d in dicc.get('data', []) if is_raster_ref(d)]
    if len(rasters) < 2:
        raise Exception('Conecta al menos dos ráster para combinarlos.')
    names = []
    for path in rasters:
        meta_names = read_meta(path).get('band_names')
        names.append(meta_names)
    prefixes = [dicc.get('prefix-%d' % (i + 1)) or '' for i in range(STACK_MAX_INPUTS)]
    out_path = new_artifact_path(dicc['id'], '.tif')
    out_names = stack_rasters(rasters, out_path, names, prefixes=prefixes,
                              resampling=dicc.get('resampling') or 'bilinear')
    meta = {'band_names': out_names}
    crs = read_meta(rasters[0]).get('crs')
    if crs:
        meta['crs'] = crs
    write_meta(out_path, meta)
    print('Combinados %d ráster en uno de %d bandas (%s).' % (len(rasters), len(out_names), ', '.join(out_names)))
    return [out_path]


def _sql_type_of(values):
    """Tipo PostgreSQL de la columna de predicción según los valores."""
    present = [v for v in values if v is not None and not (isinstance(v, float) and np.isnan(v))]
    if present and all(isinstance(v, (int, np.integer)) and not isinstance(v, bool) for v in present):
        return 'bigint'
    if present and all(isinstance(v, (int, float, np.integer, np.floating)) and not isinstance(v, bool) for v in present):
        return 'double precision'
    return 'text'


def trans_TablePredict(dicc):
    """
    Tabla + modelo -> la misma tabla con la predicción y su confianza. Conserva todas las
    columnas (también la geometría y sus tipos): copia la tabla en SQL y rellena las dos columnas
    nuevas con la clave temporal __rid, todo en una transacción (si algo falla no queda nada).
    """
    import joblib
    import psycopg2
    from psycopg2 import sql
    from psycopg2.extras import execute_values

    table = next((d for d in dicc.get('data', []) if not is_artifact_ref(d)), None)
    model_path = next((d for d in dicc.get('data', []) if is_model_ref(d)), None)
    if not table or not model_path:
        raise Exception('Conecta una tabla y un modelo entrenado.')
    column = _identifier(dicc.get('column') or 'prediction')
    conf_column = column + '_confidence'
    bundle = load_model_bundle(model_path)
    features = bundle['features']

    schema, out_table = GEOETL_DB['schema'], dicc['id']
    conn = psycopg2.connect(user=GEOETL_DB['user'], password=GEOETL_DB['password'], host=GEOETL_DB['host'],
                            port=GEOETL_DB['port'], database=GEOETL_DB['database'])
    try:
        with conn, conn.cursor() as cur:
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema=%s AND table_name=%s",
                        (schema, table))
            existing = [r[0] for r in cur.fetchall()]
            if not existing:
                raise ValueError('No se encuentra la tabla de entrada.')
            missing = [f for f in features if f not in existing]
            if missing:
                raise ValueError('La tabla no tiene las columnas con las que se entrenó el modelo: %s. '
                                 'Columnas de la tabla: %s.' % (', '.join(missing), ', '.join(existing)))
            clash = [c for c in (column, conf_column, '__rid') if c in existing]
            if clash:
                raise ValueError('La tabla ya tiene una columna llamada "%s". Elige otro nombre para la columna '
                                 'de predicción o renómbrala antes.' % clash[0])

            ident_out, ident_in = sql.Identifier(schema, out_table), sql.Identifier(schema, table)
            cur.execute(sql.SQL('DROP TABLE IF EXISTS {}').format(ident_out))
            cur.execute(sql.SQL('CREATE TABLE {} AS SELECT * FROM {}').format(ident_out, ident_in))
            cur.execute(sql.SQL('ALTER TABLE {} ADD COLUMN __rid bigserial').format(ident_out))
            cur.execute(sql.SQL('CREATE INDEX {} ON {} (__rid)').format(sql.Identifier(out_table + '_rid_idx'), ident_out))

            cur.execute(sql.SQL('SELECT __rid, {} FROM {} ORDER BY __rid').format(
                sql.SQL(', ').join(sql.Identifier(f) for f in features), ident_out))
            rows = cur.fetchall()
            frame = pd.DataFrame(rows, columns=['__rid'] + features)
            del rows
            predicted, confidence = predict_dataframe(frame, bundle)
            rids = frame['__rid'].to_numpy()
            ptype = 'double precision' if bundle['problem'] != 'classification' else _sql_type_of(predicted)
            cur.execute(sql.SQL('ALTER TABLE {} ADD COLUMN {} ' + ptype + ', ADD COLUMN {} double precision').format(
                ident_out, sql.Identifier(column), sql.Identifier(conf_column)))
            cast = '::' + ptype
            update = sql.SQL('UPDATE {} AS t SET {} = v.p, {} = v.c FROM (VALUES %s) AS v(rid, p, c) '
                             'WHERE t.__rid = v.rid').format(ident_out, sql.Identifier(column),
                                                            sql.Identifier(conf_column)).as_string(cur)
            batch = 20000
            for start in range(0, len(rids), batch):
                part = [(int(rids[i]),
                         None if predicted[i] is None or (isinstance(predicted[i], float) and np.isnan(predicted[i]))
                         else (predicted[i].item() if hasattr(predicted[i], 'item') else predicted[i]),
                         None if np.isnan(confidence[i]) else float(confidence[i]))
                        for i in range(start, min(start + batch, len(rids)))]
                execute_values(cur, update, part, template='(%s::bigint, %s' + cast + ', %s::double precision)')
            cur.execute(sql.SQL('ALTER TABLE {} DROP COLUMN __rid').format(ident_out))
            skipped = int(np.isnan(confidence).sum())
    finally:
        conn.close()
    print('Predicción aplicada a %d filas en "%s" (%d sin predecir por tener valores nulos o no numéricos).'
          % (len(rids), column, skipped))
    return [out_table]


def _read_mask_geometries(table_name, crs, geom_attr='wkb_geometry'):
    """Polígonos de una tabla PostGIS, reproyectados al sistema de coordenadas del ráster y válidos."""
    import geopandas as gpd
    from .etl_tasks import get_type_n_srid

    srid, _ = get_type_n_srid(table_name, geom=geom_attr)
    if not srid:
        raise ValueError('La máscara no tiene sistema de coordenadas.')
    engine = _engine()
    try:
        query = 'SELECT "%s" FROM "%s"."%s"' % (geom_attr.replace('"', '""'), GEOETL_DB['schema'],
                                              table_name.replace('"', '""'))
        with engine.connect() as conn:
            gdf = gpd.read_postgis(query, conn, geom_col=geom_attr, crs='EPSG:%d' % srid)
    finally:
        engine.dispose()
    gdf = gdf.to_crs(crs)
    geoms = []
    for g in gdf.geometry:
        if g is None or g.is_empty or g.geom_type not in ('Polygon', 'MultiPolygon'):
            continue
        geoms.append(g if g.is_valid else g.buffer(0))
    if not geoms:
        raise ValueError('La máscara debe ser una capa de polígonos con al menos un polígono.')
    return geoms


def trans_RasterClip(dicc):
    """Ráster + máscara de polígonos -> el ráster recortado (y, si se pide, a otro tamaño de píxel)."""
    import rasterio
    raster, _, table = _split_inputs(dicc.get('data', []))
    if not raster or not table:
        raise Exception('Conecta un ráster y una capa de polígonos que sirva de máscara.')
    pixel_size = _to_float(dicc.get('pixel-size'))
    with rasterio.open(raster) as src:
        crs, res = src.crs, src.res
    if crs is None:
        raise Exception('El ráster no tiene sistema de coordenadas.')
    geoms = _read_mask_geometries(table, crs, dicc.get('geom-attr') or 'wkb_geometry')
    out_path = new_artifact_path(dicc['id'], '.tif')
    try:
        w, h, inside, added = clip_raster_file(
            raster, geoms, out_path, mode=dicc.get('mode') or 'polygon', pixel_size=pixel_size,
            resampling=dicc.get('resampling') or 'average')
    except Exception:
        remove_artifact(out_path)
        raise
    print('Recorte: %d x %d píxeles%s.' % (w, h, (' (de %s m a %s m)' % (res[0], pixel_size)) if pixel_size else ''))
    if added:
        print('AVISO: el ráster no declaraba valor de sin dato; se ha usado el 0 para lo que queda fuera de la máscara.')
    return [out_path]


def _write_points(rows, table_name, epsg, columns):
    """Tabla de puntos (ogc_fid, columnas de texto/número, wkb_geometry) con psycopg2, en una transacción."""
    import psycopg2
    from psycopg2 import sql
    from psycopg2.extras import execute_values
    schema = GEOETL_DB['schema']
    conn = psycopg2.connect(user=GEOETL_DB['user'], password=GEOETL_DB['password'], host=GEOETL_DB['host'],
                            port=GEOETL_DB['port'], database=GEOETL_DB['database'])
    try:
        with conn, conn.cursor() as cur:
            cur.execute(sql.SQL('DROP TABLE IF EXISTS {}.{}').format(sql.Identifier(schema), sql.Identifier(table_name)))
            defs = sql.SQL(', ').join(sql.SQL('{} ' + ctype).format(sql.Identifier(name)) for name, ctype in columns)
            cur.execute(sql.SQL('CREATE TABLE {}.{} (ogc_fid serial PRIMARY KEY, {}, wkb_geometry geometry(Point, {}))').format(
                sql.Identifier(schema), sql.Identifier(table_name), defs, sql.Literal(int(epsg))))
            names = sql.SQL(', ').join(sql.Identifier(name) for name, _ in columns)
            insert = sql.SQL('INSERT INTO {}.{} ({}, wkb_geometry) VALUES %s').format(
                sql.Identifier(schema), sql.Identifier(table_name), names).as_string(cur)
            template = '(' + ', '.join(['%s'] * len(columns)) + ', ST_SetSRID(ST_MakePoint(%s, %s), ' + str(int(epsg)) + '))'
            if rows:
                execute_values(cur, insert, rows, template=template, page_size=5000)
            cur.execute(sql.SQL('CREATE INDEX {} ON {}.{} USING gist (wkb_geometry)').format(
                sql.Identifier(table_name + '_geom_idx'), sql.Identifier(schema), sql.Identifier(table_name)))
    finally:
        conn.close()


def trans_StratifiedSample(dicc):
    """Ráster clasificado -> puntos de una muestra aleatoria estratificada por clase, para etiquetar la clase real."""
    import rasterio
    raster, _, _ = _split_inputs(dicc.get('data', []))
    if not raster:
        raise Exception('Conecta un ráster clasificado.')
    per_class = _to_int(dicc.get('per-class'), DEFAULT_SAMPLES_PER_CLASS)
    points = stratified_sample_points(raster, per_class=per_class, seed=_to_int(dicc.get('seed'), DEFAULT_SEED))
    with rasterio.open(raster) as src:
        epsg = src.crs.to_epsg() if src.crs else None
    if not epsg:
        raise Exception('No se puede determinar el código EPSG del ráster.')
    class_map = read_meta(raster)['class_map']
    rows = [(k + 1, class_map[str(code)], int(code), None, x, y) for k, (code, x, y) in enumerate(points)]
    table_name = dicc['id']
    _write_points(rows, table_name, epsg, [('id', 'integer'), ('map_class', 'text'), ('map_code', 'integer'),
                                          ('reference', 'text')])
    counts = {}
    for _, name, _, _, _, _ in rows:
        counts[name] = counts.get(name, 0) + 1
    print('Muestreo estratificado: %d puntos (%s). Rellena la columna "reference" con la clase real de cada punto.'
          % (len(rows), ', '.join('%s=%d' % kv for kv in sorted(counts.items()))))
    return [table_name]


def trans_AreaEstimate(dicc):
    """Ráster clasificado + puntos de referencia -> [superficies por clase con intervalo, informe]."""
    import geopandas as gpd
    import rasterio
    raster, _, table = _split_inputs(dicc.get('data', []))
    if not raster or not table:
        raise Exception('Conecta un ráster clasificado y la tabla de puntos de referencia.')
    attr = dicc.get('reference-attr')
    if not attr:
        raise Exception('Indica la columna que contiene la clase real de cada punto.')
    level = str(dicc.get('confidence-level') or '0.95')
    if level not in CONFIDENCE_Z:
        raise Exception('Nivel de confianza no válido: %s.' % level)
    gdf = _read_samples_table(table, attr, dicc.get('geom-attr') or 'wkb_geometry')
    kinds = set(gdf.geometry.geom_type.dropna())
    if kinds - {'Point'}:
        raise Exception('La estimación de superficies necesita PUNTOS de una muestra aleatoria estratificada (por ejemplo, '
                        'los de "Muestreo estratificado" con su clase real anotada), no %s.' % ', '.join(sorted(kinds - {'Point'})))
    map_pixels, pixel_area = map_class_areas(raster)
    class_map = read_meta(raster)['class_map']
    samples, outside, unlabeled = [], 0, 0
    with rasterio.open(raster) as src:
        pts = gdf.to_crs(src.crs) if gdf.crs is not None else None
        if pts is None:
            raise Exception('La tabla de puntos no tiene sistema de coordenadas.')
        left, bottom, right, top = src.bounds
        for geom, label in zip(pts.geometry, pts[attr]):
            if label is None or (isinstance(label, float) and np.isnan(label)) or str(label).strip() == '':
                unlabeled += 1
                continue
            if geom is None or not (left <= geom.x < right and bottom < geom.y <= top):
                outside += 1
                continue
            code = int(next(src.sample([(geom.x, geom.y)]))[0])
            if code == 0 or str(code) not in class_map:
                outside += 1
                continue
            samples.append((class_map[str(code)], str(_clean_class_label(label)).strip()))
    if not samples:
        raise Exception('Ningún punto con clase real cae sobre píxeles clasificados del ráster.')
    rows, summary = estimate_areas(map_pixels, pixel_area, samples, z=CONFIDENCE_Z[level])
    areas_table, report_table = dicc['id'] + '_0', dicc['id'] + '_1'
    _write_table(pd.DataFrame(rows, columns=['class', 'map_area', 'estimated_area', 'se_area', 'ci_low', 'ci_high',
                                             'users_accuracy', 'users_ci', 'producers_accuracy', 'producers_ci',
                                             'samples', 'reference_samples']), areas_table)
    report = [('area_estimation', 'overall_accuracy', summary['overall_accuracy']),
              ('area_estimation', 'overall_accuracy_ci', summary['overall_ci']),
              ('area_estimation', 'total_area', summary['total_area']),
              ('area_estimation', 'samples', float(summary['samples'])),
              ('area_estimation', 'samples_outside_or_unclassified', float(outside)),
              ('area_estimation', 'samples_without_reference', float(unlabeled)),
              ('area_estimation', 'confidence_level', float(level))]
    no_errors = all(r[0] == r[1] for r in samples)
    if no_errors:
        report.append(('area_estimation', 'no_errors_in_sample', 1.0))
    _write_table(pd.DataFrame(report, columns=['section', 'name', 'value']), report_table)
    if no_errors:
        print('AVISO: la muestra no contiene ningún error, así que los intervalos salen de anchura 0. Eso no significa que '
              'el mapa sea perfecto: con una muestra mayor aparecerían errores y el intervalo sería realista.')
    print('Estimación de superficies (%d puntos, nivel %s): exactitud global %.3f ± %.3f; %s' % (
        summary['samples'], level, summary['overall_accuracy'], summary['overall_ci'],
        ', '.join('%s=%.0f ± %.0f' % (r['class'], r['estimated_area'], CONFIDENCE_Z[level] * r['se_area']) for r in rows)))
    if unlabeled:
        print('AVISO: %d puntos no tienen clase real y no se han usado.' % unlabeled)
    return [areas_table, report_table]


def _write_polygon_chunks(chunks, table_name, epsg):
    """
    Crea la tabla de polígonos (ogc_fid, class_name, class_code, area, wkb_geometry) con
    psycopg2 y WKB, sin depender de geoalchemy2. Inserta por lotes en UNA transacción: si falla
    la vectorización a mitad, no queda una tabla a medias. Devuelve (nº de polígonos, clases).
    """
    import psycopg2
    from psycopg2 import sql
    from psycopg2.extras import execute_values

    schema = GEOETL_DB['schema']
    total, names = 0, set()
    conn = psycopg2.connect(user=GEOETL_DB['user'], password=GEOETL_DB['password'], host=GEOETL_DB['host'],
                            port=GEOETL_DB['port'], database=GEOETL_DB['database'])
    try:
        with conn, conn.cursor() as cur:
            cur.execute(sql.SQL('DROP TABLE IF EXISTS {}.{}').format(sql.Identifier(schema), sql.Identifier(table_name)))
            cur.execute(sql.SQL(
                'CREATE TABLE {}.{} (ogc_fid serial PRIMARY KEY, class_name text, class_code integer, '
                'area double precision, wkb_geometry geometry(Polygon, {}))'
            ).format(sql.Identifier(schema), sql.Identifier(table_name), sql.Literal(int(epsg))))
            insert = sql.SQL('INSERT INTO {}.{} (class_name, class_code, area, wkb_geometry) VALUES %s').format(
                sql.Identifier(schema), sql.Identifier(table_name)).as_string(cur)
            template = '(%s, %s, %s, ST_SetSRID(ST_GeomFromWKB(%s), ' + str(int(epsg)) + '))'
            for chunk in chunks:
                rows = [(r['class_name'], int(r['class_code']), float(r['area']), r['geometry'].wkb) for r in chunk]
                if rows:
                    execute_values(cur, insert, rows, template=template)
                    total += len(rows)
                    names.update(r['class_name'] for r in chunk)
            cur.execute(sql.SQL('CREATE INDEX {} ON {}.{} USING gist (wkb_geometry)').format(
                sql.Identifier(table_name + '_geom_idx'), sql.Identifier(schema), sql.Identifier(table_name)))
    finally:
        conn.close()
    return total, names


def _write_polygon_table(gdf, table_name, epsg):
    """Escribe un GeoDataFrame de polígonos (ver polygonize_raster_file) como tabla PostGIS."""
    rows = [{'class_name': r.class_name, 'class_code': r.class_code, 'area': r.area, 'geometry': r.geometry}
            for r in gdf.itertuples()]
    _write_polygon_chunks([rows], table_name, epsg)


def trans_RasterPolygonize(dicc):
    """Ráster clasificado -> tabla PostGIS de polígonos (clase, código, área)."""
    import rasterio
    raster, _, _ = _split_inputs(dicc.get('data', []))
    if not raster:
        raise Exception('Conecta un ráster clasificado.')
    classes = dicc.get('classes') or []
    if isinstance(classes, str):
        classes = [c.strip() for c in classes.split(',') if c.strip()]

    with rasterio.open(raster) as src:
        epsg = src.crs.to_epsg() if src.crs else None
    if not epsg:
        raise Exception('No se puede determinar el código EPSG del ráster.')

    chunks = iter_polygon_chunks(
        raster, classes=classes,
        min_area=float(dicc.get('min-area') or 0),
        simplify=float(dicc.get('simplify') or 0),
        connectivity=_to_int(dicc.get('connectivity'), 4))
    table_name = dicc['id']
    total, names = _write_polygon_chunks(chunks, table_name, epsg)
    print('Vectorizados %d polígonos (%s)' % (total, ', '.join(sorted(names)) if total else 'ninguno'))
    return [table_name]
