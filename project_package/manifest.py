# -*- coding: utf-8 -*-
import hashlib
import json
import os
import zipfile

from gvsigol_core.project_package.constants import (
    MANIFEST_PATH,
    PACKAGE_FORMAT_VERSION,
    PACKAGE_FORMAT_VERSION_MAX,
    PACKAGE_FORMAT_VERSION_MIN,
)


def _parse_semver(s):
    parts = str(s).split('.')
    return tuple(int(x) for x in parts[:3])


def is_compatible_version(version_str):
    try:
        v = _parse_semver(version_str)
    except Exception:
        return False
    return PACKAGE_FORMAT_VERSION_MIN <= v < PACKAGE_FORMAT_VERSION_MAX  # e.g. 1.x only


def compute_inventory(root_dir, exclude_relative=None):
    exclude_relative = set(exclude_relative or [])
    exclude_relative.add(MANIFEST_PATH)
    inventory = []
    for dirpath, _, filenames in os.walk(root_dir):
        for fn in filenames:
            abs_path = os.path.join(dirpath, fn)
            rel = os.path.relpath(abs_path, root_dir).replace(os.sep, '/')
            if rel in exclude_relative:
                continue
            h = hashlib.sha256()
            with open(abs_path, 'rb') as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b''):
                    h.update(chunk)
            inventory.append({
                'path': rel,
                'media_type': 'application/octet-stream',
                'size': os.path.getsize(abs_path),
                'sha256': h.hexdigest(),
            })
    return sorted(inventory, key=lambda x: x['path'])


def verify_manifest_against_dir(manifest, root_dir):
    errors = []
    inv = manifest.get('inventory') or []
    for item in inv:
        rel = item['path']
        path = os.path.join(root_dir, rel.replace('/', os.sep))
        if not os.path.isfile(path):
            errors.append('missing_file:%s' % rel)
            continue
        h = hashlib.sha256()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b''):
                h.update(chunk)
        if h.hexdigest() != item.get('sha256'):
            errors.append('checksum_mismatch:%s' % rel)
        if os.path.getsize(path) != item.get('size'):
            errors.append('size_mismatch:%s' % rel)
    return errors


def read_manifest_from_zip(zip_path):
    with zipfile.ZipFile(zip_path, 'r') as zf:
        try:
            raw = zf.read(MANIFEST_PATH)
        except KeyError:
            raise ValueError('Invalid package: missing %s' % MANIFEST_PATH)
        return json.loads(raw.decode('utf-8'))


def read_manifest_from_extracted(extract_dir):
    path = os.path.join(extract_dir, MANIFEST_PATH.replace('/', os.sep))
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def build_base_manifest(project_name, export_options, inventory, capabilities_required=None):
    from gvsigol import settings

    return {
        'package_format_version': PACKAGE_FORMAT_VERSION,
        'source_base_url': getattr(settings, 'BASE_URL', ''),
        'project': {
            'name': project_name,
            'export_options': export_options,
        },
        'inventory': inventory,
        'capabilities_required': capabilities_required or {},
    }
