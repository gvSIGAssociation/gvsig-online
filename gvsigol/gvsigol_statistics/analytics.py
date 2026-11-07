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
Consultas de la API de estadísticas (v1).

Diferencias deliberadas con el panel antiguo (legacy_get_actions):
- Todo se calcula en la zona horaria de Django (settings.TIME_ZONE), no en la de la BD.
- Acción anónima = el actor es el propio objeto (p. ej. proyecto público sin sesión).
- Rankings por usuario: solo actores de tipo usuario, sin perder acciones cuyo id
  coincida con el del objeto (fallo del modo inverso antiguo).
'''

import datetime
from dataclasses import dataclass
from typing import Optional

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, F, Max, Min, Q
from django.db.models.functions import (ExtractHour, ExtractIsoWeekDay, TruncDay,
                                        TruncMonth, TruncWeek)
from django.utils import timezone as dj_timezone

from actstream.models import Action

from .services import get_metrics

from .events import VERB_LAYER, VERB_LOGIN, VERB_PROJECT  # noqa: E402

DEFAULT_DAYS = 30
MAX_RANGE_DAYS = 3660
MAX_SERIES_POINTS = 1000
MAX_TOP_LIMIT = 100
MAX_UNUSED_LIMIT = 5000

INTERVALS = {
    'day': TruncDay,
    'week': TruncWeek,
    'month': TruncMonth,
}

# Campos preferidos para etiquetar objetos
LABEL_FIELDS = ('title', 'username', 'name')


class QueryError(ValueError):
    """Parámetros de consulta no válidos (se responde con 400)."""


# ---------------------------------------------------------------------------
# Parámetros
# ---------------------------------------------------------------------------

@dataclass
class StatsQuery:
    start: datetime.datetime          # incluido (con zona)
    end: datetime.datetime            # excluido (con zona)
    tz: datetime.tzinfo
    username: Optional[str] = None    # None, 'anonymous' o nombre de usuario
    user_id: Optional[int] = None
    project_id: Optional[int] = None

    @property
    def date_from(self):
        return self.start.astimezone(self.tz).date()

    @property
    def date_to(self):
        """Último día incluido."""
        return (self.end.astimezone(self.tz) - datetime.timedelta(days=1)).date()

    def previous(self):
        """Mismo filtro sobre el periodo inmediatamente anterior de igual duración."""
        length = self.end - self.start
        return StatsQuery(self.start - length, self.start, self.tz,
                          self.username, self.user_id, self.project_id)

    def as_meta(self):
        return {
            'from': self.date_from.isoformat(),
            'to': self.date_to.isoformat(),
            'timezone': str(self.tz),
            'user': self.username,
            'project': self.project_id,
        }


def _parse_day(value, name):
    try:
        return datetime.date.fromisoformat(value)
    except (TypeError, ValueError):
        raise QueryError('Invalid date for %s (expected YYYY-MM-DD): %r' % (name, value))


def _local_midnight(day, tz):
    return datetime.datetime(day.year, day.month, day.day, tzinfo=tz)


def parse_query(params, today=None):
    """Construye un StatsQuery a partir de los parámetros GET (from, to, user, project)."""
    tz = dj_timezone.get_default_timezone()
    today = today or dj_timezone.localdate()

    date_to = _parse_day(params['to'], 'to') if params.get('to') else today
    if params.get('from'):
        date_from = _parse_day(params['from'], 'from')
    else:
        date_from = date_to - datetime.timedelta(days=DEFAULT_DAYS - 1)
    if date_from > date_to:
        raise QueryError('"from" must be before "to"')
    if (date_to - date_from).days > MAX_RANGE_DAYS:
        raise QueryError('Date range too long (max %d days)' % MAX_RANGE_DAYS)

    query = StatsQuery(
        start=_local_midnight(date_from, tz),
        end=_local_midnight(date_to + datetime.timedelta(days=1), tz),
        tz=tz,
    )

    username = params.get('user') or None
    if username and username != 'all':
        query.username = username
        if username != 'anonymous':
            user = get_user_model().objects.filter(username=username).only('id').first()
            if user is None:
                raise QueryError('Unknown user: %s' % username)
            query.user_id = user.id

    project = params.get('project') or None
    if project:
        try:
            query.project_id = int(project)
        except ValueError:
            raise QueryError('Invalid project id: %r' % project)
    return query


def parse_int(params, name, default, minimum, maximum):
    value = params.get(name)
    if value in (None, ''):
        return default
    try:
        value = int(value)
    except ValueError:
        raise QueryError('Invalid integer for %s: %r' % (name, value))
    if not minimum <= value <= maximum:
        raise QueryError('%s must be between %d and %d' % (name, minimum, maximum))
    return value


def get_known_verbs():
    verbs = {VERB_LOGIN, VERB_PROJECT, VERB_LAYER}
    verbs.update(m.verb for m in get_metrics())
    return verbs


def parse_verb(params, default=VERB_PROJECT):
    verb = params.get('verb') or default
    if verb not in get_known_verbs():
        raise QueryError('Unknown metric: %s' % verb)
    return verb


# ---------------------------------------------------------------------------
# Consultas base
# ---------------------------------------------------------------------------

def _ct(model):
    return ContentType.objects.get_for_model(model)


def _user_ct():
    return _ct(get_user_model())


def anonymous_q():
    """Acción anónima: el actor es el propio objeto."""
    return Q(actor_content_type=F('action_object_content_type'),
             actor_object_id=F('action_object_object_id'))


def authenticated_q():
    return Q(actor_content_type=_user_ct())


def project_layer_ids(project_id):
    from gvsigol_services.models import Layer
    return [str(pk) for pk in Layer.objects.filter(
        layer_group__projectlayergroup__project_id=project_id).values_list('id', flat=True).distinct()]


def events(verb, query, start=None, end=None):
    """Acciones de un verbo en el periodo de la consulta, con sus filtros."""
    qs = Action.objects.filter(verb=verb,
                               timestamp__gte=start or query.start,
                               timestamp__lt=end or query.end).order_by()
    if query.username == 'anonymous':
        qs = qs.filter(anonymous_q())
    elif query.user_id is not None:
        qs = qs.filter(authenticated_q(), actor_object_id=str(query.user_id))

    if query.project_id is not None:
        from gvsigol_core.models import Project
        if verb == VERB_LAYER:
            qs = qs.filter(action_object_object_id__in=project_layer_ids(query.project_id))
            from gvsigol_services.models import Layer
            qs = qs.filter(action_object_content_type=_ct(Layer))
        elif verb != VERB_LOGIN:
            # Métricas cuyo objeto es un proyecto (las demás no se pueden filtrar)
            qs = qs.filter(action_object_content_type=_ct(Project),
                           action_object_object_id=str(query.project_id))
    return qs


def first_event(verbs=None):
    """datetime de la primera acción registrada (o None si no hay ninguna)."""
    qs = Action.objects.order_by()
    if verbs:
        qs = qs.filter(verb__in=list(verbs))
    return qs.aggregate(first=Min('timestamp'))['first']


def tracking_since(verbs=None):
    """Fecha (hora local, ISO) de la primera acción, para avisar de la cobertura de los datos."""
    first = first_event(verbs)
    return dj_timezone.localtime(first).isoformat() if first else None


# ---------------------------------------------------------------------------
# Etiquetas de objetos
# ---------------------------------------------------------------------------

def _label_for(obj):
    for name in LABEL_FIELDS:
        value = getattr(obj, name, None)
        if value:
            return str(value)
    return str(obj)


def resolve_labels(pairs):
    """
    pairs: iterable de (content_type_id, object_id). Devuelve
    {(ct_id, object_id): {'label', 'type', 'exists'}} con una consulta por tipo.
    """
    by_ct = {}
    for ct_id, obj_id in pairs:
        if ct_id is not None and obj_id is not None:
            by_ct.setdefault(ct_id, set()).add(str(obj_id))
    result = {}
    for ct_id, ids in by_ct.items():
        ct = ContentType.objects.get_for_id(ct_id)
        model = ct.model_class()
        type_name = '%s.%s' % (ct.app_label, ct.model)
        found = {}
        if model is not None:
            valid_ids = [i for i in ids if i.isdigit()]
            for obj in model._default_manager.filter(pk__in=valid_ids):
                found[str(obj.pk)] = _label_for(obj)
        for obj_id in ids:
            result[(ct_id, obj_id)] = {
                'type': type_name,
                'label': found.get(obj_id),
                'exists': obj_id in found,
            }
    return result


# ---------------------------------------------------------------------------
# Resultados
# ---------------------------------------------------------------------------

def _change(current, previous):
    if not previous:
        return None
    return round((current - previous) * 100.0 / previous, 1)


def _kpi(current, previous):
    return {'value': current, 'previous': previous, 'change': _change(current, previous)}


def _period_kpis(query, start=None, end=None):
    project_views = events(VERB_PROJECT, query, start, end)
    layer_events = events(VERB_LAYER, query, start, end)
    login_events = events(VERB_LOGIN, query, start, end)
    user_ct = _user_ct()

    views = project_views.aggregate(
        total=Count('id'),
        anonymous=Count('id', filter=anonymous_q()),
        projects=Count('action_object_object_id', distinct=True),
    )
    layers = layer_events.aggregate(
        total=Count('id'),
        layers=Count('action_object_object_id', distinct=True),
    )
    logins = login_events.aggregate(total=Count('id'))
    unique_users = set()
    for qs in (project_views, layer_events, login_events):
        unique_users.update(qs.filter(actor_content_type=user_ct)
                            .values_list('actor_object_id', flat=True).distinct())
    return {
        'project_views': views['total'],
        'anonymous_views': views['anonymous'],
        'active_projects': views['projects'],
        'layer_activations': layers['total'],
        'active_layers': layers['layers'],
        'logins': logins['total'],
        'unique_users': len(unique_users),
    }


def summary(query):
    current = _period_kpis(query)
    prev_query = query.previous()
    previous = _period_kpis(prev_query)
    kpis = {key: _kpi(current[key], previous[key]) for key in current}

    def share(d):
        return round(d['anonymous_views'] * 100.0 / d['project_views'], 1) if d['project_views'] else None
    kpis['anonymous_share'] = {'value': share(current), 'previous': share(previous), 'change': None}
    return {
        'meta': dict(query.as_meta(),
                     previous_from=prev_query.date_from.isoformat(),
                     previous_to=prev_query.date_to.isoformat(),
                     tracking_since=tracking_since([VERB_PROJECT, VERB_LAYER, VERB_LOGIN])),
        'kpis': kpis,
    }


def _period_starts(query, interval):
    """Inicio (fecha local) de todos los periodos del rango, para rellenar huecos."""
    day = query.date_from
    if interval == 'week':
        day = day - datetime.timedelta(days=day.weekday())
    elif interval == 'month':
        day = day.replace(day=1)
    periods = []
    while day <= query.date_to:
        periods.append(day)
        if interval == 'day':
            day = day + datetime.timedelta(days=1)
        elif interval == 'week':
            day = day + datetime.timedelta(days=7)
        else:
            day = (day.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
    return periods


def timeseries(query, verb, interval):
    if interval not in INTERVALS:
        raise QueryError('Invalid interval: %r' % interval)
    periods = _period_starts(query, interval)
    if len(periods) > MAX_SERIES_POINTS:
        raise QueryError('Too many points (%d); use a wider interval' % len(periods))

    trunc = INTERVALS[interval]('timestamp', tzinfo=query.tz)
    rows = (events(verb, query).annotate(period=trunc).values('period')
            .annotate(total=Count('id'),
                      anonymous=Count('id', filter=anonymous_q()),
                      authenticated=Count('id', filter=authenticated_q()))
            .order_by())
    by_period = {}
    for row in rows:
        day = row['period'].astimezone(query.tz).date() if isinstance(row['period'], datetime.datetime) else row['period']
        by_period[day] = row
    points = []
    for day in periods:
        row = by_period.get(day, {})
        points.append({
            'period': day.isoformat(),
            'total': row.get('total', 0),
            'authenticated': row.get('authenticated', 0),
            'anonymous': row.get('anonymous', 0),
        })
    return {
        'meta': dict(query.as_meta(), verb=verb, interval=interval,
                     tracking_since=tracking_since([verb])),
        'points': points,
    }


def top(query, verb, by, limit):
    base = events(verb, query)
    total = base.count()
    if by == 'object':
        qs = base.exclude(action_object_content_type__isnull=True)
        ct_field, id_field = 'action_object_content_type', 'action_object_object_id'
        rows = (qs.values(ct_field, id_field)
                .annotate(count=Count('id'), last_seen=Max('timestamp'),
                          unique_users=Count('actor_object_id', distinct=True,
                                             filter=authenticated_q()))
                .order_by('-count', id_field)[:limit])
        anonymous = None
    elif by == 'user':
        qs = base.filter(authenticated_q())
        ct_field, id_field = 'actor_content_type', 'actor_object_id'
        rows = (qs.values(ct_field, id_field)
                .annotate(count=Count('id'), last_seen=Max('timestamp'))
                .order_by('-count', id_field)[:limit])
        anonymous = base.filter(anonymous_q()).count()
    else:
        raise QueryError('Invalid "by" (object or user): %r' % by)

    rows = list(rows)
    labels = resolve_labels((r[ct_field], r[id_field]) for r in rows)
    items = []
    for position, row in enumerate(rows, start=1):
        info = labels.get((row[ct_field], str(row[id_field])), {})
        item = {
            'position': position,
            'type': info.get('type'),
            'id': row[id_field],
            'label': info.get('label'),
            'exists': info.get('exists', False),
            'count': row['count'],
            'share': round(row['count'] * 100.0 / total, 1) if total else 0,
            'last_seen': dj_timezone.localtime(row['last_seen'], query.tz).isoformat() if row['last_seen'] else None,
        }
        if 'unique_users' in row:
            item['unique_users'] = row['unique_users']
        items.append(item)
    return {
        'meta': dict(query.as_meta(), verb=verb, by=by, limit=limit,
                     tracking_since=tracking_since([verb])),
        'total': total,
        'anonymous': anonymous,
        'items': items,
    }


def heatmap(query, verb):
    rows = (events(verb, query)
            .annotate(weekday=ExtractIsoWeekDay('timestamp', tzinfo=query.tz),
                      hour=ExtractHour('timestamp', tzinfo=query.tz))
            .values('weekday', 'hour').annotate(count=Count('id')).order_by())
    matrix = [[0] * 24 for _ in range(7)]  # lunes..domingo x 0..23 h
    for row in rows:
        matrix[row['weekday'] - 1][row['hour']] = row['count']
    return {
        'meta': dict(query.as_meta(), verb=verb, tracking_since=tracking_since([verb])),
        'matrix': matrix,
        'max': max(max(r) for r in matrix),
    }


def unused(kind, days, limit, now=None):
    """
    Proyectos o capas sin uso en los últimos 'days' días (o nunca usados desde que
    hay datos). Ordenados de más antiguo a más reciente, con los nunca usados primero.
    """
    from gvsigol_core.models import Project
    from gvsigol_services.models import Layer
    now = now or dj_timezone.now()
    cutoff = now - datetime.timedelta(days=days)

    if kind == 'project':
        model, verb = Project, VERB_PROJECT
        objects = model.objects.values('id', 'name', 'title')
    elif kind == 'layer':
        model, verb = Layer, VERB_LAYER
        objects = model.objects.values('id', 'name', 'title', 'external',
                                       workspace=F('datastore__workspace__name'))
    else:
        raise QueryError('Invalid type (project or layer): %r' % kind)

    last_used = dict(Action.objects.filter(verb=verb, action_object_content_type=_ct(model))
                     .order_by().values('action_object_object_id')
                     .annotate(last=Max('timestamp'))
                     .values_list('action_object_object_id', 'last'))
    items = []
    for obj in objects:
        last = last_used.get(str(obj['id']))
        if last is None or last < cutoff:
            item = dict(obj)
            item['type'] = kind
            item['last_used'] = dj_timezone.localtime(last).isoformat() if last else None
            items.append((last, item))
    # Nunca usados primero; después, de uso más antiguo a más reciente
    items.sort(key=lambda pair: (pair[0] is not None, pair[0] or now))
    items = [item for _, item in items]
    first = first_event([verb])
    return {
        'meta': {
            'type': kind,
            'days': days,
            'cutoff': dj_timezone.localtime(cutoff).isoformat(),
            'tracking_since': dj_timezone.localtime(first).isoformat() if first else None,
            # Si no hay datos que cubran todo el periodo, "sin uso" puede no ser fiable
            'partial_coverage': first is None or first > cutoff,
            'limit': limit,
        },
        'total': len(items),
        'items': items[:limit],
    }


def metrics_catalog():
    items = []
    for metric in get_metrics():
        items.append({
            'key': metric.key,
            'verb': metric.verb,
            'title': str(metric.title),
            'target_title': str(metric.target_title),
            'reverse': metric.reverse_petition,
        })
    return {'meta': {'tracking_since': tracking_since()}, 'metrics': items}
