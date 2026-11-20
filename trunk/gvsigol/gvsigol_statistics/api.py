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
API JSON de estadísticas (v1). Solo lectura (GET) y solo superusuarios.

Parámetros comunes: from, to (YYYY-MM-DD, hora local, ambos incluidos; por
defecto los últimos 30 días), user (nombre de usuario o 'anonymous'), project (id).
Con format=csv, timeseries, top y unused devuelven un CSV (separador ';').
'''

import csv
import io
import logging
from functools import wraps

from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET

from . import analytics
from .analytics import QueryError

logger = logging.getLogger('gvsigol')


def _json_error(msg, status):
    return JsonResponse({'status': 'ERROR', 'msg': msg}, status=status)


def stats_api(view):
    """GET, superusuario, errores de parámetros como 400 en JSON."""
    @require_GET
    @wraps(view)
    def wrap(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_superuser:
            return _json_error('Permission denied', 403)
        try:
            return view(request, *args, **kwargs)
        except QueryError as e:
            return _json_error(str(e), 400)
    return wrap


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------

def _csv_safe(value):
    """Evita que las hojas de cálculo interpreten un texto como fórmula."""
    if value is None:
        return ''
    if isinstance(value, str) and value[:1] in ('=', '+', '-', '@', '\t', '\r'):
        return "'" + value
    return value


def csv_response(filename, header, rows):
    buffer = io.StringIO()
    buffer.write('﻿')  # BOM: Excel detecta UTF-8
    writer = csv.writer(buffer, delimiter=';')
    writer.writerow(header)
    for row in rows:
        writer.writerow([_csv_safe(v) for v in row])
    response = HttpResponse(buffer.getvalue(), content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="%s"' % filename
    return response


def _wants_csv(request):
    return request.GET.get('format') == 'csv'


def _slug(verb):
    return verb.replace('/', '_')


# ---------------------------------------------------------------------------
# Vistas
# ---------------------------------------------------------------------------

@stats_api
def metrics(request):
    return JsonResponse(analytics.metrics_catalog())


@stats_api
def summary(request):
    query = analytics.parse_query(request.GET)
    return JsonResponse(analytics.summary(query))


@stats_api
def timeseries(request):
    query = analytics.parse_query(request.GET)
    verb = analytics.parse_verb(request.GET)
    data = analytics.timeseries(query, verb, request.GET.get('interval') or 'day')
    if _wants_csv(request):
        return csv_response(
            'timeseries_%s_%s_%s.csv' % (_slug(verb), data['meta']['from'], data['meta']['to']),
            ['period', 'total', 'authenticated', 'anonymous'],
            ([p['period'], p['total'], p['authenticated'], p['anonymous']] for p in data['points']))
    return JsonResponse(data)


@stats_api
def top(request):
    query = analytics.parse_query(request.GET)
    verb = analytics.parse_verb(request.GET)
    limit = analytics.parse_int(request.GET, 'limit', 10, 1, analytics.MAX_TOP_LIMIT)
    data = analytics.top(query, verb, request.GET.get('by') or 'object', limit)
    if _wants_csv(request):
        return csv_response(
            'top_%s_%s_%s_%s.csv' % (_slug(verb), data['meta']['by'], data['meta']['from'], data['meta']['to']),
            ['position', 'type', 'id', 'label', 'count', 'share', 'unique_users', 'last_seen'],
            ([i['position'], i['type'], i['id'], i['label'], i['count'], i['share'],
              i.get('unique_users'), i['last_seen']] for i in data['items']))
    return JsonResponse(data)


@stats_api
def heatmap(request):
    query = analytics.parse_query(request.GET)
    verb = analytics.parse_verb(request.GET)
    return JsonResponse(analytics.heatmap(query, verb))


@stats_api
def unused(request):
    days = analytics.parse_int(request.GET, 'days', 90, 1, analytics.MAX_RANGE_DAYS)
    limit = analytics.parse_int(request.GET, 'limit', 500, 1, analytics.MAX_UNUSED_LIMIT)
    data = analytics.unused(request.GET.get('type') or 'project', days, limit)
    if _wants_csv(request):
        return csv_response(
            'unused_%s_%sd.csv' % (data['meta']['type'], days),
            ['type', 'id', 'name', 'title', 'workspace', 'last_used'],
            ([i['type'], i['id'], i['name'], i['title'], i.get('workspace'), i['last_used']]
             for i in data['items']))
    return JsonResponse(data)
