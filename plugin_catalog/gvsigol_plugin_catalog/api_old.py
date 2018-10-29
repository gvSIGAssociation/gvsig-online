# -*- coding: utf-8 -*-

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
'''
import xml.etree.ElementTree as ET
from datetime import datetime
import requests

class Geonetwork():
    """
    geonetwork-py is a Python interface to Geonetwork XML API
    """
    
    def __init__(self, service_url):
        self.session = requests.Session()
        self.session.verify = False
        self.service_url = service_url
        
    def get_session(self):
        return self.session
    
    def get_service_url(self):
        return self.service_url
    
    def gn_auth(self, user, password):
        self.session.auth = (user, password)
        
    def gn_unauth(self):
        self.session.auth = None
        
        
    def get_query(self, query):
        url = self.service_url + "/srv/spa/q?" + query
        headers = {
            'Accept': 'application/json',
            'X-XSRF-TOKEN': self.get_csrf_token()
        }
              
        r = self.session.get(url, headers=headers)
        if r.status_code==200:
            return r.content
        raise FailedRequestError(r.status_code, r.content)

        
    def gn_insert_metadata(self, layer, abstract, ws, layer_info, ds_type, md_record=None):
        if md_record:
            md_record = md_record.decode("utf-8")
        else:
            md_record = self.create_metadata(layer, abstract, ws, layer_info, ds_type)

        url = self.service_url + "xml.metadata.insert"
        headers = {'content-type': 'application/xml'}
        
        xml =   u'<?xml version="1.0" encoding="UTF-8"?>'
        xml +=  u'<request>'
        xml +=      u'<group>2</group>'
        xml +=      u'<category>_none_</category>'
        xml +=      u'<styleSheet>_none_</styleSheet>'
        xml +=      u'<uuidAction>generateUUID</uuidAction>'
        xml +=      u'<data><![CDATA['
        xml +=          md_record
        xml +=      u']]></data>'
        xml +=  u'</request>'
        
        r = self.session.post(url, data=xml.encode('utf-8'), headers=headers)
        if r.status_code==200:
            response = ET.fromstring(r.text)
            
            for child in response:
                if child.tag == 'uuid':
                    return child.text
                       
        raise FailedRequestError(r.status_code, r.content)

    def csw_update_metadata(uuid, updated_xml_md):
        metadata = '<csw:Transaction xmlns:csw="http://www.opengis.net/cat/csw/2.0.2" xmlns:ogc="http://www.opengis.net/ogc" service="CSW" version="2.0.2">'
        metadata +=     '<csw:Update>'
        metadata +=         updated_xml_md
        metadata +=         '<csw:Constraint version="1.1.0">'
        metadata +=             '<ogc:Filter>'
        metadata +=                 '<ogc:PropertyIsEqualTo>'
        metadata +=                     '<ogc:PropertyName>identifier</ogc:PropertyName>'
        metadata +=                     '<ogc:Literal>' + uuid + '</ogc:Literal>'
        metadata +=                 '</ogc:PropertyIsEqualTo>'
        metadata +=             '</ogc:Filter>'
        metadata +=         '</csw:Constraint>'
        metadata +=     '</csw:Update>'
        metadata += '</csw:Transaction>'
        headers = {
            'Accept': 'application/xml',
            'Content-Type': 'application/xml',
        }
        csw_transaction_url = self.service_url + "/srv/eng/csw-publication"
        csw_response = self.session.post(csw_transaction_url, headers=headers, data=metadata)
        if csw_response.status_code==200:
            tree = ET.fromstring(csw_response.text)
            ns = {'csw': 'http://www.opengis.net/cat/csw/2.0.2'}
            for total_updated in tree.findall('./csw:TransactionResponse/csw:TransactionSummary/csw:totalUpdated', ns):
                if total_updated.text == '1':
                    return uuid
        raise FailedRequestError(r.status_code, r.content)

    def gn_update_metadata(self, uuid, layer, abstract, layer_info, ds_type):
        updated_xml_md = self.get_updated_metadata(layer, uuid, layer_info, ds_type)
        return self.csw_update_metadata(uuid, updated_xml_md)
    
    def add_thumbnail(self, uuid, thumbnail_url):      
        op = "md.processing"        
        url = self.service_url + op + "?uuid=" + uuid + "&process=thumbnail-add&thumbnail_url=" + thumbnail_url       
        r = self.session.get(url)
        if r.status_code==200:
            op = "md.edit"       
            url = self.service_url + op + "?uuid=" + uuid + "&process=thumbnail-add&thumbnail_url=" + thumbnail_url         
            r = self.session.get(url)
            if r.status_code==200:
                return True
                    
        raise FailedRequestError(r.status_code, r.content)
  
    
    def set_metadata_privileges(self, uuid):
        url = self.service_url + "md.privileges.update?_content_type=json&_1_0=on&_1_1=on&_2_0=on&_2_3=on&uuid=" + uuid
        
        r = self.session.get(url)
        if r.status_code==200:
            return True
                    
        raise FailedRequestError(r.status_code, r.content)
    
    def gn_delete_metadata(self, lm):
        
        url = self.service_url + "xml.metadata.delete"
        headers = {'content-type': 'application/xml'}
        
        xml =   '<?xml version="1.0" encoding="UTF-8"?>'
        xml +=  '<request>'
        xml +=      '<uuid>' + lm.metadata_uuid + '</uuid>'
        xml +=  '</request>'
        
        r = self.session.post(url, data=xml, headers=headers)
        if r.status_code==200:
            return True
        raise FailedRequestError(r.status_code, r.content)
    
    
    def create_metadata(self, layer, abstract, ws, layer_info, ds_type):
        
        maxx = str(layer_info[ds_type]['latLonBoundingBox']['maxx'])
        maxy = str(layer_info[ds_type]['latLonBoundingBox']['maxy'])
        minx = str(layer_info[ds_type]['latLonBoundingBox']['minx'])
        miny = str(layer_info[ds_type]['latLonBoundingBox']['miny'])
        crs_object = layer_info[ds_type]['nativeBoundingBox']['crs']
        
        crs = None
        if isinstance(crs_object,dict):
            crs = str(crs_object['$'])
        else:
            crs = str(crs_object)
        
        metadata =  '<gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd" '
        metadata +=     'xmlns:srv="http://www.isotc211.org/2005/srv" xmlns:gmx="http://www.isotc211.org/2005/gmx" '
        metadata +=     'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:gco="http://www.isotc211.org/2005/gco" '
        metadata +=     'xmlns:gml="http://www.opengis.net/gml" xmlns:gts="http://www.isotc211.org/2005/gts" '
        metadata +=     'xmlns:geonet="http://www.fao.org/geonetwork" xsi:schemaLocation="http://www.isotc211.org/2005/gmd ../schema.xsd">'
        
        metadata +=     '<gmd:metadataStandardName>'
        metadata +=         '<gco:CharacterString>ISO 19115:2003/19139</gco:CharacterString>'
        metadata +=     '</gmd:metadataStandardName>'
        
        metadata +=     '<gmd:metadataStandardVersion>'
        metadata +=         '<gco:CharacterString>1.0</gco:CharacterString>'
        metadata +=     '</gmd:metadataStandardVersion>'
        
        metadata +=     '<gmd:spatialRepresentationInfo/>'
        
        metadata +=     '<gmd:referenceSystemInfo>'
        metadata +=         '<gmd:MD_ReferenceSystem>'
        metadata +=             '<gmd:referenceSystemIdentifier>'
        metadata +=                 '<gmd:RS_Identifier>'
        metadata +=                     '<gmd:code>'
        metadata +=                         '<gco:CharacterString>' + crs + '</gco:CharacterString>'
        metadata +=                     '</gmd:code>'
        metadata +=                 '</gmd:RS_Identifier>'
        metadata +=             '</gmd:referenceSystemIdentifier>'
        metadata +=         '</gmd:MD_ReferenceSystem>'
        metadata +=     '</gmd:referenceSystemInfo>'
        
        metadata +=     '<gmd:identificationInfo>'
        metadata +=         '<gmd:MD_DataIdentification>'
        metadata +=             '<gmd:citation>'
        metadata +=                 '<gmd:CI_Citation>'
        metadata +=                     '<gmd:title xsi:type="gmd:PT_FreeText_PropertyType">'
        metadata +=                         '<gco:CharacterString>' + layer.title + '</gco:CharacterString>'
        metadata +=                         '<gmd:PT_FreeText>'
        metadata +=                             '<gmd:textGroup>'
        metadata +=                                 '<gmd:LocalisedCharacterString locale="#ES">' + layer.title + '</gmd:LocalisedCharacterString>'
        metadata +=                             '</gmd:textGroup>'
        metadata +=                         '</gmd:PT_FreeText>'
        metadata +=                     '</gmd:title>'
        metadata +=                     '<gmd:date>'
        metadata +=                         '<gmd:CI_Date>'
        metadata +=                             '<gmd:date>'
        metadata +=                                 '<gco:DateTime>' + str(datetime.now()) + '</gco:DateTime>'
        metadata +=                             '</gmd:date> '
        metadata +=                             '<gmd:dateType>'
        metadata +=                                 '<gmd:CI_DateTypeCode codeList="./resources/codeList.xml#CI_DateTypeCode" codeListValue="creation"/>'
        metadata +=                             '</gmd:dateType>'
        metadata +=                         '</gmd:CI_Date>'
        metadata +=                     '</gmd:date>'
        metadata +=                 '</gmd:CI_Citation>'
        metadata +=             '</gmd:citation>'
        metadata +=             '<gmd:abstract>'
        metadata +=                 '<gco:CharacterString>' + abstract + '</gco:CharacterString>'
        metadata +=             '</gmd:abstract>'
        metadata +=             '<gmd:extent>'
        metadata +=                 '<gmd:EX_Extent>'
        metadata +=                     '<gmd:geographicElement>'
        metadata +=                         '<gmd:EX_GeographicBoundingBox>'
        metadata +=                             '<gmd:westBoundLongitude>'
        metadata +=                                 '<gco:Decimal>' + maxx + '</gco:Decimal>'
        metadata +=                             '</gmd:westBoundLongitude>'
        metadata +=                             '<gmd:eastBoundLongitude>'
        metadata +=                                 '<gco:Decimal>' + minx + '</gco:Decimal>'
        metadata +=                             '</gmd:eastBoundLongitude>'
        metadata +=                             '<gmd:southBoundLatitude>'
        metadata +=                                 '<gco:Decimal>' + maxy + '</gco:Decimal>'
        metadata +=                             '</gmd:southBoundLatitude>'
        metadata +=                             '<gmd:northBoundLatitude>'
        metadata +=                                 '<gco:Decimal>' + miny + '</gco:Decimal>'
        metadata +=                             '</gmd:northBoundLatitude>'
        metadata +=                         '</gmd:EX_GeographicBoundingBox>'
        metadata +=                     '</gmd:geographicElement>'
        metadata +=                 '</gmd:EX_Extent>'
        metadata +=             '</gmd:extent>'
        metadata +=         '</gmd:MD_DataIdentification>'
        metadata +=     '</gmd:identificationInfo>'
        
        metadata +=     '<gmd:distributionInfo>'
        metadata +=         '<gmd:MD_Distribution>'
        metadata +=             '<gmd:distributionFormat>'
        metadata +=                 '<gmd:MD_Format>'
        metadata +=                     '<gmd:name>'
        metadata +=                         '<gco:CharacterString>ShapeFile</gco:CharacterString>'
        metadata +=                     '</gmd:name>'
        metadata +=                     '<gmd:version>'
        metadata +=                         '<gco:CharacterString>Grass Version 6.1</gco:CharacterString>'
        metadata +=                     '</gmd:version>'
        metadata +=                 '</gmd:MD_Format>'
        metadata +=             '</gmd:distributionFormat>'
        metadata +=             '<gmd:transferOptions>'
        metadata +=                 '<gmd:MD_DigitalTransferOptions>'
        metadata +=                     '<gmd:onLine>'
        metadata +=                         '<gmd:CI_OnlineResource>'
        metadata +=                             '<gmd:linkage>'
        metadata +=                                 '<gmd:URL>' + ws.wms_endpoint + '</gmd:URL>'
        metadata +=                             '</gmd:linkage>'
        metadata +=                             '<gmd:protocol>'
        metadata +=                                 '<gco:CharacterString>OGC:WMS</gco:CharacterString>'
        metadata +=                             '</gmd:protocol>'
        metadata +=                             '<gmd:name>'
        metadata +=                                 '<gco:CharacterString>' + ws.name + ':' + layer.name + '</gco:CharacterString>'
        metadata +=                             '</gmd:name>'
        metadata +=                             '<gmd:description>'
        metadata +=                                 '<gco:CharacterString>' + layer.title + '</gco:CharacterString>'
        metadata +=                             '</gmd:description>'
        metadata +=                         '</gmd:CI_OnlineResource>'
        metadata +=                     '</gmd:onLine>'
        metadata +=                 '</gmd:MD_DigitalTransferOptions>'
        metadata +=             '</gmd:transferOptions>'
        metadata +=         '</gmd:MD_Distribution>'
        metadata +=     '</gmd:distributionInfo>'
        
        metadata += '</gmd:MD_Metadata>'
        
        return metadata

    def get_updated_metadata(self, layer, uuid, layer_info, ds_type):
        url = self.service_url + "xml.metadata.get?uuid=" + uuid
        md_response = self.session.get(url)
        if md_response.status_code == 200:
            extent_tuple = self.get_extent(layer_info, ds_type)
            # TODO: we can later generalize this import to call a different module according to the
            # metadata standard of the record to be updated
            from gvsigol_plugin_catalog.mdstandards import iso19139_2007
            return iso19139_2007.update_metadata(md_response.content, extent_tuple, layer.thumbnail.url)
        raise FailedRequestError(md_response.status_code, md_response.content)

class RequestError(Exception):
    def __init__(self, status_code=-1, server_message=""):
        self.status_code = status_code
        self.server_message = server_message
        self.message = None
    
    def set_message(self, message):
        self.message = message
    
    def get_message(self):
        if self.message:
            return self.message
        else:
            return self.server_message 

class UploadError(RequestError):
    pass

class ConflictingDataError(RequestError):
    pass

class AmbiguousRequestError(RequestError):
    pass

class FailedRequestError(RequestError):
    pass
