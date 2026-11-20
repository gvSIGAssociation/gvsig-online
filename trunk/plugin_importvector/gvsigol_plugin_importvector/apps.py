# -*- coding: utf-8 -*-
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class GvsigolImportVectorConfig(AppConfig):
    name = 'gvsigol_plugin_importvector'
    verbose_name = _("Plugin for importing vector files")
    label = "gvsigol_plugin_importvector"
