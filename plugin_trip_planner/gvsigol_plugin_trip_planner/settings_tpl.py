# -*- coding: utf-8 -*-

'''
    gvSIG Online.
    Copyright (C) 2010-2017 Scolab Software Colaborativo S.L.

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
@author: José Badía <jbadia@scolab.es>
'''
from django.utils.translation import ugettext_lazy as _
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

STATIC_URL = '/gvsigonline/static/'

LAST_MODIFIED_FIELD_NAME="last_modified"

URL_SOLR="##SOLR_URL##"
DIR_SOLR_CONFIG="/var/solr/data/gvsigonline/conf/"
FILE_DATE_CONFIG="data-config.xml"
FILE_SOLR_CONFIG="solrconfig.xml"
SOLR_CORE_NAME="gvsigonline"

   