

from django.apps import AppConfig
import sys
import os
import locale
import logging


class GvsigolCoreConfig(AppConfig):
    name = 'gvsigol_core'
    label = 'gvsigol_core'

    def ready(self):
        from gvsigol_core.utils import is_gvsigol_process
        if is_gvsigol_process():
            self.output_locale_conf()
        from actstream import registry
        registry.register(self.get_model('Project'))

        try:
            # ensure we have a proper environment
            self.config_gdaltools()            
        except:
            pass

    def config_gdaltools(self):
        import gdaltools
        from gvsigol.settings import GDALTOOLS_BASEPATH
        
        if GDALTOOLS_BASEPATH and GDALTOOLS_BASEPATH != '':
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