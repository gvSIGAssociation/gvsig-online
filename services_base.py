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
