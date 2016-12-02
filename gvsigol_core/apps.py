from __future__ import unicode_literals

from django.apps import AppConfig


class GvsigolCoreConfig(AppConfig):
    name = 'gvsigol_core'

    def ready(self):
        try:
            # ensure we have a proper environment
            self.config_gdaltools()
        except:
            pass

    def config_gdaltools(self):
        import gdaltools
        from gvsigol.settings import GDALTOOLS_BASEPATH
        if GDALTOOLS_BASEPATH != '':
            gdaltools.Wrapper.BASEPATH = GDALTOOLS_BASEPATH
