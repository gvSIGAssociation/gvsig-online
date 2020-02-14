# -*- coding: utf-8 -*-
from lxml import etree as ET
from builtins import str as text
from registry import XmlStandardUpdater, BaseStandardManager, XmlStandardReader
from datetime import datetime
from django.utils.translation import ugettext as _
from gvsigol_plugin_catalog.xmlutils import getTextFromXMLNode, sanitizeXmlText
import collections

def define_translations():
    """
    Force some strings to be detected by gettext/makemessages
    """
    _('author')
    _('owner')
    _('Contact')

namespaces = {'gmd': 'http://www.isotc211.org/2005/gmd', 'gco': 'http://www.isotc211.org/2005/gco'}

def create_datset_metadata(mdfields):
    qualified_name = mdfields.get('qualified_name')
    title = mdfields.get('title')
    abstract = mdfields.get('abstract')
    extent_tuple = mdfields.get('extent_tuple', (0.0, 0.0, 0.0, 0.0))
    crs = mdfields.get('crs')
    thumbnail_url = mdfields.get('thumbnail_url')
    wms_endpoint = mdfields.get('wms_endpoint')
    wfs_endpoint = mdfields.get('wfs_endpoint')
    wcs_endpoint = mdfields.get('wcs_endpoint')
    
    minx, miny, maxx, maxy = extent_tuple
    metadata =  u'<gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd" '
    metadata +=     u'xmlns:srv="http://www.isotc211.org/2005/srv" xmlns:gmx="http://www.isotc211.org/2005/gmx" '
    metadata +=   u'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:gco="http://www.isotc211.org/2005/gco" '
    metadata +=   u'xmlns:gml="http://www.opengis.net/gml" xmlns:gts="http://www.isotc211.org/2005/gts" '
    metadata +=   u'xmlns:geonet="http://www.fao.org/geonetwork" xsi:schemaLocation="http://www.isotc211.org/2005/gmd ../schema.xsd">'
    
    metadata +=   u'<gmd:metadataStandardName>'
    metadata +=       u'<gco:CharacterString>ISO 19115:2003/19139</gco:CharacterString>'
    metadata +=   u'</gmd:metadataStandardName>'
    
    metadata +=   u'<gmd:metadataStandardVersion>'
    metadata +=       u'<gco:CharacterString>1.0</gco:CharacterString>'
    metadata +=   u'</gmd:metadataStandardVersion>'
    
    metadata +=   u'<gmd:spatialRepresentationInfo/>'
    
    metadata +=   u'<gmd:referenceSystemInfo>'
    metadata +=       u'<gmd:MD_ReferenceSystem>'
    metadata +=           u'<gmd:referenceSystemIdentifier>'
    metadata +=               u'<gmd:RS_Identifier>'
    metadata +=                   u'<gmd:code>'
    metadata +=                       u'<gco:CharacterString>' + sanitizeXmlText(crs) + u'</gco:CharacterString>'
    metadata +=                   u'</gmd:code>'
    metadata +=               u'</gmd:RS_Identifier>'
    metadata +=           u'</gmd:referenceSystemIdentifier>'
    metadata +=       u'</gmd:MD_ReferenceSystem>'
    metadata +=   u'</gmd:referenceSystemInfo>'
    
    metadata +=   u'<gmd:identificationInfo>'
    metadata +=       u'<gmd:MD_DataIdentification>'
    metadata +=           u'<gmd:citation>'
    metadata +=               u'<gmd:CI_Citation>'
    metadata +=                   u'<gmd:title xsi:type="gmd:PT_FreeText_PropertyType">'
    metadata +=                       u'<gco:CharacterString>' + sanitizeXmlText(title) + u'</gco:CharacterString>'
    metadata +=                       u'<gmd:PT_FreeText>'
    metadata +=                           u'<gmd:textGroup>'
    metadata +=                               u'<gmd:LocalisedCharacterString locale="#ES">' + sanitizeXmlText(title) + u'</gmd:LocalisedCharacterString>'
    metadata +=                           u'</gmd:textGroup>'
    metadata +=                       u'</gmd:PT_FreeText>'
    metadata +=                   u'</gmd:title>'
    metadata +=                   u'<gmd:date>'
    metadata +=                       u'<gmd:CI_Date>'
    metadata +=                           u'<gmd:date>'
    metadata +=                               u'<gco:DateTime>' + sanitizeXmlText(text(datetime.now())) + u'</gco:DateTime>'
    metadata +=                           u'</gmd:date> '
    metadata +=                           u'<gmd:dateType>'
    metadata +=                               u'<gmd:CI_DateTypeCode codeList="./resources/codeList.xml#CI_DateTypeCode" codeListValue="creation"/>'
    metadata +=                           u'</gmd:dateType>'
    metadata +=                       u'</gmd:CI_Date>'
    metadata +=                   u'</gmd:date>'
    metadata +=               u'</gmd:CI_Citation>'
    metadata +=           u'</gmd:citation>'
    metadata +=           u'<gmd:abstract>'
    metadata +=               u'<gco:CharacterString>' + sanitizeXmlText(abstract) + u'</gco:CharacterString>'
    metadata +=           u'</gmd:abstract>'
    metadata +=           u'<gmd:graphicOverview><gmd:MD_BrowseGraphic>'
    metadata +=               u'<gmd:fileName>'
    metadata +=                   u'<gco:CharacterString>' + sanitizeXmlText(thumbnail_url) + u'</gco:CharacterString>'
    metadata +=               u'</gmd:fileName>'
    metadata +=               u'<gmd:fileDescription>'
    metadata +=                   u'<gco:CharacterString>gvsigol thumbnail</gco:CharacterString>'
    metadata +=               u'</gmd:fileDescription>'
    metadata +=           u'</gmd:MD_BrowseGraphic></gmd:graphicOverview>'
    metadata +=           u'<gmd:extent>'
    metadata +=               u'<gmd:EX_Extent>'
    metadata +=                   u'<gmd:geographicElement>'
    metadata +=                       u'<gmd:EX_GeographicBoundingBox>'
    metadata +=                           u'<gmd:westBoundLongitude>'
    metadata +=                               u'<gco:Decimal>' + sanitizeXmlText(minx) + u'</gco:Decimal>'
    metadata +=                           u'</gmd:westBoundLongitude>'
    metadata +=                           u'<gmd:eastBoundLongitude>'
    metadata +=                               u'<gco:Decimal>' + sanitizeXmlText(maxx) + u'</gco:Decimal>'
    metadata +=                           u'</gmd:eastBoundLongitude>'
    metadata +=                           u'<gmd:southBoundLatitude>'
    metadata +=                               u'<gco:Decimal>' + sanitizeXmlText(miny) + u'</gco:Decimal>'
    metadata +=                           u'</gmd:southBoundLatitude>'
    metadata +=                           u'<gmd:northBoundLatitude>'
    metadata +=                               u'<gco:Decimal>' + sanitizeXmlText(maxy) + u'</gco:Decimal>'
    metadata +=                           u'</gmd:northBoundLatitude>'
    metadata +=                       u'</gmd:EX_GeographicBoundingBox>'
    metadata +=                   u'</gmd:geographicElement>'
    metadata +=               u'</gmd:EX_Extent>'
    metadata +=           u'</gmd:extent>'
    metadata +=       u'</gmd:MD_DataIdentification>'
    metadata +=   u'</gmd:identificationInfo>'
    
    metadata +=   u'<gmd:distributionInfo>'
    metadata +=       u'<gmd:MD_Distribution>'
    metadata +=           u'<gmd:distributionFormat>'
    metadata +=               u'<gmd:MD_Format>'
    metadata +=                   u'<gmd:name>'
    metadata +=                       u'<gco:CharacterString>ShapeFile</gco:CharacterString>'
    metadata +=                   u'</gmd:name>'
    metadata +=                   u'<gmd:version>'
    metadata +=                       u'<gco:CharacterString>Grass Version 6.1</gco:CharacterString>'
    metadata +=                   u'</gmd:version>'
    metadata +=               u'</gmd:MD_Format>'
    metadata +=           u'</gmd:distributionFormat>'
    metadata +=           u'<gmd:transferOptions>'
    metadata +=               u'<gmd:MD_DigitalTransferOptions>'
    metadata +=                   u'<gmd:onLine>'
    metadata +=                       u'<gmd:CI_OnlineResource>'
    metadata +=                           u'<gmd:linkage>'
    metadata +=                               u'<gmd:URL>' + sanitizeXmlText(wms_endpoint) + u'</gmd:URL>'
    metadata +=                           u'</gmd:linkage>'
    metadata +=                           u'<gmd:protocol>'
    metadata +=                               u'<gco:CharacterString>OGC:WMS</gco:CharacterString>'
    metadata +=                           u'</gmd:protocol>'
    metadata +=                           u'<gmd:name>'
    metadata +=                               u'<gco:CharacterString>' + sanitizeXmlText(qualified_name) + u'</gco:CharacterString>'
    metadata +=                           u'</gmd:name>'
    metadata +=                           u'<gmd:description>'
    metadata +=                               u'<gco:CharacterString>' + sanitizeXmlText(title) + u'</gco:CharacterString>'
    metadata +=                           u'</gmd:description>'
    metadata +=                       u'</gmd:CI_OnlineResource>'
    metadata +=                   u'</gmd:onLine>'
    if wfs_endpoint:
        metadata +=           u'<gmd:onLine>'
        metadata +=               u'<gmd:CI_OnlineResource>'
        metadata +=                   u'<gmd:linkage>'
        metadata +=                       u'<gmd:URL>' + sanitizeXmlText(wfs_endpoint) + u'</gmd:URL>'
        metadata +=                   u'</gmd:linkage>'
        metadata +=                   u'<gmd:protocol>'
        metadata +=                       u'<gco:CharacterString>OGC:WFS</gco:CharacterString>'
        metadata +=                   u'</gmd:protocol>'
        metadata +=                   u'<gmd:name>'
        metadata +=                       u'<gco:CharacterString>' + sanitizeXmlText(qualified_name) + u'</gco:CharacterString>'
        metadata +=                   u'</gmd:name>'
        metadata +=                   u'<gmd:description>'
        metadata +=                       u'<gco:CharacterString>' + sanitizeXmlText(title) + u'</gco:CharacterString>'
        metadata +=                   u'</gmd:description>'
        metadata +=                   u'<gmd:function><gmd:CI_OnLineFunctionCode codeList="http://standards.iso.org/ittf/PubliclyAvailableStandards/ISO_19139_Schemas/resources/codelist/ML_gmxCodelists.xml#CI_OnLineFunctionCode" codeListValue="download"/></gmd:function>'
        metadata +=               u'</gmd:CI_OnlineResource>'
        metadata +=           u'</gmd:onLine>'
    if wcs_endpoint:
        metadata +=           u'<gmd:onLine>'
        metadata +=               u'<gmd:CI_OnlineResource>'
        metadata +=                   u'<gmd:linkage>'
        metadata +=                       u'<gmd:URL>' + sanitizeXmlText(wcs_endpoint) + u'</gmd:URL>'
        metadata +=                   u'</gmd:linkage>'
        metadata +=                   u'<gmd:protocol>'
        metadata +=                       u'<gco:CharacterString>OGC:WCS</gco:CharacterString>'
        metadata +=                   u'</gmd:protocol>'
        metadata +=                   u'<gmd:name>'
        metadata +=                       u'<gco:CharacterString>' + sanitizeXmlText(qualified_name) + u'</gco:CharacterString>'
        metadata +=                   u'</gmd:name>'
        metadata +=                   u'<gmd:description>'
        metadata +=                       u'<gco:CharacterString>' + sanitizeXmlText(title) + u'</gco:CharacterString>'
        metadata +=                   u'</gmd:description>'
        metadata +=                   u'<gmd:function><gmd:CI_OnLineFunctionCode codeList="http://standards.iso.org/ittf/PubliclyAvailableStandards/ISO_19139_Schemas/resources/codelist/ML_gmxCodelists.xml#CI_OnLineFunctionCode" codeListValue="download"/></gmd:function>'
        metadata +=               u'</gmd:CI_OnlineResource>'
        metadata +=           u'</gmd:onLine>'
    metadata +=               u'</gmd:MD_DigitalTransferOptions>'
    metadata +=           u'</gmd:transferOptions>'
    metadata +=       u'</gmd:MD_Distribution>'
    metadata +=   u'</gmd:distributionInfo>'
    metadata += u'</gmd:MD_Metadata>'

    return metadata

class Iso19139_2007Manager(BaseStandardManager):
    def get_code(self):
        return 'Iso19139_2007Manager'

    def get_updater_instance(self, metadata_record):
        return Iso19139_2007Updater(metadata_record)
    
    def get_reader_instance(self, metadata_record):
        return Iso19139_2007Reader(metadata_record)
    
    def can_update(self, metadata_record):
        return self.can_extract(metadata_record)

    def create(self, mdtype, mdfields):
        if mdtype == 'dataset':
            return create_datset_metadata(mdfields)
        elif mdtype == 'service':
            pass # TODO
    
    def can_extract(self, metadata_record):
        root_qname = ET.QName(metadata_record)
        if root_qname.localname == 'MD_Metadata' and root_qname.namespace == namespaces['gmd']:
            return True
        return False

def update_extent(geo_bb_elem, extent_tuple):
    minx, miny, maxx, maxy = extent_tuple
    for bound in geo_bb_elem:
        if bound.tag == '{http://www.isotc211.org/2005/gmd}westBoundLongitude':
            bound[0].text = minx
        elif bound.tag == '{http://www.isotc211.org/2005/gmd}eastBoundLongitude':
            bound[0].text = maxx
        elif bound.tag == '{http://www.isotc211.org/2005/gmd}southBoundLatitude':
            bound[0].text = miny
        elif bound.tag == '{http://www.isotc211.org/2005/gmd}northBoundLatitude':
            bound[0].text = maxy

def update_thumbnail(browse_graphic_elem, thumbnail_url):
    desc = browse_graphic_elem.findall('./gmd:fileDescription/gco:CharacterString', namespaces)
    if len(desc) > 0 and desc[0].text == u'gvsigol thumbnail':
        file_names = browse_graphic_elem.findall('./gmd:fileName/gco:CharacterString', namespaces)
        if len(file_names) > 0:
            file_names[0].text = thumbnail_url

def create_thumbnail(root_elem, thumbnail_url):
    data_ident_elements = root_elem.findall('./gmd:identificationInfo/gmd:MD_DataIdentification', namespaces)
    if len(data_ident_elements) > 0:
        grov = ET.SubElement(data_ident_elements[0], "{http://www.isotc211.org/2005/gmd}graphicOverview")
        brgr = ET.SubElement(grov, "{http://www.isotc211.org/2005/gmd}MD_BrowseGraphic")
        file_name = ET.SubElement(brgr, "{http://www.isotc211.org/2005/gmd}fileName")
        file_name_str = ET.SubElement(file_name, "{http://www.isotc211.org/2005/gco}CharacterString")
        file_name_str.text = thumbnail_url
        file_desc = ET.SubElement(brgr, "{http://www.isotc211.org/2005/gmd}fileDescription")
        file_desc_str = ET.SubElement(file_desc, "{http://www.isotc211.org/2005/gco}CharacterString")
        file_desc_str.text = u'gvsigol thumbnail'

def update_metadata(xml_str, extent_tuple, thumbnail_url):
    tree = ET.fromstring(xml_str)
    for geog_bounding_box_element in tree.findall('./gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox', namespaces):
        update_extent(geog_bounding_box_element, extent_tuple)
    thumbnails = tree.findall('./gmd:identificationInfo/gmd:MD_DataIdentification/gmd:graphicOverview/gmd:MD_BrowseGraphic', namespaces)
    if len(thumbnails) > 0:
        for thumbnail_element in thumbnails:
            update_thumbnail(thumbnail_element, thumbnail_url)
    else:
        create_thumbnail(tree, thumbnail_url)
    return ET.tostring(tree, encoding='unicode')

class Iso19139_2007Updater(XmlStandardUpdater):
    def update_extent(self, extent_tuple):
        for geog_bounding_box_element in self.tree.findall('./gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox', namespaces):
            update_extent(geog_bounding_box_element, extent_tuple)
        return self
        
    def update_thumbnail(self, thumbnail_url):
        thumbnails = self.tree.findall('./gmd:identificationInfo/gmd:MD_DataIdentification/gmd:graphicOverview/gmd:MD_BrowseGraphic', namespaces)
        if len(thumbnails) > 0:
            for thumbnail_element in thumbnails:
                update_thumbnail(thumbnail_element, thumbnail_url)
        else:
            create_thumbnail(self.tree, thumbnail_url)
        return self
        
    def update_all(self, extent_tuple, thumbnail_url):
        self.update_extent(extent_tuple)
        self.update_thumbnail(thumbnail_url)
        return self

class Iso19139_2007Reader(XmlStandardReader):
    def get_title(self):
        return getTextFromXMLNode(self.tree, './gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:title/', namespaces)
    def get_abstract(self):
        return getTextFromXMLNode(self.tree, './gmd:identificationInfo/gmd:MD_DataIdentification/gmd:abstract/', namespaces)
    def get_identifier(self):
        return getTextFromXMLNode(self.tree, './gmd:fileIdentifier/', namespaces)
    def get_crs(self):
        return getTextFromXMLNode(self.tree, './gmd:referenceSystemInfo/gmd:MD_ReferenceSystem/gmd:referenceSystemIdentifier/gmd:RS_Identifier/gmd:code/', namespaces)
    def get_transfer_options(self):
        result = []
        OnlineResource = collections.namedtuple('OnlineResource', ['url', 'protocol', 'app_profile', 'name', 'desc', 'function', 'transfer_size'])
        for transferOption in self.tree.findall('./gmd:distributionInfo/gmd:MD_Distribution/gmd:transferOptions/gmd:MD_DigitalTransferOptions', namespaces):
            transferSizeNode = transferOption.find('./gmd:transferSize/gco:Real', namespaces)
            transferSize = None
            if transferSizeNode is not None and transferSizeNode.text != '':
                try:
                    transferSize = float(transferSizeNode.text)
                except:
                    pass
            for online in transferOption.findall('./gmd:onLine/gmd:CI_OnlineResource', namespaces):
                protocol = getTextFromXMLNode(online, './gmd:protocol/', namespaces)
                name = getTextFromXMLNode(online, './gmd:name/', namespaces)
                url = getTextFromXMLNode(online, './gmd:linkage/', namespaces)
                desc = getTextFromXMLNode(online, './gmd:description/', namespaces)
                app_profile = getTextFromXMLNode(online, './gmd:applicationProfile/', namespaces)
                functionNode = online.find('./gmd:function/gmd:CI_OnLineFunctionCode', namespaces)
                if functionNode is not None:
                    function = functionNode.get('codeListValue', '')
                else:
                    function = ''
                onlineObj = OnlineResource(url, protocol, app_profile, name, desc, function, transferSize)
                result.append(onlineObj)
        return result
    
    
    
    