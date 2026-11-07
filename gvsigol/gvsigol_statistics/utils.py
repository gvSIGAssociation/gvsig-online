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

from gvsigol import settings

import psycopg2

from .services import ALLOWED_DATE_PATTERNS, legacy_get_actions  # noqa: F401 (API pública)


def get_DB_connection():
    """Se conserva por compatibilidad; las estadísticas ya no la usan."""
    db = settings.DATABASES['default']
    connection = psycopg2.connect(
        host=db['HOST'],
        port=db['PORT'],
        dbname=db['NAME'],
        user=db['USER'],
        password=db['PASSWORD'],
    )
    connection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    return connection

def close_DB_connection(connection):
    connection.close()


def get_actions(verb, reverse=False, is_count=False, user=None, target=None, start_date=None, end_date=None, group_by_date=None, date_pattern=None):
    """
    Se conserva por compatibilidad: delega en services.legacy_get_actions (ORM),
    que devuelve las mismas filas que la antigua consulta SQL.
    """
    return legacy_get_actions(verb, reverse, is_count, user, target, start_date, end_date, group_by_date, date_pattern)
