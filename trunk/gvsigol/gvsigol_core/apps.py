

from django.apps import AppConfig
import sys
import os
import locale
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
        from gvsigol_core.utils import is_gvsigol_process, is_shell_process
        from gvsigol.celery import is_celery_process
        if is_gvsigol_process() or is_shell_process() or is_celery_process():
            self.output_locale_conf()
            self.output_gdal_version()
        try:
            from gvsigol.celery import debug_loggers
            # debug Celery loggers behaviour in gvsigol startup
            debug_loggers.apply_async()
        except:
            logging.getLogger('gvsigol').exception("Error in debug_environment task")

    def output_gdal_version(self):
        try:
            try:
                import gdaltools
                ogr = gdaltools.ogr2ogr()
                (major, minor, patch, prerelease) = ogr.get_version_tuple()
                print(f"GDAL/OGR version (gdaltools): {major}.{minor}.{patch} {prerelease}")
            except:
                print("GDAL/OGR version (gdaltools): not available")
            try:
                from django.contrib.gis import gdal
                print(f"GDAL version (django): {gdal.GDAL_VERSION}")
            except:
                print("GDAL version (django): not available")
            try:
                from gvsigol import settings
                print(f"GDAL_LIBRARY_PATH: {getattr(settings, 'GDAL_LIBRARY_PATH', '')}")
            except:
                print("GDAL_LIBRARY_PATH: not available")
        except:
            pass

    def config_gdaltools(self):
        from gvsigol import settings
        import gdaltools
        GDALTOOLS_BASEPATH = getattr(settings, 'GDALTOOLS_BASEPATH', '')
        if GDALTOOLS_BASEPATH:
            gdaltools.Wrapper.BASEPATH = GDALTOOLS_BASEPATH

    def output_locale_conf(self):
        logger = logging.getLogger('gvsigol')
        try:
            logger.info("sys.stdout.encoding: {}".format(sys.stdout.encoding))
        except:
            logger.info('sys.stdout.encoding not defined')
        try:
            logger.info("locale.getpreferredencoding(): {}".format(locale.getpreferredencoding()))
        except:
            logger.info('locale.getpreferredencoding() not defined')

        try:
            logger.info("locale.getdefaultlocale(): {}".format(locale.getdefaultlocale()))
        except:
            logger.info('locale.getdefaultlocale() not defined')

        try:
            logger.info("'LANG': {}".format(os.environ.get('LANG')))
        except:
            logger.info("os.environ.get('LANG') not defined")

        try:
            logger.info("'LC_ALL': {}".format(os.environ.get('LC_ALL')))
        except:
            logger.info("os.environ.get('LC_ALL') not defined")