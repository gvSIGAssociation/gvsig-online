# -*- coding: utf-8 -*-
"""Regla de URL checks de GeoServer para los iconos de las bibliotecas (sin GeoServer real)."""
from unittest import mock

from django.test import SimpleTestCase, override_settings

from gvsigol_symbology import geoserver_urlchecks as uc


class FakeResponse:
    def __init__(self, status, payload=None):
        self.status_code = status
        self._payload = payload

    def json(self):
        return self._payload


def fake_gs(rules=None):
    """rules: {nombre: regla}. Devuelve (gs, session)."""
    rules = dict(rules or {})
    session = mock.Mock()

    def get(url, **kw):
        if url.endswith('/urlchecks.json'):
            items = [{'name': n} for n in rules]
            return FakeResponse(200, {'urlChecks': {'urlCheck': items} if items else ''})
        name = url.rsplit('/', 1)[-1][:-len('.json')]
        return FakeResponse(200, {'regexUrlCheck': rules[name]}) if name in rules else FakeResponse(404)

    session.get.side_effect = get
    session.post.return_value = FakeResponse(201)
    gs = mock.Mock(rest_url='https://gs/geoserver/rest', user='u', password='p')
    gs.rest_catalog.session = session
    return gs, session


@override_settings(MEDIA_ROOT='/opt/gvsigol_data/', MEDIA_URL='/media/')
class UrlChecksTests(SimpleTestCase):
    def setUp(self):
        uc._done.clear()

    def test_regex_matches_both_file_forms(self):
        rule = {'enabled': True, 'regex': uc.library_regex()}
        for url in uc.sample_urls():
            self.assertTrue(uc.rule_allows(rule, url))
        self.assertFalse(uc.rule_allows(rule, 'file:/etc/passwd'))
        self.assertFalse(uc.rule_allows(rule, 'file:/opt/gvsigol_data/data/x.svg'))
        self.assertFalse(uc.rule_allows({'enabled': False, 'regex': '.*'}, uc.sample_urls()[0]))

    def test_creates_rule_when_missing_and_is_idempotent(self):
        gs, session = fake_gs()
        self.assertEqual(uc.ensure_symbol_library_urlcheck(gs), 'created')
        body = session.post.call_args[1]['json']['regexUrlCheck']
        self.assertEqual(body['name'], uc.RULE_NAME)
        gs2, session2 = fake_gs({uc.RULE_NAME: body})
        self.assertEqual(uc.ensure_symbol_library_urlcheck(gs2), 'exists')
        session2.post.assert_not_called()

    def test_existing_broader_rule_is_respected(self):
        gs, session = fake_gs({'todo': {'enabled': True, 'regex': '^file:.*$'}})
        self.assertEqual(uc.ensure_symbol_library_urlcheck(gs), 'exists')
        session.post.assert_not_called()

    def test_errors_never_raise(self):
        gs, session = fake_gs()
        session.get.side_effect = OSError('sin red')
        self.assertEqual(uc.ensure_symbol_library_urlcheck(gs), 'error')

    @override_settings(GEOSERVER_ENSURE_SYMBOL_URLCHECK=False)
    def test_hook_does_nothing_by_default(self):
        gs, session = fake_gs()
        self.assertIsNone(uc.maybe_ensure_for_sld(gs, '<x href="file:/opt/gvsigol_data/symbol_libraries/a.svg"/>'))
        session.get.assert_not_called()

    @override_settings(GEOSERVER_ENSURE_SYMBOL_URLCHECK=True)
    def test_hook_only_for_library_icons_and_once(self):
        gs, session = fake_gs()
        self.assertIsNone(uc.maybe_ensure_for_sld(gs, '<sld>sin iconos</sld>'))
        session.get.assert_not_called()
        self.assertEqual(uc.maybe_ensure_for_sld(gs, b'file:/opt/gvsigol_data/symbol_libraries/a.svg'), 'created')
        self.assertIsNone(uc.maybe_ensure_for_sld(gs, 'file:/opt/gvsigol_data/symbol_libraries/a.svg'))
        self.assertEqual(session.post.call_count, 1)
