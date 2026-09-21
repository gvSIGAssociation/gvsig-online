# -*- coding: utf-8 -*-
from django.test import SimpleTestCase
from lxml import etree as ET

from gvsigol_plugin_catalog.mdstandards import registry
from gvsigol_plugin_catalog.mdstandards.templates import plugin_mdtemplate
from gvsigol_plugin_catalog.mdstandards.iso19115_3_mgb import MGB_PROFILE_TITLE
from gvsigol_plugin_catalog.mdstandards.iso19139_2007 import Iso19139_2007Reader
from gvsigol_plugin_catalog.mdstandards.iso19115_3 import Iso19115_3Reader
from gvsigol_plugin_catalog.mdstandards.iso19115_3_mgb import Iso19115_3MgbReader

MGB_UF_SNIPPET = '''
      <cit:contactInfo xmlns:cit="http://standards.iso.org/iso/19115/-3/cit/2.0">
        <cit:CI_Contact>
          <cit:address>
            <cit:CI_Address>
              <cit:administrativeArea>
                <cit:CI_UFCode codeList="http://inde.gov.br/mgb/2.0#CI_UFCode" codeListValue="TO"/>
              </cit:administrativeArea>
            </cit:CI_Address>
          </cit:address>
        </cit:CI_Contact>
      </cit:contactInfo>
'''


def _mdfields():
    return {
        'title': 'Camada de teste',
        'abstract': 'Resumo da camada de teste',
        'qualified_name': 'workspace:layer',
        'extent_tuple': ('-48.5', '-13.5', '-45.5', '-5.0'),
        'crs': 'EPSG:4674',
        'spatial_representation_type': 'vector',
        'thumbnail_url': 'https://example.test/thumb.png',
        'wms_endpoint': 'https://example.test/wms',
        'wfs_endpoint': 'https://example.test/wfs',
        'wcs_endpoint': None,
    }


class MetadataStandardsTests(SimpleTestCase):
    def test_reader_detects_iso19139_template(self):
        xml = ET.parse(plugin_mdtemplate('dataset19139.xml'))
        reader = registry.get_reader(xml.getroot())
        self.assertIsInstance(reader, Iso19139_2007Reader)
        record = reader.as_catalog_record()
        self.assertTrue(record.get('title'))
        self.assertFalse(record.get('metadata_profile'))

    def test_reader_detects_iso19115_3_template(self):
        xml = ET.parse(plugin_mdtemplate('dataset19115-3.xml'))
        reader = registry.get_reader(xml.getroot())
        self.assertIsInstance(reader, Iso19115_3Reader)
        self.assertNotIsInstance(reader, Iso19115_3MgbReader)
        record = reader.as_catalog_record()
        self.assertIn('ISO 19115-1', record.get('metadata_standard_name', ''))
        self.assertEqual(record.get('metadata_profile'), '')

    def test_reader_detects_mgb_template(self):
        xml = ET.parse(plugin_mdtemplate('dataset19115-3.mgb.xml'))
        reader = registry.get_reader(xml.getroot())
        self.assertIsInstance(reader, Iso19115_3MgbReader)
        record = reader.as_catalog_record()
        self.assertEqual(record.get('metadata_profile'), MGB_PROFILE_TITLE)
        self.assertIn('ISO 19115-1', record.get('metadata_standard_name', ''))

    def test_mgb_reader_extracts_uf_code(self):
        tree = ET.parse(plugin_mdtemplate('dataset19115-3.mgb.xml'))
        org = tree.find(
            './/{http://standards.iso.org/iso/19115/-3/cit/2.0}CI_Organisation'
        )
        org.append(ET.fromstring(MGB_UF_SNIPPET))
        reader = registry.get_reader(tree.getroot())
        record = reader.as_catalog_record()
        self.assertIn('TO', record.get('geographic_place', []))

    def test_create_default_is_iso19139(self):
        xml = registry.create('dataset', _mdfields())
        root = ET.fromstring(xml)
        self.assertEqual(
            ET.QName(root).namespace,
            'http://www.isotc211.org/2005/gmd',
        )
        self.assertIn('Camada de teste', xml)

    def test_create_iso19115_3(self):
        xml = registry.create('dataset', _mdfields(), mdcode='iso19115-3')
        root = ET.fromstring(xml)
        self.assertIn('/iso/19115/-3/mdb/', ET.QName(root).namespace)
        reader = registry.get_reader(root)
        self.assertIsInstance(reader, Iso19115_3Reader)
        self.assertNotIsInstance(reader, Iso19115_3MgbReader)
        record = reader.as_catalog_record()
        self.assertEqual(record['title'], 'Camada de teste')
        self.assertEqual(record['resource_identifier'], 'workspace:layer')
        self.assertEqual(record['srs'], 'EPSG:4674')

    def test_create_mgb(self):
        xml = registry.create('dataset', _mdfields(), mdcode='mgb-2.0')
        root = ET.fromstring(xml)
        reader = registry.get_reader(root)
        self.assertIsInstance(reader, Iso19115_3MgbReader)
        record = reader.as_catalog_record()
        self.assertEqual(record['metadata_profile'], MGB_PROFILE_TITLE)
        self.assertEqual(record['title'], 'Camada de teste')
        self.assertTrue(any(res.get('protocol') == 'OGC:WMS' for res in record['resources']))

    def test_mgb_updater_rewrites_extent(self):
        xml = registry.create('dataset', _mdfields(), mdcode='iso19115-3.mgb')
        updater = registry.get_updater(xml)
        updated = updater.update_all(('-50', '-14', '-44', '-4'), 'https://example.test/new.png').tostring()
        record = registry.get_reader(updated).as_catalog_record()
        self.assertEqual(record['extent_west'], '-50')
        self.assertEqual(record['extent_east'], '-44')
        self.assertTrue(any(t['url'] == 'https://example.test/new.png' for t in record['thumbnails']))
