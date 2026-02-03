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
@author: Javier Rodrigo <jrodrigo@scolab.es>
'''
from django.utils.translation import ugettext_noop as _
import os


STATISTICS=[{
    'id': 'gvsigol_core',
    'count': 1,
    'operation': 'get_conf',
    'reverse_petition': False,
    'title': _('Project requests'),
    'target_title': _('Projects'),
    'target_field': 'title'
},
{
    'id': 'gvsigol_core',
    'count': 2,
    'operation': 'get_conf',
    'reverse_petition': True,
    'title': _('Project requests by user'),
    'target_title': _('Users'),
    'target_field': 'username'
}]

def get_neu_axisorder_srss():
    from gvsigol.settings import BASE_DIR
    with open(os.path.join(BASE_DIR, 'gvsigol_core/static/crs_axis_order/mapaxisorder.csv'), 'r') as f:
        next(f)  # Skip header line
        for line in f:
            yield int(line.strip())

def is_django_geosgeometry_broken():
    from django.utils import version
    django_major, django_minor, django_patch = version.get_version_tuple(version.get_version())
    if django_major < 4 or (django_major == 4 and django_minor < 2):
        import gdaltools
        (gdal_major, gdal_minor, gdal_patch, gdal_prerelease) = gdaltools.ogr2ogr().get_version_tuple()
        if int(gdal_major) > 2:
            return True
    return False

NEU_AXIS_ORDER_SRSS = set(get_neu_axisorder_srss())
DJANGO_BROKEN_GEOSGEOMETRY = is_django_geosgeometry_broken()