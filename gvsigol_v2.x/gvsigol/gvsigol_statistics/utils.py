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



def get_actions(verb, reverse=False, is_count=False, user=None, target=None, start_date=None, end_date=None, group_by_date=None, date_pattern=None):
    conn = get_DB_connection()
    cursor = conn.cursor()

    selector = 'action_object'
    if reverse:
        selector = 'actor'

    select = '*'
    group_by_date_query = 'NULL'
    if group_by_date:
        group_by_date_query = 'to_char(timestamp, \'' + date_pattern +'\') as time_pattern'

    half_select = ', '+selector+'_content_type_id, '+selector+'_object_id, COUNT(*) as count'
    half_empty_select = ', NULL, NULL, COUNT(*) as count'
    select = group_by_date_query + half_select
    if is_count:
        select = 'NULL' + half_empty_select



    start_date_query = '';
    if start_date:
        start_date_query = ' AND timestamp >= ' + start_date

    end_date_query = '';
    if end_date:
        end_date_query = ' AND timestamp <= ' + end_date

    user_query = ''
    if not user or user == 'all':
        user_query = ''
    else:
        if user == 'anonymous':
            user_query = ' AND actor_content_type_id = action_object_content_type_id AND actor_object_id = action_object_object_id'
        else:
            user_query = ' AND actor_object_id = \'' + str(user) + '\''

    target_query = ''
    if target:
        target_query = ' AND action_object_object_id = \'' + str(target) + '\''

    group_by_query = ''
    order_by_query = ''
    if group_by_date:
        group_by_query = ' GROUP BY time_pattern, '+selector+'_object_id, '+selector+'_content_type_id'
        order_by_query = ' ORDER BY to_date(to_char(timestamp, \'' + date_pattern +'\'), \'' + date_pattern +'\') asc, count desc'
    else:
        group_by_query = ' GROUP BY '+selector+'_content_type_id, '+selector+'_object_id'
        order_by_query = ' ORDER BY count DESC'


    query = ''
    if not reverse:
        query = "SELECT "+select+" FROM public.actstream_action WHERE verb LIKE '" + verb + "'" + user_query + target_query + start_date_query + end_date_query + group_by_query
        query = query + order_by_query + ";"
    else:
        reverse_where2 = '(actor_content_type_id = action_object_content_type_id AND actor_object_id = action_object_object_id) '
        reverse_where = '(action_object_content_type_id IS NULL OR (actor_content_type_id <> action_object_content_type_id AND actor_object_id <> action_object_object_id))'
        query = "SELECT "+select+" FROM public.actstream_action WHERE verb LIKE '" + verb + "' AND " + reverse_where +  user_query + target_query + start_date_query + end_date_query + group_by_query
        if not user or user == 'all' or user == 'anonymous':
            query = query + " UNION ALL " + "SELECT "+ group_by_date_query + half_empty_select+" FROM public.actstream_action WHERE verb LIKE '" + verb + "' AND " + reverse_where2 + user_query + target_query + start_date_query + end_date_query
            if group_by_date:
                query = query + " GROUP BY time_pattern "
                query = 'SELECT * FROM (' + query + ') AS aux ORDER BY to_date(time_pattern, \'' + date_pattern +'\') asc;'
            else:
                query = query + order_by_query + ";"
        else:
            query = query + order_by_query + ";"


    print query

    values = []
    cursor.execute(query, [])
    for r in cursor.fetchall():
        values.append(r)
        print r

    close_DB_connection(conn)

    return values




