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
from django.shortcuts import render_to_response, RequestContext
from django.utils.translation import ugettext as _
import gvsigol.settings
from gvsigol import settings

import psycopg2

def get_DB_connection():
    db = settings.DATABASES['default']

    dbhost = settings.DATABASES['default']['HOST']
    dbport = settings.DATABASES['default']['PORT']
    dbname = settings.DATABASES['default']['NAME']
    dbuser = settings.DATABASES['default']['USER']
    dbpassword = settings.DATABASES['default']['PASSWORD']

    try:
        connection = psycopg2.connect("host=" + dbhost +" port=" + dbport +" dbname=" + dbname +" user=" + dbuser +" password="+ dbpassword);
        connection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        print "Connecting ... "

        return connection
    except StandardError, e:
        print "Failed to connect!", e

    return None

def close_DB_connection(connection):
    connection.close();



def get_actions(verb, is_count=False, user=None, target=None, start_date=None, end_date=None):
    conn = get_DB_connection()
    cursor = conn.cursor()

    select = '*'
    if is_count:
        select = 'COUNT(*)'

    start_date_query = '';
    if start_date:
        start_date_query = ' AND timestamp >= ' + start_date

    end_date_query = '';
    if end_date:
        end_date_query = ' AND timestamp < ' + end_date

    user_query = ''
    if not user or user == 'all':
        user_query = ''
    else:
        if user == 'anonymous':
            user_query = ' AND actor_content_type_id = target_content_type_id AND actor_object_id = target_object_id'
        else:
            user_query = ' AND actor_object_id = \'' + str(user) + '\''

    target_query = ''
    if target:
        target_query = ' AND target_object_id = \'' + str(target) + '\''

    group_by_query =''
    #group_by_query = ' GROUP BY DATEPART(timestamp, timestamp), DATEPART(timestamp, timestamp)'

    # SELECT count(*) bugs_count, target_object_id, to_char(timestamp, 'YYYY-MM-dd') as day_of_week FROM public.actstream_action WHERE verb LIKE 'gvsigol_core/get_conf' group by day_of_week, target_object_id order by bugs_count desc;


    query = "SELECT "+select+" FROM public.actstream_action WHERE verb LIKE '" + verb + "'" + user_query + target_query + start_date_query + end_date_query + group_by_query +';'
    print query

    values = []
    cursor.execute(query, [])
    for r in cursor.fetchall():
        values.append(r)
        print r

    close_DB_connection(conn)

    return values




