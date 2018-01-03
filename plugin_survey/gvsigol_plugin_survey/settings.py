# -*- coding: utf-8 -*-
from django.utils.translation import ugettext as _
from gvsigol_core import utils as core_utils

supported_srs = tuple((x['code'].replace('EPSG:',''),x['code']+' - '+x['title']) for x in core_utils.get_supported_crs_array())
supported_srs_and_blank = (('', '---------'),) + supported_srs
