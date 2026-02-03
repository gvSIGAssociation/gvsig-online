# -*- coding: utf-8 -*-

'''
    gvSIG Online.
    Copyright (C) 2010-2017 SCOLAB.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

    @author: Cesar Martinez <cmartinez@scolab.es>
'''

from django.utils.translation import ugettext_noop as _

class ServiceException(Exception):
    pass

class BackendNotAvailable(ServiceException):
    pass

# ugettext_noop to keep all languages in .po regardless settings.py
lang_ca = _("Catalan")
lang_de = _("German")
lang_en = _("English")
lang_es = _("Spanish")
lang_pt = _("Portuguese")
lang_pt_br = _("Brazilian Portuguese")
lang_va = _("Valencian")


class CloneConf():
    LAYER_CLONE = 'clone'
    LAYER_SKIP = 'skip'
    LYRGROUP_REFERENCE = 'ref'
    LYRGROUP_CLONE = 'clone'
    LYRGROUP_SKIP = 'skip'
    PERMISSION_CLONE = "clone"
    PERMISSION_SKIP = "skip"

    def __init__(self,
                 recursive=True,
                 copy_data=True,
                 permissions=PERMISSION_CLONE,
                 base_lyrgroup=LYRGROUP_REFERENCE,
                 vector_lyrs=LAYER_CLONE,
                 raster_lyrs=LAYER_SKIP,
                 external_lyrs=LAYER_SKIP,
                 clean_on_failure=False
                 ) -> None:
        """
        Args:
            recursive (boolean): True by default
            copy_data (boolean): True by default
            permissions (string): CloneConf.PERMISSION_CLONE or CloneConf.PERMISSION_SKIP. By default: PERMISSION_CLONE
            base_lyrgroup (string): Only CloneConf.LYRGROUP_REFERENCE and CloneConf.LYRGROUP_SKIP are supported for the moment
            vector_lyrs (string): CloneConf.LAYER_CLONE or CloneConf.LAYER_SKIP
            raster_lyrs (string): Only CloneConf.LAYER_SKIP is supported for the moment
            external_lyrs (string): CloneConf.LAYER_CLONE or CloneConf.LAYER_SKIP
            clean_on_failure (boolean): False by default
        """
        self.recursive = recursive
        self.copy_data = copy_data
        self.permissions = permissions
        self.base_lyrgroup = base_lyrgroup
        self.vector_lyrs = vector_lyrs
        self.raster_lyrs = raster_lyrs
        self.external_lyrs = external_lyrs
        self.clean_on_failure = clean_on_failure
