# -*- coding: utf-8 -*-
from io import BytesIO
from unittest import mock

from PIL import Image
from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import RequestFactory, SimpleTestCase, TestCase
from gvsigol_plugin_panels.utils import (
    unique_slug, normalize_rows, apply_widget_payload, serialize_panel,
    is_vector_layer,
)
from gvsigol_plugin_panels.models import Panel, PanelWidget
from gvsigol_plugin_panels.views import _reassignable_roles, _uploaded_panel_image


class FakeQuerySet:
    def __init__(self, slugs):
        self.slugs = set(slugs)

    def exclude(self, pk=None):
        return self

    def filter(self, slug=None):
        class R:
            def __init__(self, exists):
                self._exists = exists

            def exists(self):
                return self._exists
        return R(slug in self.slugs)


class FakeManager:
    def __init__(self, slugs):
        self._qs = FakeQuerySet(slugs)

    def all(self):
        return self._qs

    def filter(self, slug=None):
        return self._qs.filter(slug=slug)

    def exclude(self, pk=None):
        return self._qs.exclude(pk=pk)


class UtilsTests(SimpleTestCase):
    def test_unique_slug_increments(self):
        with mock.patch.object(Panel, 'objects', FakeManager({'informe', 'informe-2'})):
            self.assertEqual(unique_slug('Informe'), 'informe-3')

    def test_normalize_rows_limit_and_keys(self):
        rows = [{'A': 1}, 'skip', {None: 2, 'b': 3}]
        out = normalize_rows(rows, limit=10)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]['A'], 1)
        self.assertIn('b', out[1])

    def test_apply_widget_payload_defaults(self):
        widget = PanelWidget(widget_type='bar', filter_mode='linked')
        apply_widget_payload(widget, {
            'widget_type': 'not-a-type',
            'title': 'KPI',
            'filter_mode': 'independent',
            'x': 2,
            'dataset_id': '',
        }, index=4)
        self.assertEqual(widget.widget_type, 'bar')
        self.assertEqual(widget.title, 'KPI')
        self.assertEqual(widget.filter_mode, 'independent')
        self.assertEqual(widget.x, 2)
        self.assertIsNone(widget.dataset_id)
        self.assertEqual(widget.sort_order, 4)

    def test_raster_layers_are_not_vector(self):
        raster = mock.Mock(type='c_GeoTIFF')
        raster.datastore.type = 'c_GeoTIFF'
        vector = mock.Mock(type='v_PostGIS')
        vector.datastore.type = 'v_PostGIS'
        shapefile = mock.Mock(type='')
        shapefile.datastore.type = 'v_SHP'
        self.assertFalse(is_vector_layer(raster))
        self.assertTrue(is_vector_layer(vector))
        self.assertTrue(is_vector_layer(shapefile))

    def test_panel_image_falls_back_to_default(self):
        panel = Panel(title='Panel', slug='panel')
        self.assertTrue(panel.image_url.endswith('/panels/panel.svg'))

    def test_uploaded_panel_image_is_validated(self):
        content = BytesIO()
        Image.new('RGB', (2, 2), '#26648c').save(content, format='PNG')
        request = RequestFactory().post('/', {
            'panel-image': SimpleUploadedFile(
                'panel.png', content.getvalue(), content_type='image/png'),
        })
        image = _uploaded_panel_image(request)
        self.assertEqual(image.name, 'panel.png')

    def test_invalid_panel_image_is_rejected(self):
        request = RequestFactory().post('/', {
            'panel-image': SimpleUploadedFile(
                'panel.png', b'not an image', content_type='image/png'),
        })
        with self.assertRaises(ValidationError):
            _uploaded_panel_image(request)


class FakeRoleQuerySet:
    def __init__(self, roles):
        self.roles = roles

    def values_list(self, field, flat=False):
        return list(self.roles)


class PublishLayersTests(SimpleTestCase):
    def test_reassignable_roles_drops_duplicates_and_admin(self):
        roles = FakeRoleQuerySet(
            ['GVSIGOL_DJANGO_SUPERUSER', 'tecnicos', 'tecnicos', 'consulta'])
        self.assertEqual(
            _reassignable_roles(roles, ('GVSIGOL_DJANGO_SUPERUSER',)),
            ['tecnicos', 'consulta'])

    def test_reassignable_roles_keeps_admin_when_not_skipped(self):
        roles = FakeRoleQuerySet(['GVSIGOL_DJANGO_SUPERUSER'])
        self.assertEqual(
            _reassignable_roles(roles), ['GVSIGOL_DJANGO_SUPERUSER'])


class StandalonePanelTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.owner = User.objects.create_user(username='panel-owner')

    def request_for(self, user):
        request = self.factory.get('/')
        request.user = user
        return request

    def test_standalone_owner_can_manage_private_panel(self):
        panel = Panel.objects.create(
            title='Autonomous', slug='autonomous', created_by=self.owner.username)
        self.assertTrue(panel.can_read(self.request_for(self.owner)))
        self.assertTrue(panel.can_manage(self.request_for(self.owner)))
        self.assertFalse(panel.can_read(self.request_for(AnonymousUser())))

    def test_public_standalone_panel_is_anonymous_readable(self):
        panel = Panel.objects.create(
            title='Public', slug='public-panel', is_public=True)
        self.assertTrue(panel.can_read(self.request_for(AnonymousUser())))

    def test_standalone_paths_do_not_contain_project(self):
        panel = Panel.objects.create(title='Global', slug='global-panel')
        data = serialize_panel(panel, include_widgets=False)
        self.assertEqual(data['public_path'], '/panel/global-panel/')
        self.assertEqual(data['edit_path'], '/panel/global-panel/edit/')
        self.assertEqual(data['relative_image'], panel.image_url)
        self.assertEqual(data['image'], settings.BASE_URL + panel.image_url)
        self.assertTrue(data['image'].startswith(('http://', 'https://')))

    def test_standalone_slug_is_unique(self):
        Panel.objects.create(title='First', slug='same')
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Panel.objects.create(title='Second', slug='same')
