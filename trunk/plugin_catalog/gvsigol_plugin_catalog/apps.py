# -*- coding: utf-8 -*-

from django.apps import AppConfig

class GvsigolCatalogConfig(AppConfig):
    name = 'gvsigol_plugin_catalog'
    verbose_name = "Catálogo"
    label = "gvsigol_plugin_catalog"

    def ready(self):
        # Ensure GeoNetwork signal handlers (layer create/update/delete) are connected
        # even if catalog URLs/views have not been imported yet in this worker.
        try:
            import gvsigol_plugin_catalog.service  # noqa: F401
        except Exception:
            import logging
            logging.getLogger('gvsigol').exception(
                'Failed to initialize gvsigol_plugin_catalog service/signals'
            )
