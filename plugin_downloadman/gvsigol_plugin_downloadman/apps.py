# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.apps import AppConfig

PLUGIN_NAME = 'gvsigol_plugin_downloadman'

class GvsigolDownloadManConfig(AppConfig):
    name = PLUGIN_NAME
    verbose_name = "Download Manager"
    label = "gvsigol_plugin_downloadman"

    def ready(self):
        from actstream import registry
        registry.register(self.get_model('LayerProxy'))
        registry.register(self.get_model('LayerResourceProxy'))
