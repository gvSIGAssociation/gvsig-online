# -*- coding: utf-8 -*-
"""
GTFS file handling for the trip planner.

  MEDIA_ROOT/data/plugin_trip_planner/
      sources/<provider_id>.zip   GTFS of every provider (downloaded or uploaded)
      GTFS/<provider_id>.zip      staging dir rebuilt before each graph build with the
                                  ACTIVE providers only. GTFS_SCRIPT reads it
                                  ($GTFS_DIR, or <base>/GTFS in gtfs_script.sh).
"""
import glob
import hashlib
import logging
import os
import shutil
import zipfile

from django.utils.translation import gettext as _

from gvsigol import settings

logger = logging.getLogger(__name__)

BASE_DIR = os.path.join('data', 'plugin_trip_planner')
# Minimum files of a valid GTFS feed (plus calendar.txt or calendar_dates.txt)
REQUIRED_FILES = ('agency.txt', 'stops.txt', 'routes.txt', 'trips.txt', 'stop_times.txt')
CALENDAR_FILES = ('calendar.txt', 'calendar_dates.txt')


def base_dir():
    return os.path.join(settings.MEDIA_ROOT, BASE_DIR)


def sources_dir():
    return os.path.join(base_dir(), 'sources')


def staging_dir():
    return os.path.join(base_dir(), 'GTFS')


def source_path(provider_id):
    return os.path.join(sources_dir(), '{0}.zip'.format(int(provider_id)))


def has_source(provider_id):
    return os.path.exists(source_path(provider_id))


def validate_gtfs_zip(fileobj):
    """Raise ValueError (translated message) if fileobj is not a GTFS zip."""
    try:
        with zipfile.ZipFile(fileobj) as zf:
            names = {os.path.basename(n) for n in zf.namelist() if not n.endswith('/')}
            bad = zf.testzip()
    except zipfile.BadZipFile:
        raise ValueError(_('The file is not a valid zip file.'))
    finally:
        if hasattr(fileobj, 'seek'):
            fileobj.seek(0)
    if bad:
        raise ValueError(_('The zip file is corrupted (%(name)s).') % {'name': bad})
    missing = [f for f in REQUIRED_FILES if f not in names]
    if not any(f in names for f in CALENDAR_FILES):
        missing.append(' / '.join(CALENDAR_FILES))
    if missing:
        raise ValueError(_('This is not a GTFS feed. Missing files: %(files)s') % {'files': ', '.join(missing)})


def save_uploaded(provider_id, uploaded_file):
    """Store an uploaded GTFS as the provider source (atomic replace)."""
    os.makedirs(sources_dir(), exist_ok=True)
    dst = source_path(provider_id)
    tmp = dst + '.tmp'
    with open(tmp, 'wb') as out:
        for chunk in uploaded_file.chunks():
            out.write(chunk)
    os.replace(tmp, dst)


def delete_source(provider_id):
    for path in (source_path(provider_id),
                 os.path.join(staging_dir(), '{0}.zip'.format(int(provider_id)))):
        try:
            os.remove(path)
        except FileNotFoundError:
            pass


def migrate_legacy_file(provider_id):
    """Before 'sources/' existed, files were downloaded directly into GTFS/<id>.zip."""
    legacy = os.path.join(staging_dir(), '{0}.zip'.format(int(provider_id)))
    if not has_source(provider_id) and os.path.exists(legacy):
        os.makedirs(sources_dir(), exist_ok=True)
        shutil.copy2(legacy, source_path(provider_id))


def sync_staging(provider_ids):
    """Leave in GTFS/ exactly the sources of provider_ids. Returns the staged ids."""
    os.makedirs(staging_dir(), exist_ok=True)
    wanted = {'{0}.zip'.format(int(i)): int(i) for i in provider_ids if has_source(i)}
    for path in glob.glob(os.path.join(staging_dir(), '*.zip')):
        if os.path.basename(path) not in wanted:
            os.remove(path)
    for name, pid in wanted.items():
        src = source_path(pid)
        dst = os.path.join(staging_dir(), name)
        st = os.stat(src)
        if os.path.exists(dst):
            dt = os.stat(dst)
            if dt.st_size == st.st_size and dt.st_mtime_ns == st.st_mtime_ns:
                continue
        shutil.copy2(src, dst + '.tmp')
        os.replace(dst + '.tmp', dst)
    return sorted(wanted.values())


def signature(provider_ids):
    """Fingerprint of the active GTFS set: changes when a file is added, removed or modified."""
    h = hashlib.sha256()
    for pid in sorted(int(i) for i in provider_ids):
        if has_source(pid):
            st = os.stat(source_path(pid))
            h.update('{0}:{1}:{2};'.format(pid, st.st_size, st.st_mtime_ns).encode())
    return h.hexdigest()
