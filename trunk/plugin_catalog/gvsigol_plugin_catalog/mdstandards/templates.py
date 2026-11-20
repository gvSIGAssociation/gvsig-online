# -*- coding: utf-8 -*-
"""Resolve metadata XML templates from client apps or the plugin defaults."""
import os

from django.apps import apps
from gvsigol.settings import BASE_DIR


def plugin_mdtemplate(filename):
    module_dir = os.path.dirname(__file__)
    return os.path.abspath(os.path.join(module_dir, '..', 'mdtemplates', filename))


def find_app_mdtemplate(filename):
    """
    Look for mdtemplates/<filename> in any installed gvsigol_app_*.

    Tries BASE_DIR/<app.name>/... first (historical layout) and then Django's
    app.path, which is where the package actually lives.
    """
    for app in apps.get_app_configs():
        if 'gvsigol_app_' not in app.name:
            continue
        candidates = [
            os.path.join(BASE_DIR, app.name, 'mdtemplates', filename),
            os.path.join(getattr(app, 'path', '') or '', 'mdtemplates', filename),
        ]
        for path in candidates:
            if path and os.path.isfile(path):
                return path
    return None


def resolve_mdtemplate(preferred_names, plugin_fallback):
    for name in preferred_names:
        found = find_app_mdtemplate(name)
        if found:
            return found
    return plugin_fallback
