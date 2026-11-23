# -*- coding: utf-8 -*-
'''
Tests de caracterización ("golden master") de la simbología.

Fijan la salida ACTUAL de sld_builder.build_sld y utils.symbolizer_to_json para
cada tipo de leyenda, de modo que cualquier refactor que cambie el SLD generado
(y por tanto lo que GeoServer pinta para estilos ya guardados) haga fallar el test.

Si un cambio de salida es intencionado, regenerar los ficheros de referencia con:
    SYMBOLOGY_UPDATE_GOLDEN=1 python manage.py test gvsigol_symbology
y revisar el diff de test_golden/ antes de hacer commit.
'''
import json
import os
from unittest import mock

from django.test import TestCase

from gvsigol_services.models import Layer
from gvsigol_symbology import sld_builder, utils
from gvsigol_symbology.models import (
    Style, Rule, MarkSymbolizer, LineSymbolizer, PolygonSymbolizer,
    TextSymbolizer, ExternalGraphicSymbolizer, RasterSymbolizer, ColorMap,
    ColorMapEntry, Symbolizer,
)

GOLDEN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_golden')
UPDATE_GOLDEN = os.environ.get('SYMBOLOGY_UPDATE_GOLDEN') == '1'

POINT_GEOM = {'field_name': 'wkb_geometry', 'field_type': 'POINT'}
LINE_GEOM = {'field_name': 'wkb_geometry', 'field_type': 'MULTILINESTRING'}
POLYGON_GEOM = {'field_name': 'wkb_geometry', 'field_type': 'MULTIPOLYGON'}


def _layer(name='test_layer'):
    # Instancia sin guardar: build_sld solo usa name/type y get_geometry_field se parchea.
    return Layer(name=name, type='v_PostGIS')


def _style(name, stype, **kw):
    return Style.objects.create(name=name, title=name + ' title', type=stype, **kw)


def _rule(style, name, filter_obj='', order=0, title=None, **kw):
    filter_text = json.dumps(filter_obj) if filter_obj != '' else ''
    return Rule.objects.create(style=style, name=name, title=title or name,
                               abstract='', filter=filter_text, order=order, **kw)


def _poly(rule, order=0, fill='#ff0000', dash='none'):
    return PolygonSymbolizer.objects.create(
        rule=rule, order=order, fill=fill, fill_opacity=0.5, stroke='#000000',
        stroke_width=2, stroke_opacity=1.0, stroke_dash_array=dash)


def _line(rule, order=0, dash='none'):
    return LineSymbolizer.objects.create(
        rule=rule, order=order, stroke='#0000ff', stroke_width=3,
        stroke_opacity=0.8, stroke_dash_array=dash)


def _mark(rule, order=0, wkn='circle'):
    return MarkSymbolizer.objects.create(
        rule=rule, order=order, opacity=1, size=10, rotation=0, well_known_name=wkn,
        fill='#00ff00', fill_opacity=1.0, stroke='#000000', stroke_width=1,
        stroke_opacity=1.0, stroke_dash_array='none')


def _text(rule, order=1):
    return TextSymbolizer.objects.create(
        rule=rule, order=order, is_actived=True, label='nombre', font_family='Arial',
        font_size=12, font_style='normal', font_weight='bold', fill='#000000',
        fill_opacity=1.0, halo_radius=1, halo_fill='#ffffff', halo_fill_opacity=1.0,
        anchor_point_x=0.5, anchor_point_y=-1.5)


class GoldenMixin(object):
    def assertGolden(self, name, content):
        if isinstance(content, bytes):
            content = content.decode('utf-8')
        path = os.path.join(GOLDEN_DIR, name)
        if UPDATE_GOLDEN or not os.path.exists(path):
            os.makedirs(GOLDEN_DIR, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            if not UPDATE_GOLDEN:
                self.fail('Fichero de referencia creado: %s. Revísalo y vuelve a ejecutar.' % name)
            return
        with open(path, encoding='utf-8') as f:
            expected = f.read()
        self.assertEqual(content, expected, 'La salida difiere de test_golden/%s' % name)


class BuildSldCharacterizationTest(GoldenMixin, TestCase):

    def build(self, style, geom=POLYGON_GEOM, single_symbol=False):
        with mock.patch.object(utils, 'get_geometry_field', return_value=geom):
            return sld_builder.build_sld(_layer(), style, single_symbol=single_symbol)

    def test_unique_symbol_polygon_with_label(self):
        style = _style('us_polygon', 'US', minscale=-1, maxscale=-1)
        r = _rule(style, 'us_polygon_rule', minscale=-1, maxscale=-1)
        _poly(r, order=0, dash='5 2')
        rt = _rule(style, 'us_polygon_text', minscale=-1, maxscale=-1, order=1)
        _text(rt)
        self.assertGolden('us_polygon_label.sld', self.build(style))

    def test_unique_symbol_line_with_label(self):
        style = _style('us_line', 'US')
        r = _rule(style, 'us_line_rule', minscale=1000, maxscale=50000)
        _line(r)
        rt = _rule(style, 'us_line_text', order=1)
        _text(rt)
        self.assertGolden('us_line_label.sld', self.build(style, geom=LINE_GEOM))

    def test_unique_symbol_point_mark_and_external_graphic(self):
        style = _style('us_point', 'US')
        r = _rule(style, 'us_point_rule')
        _mark(r, order=0, wkn='star')
        ExternalGraphicSymbolizer.objects.create(
            rule=r, order=1, opacity=1, size=20, rotation=45,
            online_resource='http://example.org/icon.png', format='image/png')
        rt = _rule(style, 'us_point_text', order=1)
        _text(rt)
        self.assertGolden('us_point_mark_eg.sld', self.build(style, geom=POINT_GEOM))

    def test_unique_values(self):
        style = _style('uv', 'UV')
        for i, val in enumerate(['A', 'B', 'C']):
            r = _rule(style, 'uv_%s' % val, {'type': 'is_equal_to', 'field': 'tipo',
                                             'operation': 'is_equal_to', 'value': val}, order=i)
            _poly(r, fill='#%02x0000' % (i * 60))
        r_null = _rule(style, 'uv_null', {'type': 'is_null', 'field': 'tipo',
                                          'operation': 'is_null', 'value': ''}, order=3)
        _poly(r_null)
        self.assertGolden('uv.sld', self.build(style))

    def test_intervals(self):
        style = _style('in', 'IN')
        bounds = [(0, 10), (10, 25.5), (25.5, 100)]
        for i, (v1, v2) in enumerate(bounds):
            r = _rule(style, 'in_%d' % i, {'type': 'is_between', 'field': 'valor',
                                           'operation': 'is_between', 'value1': v1, 'value2': v2}, order=i)
            _poly(r)
        self.assertGolden('in.sld', self.build(style))

    def test_expressions_all_single_operators(self):
        # Fija el comportamiento ACTUAL de cada operador en filtros de una sola condición
        # (is_less_than se corrigió: antes generaba PropertyIsGreaterThan).
        style = _style('ex', 'EX')
        ops = ['is_equal_to', 'is_less_than_or_equal_to', 'is_less_than',
               'is_greater_than_or_equal_to', 'is_greater_than', 'is_not_equal',
               'is_like', 'is_null']
        for i, op in enumerate(ops):
            r = _rule(style, 'ex_%s' % op, [{'type': 'expression', 'field': 'campo',
                                             'operation': op, 'value': '5'}], order=i)
            _poly(r)
        self.assertGolden('ex_single.sld', self.build(style))

    def test_expressions_complex_and_or(self):
        style = _style('ex_complex', 'EX')
        f_and = [
            {'type': 'expression', 'field': 'a', 'operation': 'is_greater_than', 'value': '1'},
            {'type': 'and'},
            {'type': 'expression', 'field': 'b', 'operation': 'is_less_than', 'value': '9'},
        ]
        f_or = [
            {'type': 'expression', 'field': 'c', 'operation': 'is_equal_to', 'value': 'x'},
            {'type': 'or'},
            {'type': 'expression', 'field': 'c', 'operation': 'is_like', 'value': 'y%'},
        ]
        _poly(_rule(style, 'ex_and', f_and, order=0))
        _poly(_rule(style, 'ex_or', f_or, order=1))
        self.assertGolden('ex_complex.sld', self.build(style))

    def test_clustered_points(self):
        style = _style('cp', 'CP')
        _mark(_rule(style, 'cp_single', [{'type': 'expression', 'field': 'count',
                                          'operation': 'is_equal_to', 'value': '1'}], order=0))
        _mark(_rule(style, 'cp_cluster', [{'type': 'expression', 'field': 'count',
                                           'operation': 'is_greater_than', 'value': '1'}], order=1))
        self.assertGolden('cp.sld', self.build(style, geom=POINT_GEOM))
        self.assertGolden('cp_single_symbol.sld',
                          self.build(style, geom=POINT_GEOM, single_symbol=True))

    def test_clustered_points_graphic_keeps_size_and_count_anchor(self):
        style = _style('cp_eg', 'CP')
        single = _rule(style, 'cp_single', [{'type': 'expression', 'field': 'count',
                                             'operation': 'is_equal_to', 'value': '1'}], order=0)
        _mark(single, order=0)
        group = _rule(style, 'cp_group', [{'type': 'expression', 'field': 'count',
                                           'operation': 'is_greater_than_or_equal_to', 'value': '2'}], order=1)
        ExternalGraphicSymbolizer.objects.create(
            rule=group, order=0, opacity=1, size=48, rotation=0,
            online_resource='http://example.org/tree.png', format='image/png')
        TextSymbolizer.objects.create(
            rule=group, order=1, is_actived=True, label='count', font_family='Arial',
            font_size=12, font_style='normal', font_weight='bold', fill='#ffffff',
            fill_opacity=1.0, halo_radius=1, halo_fill='#000000', halo_fill_opacity=0.6,
            anchor_point_x=0.5, anchor_point_y=0.8)
        sld = self.build(style, geom=POINT_GEOM).decode('utf-8')
        self.assertIn('tree.png', sld)
        self.assertIn('>48<', sld)
        self.assertIn('count', sld)
        self.assertIn('>0.8<', sld)
        # un único FeatureTypeStyle (la palabra aparece también en la etiqueta de cierre)
        self.assertEqual(sld.count('<sld:FeatureTypeStyle>'), 1)

    def test_point_label_anchor_stays_fixed_outside_clusters(self):
        style = _style('us_anchor', 'US')
        rule = _rule(style, 'us_anchor_rule')
        _mark(rule)
        TextSymbolizer.objects.create(
            rule=rule, order=1, is_actived=True, label='nombre', font_family='Arial',
            font_size=12, font_style='normal', font_weight='bold', fill='#000000',
            fill_opacity=1.0, halo_radius=1, halo_fill='#ffffff', halo_fill_opacity=1.0,
            anchor_point_x=0.5, anchor_point_y=0.8)
        sld = self.build(style, geom=POINT_GEOM).decode('utf-8')
        self.assertIn('-1.5', sld)
        self.assertNotIn('>0.8<', sld)

    def test_color_table_raster(self):
        style = _style('ct', 'CT')
        r = _rule(style, 'ct_rule')
        cmap = ColorMap.objects.create(type='intervals', extended=False)
        for i, (color, qty) in enumerate([('#000000', 0), ('#888888', 50.5), ('#ffffff', 100)]):
            ColorMapEntry.objects.create(order=i, color_map=cmap, color=color,
                                         quantity=qty, label='e%d' % i, opacity=1.0)
        RasterSymbolizer.objects.create(rule=r, order=0, opacity=1.0, color_map=cmap)
        self.assertGolden('ct.sld', self.build(style, geom=''))

    def test_geometry_field_is_queried_once_per_style(self):
        style = _style('geom_once', 'UV')
        for i in range(5):
            _poly(_rule(style, 'r%d' % i, order=i))
        with mock.patch.object(utils, 'get_geometry_field', return_value=POLYGON_GEOM) as m:
            sld_builder.build_sld(_layer(), style)
        self.assertEqual(m.call_count, 1)

    def test_geometry_field_not_queried_without_rules(self):
        style = _style('no_rules', 'US')
        with mock.patch.object(utils, 'get_geometry_field', return_value=POLYGON_GEOM) as m:
            sld_builder.build_sld(_layer(), style)
        self.assertEqual(m.call_count, 0)

    def test_symbolizer_order_is_descending_in_sld(self):
        style = _style('order', 'US')
        r = _rule(style, 'order_rule')
        _poly(r, order=0, fill='#111111')
        _poly(r, order=1, fill='#222222')
        sld = self.build(style).decode('utf-8')
        self.assertLess(sld.index('#222222'), sld.index('#111111'))


class SymbolizerToJsonCharacterizationTest(GoldenMixin, TestCase):

    def test_all_symbolizer_types(self):
        style = _style('json', 'US')
        r = _rule(style, 'json_rule')
        _poly(r, order=0)
        _line(r, order=1)
        _mark(r, order=2)
        _text(r, order=3)
        ExternalGraphicSymbolizer.objects.create(
            rule=r, order=4, opacity=1, size=20, rotation=0,
            online_resource='http://example.org/icon.png', format='image/png')
        out = []
        for s in Symbolizer.objects.filter(rule=r).order_by('order'):
            j = utils.symbolizer_to_json(s)
            # Los ids dependen de la secuencia de la BD de test: se normalizan.
            payload = json.loads(j['json'])
            for item in payload:
                item['pk'] = 'PK'
                item['fields'].pop('rule', None)
            j['json'] = payload
            out.append(j)
        self.assertGolden('symbolizer_to_json.json', json.dumps(out, indent=1, sort_keys=True))


class LayerManagerRequiredTest(TestCase):
    """Protección por capa de las vistas de simbología (Fase 1)."""

    def setUp(self):
        from django.test import RequestFactory
        from django.contrib.auth.models import AnonymousUser
        self.rf = RequestFactory()
        self.anon = AnonymousUser

    def _decorated(self):
        from gvsigol_symbology.views import layer_manager_required
        calls = []

        @layer_manager_required
        def view(request, layer_id=None, style_id=None):
            from django.http import HttpResponse
            calls.append((layer_id, style_id))
            return HttpResponse('ok')
        return view, calls

    def test_denies_when_user_cannot_manage_layer(self):
        view, calls = self._decorated()
        req = self.rf.post('/x/', {}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        with mock.patch('gvsigol_symbology.views.service_utils.can_manage_layer', return_value=False):
            resp = view(req, layer_id=1)
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(calls, [])

    def test_allows_manager_and_reads_layer_id_from_post(self):
        view, calls = self._decorated()
        req = self.rf.post('/x/', {'layer_id': '7'})
        with mock.patch('gvsigol_symbology.views.service_utils.can_manage_layer', return_value=True) as m:
            resp = view(req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(m.call_args[0][1], 7)

    def test_denies_style_not_belonging_to_layer(self):
        view, calls = self._decorated()
        style = _style('foreign', 'US')
        req = self.rf.post('/x/', {})
        with mock.patch('gvsigol_symbology.views.service_utils.can_manage_layer', return_value=True):
            resp = view(req, layer_id=999999, style_id=style.id)
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(calls, [])

    def test_denies_missing_layer_id(self):
        view, calls = self._decorated()
        req = self.rf.post('/x/', {})
        resp = view(req)
        self.assertEqual(resp.status_code, 403)


class MinMaxQueryTest(TestCase):
    """get_minmax_query escapa el campo como identificador."""

    def _sql_for(self, field):
        from django.db import connection
        from gvsigol_services import utils as service_utils
        captured = {}

        class Cur(object):
            def execute(self, sql):
                captured['sql'] = sql
                raise RuntimeError('stop')

        class Conn(object):
            def cursor(self):
                return Cur()

        with mock.patch.object(service_utils, 'get_connection', return_value=Conn()):
            self.assertEqual(service_utils.get_minmax_query('h', '1', 'public', 'db', 'u', 'p', 'capa', field), {})
        connection.ensure_connection()
        return captured['sql'].as_string(connection.connection)

    def test_valid_field_sql_unchanged(self):
        self.assertEqual(self._sql_for('poblacion'),
                         'SELECT MIN("poblacion") AS MinValue, MAX("poblacion") AS MaxValue '
                         'FROM public.capa WHERE "poblacion" IS NOT NULL;')

    def test_quotes_are_escaped(self):
        sql = self._sql_for('x") FROM pg_user; --')
        self.assertIn('"x"") FROM pg_user; --"', sql)


class UpdateStyleAtomicityTest(TestCase):
    """Un fallo a mitad de update_style no debe dejar el estilo sin reglas (Fase 2)."""

    def test_rules_preserved_when_update_fails(self):
        from gvsigol_symbology import services_unique_values
        style = _style('atomic_uv', 'UV')
        _poly(_rule(style, 'orig_a', order=0))
        _poly(_rule(style, 'orig_b', order=1))
        good_sym = {'type': 'PolygonSymbolizer', 'order': 0, 'json': json.dumps({
            'fill': '#fff', 'fill_opacity': 1, 'stroke': '#000', 'stroke_width': 1,
            'stroke_opacity': 1, 'stroke_dash_array': 'none'})}
        bad_sym = {'type': 'PolygonSymbolizer', 'order': 0, 'json': '{json roto'}
        rule_def = lambda name, order: {'name': name, 'title': name, 'filter': '',
                                        'minscale': -1, 'maxscale': -1, 'order': order}
        json_data = {'title': 'nuevo', 'minscale': '', 'maxscale': '', 'is_default': False,
                     'rules': [{'rule': rule_def('new_a', 0), 'symbolizers': [good_sym]},
                               {'rule': rule_def('new_b', 1), 'symbolizers': [bad_sym]}]}
        with mock.patch.object(utils, 'set_default_style', return_value=False), \
                mock.patch.object(utils, 'publish_style') as publish:
            with self.assertRaises(ValueError):
                services_unique_values.update_style(None, json_data, _layer(), mock.Mock(), style)
        publish.assert_not_called()
        names = sorted(Rule.objects.filter(style=style).values_list('name', flat=True))
        self.assertEqual(names, ['orig_a', 'orig_b'])
        style.refresh_from_db()
        self.assertEqual(style.title, 'atomic_uv title')


class ViewsSmokeTest(TestCase):
    """Smoke test de permisos sobre datos existentes (se omite si la BD no tiene capas con estilo)."""

    def setUp(self):
        from django.contrib.auth.models import User
        from gvsigol_symbology.models import StyleLayer
        self.sl = StyleLayer.objects.select_related('layer', 'style').filter(
            layer__external=False).first()
        if self.sl is None:
            self.skipTest('No hay capas con estilo en la BD')
        self.superuser = User.objects.create(username='zz_symb_super', is_staff=True, is_superuser=True)
        self.staff = User.objects.create(username='zz_symb_staff', is_staff=True)

    def test_superuser_lists_styles(self):
        self.client.force_login(self.superuser, backend='django.contrib.auth.backends.ModelBackend')
        resp = self.client.get('/gvsigonline/symbology/style_layer_list/')
        self.assertEqual(resp.status_code, 200)

    def test_staff_without_role_cannot_open_foreign_style(self):
        self.client.force_login(self.staff, backend='django.contrib.auth.backends.ModelBackend')
        url = '/gvsigonline/symbology/style_layer_update/%d/%d/' % (self.sl.layer_id, self.sl.style_id)
        with mock.patch('gvsigol_services.utils.auth_backend.get_roles', return_value=[]):
            resp = self.client.get(url)
        self.assertEqual(resp.status_code, 403)

    def test_staff_without_role_cannot_delete_foreign_style(self):
        self.client.force_login(self.staff, backend='django.contrib.auth.backends.ModelBackend')
        with mock.patch('gvsigol_services.utils.auth_backend.get_roles', return_value=[]):
            resp = self.client.post('/gvsigonline/symbology/style_layer_delete/',
                                    {'layer_id': self.sl.layer_id, 'style_id': self.sl.style_id})
        self.assertEqual(resp.status_code, 403)


class GeoserverProxyTest(TestCase):
    """Validación del proxy de previsualización (sustituye a la contraseña en el navegador)."""

    FRONTENDS = [('https://gvsigol.example.org/geoserver', 'http://gvsigol-geoserver:8080/geoserver')]

    def resolve(self, url, extra=()):
        from gvsigol_symbology import geoserver_proxy
        return geoserver_proxy.resolve_target(url, list(extra), self.FRONTENDS)

    def assertRejected(self, url, extra=()):
        from gvsigol_symbology import geoserver_proxy
        with self.assertRaises(geoserver_proxy.ProxyNotAllowed):
            self.resolve(url, extra)

    def test_relative_wms_tile(self):
        url, params = self.resolve('/geoserver/ws1/wms?SERVICE=WMS&REQUEST=GetMap&LAYERS=ws1:capa')
        self.assertEqual(url, 'http://gvsigol-geoserver:8080/geoserver/ws1/wms')
        self.assertIn(('LAYERS', 'ws1:capa'), params)

    def test_absolute_wfs_with_extra_params(self):
        url, params = self.resolve('https://gvsigol.example.org/geoserver/ws1/wfs',
                                   [('service', 'WFS'), ('request', 'GetFeature'), ('typename', 'ws1:capa')])
        self.assertEqual(url, 'http://gvsigol-geoserver:8080/geoserver/ws1/wfs')
        self.assertIn(('typename', 'ws1:capa'), params)

    def test_rejects_other_hosts_and_paths(self):
        self.assertRejected('https://evil.example.org/geoserver/wms?SERVICE=WMS&REQUEST=GetMap')
        self.assertRejected('/gvsigonline/admin/?SERVICE=WMS&REQUEST=GetMap')
        self.assertRejected('/geoserverX/wms?SERVICE=WMS&REQUEST=GetMap')
        self.assertRejected('/geoserver/../gvsigonline/?SERVICE=WMS&REQUEST=GetMap')
        self.assertRejected('file:///etc/passwd')

    def test_rejects_write_or_rest_operations(self):
        self.assertRejected('/geoserver/rest/styles?SERVICE=WMS&REQUEST=GetMap'.replace('SERVICE=WMS', 'SERVICE=REST'))
        self.assertRejected('/geoserver/ows?SERVICE=WFS&REQUEST=Transaction')
        self.assertRejected('/geoserver/wms')

    def test_context_never_contains_password(self):
        from django.test import RequestFactory
        req = RequestFactory().get('/')
        req.session = {'username': 'u', 'password': 'secreto'}
        conf = {}
        utils.set_auth_settings(req, conf)
        self.assertNotIn('secreto', json.dumps(conf))
        self.assertTrue(conf['gs_proxy'])
        # Keycloak: el token tampoco llega al navegador (caduca antes de renovarse); va por el proxy
        req.session = {'username': 'u', 'oidc_access_token': 'tok'}
        conf = {}
        utils.set_auth_settings(req, conf)
        self.assertNotIn('tok', json.dumps(conf))
        self.assertNotIn('auth_token', conf)
        self.assertTrue(conf['gs_proxy'])

    def test_path_workspace(self):
        from gvsigol_symbology import geoserver_proxy as gp
        base = 'https://gvsigol.example.org/geoserver'
        self.assertEqual(gp.path_workspace('/geoserver/ws1/wms?x=1', base), 'ws1')
        self.assertEqual(gp.path_workspace(base + '/ws1/wfs', base), 'ws1')
        self.assertIsNone(gp.path_workspace('/geoserver/wms', base))
        self.assertIsNone(gp.path_workspace('/geoserver/ws1/gwc/service/wms', base))
        # GeoServer en la raíz del dominio
        self.assertEqual(gp.path_workspace('https://gs.example.org/ws1/ows', 'https://gs.example.org'), 'ws1')
        self.assertIsNone(gp.path_workspace('https://gs.example.org/wms', 'https://gs.example.org'))

    def test_requested_layers(self):
        from gvsigol_symbology import geoserver_proxy as gp
        params = [('LAYERS', 'ws1:a, b'), ('typename', 'ws2:c'), ('STYLES', 'x')]
        self.assertEqual(gp.requested_layers(params, 'wsp'), [('ws1', 'a'), ('wsp', 'b'), ('ws2', 'c')])

    def test_check_service_request(self):
        from gvsigol_symbology import geoserver_proxy as gp
        readable = {('ws1', 'capa')}
        can_read = lambda ws, name: (ws, name) in readable

        def ok(params, ws=None):
            gp.check_service_request(params, ws, can_read)

        def rejected(params, ws=None):
            with self.assertRaises(gp.ProxyNotAllowed):
                gp.check_service_request(params, ws, can_read)

        ok([('SERVICE', 'WMS'), ('REQUEST', 'GetMap'), ('LAYERS', 'ws1:capa'), ('STYLES', 'ws1_capa__tmp')])
        ok([('service', 'WFS'), ('request', 'GetFeature'), ('typename', 'capa')], ws='ws1')
        ok([('REQUEST', 'GetLegendGraphic'), ('LAYER', 'preview_polygon')])
        rejected([('REQUEST', 'GetMap'), ('LAYERS', 'ws1:otra')])                  # sin permiso
        rejected([('REQUEST', 'GetMap'), ('LAYERS', 'ws1:capa,ws1:otra')])         # una de ellas sin permiso
        rejected([('REQUEST', 'GetMap'), ('LAYERS', 'capa')])                      # sin espacio de trabajo
        rejected([('REQUEST', 'GetMap')])                                          # sin capas
        rejected([('REQUEST', 'GetCapabilities'), ('LAYERS', 'ws1:capa')])
        rejected([('REQUEST', 'GetMap'), ('LAYER', 'otro:preview_point')])         # no es la capa técnica
        for param in ('SLD', 'SLD_BODY', 'cql_filter', 'FILTER', 'viewparams', 'FEATUREID'):
            rejected([('REQUEST', 'GetMap'), ('LAYERS', 'ws1:capa'), (param, 'x')])

    def test_view_forwards_with_session_credentials(self):
        from django.contrib.auth.models import User
        from gvsigol_services.models import Server
        user = User.objects.create(username='zz_symb_proxy', is_staff=True)
        self.client.force_login(user, backend='django.contrib.auth.backends.ModelBackend')
        frontend = Server.objects.exclude(frontend_url='').values_list('frontend_url', flat=True).first()
        if not frontend:
            self.skipTest('No hay Server configurado')
        session = self.client.session
        session['password'] = 'secreto'   # sesión con contraseña: credenciales del propio usuario
        session.save()
        fake = mock.Mock(status_code=200, content=b'PNG', headers={'Content-Type': 'image/png'})
        with mock.patch('gvsigol_symbology.views.service_utils.getUserAuthSession') as sess:
            sess.return_value.get.return_value = fake
            resp = self.client.get('/gvsigonline/symbology/geoserver_proxy/', {
                'url': frontend.rstrip('/') + '/wms?SERVICE=WMS&REQUEST=GetMap&LAYERS=x'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content, b'PNG')
        self.assertEqual(resp['Content-Type'], 'image/png')
        resp = self.client.get('/gvsigonline/symbology/geoserver_proxy/', {'url': 'http://169.254.169.254/?SERVICE=WMS&REQUEST=GetMap'})
        self.assertEqual(resp.status_code, 403)

    def test_view_keycloak_session_uses_service_credentials_after_permission_check(self):
        from django.contrib.auth.models import User
        from gvsigol_services.models import Server
        user = User.objects.create(username='zz_symb_proxy_oidc', is_staff=True)
        self.client.force_login(user, backend='django.contrib.auth.backends.ModelBackend')
        session = self.client.session
        session['oidc_access_token'] = 'caducado'   # sin contraseña: modo servicio
        session.save()
        frontend = Server.objects.exclude(frontend_url='').values_list('frontend_url', flat=True).first()
        if not frontend:
            self.skipTest('No hay Server configurado')
        url = frontend.rstrip('/') + '/ws1/wms?SERVICE=WMS&REQUEST=GetMap&LAYERS=ws1:capa'
        fake = mock.Mock(status_code=200, content=b'PNG', headers={'Content-Type': 'image/png'})
        with mock.patch('gvsigol_symbology.views._service_session') as service, \
                mock.patch('gvsigol_symbology.views.service_utils.getUserAuthSession') as user_session, \
                mock.patch('gvsigol_symbology.views._can_read_layer_fn') as can_read_fn:
            service.return_value.get.return_value = fake
            can_read_fn.return_value = lambda ws, name: (ws, name) == ('ws1', 'capa')
            resp = self.client.get('/gvsigonline/symbology/geoserver_proxy/', {'url': url})
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.content, b'PNG')
            user_session.assert_not_called()   # el token caducado de la sesión no se usa
            # Capa sin permiso, o parámetros que podrían leer otras capas: rechazado antes de pedir nada
            service.reset_mock()
            for bad in (url.replace('ws1:capa', 'ws1:otra'), url + '&SLD_BODY=x', url + '&CQL_FILTER=x',
                        url.replace('GetMap', 'GetCapabilities')):
                resp = self.client.get('/gvsigonline/symbology/geoserver_proxy/', {'url': bad})
                self.assertEqual(resp.status_code, 403, bad)
            service.return_value.get.assert_not_called()


class RegenerateCommandDetectionTest(TestCase):
    """Detección de estilos afectados por la corrección de is_less_than."""

    def test_detects_only_single_condition_less_than(self):
        from gvsigol_symbology.management.commands.regenerate_symbology_sld import style_uses_single_less_than
        single_list = _style('lt_list', 'EX')
        _rule(single_list, 'r', [{'type': 'expression', 'field': 'a', 'operation': 'is_less_than', 'value': '1'}])
        single_dict = _style('lt_dict', 'UV')
        _rule(single_dict, 'r', {'type': 'is_less_than', 'field': 'a', 'operation': 'is_less_than', 'value': '1'})
        complex_f = _style('lt_complex', 'CP')
        _rule(complex_f, 'r', [
            {'type': 'expression', 'field': 'count', 'operation': 'is_greater_than', 'value': '1'},
            {'type': 'and'},
            {'type': 'expression', 'field': 'count', 'operation': 'is_less_than', 'value': '9'}])
        other = _style('lt_other', 'EX')
        _rule(other, 'r', [{'type': 'expression', 'field': 'a', 'operation': 'is_less_than_or_equal_to', 'value': '1'}])
        no_filter = _style('lt_none', 'US')
        _rule(no_filter, 'r')
        self.assertTrue(style_uses_single_less_than(single_list))
        self.assertTrue(style_uses_single_less_than(single_dict))
        self.assertFalse(style_uses_single_less_than(complex_f))
        self.assertFalse(style_uses_single_less_than(other))
        self.assertFalse(style_uses_single_less_than(no_filter))


def _all_symbolizers_json():
    def sym(t, order, d):
        return {'type': t, 'order': order, 'json': json.dumps(d)}
    return [
        sym('PolygonSymbolizer', 0, {'fill': '#aa0000', 'fill_opacity': 0.4, 'stroke': '#000000', 'stroke_width': 2,
                                     'stroke_opacity': 0.9, 'stroke_dash_array': '4 2'}),
        sym('LineSymbolizer', 1, {'stroke': '#00aa00', 'stroke_width': 3, 'stroke_opacity': 0.7, 'stroke_dash_array': 'none'}),
        sym('MarkSymbolizer', 2, {'opacity': 1, 'size': 12, 'rotation': 30, 'well_known_name': 'triangle', 'fill': '#0000aa',
                                  'fill_opacity': 0.5, 'stroke': '#111111', 'stroke_width': 1, 'stroke_opacity': 1,
                                  'stroke_dash_array': 'none'}),
        sym('ExternalGraphicSymbolizer', 3, {'opacity': 1, 'size': 24, 'rotation': 0,
                                             'online_resource': 'http://example.org/i.png', 'format': 'image/png'}),
        sym('TextSymbolizer', 4, {'label': 'nombre', 'font_family': 'Arial', 'font_size': 11, 'font_weight': 'bold',
                                  'font_style': 'italic', 'fill': '#222222', 'fill_opacity': 0.8, 'halo_fill': '#ffffff',
                                  'halo_fill_opacity': 0.6, 'halo_radius': 2, 'anchor_point_x': 0.25, 'anchor_point_y': 0.75}),
        sym('TipoDesconocido', 5, {}),
    ]


def _style_payload(name, minscale='', maxscale=''):
    rules = []
    for i, flt in enumerate(['', [{'type': 'expression', 'field': 'f', 'operation': 'is_equal_to', 'value': 'x'}]]):
        rules.append({'rule': {'name': '%s_r%d' % (name, i), 'title': 'T%d' % i, 'filter': flt,
                               'minscale': -1, 'maxscale': -1, 'order': i},
                      'symbolizers': _all_symbolizers_json()})
    return {'name': name, 'title': name + ' t', 'minscale': minscale, 'maxscale': maxscale,
            'is_default': False, 'rules': rules}


def _dump_style(style):
    out = []
    for r in Rule.objects.filter(style=style).order_by('order', 'id'):
        syms = []
        for s in Symbolizer.objects.filter(rule=r).order_by('order', 'id'):
            j = utils.symbolizer_to_json(s)
            payload = json.loads(j['json'])
            for item in payload:
                item['pk'] = 'PK'
                item['fields'].pop('rule', None)
            j['json'] = payload
            syms.append(j)
        out.append({'name': r.name, 'title': r.title, 'filter': r.filter, 'order': r.order,
                    'minscale': r.minscale, 'maxscale': r.maxscale, 'symbolizers': syms})
    return json.dumps({'type': style.type, 'title': style.title, 'minscale': style.minscale,
                       'maxscale': style.maxscale, 'rules': out}, indent=1, sort_keys=True)


class StyleServicesCharacterizationTest(GoldenMixin, TestCase):
    """Fija lo que create_style/update_style guardan en BD para cada tipo de leyenda vectorial."""

    MODULES = ['services_unique_symbol', 'services_unique_values', 'services_intervals',
               'services_expressions', 'services_clustered_points']

    def _patches(self, module):
        return [
            mock.patch.object(utils, 'begin_style_creation', return_value=None),
            mock.patch.object(utils, 'resolve_is_default', return_value=False),
            mock.patch.object(utils, 'set_default_style', return_value=False),
            mock.patch.object(utils, 'publish_style', side_effect=lambda gs, layer, style, sld, **kw: style),
            mock.patch.object(sld_builder, 'build_sld', return_value=b'<sld/>'),
            mock.patch.object(module, 'StyleLayer'),
        ]

    def _run(self, modname, op, scales):
        import importlib
        from contextlib import ExitStack
        module = importlib.import_module('gvsigol_symbology.' + modname)
        payload = _style_payload(modname, *scales)
        with ExitStack() as stack:
            for p in self._patches(module):
                stack.enter_context(p)
            if op == 'create':
                style = module.create_style(None, payload, _layer(), mock.Mock())
            else:
                style = _style(modname + '_upd', 'US')
                _poly(_rule(style, 'old_rule'))
                style = module.update_style(None, payload, _layer(), mock.Mock(), style)
        return style

    def _cases(self):
        for modname in self.MODULES:
            yield modname, ('1000', '50000'), 'scales'
            if modname != 'services_unique_symbol':  # US.create_style no admite escala vacía (comportamiento actual)
                yield modname, ('', ''), 'noscale'

    def test_create_style(self):
        for modname, scales, tag in self._cases():
            with self.subTest(modname, tag=tag):
                self.assertGolden('svc_create_%s_%s.json' % (modname, tag),
                                  _dump_style(self._run(modname, 'create', scales)))

    def test_update_style(self):
        for modname, scales, tag in self._cases():
            with self.subTest(modname, tag=tag):
                self.assertGolden('svc_update_%s_%s.json' % (modname, tag),
                                  _dump_style(self._run(modname, 'update', scales)))


class ViewHelpersTest(TestCase):
    """Helpers extraídos de las vistas (Fase 3): mismo resultado que los bloques duplicados."""

    def test_rule_to_dict(self):
        from gvsigol_symbology.views import _rule_to_dict
        style = _style('helper', 'UV')
        r = _rule(style, 'r1', {'field': 'f', 'operation': 'is_equal_to', 'value': 'a'},
                  order=3, minscale=10, maxscale=20, title='Título')
        _poly(r, order=1)
        _line(r, order=0)
        d = _rule_to_dict(r)
        self.assertEqual(set(d), {'id', 'name', 'title', 'abstract', 'filter', 'minscale', 'maxscale', 'order', 'symbolizers'})
        self.assertEqual((d['id'], d['name'], d['title'], d['abstract'], d['order'], d['minscale'], d['maxscale']),
                         (r.id, 'r1', 'Título', '', 3, 10, 20))
        self.assertEqual(d['filter'], r.filter)
        self.assertEqual([x['type'] for x in d['symbolizers']], ['LineSymbolizer', 'PolygonSymbolizer'])

    def test_style_saved_response_default_and_cached(self):
        from gvsigol_symbology import views
        gs = mock.Mock()
        layer = mock.Mock(cached=True)
        style = mock.Mock(is_default=True)
        with mock.patch.object(views, 'delete_preview_style') as dps, \
                mock.patch.object(views, 'do_layer_cache_clear') as clear:
            resp = views._style_saved_response(None, style, layer, gs, 'nombre')
        dps.assert_called_once_with(None, 'nombre', gs)
        gs.reload_nodes.assert_called_once_with()
        gs.updateThumbnail.assert_called_once_with(layer)
        clear.assert_called_once_with(layer, gs)
        self.assertEqual(json.loads(resp.content), {'success': True})

    def test_style_saved_response_not_default(self):
        from gvsigol_symbology import views
        gs = mock.Mock()
        with mock.patch.object(views, 'delete_preview_style'), \
                mock.patch.object(views, 'do_layer_cache_clear') as clear:
            views._style_saved_response(None, mock.Mock(is_default=False), mock.Mock(cached=True), gs, 'n')
        gs.updateThumbnail.assert_not_called()
        clear.assert_not_called()


class GetConfCharacterizationTest(GoldenMixin, TestCase):
    """Fija la salida de get_conf de los tipos vectoriales (GeoServer simulado, capa real de la BD)."""

    MODULES = ['services_unique_symbol', 'services_unique_values', 'services_intervals',
               'services_expressions', 'services_clustered_points', 'services_map_heat']
    FIELDS = [
        {'name': 'nombre', 'binding': 'java.lang.String'},
        {'name': 'poblacion', 'binding': 'java.lang.Integer'},
        {'name': 'superficie', 'binding': 'java.lang.Double'},
        {'name': 'geom', 'binding': 'org.locationtech.jts.geom.MultiPolygon'},
    ]

    def setUp(self):
        self.layer = Layer.objects.filter(external=False).select_related('datastore__workspace__server').first()
        if self.layer is None:
            self.skipTest('No hay capas en la BD')

    def _conf(self, modname, layer_conf):
        import copy, importlib
        from contextlib import ExitStack
        from django.test import RequestFactory
        module = importlib.import_module('gvsigol_symbology.' + modname)
        self.layer.conf = layer_conf
        gs = mock.Mock()
        gs.getResourceInfo.return_value = ('featureType', {})
        gs.getSupportedFonts.return_value = json.dumps({'fonts': ['Verdana', 'Arial', 'DejaVu Sans']})
        req = RequestFactory().get('/')
        req.session = {'username': 'u', 'password': 'p'}
        with ExitStack() as st:
            st.enter_context(mock.patch.object(Layer.objects, 'get', return_value=self.layer))
            inst = st.enter_context(mock.patch('gvsigol_services.geographic_servers.get_instance'))
            inst.return_value.get_server_by_id.return_value = gs
            st.enter_context(mock.patch.object(utils, 'get_fields', side_effect=lambda r: copy.deepcopy(self.FIELDS)))
            st.enter_context(mock.patch.object(utils, 'get_next_index', return_value=7))
            conf = module.get_conf(req, self.layer.id)
        out = {}
        for k, v in conf.items():
            if hasattr(v, 'model'):
                v = '<QuerySet %s>' % v.model.__name__   # contenido dependiente de la BD
            elif k in ('layer_url', 'layer_wfs_url', 'supported_crs'):
                v = '<env>'
            elif k == 'preview_url':
                v = '<env>' + v.split('&LAYER=')[-1] if v else v
            out[k] = v
        # Normaliza lo que depende de la capa elegida (para que el golden no dependa de la BD)
        ws = self.layer.datastore.workspace
        txt = json.dumps(out, indent=1, sort_keys=True, default=str)
        for real, fake in ((ws.name + ':' + self.layer.name, 'WS:LAYER'), (ws.name + '_' + self.layer.name, 'WS_LAYER'),
                           ('"layer_id": %d' % self.layer.id, '"layer_id": "ID"')):
            txt = txt.replace(real, fake)
        return txt

    def test_get_conf_without_layer_conf(self):
        for modname in self.MODULES:
            with self.subTest(modname):
                self.assertGolden('conf_%s_plain.json' % modname, self._conf(modname, None))

    def test_get_conf_with_field_titles(self):
        layer_conf = str({'fields': [{'name': 'nombre', 'title-es': 'Nombre', 'title-en': 'Name'},
                                     {'name': 'poblacion'}]})
        for modname in self.MODULES:
            with self.subTest(modname):
                self.assertGolden('conf_%s_titles.json' % modname, self._conf(modname, layer_conf))


class JsonForScriptTest(TestCase):
    def test_cannot_close_script_and_roundtrips(self):
        value = [{'title': '</script><script>alert(1)</script>', 'name': 'a & b > c', 'n': 1.5, 'u': 'ñ€'}]
        out = utils.json_for_script(value)
        self.assertNotIn('<', out)
        self.assertNotIn('>', out)
        self.assertNotIn('&', out)
        self.assertEqual(json.loads(out), value)

    def test_same_as_json_dumps_for_plain_values(self):
        value = {'fields': [{'name': 'poblacion', 'binding': 'java.lang.Integer'}]}
        self.assertEqual(utils.json_for_script(value), json.dumps(value))


class TemplatesRenderWithRealContextTest(TestCase):
    """
    Renderiza plantillas con el contexto MÍNIMO que pasa cada vista (no un contexto completo):
    un argumento de filtro o de {% url %} que falte rompe la página con un 500.
    """

    def _render(self, template, ctx):
        from types import SimpleNamespace as NS
        from django.contrib.auth.models import User
        from django.template.loader import render_to_string
        from django.test import RequestFactory
        req = RequestFactory().get('/gvsigonline/symbology/')
        req.user = User(id=999999, username='tester', is_staff=True, is_superuser=True)
        req.session = {}
        return render_to_string(template, ctx, request=req)

    def test_contexts(self):
        from types import SimpleNamespace as NS
        library = NS(id=1, name='lib', description='d')
        folder = NS(id=6, name='f', description='d')
        ramp = NS(id=5, name='r', definition='{}', color_ramp_folder_id=6)
        rule = {'id': 3, 'name': 'r', 'title': 't', 'minscale': -1, 'maxscale': -1, 'order': 0,
                'type': 'PolygonSymbolizer', 'symbolizers': '[]', 'symbolizer_format': 'image/png',
                'symbolizer_size': 24, 'symbolizer_online_resource': ''}
        cases = [
            ('color_ramp_add.html', {'folder': folder, 'library': library, 'color_ramps': [], 'message': ''}, 'color_ramp_folder_update/6/'),
            ('color_ramp_update.html', {'color_ramp': ramp, 'message': ''}, 'color_ramp_folder_update/6/'),
            ('color_ramp_folder_add.html', {'library': library}, 'color_ramp_library_update/1/'),
            ('color_ramp_folder_update.html', {'folder': folder, 'folders': [], 'library': library, 'color_ramps': []}, 'color_ramp_library_update/1/'),
            ('color_ramp_library_update.html', {'library': library, 'folders': []}, 'color_ramp_library_list/'),
            ('library_add.html', {}, 'library_list/'),
            ('library_import.html', {'message': 'x'}, 'library_list/'),
            ('color_ramp_library_add.html', {}, 'color_ramp_library_list/'),
            ('color_ramp_library_import.html', {}, 'color_ramp_library_list/'),
            ('library_update.html', {'library': library, 'rules': []}, 'library_list/'),
            ('symbol_add.html', {'library_id': 1, 'symbol_type': 'PolygonSymbolizer'}, 'library_update/1/'),
            ('symbol_update.html', {'rule': rule, 'library_id': 1}, 'library_update/1/'),
            ('external_graphic_add.html', {'library_id': 1, 'symbol_type': 'ExternalGraphicSymbolizer'}, 'library_update/1/'),
            ('external_graphic_update.html', {'rule': rule}, 'library_list/'),   # la vista no pasa library_id
            ('select_legend_type.html', {'layer': NS(id=2, name='capa', title=None), 'is_vectorial': False}, 'style_layer_list/'),
            ('sld_import.html', {'layer_id': 2, 'style_name': 'ws_capa_1'}, 'style_layer_list/'),
        ]
        for template, ctx, expected_link in cases:
            with self.subTest(template):
                html = self._render(template, ctx)
                self.assertIn(expected_link, html)


# ---------------------------------------------------------------------------
# Etiquetado (Fase 0 de la mejora de etiquetas): fija el SLD que generan HOY las
# etiquetas. Las etiquetas existentes no pueden cambiar en nada.
# ---------------------------------------------------------------------------
def _label(rule, order=1, **kw):
    values = dict(is_actived=True, label='nombre', font_family='Arial', font_size=12, font_style='normal',
                  font_weight='normal', fill='#000000', fill_opacity=1.0, halo_radius=1, halo_fill='#ffffff',
                  halo_fill_opacity=1.0, anchor_point_x=0.5, anchor_point_y=-1.5)
    values.update(kw)
    return TextSymbolizer.objects.create(rule=rule, order=order, **values)


class LabelSldCharacterizationTest(GoldenMixin, TestCase):
    GEOMS = {
        'point': {'field_name': 'wkb_geometry', 'field_type': 'POINT'},
        'multipoint': {'field_name': 'wkb_geometry', 'field_type': 'MULTIPOINT'},
        'line': {'field_name': 'wkb_geometry', 'field_type': 'LINESTRING'},
        'multiline': {'field_name': 'wkb_geometry', 'field_type': 'MULTILINESTRING'},
        'polygon': {'field_name': 'geom', 'field_type': 'POLYGON'},
        'multipolygon': {'field_name': 'geom', 'field_type': 'MULTIPOLYGON'},
    }

    def build(self, style, geom):
        with mock.patch.object(utils, 'get_geometry_field', return_value=geom):
            return sld_builder.build_sld(_layer(), style)

    def _style_with_label(self, name, **label_kw):
        style = _style(name, 'UV')
        _poly(_rule(style, name + '_r0'))
        rt = _rule(style, name + '_text', order=1, minscale=-1, maxscale=-1)
        _label(rt, **label_kw)
        return style

    def test_label_per_geometry_type(self):
        for gname, geom in self.GEOMS.items():
            with self.subTest(gname):
                style = self._style_with_label('lbl_' + gname)
                self.assertGolden('label_geom_%s.sld' % gname, self.build(style, geom))

    def test_label_options_currently_stored(self):
        # Valores guardados que hoy el SLD ignora o usa (anclaje, cursiva, opacidades, halo)
        style = self._style_with_label('lbl_opts', anchor_point_x=0.2, anchor_point_y=0.9, font_style='italic',
                                       font_weight='bold', font_size=15, fill='#123456', fill_opacity=0.5,
                                       halo_radius=3, halo_fill='#fedcba', halo_fill_opacity=0.25, font_family='DejaVu Sans')
        for gname in ('point', 'line', 'polygon'):
            with self.subTest(gname):
                self.assertGolden('label_opts_%s.sld' % gname, self.build(style, self.GEOMS[gname]))

    def test_label_inactive_and_with_filter_and_scales(self):
        style = _style('lbl_misc', 'EX')
        _poly(_rule(style, 'lbl_misc_r0'))
        rt = _rule(style, 'lbl_misc_text', [{'type': 'expression', 'field': 'tipo', 'operation': 'is_equal_to', 'value': 'A'}],
                   order=1, minscale=1000, maxscale=50000)
        _label(rt, is_actived=False)
        self.assertGolden('label_inactive_filter_scales.sld', self.build(style, self.GEOMS['polygon']))

    def test_label_only_text_rule_not_named_text(self):
        # Una regla solo con TextSymbolizer, aunque no termine en _text, se marca mapOnly
        style = _style('lbl_onlytext', 'US')
        _label(_rule(style, 'regla_etiqueta'), order=0)
        self.assertGolden('label_only_text_rule.sld', self.build(style, self.GEOMS['point']))

    def test_label_without_postgis_geometry_fails_today(self):
        # Comportamiento ACTUAL (bug existente): si la capa no es v_PostGIS, get_geometry_field
        # devuelve '' y el bloque de etiquetas falla. Se documenta para no cambiarlo sin querer.
        style = self._style_with_label('lbl_nogeom')
        with self.assertRaises(TypeError):
            self.build(style, '')


class LabelOptionsNormalizeTest(TestCase):
    """label_options: solo claves conocidas, valores acotados y nombres de campo seguros."""

    def test_empty_or_invalid_is_legacy(self):
        from gvsigol_symbology import label_options as lo
        for raw in (None, '', '{}', 'no es json', '[1,2]', '"texto"'):
            self.assertIsNone(lo.normalize(raw), raw)

    def test_defaults_and_clamping(self):
        from gvsigol_symbology import label_options as lo
        o = lo.normalize({'v': 1, 'placement': {'point': {'position': 'nope', 'dx': 9999, 'dy': 'x'},
                                                 'line': {'repeat': -5, 'max_angle': 500}, 'wrap': 99999},
                          'style': {'letter_spacing': 100, 'halo': 'si'}, 'desconocida': {'a': 1}})
        self.assertEqual(o['placement']['point'], {'position': 'top', 'dx': 200, 'dy': 0})
        self.assertEqual(o['placement']['line']['repeat'], 0)
        self.assertEqual(o['placement']['line']['max_angle'], 90)
        self.assertEqual(o['placement']['wrap'], 2000)
        self.assertEqual(o['style'], {'letter_spacing': 30, 'halo': True})
        self.assertNotIn('desconocida', o)

    def test_unsafe_values_are_dropped(self):
        from gvsigol_symbology import label_options as lo
        o = lo.normalize({'content': {'parts': [
            {'type': 'field', 'name': 'nombre'},
            {'type': 'field', 'name': 'x"/><evil'},
            {'type': 'field', 'name': 'otro', 'date': 'formato raro'},
            {'type': 'text', 'value': 'a' * 500},
            {'type': 'script', 'value': 'x'}]},
            'priority': {'field': '1; DROP'}, 'background': {'type': 'box', 'fill': 'red', 'stroke': '#12345'}},
            allowed_fields=['nombre', 'poblacion'])
        self.assertEqual([p.get('name') for p in o['content']['parts'] if p['type'] == 'field'], ['nombre'])
        self.assertEqual(len(o['content']['parts'][1]['value']), 100)
        self.assertIsNone(o['priority']['field'])
        self.assertEqual((o['background']['fill'], o['background']['stroke']), ('#ffffff', '#000000'))

    def test_roundtrip_is_stable(self):
        from gvsigol_symbology import label_options as lo
        o = lo.normalize({'content': {'case': 'upper'}})
        self.assertEqual(lo.normalize(lo.dumps(o)), o)


class LabelOptionsPersistenceTest(TestCase):
    """symbolizer_factory guarda las opciones normalizadas solo si el editor las envía."""

    def test_factory(self):
        from gvsigol_symbology import symbolizer_factory, label_options as lo
        style = _style('persist', 'US')
        rule = _rule(style, 'persist_text')
        base = {'label': 'nombre', 'font_family': 'Arial', 'font_size': 12, 'font_weight': 'normal',
                'font_style': 'normal', 'halo_fill': '#ffffff', 'halo_fill_opacity': 1, 'halo_radius': 1,
                'fill': '#000000', 'fill_opacity': 1}
        old = symbolizer_factory.create_symbolizer_from_json(rule, {'type': 'TextSymbolizer', 'order': 0, 'json': json.dumps(base)})
        self.assertIsNone(old.options)
        new = symbolizer_factory.create_symbolizer_from_json(rule, {'type': 'TextSymbolizer', 'order': 1, 'json': json.dumps(
            dict(base, options={'content': {'case': 'upper'}, 'cosa_rara': 1}))})
        saved = json.loads(new.options)
        self.assertEqual(saved['content']['case'], 'upper')
        self.assertNotIn('cosa_rara', saved)
        self.assertEqual(saved, lo.normalize(saved))


NEW_LABEL_CASES = {
    # nombre: (geometría, opciones)
    'point_default': ('point', {'v': 1}),
    'point_bottom_right_displaced_rotated': ('point', {'placement': {'point': {'position': 'bottom-right', 'dx': 4, 'dy': -6},
                                                                     'rotation': {'angle': 30}}}),
    'point_rotation_field': ('point', {'placement': {'rotation': {'field': 'angulo'}}}),
    'content_compound_upper': ('point', {'content': {'case': 'upper', 'parts': [
        {'type': 'field', 'name': 'nombre'}, {'type': 'text', 'value': ' ('},
        {'type': 'field', 'name': 'poblacion', 'number': {'decimals': 0, 'thousands': True}},
        {'type': 'text', 'value': ' hab.)'}]}}),
    'content_date': ('point', {'content': {'parts': [{'type': 'field', 'name': 'fecha', 'date': 'dd/MM/yyyy'}]}}),
    'line_follow_repeat_offset': ('line', {'placement': {'line': {'follow': True, 'repeat': 300, 'offset': 8, 'max_angle': 30}}}),
    'line_no_follow': ('multiline', {'placement': {'line': {'follow': False}}}),
    'polygon_interior': ('polygon', {'v': 1}),
    'polygon_centroid_rotated': ('multipolygon', {'placement': {'polygon': {'mode': 'centroid'}, 'rotation': {'angle': -15}}}),
    'priority_overlap_spacing_nohalo': ('point', {'priority': {'field': 'poblacion', 'allow_overlap': True, 'space_around': 5},
                                                  'placement': {'wrap': 0}, 'style': {'letter_spacing': 2, 'halo': False}}),
    'background_box': ('point', {'background': {'type': 'box', 'fill': '#ffffee', 'fill_opacity': 0.8,
                                                'stroke': '#333333', 'stroke_width': 1, 'padding': 3}}),
    # Recuadro de fondo y texto en varias líneas (label_sld.box_layout, fallo de GeoTools)
    'box_polygon_independent': ('polygon', {'background': {'type': 'box', 'fill': '#25d4c9', 'fill_opacity': 1, 'stroke': '#064728', 'stroke_width': 2.5, 'padding': 14}}),
    'box_polygon_rotated_single_line': ('polygon', {'background': {'type': 'box', 'fill': '#25d4c9', 'fill_opacity': 1, 'stroke': '#064728', 'stroke_width': 2.5, 'padding': 14}, 'placement': {'rotation': {'angle': 20}}}),
    'box_point_center_independent': ('point', {'background': {'type': 'box', 'fill': '#25d4c9', 'fill_opacity': 1, 'stroke': '#064728', 'stroke_width': 2.5, 'padding': 14}, 'placement': {'point': {'position': 'center'}}}),
    'box_point_right_keeps_wrap': ('point', {'background': {'type': 'box', 'fill': '#25d4c9', 'fill_opacity': 1, 'stroke': '#064728', 'stroke_width': 2.5, 'padding': 14}, 'placement': {'point': {'position': 'right'}}}),
    'box_line_single_line': ('line', {'background': {'type': 'box', 'fill': '#25d4c9', 'fill_opacity': 1, 'stroke': '#064728', 'stroke_width': 2.5, 'padding': 14}}),
    'escaping': ('point', {'content': {'parts': [{'type': 'text', 'value': '</sld:Label><evil a="1"/> & <'},
                                                 {'type': 'field', 'name': 'nombre'}]}}),
}


class NewLabelSldTest(GoldenMixin, TestCase):
    """SLD de las etiquetas NUEVAS (con options), una referencia por opción."""

    def build(self, geom_name, options, **label_kw):
        style = _style('new_lbl', 'UV')
        _poly(_rule(style, 'new_lbl_r0'))
        rt = _rule(style, 'new_lbl_text', order=1)
        from gvsigol_symbology import label_options as lo
        _label(rt, options=lo.dumps(lo.normalize(options)), **label_kw)
        geom = LabelSldCharacterizationTest.GEOMS.get(geom_name, geom_name)
        with mock.patch.object(utils, 'get_geometry_field', return_value=geom):
            return sld_builder.build_sld(_layer(), style)

    def test_cases(self):
        for name, (geom, options) in NEW_LABEL_CASES.items():
            with self.subTest(name):
                self.assertGolden('newlabel_%s.sld' % name, self.build(geom, options))

    def test_new_label_ignores_is_actived_like_legacy(self):
        # El editor no guarda is_actived (queda False en BD): si la etiqueta existe, se dibuja
        sld = self.build('point', {'v': 1}, is_actived=False)
        self.assertIn(b'TextSymbolizer', sld)

    def test_new_label_without_postgis_geometry_does_not_fail(self):
        sld = self.build('', {'v': 1})
        self.assertIn(b'TextSymbolizer', sld)
        self.assertIn(b'PointPlacement', sld)

    def test_escaping_produces_valid_xml(self):
        from lxml import etree
        sld = self.build('point', NEW_LABEL_CASES['escaping'][1])
        root = etree.fromstring(sld)
        self.assertEqual(len(root.findall('.//{*}evil')), 0)


class LabelEditorRoundTripTest(GoldenMixin, TestCase):
    """
    Lo que envía el editor (TextSymbolizer.toJSON con opciones avanzadas, capturado de
    LabelOptionsEditor.js en un navegador simulado) se guarda tal cual tras normalizar y
    genera el SLD esperado. Si el editor y label_options.py se desalinean, falla aquí.
    """
    GEOMS = {'point': 'point', 'line': 'line', 'polygon': 'polygon'}

    def test_editor_output(self):
        from gvsigol_symbology import symbolizer_factory, label_options as lo
        path = os.path.join(os.path.dirname(__file__), 'test_golden', 'label_editor_output.json')
        with open(path, encoding='utf-8') as f:
            payloads = json.load(f)
        self.assertEqual(sorted(payloads), sorted(self.GEOMS))
        for kind, payload in sorted(payloads.items()):
            with self.subTest(kind):
                style = _style('editor_%s' % kind, 'US')
                _poly(_rule(style, 'editor_%s_r0' % kind))
                rt = _rule(style, 'editor_%s_text' % kind, order=1)
                saved = symbolizer_factory.create_symbolizer_from_json(
                    rt, {'type': 'TextSymbolizer', 'order': 0, 'json': json.dumps(payload)})
                stored = json.loads(saved.options)
                # el editor ya produce opciones completas y válidas: normalizar no cambia nada
                self.assertEqual(stored, payload['options'])
                self.assertEqual(stored, lo.normalize(stored))
                geom = LabelSldCharacterizationTest.GEOMS[self.GEOMS[kind]]
                with mock.patch.object(utils, 'get_geometry_field', return_value=geom):
                    sld = sld_builder.build_sld(_layer(), style)
                self.assertGolden('label_editor_%s.sld' % kind, sld)


class LabelSldImportTest(TestCase):
    """
    Fase 5: al importar un SLD, una etiqueta nueva exportada desde gvSIG Online conserva
    sus opciones; cualquier otro TextSymbolizer se importa exactamente como antes.
    """
    G = os.path.join(os.path.dirname(__file__), 'test_golden')
    GEOMS = LabelSldCharacterizationTest.GEOMS

    def _text_rules(self, filename):
        from lxml import etree
        root = etree.parse(os.path.join(self.G, filename)).getroot()
        rules = root.xpath('//sld:Rule[sld:TextSymbolizer]', namespaces={'sld': 'http://www.opengis.net/sld'})
        self.assertEqual(len(rules), 1, filename)
        return rules[0]

    def _import(self, filename, geom_field):
        from gvsigol_symbology import services
        style = _style('imp_' + filename[:30], 'EX')
        rule = _rule(style, 'imp_text')
        services._sld_import_symbolizers(self._text_rules(filename), rule, geom_field=geom_field)
        return TextSymbolizer.objects.get(rule=rule)

    def _rebuild(self, ts, geom, tag):
        style = _style('reimp_' + tag, 'UV')
        _poly(_rule(style, 'new_lbl_r0'))
        rt = _rule(style, 'new_lbl_text', order=1)
        ts.pk = None
        ts.id = None
        ts.symbolizer_ptr_id = None
        ts.rule = rt
        ts.order = 1
        ts.save()
        with mock.patch.object(utils, 'get_geometry_field', return_value=geom):
            return sld_builder.build_sld(_layer(), style).decode('utf-8').replace('reimp_' + tag, 'new_lbl')

    def test_new_labels_keep_their_options(self):
        # exportar -> importar -> volver a generar: el SLD es exactamente el mismo
        for name, (geom_name, options) in NEW_LABEL_CASES.items():
            geom = self.GEOMS.get(geom_name, geom_name)
            with self.subTest(name):
                ts = self._import('newlabel_%s.sld' % name, geom)
                self.assertIsNotNone(ts.options)
                self.assertTrue(ts.label)
                with open(os.path.join(self.G, 'newlabel_%s.sld' % name), encoding='utf-8') as f:
                    self.assertEqual(self._rebuild(ts, geom, name), f.read())

    def test_editor_labels_keep_their_options(self):
        from gvsigol_symbology import label_options as lo
        with open(os.path.join(self.G, 'label_editor_output.json'), encoding='utf-8') as f:
            payloads = json.load(f)
        for kind in ('point', 'line', 'polygon'):
            with self.subTest(kind):
                ts = self._import('label_editor_%s.sld' % kind, self.GEOMS[kind])
                imported, sent = lo.of(ts), lo.normalize(payloads[kind]['options'])
                # lo que se dibuja para esta geometría es lo mismo que envió el editor
                self.assertEqual(imported['content'], sent['content'])
                self.assertEqual(imported['background'], sent['background'])
                self.assertEqual(imported['priority'], sent['priority'])
                self.assertEqual(imported['style'], sent['style'])
                key = {'point': 'point', 'line': 'line', 'polygon': 'polygon'}[kind]
                self.assertEqual(imported['placement'][key], sent['placement'][key])
                self.assertEqual(imported['placement']['wrap'], sent['placement']['wrap'])

    def test_legacy_labels_are_imported_as_before(self):
        for filename, geom in (('label_geom_point.sld', 'point'), ('label_geom_line.sld', 'line'),
                               ('label_geom_polygon.sld', 'polygon'), ('label_opts_point.sld', 'point'),
                               ('label_opts_polygon.sld', 'polygon')):
            with self.subTest(filename):
                ts = self._import(filename, self.GEOMS[geom])
                self.assertIsNone(ts.options)

    def test_other_geometry_or_unknown_geometry_imports_as_classic(self):
        # SLD de puntos en una capa de polígonos: no coincide -> etiqueta clásica
        self.assertIsNone(self._import('newlabel_point_default.sld', self.GEOMS['polygon']).options)
        # sin geometría conocida (llamadas antiguas): exactamente como antes
        self.assertIsNone(self._import('newlabel_point_default.sld', None).options)

    def test_new_label_exported_with_partials_true_is_still_recognised(self):
        # Los SLD exportados antes del cambio a partials=false siguen importándose como etiqueta nueva
        rule_node = self._text_rules('newlabel_background_box.sld')
        ns = {'sld': 'http://www.opengis.net/sld'}
        partials = rule_node.xpath('sld:TextSymbolizer/sld:VendorOption[@name="partials"]', namespaces=ns)
        self.assertEqual(len(partials), 1)
        partials[0].text = 'true'
        from gvsigol_symbology import services
        style = _style('imp_partials', 'EX')
        rule = _rule(style, 'imp_partials_text')
        services._sld_import_symbolizers(rule_node, rule, geom_field=self.GEOMS['point'])
        self.assertIsNotNone(TextSymbolizer.objects.get(rule=rule).options)

    def test_modified_new_label_imports_as_classic(self):
        from lxml import etree
        rule_node = self._text_rules('newlabel_background_box.sld')
        ts_node = rule_node.xpath('sld:TextSymbolizer', namespaces={'sld': 'http://www.opengis.net/sld'})[0]
        extra = etree.SubElement(ts_node, '{http://www.opengis.net/sld}VendorOption', name='maxDisplacement')
        extra.text = '50'
        from gvsigol_symbology import services
        style = _style('imp_mod', 'EX')
        rule = _rule(style, 'imp_mod_text')
        services._sld_import_symbolizers(rule_node, rule, geom_field=self.GEOMS['point'])
        self.assertIsNone(TextSymbolizer.objects.get(rule=rule).options)


class LabelCloneTest(TestCase):
    """Fase 5: clonar un estilo (copiar capa, etc.) conserva las opciones de las etiquetas."""

    def test_clone_keeps_options(self):
        from gvsigol_symbology import services, label_options as lo
        options = lo.dumps(lo.normalize(NEW_LABEL_CASES['background_box'][1]))
        original = _style('clone_src', 'UV')
        _poly(_rule(original, 'clone_src_r0'))
        rt = _rule(original, 'clone_src_text', order=1)
        _label(rt, options=options)
        _label(rt, order=2)  # una clásica en la misma regla
        target = _style('clone_dst', 'UV')
        services._clone_layer_style(target, Style.objects.get(id=original.id))
        cloned = TextSymbolizer.objects.filter(rule__style=target).order_by('order')
        self.assertEqual([c.options for c in cloned], [options, None])
        # el original no cambia
        self.assertEqual(TextSymbolizer.objects.filter(rule__style=original).count(), 2)


class ExternalGraphicSvgTest(TestCase):
    """Gráficos externos de biblioteca: PNG como siempre y SVG limpio (external_graphics.py)."""

    PNG = b'\x89PNG\r\n\x1a\n' + b'\x00' * 32

    def _clean(self, svg):
        from gvsigol_symbology import external_graphics as eg
        return eg.sanitize_svg(svg.encode('utf-8')).decode('utf-8')

    def test_png_and_other_files_are_saved_as_before(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from gvsigol_symbology import external_graphics as eg
        f = SimpleUploadedFile('icono.png', self.PNG, content_type='image/png')
        ext, out, fmt = eg.prepare_upload(f)
        self.assertEqual((ext, fmt), ('.png', None))
        self.assertIs(out, f)
        self.assertEqual(out.read(), self.PNG)   # contenido intacto y puntero al inicio
        jpg = SimpleUploadedFile('foto.png', b'\xff\xd8\xff\xe0' + b'\x00' * 16)
        self.assertEqual(eg.prepare_upload(jpg)[0], '.png')   # como antes: no se rechaza

    def test_valid_svg_is_kept_and_marked_as_svg(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from gvsigol_symbology import external_graphics as eg
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32">'
               '<circle cx="16" cy="16" r="14" fill="#e6194b"/></svg>')
        ext, out, fmt = eg.prepare_upload(SimpleUploadedFile('punto.svg', svg.encode()))
        self.assertEqual((ext, fmt), ('.svg', 'image/svg+xml'))
        clean = out.read().decode()
        self.assertIn('<circle', clean)
        self.assertIn('fill="#e6194b"', clean)
        self.assertIn('width="32"', clean)

    def test_dangerous_content_is_removed(self):
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
               'xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" width="10" height="10" onload="alert(1)">'
               '<script>alert(1)</script>'
               '<foreignObject><body xmlns="http://www.w3.org/1999/xhtml"><iframe src="x"/></body></foreignObject>'
               '<a href="javascript:alert(1)"><rect width="5" height="5"/></a>'
               '<rect width="5" height="5" onclick="alert(1)" inkscape:label="capa" fill="red"/>'
               '<use xlink:href="http://evil.example/x.svg#a"/>'
               '<use href="#ok"/>'
               '<image href="http://evil.example/x.png" width="1" height="1"/>'
               '<rect style="fill:url(http://evil.example/p)" width="1" height="1"/>'
               '<rect style="fill:url(#grad)" width="1" height="1"/>'
               '<style>@import url(http://evil.example/a.css);</style>'
               '<set attributeName="href" to="javascript:alert(1)"/>'
               '<animate attributeName="x" values="0;1"/>'
               '</svg>')
        clean = self._clean(svg)
        for bad in ('script', 'alert', 'foreignObject', 'iframe', 'onload', 'onclick', 'javascript:',
                    'evil.example', 'inkscape', '@import', '<set', '<animate', '<a '):
            self.assertNotIn(bad, clean, bad)
        self.assertIn('href="#ok"', clean)
        self.assertIn('url(#grad)', clean)
        self.assertIn('fill="red"', clean)

    def test_entities_and_doctype_are_not_expanded(self):
        svg = ('<?xml version="1.0"?><!DOCTYPE svg [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
               '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><text>&xxe;</text></svg>')
        try:
            clean = self._clean(svg)
        except ValueError:
            return   # rechazarlo también es correcto
        self.assertNotIn('root:', clean)
        self.assertNotIn('DOCTYPE', clean)

    def test_size_is_taken_from_viewbox(self):
        clean = self._clean('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 24"><rect width="48" height="24"/></svg>')
        self.assertIn('width="48"', clean)
        self.assertIn('height="24"', clean)
        clean = self._clean('<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%" viewBox="0,0,20,10"><rect width="1" height="1"/></svg>')
        self.assertIn('width="20"', clean)

    def test_invalid_files_are_rejected_with_a_message(self):
        from gvsigol_symbology import external_graphics as eg
        for bad in ('<svg xmlns="http://www.w3.org/2000/svg"><rect width="1" height="1"/></svg>',   # sin tamaño
                    '<html><body>hola</body></html>',                                                 # no es SVG
                    '<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"><rect></svg>',      # XML roto
                    '<svg width="1" height="1"><rect/></svg>'):                                       # sin espacio SVG
            with self.subTest(bad[:40]):
                with self.assertRaises(eg.ExternalGraphicError):
                    eg.sanitize_svg(bad.encode())
        with self.assertRaises(eg.ExternalGraphicError):
            eg.sanitize_svg(b'<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1">' + b' ' * (eg.MAX_SVG_BYTES + 1) + b'</svg>')

    def test_imported_svg_files_are_cleaned_or_discarded(self):
        import tempfile
        from gvsigol_symbology import external_graphics as eg
        with tempfile.TemporaryDirectory() as d:
            good = os.path.join(d, 'a.svg'); bad = os.path.join(d, 'b.svg')
            open(good, 'w').write('<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"><script>x()</script><rect width="1" height="1"/></svg>')
            open(bad, 'w').write('esto no es un svg')
            self.assertTrue(eg.sanitize_svg_file(good))
            self.assertNotIn('script', open(good).read())
            self.assertFalse(eg.sanitize_svg_file(bad))


class DefaultStylePaletteTest(TestCase):
    """Elección del color del estilo por defecto."""

    def test_palette_has_valid_distinct_colors(self):
        from gvsigol_symbology import default_style_palette as dsp
        self.assertEqual(len(set(dsp.PALETTE)), len(dsp.PALETTE))
        for color in dsp.PALETTE:
            self.assertRegex(color, r'^#[0-9A-Fa-f]{6}$')

    def test_layers_of_a_group_get_different_colors(self):
        from gvsigol_symbology import default_style_palette as dsp
        colors = [dsp.pick_color('grupo', n) for n in range(len(dsp.PALETTE))]
        self.assertEqual(len(set(colors)), len(dsp.PALETTE))

    def test_color_is_reproducible(self):
        from gvsigol_symbology import default_style_palette as dsp
        self.assertEqual(dsp.pick_color('grupo', 3), dsp.pick_color('grupo', 3))

    def test_missing_group_data_still_returns_a_color(self):
        from gvsigol_symbology import default_style_palette as dsp
        self.assertIn(dsp.pick_color(None, None), dsp.PALETTE)

    def test_darken(self):
        from gvsigol_symbology import default_style_palette as dsp
        self.assertEqual(dsp.darken('#64C8FF', 0.5), '#32647F')
        self.assertEqual(dsp.darken('#000000'), '#000000')


class CreateDefaultStyleTest(TestCase):
    """Lo que create_default_style guarda en BD y el SLD que genera, por geometría."""

    def _create(self, geom_type, geom_field, count=None, filter_side_effect=None):
        from gvsigol_services.models import LayerGroup
        from gvsigol_symbology import services
        layer = Layer(name='capa', title='Capa', type='v_PostGIS', layer_group=LayerGroup(name='grupo'))
        with mock.patch.object(services, 'Layer') as layer_model, \
                mock.patch.object(services, 'StyleLayer'), \
                mock.patch.object(utils, 'get_geometry_field', return_value=geom_field):
            layer_model.objects.get.return_value = layer
            layer_model.objects.filter.return_value.count.return_value = 2
            if filter_side_effect:
                layer_model.objects.filter.side_effect = filter_side_effect
            sld = services.create_default_style(1, 'estilo', 'US', geom_type, count)
        return Style.objects.get(name='estilo'), sld.decode('utf-8')

    def _symbolizer(self, style, model):
        return model.objects.get(rule__style=style)

    def test_polygon(self):
        from gvsigol_core import geom
        from gvsigol_symbology import default_style_palette as dsp
        style, sld = self._create(geom.MULTIPOLYGON, POLYGON_GEOM)
        sym = self._symbolizer(style, PolygonSymbolizer)
        self.assertIn(sym.fill, dsp.PALETTE)
        self.assertEqual(sym.fill_opacity, 0.45)
        self.assertEqual(sym.stroke, dsp.darken(sym.fill))
        self.assertEqual(sym.stroke_width, 1)
        self.assertIn(sym.fill, sld)

    def test_line(self):
        from gvsigol_core import geom
        from gvsigol_symbology import default_style_palette as dsp
        style, sld = self._create(geom.MULTILINESTRING, LINE_GEOM)
        sym = self._symbolizer(style, LineSymbolizer)
        self.assertIn(sym.stroke, dsp.PALETTE)
        self.assertEqual(sym.stroke_width, 2)
        self.assertEqual(sym.stroke_opacity, 1.0)
        self.assertIn(sym.stroke, sld)

    def test_point(self):
        from gvsigol_core import geom
        from gvsigol_symbology import default_style_palette as dsp
        style, sld = self._create(geom.POINT, POINT_GEOM)
        sym = self._symbolizer(style, MarkSymbolizer)
        self.assertIn(sym.fill, dsp.PALETTE)
        self.assertEqual((sym.size, sym.fill_opacity, sym.stroke), (10, 0.9, '#ffffff'))
        self.assertEqual(sym.well_known_name, 'circle')
        self.assertIn(sym.fill, sld)

    def test_large_layer_keeps_scale_limits(self):
        from gvsigol_core import geom
        style, _sld = self._create(geom.POINT, POINT_GEOM, count=200001)
        self.assertEqual((style.minscale, style.maxscale), (0, 50000))

    def test_failure_choosing_color_does_not_block_publication(self):
        from gvsigol_core import geom
        from gvsigol_symbology import default_style_palette as dsp
        style, _sld = self._create(geom.MULTIPOLYGON, POLYGON_GEOM, filter_side_effect=RuntimeError('fallo'))
        self.assertEqual(self._symbolizer(style, PolygonSymbolizer).fill, dsp.PALETTE[0])


# ---------------------------------------------------------------------------
# Simbolizadores avanzados, fase 0: red de seguridad de los simbolizadores de
# punto, línea y polígono ACTUALES. Lo que hoy se genera para ellos no puede
# cambiar (SLD, biblioteca, importación de SLD y de bibliotecas).
# ---------------------------------------------------------------------------

# Patrones del editor (SymbologyUtils.linePatterns)
EDITOR_DASH_PATTERNS = ('none', '5 10', '10 5', '5 1', '1 5', '15 10 5 10', '5 5 1 5')
WELL_KNOWN_NAMES = ('circle', 'square', 'triangle', 'star', 'cross')
_ROW_SKIP = ('id', 'symbolizer_ptr', 'rule')


def _symbolizer_rows(rule):
    '''Simbolizadores de la regla tal como quedan en la BD (se releen para tener los tipos reales).'''
    rows = []
    for s in Symbolizer.objects.filter(rule=rule).order_by('id'):
        for attr, model in (('marksymbolizer', MarkSymbolizer), ('linesymbolizer', LineSymbolizer),
                            ('polygonsymbolizer', PolygonSymbolizer),
                            ('externalgraphicsymbolizer', ExternalGraphicSymbolizer)):
            if hasattr(s, attr):
                child = model.objects.get(pk=s.pk)
                row = {'type': model.__name__}
                for f in model._meta.concrete_fields:
                    if f.name not in _ROW_SKIP:
                        row[f.name] = getattr(child, f.attname)
                rows.append(row)
    return rows


def _rows_json(data):
    return json.dumps(data, indent=1, sort_keys=True, ensure_ascii=False, default=repr) + '\n'


class LegacyGeometrySymbolizersSldTest(GoldenMixin, TestCase):
    '''SLD de marcas, líneas y polígonos tal como se generan hoy (estilos y biblioteca).'''

    def build(self, style, geom):
        with mock.patch.object(utils, 'get_geometry_field', return_value=geom):
            return sld_builder.build_sld(_layer(), style)

    def test_marks(self):
        style = _style('legacy_marks', 'UV')
        for i, wkn in enumerate(WELL_KNOWN_NAMES):
            r = _rule(style, 'mark_%s' % wkn, order=i)
            MarkSymbolizer.objects.create(
                rule=r, order=0, opacity=1, size=6 + 2 * i, rotation=15 * i, well_known_name=wkn,
                fill='#%02x8040' % (40 * i), fill_opacity=(0.4, 1.0, 0.0, 0.7, 0.5)[i], stroke='#101010',
                stroke_width=i, stroke_opacity=(1.0, 0.7, 0.0, 1.0, 0.3)[i],
                stroke_dash_array=EDITOR_DASH_PATTERNS[i])
        # dos marcas apiladas en la misma regla (p. ej. círculo con punto central)
        r = _rule(style, 'mark_stack', order=9)
        _mark(r, order=0, wkn='circle')
        MarkSymbolizer.objects.create(
            rule=r, order=1, opacity=1, size=3, rotation=0, well_known_name='circle', fill='#ffffff',
            fill_opacity=1.0, stroke='#000000', stroke_width=0, stroke_opacity=1.0, stroke_dash_array='none')
        self.assertGolden('legacy_marks.sld', self.build(style, POINT_GEOM))

    def test_lines(self):
        style = _style('legacy_lines', 'UV')
        for i, dash in enumerate(EDITOR_DASH_PATTERNS):
            r = _rule(style, 'line_%d' % i, order=i)
            LineSymbolizer.objects.create(rule=r, order=0, stroke='#3366cc', stroke_width=1 + i,
                                          stroke_opacity=(1.0, 0.5, 0.0)[i % 3], stroke_dash_array=dash)
        # carretera: casing ancho + línea estrecha en la misma regla
        r = _rule(style, 'line_casing', order=20)
        LineSymbolizer.objects.create(rule=r, order=0, stroke='#000000', stroke_width=6, stroke_opacity=1.0,
                                      stroke_dash_array='none')
        LineSymbolizer.objects.create(rule=r, order=1, stroke='#ffcc00', stroke_width=4, stroke_opacity=1.0,
                                      stroke_dash_array='none')
        # grosor 0 y valor de guiones que no es de la lista del editor (importado de un SLD)
        r = _rule(style, 'line_odd', order=21)
        LineSymbolizer.objects.create(rule=r, order=0, stroke='#ff0000', stroke_width=0, stroke_opacity=1.0,
                                      stroke_dash_array='4,2')
        self.assertGolden('legacy_lines.sld', self.build(style, LINE_GEOM))

    def test_polygons(self):
        style = _style('legacy_polygons', 'UV')
        for i, dash in enumerate(EDITOR_DASH_PATTERNS):
            r = _rule(style, 'poly_%d' % i, order=i)
            PolygonSymbolizer.objects.create(rule=r, order=0, fill='#88aa%02x' % (30 * i),
                                             fill_opacity=(0.5, 0.0, 1.0)[i % 3], stroke='#222222',
                                             stroke_width=i, stroke_opacity=(1.0, 0.4)[i % 2],
                                             stroke_dash_array=dash)
        # polígono + línea interior en la misma regla
        r = _rule(style, 'poly_stack', order=20)
        _poly(r, order=0)
        LineSymbolizer.objects.create(rule=r, order=1, stroke='#ffffff', stroke_width=1, stroke_opacity=1.0,
                                      stroke_dash_array='5 5 1 5')
        self.assertGolden('legacy_polygons.sld', self.build(style, POLYGON_GEOM))

    def test_library_symbols(self):
        style = _style('lib_lib_simbolos', 'US')
        cases = {
            'mark': lambda r: _mark(r, wkn='triangle'),
            'line': lambda r: _line(r, dash='15 10 5 10'),
            'polygon': lambda r: _poly(r, dash='5 1'),
            'external_graphic': lambda r: ExternalGraphicSymbolizer.objects.create(
                rule=r, order=0, opacity=1, size=24, rotation=0,
                online_resource='/media/symbol_libraries/lib/icono.png', format='image/png'),
        }
        for kind, make in cases.items():
            with self.subTest(kind):
                r = _rule(style, 'lib_lib_%s' % kind, title='Símbolo %s' % kind)
                make(r)
                self.assertGolden('legacy_library_%s.sld' % kind, sld_builder.build_library_symbol(r))


def _library_payload(sym_type, **values):
    '''Lo que envía LibrarySymbol.js: valores del formulario (muchos como texto) en symbolizers[].json.'''
    values = dict(values, type=sym_type, id='%s-uuid' % sym_type.lower(), order=0)
    return {'name': 'simbolo', 'title': 'Símbolo de prueba', 'minscale': -1, 'maxscale': -1, 'order': 0,
            'symbolizers': [{'type': sym_type, 'order': 0, 'json': json.dumps(values)}]}


LIBRARY_PAYLOADS = {
    'MarkSymbolizer': dict(opacity=1, size='12', rotation='30', well_known_name='star', fill='#ff8800',
                           fill_opacity='0.5', stroke='#000000', stroke_width='2', stroke_opacity='0.8',
                           stroke_dash_array='5 10'),
    'LineSymbolizer': dict(stroke='#3366cc', stroke_width='3', stroke_opacity='0.6', stroke_dash_array='15 10 5 10'),
    'PolygonSymbolizer': dict(fill='#88aa00', fill_opacity='0.4', stroke='#222222', stroke_width='1',
                              stroke_opacity=1, stroke_dash_array='none'),
}


class LibrarySymbolServicesCharacterizationTest(GoldenMixin, TestCase):
    '''services_library.add_symbol / update_symbol: filas que se guardan y SLD que se publica.'''

    def _gs(self):
        gs = mock.Mock()
        gs.getStyle.return_value = None
        gs.createStyle.return_value = True
        gs.deleteStyle.return_value = True
        return gs

    def test_add_and_update(self):
        from gvsigol_symbology import services_library
        from gvsigol_symbology.models import Library, LibraryRule
        out = {}
        for sym_type, values in LIBRARY_PAYLOADS.items():
            library = Library.objects.create(name='lib_%s' % sym_type.lower(), description='')
            request = mock.Mock(FILES={})
            gs = self._gs()
            self.assertTrue(services_library.add_symbol(request, _library_payload(sym_type, **values),
                                                        library.id, sym_type, gs))
            lr = LibraryRule.objects.get(library=library)
            added = {'rows': _symbolizer_rows(lr.rule), 'sld': gs.createStyle.call_args[0][1].decode('utf-8')}

            changed = dict(values, stroke='#123456')
            changed['stroke_width'] = '4'
            gs2 = self._gs()
            self.assertTrue(services_library.update_symbol(request, _library_payload(sym_type, **changed),
                                                           lr.rule, lr, gs2))
            updated = {'rows': _symbolizer_rows(lr.rule), 'sld': gs2.createStyle.call_args[0][1].decode('utf-8')}
            out[sym_type] = {'add': added, 'update': updated}
        self.assertGolden('legacy_library_services.json', _rows_json(out))


ADVANCED_SLD_RULES = '''<?xml version="1.0" encoding="UTF-8"?>
<sld:StyledLayerDescriptor xmlns:sld="http://www.opengis.net/sld" xmlns:ogc="http://www.opengis.net/ogc"
  xmlns:xlink="http://www.w3.org/1999/xlink" version="1.0.0">
 <sld:NamedLayer><sld:Name>avanzado</sld:Name><sld:UserStyle><sld:Name>avanzado</sld:Name><sld:FeatureTypeStyle>
  <sld:Rule><sld:Name>trama</sld:Name><sld:Title>trama</sld:Title>
   <sld:PolygonSymbolizer><sld:Fill><sld:GraphicFill><sld:Graphic><sld:Mark>
     <sld:WellKnownName>shape://slash</sld:WellKnownName>
     <sld:Stroke><sld:CssParameter name="stroke">#0000ff</sld:CssParameter>
     <sld:CssParameter name="stroke-width">1</sld:CssParameter></sld:Stroke></sld:Mark>
     <sld:Size>8</sld:Size></sld:Graphic></sld:GraphicFill></sld:Fill>
    <sld:Stroke><sld:CssParameter name="stroke">#000000</sld:CssParameter>
    <sld:CssParameter name="stroke-linejoin">round</sld:CssParameter></sld:Stroke>
   </sld:PolygonSymbolizer>
  </sld:Rule>
  <sld:Rule><sld:Name>via</sld:Name><sld:Title>via</sld:Title>
   <sld:LineSymbolizer><sld:Stroke><sld:CssParameter name="stroke">#333333</sld:CssParameter>
    <sld:CssParameter name="stroke-width">3</sld:CssParameter>
    <sld:CssParameter name="stroke-linecap">butt</sld:CssParameter></sld:Stroke>
    <sld:PerpendicularOffset>4</sld:PerpendicularOffset></sld:LineSymbolizer>
   <sld:LineSymbolizer><sld:Stroke><sld:GraphicStroke><sld:Graphic><sld:Mark>
     <sld:WellKnownName>shape://vertline</sld:WellKnownName>
     <sld:Stroke><sld:CssParameter name="stroke">#333333</sld:CssParameter></sld:Stroke></sld:Mark>
     <sld:Size>10</sld:Size></sld:Graphic></sld:GraphicStroke>
     <sld:CssParameter name="stroke-dasharray">10 20</sld:CssParameter></sld:Stroke></sld:LineSymbolizer>
  </sld:Rule>
  <sld:Rule><sld:Name>punto</sld:Name><sld:Title>punto</sld:Title>
   <sld:PointSymbolizer><sld:Graphic><sld:Mark><sld:WellKnownName>shape://times</sld:WellKnownName>
     <sld:Stroke><sld:CssParameter name="stroke">#ff0000</sld:CssParameter>
     <sld:CssParameter name="stroke-width">2</sld:CssParameter></sld:Stroke></sld:Mark>
     <sld:Size>9.5</sld:Size><sld:Rotation><ogc:PropertyName>angulo</ogc:PropertyName></sld:Rotation>
     <sld:Displacement><sld:DisplacementX>3</sld:DisplacementX><sld:DisplacementY>-2</sld:DisplacementY></sld:Displacement>
   </sld:Graphic></sld:PointSymbolizer>
  </sld:Rule>
 </sld:FeatureTypeStyle></sld:UserStyle></sld:NamedLayer>
</sld:StyledLayerDescriptor>
'''


def _sld_rule_nodes(sld_text):
    from lxml import etree
    if isinstance(sld_text, str):
        sld_text = sld_text.encode('utf-8')
    root = etree.fromstring(sld_text)
    return root.xpath('//sld:Rule', namespaces={'sld': 'http://www.opengis.net/sld'})


class GeometrySldImportCharacterizationTest(GoldenMixin, TestCase):
    '''services._sld_import_symbolizers con marcas, líneas y polígonos (importar SLD de estilo).'''

    def _import_all(self, sld_text, tag):
        from gvsigol_symbology import services
        style = _style('imp_geom_' + tag, 'EX')
        out = []
        for i, node in enumerate(_sld_rule_nodes(sld_text)):
            rule = _rule(style, 'imp_%s_%d' % (tag, i), order=i)
            try:
                services._sld_import_symbolizers(node, rule)
                out.append(_symbolizer_rows(rule))
            except Exception as e:  # se documenta el fallo tal como es hoy
                out.append({'error': type(e).__name__})
        return out

    def test_legacy_roundtrip(self):
        # SLD generado hoy por gvSIG -> importar -> filas: las mismas que lo generaron
        out = {}
        for kind, geom in (('marks', POINT_GEOM), ('lines', LINE_GEOM), ('polygons', POLYGON_GEOM)):
            path = os.path.join(GOLDEN_DIR, 'legacy_%s.sld' % kind)
            with open(path, encoding='utf-8') as f:
                out[kind] = self._import_all(f.read(), kind)
        self.assertGolden('legacy_sld_import.json', _rows_json(out))

    def test_advanced_constructs_today(self):
        # Tramas, marcas en línea, desplazamientos...: hoy se pierden o se degradan al importar
        self.assertGolden('advanced_sld_import_today.json', _rows_json(self._import_all(ADVANCED_SLD_RULES, 'adv')))


class LibraryUploadCharacterizationTest(GoldenMixin, TestCase):
    '''services_library.upload_library: el lector POSICIONAL de CssParameter (índice 0..3) de los .zip.'''

    def _upload(self, name, slds):
        import shutil
        import tempfile
        from gvsigol_symbology import services_library
        from gvsigol_symbology.models import Library, LibraryRule
        tmp = tempfile.mkdtemp(prefix='symlibtest-')
        self.addCleanup(shutil.rmtree, tmp, True)
        os.makedirs(os.path.join(tmp, 'resources'))
        for fname, body in slds.items():
            with open(os.path.join(tmp, fname), 'wb') as f:
                f.write(body if isinstance(body, bytes) else body.encode('utf-8'))
        gs = mock.Mock()
        gs.createStyle.return_value = True
        servers = mock.Mock()
        servers.get_instance.return_value.get_default_server.return_value = gs
        libdir = os.path.join(tmp, 'libdir')
        os.makedirs(libdir)
        with mock.patch.object(services_library, 'geographic_servers', servers), \
                mock.patch.object(utils, 'check_library_path', return_value=libdir), \
                mock.patch.object(utils, '__get_uncompressed_file_upload_path', return_value=tmp), \
                mock.patch.object(utils, 'copyrecursively'), \
                mock.patch.object(utils, '__delete_temporaries'):
            error = None
            try:
                services_library.upload_library(name, '', mock.Mock())
            except Exception as e:  # se documenta el fallo tal como es hoy
                error = type(e).__name__
        library = Library.objects.get(name=name)
        rules = {lr.rule.name: _symbolizer_rows(lr.rule)
                 for lr in LibraryRule.objects.filter(library=library).order_by('rule__name')}
        return {'error': error, 'rules': rules}

    def test_exported_legacy_symbols(self):
        # .zip exportado hoy (build_library_symbol) -> importar: filas resultantes
        style = _style('exp_lib_simbolos', 'US')
        slds = {}
        makers = {
            'mark': lambda r: MarkSymbolizer.objects.create(
                rule=r, order=0, opacity=1, size=12, rotation=30, well_known_name='star', fill='#ff8800',
                fill_opacity=0.5, stroke='#000000', stroke_width=2, stroke_opacity=0.8, stroke_dash_array='5 10'),
            'mark_nodash': lambda r: _mark(r, wkn='square'),
            'line': lambda r: _line(r, dash='15 10 5 10'),
            'line_nodash': lambda r: _line(r),
            'polygon': lambda r: _poly(r, dash='5 1'),
            'polygon_nodash': lambda r: _poly(r),
        }
        for i, (kind, make) in enumerate(makers.items()):
            r = _rule(style, kind, title='Símbolo %s' % kind)
            make(r)
            slds['symbol-%s-%d.sld' % (kind, i)] = sld_builder.build_library_symbol(r)
        self.assertGolden('legacy_library_upload.json', _rows_json(self._upload('lib_import_legacy', slds)))

    def test_param_order_matters_today(self):
        # El lector usa la POSICIÓN: un SLD con stroke-linecap y sin guiones se lee mal (fase 2)
        body = ('<?xml version="1.0" encoding="UTF-8"?><sld:StyledLayerDescriptor xmlns:sld="http://www.opengis.net/sld" '
                'xmlns:ogc="http://www.opengis.net/ogc" version="1.0.0"><sld:NamedLayer><sld:Name>linea</sld:Name>'
                '<sld:UserStyle><sld:Name>linea</sld:Name><sld:FeatureTypeStyle><sld:Rule><sld:Name>linea</sld:Name>'
                '<sld:Title>linea</sld:Title><sld:LineSymbolizer><sld:Stroke>'
                '<sld:CssParameter name="stroke">#333333</sld:CssParameter>'
                '<sld:CssParameter name="stroke-width">3</sld:CssParameter>'
                '<sld:CssParameter name="stroke-opacity">1</sld:CssParameter>'
                '<sld:CssParameter name="stroke-linecap">butt</sld:CssParameter>'
                '</sld:Stroke></sld:LineSymbolizer></sld:Rule></sld:FeatureTypeStyle></sld:UserStyle>'
                '</sld:NamedLayer></sld:StyledLayerDescriptor>')
        self.assertGolden('library_upload_param_order_today.json',
                          _rows_json(self._upload('lib_import_order', {'symbol-linea-0.sld': body})))


# ---------------------------------------------------------------------------
# Simbolizadores avanzados, fase 1: modelo (options y decimales) y esquema.
# ---------------------------------------------------------------------------

class SymbolOptionsNormalizeTest(TestCase):

    def test_empty_or_invalid_is_legacy(self):
        from gvsigol_symbology import symbol_options as so
        for kind in so.KINDS:
            for raw in (None, '', '{}', 'no es json', '[1, 2]', {}, '"texto"'):
                with self.subTest(kind=kind, raw=raw):
                    self.assertIsNone(so.normalize(kind, raw))
        with self.assertRaises(ValueError):
            so.normalize('text', '{"v": 1}')

    def test_defaults(self):
        from gvsigol_symbology import symbol_options as so
        self.assertEqual(so.normalize('mark', {'v': 1}), {
            'v': 1, 'shape': 'circle', 'fill': True, 'displacement': {'x': 0, 'y': 0}, 'rotation_field': None})
        self.assertEqual(so.normalize('line', {'v': 1}), {
            'v': 1, 'line': True, 'marks': None, 'start': None, 'end': None,
            'stroke': {'linecap': 'butt', 'linejoin': 'miter', 'dash_offset': 0, 'offset': 0}})
        self.assertEqual(so.normalize('polygon', {'v': 1}), {
            'v': 1, 'fill': {'type': 'solid'}, 'stroke': {'linecap': 'butt', 'linejoin': 'miter', 'dash_offset': 0}})

    def test_full_values_and_clamping(self):
        from gvsigol_symbology import symbol_options as so
        line = so.normalize('line', {
            'line': False, 'stroke': {'linecap': 'round', 'linejoin': 'bevel', 'dash_offset': 5, 'offset': -500},
            'marks': {'shape': 'shape://vertline', 'size': 12.5, 'spacing': 0, 'start': 4, 'fill': '#FF0000',
                      'stroke': '#333333', 'stroke_width': 2},
            'end': {'shape': 'shape://carrow', 'size': 14, 'fill': '#333333'}})
        self.assertEqual(line['stroke'], {'linecap': 'round', 'linejoin': 'bevel', 'dash_offset': 5, 'offset': -100})
        # las formas de solo trazo no llevan relleno; el espaciado mínimo es 1
        self.assertEqual(line['marks'], {'shape': 'shape://vertline', 'size': 12.5, 'spacing': 1, 'start': 4,
                                         'fill': None, 'stroke': '#333333', 'stroke_width': 2})
        self.assertEqual(line['end'], {'shape': 'shape://carrow', 'size': 14, 'fill': '#333333',
                                       'stroke': '#000000', 'stroke_width': 1})
        self.assertIsNone(line['start'])
        self.assertFalse(line['line'])
        poly = so.normalize('polygon', {'fill': {'type': 'hatch', 'hatch': {
            'pattern': 'times', 'color': '#AABBCC', 'width': 0, 'spacing': 500, 'background': False}}})
        self.assertEqual(poly['fill'], {'type': 'hatch', 'hatch': {
            'pattern': 'times', 'color': '#aabbcc', 'width': 0.25, 'spacing': 100, 'background': False}})
        # relleno con imagen: GeoServer 2.28 no lo pinta (fase 2); se guarda como sólido
        graphic = so.normalize('polygon', {'fill': {'type': 'graphic', 'graphic': {
            'online_resource': '/media/symbol_libraries/lib/arbol.svg', 'format': 'image/svg+xml', 'size': 20}}})
        self.assertEqual(graphic['fill'], {'type': 'solid'})

    def test_unsafe_values_are_dropped(self):
        from gvsigol_symbology import symbol_options as so
        mark = so.normalize('mark', {'shape': 'qgis://octagon', 'rotation_field': 'a; drop table',
                                     'displacement': {'x': 'NaN', 'y': float('inf')}, 'fill': 'si'})
        # qgis://octagon hace fallar la capa entera en GeoServer: no está en la lista
        self.assertEqual(mark, {'v': 1, 'shape': 'circle', 'fill': True, 'displacement': {'x': 0, 'y': 0},
                                'rotation_field': None})
        self.assertIsNone(so.normalize('mark', {'rotation_field': 'angulo'}, allowed_fields=['otro'])['rotation_field'])
        self.assertEqual(so.normalize('mark', {'rotation_field': 'angulo'}, allowed_fields=['angulo'])['rotation_field'],
                         'angulo')
        line = so.normalize('line', {'marks': {'shape': 'ttf://Wingdings#0x41', 'stroke': 'red"/><x'},
                                     'stroke': {'linecap': 'evil'}})
        self.assertEqual(line['marks']['shape'], 'shape://vertline')
        self.assertEqual(line['marks']['stroke'], '#000000')
        self.assertEqual(line['stroke']['linecap'], 'butt')
        for bad in ('http://evil.org/x.png', '/media/../etc/passwd', 'media/x.png', '//host/x.png',
                    '/media/x.png"><script>'):
            with self.subTest(bad):
                poly = so.normalize('polygon', {'fill': {'type': 'graphic', 'graphic': {'online_resource': bad}}})
                self.assertEqual(poly['fill'], {'type': 'solid'})
        # sin trazo ni decoraciones no se vería nada: se mantiene el trazo
        self.assertTrue(so.normalize('line', {'line': False})['line'])

    def test_roundtrip_is_stable(self):
        from gvsigol_symbology import symbol_options as so
        for kind, raw in (('mark', {'shape': 'x', 'displacement': {'x': 3, 'y': -2.5}}),
                          ('line', {'marks': {'spacing': 30}, 'end': {}}),
                          ('polygon', {'fill': {'type': 'hatch', 'hatch': {'pattern': 'dots'}}})):
            with self.subTest(kind):
                once = so.normalize(kind, raw)
                self.assertEqual(so.normalize(kind, so.dumps(once)), once)

    def test_shapes_and_legacy_equivalents(self):
        from gvsigol_symbology import symbol_options as so
        for shape in so.SHAPES:
            with self.subTest(shape):
                self.assertIn(so.legacy_shape(shape), so.LEGACY_SHAPES)
                self.assertLessEqual(len(shape), 27)
        self.assertEqual(so.legacy_shape('star'), 'star')
        self.assertEqual(so.legacy_shape('qgis://diamond'), 'square')
        self.assertNotIn('shape://dot', so.SHAPES)       # no pinta nada como trama (fase 0)
        self.assertNotIn('shape://horline', so.SHAPES)   # no se ve como marca suelta (fase 0)


class IntegralFloatFieldTest(TestCase):
    '''Los grosores y tamaños admiten decimales; los enteros se siguen leyendo y escribiendo como antes.'''

    def test_values_roundtrip(self):
        style = _style('decimales', 'US')
        r = _rule(style, 'decimales_r')
        line = LineSymbolizer.objects.create(rule=r, order=0, stroke='#000000', stroke_width='3',
                                             stroke_opacity=1.0, stroke_dash_array='none')
        thin = LineSymbolizer.objects.create(rule=r, order=1, stroke='#000000', stroke_width=0.5,
                                             stroke_opacity=1.0, stroke_dash_array='none')
        mark = MarkSymbolizer.objects.create(
            rule=r, order=2, opacity=0.5, size=9.5, rotation=0, well_known_name='circle', fill='#ffffff',
            fill_opacity=1.0, stroke='#000000', stroke_width=1.5, stroke_opacity=1.0, stroke_dash_array='none')
        line, thin, mark = (LineSymbolizer.objects.get(pk=line.pk), LineSymbolizer.objects.get(pk=thin.pk),
                            MarkSymbolizer.objects.get(pk=mark.pk))
        self.assertIs(type(line.stroke_width), int)
        self.assertEqual((thin.stroke_width, mark.opacity, mark.size, mark.stroke_width), (0.5, 0.5, 9.5, 1.5))
        with mock.patch.object(utils, 'get_geometry_field', return_value=LINE_GEOM):
            sld = sld_builder.build_sld(_layer(), style).decode('utf-8')
        self.assertIn('<sld:CssParameter name="stroke-width">3</sld:CssParameter>', sld)
        self.assertIn('<sld:CssParameter name="stroke-width">0.5</sld:CssParameter>', sld)
        self.assertIn('<sld:Size>9.5</sld:Size>', sld)
        self.assertIn('<sld:Opacity>0.5</sld:Opacity>', sld)
        self.assertNotIn('3.0<', sld)
        # el JSON que recibe el editor tampoco cambia para los enteros
        self.assertIn('"stroke_width": 3,', utils.symbolizer_to_json(Symbolizer.objects.get(pk=line.pk))['json'])


class GeometryOptionsPersistenceTest(TestCase):
    '''symbolizer_factory y la biblioteca guardan las opciones normalizadas (o NULL si no hay).'''

    def _create(self, sym_type, values):
        from gvsigol_symbology.symbolizer_factory import create_symbolizer_from_json
        style = _style('opts_' + sym_type, 'US')
        r = _rule(style, 'opts_r')
        sym = create_symbolizer_from_json(r, {'type': sym_type, 'order': '0', 'json': json.dumps(values)})
        return type(sym).objects.get(pk=sym.pk)

    def test_factory(self):
        from gvsigol_symbology import symbol_options as so
        line_values = dict(LIBRARY_PAYLOADS['LineSymbolizer'])
        self.assertIsNone(self._create('LineSymbolizer', line_values).options)
        self.assertIsNone(self._create('LineSymbolizer', dict(line_values, options='no json')).options)
        line = self._create('LineSymbolizer', dict(line_values, options={'stroke': {'linecap': 'round', 'x': 1}}))
        self.assertEqual(so.of(line), so.normalize('line', {'stroke': {'linecap': 'round'}}))
        self.assertNotIn('"x"', line.options)

        poly = self._create('PolygonSymbolizer', dict(LIBRARY_PAYLOADS['PolygonSymbolizer'],
                                                      options=json.dumps({'fill': {'type': 'none'}})))
        self.assertEqual(so.of(poly)['fill'], {'type': 'none'})

        # forma nueva: well_known_name guarda la clásica equivalente
        mark = self._create('MarkSymbolizer', dict(LIBRARY_PAYLOADS['MarkSymbolizer'],
                                                   options={'shape': 'qgis://hexagon'}))
        self.assertEqual((so.of(mark)['shape'], mark.well_known_name), ('qgis://hexagon', 'circle'))
        # opciones sin forma: se conserva la de la columna
        mark = self._create('MarkSymbolizer', dict(LIBRARY_PAYLOADS['MarkSymbolizer'], options={'fill': False}))
        self.assertEqual((so.of(mark)['shape'], mark.well_known_name, so.of(mark)['fill']), ('star', 'star', False))
        self.assertEqual(mark.size, 12)

    def test_library_add_and_update_keep_options(self):
        from gvsigol_symbology import services_library, symbol_options as so
        from gvsigol_symbology.models import Library, LibraryRule
        library = Library.objects.create(name='lib_opciones', description='')
        gs = mock.Mock()
        gs.getStyle.return_value = None
        gs.createStyle.return_value = True
        gs.deleteStyle.return_value = True
        values = dict(LIBRARY_PAYLOADS['PolygonSymbolizer'],
                      options={'fill': {'type': 'hatch', 'hatch': {'pattern': 'slash'}}})
        services_library.add_symbol(mock.Mock(FILES={}), _library_payload('PolygonSymbolizer', **values),
                                    library.id, 'PolygonSymbolizer', gs)
        lr = LibraryRule.objects.get(library=library)
        poly = PolygonSymbolizer.objects.get(rule=lr.rule)
        self.assertEqual(so.of(poly)['fill']['hatch']['pattern'], 'slash')
        values['options'] = {'fill': {'type': 'hatch', 'hatch': {'pattern': 'plus'}}}
        services_library.update_symbol(mock.Mock(FILES={}), _library_payload('PolygonSymbolizer', **values),
                                       lr.rule, lr, gs)
        poly = PolygonSymbolizer.objects.get(rule=lr.rule)
        self.assertEqual(so.of(poly)['fill']['hatch']['pattern'], 'plus')


# ---------------------------------------------------------------------------
# Simbolizadores avanzados, fase 2: SLD de los simbolizadores nuevos e importación.
# ---------------------------------------------------------------------------

def _new_mark(rule, options, order=0, **kw):
    values = dict(opacity=1, size=12, rotation=0, well_known_name='circle', fill='#3366cc', fill_opacity=0.8,
                  stroke='#000000', stroke_width=1, stroke_opacity=1.0, stroke_dash_array='none')
    values.update(kw)
    from gvsigol_symbology import symbol_options as so
    return MarkSymbolizer.objects.create(rule=rule, order=order, options=so.dumps(so.normalize('mark', options)),
                                         **values)


def _new_line(rule, options, order=0, **kw):
    values = dict(stroke='#333333', stroke_width=2, stroke_opacity=1.0, stroke_dash_array='none')
    values.update(kw)
    from gvsigol_symbology import symbol_options as so
    return LineSymbolizer.objects.create(rule=rule, order=order, options=so.dumps(so.normalize('line', options)),
                                         **values)


def _new_poly(rule, options, order=0, **kw):
    values = dict(fill='#ffffcc', fill_opacity=1.0, stroke='#222222', stroke_width=1, stroke_opacity=1.0,
                  stroke_dash_array='none')
    values.update(kw)
    from gvsigol_symbology import symbol_options as so
    return PolygonSymbolizer.objects.create(rule=rule, order=order,
                                            options=so.dumps(so.normalize('polygon', options)), **values)


NEW_SYMBOL_CASES = {
    # nombre: (geometría, creador, opciones, columnas)
    'mark_hexagon_displaced': ('point', _new_mark, {'shape': 'qgis://hexagon', 'displacement': {'x': 4, 'y': -3}},
                               {}),
    'mark_rotation_field': ('point', _new_mark, {'shape': 'extshape://narrow', 'rotation_field': 'angulo'},
                            {'rotation': 15, 'stroke_dash_array': '2 1'}),
    'mark_line_shape_decimals': ('point', _new_mark, {'shape': 'shape://times', 'fill': False},
                                 {'size': 9.5, 'stroke_width': 1.5, 'opacity': 0.5}),
    'line_caps_offset': ('line', _new_line, {'stroke': {'linecap': 'round', 'linejoin': 'bevel', 'dash_offset': 5,
                                                         'offset': 6}}, {'stroke_dash_array': '10 5'}),
    'line_railway': ('line', _new_line, {'marks': {'shape': 'shape://vertline', 'size': 10, 'spacing': 12,
                                                    'stroke': '#333333', 'stroke_width': 2}}, {}),
    'line_arrows': ('line', _new_line, {'marks': {'shape': 'shape://oarrow', 'size': 10, 'spacing': 40, 'start': 20,
                                                   'stroke': '#333333'},
                                         'start': {'shape': 'circle', 'size': 8, 'fill': '#333333', 'stroke_width': 0},
                                         'end': {'shape': 'shape://carrow', 'size': 14, 'fill': '#333333'}},
                    {'stroke_width': 1.5}),
    'line_only_marks': ('line', _new_line, {'line': False, 'marks': {'shape': 'circle', 'size': 6, 'spacing': 10,
                                                                      'fill': '#cc3333', 'stroke_width': 0}}, {}),
    'polygon_none': ('polygon', _new_poly, {'fill': {'type': 'none'}, 'stroke': {'linejoin': 'round'}},
                     {'stroke_width': 3, 'stroke_dash_array': '10 5'}),
    'polygon_hatch_bg': ('polygon', _new_poly, {'fill': {'type': 'hatch', 'hatch': {'pattern': 'slash',
                                                                                      'color': '#3366cc'}}}, {}),
    'polygon_hatch_cross_nobg': ('polygon', _new_poly, {'fill': {'type': 'hatch', 'hatch': {
        'pattern': 'times', 'color': '#cc3333', 'width': 2, 'spacing': 14, 'background': False}}}, {}),
    'polygon_dots': ('polygon', _new_poly, {'fill': {'type': 'hatch', 'hatch': {'pattern': 'dots', 'width': 2,
                                                                                  'spacing': 12}}}, {}),
    'polygon_solid_no_stroke': ('polygon', _new_poly, {'stroke': {'linecap': 'round'}}, {'stroke_width': 0}),
}
NEW_SYMBOL_GEOMS = {'point': POINT_GEOM, 'line': LINE_GEOM, 'polygon': POLYGON_GEOM}


class NewGeometrySymbolizersSldTest(GoldenMixin, TestCase):

    def _style(self, name):
        geom, make, options, columns = NEW_SYMBOL_CASES[name]
        style = _style('newsym_' + name, 'US')
        r = _rule(style, 'newsym_r')
        make(r, options, **columns)
        return style, NEW_SYMBOL_GEOMS[geom]

    def build(self, name):
        style, geom = self._style(name)
        with mock.patch.object(utils, 'get_geometry_field', return_value=geom):
            return sld_builder.build_sld(_layer(), style)

    def test_cases(self):
        from lxml import etree
        for name in NEW_SYMBOL_CASES:
            with self.subTest(name):
                sld = self.build(name)
                etree.fromstring(sld)  # XML válido
                self.assertNotIn(b'<sld:LineSymbolizer/>', sld)
                self.assertGolden('newsym_%s.sld' % name, sld)

    def test_library_symbol_without_geometry_has_no_end_points(self):
        # Los símbolos de biblioteca no conocen la geometría: sin flechas en los extremos
        style, _geom = self._style('line_arrows')
        rule = Rule.objects.get(style=style)
        sld = sld_builder.build_library_symbol(rule)
        self.assertNotIn(b'endPoint', sld)
        self.assertGolden('newsym_library_line_arrows.sld', sld)

    def test_legacy_symbolizers_in_same_rule_unchanged(self):
        style = _style('newsym_mixed', 'US')
        r = _rule(style, 'mixed_r')
        _poly(r, order=0, dash='5 2')
        _new_poly(r, {'fill': {'type': 'hatch', 'hatch': {'pattern': 'plus'}}}, order=1)
        with mock.patch.object(utils, 'get_geometry_field', return_value=POLYGON_GEOM):
            self.assertGolden('newsym_mixed_with_legacy.sld', sld_builder.build_sld(_layer(), style))

    def test_user_values_are_escaped(self):
        from lxml import etree
        style = _style('newsym_escape', 'US')
        r = _rule(style, 'esc_r')
        _new_poly(r, {'fill': {'type': 'none'}}, stroke='#000000"/><x a="')
        with mock.patch.object(utils, 'get_geometry_field', return_value=POLYGON_GEOM):
            sld = sld_builder.build_sld(_layer(), style)
        root = etree.fromstring(sld)
        self.assertEqual(len(root.xpath('//x')), 0)


class NewGeometrySymbolizersImportTest(TestCase):
    '''Exportar -> importar SLD de estilo: los símbolos nuevos conservan sus opciones; lo demás, como antes.'''

    def _rule_node(self, sld_bytes):
        nodes = _sld_rule_nodes(sld_bytes)
        self.assertEqual(len(nodes), 1)
        return nodes[0]

    def _import(self, sld_bytes, geom, tag):
        from gvsigol_symbology import services
        style = _style('imp_new_' + tag, 'US')
        rule = _rule(style, 'newsym_r')  # mismo título que el SLD original
        services._sld_import_symbolizers(self._rule_node(sld_bytes), rule, geom_field=geom)
        return style, rule

    def _rebuild(self, style, geom):
        with mock.patch.object(utils, 'get_geometry_field', return_value=geom):
            return sld_builder.build_sld(_layer(), style)

    def test_roundtrip_all_cases(self):
        from gvsigol_symbology import symbol_options as so
        for name, (geom_name, _make, options, _cols) in NEW_SYMBOL_CASES.items():
            geom = NEW_SYMBOL_GEOMS[geom_name]
            with self.subTest(name):
                with open(os.path.join(GOLDEN_DIR, 'newsym_%s.sld' % name), 'rb') as f:
                    original = f.read()
                style, rule = self._import(original, geom, name)
                syms = list(Symbolizer.objects.filter(rule=rule))
                self.assertEqual(len(syms), 1, 'un simbolizador del modelo por símbolo')
                child = (getattr(syms[0], 'marksymbolizer', None) or getattr(syms[0], 'linesymbolizer', None)
                         or getattr(syms[0], 'polygonsymbolizer', None))
                self.assertEqual(so.of(child), so.normalize(so.kind_of(child), options))
                rebuilt = self._rebuild(style, geom).replace(b'imp_new_' + name.encode(), b'newsym_' + name.encode())
                self.assertEqual(rebuilt.decode('utf-8'), original.decode('utf-8'))

    def test_edited_sld_is_imported_as_before(self):
        # Si alguien retoca el SLD (aquí, el color de la trama), no coincide: importación clásica
        with open(os.path.join(GOLDEN_DIR, 'newsym_polygon_hatch_bg.sld'), 'rb') as f:
            edited = f.read().replace(b'#3366cc</sld:CssParameter>', b'#ff0000</sld:CssParameter>', 1)
        _style_, rule = self._import(edited, POLYGON_GEOM, 'edited')
        rows = _symbolizer_rows(rule)
        self.assertEqual(len(rows), 2)  # fondo + trama, como dos polígonos clásicos
        self.assertTrue(all(r['options'] is None for r in rows))

    def test_marker_alone_is_not_trusted(self):
        # Un marcador que no describe los nodos (p. ej. copiado a otro simbolizador) se ignora
        with open(os.path.join(GOLDEN_DIR, 'newsym_polygon_none.sld'), 'rb') as f:
            text = f.read()
        tampered = text.replace(b'<sld:CssParameter name="stroke-width">3</sld:CssParameter>',
                                b'<sld:CssParameter name="stroke-width">7</sld:CssParameter>')
        self.assertNotEqual(text, tampered)
        _style_, rule = self._import(tampered, POLYGON_GEOM, 'tampered')
        rows = _symbolizer_rows(rule)
        self.assertEqual((len(rows), rows[0]['options'], rows[0]['stroke_width']), (1, None, 7))

    def test_line_with_ends_without_geometry_falls_back(self):
        # Sin la geometría de la capa no se pueden regenerar los extremos: se importa como antes
        with open(os.path.join(GOLDEN_DIR, 'newsym_line_arrows.sld'), 'rb') as f:
            original = f.read()
        _style_, rule = self._import(original, None, 'nogeom')
        rows = _symbolizer_rows(rule)
        self.assertTrue(all(r['options'] is None for r in rows))

    def test_mixed_rule_keeps_order(self):
        with open(os.path.join(GOLDEN_DIR, 'newsym_mixed_with_legacy.sld'), 'rb') as f:
            original = f.read()
        style, rule = self._import(original, POLYGON_GEOM, 'mixed')
        rows = _symbolizer_rows(rule)
        self.assertEqual([r['options'] is not None for r in rows], [True, False])
        # el primero del SLD se pinta debajo: order más alto (como al crearlo en el editor)
        self.assertEqual([r['order'] for r in rows], [1, 0])
        rebuilt = self._rebuild(style, POLYGON_GEOM).replace(b'imp_new_mixed', b'newsym_mixed').replace(
            b'<sld:Title>newsym_r</sld:Title>', b'<sld:Title>mixed_r</sld:Title>')
        self.assertEqual(rebuilt.decode('utf-8'), original.decode('utf-8'))


class NewGeometrySymbolizersLibraryUploadTest(LibraryUploadCharacterizationTest):
    '''Exportar -> importar una biblioteca (.zip) con símbolos nuevos y antiguos.'''

    def test_exported_new_symbols(self):
        from gvsigol_symbology import symbol_options as so
        from gvsigol_symbology.models import Library, LibraryRule
        style = _style('exp_lib_nuevos', 'US')
        slds, expected = {}, {}
        for i, name in enumerate(('polygon_hatch_bg', 'line_railway', 'line_arrows', 'mark_hexagon_displaced')):
            _geom, make, options, columns = NEW_SYMBOL_CASES[name]
            r = _rule(style, name, title='Símbolo %s' % name)
            sym = make(r, options, **columns)
            expected[name] = so.of(sym)
            slds['symbol-%s-%d.sld' % (name, i)] = sld_builder.build_library_symbol(r)
        r = _rule(style, 'legacy_line', title='Línea clásica')
        _line(r, dash='5 10')
        slds['symbol-legacy_line-9.sld'] = sld_builder.build_library_symbol(r)

        result = self._upload('lib_import_nuevos', slds)
        self.assertIsNone(result['error'])
        for name, options in expected.items():
            with self.subTest(name):
                rows = result['rules'][name]
                self.assertEqual(len(rows), 1)
                self.assertEqual(so.loads(rows[0]['options']), options)
        legacy = result['rules']['legacy_line']
        self.assertEqual((len(legacy), legacy[0]['options'], legacy[0]['stroke_dash_array']), (1, None, '5 10'))
        library = Library.objects.get(name='lib_import_nuevos')
        # la biblioteca importada vuelve a exportar exactamente el mismo SLD
        for lr in LibraryRule.objects.filter(library=library):
            if lr.rule.name in expected:
                with self.subTest('reexport ' + lr.rule.name):
                    again = sld_builder.build_library_symbol(lr.rule).decode('utf-8')
                    original = [v for k, v in slds.items() if ('-%s-' % lr.rule.name) in k][0].decode('utf-8')
                    self.assertEqual(again.replace('lib_import_nuevos_lib_', ''), original)


class StackedSymbolizersImportOrderTest(TestCase):
    """
    Exportar el SLD de un estilo e importarlo conserva el orden de dibujo de los simbolizadores
    apilados (antes quedaban al revés). Los estilos ya guardados no se tocan.
    """

    def _roundtrip(self, golden, geom, tag):
        from gvsigol_symbology import services
        with open(os.path.join(GOLDEN_DIR, golden), 'rb') as f:
            original = f.read()
        style = _style(tag, 'UV')
        for i, node in enumerate(_sld_rule_nodes(original)):
            title = node.xpath('sld:Title', namespaces={'sld': 'http://www.opengis.net/sld'})[0].text
            rule = _rule(style, title, order=i)
            services._sld_import_symbolizers(node, rule, geom_field=geom)
        with mock.patch.object(utils, 'get_geometry_field', return_value=geom):
            return original, sld_builder.build_sld(_layer(), style)

    def test_legacy_styles_roundtrip_identically(self):
        for golden, geom, name in (('legacy_marks.sld', POINT_GEOM, 'legacy_marks'),
                                   ('legacy_lines.sld', LINE_GEOM, 'legacy_lines'),
                                   ('legacy_polygons.sld', POLYGON_GEOM, 'legacy_polygons')):
            with self.subTest(golden):
                original, rebuilt = self._roundtrip(golden, geom, name + '_rt')
                rebuilt = rebuilt.replace((name + '_rt').encode(), name.encode())
                self.assertEqual(rebuilt.decode('utf-8'), original.decode('utf-8'))

    def test_existing_rules_are_not_touched(self):
        from gvsigol_symbology import services
        style = _style('ya_guardado', 'US')
        r = _rule(style, 'ya_guardado_r')
        a, b = _line(r, order=0), _line(r, order=1)
        other = _rule(style, 'importada', order=1)
        with open(os.path.join(GOLDEN_DIR, 'legacy_lines.sld'), 'rb') as f:
            node = _sld_rule_nodes(f.read())[-2]  # regla con dos líneas apiladas
        services._sld_import_symbolizers(node, other, geom_field=LINE_GEOM)
        self.assertEqual([Symbolizer.objects.get(pk=x.pk).order for x in (a, b)], [0, 1])


# ---------------------------------------------------------------------------
# Simbolizadores avanzados, fase 5: vista previa con el SLD publicado y exportación compatible.
# ---------------------------------------------------------------------------

def _preview_item(name):
    _geom, make, options, columns = NEW_SYMBOL_CASES[name]
    sym_type = {_new_mark: 'MarkSymbolizer', _new_line: 'LineSymbolizer', _new_poly: 'PolygonSymbolizer'}[make]
    defaults = {'MarkSymbolizer': dict(opacity=1, size=12, rotation=0, well_known_name='circle', fill='#3366cc',
                                       fill_opacity=0.8, stroke='#000000', stroke_width=1, stroke_opacity=1.0,
                                       stroke_dash_array='none'),
                'LineSymbolizer': dict(stroke='#333333', stroke_width=2, stroke_opacity=1.0, stroke_dash_array='none'),
                'PolygonSymbolizer': dict(fill='#ffffcc', fill_opacity=1.0, stroke='#222222', stroke_width=1,
                                          stroke_opacity=1.0, stroke_dash_array='none')}[sym_type]
    data = dict(defaults, **columns)
    data['options'] = options
    return {'type': sym_type, 'json': json.dumps(data)}


class SymbolPreviewTest(TestCase):
    URL = '/geoserver/wms?REQUEST=GetLegendGraphic&VERSION=1.0.0&FORMAT=image/png&WIDTH=20&HEIGHT=20&LAYER=preview_%s'

    def test_same_symbolizer_xml_as_published(self):
        from lxml import etree
        from gvsigol_symbology import symbol_preview
        for name in ('polygon_hatch_bg', 'line_arrows', 'mark_hexagon_displaced'):
            with self.subTest(name):
                instances = symbol_preview.parse_symbolizers(json.dumps([_preview_item(name)]))
                preview = etree.fromstring(symbol_preview.build_sld('preview_x', instances))
                with open(os.path.join(GOLDEN_DIR, 'newsym_%s.sld' % name), 'rb') as f:
                    published = etree.fromstring(f.read())
                ns = {'sld': 'http://www.opengis.net/sld'}
                sym = lambda root: [etree.tostring(n) for n in root.xpath('//sld:Rule/*[contains(local-name(), "Symbolizer")]', namespaces=ns)]
                a, b = sym(preview), sym(published)
                if name == 'line_arrows':  # la vista previa usa la columna geom de las tablas preview
                    b = [x.replace(b'wkb_geometry', b'geom') for x in b]
                self.assertEqual(a, b)

    def test_rejects_bad_input(self):
        from gvsigol_symbology import symbol_preview
        bad = [None, '', 'no json', '[]', json.dumps([{'type': 'TextSymbolizer', 'json': '{}'}]),
               json.dumps([{'type': 'LineSymbolizer', 'json': json.dumps({'stroke': 'red"/><x'})}]),
               json.dumps([_preview_item('line_railway')] * 11)]
        for raw in bad:
            with self.subTest(raw=raw):
                with self.assertRaises(symbol_preview.PreviewError):
                    symbol_preview.parse_symbolizers(raw)
        with self.assertRaises(symbol_preview.PreviewError):
            symbol_preview.requests_for([('LAYER', 'ws:otra_capa')], [], 20, 20)

    def test_requests(self):
        from gvsigol_symbology import symbol_preview
        lines = symbol_preview.parse_symbolizers(json.dumps([_preview_item('line_arrows')]))
        attempts = symbol_preview.requests_for([('LAYER', 'preview_line'), ('WIDTH', '20')], lines, 160, 9999)
        self.assertEqual([a[1] for a in attempts], [True, False])  # GetMap y, si falla, la leyenda
        getmap = dict(attempts[0][0])
        self.assertEqual((getmap['REQUEST'], getmap['WIDTH'], getmap['HEIGHT']), ('GetMap', '160', '600'))
        # nombre cualificado en LAYERS y en el NamedLayer: si no, GeoServer pinta el estilo guardado
        self.assertEqual(getmap['LAYERS'], 'preview:preview_line')
        self.assertIn('<sld:Name>preview:preview_line</sld:Name>', getmap['SLD_BODY'])
        self.assertIn('<sld:Name>preview_line</sld:Name>', dict(attempts[1][0])['SLD_BODY'].decode('utf-8'))
        self.assertIn('geomFromWKT', getmap['SLD_BODY'])
        self.assertNotIn('<ogc:PropertyName>geom</ogc:PropertyName>', getmap['SLD_BODY'])
        polys = symbol_preview.parse_symbolizers(json.dumps([_preview_item('polygon_hatch_bg')]))
        attempts = symbol_preview.requests_for([('LAYER', 'preview_polygon')], polys)
        self.assertEqual(len(attempts), 1)
        self.assertEqual(dict(attempts[0][0])['REQUEST'], 'GetLegendGraphic')

    def _view(self, params, forward, password=None):
        from django.contrib.auth.models import User
        from django.test import Client
        from gvsigol_symbology import views
        from gvsigol_services.models import Server
        user = (User.objects.filter(username='preview_admin_test').first()
                or User.objects.create_superuser('preview_admin_test', 'p@example.org', 'x'))
        client = Client()
        client.force_login(user)
        if password:   # sesión con contraseña (LDAP/local); sin ella es una sesión de Keycloak
            session = client.session
            session['password'] = password
            session.save()
        gs = mock.Mock(conf_url='http://gs-internal:8080/geoserver', user='svc', password='svc-pass')
        servers = [mock.Mock(id=1, frontend_url='/geoserver')]
        with mock.patch.object(Server.objects, 'all', return_value=servers), \
                mock.patch.object(views.geographic_servers, 'get_instance') as inst, \
                mock.patch.object(views.service_utils, 'getUserAuthSession', return_value=mock.Mock()), \
                mock.patch.object(views.geoserver_proxy, 'forward_form', side_effect=forward) as fwd:
            inst.return_value.get_server_by_id.return_value = gs
            return client.get('/gvsigonline/symbology/symbol_preview/', params), fwd

    def test_view_falls_back_to_legend(self):
        png = mock.Mock(status_code=200, content=b'PNG', headers={'Content-Type': 'image/png'})
        denied = mock.Mock(status_code=401, content=b'', headers={'Content-Type': 'text/html'})
        resp, fwd = self._view({'url': self.URL % 'line', 'width': '160', 'height': '80',
                                'symbolizers': json.dumps([_preview_item('line_arrows')])},
                               lambda session, url, query: denied if dict(query)['REQUEST'] == 'GetMap' else png,
                               password='secreto')
        self.assertEqual((resp.status_code, resp.content), (200, b'PNG'))
        self.assertEqual(fwd.call_count, 2)
        self.assertEqual(fwd.call_args[0][1], 'http://gs-internal:8080/geoserver/wms')
        # el GetMap (capas preview:*) va con las credenciales de servicio; la leyenda, con las del usuario
        getmap_session, legend_session = fwd.call_args_list[0][0][0], fwd.call_args_list[1][0][0]
        self.assertEqual(getmap_session.auth, ('svc', 'svc-pass'))
        self.assertIsNot(legend_session, getmap_session)

    def test_view_keycloak_session_legend_uses_service_credentials(self):
        # Sin contraseña (Keycloak): el token de la sesión puede haber caducado, así que la leyenda de la
        # capa técnica también va con las credenciales de servicio
        png = mock.Mock(status_code=200, content=b'PNG', headers={'Content-Type': 'image/png'})
        denied = mock.Mock(status_code=401, content=b'', headers={'Content-Type': 'text/html'})
        resp, fwd = self._view({'url': self.URL % 'line', 'width': '160', 'height': '80',
                                'symbolizers': json.dumps([_preview_item('line_arrows')])},
                               lambda session, url, query: denied if dict(query)['REQUEST'] == 'GetMap' else png)
        self.assertEqual((resp.status_code, resp.content), (200, b'PNG'))
        self.assertEqual([call[0][0].auth for call in fwd.call_args_list], [('svc', 'svc-pass')] * 2)

    def test_view_accepts_html_escaped_preview_url(self):
        # Así llega desde el editor: la plantilla escapa la URL ("{{ preview_url }}" -> &amp;)
        png = mock.Mock(status_code=200, content=b'PNG', headers={'Content-Type': 'image/png'})
        url = (self.URL % 'polygon').replace('&', '&amp;')
        resp, fwd = self._view({'url': url, 'symbolizers': json.dumps([_preview_item('polygon_hatch_bg')])},
                               lambda *a: png)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(dict(fwd.call_args[0][2])['LAYER'], 'preview_polygon')

    def test_view_rejects_other_layers_and_servers(self):
        png = mock.Mock(status_code=200, content=b'PNG', headers={'Content-Type': 'image/png'})
        item = json.dumps([_preview_item('polygon_none')])
        for url in ('/geoserver/wms?REQUEST=GetLegendGraphic&LAYER=ws:capa_privada',
                    'http://otro-host/geoserver/wms?REQUEST=GetLegendGraphic&LAYER=preview_polygon'):
            with self.subTest(url):
                resp, fwd = self._view({'url': url, 'symbolizers': item}, lambda *a: png)
                self.assertEqual(resp.status_code, 403)
                self.assertEqual(fwd.call_count, 0)


class LibraryCompatExportTest(TestCase):
    '''Exportación para versiones anteriores: los símbolos avanzados salen como clásicos.'''

    def test_compat_symbol_is_legacy_and_readable_by_old_importer(self):
        from gvsigol_symbology import services_library
        from gvsigol_symbology.models import Library, LibraryRule
        style = _style('compat_lib_lib_x', 'US')
        r = _rule(style, 'compat_hex', title='Hexágono')
        _new_mark(r, {'shape': 'qgis://hexagon', 'displacement': {'x': 3, 'y': 0}}, well_known_name='circle')
        r2 = _rule(style, 'compat_hatch', title='Trama')
        _new_poly(r2, {'fill': {'type': 'hatch', 'hatch': {'pattern': 'slash'}}})
        library = Library.objects.create(name='compat_lib', description='')
        LibraryRule.objects.create(library=library, rule=r)
        LibraryRule.objects.create(library=library, rule=r2)
        self.assertEqual(services_library.advanced_symbol_count(library), 2)
        for rule in (r, r2):
            sld = sld_builder.build_library_symbol(rule, ignore_options=True)
            self.assertNotIn(b'gvsigol-symbol', sld)
            self.assertNotIn(b'GraphicFill', sld)
            self.assertNotIn(b'qgis://', sld)
        # el lector posicional (el de las versiones anteriores) lo importa sin errores
        result = LibraryUploadCharacterizationTest._upload(self, 'compat_import', {
            'symbol-hex-0.sld': sld_builder.build_library_symbol(r, ignore_options=True),
            'symbol-hatch-1.sld': sld_builder.build_library_symbol(r2, ignore_options=True)})
        self.assertIsNone(result['error'])
        self.assertEqual(result['rules']['compat_hex'][0]['well_known_name'], 'circle')
        self.assertEqual(result['rules']['compat_hatch'][0]['fill'], '#ffffcc')


class SymbolEditorRoundTripTest(TestCase):
    '''
    Lo que envían los editores JS (MarkSymbolizer/LineSymbolizer/PolygonSymbolizer.toJSON, capturado
    con scratchpad/editortest/editor_test.js en test_golden/symbol_editor_output.json) se guarda,
    se publica y se previsualiza sin errores; un símbolo clásico editado sigue siendo clásico.
    '''

    def test_editor_output(self):
        from lxml import etree
        from gvsigol_symbology import symbol_options as so, symbol_preview
        from gvsigol_symbology.symbolizer_factory import create_symbolizer_from_json
        with open(os.path.join(GOLDEN_DIR, 'symbol_editor_output.json'), encoding='utf-8') as f:
            payloads = json.load(f)
        geoms = {'MarkSymbolizer': POINT_GEOM, 'LineSymbolizer': LINE_GEOM, 'PolygonSymbolizer': POLYGON_GEOM}
        for name, payload in payloads.items():
            with self.subTest(name):
                style = _style('editor_' + name, 'US')
                rule = _rule(style, 'editor_r')
                sym = create_symbolizer_from_json(rule, {'type': payload['type'], 'order': '0',
                                                         'json': json.dumps(payload['json'])})
                sym = type(sym).objects.get(pk=sym.pk)
                sent = payload['json'].get('options')
                if sent is None:
                    self.assertIsNone(sym.options)
                else:
                    self.assertEqual(so.of(sym), so.normalize(so.kind_of(sym), sent))
                    # el editor ya envía el esquema completo: normalizar no cambia nada
                    self.assertEqual(so.normalize(so.kind_of(sym), sent), sent)
                with mock.patch.object(utils, 'get_geometry_field', return_value=geoms[payload['type']]):
                    sld = sld_builder.build_sld(_layer(), style)
                etree.fromstring(sld)
                self.assertEqual(b'gvsigol-symbol' in sld, sent is not None)
                instances = symbol_preview.parse_symbolizers(json.dumps([{'type': payload['type'],
                                                                          'json': json.dumps(payload['json'])}]))
                self.assertEqual(len(instances), 1)


class LibraryExportTemplatesTest(TemplatesRenderWithRealContextTest):
    '''Aviso y exportación para versiones anteriores en las páginas de biblioteca (fase 5).'''

    def test_library_update_with_and_without_advanced_symbols(self):
        from types import SimpleNamespace as NS
        library = NS(id=1, name='lib', description='d')
        html = self._render('library_update.html', {'library': library, 'rules': [], 'advanced_symbols': 3})
        self.assertIn('library_export/1/?compat=1', html)
        self.assertIn('gol-sym-export-note', html)
        self.assertRegex(html, r'gol-sym-export-note">.*\b3\b')  # el número, en el idioma activo
        html = self._render('library_update.html', {'library': library, 'rules': [], 'advanced_symbols': 0})
        self.assertNotIn('compat=1', html)
        self.assertNotIn('gol-sym-export-note', html)

    def test_library_list_counts(self):
        from types import SimpleNamespace as NS
        html = self._render('library_list.html', {'libraries': [NS(id=1, name='lib', description='')],
                                                  'advanced_counts': utils.json_for_script({'1': 2})})
        self.assertIn('var advancedCounts = {"1": 2};', html)
        self.assertIn('id="modal-export-library"', html)

    def test_library_list_view(self):
        from django.contrib.auth.models import User
        from django.test import Client
        from gvsigol_symbology.models import Library, LibraryRule
        style = _style('view_lib_lib_x', 'US')
        rule = _rule(style, 'view_hex')
        _new_mark(rule, {'shape': 'qgis://hexagon'})
        library = Library.objects.create(name='view_lib', description='')
        LibraryRule.objects.create(library=library, rule=rule)
        user = (User.objects.filter(username='lib_admin_test').first()
                or User.objects.create_superuser('lib_admin_test', 'l@example.org', 'x'))
        client = Client()
        client.force_login(user)
        resp = client.get('/gvsigonline/symbology/library_list/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('"%d": 1' % library.id, resp.content.decode('utf-8'))


class SymbolPresetsTest(TestCase):
    '''
    Fase 6: los símbolos predefinidos (SymbolPresets.js; salida del editor capturada con
    scratchpad/editortest/presets_dump.js en test_golden/symbol_presets_output.json) se guardan, se
    publican y se previsualizan, y sus opciones ya vienen en el esquema completo.
    '''

    def test_presets(self):
        from lxml import etree
        from gvsigol_symbology import symbol_options as so, symbol_preview
        from gvsigol_symbology.symbolizer_factory import create_symbolizer_from_json
        with open(os.path.join(GOLDEN_DIR, 'symbol_presets_output.json'), encoding='utf-8') as f:
            presets = json.load(f)
        self.assertEqual(len(presets), 33)
        geoms = {'PointSymbolizer': POINT_GEOM, 'LineSymbolizer': LINE_GEOM, 'PolygonSymbolizer': POLYGON_GEOM}
        for key, preset in presets.items():
            with self.subTest(key):
                geom_type = key.split(':')[0]
                style = _style('preset_' + key.split(':')[1], 'US')
                rule = _rule(style, 'preset_r')
                for sym in preset['symbolizers']:
                    created = create_symbolizer_from_json(rule, {'type': sym['type'], 'order': str(sym['json']['order']),
                                                                 'json': json.dumps(sym['json'])})
                    created = type(created).objects.get(pk=created.pk)
                    sent = sym['json'].get('options')
                    if sent is None:
                        self.assertIsNone(created.options)
                    else:
                        self.assertEqual(so.normalize(so.kind_of(created), sent), sent)
                        if so.kind_of(created) == 'mark':
                            self.assertEqual(created.well_known_name, so.legacy_shape(sent['shape']))
                with mock.patch.object(utils, 'get_geometry_field', return_value=geoms[geom_type]):
                    sld = sld_builder.build_sld(_layer(), style)
                etree.fromstring(sld)
                self.assertEqual(b'gvsigol-symbol' in sld, preset['advanced'])
                instances = symbol_preview.parse_symbolizers(json.dumps(
                    [{'type': s['type'], 'json': json.dumps(s['json'])} for s in preset['symbolizers']]))
                self.assertEqual(len(instances), len(preset['symbolizers']))
