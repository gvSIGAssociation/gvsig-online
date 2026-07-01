# -*- coding: utf-8 -*-
"""Read-only introspection of the runtime application environment.

The information shown here comes from a fixed set of files and commands that are
hard-coded in this module; there is no user input at any point. The emphasis is
therefore on *operational robustness* (a missing/failing command or file must
never break the page) rather than on defending against injection, which is not
possible without untrusted input.

Notes
-----
* **Files** are read from a small fixed allowlist (:data:`_ALLOWED_FILES`). This
  is mostly a guardrail so future edits cannot accidentally turn this into an
  arbitrary-file reader; with today's literal paths it is not strictly needed.
* **Commands** run with a fixed argument vector and ``shell=False``. That alone
  makes command/argument injection impossible. Each command additionally has a
  wall-clock timeout, capped output, ``stdin`` redirected to ``/dev/null`` and
  broad exception handling -- these are for robustness, not security.
* **Encoding**: command output and file contents are read as *bytes* and decoded
  as UTF-8 with ``errors='replace'``, so non-UTF-8 data degrades to U+FFFD
  instead of raising.
* **Escaping**: HTML/JavaScript escaping is handled entirely by Django's
  template auto-escaping (no ``|safe`` is used in the template). :func:`_clean_text`
  only strips control characters so external output renders cleanly; it is not
  an XSS defense.
"""

import locale
import logging
import os
import platform
import re
import subprocess
import sys

logger = logging.getLogger(__name__)

# Hard limits (defensive against huge / hostile output).
MAX_OUTPUT_BYTES = 256 * 1024
MAX_FILE_BYTES = 256 * 1024
COMMAND_TIMEOUT = 15

# Absolute paths this module is allowed to read (guardrail against future edits).
_ALLOWED_FILES = frozenset({
    '/etc/os-release',
    '/proc/meminfo',
})

# Strip C0/C1-ish control characters except tab (\x09), newline (\x0a) and
# carriage return (\x0d) so external output stays renderable.
_CONTROL_CHARS_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')

# "  <driver> -<types>- (<caps>): <description>" as printed by
# ``ogr2ogr --formats`` / ``gdalinfo --formats``.
_FORMAT_LINE_RE = re.compile(
    r'^\s+(?P<driver>.+?)\s+-(?P<types>[^-]+)-\s+\((?P<caps>[^)]+)\):'
)

# libgdal dependency line in ``ldd`` output, e.g.:
#   libgdal.so.34 => /lib/x86_64-linux-gnu/libgdal.so.34 (0x00007f...)
_LDD_GDAL_RE = re.compile(r'(libgdal[^\s]*)\s*=>\s*(\S+)')


# --------------------------------------------------------------------------- #
# Low level primitives
# --------------------------------------------------------------------------- #
def _clean_text(value):
    """Coerce ``value`` to ``str`` and strip control characters.

    This is **not** an XSS defense -- HTML/JavaScript escaping is done by
    Django's template auto-escaping. It only removes control characters (NUL,
    ANSI escape sequences, ...) so that output coming from external commands,
    files or C libraries renders cleanly, and it decodes ``bytes`` returned by
    those C libraries.
    """
    if value is None:
        return ''
    if isinstance(value, bytes):
        value = value.decode('utf-8', errors='replace')
    elif not isinstance(value, str):
        try:
            value = str(value)
        except Exception:
            return ''
    return _CONTROL_CHARS_RE.sub('', value)


def _human_bytes(num):
    try:
        num = float(num)
    except (TypeError, ValueError):
        return 'unknown'
    for unit in ('B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB'):
        if abs(num) < 1024.0:
            return '%.2f %s' % (num, unit)
        num /= 1024.0
    return '%.2f EiB' % num


def _run_command(argv, timeout=COMMAND_TIMEOUT):
    """Run a fixed command (no shell) and capture combined stdout/stderr.

    ``argv`` is always a hard-coded list defined in this module. With no user
    input, ``shell=False`` plus a fixed argument vector is all that is needed to
    make command/argument injection impossible; the timeout, output cap,
    ``DEVNULL`` stdin and exception handling are about robustness.
    """
    result = {'argv': list(argv), 'ok': False, 'output': '',
              'error': '', 'returncode': None}
    try:
        completed = subprocess.run(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            shell=False,
            check=False,
        )
    except FileNotFoundError:
        result['error'] = 'Command not found'
        return result
    except PermissionError:
        result['error'] = 'Command not executable'
        return result
    except subprocess.TimeoutExpired:
        result['error'] = 'Command timed out after %ss' % timeout
        return result
    except (OSError, ValueError):
        result['error'] = 'Command failed to execute'
        return result
    except Exception:
        logger.exception('Unexpected error running environment command')
        result['error'] = 'Command failed to execute'
        return result

    raw = completed.stdout or b''
    text = _clean_text(raw[:MAX_OUTPUT_BYTES])
    if len(raw) > MAX_OUTPUT_BYTES:
        text += '\n... [output truncated] ...'
    result['output'] = text
    result['returncode'] = completed.returncode
    result['ok'] = completed.returncode == 0
    return result


def _read_allowed_file(path):
    """Read a file, but only if it is on the fixed allowlist."""
    result = {'path': path, 'ok': False, 'content': '', 'error': ''}
    if path not in _ALLOWED_FILES:
        result['error'] = 'File not allowed'
        return result
    try:
        # Only proceed for regular files (avoids fifos/devices/dirs).
        if not os.path.isfile(path):
            result['error'] = 'File not found'
            return result
        with open(path, 'rb') as handle:
            raw = handle.read(MAX_FILE_BYTES + 1)
    except FileNotFoundError:
        result['error'] = 'File not found'
        return result
    except PermissionError:
        result['error'] = 'File not readable'
        return result
    except (OSError, ValueError):
        result['error'] = 'File could not be read'
        return result
    except Exception:
        logger.exception('Unexpected error reading %s', path)
        result['error'] = 'Unexpected error reading file'
        return result

    content = _clean_text(raw[:MAX_FILE_BYTES])
    if len(raw) > MAX_FILE_BYTES:
        content += '\n... [content truncated] ...'
    result['content'] = content
    result['ok'] = True
    return result


def _parse_formats(stdout):
    """Parse ``--formats`` output (already cleaned) into a sorted driver list."""
    drivers = []
    for line in (stdout or '').splitlines():
        match = _FORMAT_LINE_RE.match(line)
        if match:
            drivers.append({
                'name': match.group('driver').strip(),
                'types': match.group('types').strip(),
                'capabilities': match.group('caps').strip(),
            })
    drivers.sort(key=lambda item: item['name'].lower())
    return drivers


def _list_bundled_libraries(module):
    """Best-effort listing of native shared libraries bundled with a wheel.

    Handles the common ``auditwheel`` layout (``<pkg>.libs`` sibling dir), the
    ``delocate`` layout (``<pkg>/.dylibs``) and shared objects living directly
    inside the package directory.
    """
    libraries = []
    seen = set()
    try:
        pkg_dir = os.path.dirname(os.path.abspath(module.__file__))
    except Exception:
        return libraries

    parent = os.path.dirname(pkg_dir)
    base = os.path.basename(pkg_dir)
    search_dirs = [
        os.path.join(parent, base + '.libs'),  # auditwheel (Linux)
        os.path.join(pkg_dir, '.dylibs'),      # delocate (macOS)
    ]
    for directory in search_dirs:
        try:
            if not os.path.isdir(directory):
                continue
            for name in sorted(os.listdir(directory)):
                full = os.path.join(directory, name)
                if os.path.isfile(full) and full not in seen:
                    seen.add(full)
                    libraries.append({'name': name, 'path': full})
        except Exception:
            continue

    try:
        for name in sorted(os.listdir(pkg_dir)):
            if ('.so' in name) or name.endswith('.dll') or name.endswith('.pyd') \
                    or name.endswith('.dylib'):
                full = os.path.join(pkg_dir, name)
                if os.path.isfile(full) and full not in seen:
                    seen.add(full)
                    libraries.append({'name': name, 'path': full})
    except Exception:
        pass
    return libraries


# --------------------------------------------------------------------------- #
# Individual information collectors
# --------------------------------------------------------------------------- #
def get_os_release():
    """Contents of ``/etc/os-release`` (allowlisted)."""
    return _read_allowed_file('/etc/os-release')


def get_lsb_release():
    """Output of ``lsb_release -a`` (fixed arguments, no shell)."""
    return _run_command(['lsb_release', '-a'])


def get_memory_info():
    """Total system RAM, from ``/proc/meminfo`` with a ``sysconf`` fallback."""
    info = {
        'total_bytes': None,
        'total_human': 'unknown',
        'source': None,
        'error': '',
    }
    meminfo = _read_allowed_file('/proc/meminfo')
    if meminfo['ok']:
        for line in meminfo['content'].splitlines():
            if line.startswith('MemTotal:'):
                parts = line.split()
                try:
                    kib = int(parts[1])
                    info['total_bytes'] = kib * 1024
                    info['total_human'] = _human_bytes(kib * 1024)
                    info['source'] = '/proc/meminfo'
                except (IndexError, ValueError):
                    pass
                break
    if info['total_bytes'] is None:
        try:
            page_size = os.sysconf('SC_PAGE_SIZE')
            phys_pages = os.sysconf('SC_PHYS_PAGES')
            total = page_size * phys_pages
            info['total_bytes'] = total
            info['total_human'] = _human_bytes(total)
            info['source'] = 'os.sysconf'
        except (ValueError, OSError, AttributeError):
            info['error'] = 'Total RAM could not be determined'
    return info


def get_system_info():
    """Basic OS/machine information from :mod:`platform`."""
    data = {}
    try:
        uname = platform.uname()
        data['system'] = uname.system
        data['node'] = uname.node
        data['release'] = uname.release
        data['version'] = uname.version
        data['machine'] = uname.machine
        data['processor'] = uname.processor
    except Exception:
        data['error'] = 'System information unavailable'
    try:
        data['cpu_count'] = os.cpu_count()
    except Exception:
        data['cpu_count'] = None
    return data


def _detect_python_executable():
    """Best-effort path to the *real* Python interpreter.

    Under application servers such as uWSGI, ``sys.executable`` points at the
    server binary (e.g. ``/usr/local/bin/uwsgi``), not at Python. In that case
    we look for a ``python`` binary in the environment's ``bin`` directory.
    """
    def _is_python(path):
        return bool(path) and 'python' in os.path.basename(path).lower() \
            and os.path.isfile(path)

    if _is_python(sys.executable):
        return sys.executable
    base_exec = getattr(sys, '_base_executable', None)
    if _is_python(base_exec):
        return base_exec

    version = '%d.%d' % (sys.version_info[0], sys.version_info[1])
    names = ['python%s' % version, 'python%d' % sys.version_info[0], 'python']
    bindirs = []
    try:
        import sysconfig
        scripts = sysconfig.get_path('scripts')
        if scripts:
            bindirs.append(scripts)
    except Exception:
        pass
    for prefix in (sys.prefix, sys.base_prefix, getattr(sys, 'exec_prefix', '')):
        if prefix:
            bindirs.append(os.path.join(prefix, 'bin'))
    for bindir in bindirs:
        for name in names:
            candidate = os.path.join(bindir, name)
            if os.path.isfile(candidate):
                return candidate
    return sys.executable or 'unknown'


def _detect_application_server():
    """Best-effort identification of the WSGI/application server in use."""
    try:
        import uwsgi  # type: ignore  # provided only inside a uWSGI worker
        try:
            raw = uwsgi.version
            version = raw.decode() if isinstance(raw, bytes) else str(raw)
        except Exception:
            version = ''
        return ('uWSGI %s' % version).strip()
    except Exception:
        pass

    server_software = os.environ.get('SERVER_SOFTWARE', '')
    if 'gunicorn' in server_software.lower():
        return server_software
    if 'mod_wsgi' in sys.modules or 'mod_wsgi' in server_software.lower():
        return server_software or 'mod_wsgi'

    argv = ' '.join(sys.argv) if sys.argv else ''
    if 'runserver' in argv:
        return 'Django development server (runserver)'
    if 'daphne' in sys.modules:
        return 'Daphne (ASGI)'
    if 'uvicorn' in sys.modules:
        return 'Uvicorn (ASGI)'

    exe_base = os.path.basename(sys.executable or '')
    if exe_base and 'python' not in exe_base.lower():
        return exe_base
    if server_software:
        return server_software
    return 'unknown'


def get_python_info():
    """Details of the Python interpreter running the application."""
    data = {}
    accessors = {
        'version': lambda: sys.version,
        'version_short': platform.python_version,
        'implementation': platform.python_implementation,
        'process_executable': lambda: sys.executable or 'unknown',
        'real_executable': _detect_python_executable,
        'application_server': _detect_application_server,
        'prefix': lambda: sys.prefix,
        'platform': platform.platform,
    }
    for key, func in accessors.items():
        try:
            data[key] = func()
        except Exception:
            data[key] = 'unknown'
    return data


def get_locale_info():
    """Locale and character-encoding configuration of the running process.

    This information used to be written to the gvsigol startup log; it is
    surfaced here instead.
    """
    data = {'env': {}}
    try:
        data['stdout_encoding'] = getattr(sys.stdout, 'encoding', None) or 'unknown'
    except Exception:
        data['stdout_encoding'] = 'unknown'
    try:
        data['stderr_encoding'] = getattr(sys.stderr, 'encoding', None) or 'unknown'
    except Exception:
        data['stderr_encoding'] = 'unknown'
    try:
        data['filesystem_encoding'] = sys.getfilesystemencoding() or 'unknown'
    except Exception:
        data['filesystem_encoding'] = 'unknown'
    try:
        data['preferred_encoding'] = locale.getpreferredencoding(False)
    except Exception:
        data['preferred_encoding'] = 'unknown'
    try:
        data['default_locale'] = str(locale.getdefaultlocale())
    except Exception:
        data['default_locale'] = 'unknown'
    for key in ('LANG', 'LANGUAGE', 'LC_ALL', 'LC_CTYPE',
                'PYTHONIOENCODING', 'PYTHONUTF8'):
        try:
            data['env'][key] = _clean_text(os.environ.get(key) or '')
        except Exception:
            data['env'][key] = ''
    return data


def get_installed_packages():
    """List installed distributions (``pip freeze``-like) for the running env.

    Uses :mod:`importlib.metadata` in-process instead of shelling out to
    ``pip``. This is both more robust and necessary under application servers
    such as uWSGI, where ``sys.executable`` points at the server binary and
    ``<executable> -m pip`` fails ("unable to load configuration from pip").
    """
    result = {'ok': False, 'source': 'importlib.metadata', 'output': '', 'error': ''}
    try:
        try:
            from importlib import metadata as importlib_metadata
        except ImportError:
            import importlib_metadata  # type: ignore

        packages = {}
        for dist in importlib_metadata.distributions():
            name = None
            try:
                name = dist.metadata['Name']
            except Exception:
                name = None
            if not name:
                name = getattr(dist, 'name', None)
            if not name:
                continue
            try:
                version = dist.version or ''
            except Exception:
                version = ''
            packages[str(name)] = str(version)

        if not packages:
            result['error'] = 'No installed distributions found'
            return result

        lines = [
            ('%s==%s' % (name, version)) if version else name
            for name, version in sorted(packages.items(), key=lambda kv: kv[0].lower())
        ]
        result['output'] = _clean_text('\n'.join(lines))
        result['ok'] = True
    except Exception:
        logger.exception('Failed to list installed packages')
        result['error'] = 'Installed packages could not be listed'
    return result


def _formats_via_binary(command_path):
    """Run ``<binary> --formats`` for a pygdaltools-resolved binary path.

    Only executes a real, existing regular file (defends against unusual
    ``CMD_PREFIX`` values that would need shell semantics).
    """
    if not command_path:
        return None
    try:
        path_str = str(command_path)
    except Exception:
        return None
    if not os.path.isfile(path_str):
        return None
    result = _run_command([path_str, '--formats'])
    if not result.get('ok'):
        return None
    return _parse_formats(result.get('output', ''))


def get_pygdaltools_gdal():
    """GDAL environment as seen by pygdaltools (external CLI binaries).

    The pygdaltools wrappers are read as-is: their ``BASEPATH`` / ``CMD_PREFIX``
    are already configured by gvsigol at startup (see
    ``gvsigol_core.apps.config_gdaltools``), so this module never touches that
    configuration to avoid interfering with the startup logic.
    """
    data = {
        'available': False,
        'version': 'unknown',
        'ogr_command_path': 'unknown',
        'gdalinfo_command_path': 'unknown',
        'vector_drivers': [],
        'raster_drivers': [],
        'error': '',
        'notes': 'GEOS/PROJ versions are not reported by the GDAL command-line tools.',
    }
    try:
        import gdaltools
    except Exception:
        data['error'] = 'pygdaltools (gdaltools) is not importable'
        return data

    ogr_cmd = None
    try:
        ogr = gdaltools.ogr2ogr()
        try:
            version_tuple = ogr.get_version_tuple()
            if version_tuple:
                major, minor, patch, prerelease = version_tuple
                version = '%s.%s.%s' % (major, minor, patch)
                if prerelease:
                    version = '%s %s' % (version, prerelease)
                data['version'] = version
                data['available'] = True
        except Exception:
            data['error'] = 'Could not obtain GDAL version from pygdaltools'
        try:
            ogr_cmd = ogr._get_command()
            data['ogr_command_path'] = str(ogr_cmd)
        except Exception:
            pass
    except Exception:
        if not data['error']:
            data['error'] = 'pygdaltools ogr2ogr wrapper failed'

    vector_formats = _formats_via_binary(ogr_cmd)
    if vector_formats:
        data['vector_drivers'] = [
            drv for drv in vector_formats if 'vector' in drv['types']
        ]

    gdalinfo_cmd = None
    try:
        from gdaltools.gdalinfocmd import GdalInfo
        gdalinfo = GdalInfo()
        try:
            gdalinfo_cmd = gdalinfo._get_command()
            data['gdalinfo_command_path'] = str(gdalinfo_cmd)
        except Exception:
            pass
    except Exception:
        pass

    raster_formats = _formats_via_binary(gdalinfo_cmd)
    if raster_formats:
        data['raster_drivers'] = [
            drv for drv in raster_formats if 'raster' in drv['types']
        ]

    return data


def _loaded_library_paths():
    """Map ``basename -> absolute path`` for shared libraries mapped into this
    process, by reading ``/proc/self/maps`` (Linux). Returns ``{}`` on failure.
    """
    paths = {}
    try:
        with open('/proc/self/maps', 'r', errors='replace') as handle:
            for line in handle:
                # Format: address perms offset dev inode pathname
                parts = line.split(None, 5)
                if len(parts) < 6:
                    continue
                pathname = parts[5].strip()
                if not pathname or pathname.startswith('['):
                    continue
                if '.so' not in pathname:
                    continue
                paths.setdefault(os.path.basename(pathname), pathname)
    except Exception:
        return {}
    return paths


def _resolve_full_library_path(name_or_path):
    """Best-effort resolution of a soname to its absolute on-disk path.

    Django only knows the library by its soname (e.g. ``libgdal.so.32``) when it
    is located via ``ctypes.util.find_library``; the real path is recovered from
    the process' memory map.
    """
    if not name_or_path:
        return None
    try:
        candidate = str(name_or_path)
    except Exception:
        return None
    if os.path.isabs(candidate) and os.path.exists(candidate):
        return candidate
    base = os.path.basename(candidate)
    loaded = _loaded_library_paths()
    if base in loaded:
        return loaded[base]
    for lib_base, full in loaded.items():
        if lib_base.startswith(base) or base.startswith(lib_base):
            return full
    return None


def _gdal_version_from_lib(handle):
    """Return GDAL ``RELEASE_NAME`` from an arbitrary GDAL CDLL handle."""
    try:
        from ctypes import c_char_p
        func = getattr(handle, 'GDALVersionInfo', None)
        if func is None:
            return None
        func.argtypes = [c_char_p]
        func.restype = c_char_p
        value = func(b'RELEASE_NAME')
        if value:
            return value.decode('utf-8', 'replace')
    except Exception:
        return None
    return None


def _gdal_from_ldd(lib_path):
    """Resolve which ``libgdal`` a native library links against, via ``ldd``.

    ``ldd`` is run only on our own installed PDAL libraries (paths taken from
    this process' memory map or the ``pdal`` package directory), never on user
    input. Returns ``(soname, full_path)`` or ``(None, None)``.
    """
    if not lib_path or not os.path.isfile(lib_path):
        return None, None
    result = _run_command(['ldd', lib_path])
    if not result.get('ok'):
        return None, None
    for line in result['output'].splitlines():
        match = _LDD_GDAL_RE.search(line)
        if match:
            soname = match.group(1)
            path = match.group(2)
            if path and path.startswith('/'):
                return soname, path
    return None, None


def _proj_version_from_lib(handle):
    """Return the PROJ version string from a GDAL >= 3 CDLL handle, if exposed."""
    try:
        from ctypes import POINTER, byref, c_int
        func = getattr(handle, 'OSRGetPROJVersion', None)
        if func is None:
            return None
        func.argtypes = [POINTER(c_int), POINTER(c_int), POINTER(c_int)]
        func.restype = None
        major = c_int(0)
        minor = c_int(0)
        patch = c_int(0)
        func(byref(major), byref(minor), byref(patch))
        if major.value == 0 and minor.value == 0 and patch.value == 0:
            return None
        return '%d.%d.%d' % (major.value, minor.value, patch.value)
    except Exception:
        return None


def _drivers_from_lib(handle):
    """Enumerate raster (GDAL) and vector (OGR) drivers from a CDLL handle.

    Uses a *private* CDLL handle so we never mutate the ``argtypes`` of the
    function pointers Django itself relies on.
    """
    raster = []
    vector = []
    try:
        from ctypes import c_char_p, c_int, c_void_p

        try:
            handle.GDALAllRegister()
        except Exception:
            pass
        try:
            count = handle.GDALGetDriverCount
            count.restype = c_int
            get_driver = handle.GDALGetDriver
            get_driver.argtypes = [c_int]
            get_driver.restype = c_void_p
            short_name = handle.GDALGetDriverShortName
            short_name.argtypes = [c_void_p]
            short_name.restype = c_char_p
            for i in range(count()):
                driver = get_driver(i)
                if not driver:
                    continue
                name = short_name(driver)
                if name:
                    raster.append(name.decode('utf-8', 'replace'))
        except Exception:
            pass

        try:
            handle.OGRRegisterAll()
        except Exception:
            pass
        try:
            count = handle.OGRGetDriverCount
            count.restype = c_int
            get_driver = handle.OGRGetDriver
            get_driver.argtypes = [c_int]
            get_driver.restype = c_void_p
            drv_name = handle.OGR_Dr_GetName
            drv_name.argtypes = [c_void_p]
            drv_name.restype = c_char_p
            for i in range(count()):
                driver = get_driver(i)
                if not driver:
                    continue
                name = drv_name(driver)
                if name:
                    vector.append(name.decode('utf-8', 'replace'))
        except Exception:
            pass
    except Exception:
        pass
    return sorted(set(raster), key=str.lower), sorted(set(vector), key=str.lower)


def get_geodjango_gdal():
    """GDAL/GEOS/PROJ environment as seen by GeoDjango (in-process libraries)."""
    data = {
        'available': False,
        'gdal_version': 'unknown',
        'gdal_full_version': '',
        'library_path': 'unknown',
        'library_full_path': 'unknown',
        'library_path_source': 'unknown',
        'geos_version': 'unknown',
        'geos_library_path': 'unknown',
        'geos_library_full_path': 'unknown',
        'proj_version': 'unknown',
        'vector_drivers': [],
        'raster_drivers': [],
        'error': '',
    }

    lib_path = None
    try:
        from django.contrib.gis.gdal import libgdal
        data['available'] = True
        try:
            data['gdal_version'] = '.'.join(
                str(x) for x in libgdal.GDAL_VERSION if x is not None
            )
        except Exception:
            pass
        try:
            # bytes from the C library -> decode + clean.
            data['gdal_full_version'] = _clean_text(libgdal.gdal_full_version())
        except Exception:
            pass
        try:
            lib_path = libgdal.lib_path
            data['library_path'] = str(lib_path)
            full_path = _resolve_full_library_path(lib_path)
            if full_path:
                data['library_full_path'] = full_path
        except Exception:
            pass
    except Exception:
        data['error'] = 'GeoDjango GDAL is not importable'

    try:
        from django.conf import settings
        if getattr(settings, 'GDAL_LIBRARY_PATH', None):
            data['library_path_source'] = 'settings.GDAL_LIBRARY_PATH'
        else:
            data['library_path_source'] = 'django heuristic (ctypes.util.find_library)'
    except Exception:
        pass

    try:
        from django.contrib.gis.geos import libgeos
        try:
            # bytes from the C library -> decode + clean.
            data['geos_version'] = _clean_text(libgeos.geos_version())
        except Exception:
            pass
        try:
            geos_name = getattr(libgeos.lgeos, '_name', None)
            if geos_name:
                data['geos_library_path'] = str(geos_name)
                geos_full = _resolve_full_library_path(geos_name)
                if geos_full:
                    data['geos_library_full_path'] = geos_full
        except Exception:
            pass
    except Exception:
        pass

    if lib_path:
        handle = None
        try:
            from ctypes import CDLL
            handle = CDLL(str(lib_path))
        except Exception:
            handle = None
        if handle is not None:
            proj = _proj_version_from_lib(handle)
            if proj:
                data['proj_version'] = proj
            raster, vector = _drivers_from_lib(handle)
            data['raster_drivers'] = raster
            data['vector_drivers'] = vector

    return data


def get_pyogrio_info():
    """pyogrio version plus the native GDAL it embeds (bundled wheel)."""
    data = {
        'available': False,
        'version': 'unknown',
        'gdal_version': 'unknown',
        'gdal_version_string': '',
        'geos_version': 'unknown',
        'module_path': 'unknown',
        'bundled_libraries': [],
        'error': '',
    }
    try:
        import pyogrio
    except Exception:
        data['error'] = 'pyogrio is not importable'
        return data

    data['available'] = True
    try:
        data['version'] = getattr(pyogrio, '__version__', 'unknown')
    except Exception:
        pass
    try:
        gdal_version = getattr(pyogrio, '__gdal_version__', None)
        if isinstance(gdal_version, (tuple, list)):
            data['gdal_version'] = '.'.join(str(x) for x in gdal_version)
        elif gdal_version is not None:
            data['gdal_version'] = str(gdal_version)
    except Exception:
        pass
    try:
        data['gdal_version_string'] = getattr(pyogrio, '__gdal_version_string__', '')
    except Exception:
        pass
    try:
        geos_version = getattr(pyogrio, '__gdal_geos_version__', None)
        if isinstance(geos_version, (tuple, list)):
            data['geos_version'] = '.'.join(str(x) for x in geos_version)
        elif geos_version:
            data['geos_version'] = str(geos_version)
    except Exception:
        pass
    try:
        data['module_path'] = os.path.dirname(pyogrio.__file__)
    except Exception:
        pass
    data['bundled_libraries'] = _list_bundled_libraries(pyogrio)
    return data


def get_rasterio_info():
    """rasterio version plus the native GDAL/GEOS/PROJ it embeds (bundled wheel)."""
    data = {
        'available': False,
        'version': 'unknown',
        'gdal_version': 'unknown',
        'proj_version': 'unknown',
        'geos_version': 'unknown',
        'module_path': 'unknown',
        'bundled_libraries': [],
        'error': '',
    }
    try:
        import rasterio
    except Exception:
        data['error'] = 'rasterio is not importable'
        return data

    data['available'] = True
    for attr, key in (
        ('__version__', 'version'),
        ('__gdal_version__', 'gdal_version'),
        ('__proj_version__', 'proj_version'),
        ('__geos_version__', 'geos_version'),
    ):
        try:
            value = getattr(rasterio, attr, None)
            if value is not None:
                data[key] = str(value)
        except Exception:
            pass
    try:
        data['module_path'] = os.path.dirname(rasterio.__file__)
    except Exception:
        pass
    data['bundled_libraries'] = _list_bundled_libraries(rasterio)
    return data


def get_pdal_info():
    """PDAL version plus the GDAL it links against at runtime.

    On some distributions (e.g. RHEL 9) the GDAL used by PDAL is **not** the
    same as the one used by GeoDjango or pygdaltools. It is therefore resolved
    independently: the native ``libpdal`` is located, its ``libgdal`` dependency
    is discovered with ``ldd``, and that GDAL is then queried directly for its
    version and available vector/raster drivers.
    """
    data = {
        'available': False,
        'version': 'unknown',
        'library_path': 'unknown',
        'module_path': 'unknown',
        'gdal_version': 'unknown',
        'gdal_library_soname': 'unknown',
        'gdal_library_path': 'unknown',
        'vector_drivers': [],
        'raster_drivers': [],
        'error': '',
    }
    try:
        import pdal  # type: ignore  # optional native dependency
    except Exception:
        data['error'] = 'PDAL (python bindings) is not importable'
        return data

    data['available'] = True
    try:
        data['version'] = str(getattr(pdal, '__version__', 'unknown'))
    except Exception:
        pass
    try:
        data['module_path'] = os.path.dirname(pdal.__file__)
    except Exception:
        pass

    # Candidate native PDAL libraries: those mapped into the process plus any
    # shared objects shipped inside the ``pdal`` package.
    candidates = []
    for base, full in _loaded_library_paths().items():
        if 'pdal' in base.lower() and full not in candidates:
            candidates.append(full)
    try:
        for lib in _list_bundled_libraries(pdal):
            if lib['path'] not in candidates:
                candidates.append(lib['path'])
    except Exception:
        pass

    # Prefer the core libpdal (not the python extension) for display.
    for candidate in candidates:
        base = os.path.basename(candidate).lower()
        if base.startswith('libpdal') and 'python' not in base:
            data['library_path'] = candidate
            break
    else:
        if candidates:
            data['library_path'] = candidates[0]

    # Resolve PDAL's GDAL and query it directly.
    gdal_soname = gdal_path = None
    for candidate in candidates:
        gdal_soname, gdal_path = _gdal_from_ldd(candidate)
        if gdal_path:
            break

    if gdal_path:
        data['gdal_library_soname'] = gdal_soname or 'unknown'
        data['gdal_library_path'] = gdal_path
        handle = None
        try:
            from ctypes import CDLL
            handle = CDLL(gdal_path)
        except Exception:
            handle = None
        if handle is not None:
            version = _gdal_version_from_lib(handle)
            if version:
                data['gdal_version'] = version
            raster, vector = _drivers_from_lib(handle)
            data['raster_drivers'] = raster
            data['vector_drivers'] = vector
    else:
        data['error'] = (
            "Could not determine PDAL's GDAL (ldd unavailable or no libgdal "
            "dependency found)."
        )

    return data


def collect_environment():
    """Aggregate every environment section into a single dict for the template.

    Each collector is isolated so that a failure in one section never prevents
    the rest of the page from rendering.
    """
    collectors = (
        ('system', get_system_info),
        ('os_release', get_os_release),
        ('lsb_release', get_lsb_release),
        ('memory', get_memory_info),
        ('python', get_python_info),
        ('locale', get_locale_info),
        ('packages', get_installed_packages),
        ('pygdaltools', get_pygdaltools_gdal),
        ('geodjango', get_geodjango_gdal),
        ('pyogrio', get_pyogrio_info),
        ('rasterio', get_rasterio_info),
        ('pdal', get_pdal_info),
    )
    environment = {}
    for key, collector in collectors:
        try:
            environment[key] = collector()
        except Exception:
            logger.exception('Environment collector %s failed', key)
            environment[key] = {'error': 'Section could not be collected'}
    return environment
