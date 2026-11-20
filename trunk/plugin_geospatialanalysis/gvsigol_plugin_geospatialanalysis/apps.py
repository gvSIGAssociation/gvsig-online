# -*- coding: utf-8 -*-
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class GvsigolGeospatialAnalysisConfig(AppConfig):
    name = 'gvsigol_plugin_geospatialanalysis'
    verbose_name = _("Análisis geoespacial")
    label = "gvsigol_plugin_geospatialanalysis"
