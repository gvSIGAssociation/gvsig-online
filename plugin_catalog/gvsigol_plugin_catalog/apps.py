# -*- coding: utf-8 -*-

from django.apps import AppConfig

class GvsigolCatalogConfig(AppConfig):
    name = 'gvsigol_plugin_catalog'
    verbose_name = "Catálogo"
    label = "gvsigol_plugin_catalog"

    def ready(self):
        from gvsigol_plugin_catalog.service import geonetwork_service