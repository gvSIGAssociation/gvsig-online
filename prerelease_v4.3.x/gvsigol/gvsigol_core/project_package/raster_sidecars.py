# -*- coding: utf-8 -*-
import hashlib
import os

def collect_sidecar_paths(primary_path):
    """
    Given a primary raster file path, return a list of absolute paths for the primary
    plus ALL regular files in the same directory that share the same stem (basename
    without extension), regardless of extension or count.
    """
    if not primary_path or not os.path.isfile(primary_path):
        return []
    primary_abs = os.path.abspath(primary_path)
    directory = os.path.dirname(primary_abs)
    stem_lower = os.path.splitext(os.path.basename(primary_abs))[0].lower()
    results = [primary_abs]
    try:
        names = os.listdir(directory)
    except OSError:
        return results
    for name in names:
        path = os.path.abspath(os.path.join(directory, name))
        if path == primary_abs:
            continue
        if os.path.splitext(name)[0].lower() == stem_lower and os.path.isfile(path):
            results.append(path)
    return sorted(set(results))


def sha256_file(path, chunk=1024 * 1024):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def build_sidecar_manifest(paths):
    return [
        {
            'path': p,
            'name': os.path.basename(p),
            'size': os.path.getsize(p),
            'sha256': sha256_file(p),
        }
        for p in paths
    ]


def extract_primary_raster_path_from_connection_params(params):
    """
    Best-effort: GeoTIFF / ImageMosaic stores often use 'url' or 'location' style keys in JSON.
    Returns absolute path if file exists, else None.
    """
    if not isinstance(params, dict):
        return None
    for key in ('url', 'URL', 'location', 'path', 'filepath'):
        val = params.get(key)
        if not val:
            continue
        if isinstance(val, str) and val.startswith('file:'):
            val = val[5:]
        if isinstance(val, str) and os.path.isfile(val):
            return val
    # Sometimes nested
    nested = params.get('coverageName') or params.get('directory')
    if isinstance(nested, str) and os.path.isdir(nested):
        for name in os.listdir(nested):
            low = name.lower()
            if low.endswith('.tif') or low.endswith('.tiff'):
                p = os.path.join(nested, name)
                if os.path.isfile(p):
                    return p
    return None


def copy_sidecar_tree(paths, dest_dir):
    os.makedirs(dest_dir, exist_ok=True)
    copied = []
    for p in paths:
        dest = os.path.join(dest_dir, os.path.basename(p))
        with open(p, 'rb') as src, open(dest, 'wb') as dst:
            dst.write(src.read())
        copied.append(dest)
    return copied
