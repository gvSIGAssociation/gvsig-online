# -*- coding: utf-8 -*-
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class GvsigolPanelsConfig(AppConfig):
    name = 'gvsigol_plugin_panels'
    verbose_name = _("Paneles")
    label = "gvsigol_plugin_panels"
