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

Capa de servicios de estadísticas.

- Registro de métricas: lee las listas STATISTICS de los settings.py de las apps.
- Consultas sobre actstream_action con el ORM de Django.
- legacy_get_actions(): reproduce exactamente las filas que devolvía la antigua
  consulta SQL de utils.get_actions (la usan los endpoints que consume el panel).
'''

import datetime
import logging
from dataclasses import dataclass, field
from importlib import import_module

try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:  # pragma: no cover - Python < 3.9
    from backports.zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.db import connection
from django.db.models import (BooleanField, CharField, Count, DateTimeField,
                              ExpressionWrapper, F, Func, Q, Value)
from django.utils import timezone as dj_timezone

from actstream.models import Action

from gvsigol import settings

logger = logging.getLogger('gvsigol')

# Patrones de fecha que acepta to_char() al agrupar por tiempo. Son los del
# selector "División temporal" del panel. El valor es el equivalente strptime.
DATE_PATTERNS = {
    'YYYY': '%Y',
    'MM-YYYY': '%m-%Y',
    'dd-MM-YYYY': '%d-%m-%Y',
}
ALLOWED_DATE_PATTERNS = tuple(DATE_PATTERNS)

# Campos que se pueden leer de los objetos para etiquetar las gráficas. Se amplía
# con los 'target_field' declarados en las STATISTICS de las apps instaladas.
DEFAULT_TARGET_FIELDS = ('title', 'username', 'name')

# Claves obligatorias de cada entrada de STATISTICS
METRIC_REQUIRED_KEYS = ('id', 'operation', 'count', 'title', 'target_title', 'target_field')


# ---------------------------------------------------------------------------
# Registro de métricas
# ---------------------------------------------------------------------------

@dataclass
class Metric:
    """Una entrada de STATISTICS. Las claves no reconocidas se guardan en 'extra'."""
    id: str
    operation: str
    count: int
    title: str
    target_title: str
    target_field: str
    reverse_petition: bool = False
    extra: dict = field(default_factory=dict)

    @property
    def verb(self):
        """Verbo con el que se registran las acciones en actstream."""
        return '%s/%s' % (self.id, self.operation)

    @property
    def key(self):
        """Identificador único (el que usa el panel en los id del DOM)."""
        return '%s-%s-%s' % (self.id, self.operation, self.count)

    @classmethod
    def from_conf(cls, conf):
        missing = [k for k in METRIC_REQUIRED_KEYS if k not in conf]
        if missing:
            raise ValueError('STATISTICS entry without %s: %r' % (', '.join(missing), conf))
        known = set(METRIC_REQUIRED_KEYS) | {'reverse_petition'}
        return cls(
            id=conf['id'],
            operation=conf['operation'],
            count=conf['count'],
            title=conf['title'],
            target_title=conf['target_title'],
            target_field=conf['target_field'],
            reverse_petition=bool(conf.get('reverse_petition', False)),
            extra={k: v for k, v in conf.items() if k not in known},
        )


def get_statistics_conf():
    """Devuelve copias de las entradas STATISTICS de los settings de las apps instaladas."""
    statistics_conf = []
    for app in settings.INSTALLED_APPS:
        try:
            mod = import_module('%s.settings' % app)
        except Exception:
            continue
        for stat in getattr(mod, 'STATISTICS', []) or []:
            statistics_conf.append(dict(stat))
    return statistics_conf


def get_metrics():
    """Métricas válidas declaradas por las apps instaladas (se ignoran las mal formadas)."""
    metrics = []
    for conf in get_statistics_conf():
        try:
            metrics.append(Metric.from_conf(conf))
        except (ValueError, TypeError):
            logger.warning("statistics: entrada STATISTICS no válida: %r", conf)
    return metrics


def get_allowed_target_fields():
    fields = set(DEFAULT_TARGET_FIELDS)
    for stat in get_statistics_conf():
        if stat.get('target_field'):
            fields.add(stat['target_field'])
    return fields


# ---------------------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------------------

def get_database_timezone():
    """
    Zona horaria por defecto del servidor PostgreSQL (la que usaba la antigua
    consulta SQL, que abría su propia conexión sin fijar zona). Django fija UTC
    en sus conexiones, por eso se lee el valor por defecto de pg_settings.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT reset_val FROM pg_settings WHERE name = 'TimeZone'")
            row = cursor.fetchone()
        if row and row[0]:
            return row[0]
    except Exception:
        logger.exception("statistics: no se pudo leer la zona horaria de la BD")
    return 'UTC'


def _aware(value, tz_name):
    """Interpreta un datetime sin zona en tz_name (como hacía PostgreSQL con la sesión)."""
    if value is None or dj_timezone.is_aware(value):
        return value
    try:
        tz = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError):
        logger.warning("statistics: zona horaria desconocida %r, se usa UTC", tz_name)
        tz = datetime.timezone.utc
    return value.replace(tzinfo=tz)


def time_bucket(date_pattern, tz_name):
    """to_char(timezone(tz, timestamp), pattern): periodo de la acción en la zona tz."""
    local_ts = Func(Value(tz_name, output_field=CharField()), F('timestamp'),
                    function='timezone', output_field=DateTimeField())
    return Func(local_ts, Value(date_pattern, output_field=CharField()),
                function='to_char', output_field=CharField())


def bucket_sort_key(bucket, date_pattern):
    """Equivalente a to_date(bucket, pattern) para ordenar periodos en Python."""
    if bucket is None:
        return datetime.datetime.min
    return datetime.datetime.strptime(bucket, DATE_PATTERNS[date_pattern])


def _same_actor_and_object():
    """Acciones anónimas: el actor es el propio objeto (p. ej. proyecto público)."""
    return Q(actor_content_type=F('action_object_content_type'),
             actor_object_id=F('action_object_object_id'))


def actions_queryset(verb, user=None, target=None, start_date=None, end_date=None, tz_name='UTC'):
    """
    Acciones de un verbo con los filtros del panel.

    user: None/'all' (todas), 'anonymous' (actor == objeto) o el id del actor.
    start_date/end_date: datetime; si no llevan zona se interpretan en tz_name.
    """
    qs = Action.objects.filter(verb=verb)
    if user and user != 'all':
        if user == 'anonymous':
            qs = qs.filter(_same_actor_and_object())
        else:
            qs = qs.filter(actor_object_id=str(user))
    if target:
        qs = qs.filter(action_object_object_id=str(target))
    if start_date:
        qs = qs.filter(timestamp__gte=_aware(start_date, tz_name))
    if end_date:
        qs = qs.filter(timestamp__lte=_aware(end_date, tz_name))
    # Action tiene ordering por defecto (-timestamp): hay que quitarlo para agrupar
    return qs.order_by()


def _grouped_counts(qs, keys, bucket=None):
    """Agrupa por keys (y por periodo si se indica). Devuelve dicts con 'count'."""
    if bucket is not None:
        qs = qs.annotate(bucket=bucket)
        keys = ['bucket'] + list(keys)
    if keys:
        return list(qs.values(*keys).annotate(count=Count('id')).order_by())
    return [qs.aggregate(count=Count('id'))]


def build_legacy_rows(primary, anonymous, selector, is_count, group_by_date, date_pattern):
    """
    Construye las filas (periodo, content_type_id, object_id, count) con el mismo
    contenido y orden que la antigua consulta SQL.

    primary: grupos por actor u objeto. anonymous: grupos de acciones anónimas
    (solo en modo inverso y sin usuario concreto), o None si no aplica.
    """
    rows = []
    for g in primary:
        if is_count:
            rows.append((None, None, None, g['count']))
        else:
            rows.append((g.get('bucket'), g[selector + '_content_type'], g[selector + '_object_id'], g['count']))

    if anonymous is None:
        if group_by_date and not is_count:
            # ORDER BY to_date(periodo) asc, count desc
            rows.sort(key=lambda r: (bucket_sort_key(r[0], date_pattern), -r[3]))
        else:
            rows.sort(key=lambda r: -r[3])
        return rows

    for g in anonymous:
        rows.append((g.get('bucket'), None, None, g['count']))
    if group_by_date and not is_count:
        # SELECT * FROM (... UNION ALL ...) ORDER BY to_date(periodo) asc
        rows.sort(key=lambda r: bucket_sort_key(r[0], date_pattern))
    else:
        rows.sort(key=lambda r: -r[3])
    return rows


def legacy_get_actions(verb, reverse=False, is_count=False, user=None, target=None,
                       start_date=None, end_date=None, group_by_date=None, date_pattern=None,
                       tz_name=None):
    """
    Sustituto con ORM de la antigua utils.get_actions. Devuelve una lista de tuplas
    (periodo, content_type_id, object_id, count):

    - Modo normal: agrupa por el objeto de la acción (proyecto, capa…).
    - Modo inverso (reverse): agrupa por el actor (usuario), excluyendo las acciones
      anónimas, que se suman en una fila con content_type/object_id a None.
    - is_count: mismas filas pero sin identificar el grupo (el panel solo suma 'count').

    tz_name: zona para los periodos y las fechas sin zona; por defecto la de la BD,
    que es la que usaba la consulta antigua.
    Lanza ValueError si se agrupa por fecha con un patrón no permitido.
    """
    if group_by_date and date_pattern not in ALLOWED_DATE_PATTERNS:
        raise ValueError('Invalid date pattern: %r' % (date_pattern,))
    if tz_name is None:
        tz_name = get_database_timezone()
    # Agrupar por periodo y solo contar no tiene sentido (la consulta antigua daba error):
    # se cuenta sin dividir por tiempo.
    if is_count:
        group_by_date = False

    selector = 'actor' if reverse else 'action_object'
    keys = [selector + '_content_type', selector + '_object_id']
    bucket = time_bucket(date_pattern, tz_name) if group_by_date else None

    qs = actions_queryset(verb, user, target, start_date, end_date, tz_name)
    anonymous = None
    if reverse:
        same_ct = ExpressionWrapper(Q(actor_content_type=F('action_object_content_type')),
                                    output_field=BooleanField())
        same_id = ExpressionWrapper(Q(actor_object_id=F('action_object_object_id')),
                                    output_field=BooleanField())
        # Igual que la SQL antigua: sin objeto, o actor y objeto distintos en tipo E id
        # (comparaciones con NULL no cuentan, como '<>' en SQL)
        primary_qs = qs.annotate(same_ct=same_ct, same_id=same_id).filter(
            Q(action_object_content_type__isnull=True) | Q(same_ct=False, same_id=False))
        if not user or user in ('all', 'anonymous'):
            # Sin periodo: una sola fila (aunque sea 0). Con periodo: una por periodo.
            anonymous = _grouped_counts(qs.filter(_same_actor_and_object()), [], bucket)
    else:
        primary_qs = qs

    primary = _grouped_counts(primary_qs, keys, bucket)
    return build_legacy_rows(primary, anonymous, selector, is_count, group_by_date, date_pattern)
