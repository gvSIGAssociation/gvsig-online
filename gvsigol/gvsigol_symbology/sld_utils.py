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
'''

'''
@author: Jose Badia <jbadia@scolab.es>
'''

from models import Style, Rule, Symbolizer
from xml.sax.saxutils import escape
import gvsigol.settings
import xmltodict
import json
import utils
import re

def copy_resources(symbol, resource_path):
    symbolizers = Symbolizer.objects.filter(rule = symbol)
    for symbolizer in symbolizers:
        if hasattr(symbolizer, 'externalgraphicsymbolizer'):
            local_path = symbolizer.externalgraphicsymbolizer.online_resource.replace(gvsigol.settings.MEDIA_URL, '')
            file_name = local_path.split('/')[-1]
            absolute_path = gvsigol.settings.MEDIA_ROOT + local_path
            utils.copy(absolute_path, resource_path + file_name)