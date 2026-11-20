from urllib.parse import quote


def sizeof_fmt(num):
    """
    Format file sizes for a humans beings.
    http://stackoverflow.com/questions/1094841/reusable-library-to-get-human-readable-version-of-file-size
    """
    for x in ['bytes', 'KB', 'MB', 'GB']:
        if num < 1024.0 and num > -1024.0:
            return "%3.1f %s" % (num, x)
        num /= 1024.0
    return "%3.1f %s" % (num, 'TB')


def export_redirect(base, rel_path):
    """URL de la aplicación con ?path= codificado (la ruta lleva nombres de ficheros del usuario)."""
    return base + quote(rel_path or '', safe='/')


def safe_redirect(url):
    """La URL guardada en el historial solo si es una ruta de esta aplicación ('/...', no '//...')."""
    if isinstance(url, str) and url.startswith('/') and not url.startswith('//') and not url.startswith('/\\'):
        return url
    return ''
