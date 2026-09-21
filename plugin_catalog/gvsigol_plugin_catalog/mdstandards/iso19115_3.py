# -*- coding: utf-8 -*-
"""ISO 19115-1 encoded as ISO 19115-3 (mdb) for GeoNetwork 4.x."""
from builtins import str as text
from datetime import datetime
import collections
import logging

from lxml import etree as ET

from gvsigol_plugin_catalog.xmlutils import (
    getTextFromXMLNode,
    getXMLCodeText,
    insertAfter,
    sanitizeXmlText,
)
from .catalog_record import empty_catalog_record, empty_constraints
from .registry import BaseStandardManager, XmlStandardReader, XmlStandardUpdater
from .templates import plugin_mdtemplate, resolve_mdtemplate

logger = logging.getLogger('gvsigol')

NS = {
    'mdb': 'http://standards.iso.org/iso/19115/-3/mdb/2.0',
    'mri': 'http://standards.iso.org/iso/19115/-3/mri/1.0',
    'cit': 'http://standards.iso.org/iso/19115/-3/cit/2.0',
    'gco': 'http://standards.iso.org/iso/19115/-3/gco/1.0',
    'gex': 'http://standards.iso.org/iso/19115/-3/gex/1.0',
    'mcc': 'http://standards.iso.org/iso/19115/-3/mcc/1.0',
    'mrd': 'http://standards.iso.org/iso/19115/-3/mrd/1.0',
    'mco': 'http://standards.iso.org/iso/19115/-3/mco/1.0',
    'mmi': 'http://standards.iso.org/iso/19115/-3/mmi/1.0',
    'lan': 'http://standards.iso.org/iso/19115/-3/lan/1.0',
    'mrs': 'http://standards.iso.org/iso/19115/-3/mrs/1.0',
    'gml': 'http://www.opengis.net/gml/3.2',
}

CL = 'http://standards.iso.org/iso/19115/resources/Codelists/cat/codelists.xml'
GVSIGOL_THUMBNAIL = 'gvsigol thumbnail'
NS_MARKERS = {
    'mdb': '/iso/19115/-3/mdb/',
    'mri': '/iso/19115/-3/mri/',
    'cit': '/iso/19115/-3/cit/',
    'gco': '/iso/19115/-3/gco/',
    'gex': '/iso/19115/-3/gex/',
    'mcc': '/iso/19115/-3/mcc/',
    'mrd': '/iso/19115/-3/mrd/',
    'mco': '/iso/19115/-3/mco/',
    'mmi': '/iso/19115/-3/mmi/',
    'lan': '/iso/19115/-3/lan/',
    'mrs': '/iso/19115/-3/mrs/',
}


def ns_for(elem):
    """Bind prefixes to the namespace URIs actually used in the document."""
    ns = dict(NS)
    nsmap = getattr(elem, 'nsmap', None) or {}
    for uri in nsmap.values():
        if not uri:
            continue
        for prefix, marker in NS_MARKERS.items():
            if marker in uri:
                ns[prefix] = uri
        if uri.endswith('/gml/3.2') or uri.endswith('/gml'):
            ns['gml'] = uri
    return ns


def is_iso19115_3_root(elem):
    qname = ET.QName(elem)
    namespace = qname.namespace or ''
    return qname.localname == 'MD_Metadata' and '/iso/19115/-3/mdb/' in namespace


def q(prefix, tag):
    return '{%s}%s' % (NS[prefix], tag)


def _set_text(elem, value):
    if elem is None:
        return
    cs = elem.find('./gco:CharacterString', NS)
    if cs is not None:
        cs.text = value
        return
    if ET.QName(elem).localname in ('CharacterString', 'Decimal', 'Date', 'DateTime', 'Real'):
        elem.text = value
        return
    if len(elem):
        _set_text(elem[0], value)
    else:
        elem.text = value


def _code_value(node):
    return sanitizeXmlText(getXMLCodeText(node)) if node is not None else ''


def _identification(tree, ns=None):
    ns = ns or ns_for(tree)
    ident = tree.find('./mdb:identificationInfo/mri:MD_DataIdentification', ns)
    if ident is None:
        ident = tree.find('./mdb:identificationInfo/*', ns)
    return ident


def get_template(md_type):
    fallback = plugin_mdtemplate('dataset19115-3.xml')
    return resolve_mdtemplate(['dataset19115-3.xml'], fallback)


def create_dataset_metadata(mdfields, template_path=None):
    try:
        qualified_name = mdfields.get('qualified_name')
        title = mdfields.get('title')
        abstract = mdfields.get('abstract')
        extent_tuple = mdfields.get('extent_tuple', (0.0, 0.0, 0.0, 0.0))
        crs = mdfields.get('crs')
        thumbnail_url = mdfields.get('thumbnail_url')
        wms_endpoint = mdfields.get('wms_endpoint')
        wfs_endpoint = mdfields.get('wfs_endpoint')
        wcs_endpoint = mdfields.get('wcs_endpoint')
        spatial_representation_type = mdfields.get('spatial_representation_type', 'vector')
        current_datetime = datetime.now()

        tree = ET.parse(template_path or get_template('dataset'))
        ident = _identification(tree)
        if ident is None:
            raise ValueError('ISO 19115-3 template has no identificationInfo')

        spatial_code = ident.find('.//mcc:MD_SpatialRepresentationTypeCode', NS)
        if spatial_code is not None and spatial_representation_type:
            spatial_code.set('codeListValue', spatial_representation_type)

        title_elem = ident.find('./mri:citation/cit:CI_Citation/cit:title', NS)
        _set_text(title_elem, title)
        abstract_elem = ident.find('./mri:abstract', NS)
        _set_text(abstract_elem, abstract)

        crs_elem = tree.find(
            './mdb:referenceSystemInfo/mrs:MD_ReferenceSystem'
            '/mrs:referenceSystemIdentifier/mcc:MD_Identifier/mcc:code',
            NS,
        )
        _set_text(crs_elem, crs)

        date_node = ident.find(
            './mri:citation/cit:CI_Citation/cit:date/cit:CI_Date/cit:date',
            NS,
        )
        if date_node is not None:
            date_time = date_node.find('./gco:DateTime', NS)
            date_only = date_node.find('./gco:Date', NS)
            if date_time is not None:
                date_time.text = text(current_datetime.isoformat())
            elif date_only is not None:
                date_only.text = text(current_datetime.date().isoformat())

        if thumbnail_url:
            create_thumbnail(tree, thumbnail_url, title)

        minx, miny, maxx, maxy = extent_tuple
        bbox = ident.find('.//gex:EX_GeographicBoundingBox', NS)
        if bbox is not None:
            update_extent(bbox, (minx, miny, maxx, maxy))
        else:
            create_extent(tree, minx, miny, maxx, maxy)

        create_transfer_options(
            tree, qualified_name, spatial_representation_type,
            title, wms_endpoint, wfs_endpoint, wcs_endpoint,
        )
        for res_code in tree.xpath("//*[text()='RESOURCE_CODE']"):
            res_code.text = qualified_name
        return ET.tostring(tree, encoding='unicode')
    except Exception:
        logger.exception('Error creating ISO 19115-3 metadata')
        return None


def update_extent(geo_bb_elem, extent_tuple):
    minx, miny, maxx, maxy = extent_tuple
    for bound in geo_bb_elem:
        local = ET.QName(bound).localname
        if local == 'westBoundLongitude' and len(bound):
            bound[0].text = text(minx)
        elif local == 'eastBoundLongitude' and len(bound):
            bound[0].text = text(maxx)
        elif local == 'southBoundLatitude' and len(bound):
            bound[0].text = text(miny)
        elif local == 'northBoundLatitude' and len(bound):
            bound[0].text = text(maxy)


def create_thumbnail(root_elem, thumbnail_url, thumbnail_desc=None):
    ident = _identification(root_elem)
    if ident is None:
        return
    prev_siblings = [
        'mri:citation', 'mri:abstract', 'mri:purpose', 'mri:credit',
        'mri:status', 'mri:pointOfContact', 'mri:spatialRepresentationType',
        'mri:spatialResolution', 'mri:temporalResolution', 'mri:topicCategory',
        'mri:extent', 'mri:additionalDocumentation', 'mri:processingLevel',
        'mri:resourceMaintenance',
    ]
    overview = ET.Element(q('mri', 'graphicOverview'))
    insertAfter(ident, overview, prev_siblings, NS)
    browse = ET.SubElement(overview, q('mcc', 'MD_BrowseGraphic'))
    file_name = ET.SubElement(browse, q('mcc', 'fileName'))
    file_name_str = ET.SubElement(file_name, q('gco', 'CharacterString'))
    file_name_str.text = thumbnail_url
    if thumbnail_desc:
        file_desc = ET.SubElement(browse, q('mcc', 'fileDescription'))
        ET.SubElement(file_desc, q('gco', 'CharacterString')).text = thumbnail_desc
    file_type = ET.SubElement(browse, q('mcc', 'fileType'))
    ET.SubElement(file_type, q('gco', 'CharacterString')).text = GVSIGOL_THUMBNAIL


def create_extent(root_elem, minx, miny, maxx, maxy):
    ident = _identification(root_elem)
    if ident is None:
        return
    prev_siblings = [
        'mri:citation', 'mri:abstract', 'mri:purpose', 'mri:credit',
        'mri:status', 'mri:pointOfContact', 'mri:spatialRepresentationType',
        'mri:spatialResolution', 'mri:temporalResolution', 'mri:topicCategory',
        'mri:environmentDescription',
    ]
    extent_elem = ET.Element(q('mri', 'extent'))
    insertAfter(ident, extent_elem, prev_siblings, NS)
    ex_extent = ET.SubElement(extent_elem, q('gex', 'EX_Extent'))
    geog = ET.SubElement(ex_extent, q('gex', 'geographicElement'))
    bbox = ET.SubElement(geog, q('gex', 'EX_GeographicBoundingBox'))
    for tag, value in (
        ('westBoundLongitude', minx),
        ('eastBoundLongitude', maxx),
        ('southBoundLatitude', miny),
        ('northBoundLatitude', maxy),
    ):
        bound = ET.SubElement(bbox, q('gex', tag))
        decimal = ET.SubElement(bound, q('gco', 'Decimal'))
        decimal.text = text(value)


def create_online_resource(parent, url, protocol, name, description, application_profile=None, function=None):
    online = ET.SubElement(parent, q('mrd', 'onLine'))
    resource = ET.SubElement(online, q('cit', 'CI_OnlineResource'))
    linkage = ET.SubElement(resource, q('cit', 'linkage'))
    ET.SubElement(linkage, q('gco', 'CharacterString')).text = url
    protocol_elem = ET.SubElement(resource, q('cit', 'protocol'))
    ET.SubElement(protocol_elem, q('gco', 'CharacterString')).text = protocol
    if application_profile:
        profile_elem = ET.SubElement(resource, q('cit', 'applicationProfile'))
        ET.SubElement(profile_elem, q('gco', 'CharacterString')).text = application_profile
    name_elem = ET.SubElement(resource, q('cit', 'name'))
    ET.SubElement(name_elem, q('gco', 'CharacterString')).text = name
    desc_elem = ET.SubElement(resource, q('cit', 'description'))
    ET.SubElement(desc_elem, q('gco', 'CharacterString')).text = description
    if function:
        function_elem = ET.SubElement(resource, q('cit', 'function'))
        fn_code = ET.SubElement(function_elem, q('cit', 'CI_OnLineFunctionCode'))
        fn_code.set('codeList', CL + '#CI_OnLineFunctionCode')
        fn_code.set('codeListValue', function)


def create_distrib_format(parent, name, version, specification=None):
    fmt = ET.Element(q('mrd', 'distributionFormat'))
    md_format = ET.SubElement(fmt, q('mrd', 'MD_Format'))
    citation_wrap = ET.SubElement(md_format, q('mrd', 'formatSpecificationCitation'))
    citation = ET.SubElement(citation_wrap, q('cit', 'CI_Citation'))
    title = ET.SubElement(citation, q('cit', 'title'))
    ET.SubElement(title, q('gco', 'CharacterString')).text = name
    edition = ET.SubElement(citation, q('cit', 'edition'))
    ET.SubElement(edition, q('gco', 'CharacterString')).text = version
    if specification:
        alt = ET.SubElement(citation, q('cit', 'alternateTitle'))
        ET.SubElement(alt, q('gco', 'CharacterString')).text = specification
    insertAfter(parent, fmt, [], NS)


def _tree_root(root_elem):
    return root_elem.getroot() if hasattr(root_elem, 'getroot') else root_elem


def create_transfer_options(root_elem, qualified_name, spatial_representation_type, title, wms_endpoint, wfs_endpoint=None, wcs_endpoint=None):
    tree_root = _tree_root(root_elem)
    distribs = tree_root.findall('./mdb:distributionInfo/mrd:MD_Distribution', NS)
    if not distribs:
        dist_info = ET.SubElement(tree_root, q('mdb', 'distributionInfo'))
        md_dist = ET.SubElement(dist_info, q('mrd', 'MD_Distribution'))
        distribs = [md_dist]

    for distrib in distribs:
        if spatial_representation_type == 'vector':
            create_distrib_format(distrib, 'Shapefile', 'SHP 1.0')
        elif spatial_representation_type == 'grid':
            create_distrib_format(distrib, 'TIF', 'GeoTiff 1.0')
        transfer = ET.Element(q('mrd', 'transferOptions'))
        insertAfter(distrib, transfer, ['mrd:distributionFormat', 'mrd:distributor'], NS)
        options = ET.SubElement(transfer, q('mrd', 'MD_DigitalTransferOptions'))
        if wms_endpoint:
            create_online_resource(options, wms_endpoint, 'OGC:WMS', qualified_name, title)
        if wfs_endpoint:
            create_online_resource(options, wfs_endpoint, 'OGC:WFS', qualified_name, title)
        if wcs_endpoint:
            create_online_resource(options, wcs_endpoint, 'OGC:WCS', qualified_name, title)


class Iso19115_3Manager(BaseStandardManager):
    def get_code(self):
        return 'Iso19115_3Manager'

    def get_priority(self):
        return 150

    def get_updater_instance(self, metadata_record):
        return Iso19115_3Updater(metadata_record)

    def get_reader_instance(self, metadata_record):
        return Iso19115_3Reader(metadata_record)

    def can_update(self, metadata_record):
        return self.can_extract(metadata_record)

    def can_extract(self, metadata_record):
        return is_iso19115_3_root(metadata_record)

    def get_dataset_template(self):
        return get_template('dataset')

    def create(self, mdtype, mdfields):
        if mdtype == 'dataset':
            return create_dataset_metadata(mdfields, template_path=self.get_dataset_template())
        return None


class Iso19115_3Updater(XmlStandardUpdater):
    def __init__(self, metadata_record):
        super().__init__(metadata_record)
        self.ns = ns_for(self.tree)

    def update_dateStamp(self):
        str_timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')
        date_infos = self.tree.findall('./mdb:dateInfo/cit:CI_Date', self.ns)
        updated = False
        for date_info in date_infos:
            type_node = date_info.find('./cit:dateType/cit:CI_DateTypeCode', self.ns)
            date_type = _code_value(type_node)
            if date_type and date_type not in ('revision', 'creation'):
                continue
            date_el = date_info.find('./cit:date', self.ns)
            if date_el is None:
                continue
            dt = date_el.find('./gco:DateTime', self.ns)
            d = date_el.find('./gco:Date', self.ns)
            if dt is not None:
                dt.text = str_timestamp
                updated = True
                break
            if d is not None:
                d.text = str_timestamp[:10]
                updated = True
                break
        if not updated:
            date_info_wrap = ET.Element(q('mdb', 'dateInfo'))
            ci_date = ET.SubElement(date_info_wrap, q('cit', 'CI_Date'))
            date_el = ET.SubElement(ci_date, q('cit', 'date'))
            dt = ET.SubElement(date_el, q('gco', 'DateTime'))
            dt.text = str_timestamp
            type_wrap = ET.SubElement(ci_date, q('cit', 'dateType'))
            type_code = ET.SubElement(type_wrap, q('cit', 'CI_DateTypeCode'))
            type_code.set('codeList', CL + '#CI_DateTypeCode')
            type_code.set('codeListValue', 'revision')
            insertAfter(self.tree, date_info_wrap, ['mdb:contact', 'mdb:dateInfo'], self.ns)
        return self

    def update_extent(self, extent_tuple):
        ident = _identification(self.tree)
        if ident is None:
            return self
        boxes = ident.findall('.//gex:EX_GeographicBoundingBox', self.ns)
        if boxes:
            for bbox in boxes:
                update_extent(bbox, extent_tuple)
        else:
            minx, miny, maxx, maxy = extent_tuple
            create_extent(self.tree, minx, miny, maxx, maxy)
        return self

    def update_thumbnail(self, thumbnail_url):
        ident = _identification(self.tree)
        if ident is None:
            return self
        overviews = ident.findall('./mri:graphicOverview', self.ns)
        to_remove = []
        updated = False
        for overview in overviews:
            file_name = overview.find('./mcc:MD_BrowseGraphic/mcc:fileName/gco:CharacterString', self.ns)
            file_text = (file_name.text or '').strip() if file_name is not None else ''
            if file_text == '' or file_text == 'n/a' or 'no_thumbnail' in file_text:
                to_remove.append(overview)
                continue
            ftype = overview.find('./mcc:MD_BrowseGraphic/mcc:fileType/gco:CharacterString', self.ns)
            desc = overview.find('./mcc:MD_BrowseGraphic/mcc:fileDescription/gco:CharacterString', self.ns)
            is_gvsigol = (
                (ftype is not None and ftype.text == GVSIGOL_THUMBNAIL)
                or (desc is not None and desc.text == GVSIGOL_THUMBNAIL)
            )
            if is_gvsigol and thumbnail_url:
                file_name.text = thumbnail_url
                updated = True
            elif is_gvsigol and not thumbnail_url:
                to_remove.append(overview)
        for el in to_remove:
            el.getparent().remove(el)
        if thumbnail_url and not updated:
            create_thumbnail(self.tree, thumbnail_url)
        return self

    def update_all(self, extent_tuple, thumbnail_url):
        self.update_extent(extent_tuple)
        self.update_thumbnail(thumbnail_url)
        self.update_dateStamp()
        return self


class Iso19115_3Reader(XmlStandardReader):
    def __init__(self, metadata_record):
        super().__init__(metadata_record)
        self.ns = ns_for(self.tree)

    def _ident(self):
        return _identification(self.tree, self.ns)

    def get_title(self):
        ident = self._ident()
        if ident is None:
            return ''
        return getTextFromXMLNode(ident, './mri:citation/cit:CI_Citation/cit:title', self.ns)

    def get_abstract(self):
        ident = self._ident()
        if ident is None:
            return ''
        return getTextFromXMLNode(ident, './mri:abstract', self.ns)

    def get_identifier(self):
        return getTextFromXMLNode(
            self.tree,
            './mdb:metadataIdentifier/mcc:MD_Identifier/mcc:code',
            self.ns,
        )

    def get_crs(self):
        return getTextFromXMLNode(
            self.tree,
            './mdb:referenceSystemInfo/mrs:MD_ReferenceSystem'
            '/mrs:referenceSystemIdentifier/mcc:MD_Identifier/mcc:code',
            self.ns,
        )

    def get_resource_identifier(self):
        ident = self._ident()
        if ident is None:
            return ''
        return getTextFromXMLNode(
            ident,
            './mri:citation/cit:CI_Citation/cit:identifier/*/mcc:code',
            self.ns,
        )

    def get_graphic_overviews(self):
        ident = self._ident()
        if ident is None:
            return []
        result = []
        for browse in ident.findall('./mri:graphicOverview/mcc:MD_BrowseGraphic', self.ns):
            url = getTextFromXMLNode(browse, './mcc:fileName', self.ns)
            if not url:
                continue
            name = getTextFromXMLNode(browse, './mcc:fileDescription', self.ns)
            result.append({'url': sanitizeXmlText(url), 'name': sanitizeXmlText(name)})
        return result

    def get_transfer_options(self):
        result = []
        OnlineResource = collections.namedtuple(
            'OnlineResource',
            ['url', 'protocol', 'app_profile', 'name', 'desc', 'function', 'transfer_size'],
        )
        for transfer in self.tree.findall(
            './mdb:distributionInfo/mrd:MD_Distribution/mrd:transferOptions/mrd:MD_DigitalTransferOptions',
            self.ns,
        ):
            size_node = transfer.find('./mrd:transferSize/gco:Real', self.ns)
            transfer_size = None
            if size_node is not None and size_node.text:
                try:
                    transfer_size = float(size_node.text)
                except (TypeError, ValueError):
                    pass
            for online in transfer.findall('./mrd:onLine/cit:CI_OnlineResource', self.ns):
                parsed = self._parse_online_resource(online)
                result.append(OnlineResource(
                    parsed['url'], parsed['protocol'], parsed['applicationProfile'],
                    parsed['name'], parsed['description'], parsed['function'], transfer_size,
                ))
        return result

    def _parse_online_resource(self, node):
        url = getTextFromXMLNode(node, './cit:linkage', self.ns)
        protocol = getTextFromXMLNode(node, './cit:protocol', self.ns)
        name = getTextFromXMLNode(node, './cit:name', self.ns)
        description = getTextFromXMLNode(node, './cit:description', self.ns)
        application_profile = getTextFromXMLNode(node, './cit:applicationProfile', self.ns)
        function_node = node.find('./cit:function/cit:CI_OnLineFunctionCode', self.ns)
        if function_node is not None:
            function = _code_value(function_node)
        else:
            function = getTextFromXMLNode(node, './cit:function', self.ns)
        return {
            'name': sanitizeXmlText(name),
            'description': sanitizeXmlText(description),
            'applicationProfile': sanitizeXmlText(application_profile),
            'function': sanitizeXmlText(function),
            'protocol': sanitizeXmlText(protocol),
            'url': sanitizeXmlText(url),
        }

    def _parse_constraints(self, xpath_filter):
        result = empty_constraints()
        for wrapper in self.tree.findall(xpath_filter, self.ns):
            for node in wrapper:
                local = ET.QName(node).localname
                ns_ok = ET.QName(node).namespace == self.ns['mco']
                if not ns_ok and local not in ('MD_Constraints', 'MD_LegalConstraints'):
                    continue
                for use_lim in node.findall('./mco:useLimitation', self.ns):
                    value = ''.join(use_lim.itertext()).strip()
                    if value:
                        result['useLimitations'].append(sanitizeXmlText(value))
                for acc in node.findall('./mco:accessConstraints/mco:MD_RestrictionCode', self.ns):
                    result['accessConstraints'].append(_code_value(acc))
                for use_c in node.findall('./mco:useConstraints/mco:MD_RestrictionCode', self.ns):
                    result['useConstraints'].append(_code_value(use_c))
                for other in node.findall('./mco:otherConstraints', self.ns):
                    value = ''.join(other.itertext()).strip()
                    if value:
                        result['otherConstraints'].append(sanitizeXmlText(value))
        return result

    def _parse_responsibility(self, node):
        role_node = node.find('./cit:role/cit:CI_RoleCode', self.ns)
        role = _code_value(role_node)
        organisation = ''
        individual = ''
        email = ''
        phone = ''
        url = ''
        online_resource = None
        for party in node.findall('./cit:party/*', self.ns):
            local = ET.QName(party).localname
            if local == 'CI_Organisation' and not organisation:
                organisation = getTextFromXMLNode(party, './cit:name', self.ns)
            elif local == 'CI_Individual' and not individual:
                individual = getTextFromXMLNode(party, './cit:name', self.ns)
            if not email:
                email = getTextFromXMLNode(
                    party,
                    './cit:contactInfo/cit:CI_Contact/cit:address/cit:CI_Address/cit:electronicMailAddress',
                    self.ns,
                )
            if not phone:
                phone = getTextFromXMLNode(
                    party,
                    './cit:contactInfo/cit:CI_Contact/cit:phone/cit:CI_Telephone/cit:number',
                    self.ns,
                )
            if not url:
                url = getTextFromXMLNode(
                    party,
                    './cit:contactInfo/cit:CI_Contact/cit:onlineResource/cit:CI_OnlineResource/cit:linkage',
                    self.ns,
                )
            for online_node in party.findall(
                './cit:contactInfo/cit:CI_Contact/cit:onlineResource/cit:CI_OnlineResource',
                self.ns,
            ):
                online_resource = self._parse_online_resource(online_node)
                if online_resource.get('url'):
                    break
        return {
            'individualName': individual,
            'organisationName': organisation,
            'role': role,
            'email': email,
            'phone': phone,
            'url': url,
            'organisation': sanitizeXmlText(organisation or individual),
            'onlineResource': online_resource,
        }

    def _contacts_from_xpath(self, xpath):
        contacts = []
        for wrapper in self.tree.findall(xpath, self.ns):
            party = wrapper
            if not ET.QName(wrapper).localname == 'CI_Responsibility':
                party = wrapper.find('./cit:CI_Responsibility', self.ns)
            if party is None:
                continue
            parsed = self._parse_responsibility(party)
            if not parsed.get('organisation'):
                continue
            contacts.append({
                'organisation': parsed['organisation'],
                'role': sanitizeXmlText(parsed.get('role', '')),
                'email': sanitizeXmlText(parsed.get('email', '')),
                'phone': sanitizeXmlText(parsed.get('phone', '')),
                'url': sanitizeXmlText(parsed.get('url', '')),
                'onlineResource': parsed.get('onlineResource'),
            })
        return contacts

    def _keyword_groups(self, ident):
        groups = []
        if ident is None:
            return groups
        for block in ident.findall('./mri:descriptiveKeywords/mri:MD_Keywords', self.ns):
            keywords = []
            for keyword in block.findall('./mri:keyword', self.ns):
                value = ''.join(keyword.itertext()).strip()
                if value:
                    keywords.append(sanitizeXmlText(value))
            if not keywords:
                continue
            type_node = block.find('./mri:type/mri:MD_KeywordTypeCode', self.ns)
            thesaurus = getTextFromXMLNode(
                block,
                './mri:thesaurusName/cit:CI_Citation/cit:title',
                self.ns,
            )
            groups.append({
                'type': _code_value(type_node),
                'keywords': keywords,
                'thesaurus': sanitizeXmlText(thesaurus),
            })
        return groups

    def _languages(self, ident):
        languages = []
        for path in (
            './mdb:defaultLocale/lan:PT_Locale/lan:language/lan:LanguageCode',
            './mdb:defaultLocale/lan:PT_Locale/lan:language',
        ):
            for node in self.tree.findall(path, self.ns):
                value = _code_value(node) or ''.join(node.itertext()).strip()
                if value and value not in languages:
                    languages.append(sanitizeXmlText(value))
        if ident is not None:
            for node in ident.findall('./mri:defaultLocale/lan:PT_Locale/lan:language/lan:LanguageCode', self.ns):
                value = _code_value(node)
                if value and value not in languages:
                    languages.append(sanitizeXmlText(value))
        return languages

    def _character_set(self, ident):
        for path in (
            './mdb:defaultLocale/lan:PT_Locale/lan:characterEncoding/lan:MD_CharacterSetCode',
        ):
            node = self.tree.find(path, self.ns)
            value = _code_value(node)
            if value:
                return value
        if ident is not None:
            node = ident.find('./mri:defaultLocale/lan:PT_Locale/lan:characterEncoding/lan:MD_CharacterSetCode', self.ns)
            value = _code_value(node)
            if value:
                return value
        return ''

    def _geographic_place(self, ident):
        places = []
        if ident is None:
            return places
        desc = getTextFromXMLNode(ident, './mri:extent/gex:EX_Extent/gex:description', self.ns)
        if desc:
            places.append(sanitizeXmlText(desc))
        for geo_desc in ident.findall(
            './mri:extent/gex:EX_Extent/gex:geographicElement/gex:EX_GeographicDescription',
            self.ns,
        ):
            code = getTextFromXMLNode(geo_desc, './gex:geographicIdentifier/*/mcc:code', self.ns)
            if code and sanitizeXmlText(code) not in places:
                places.append(sanitizeXmlText(code))
        for group in self._keyword_groups(ident):
            if group.get('type') != 'place':
                continue
            for keyword in group.get('keywords', []):
                if keyword not in places:
                    places.append(keyword)
        return places

    def _bbox(self, ident):
        if ident is None:
            return '', '', '', ''
        bbox = ident.find('.//gex:EX_GeographicBoundingBox', self.ns)
        if bbox is None:
            return '', '', '', ''
        west = getTextFromXMLNode(bbox, './gex:westBoundLongitude', self.ns)
        east = getTextFromXMLNode(bbox, './gex:eastBoundLongitude', self.ns)
        south = getTextFromXMLNode(bbox, './gex:southBoundLatitude', self.ns)
        north = getTextFromXMLNode(bbox, './gex:northBoundLatitude', self.ns)
        return west, east, south, north

    def _temporal_extent(self, ident):
        start = ''
        end = ''
        if ident is None:
            return start, end
        period = ident.find(
            './mri:extent/gex:EX_Extent/gex:temporalElement/gex:EX_TemporalExtent/gex:extent/*',
            self.ns,
        )
        if period is not None:
            begin = period.find('./gml:beginPosition', self.ns)
            finish = period.find('./gml:endPosition', self.ns)
            if begin is None:
                begin = period.find('./{http://www.opengis.net/gml}beginPosition')
            if finish is None:
                finish = period.find('./{http://www.opengis.net/gml}endPosition')
            if begin is not None and begin.text:
                start = begin.text
            if finish is not None and finish.text:
                end = finish.text
        return start, end

    def _citation_dates(self, ident):
        publish = ''
        if ident is None:
            return publish
        for date_elem in ident.findall('./mri:citation/cit:CI_Citation/cit:date/cit:CI_Date', self.ns):
            date_type = _code_value(date_elem.find('./cit:dateType/cit:CI_DateTypeCode', self.ns))
            value = getTextFromXMLNode(date_elem, './cit:date', self.ns)
            if date_type == 'publication' and value:
                return sanitizeXmlText(value)
            if not publish and value:
                publish = sanitizeXmlText(value)
        return publish

    def _metadata_date(self):
        for date_elem in self.tree.findall('./mdb:dateInfo/cit:CI_Date', self.ns):
            date_type = _code_value(date_elem.find('./cit:dateType/cit:CI_DateTypeCode', self.ns))
            value = getTextFromXMLNode(date_elem, './cit:date', self.ns)
            if date_type in ('revision', 'creation') and value:
                return sanitizeXmlText(value)
        return sanitizeXmlText(getTextFromXMLNode(self.tree, './mdb:dateInfo/cit:CI_Date/cit:date', self.ns))

    def _distribution_formats(self):
        formats = []
        for fmt in self.tree.findall(
            './mdb:distributionInfo/mrd:MD_Distribution/mrd:distributionFormat/mrd:MD_Format',
            self.ns,
        ):
            name = getTextFromXMLNode(fmt, './mrd:formatSpecificationCitation/cit:CI_Citation/cit:title', self.ns)
            version = getTextFromXMLNode(fmt, './mrd:formatSpecificationCitation/cit:CI_Citation/cit:edition', self.ns)
            if not name:
                continue
            label = sanitizeXmlText(name)
            if version:
                label += ' (' + sanitizeXmlText(version) + ')'
            if label not in formats:
                formats.append(label)
        return formats

    def as_catalog_record(self):
        ident = self._ident()
        record = empty_catalog_record()
        west, east, south, north = self._bbox(ident)
        period_start, period_end = self._temporal_extent(ident)
        keyword_groups = self._keyword_groups(ident)
        keywords = []
        for group in keyword_groups:
            keywords.extend(group.get('keywords', []))

        categories = []
        if ident is not None:
            for category in ident.findall('./mri:topicCategory/mri:MD_TopicCategoryCode', self.ns):
                value = (category.text or '').strip()
                if value:
                    categories.append(sanitizeXmlText(value))

        representation_type = ''
        if ident is not None:
            rep = ident.find('./mri:spatialRepresentationType/mcc:MD_SpatialRepresentationTypeCode', self.ns)
            representation_type = _code_value(rep)

        scale = ''
        if ident is not None:
            scale = getTextFromXMLNode(
                ident,
                './mri:spatialResolution/mri:MD_Resolution/mri:equivalentScale/mri:MD_RepresentativeFraction/mri:denominator',
                self.ns,
            )

        status = ''
        if ident is not None:
            status = _code_value(ident.find('./mri:status/mcc:MD_ProgressCode', self.ns))

        purpose = ''
        if ident is not None:
            purpose = sanitizeXmlText(getTextFromXMLNode(ident, './mri:purpose', self.ns))

        update_frequency = ''
        if ident is not None:
            freq = ident.find(
                './mri:resourceMaintenance/mmi:MD_MaintenanceInformation/mmi:maintenanceAndUpdateFrequency/mmi:MD_MaintenanceFrequencyCode',
                self.ns,
            )
            update_frequency = _code_value(freq)
        if not update_frequency:
            freq = self.tree.find(
                './mdb:metadataMaintenance/mmi:MD_MaintenanceInformation/mmi:maintenanceAndUpdateFrequency/mmi:MD_MaintenanceFrequencyCode',
                self.ns,
            )
            update_frequency = _code_value(freq)

        update_scope = ''
        if ident is not None:
            scope = ident.find(
                './mri:resourceMaintenance/mmi:MD_MaintenanceInformation/mmi:maintenanceScope/*/mcc:level/mcc:MD_ScopeCode',
                self.ns,
            )
            update_scope = _code_value(scope)

        hierarchy = _code_value(
            self.tree.find('./mdb:metadataScope/mdb:MD_MetadataScope/mdb:resourceScope/mcc:MD_ScopeCode', self.ns)
        )
        # Default-namespace variant used by MGB templates (<MD_MetadataScope> without prefix)
        if not hierarchy:
            for scope in self.tree.findall('./mdb:metadataScope/*', self.ns):
                if ET.QName(scope).localname == 'MD_MetadataScope':
                    hierarchy = _code_value(scope.find('./mdb:resourceScope/mcc:MD_ScopeCode', self.ns))
                    if not hierarchy:
                        hierarchy = _code_value(scope.find('./{*}resourceScope/{*}MD_ScopeCode'))
                    break

        resources = []
        for online in self.tree.findall(
            './mdb:distributionInfo/mrd:MD_Distribution/mrd:transferOptions'
            '/mrd:MD_DigitalTransferOptions/mrd:onLine/cit:CI_OnlineResource',
            self.ns,
        ):
            resources.append(self._parse_online_resource(online))

        record.update({
            'metadata_id': sanitizeXmlText(self.get_identifier()),
            'title': sanitizeXmlText(self.get_title()),
            'abstract': sanitizeXmlText(self.get_abstract()),
            'publish_date': self._citation_dates(ident),
            'update_frequency': sanitizeXmlText(update_frequency),
            'resource_identifier': sanitizeXmlText(self.get_resource_identifier()),
            'languages': self._languages(ident),
            'geographic_place': self._geographic_place(ident),
            'resource_status': sanitizeXmlText(status),
            'hierarchy_level': sanitizeXmlText(hierarchy),
            'character_set': sanitizeXmlText(self._character_set(ident)),
            'distribution_formats': self._distribution_formats(),
            'purpose': purpose,
            'metadata_standard_name': sanitizeXmlText(
                getTextFromXMLNode(self.tree, './mdb:metadataStandard/cit:CI_Citation/cit:title', self.ns)
            ),
            'metadata_standard_version': sanitizeXmlText(
                getTextFromXMLNode(self.tree, './mdb:metadataStandard/cit:CI_Citation/cit:edition', self.ns)
            ),
            'metadata_profile': sanitizeXmlText(
                getTextFromXMLNode(self.tree, './mdb:metadataProfile/cit:CI_Citation/cit:title', self.ns)
            ),
            'date_stamp': self._metadata_date(),
            'metadata_update_frequency': sanitizeXmlText(_code_value(
                self.tree.find(
                    './mdb:metadataMaintenance/mmi:MD_MaintenanceInformation'
                    '/mmi:maintenanceAndUpdateFrequency/mmi:MD_MaintenanceFrequencyCode',
                    self.ns,
                )
            )),
            'update_scope': sanitizeXmlText(update_scope),
            'keyword_groups': keyword_groups,
            'period_start': sanitizeXmlText(period_start),
            'period_end': sanitizeXmlText(period_end),
            'categories': categories,
            'keywords': keywords,
            'representation_type': sanitizeXmlText(representation_type),
            'scale': sanitizeXmlText(scale),
            'srs': sanitizeXmlText(self.get_crs()),
            'extent_west': west,
            'extent_east': east,
            'extent_south': south,
            'extent_north': north,
            'thumbnails': self.get_graphic_overviews(),
            'resources': resources,
            'resource_constraints': self._parse_constraints(
                './mdb:identificationInfo/*/mri:resourceConstraints'
            ),
            'metadata_constraints': self._parse_constraints('./mdb:metadataConstraints'),
            'contacts': {
                'resource_contacts': self._contacts_from_xpath(
                    './mdb:identificationInfo/*/mri:pointOfContact'
                ),
                'metadata_contacts': self._contacts_from_xpath('./mdb:contact'),
                'responsible_parties': self._contacts_from_xpath(
                    './mdb:identificationInfo/*/mri:citation/cit:CI_Citation/cit:citedResponsibleParty'
                ),
                'distributor_contacts': self._contacts_from_xpath(
                    './mdb:distributionInfo/mrd:MD_Distribution/mrd:distributor'
                    '/mrd:MD_Distributor/mrd:distributorContact'
                ),
            },
        })
        return record
