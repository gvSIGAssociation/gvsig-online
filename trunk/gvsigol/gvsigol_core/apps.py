

from django.apps import AppConfig
import logging


class GvsigolCoreConfig(AppConfig):
    name = 'gvsigol_core'
    label = 'gvsigol_core'

    def ready(self):
        from actstream import registry
        registry.register(self.get_model('Project'))

        try:
            # ensure we have a proper environment
            self.config_gdaltools()
        except:
            pass
        try:
            from gvsigol.celery import debug_loggers
            # debug Celery loggers behaviour in gvsigol startup
            debug_loggers.apply_async()
        except:
            logging.getLogger('gvsigol').exception("Error in debug_environment task")

    def config_gdaltools(self):
        from gvsigol import settings
        import gdaltools
        GDALTOOLS_BASEPATH = getattr(settings, 'GDALTOOLS_BASEPATH', '')
        if GDALTOOLS_BASEPATH:
            gdaltools.Wrapper.BASEPATH = GDALTOOLS_BASEPATH
        GDALTOOLS_CMD_PREFIX = getattr(settings, 'GDALTOOLS_CMD_PREFIX', '')
        if GDALTOOLS_CMD_PREFIX:
            gdaltools.Wrapper.CMD_PREFIX = GDALTOOLS_CMD_PREFIX
