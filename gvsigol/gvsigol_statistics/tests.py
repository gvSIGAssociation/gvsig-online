# -*- coding: utf-8 -*-
'''
Tests de gvsigol_statistics que no necesitan base de datos.

    python manage.py test gvsigol_statistics
'''
import datetime
import io
import json
from unittest import mock

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, SimpleTestCase

from gvsigol_statistics import services, views


class FakeUser:
    is_authenticated = True

    def __init__(self, is_superuser=False):
        self.is_superuser = is_superuser
        self.is_staff = is_superuser


class LegacyRowsTest(SimpleTestCase):
    """build_legacy_rows reproduce el contenido y el orden de la antigua consulta SQL."""

    def test_normal_ordered_by_count(self):
        primary = [{'action_object_content_type': 4, 'action_object_object_id': '1', 'count': 2},
                   {'action_object_content_type': 4, 'action_object_object_id': '2', 'count': 5}]
        rows = services.build_legacy_rows(primary, None, 'action_object', False, False, 'YYYY')
        self.assertEqual(rows, [(None, 4, '2', 5), (None, 4, '1', 2)])

    def test_count_hides_groups(self):
        primary = [{'actor_content_type': 4, 'actor_object_id': '1', 'count': 2}]
        rows = services.build_legacy_rows(primary, [{'count': 0}], 'actor', True, False, 'YYYY')
        self.assertEqual(rows, [(None, None, None, 2), (None, None, None, 0)])

    def test_grouped_by_date_then_count(self):
        primary = [{'bucket': '02-2024', 'action_object_content_type': 4, 'action_object_object_id': '1', 'count': 1},
                   {'bucket': '12-2023', 'action_object_content_type': 4, 'action_object_object_id': '1', 'count': 1},
                   {'bucket': '02-2024', 'action_object_content_type': 4, 'action_object_object_id': '2', 'count': 3}]
        rows = services.build_legacy_rows(primary, None, 'action_object', False, True, 'MM-YYYY')
        self.assertEqual([(r[0], r[3]) for r in rows], [('12-2023', 1), ('02-2024', 3), ('02-2024', 1)])

    def test_reverse_union_adds_anonymous_rows(self):
        primary = [{'bucket': '2024', 'actor_content_type': 4, 'actor_object_id': '1', 'count': 2}]
        anonymous = [{'bucket': '2023', 'count': 7}]
        rows = services.build_legacy_rows(primary, anonymous, 'actor', False, True, 'YYYY')
        self.assertEqual(rows, [('2023', None, None, 7), ('2024', 4, '1', 2)])

    def test_invalid_date_pattern_rejected_before_querying(self):
        with mock.patch.object(services, 'get_database_timezone') as get_tz, \
                mock.patch.object(services, 'actions_queryset') as get_qs:
            with self.assertRaises(ValueError):
                services.legacy_get_actions('a/b', group_by_date=True, date_pattern="YYYY'); DROP TABLE x; --")
            get_tz.assert_not_called()
            get_qs.assert_not_called()

    def test_bucket_sort_key(self):
        self.assertEqual(services.bucket_sort_key('05-03-2024', 'dd-MM-YYYY'), datetime.datetime(2024, 3, 5))
        self.assertEqual(services.bucket_sort_key(None, 'YYYY'), datetime.datetime.min)


class ActionsQuerysetSqlTest(SimpleTestCase):
    """El ORM pasa los valores de la petición como parámetros, no dentro del SQL."""

    def test_values_go_as_params(self):
        evil = "x' OR '1'='1"
        qs = services.actions_queryset(evil, user=evil, target=evil,
                                       start_date=datetime.datetime(2024, 1, 1), tz_name='Europe/Madrid')
        qs = qs.annotate(bucket=services.time_bucket('MM-YYYY', 'Europe/Madrid'))
        sql, params = qs.query.sql_with_params()
        self.assertNotIn(evil, sql)
        self.assertNotIn('Europe/Madrid', sql)
        self.assertIn(evil, params)
        self.assertIn('to_char', sql)
        self.assertNotIn('ORDER BY', sql)
        start = [p for p in params if isinstance(p, datetime.datetime)][0]
        self.assertEqual(start.utcoffset(), datetime.timedelta(hours=1))

    def test_anonymous_filter(self):
        sql, _ = services.actions_queryset('a/b', user='anonymous').query.sql_with_params()
        self.assertIn('"actor_content_type_id" = ("actstream_action"."action_object_content_type_id")', sql)


class MetricTest(SimpleTestCase):

    CONF = {'id': 'gvsigol_core', 'count': 1, 'operation': 'get_conf', 'reverse_petition': True,
            'title': 'T', 'target_title': 'P', 'target_field': 'title', 'icon': 'fa-map'}

    def test_from_conf(self):
        metric = services.Metric.from_conf(self.CONF)
        self.assertEqual(metric.verb, 'gvsigol_core/get_conf')
        self.assertEqual(metric.key, 'gvsigol_core-get_conf-1')
        self.assertTrue(metric.reverse_petition)
        self.assertEqual(metric.extra, {'icon': 'fa-map'})

    def test_invalid_conf_ignored(self):
        bad = dict(self.CONF)
        del bad['operation']
        with mock.patch.object(services, 'get_statistics_conf', return_value=[bad, self.CONF]):
            self.assertEqual([m.key for m in services.get_metrics()], ['gvsigol_core-get_conf-1'])


class StatisticsViewsAccessTest(SimpleTestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def post(self, view, user, data=None, **kwargs):
        request = self.factory.post('/x/', data or {})
        request.user = user
        return view(request, **kwargs)

    def test_anonymous_is_rejected(self):
        for view, kwargs in ((views.get_registered_actions, {'plugin_name': 'a', 'action_name': 'b'}),
                             (views.get_targets_from_content_type, {}),
                             (views.register_action, {})):
            response = self.post(view, AnonymousUser(), **kwargs)
            self.assertEqual(response.status_code, 403, view.__name__)
            self.assertEqual(json.loads(response.content)['status'], 'ERROR')

    def test_read_endpoints_require_superuser(self):
        user = FakeUser(is_superuser=False)
        self.assertEqual(self.post(views.get_registered_actions, user, plugin_name='a', action_name='b').status_code, 403)
        self.assertEqual(self.post(views.get_targets_from_content_type, user).status_code, 403)

    def test_get_not_allowed(self):
        request = self.factory.get('/x/')
        request.user = FakeUser(is_superuser=True)
        self.assertEqual(views.get_targets_from_content_type(request).status_code, 405)

    def test_registered_actions_ok_and_dates_as_datetime(self):
        with mock.patch.object(views, 'get_actions', return_value=[(None, None, None, 5)]) as get_actions:
            response = self.post(views.get_registered_actions, FakeUser(True), {
                'username': 'all', 'get_count': 'true', 'start_date': '2024-01-01',
                'end_date': 'no es fecha', 'reverse': 'false', 'group_by_date': 'false',
                'date_pattern': 'YYYY'}, plugin_name='gvsigol_core', action_name='get_conf')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), {'count': [[None, None, None, 5]]})
        args = get_actions.call_args[0]
        self.assertEqual(args[0], 'gvsigol_core/get_conf')
        self.assertEqual(args[5], datetime.datetime(2024, 1, 1))
        self.assertIsNone(args[6])

    def test_registered_actions_invalid_pattern(self):
        response = self.post(views.get_registered_actions, FakeUser(True), {
            'group_by_date': 'true', 'date_pattern': "YYYY') --"}, plugin_name='a', action_name='b')
        self.assertEqual(response.status_code, 400)


class FakeModel:
    def __init__(self, pk, title, password):
        self.id = pk
        self.title = title
        self.password = password

    def __str__(self):
        return 'obj-%s' % self.id


class TargetsFromContentTypeTest(SimpleTestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.model = mock.MagicMock()
        self.model.objects.all.return_value = [FakeModel(1, 'Uno', 'hash1'), FakeModel(2, 'Dos', 'hash2')]
        ct = mock.MagicMock()
        ct.model_class.return_value = self.model
        patcher = mock.patch.object(views.ContentType.objects, 'filter')
        self.addCleanup(patcher.stop)
        patcher.start().return_value.first.return_value = ct

    def call(self, field_name, registered=True):
        request = self.factory.post('/x/', {'content_type_id': '5', 'field_name': field_name})
        request.user = FakeUser(True)
        with mock.patch.object(services, 'get_statistics_conf', return_value=[]), \
                mock.patch.object(views, 'actstream_registry', {self.model: None} if registered else {}):
            return views.get_targets_from_content_type(request)

    def test_allowed_field(self):
        response = self.call('title')
        self.assertEqual(json.loads(response.content), {'targets': {'1': 'Uno', '2': 'Dos'}})

    def test_sensitive_field_not_exposed(self):
        response = self.call('password')
        self.assertEqual(json.loads(response.content), {'targets': {'1': 'obj-1', '2': 'obj-2'}})

    def test_unregistered_model_rejected(self):
        self.assertEqual(self.call('title', registered=False).status_code, 400)


class RegisterActionTest(SimpleTestCase):

    def test_unregistered_model_rejected(self):
        request = RequestFactory().post('/x/', {'actor_type': 'session', 'actor_id': '1', 'verb': 'a/b'})
        request.user = FakeUser()
        model = mock.MagicMock()
        with mock.patch.object(views, 'get_class_from_content_type', return_value=model), \
                mock.patch.object(views, 'actstream_registry', {}), \
                mock.patch.object(views.action, 'send') as send:
            response = views.register_action(request)
        self.assertEqual(response.status_code, 400)
        send.assert_not_called()
        model.objects.get.assert_not_called()


class AnalyticsParamsTest(SimpleTestCase):
    """Análisis de parámetros de la API (sin BD)."""

    def setUp(self):
        from gvsigol_statistics import analytics
        self.analytics = analytics
        self.today = datetime.date(2026, 3, 29)  # día del cambio de hora en Europa

    def test_default_last_30_days(self):
        q = self.analytics.parse_query({}, today=self.today)
        self.assertEqual((q.date_from, q.date_to), (datetime.date(2026, 2, 28), self.today))
        self.assertEqual(q.start.tzinfo, q.tz)
        prev = q.previous()
        self.assertEqual(prev.end, q.start)
        self.assertEqual(prev.end - prev.start, q.end - q.start)

    def test_explicit_range_inclusive(self):
        q = self.analytics.parse_query({'from': '2026-01-01', 'to': '2026-01-31'}, today=self.today)
        self.assertEqual(q.as_meta()['from'], '2026-01-01')
        self.assertEqual(q.as_meta()['to'], '2026-01-31')
        self.assertEqual(q.end.date(), datetime.date(2026, 2, 1))

    def test_invalid_params(self):
        for params in ({'from': '2026-13-01'}, {'from': '2026-02-01', 'to': '2026-01-01'},
                       {'from': '2000-01-01', 'to': '2026-01-01'}, {'project': 'abc'}):
            with self.assertRaises(self.analytics.QueryError, msg=params):
                self.analytics.parse_query(params, today=self.today)

    def test_anonymous_user_needs_no_lookup(self):
        q = self.analytics.parse_query({'user': 'anonymous'}, today=self.today)
        self.assertEqual((q.username, q.user_id), ('anonymous', None))
        q = self.analytics.parse_query({'user': 'all'}, today=self.today)
        self.assertIsNone(q.username)

    def test_parse_int(self):
        self.assertEqual(self.analytics.parse_int({}, 'limit', 10, 1, 100), 10)
        self.assertEqual(self.analytics.parse_int({'limit': '5'}, 'limit', 10, 1, 100), 5)
        for bad in ('0', '101', 'x'):
            with self.assertRaises(self.analytics.QueryError):
                self.analytics.parse_int({'limit': bad}, 'limit', 10, 1, 100)

    def test_parse_verb(self):
        with mock.patch.object(self.analytics, 'get_metrics', return_value=[]):
            self.assertEqual(self.analytics.parse_verb({}), self.analytics.VERB_PROJECT)
            with self.assertRaises(self.analytics.QueryError):
                self.analytics.parse_verb({'verb': "x' OR 1=1"})

    def test_period_starts(self):
        q = self.analytics.parse_query({'from': '2026-01-28', 'to': '2026-03-02'}, today=self.today)
        days = self.analytics._period_starts(q, 'day')
        self.assertEqual((len(days), days[0], days[-1]), (34, datetime.date(2026, 1, 28), datetime.date(2026, 3, 2)))
        weeks = self.analytics._period_starts(q, 'week')
        self.assertTrue(all(d.weekday() == 0 for d in weeks))
        self.assertEqual(weeks[0], datetime.date(2026, 1, 26))
        months = self.analytics._period_starts(q, 'month')
        self.assertEqual(months, [datetime.date(2026, 1, 1), datetime.date(2026, 2, 1), datetime.date(2026, 3, 1)])

    def test_change(self):
        self.assertEqual(self.analytics._kpi(15, 10)['change'], 50.0)
        self.assertIsNone(self.analytics._kpi(5, 0)['change'])


class StatsApiTest(SimpleTestCase):

    def setUp(self):
        from gvsigol_statistics import api
        self.api = api
        self.factory = RequestFactory()

    def call(self, view, user, method='get', **params):
        request = getattr(self.factory, method)('/x/', params)
        request.user = user
        return view(request)

    def test_permissions_and_method(self):
        self.assertEqual(self.call(self.api.summary, AnonymousUser()).status_code, 403)
        self.assertEqual(self.call(self.api.summary, FakeUser(False)).status_code, 403)
        self.assertEqual(self.call(self.api.summary, FakeUser(True), method='post').status_code, 405)

    def test_query_error_is_400(self):
        response = self.call(self.api.summary, FakeUser(True), **{'from': 'mal'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content)['status'], 'ERROR')

    def test_csv_escapes_formulas(self):
        response = self.api.csv_response('x.csv', ['label'], [['=HYPERLINK("http://x")'], ['Normal'], [None]])
        body = response.content.decode('utf-8')
        self.assertTrue(body.startswith('﻿label'))
        self.assertIn("'=HYPERLINK", body)
        self.assertIn('attachment; filename="x.csv"', response['Content-Disposition'])

    def test_top_csv(self):
        data = {'meta': {'by': 'object', 'from': '2026-01-01', 'to': '2026-01-31'}, 'total': 3, 'anonymous': None,
                'items': [{'position': 1, 'type': 'gvsigol_core.project', 'id': '2', 'label': 'Mapa',
                           'exists': True, 'count': 3, 'share': 100.0, 'unique_users': 1, 'last_seen': None}]}
        with mock.patch.object(self.api.analytics, 'top', return_value=data), \
                mock.patch.object(self.api.analytics, 'parse_query'), \
                mock.patch.object(self.api.analytics, 'parse_verb', return_value='gvsigol_core/get_conf'):
            response = self.call(self.api.top, FakeUser(True), format='csv')
        lines = response.content.decode('utf-8').splitlines()
        self.assertEqual(lines[1], '1;gvsigol_core.project;2;Mapa;3;100.0;1;')


def _fake_jwt(claims):
    import base64
    def b64(data):
        return base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip('=')
    return '%s.%s.firma' % (b64({'alg': 'none'}), b64(claims))


class EventsTest(SimpleTestCase):

    def setUp(self):
        from gvsigol_statistics import events
        self.events = events

    def test_record_event_never_raises(self):
        with mock.patch('actstream.action.send', side_effect=RuntimeError('db caída')):
            self.assertFalse(self.events.record_event(mock.MagicMock(pk=1), 'a/b'))
        self.assertFalse(self.events.record_event(None, 'a/b'))

    def test_record_event_passes_channel_as_data(self):
        actor, obj = mock.MagicMock(pk=1), mock.MagicMock(pk=2)
        with mock.patch('actstream.action.send') as send:
            self.assertTrue(self.events.record_event(actor, 'a/b', action_object=obj, channel='spa'))
        send.assert_called_once_with(actor, verb='a/b', action_object=obj, channel='spa')

    def test_actor_for(self):
        project = object()
        self.assertIs(self.events.actor_for(AnonymousUser(), project), project)
        user = FakeUser()
        self.assertIs(self.events.actor_for(user, project), user)

    def test_login_signal_skips_silent_renewal(self):
        user = mock.MagicMock(pk=7)
        request = mock.MagicMock()
        request.session = {}
        with mock.patch.object(self.events, 'record_event') as record:
            self.events.on_user_logged_in(None, request, user)          # login real
            self.events.on_user_logged_in(None, request, user)          # renovación OIDC (misma sesión)
            self.assertEqual(record.call_count, 1)
            request.session = {}                                        # logout + login
            self.events.on_user_logged_in(None, request, user)
            other = mock.MagicMock(pk=8)
            self.events.on_user_logged_in(None, request, other)         # otro usuario
        self.assertEqual(record.call_count, 3)
        self.assertEqual(record.call_args[1]['channel'], 'classic')


class EventsApiTest(SimpleTestCase):

    def setUp(self):
        from rest_framework.test import APIRequestFactory
        from gvsigol_statistics import api_events
        self.api_events = api_events
        self.factory = APIRequestFactory()

    def post(self, view, data, user=None, token=None):
        from rest_framework.test import force_authenticate
        request = self.factory.post('/x/', data, format='json')
        if user is not None:
            force_authenticate(request, user=user, token=token)
        with mock.patch.object(self.api_events.EventRateThrottle, 'allow_request', return_value=True):
            return view.as_view()(request)

    def test_token_session_key(self):
        key = self.api_events.token_session_key
        self.assertEqual(key(_fake_jwt({'sid': 'abc', 'auth_time': 1})), 'sid:abc')
        self.assertEqual(key(_fake_jwt({'session_state': 'xyz'})), 'session_state:xyz')
        self.assertEqual(key(_fake_jwt({'auth_time': 1700000000})), 'auth_time:1700000000')
        self.assertIsNone(key(_fake_jwt({'sub': 'u'})))
        self.assertIsNone(key('no-es-un-jwt'))
        self.assertIsNone(key(None))

    def test_session_requires_auth(self):
        response = self.post(self.api_events.SessionEventView, {})
        self.assertIn(response.status_code, (401, 403))

    def test_session_dedupes_by_hashed_sid(self):
        user = FakeUser()
        with mock.patch.object(self.api_events, 'record_event', return_value=True) as record:
            response = self.post(self.api_events.SessionEventView, {'channel': 'spa'}, user, _fake_jwt({'sid': 'S1'}))
        self.assertEqual(response.status_code, 202)
        kwargs = record.call_args[1]
        self.assertEqual(kwargs['channel'], 'spa')
        self.assertEqual(kwargs['dedupe_data'], {'session': self.api_events.hash_key('sid:S1')})
        self.assertNotIn('S1', json.dumps(kwargs['dedupe_data']))

    def test_session_without_sid_dedupes_by_time(self):
        with mock.patch.object(self.api_events, 'record_event', return_value=True) as record:
            self.post(self.api_events.SessionEventView, {'channel': 'otro'}, FakeUser(), 'token-opaco')
        self.assertEqual(record.call_args[1]['dedupe_seconds'], 8 * 3600)
        self.assertEqual(record.call_args[1]['channel'], 'spa')  # canal desconocido -> spa

    def test_layer_validation(self):
        from gvsigol_services.models import Layer
        with mock.patch.object(Layer.objects, 'get', side_effect=Layer.DoesNotExist):
            self.assertEqual(self.post(self.api_events.LayerEventView, {'layer_id': 999}).status_code, 400)
        self.assertEqual(self.post(self.api_events.LayerEventView, {'layer_id': 'x'}).status_code, 400)

    def test_layer_anonymous_actor_is_layer(self):
        from gvsigol_services.models import Layer
        layer = mock.MagicMock(pk=5)
        with mock.patch.object(Layer.objects, 'get', return_value=layer), \
                mock.patch.object(self.api_events, 'record_event', return_value=True) as record:
            response = self.post(self.api_events.LayerEventView, {'layer_id': 5})
        self.assertEqual(response.status_code, 202)
        self.assertIs(record.call_args[0][0], layer)
        self.assertEqual(record.call_args[1]['action_object'], layer)


class PurgeCommandTest(SimpleTestCase):
    """Validaciones de statistics_purge (se rechazan antes de tocar la BD)."""

    def call(self, *args):
        from django.core.management import call_command
        out = io.StringIO()
        call_command('statistics_purge', *args, stdout=out)
        return out.getvalue()

    def test_minimum_days(self):
        from django.core.management.base import CommandError
        with self.assertRaisesMessage(CommandError, 'at least 30'):
            self.call('--older-than-days', '10')

    def test_only_statistics_verbs(self):
        from django.core.management.base import CommandError
        with mock.patch('gvsigol_statistics.analytics.get_metrics', return_value=[]):
            with self.assertRaisesMessage(CommandError, 'Not a statistics verb: follow'):
                self.call('--older-than-days', '400', '--verb', 'follow')

    def test_batch_size_bounds(self):
        from django.core.management.base import CommandError
        with self.assertRaises(CommandError):
            self.call('--older-than-days', '400', '--batch-size', '10')
