# -*- coding: utf-8 -*-
"""
Modelos predictivos guardados (nodos "Guardar modelo" y "Modelo guardado").

Un modelo entrenado se guarda en un directorio persistente, versionado y separado por usuario. Por defecto
<FILEMANAGER_DIRECTORY>/.geoetl_models (configurable con ETL_MODELS_DIR):

    <ETL_MODELS_DIR>/<usuario>-<hash>/<nombre>/v0001.joblib
                                               v0001.json     (metadatos firmados)

SEGURIDAD. Un fichero .joblib es un pickle: cargar uno manipulado ejecuta código arbitrario. Por eso
nunca se carga un fichero que no haya firmado este mismo servidor:
  * al guardar se calcula el SHA-256 del fichero y se firma (HMAC-SHA256) junto con TODOS los
    metadatos (propietario, nombre, versión, variables, clases...);
  * al cargar se leen los bytes una sola vez, se verifica el hash y la firma y solo entonces se
    entregan; el que llama trabaja con esos mismos bytes verificados (no se vuelve a leer el fichero);
  * los nombres y rutas se validan para que no puedan salir del directorio de modelos.

Las funciones de este módulo no dependen de Django salvo para leer la configuración.
"""

import fcntl
import hashlib
import hmac
import json
import os
import re
import shutil
import tempfile
import time
import unicodedata

from . import settings as plugin_settings
from .etl_raster import ensure_dir

MODEL_FORMAT = 1
NAME_MAX = 60
VERSION_FILE = re.compile(r'^v(\d{4,})\.json$')


class ModelError(ValueError):
    """Error comprensible para el usuario (nombre inválido, modelo inexistente, firma incorrecta...)."""


# --------------------------------------------------------------------------
# Rutas y nombres
# --------------------------------------------------------------------------

def models_root():
    """Directorio persistente de los modelos (se crea si no existe)."""
    configured = (getattr(plugin_settings, 'ETL_MODELS_DIR', '') or '').strip()
    if configured:
        root = configured
    else:
        from django.conf import settings
        data = getattr(settings, 'FILEMANAGER_DIRECTORY', None)
        if not data:
            raise ModelError('No hay un directorio persistente para los modelos: configura ETL_MODELS_DIR.')
        # Dentro del directorio del gestor de ficheros: es persistente y los procesos del ETL (www-data) pueden
        # escribir en él, a diferencia de su carpeta padre. La firma de cada modelo impide que se manipule.
        root = os.path.join(os.path.realpath(data), '.geoetl_models')
    try:
        ensure_dir(root, mode=0o750)
    except OSError as e:
        raise ModelError('No se puede crear el directorio de modelos (%s): %s' % (root, e))
    if not os.access(root, os.W_OK):
        raise ModelError('El directorio de modelos no es escribible por el servidor: %s' % root)
    return os.path.realpath(root)


def safe_model_name(name):
    """Nombre de modelo válido: minúsculas, dígitos y guion bajo (máx. 60)."""
    text = unicodedata.normalize('NFKD', str(name or '')).encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'[^0-9a-zA-Z_]+', '_', text).strip('_').lower()
    if not text:
        raise ModelError('Indica un nombre para el modelo.')
    if text[0].isdigit():
        text = 'm_' + text
    return text[:NAME_MAX]


def owner_dir_name(owner):
    """Nombre de carpeta del propietario: legible y sin colisiones entre usuarios parecidos."""
    if not owner or not str(owner).strip():
        raise ModelError('No se conoce el usuario propietario del modelo.')
    owner = str(owner)
    readable = re.sub(r'[^0-9A-Za-z_.-]+', '_', owner).strip('._-')[:40] or 'u'
    return '%s-%s' % (readable, hashlib.sha1(owner.encode('utf-8')).hexdigest()[:8])


def _inside(root, path):
    real = os.path.realpath(path)
    return real == root or real.startswith(root + os.sep)


def model_dir(owner, name, create=False):
    """Carpeta de un modelo; garantiza que queda dentro del directorio de modelos."""
    root = models_root()
    path = os.path.join(root, owner_dir_name(owner), safe_model_name(name))
    if not _inside(root, path):
        raise ModelError('Ruta de modelo no válida.')
    if create:
        ensure_dir(path, mode=0o750)
        if not _inside(root, path):                     # un enlace simbólico no puede sacarlo de aquí
            raise ModelError('Ruta de modelo no válida.')
    return path


def _version_paths(directory, version):
    base = os.path.join(directory, 'v%04d' % int(version))
    return base + '.joblib', base + '.json'


# --------------------------------------------------------------------------
# Firma
# --------------------------------------------------------------------------

def _signing_key():
    configured = (getattr(plugin_settings, 'ETL_MODELS_SIGNING_KEY', '') or '').strip()
    if configured:
        return configured.encode('utf-8')
    from django.conf import settings
    return hashlib.sha256(b'geoetl-models|' + str(settings.SECRET_KEY).encode('utf-8')).digest()


def _canonical(meta):
    core = {k: v for k, v in meta.items() if k != 'signature'}
    return json.dumps(core, sort_keys=True, ensure_ascii=True, separators=(',', ':')).encode('utf-8')


def sign_meta(meta):
    return hmac.new(_signing_key(), _canonical(meta), hashlib.sha256).hexdigest()


def verify_meta(meta):
    signature = meta.get('signature')
    return bool(signature) and hmac.compare_digest(str(signature), sign_meta(meta))


# --------------------------------------------------------------------------
# Guardar
# --------------------------------------------------------------------------

def _versions(directory):
    if not os.path.isdir(directory):
        return []
    found = []
    for entry in os.listdir(directory):
        m = VERSION_FILE.match(entry)
        if m:
            found.append(int(m.group(1)))
    return sorted(found)


def _runtime_versions():
    import platform
    out = {'python': platform.python_version()}
    try:
        import sklearn
        out['sklearn'] = sklearn.__version__
    except ImportError:
        pass
    try:
        import numpy
        out['numpy'] = numpy.__version__
    except ImportError:
        pass
    return out


def save_model(owner, name, model_path, info=None, description='', on_existing='version'):
    """
    Guarda el modelo de model_path (un .joblib generado por este servidor) como una versión nueva.

    info: metadatos del entrenamiento (problem, features, classes, target, metrics, params, rows).
    on_existing: 'version' (añade una versión; las antiguas se podan según ETL_MODELS_KEEP_VERSIONS),
    'replace' (borra las versiones anteriores) o 'fail' (error si ya existe).
    Devuelve los metadatos de la versión guardada.
    """
    if on_existing not in ('version', 'replace', 'fail'):
        raise ModelError('Opción desconocida para un modelo existente: %s.' % on_existing)
    if not model_path or not os.path.isfile(model_path):
        raise ModelError('No hay un modelo que guardar.')
    clean_name = safe_model_name(name)
    directory = model_dir(owner, clean_name, create=True)

    with open(os.path.join(directory, '.lock'), 'a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)              # dos ejecuciones a la vez no pisan el mismo número de versión
        try:
            existing = _versions(directory)
            if existing and on_existing == 'fail':
                raise ModelError('Ya existe un modelo llamado "%s". Elige otro nombre o permite crear una versión nueva.'
                                 % clean_name)
            version = (existing[-1] + 1) if existing else 1
            joblib_path, json_path = _version_paths(directory, version)

            with open(model_path, 'rb') as f:
                payload = f.read()
            digest = hashlib.sha256(payload).hexdigest()
            info = dict(info or {})
            meta = {
                'format': MODEL_FORMAT, 'name': clean_name, 'owner': str(owner), 'version': version,
                'created': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                'description': str(description or '')[:500],
                'problem': info.get('problem'), 'features': list(info.get('features') or []),
                'classes': list(info.get('classes') or []), 'target': info.get('target'),
                'metrics': info.get('metrics') or {}, 'params': info.get('params') or {},
                'rows': info.get('rows'), 'size': len(payload), 'sha256': digest,
                'runtime': _runtime_versions(),
            }
            meta['signature'] = sign_meta(meta)

            # Escritura atómica: primero el modelo, al final los metadatos (sin ellos la versión no existe)
            tmp_model = _tmp_in(directory, '.joblib')
            tmp_meta = _tmp_in(directory, '.json')
            try:
                with open(tmp_model, 'wb') as f:
                    f.write(payload)
                    f.flush()
                    os.fsync(f.fileno())
                with open(tmp_meta, 'w', encoding='utf-8') as f:
                    json.dump(meta, f, ensure_ascii=False, indent=1, sort_keys=True)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp_model, joblib_path)
                os.replace(tmp_meta, json_path)
            finally:
                for leftover in (tmp_model, tmp_meta):
                    if os.path.exists(leftover):
                        os.remove(leftover)

            _prune(directory, version, on_existing)
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)
    return meta


def _tmp_in(directory, suffix):
    handle, path = tempfile.mkstemp(prefix='.tmp-', suffix=suffix, dir=directory)
    os.close(handle)
    return path


def _prune(directory, current, on_existing):
    """Borra versiones antiguas: todas con 'replace'; con 'version', las que sobren sobre el máximo configurado."""
    versions = _versions(directory)
    keep = int(getattr(plugin_settings, 'ETL_MODELS_KEEP_VERSIONS', 10) or 0)
    if on_existing == 'replace':
        doomed = [v for v in versions if v != current]
    elif keep > 0 and len(versions) > keep:
        doomed = versions[:len(versions) - keep]
    else:
        doomed = []
    for v in doomed:
        _delete_version_files(directory, v)


def _delete_version_files(directory, version):
    joblib_path, json_path = _version_paths(directory, version)
    for path in (json_path, joblib_path):             # primero los metadatos: la versión deja de existir de golpe
        try:
            os.remove(path)
        except FileNotFoundError:
            pass


# --------------------------------------------------------------------------
# Consultar y cargar
# --------------------------------------------------------------------------

def _read_meta_file(json_path):
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def summarize(meta):
    """Datos de un modelo que se muestran en el editor."""
    return {k: meta.get(k) for k in ('version', 'created', 'description', 'problem', 'features', 'classes',
                                     'target', 'metrics', 'rows', 'size')}


def list_models(owner):
    """Modelos de un usuario con el resumen de cada versión. Las versiones con firma inválida no se listan."""
    root = models_root()
    owner_dir = os.path.join(root, owner_dir_name(owner))
    result = []
    if not os.path.isdir(owner_dir):
        return result
    for name in sorted(os.listdir(owner_dir)):
        directory = os.path.join(owner_dir, name)
        if not os.path.isdir(directory) or not _inside(root, directory):
            continue
        versions = []
        for v in _versions(directory):
            meta = _read_meta_file(_version_paths(directory, v)[1])
            if meta and verify_meta(meta) and meta.get('owner') == str(owner) and meta.get('name') == name:
                versions.append(summarize(meta))
        if versions:
            result.append({'name': name, 'versions': versions})
    return result


def load_verified(owner, name, version=None):
    """
    Devuelve (bytes del modelo, metadatos) tras verificar hash y firma. version None o 'latest' = la
    más reciente. Es la ÚNICA vía para obtener los bytes que luego se deserializan.
    """
    directory = model_dir(owner, name)
    available = _versions(directory)
    if not available:
        raise ModelError('No existe el modelo "%s" del usuario %s. Guárdalo antes con el nodo "Guardar modelo".'
                         % (safe_model_name(name), owner))
    if version in (None, '', 'latest'):
        number = available[-1]
    else:
        try:
            number = int(version)
        except (TypeError, ValueError):
            raise ModelError('Versión de modelo no válida: %s.' % version)
        if number not in available:
            raise ModelError('El modelo "%s" no tiene la versión %s. Versiones: %s.'
                             % (safe_model_name(name), number, ', '.join(str(v) for v in available)))
    joblib_path, json_path = _version_paths(directory, number)
    meta = _read_meta_file(json_path)
    if not meta or meta.get('format') != MODEL_FORMAT:
        raise ModelError('Los metadatos del modelo "%s" (versión %d) no se pueden leer.' % (name, number))
    if (not verify_meta(meta) or meta.get('owner') != str(owner)
            or meta.get('name') != safe_model_name(name) or meta.get('version') != number):
        raise ModelError('El modelo "%s" (versión %d) no es de confianza: su firma no es válida, así que no se carga. '
                         'Guárdalo de nuevo desde un flujo de este servidor.' % (name, number))
    if os.path.islink(joblib_path):
        raise ModelError('El fichero del modelo "%s" no es válido.' % name)
    try:
        with open(joblib_path, 'rb') as f:
            payload = f.read()
    except OSError:
        raise ModelError('Falta el fichero del modelo "%s" (versión %d).' % (name, number))
    if hashlib.sha256(payload).hexdigest() != meta.get('sha256'):
        raise ModelError('El modelo "%s" (versión %d) está dañado o fue modificado: no coincide con su firma, '
                         'así que no se carga.' % (name, number))
    return payload, meta


def runtime_warnings(meta):
    """Avisos de compatibilidad entre el entorno que guardó el modelo y el actual."""
    saved, current = meta.get('runtime') or {}, _runtime_versions()
    warnings = []
    for lib, label in (('sklearn', 'scikit-learn'), ('numpy', 'numpy')):
        if saved.get(lib) and current.get(lib) and saved[lib] != current[lib]:
            warnings.append('El modelo se guardó con %s %s y el servidor tiene la %s. Si falla la predicción, '
                            'reentrénalo.' % (label, saved[lib], current[lib]))
    return warnings


# --------------------------------------------------------------------------
# Borrar
# --------------------------------------------------------------------------

def delete_model(owner, name, version=None):
    """Borra una versión (o el modelo entero si version es None). Devuelve cuántas versiones borró."""
    directory = model_dir(owner, name)
    available = _versions(directory)
    if not available:
        raise ModelError('No existe el modelo "%s".' % safe_model_name(name))
    if version in (None, ''):
        doomed = available
    else:
        try:
            number = int(version)
        except (TypeError, ValueError):
            raise ModelError('Versión de modelo no válida: %s.' % version)
        if number not in available:
            raise ModelError('El modelo "%s" no tiene la versión %s.' % (safe_model_name(name), number))
        doomed = [number]
    for v in doomed:
        _delete_version_files(directory, v)
    if not _versions(directory):
        shutil.rmtree(directory, ignore_errors=True)
        try:
            os.rmdir(os.path.dirname(directory))          # la carpeta del usuario, si se ha quedado vacía
        except OSError:
            pass
    return len(doomed)


# --------------------------------------------------------------------------
# Nodos
# --------------------------------------------------------------------------

def output_ModelSave(dicc):
    """Guarda el modelo conectado como una versión nueva del modelo con ese nombre. No tiene salidas."""
    from . import etl_raster as er
    model = next((d for d in dicc.get('data', []) if er.is_model_ref(d)), None)
    if not model:
        raise Exception('Conecta un modelo entrenado.')
    owner = dicc.get('_models_owner')
    if not owner:
        raise Exception('No se conoce el usuario propietario del modelo.')
    info = er.read_meta(model)
    meta = save_model(owner, dicc.get('model-name'), model, info, dicc.get('description'),
                      dicc.get('on-existing') or 'version')
    print('Modelo "%s" guardado como versión %d (%s, %d variables, %s).' % (
        meta['name'], meta['version'], meta['problem'], len(meta['features']),
        ', '.join('%s=%.3g' % kv for kv in sorted((meta.get('metrics') or {}).items())[:3]) or 'sin métricas'))
    return []


def input_Model(dicc):
    """Entrega un modelo guardado (verificado) como cualquier otro modelo del flujo."""
    from . import etl_raster as er
    owner = dicc.get('_models_owner')
    if not owner:
        raise Exception('No se conoce el usuario propietario del modelo.')
    if not dicc.get('model-name'):
        raise Exception('Elige el modelo guardado que quieres usar.')
    payload, meta = load_verified(owner, dicc.get('model-name'), dicc.get('model-version') or 'latest')
    for warning in runtime_warnings(meta):
        print('AVISO: ' + warning)
    path = er.new_artifact_path(dicc['id'], er.MODEL_EXTENSION)
    with open(path, 'wb') as f:
        f.write(payload)
    er.write_meta(path, {k: meta.get(k) for k in ('problem', 'features', 'classes', 'target', 'metrics', 'params', 'rows')})
    print('Modelo "%s" versión %d (%s, entrenado el %s).' % (meta['name'], meta['version'], meta['problem'], meta['created']))
    return [path]
