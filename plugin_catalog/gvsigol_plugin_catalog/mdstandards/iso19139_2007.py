# -*- coding: utf-8 -*-
from lxml import etree as ET
from builtins import str as text
from .registry import XmlStandardUpdater, BaseStandardManager, XmlStandardReader
from datetime import datetime
from django.utils.translation import ugettext as _
from gvsigol_plugin_catalog.xmlutils import getTextFromXMLNode, sanitizeXmlText, insertAfter, namespacedTag, setLocalisedCharacterString
from gvsigol.settings import BASE_DIR, LANGUAGE_CODE
import collections
from owslib import wcs
import os
from django.apps import apps
import logging
logger = logging.getLogger("gvsigol")


def define_translations():
    """
    Force some strings to be detected by gettext/makemessages
    """
    _('author')
    _('owner')
    _('Contact')
    _('resourceProvider')
    _('custodian')
    _('originator')
    _('publisher')

namespaces = {
    'gmd': 'http://www.isotc211.org/2005/gmd',
    'gco': 'http://www.isotc211.org/2005/gco',
    'gmx': 'http://www.isotc211.org/2005/gmx',
    'xlink': 'http://www.w3.org/1999/xlink'
}

def get_template(md_type):
    """
    Allows the default templates to be replaced by templates defined by the client gvsigol app
    
    md_type: Specifies the type of template to be retrieved (dataset, series, service, etc). Ignored for the moment
    """
    for app in apps.get_app_configs():
        if 'gvsigol_app_' in app.name:
            tpl_path = os.path.join(BASE_DIR, app.name, 'mdtemplates/dataset.xml')
            if os.path.exists(tpl_path):
                return tpl_path
    return os.path.join(BASE_DIR, 'gvsigol_plugin_catalog/mdtemplates/dataset19139.xml')

def getCrsCodeAnchor(crs):
    code = ET.Element(namespacedTag('gmd', 'code', namespaces))
    anchor = ET.Element(namespacedTag('gmx', 'Anchor', namespaces))
    if crs.startswith('EPSG:'):
        crs_uri = "http://www.opengis.net/def/crs/EPSG/0/" + crs[5:]
    else:
        crs_uri = crs
    anchor.attrib[namespacedTag('xlink', 'title', namespaces)] = crs_uri
    anchor.attrib[namespacedTag('xlink', 'href', namespaces)] = crs_uri
    anchor.text = crs
    code.append(anchor)
    return code
                 
def create_datset_metadata(mdfields):
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
        
        tpl_path = get_template('dataset')
        tree = ET.parse(tpl_path)
        
        spatialRepresentationTypeCode = tree.find('//gmd:MD_SpatialRepresentationTypeCode', namespaces)
        spatialRepresentationTypeCode.set('codeListValue', spatial_representation_type)
        
        titleElem = tree.find('/gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:title', namespaces)
        setLocalisedCharacterString(titleElem, title, LANGUAGE_CODE, namespaces)
        
        abstractElem = tree.find('/gmd:identificationInfo/gmd:MD_DataIdentification/gmd:abstract', namespaces)
        setLocalisedCharacterString(abstractElem, abstract, LANGUAGE_CODE, namespaces)
        
        crsElem = tree.find('/gmd:referenceSystemInfo/gmd:MD_ReferenceSystem/gmd:referenceSystemIdentifier/gmd:RS_Identifier/gmd:code/gco:CharacterString', namespaces)
        if crsElem is not None:
            crsElem.text = crs
        else:
            crsCodeElem = tree.find('/gmd:referenceSystemInfo/gmd:MD_ReferenceSystem/gmd:referenceSystemIdentifier/gmd:RS_Identifier/gmd:code', namespaces)
            rs_identifier = crsCodeElem.getparent()
            rs_identifier.remove(crsCodeElem)
            rs_identifier.append(getCrsCodeAnchor(crs))
        
        dateTime = tree.find('/gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:date/gmd:CI_Date/gmd:date/gco:DateTime', namespaces)
        if dateTime is not None:
            dateTime.text = text(current_datetime.isoformat())
        else:
            dateTime = tree.find('/gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:date/gmd:CI_Date/gmd:date/gco:Date', namespaces)
            dateTime.text = text(current_datetime.date().isoformat())
        
        create_thumbnail(tree, thumbnail_url, title)
        minx, miny, maxx, maxy = extent_tuple
        create_extent(tree, minx, miny, maxx, maxy)
        
        create_transfer_options(tree, qualified_name, spatial_representation_type, title, wms_endpoint, wfs_endpoint, wcs_endpoint)
        resourceCodeElems = tree.xpath("//*[text()='RESOURCE_CODE']")
        for resCodeElem in resourceCodeElems:
            resCodeElem.text = qualified_name
        return ET.tostring(tree, encoding='unicode')
    except:
        logger.exception("Error creating metadata")


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

def create_thumbnail(root_elem, thumbnail_url, thumbnail_desc=None):
    data_ident_elements = root_elem.findall('./gmd:identificationInfo/gmd:MD_DataIdentification', namespaces)
    for data_ident_elem in data_ident_elements:
        prevSiblingNames = ['gmd:citation',
                            'gmd:abstract',
                            'gmd:purpose',
                            'gmd:credit',
                            'gmd:status',
                            'gmd:pointOfContact',
                            'gmd:resourceMaintenance']
        graphicOverviewElem = ET.Element("{http://www.isotc211.org/2005/gmd}graphicOverview")
        insertAfter(data_ident_elem, graphicOverviewElem, prevSiblingNames, namespaces)
        #grov = ET.SubElement(data_ident_elements[0], "{http://www.isotc211.org/2005/gmd}graphicOverview")
        brgr = ET.SubElement(graphicOverviewElem, "{http://www.isotc211.org/2005/gmd}MD_BrowseGraphic")
        file_name = ET.SubElement(brgr, "{http://www.isotc211.org/2005/gmd}fileName")
        file_name_str = ET.SubElement(file_name, "{http://www.isotc211.org/2005/gco}CharacterString")
        file_name_str.text = thumbnail_url
        if thumbnail_desc:
            file_desc = ET.SubElement(brgr, "{http://www.isotc211.org/2005/gmd}fileDescription")
            file_desc_str = ET.SubElement(file_desc, "{http://www.isotc211.org/2005/gco}CharacterString")
            file_desc_str.text = thumbnail_desc
        file_type = ET.SubElement(brgr, "{http://www.isotc211.org/2005/gmd}fileType")
        file_type_str = ET.SubElement(file_type, "{http://www.isotc211.org/2005/gco}CharacterString")
        file_type_str.text = 'gvsigol thumbnail'

def create_extent(root_elem, minx, miny, maxx, maxy):
    data_ident_elements = root_elem.findall('./gmd:identificationInfo/gmd:MD_DataIdentification', namespaces)
    for data_ident_elem in data_ident_elements:
        prevSiblingNames = ['gmd:citation',
                            'gmd:abstract',
                            'gmd:purpose',
                            'gmd:credit',
                            'gmd:status',
                            'gmd:pointOfContact',
                            'gmd:resourceMaintenance',
                            'gmd:spatialRepresentationType',
                            'gmd:spatialResolution',
                            'gmd:language',
                            'gmd:characterSet',
                            'gmd:topicCategory',
                            'gmd:environmentDescription'
                            ]
        extentElem = ET.Element("{http://www.isotc211.org/2005/gmd}extent")
        insertAfter(data_ident_elem, extentElem, prevSiblingNames, namespaces)
        #extentElem = ET.SubElement(data_ident_elem, "{http://www.isotc211.org/2005/gmd}extent")
        exExtentElem = ET.SubElement(extentElem, "{http://www.isotc211.org/2005/gmd}EX_Extent")
        geogExtentElem = ET.SubElement(exExtentElem, "{http://www.isotc211.org/2005/gmd}geographicElement")
        exGeogBBElem = ET.SubElement(geogExtentElem, "{http://www.isotc211.org/2005/gmd}EX_GeographicBoundingBox")
        westBoundLongElem = ET.SubElement(exGeogBBElem, "{http://www.isotc211.org/2005/gmd}westBoundLongitude")
        decimalElem = ET.SubElement(westBoundLongElem, "{http://www.isotc211.org/2005/gco}Decimal")
        decimalElem.text = minx
        eastBoundLongElem = ET.SubElement(exGeogBBElem, "{http://www.isotc211.org/2005/gmd}eastBoundLongitude")
        decimalElem = ET.SubElement(eastBoundLongElem, "{http://www.isotc211.org/2005/gco}Decimal")
        decimalElem.text = maxx
        southBoundLatElem = ET.SubElement(exGeogBBElem, "{http://www.isotc211.org/2005/gmd}southBoundLatitude")
        decimalElem = ET.SubElement(southBoundLatElem, "{http://www.isotc211.org/2005/gco}Decimal")
        decimalElem.text = miny
        northBoundLatElem = ET.SubElement(exGeogBBElem, "{http://www.isotc211.org/2005/gmd}northBoundLatitude")
        decimalElem = ET.SubElement(northBoundLatElem, "{http://www.isotc211.org/2005/gco}Decimal")
        decimalElem.text = maxy

def create_online_resource(parent, url, protocol, name, description, application_profile=None, function=None):
    onlineElem = ET.SubElement(parent, "{http://www.isotc211.org/2005/gmd}onLine")
    onlineResElem = ET.SubElement(onlineElem, "{http://www.isotc211.org/2005/gmd}CI_OnlineResource")
    linkageElem = ET.SubElement(onlineResElem, "{http://www.isotc211.org/2005/gmd}linkage")
    urlElem = ET.SubElement(linkageElem, "{http://www.isotc211.org/2005/gmd}URL")
    urlElem.text = url
    protocolElem = ET.SubElement(onlineResElem, "{http://www.isotc211.org/2005/gmd}protocol")
    charStr = ET.SubElement(protocolElem, "{http://www.isotc211.org/2005/gco}CharacterString")
    charStr.text = protocol
    if application_profile:
        applicationProfileElem = ET.SubElement(onlineResElem, "{http://www.isotc211.org/2005/gmd}applicationProfile")
        charStr = ET.SubElement(applicationProfileElem, "{http://www.isotc211.org/2005/gco}CharacterString")
        charStr.text = application_profile
    nameElem = ET.SubElement(onlineResElem, "{http://www.isotc211.org/2005/gmd}name")
    charStr = ET.SubElement(nameElem, "{http://www.isotc211.org/2005/gco}CharacterString")
    charStr.text = name
    descriptionElem = ET.SubElement(onlineResElem, "{http://www.isotc211.org/2005/gmd}description")
    charStr = ET.SubElement(descriptionElem, "{http://www.isotc211.org/2005/gco}CharacterString")
    charStr.text = description
    if function:
        functionElem = ET.SubElement(onlineResElem, "{http://www.isotc211.org/2005/gmd}function")
        charStr = ET.SubElement(functionElem, "{http://www.isotc211.org/2005/gco}CharacterString")
        charStr.text = function

def create_distrib_format(parent, name, version, specification=None):
    distributionFormatElem = ET.Element("{http://www.isotc211.org/2005/gmd}distributionFormat")
    MD_FormatElem = ET.SubElement(distributionFormatElem, "{http://www.isotc211.org/2005/gmd}MD_Format")
    nameElem = ET.SubElement(MD_FormatElem, "{http://www.isotc211.org/2005/gmd}name")
    nameElemCharStr = ET.SubElement(nameElem, "{http://www.isotc211.org/2005/gco}CharacterString")
    nameElemCharStr.text = name
    versionElem = ET.SubElement(MD_FormatElem, "{http://www.isotc211.org/2005/gmd}version")
    versionElemCharStr = ET.SubElement(versionElem, "{http://www.isotc211.org/2005/gco}CharacterString")
    versionElemCharStr.text = version
    if specification is not None:
        specificationElem = ET.SubElement(MD_FormatElem, "{http://www.isotc211.org/2005/gmd}specification")
        specificationElemCharStr = ET.SubElement(specificationElem, "{http://www.isotc211.org/2005/gco}CharacterString")
        specificationElemCharStr.text = specification
    insertAfter(parent, distributionFormatElem, [], namespaces)

def create_transfer_options(root_elem, qualified_name, spatialRepresentationType, title, wms_endpoint, wfs_endpoint=None, wcs_endpoint=None):
    distribInfoElements = root_elem.findall('./gmd:distributionInfo/gmd:MD_Distribution', namespaces)
    
    if len(distribInfoElements) == 0:
        distributionInfoElem = ET.SubElement(root_elem, "{http://www.isotc211.org/2005/gmd}distributionInfo")
        MD_DistributionElem = ET.SubElement(distributionInfoElem, "{http://www.isotc211.org/2005/gmd}MD_Distribution")
        distribInfoElements = [MD_DistributionElem]
        
    for distribInfoElem in distribInfoElements:
        if spatialRepresentationType == 'vector':
            create_distrib_format(distribInfoElem, 'Shapefile', 'SHP 1.0')
        elif spatialRepresentationType == 'grid':
            create_distrib_format(distribInfoElem, 'TIF', 'GeoTiff 1.0')
        prevSiblingNames = ['gmd:distributionFormat',
                            'gmd:distributor']
        transferOptionsElem = ET.Element("{http://www.isotc211.org/2005/gmd}transferOptions")
        insertAfter(distribInfoElem, transferOptionsElem, prevSiblingNames, namespaces)
        MD_DigitalTransferOptionsElem = ET.SubElement(transferOptionsElem, "{http://www.isotc211.org/2005/gmd}MD_DigitalTransferOptions")
        create_online_resource(MD_DigitalTransferOptionsElem, wms_endpoint, 'OGC:WMS', qualified_name, title)
        if wfs_endpoint:
            create_online_resource(MD_DigitalTransferOptionsElem, wfs_endpoint, 'OGC:WFS', qualified_name, title)
        if wcs_endpoint:
            create_online_resource(MD_DigitalTransferOptionsElem, wcs_endpoint, 'OGC:WCS', qualified_name, title)

class Iso19139_2007Updater(XmlStandardUpdater):
    def update_dateStamp(self):
        dateTime = self.tree.find('./gmd:dateStamp/gco:DateTime', namespaces)
        str_timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
        if dateTime is not None:
            dateTime.text = str_timestamp
        else:
            dateStamp = ET.Element(namespacedTag('gmd', 'dateStamp', namespaces))
            dateTime = ET.Element(namespacedTag('gco', 'DateTime', namespaces))
            dateTime.text =  str_timestamp
            dateStamp.insert(0, dateTime)
            prevSiblingNames = ['gmd:contact']
            insertAfter(self.tree, dateStamp, prevSiblingNames, namespaces)
        return self
    
    def update_extent(self, extent_tuple):
        for geog_bounding_box_element in self.tree.findall('./gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox', namespaces):
            update_extent(geog_bounding_box_element, extent_tuple)
        return self
        
    def update_thumbnail(self, thumbnail_url):
        graphicOverviews = self.tree.findall('./gmd:identificationInfo/gmd:MD_DataIdentification/gmd:graphicOverview', namespaces)
        valid_overviews = 0
        to_remove = []
        for overview in graphicOverviews:
            file_name = overview.find('./gmd:MD_BrowseGraphic/gmd:fileName/gco:CharacterString', namespaces)
            if file_name.text == '' or file_name.text == 'n/a':
                to_remove.append(overview)
            else:
                valid_overviews += 1
                ftype = overview.find('./gmd:MD_BrowseGraphic/gmd:fileType/gco:CharacterString', namespaces)
                desc = overview.find('./gmd:MD_BrowseGraphic/gmd:fileDescription/gco:CharacterString', namespaces)
                if (ftype is not None and ftype.text ==  'gvsigol thumbnail') \
                        or (desc is not None and desc.text == 'gvsigol thumbnail'):
                    file_name.text = thumbnail_url
        for el in to_remove:
            el.getparent().remove(el)
        if valid_overviews == 0:
            create_thumbnail(self.tree, thumbnail_url)
        return self

        
    def update_all(self, extent_tuple, thumbnail_url):
        self.update_extent(extent_tuple)
        self.update_thumbnail(thumbnail_url)
        self.update_dateStamp()
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
    
    
    
    