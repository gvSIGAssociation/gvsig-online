# -*- coding: utf-8 -*-
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class GvsigolImportFromServiceConfig(AppConfig):
    name = 'gvsigol_plugin_importfromservice'
    verbose_name = _("Plugin for importing layers from an external service")
    label = "gvsigol_plugin_importfromservice"