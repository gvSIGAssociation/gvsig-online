# -*- coding: utf-8 -*-
"""Brazilian Geospatial Metadata Profile MGB 2.0 (ISO 19115-3 profile)."""
from gvsigol_plugin_catalog.xmlutils import getTextFromXMLNode, getXMLCodeText, sanitizeXmlText
from .iso19115_3 import Iso19115_3Manager, Iso19115_3Reader, Iso19115_3Updater, ns_for
from .templates import plugin_mdtemplate, resolve_mdtemplate

MGB_PROFILE_TITLE = 'Perfil MGB 2.0'


def get_mgb_template(md_type):
    fallback = plugin_mdtemplate('dataset19115-3.mgb.xml')
    return resolve_mdtemplate(
        ['dataset-mgb.xml', 'dataset19115-3.mgb.xml'],
        fallback,
    )


class Iso19115_3MgbReader(Iso19115_3Reader):
    def _geographic_place(self, ident):
        places = super()._geographic_place(ident)
        for area in self.tree.findall('.//cit:administrativeArea', self.ns):
            code_node = area.find('./cit:CI_UFCode', self.ns)
            if code_node is not None:
                value = getXMLCodeText(code_node) or ''.join(code_node.itertext()).strip()
            else:
                value = ''.join(area.itertext()).strip()
            if value:
                sanitized = sanitizeXmlText(value)
                if sanitized not in places:
                    places.append(sanitized)
        return places


class Iso19115_3MgbUpdater(Iso19115_3Updater):
    pass


class Iso19115_3MgbManager(Iso19115_3Manager):
    def get_code(self):
        return 'Iso19115_3MgbManager'

    def get_priority(self):
        return 200

    def get_reader_instance(self, metadata_record):
        return Iso19115_3MgbReader(metadata_record)

    def get_updater_instance(self, metadata_record):
        return Iso19115_3MgbUpdater(metadata_record)

    def can_extract(self, metadata_record):
        if not super().can_extract(metadata_record):
            return False
        ns = ns_for(metadata_record)
        profile = getTextFromXMLNode(
            metadata_record,
            './mdb:metadataProfile/cit:CI_Citation/cit:title',
            ns,
        )
        if not profile:
            profile = getTextFromXMLNode(metadata_record, './mdb:metadataProfile', ns)
        return MGB_PROFILE_TITLE.lower() in (profile or '').lower()

    def get_dataset_template(self):
        return get_mgb_template('dataset')
