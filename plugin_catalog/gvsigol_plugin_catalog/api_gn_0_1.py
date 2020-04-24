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
from builtins import str as text
from lxml import etree as ET
from gvsigol import settings
from datetime import datetime
import requests
import json
import re
from gvsigol_plugin_catalog.mdstandards import registry
#from gvsigol_plugin_catalog.mdstandards import iso19139_2007
import logging
logger = logging.getLogger("gvsigol")
from xmlutils import getTextFromXMLNode, getXMLNode, getXMLCodeText, sanitizeXmlText

DEFAULT_TIMEOUT = 10 #seconds

def get_default_timeout():
    global DEFAULT_TIMEOUT
    try:
        from gvsigol_plugin_catalog.settings import CATALOG_TIMEOUT
        DEFAULT_TIMEOUT = CATALOG_TIMEOUT
    except:
        try:
            from gvsigol_plugin_catalog.settings import DEFAULT_SERVICE_TIMEOUT
            DEFAULT_TIMEOUT = DEFAULT_SERVICE_TIMEOUT
        except:
            pass
    return DEFAULT_TIMEOUT

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
    
    def get_auth(self):
        return self.session.auth
    
    def gn_auth(self, user, password):
        self.session.auth = (user, password)
        try:
            #URL = 'http://localhost:8080/geonetwork/srv/eng/info?type=me'
            URL = self.service_url + "/srv/eng/info?type=me"
            r = self.session.post(URL, timeout=get_default_timeout(), proxies=settings.PROXIES)
            if r.status_code==403:
                
                headers = {
                    'X-XSRF-TOKEN': self.get_csrf_token()
                }
                
                r = self.session.post(URL, auth=(user, password), headers=headers, timeout=get_default_timeout(), proxies=settings.PROXIES)
                if r.status_code==200:
                    return True
                return False
            else:
                return False
        except Exception as e:
            logger.exception('Error authenticating')
            print (e.message)
            return False
        
    def gn_unauth(self):
        self.session.auth = None
        
    def get_csrf_token(self):
        cookie = self.session.cookies.get_dict()
        return cookie.get('XSRF-TOKEN')
    
    def gn_insert_metadata(self, md_record):
        #curl -X PUT --header 'Content-Type: application/xml' --header 'Accept: application/json' -d '.........XML_code............'  
        # 'http://localhost:8080/geonetwork/srv/api/0.1/records?metadataType=METADATA&assignToCatalog=true&uuidProcessing=generateUUID&transformWith=_none_'
        url = self.service_url + "/srv/api/0.1/records?metadataType=METADATA&assignToCatalog=true&transformWith=_none_"
        headers = {
            'Content-Type': 'application/xml',
            'Accept': 'application/json',
            'X-XSRF-TOKEN': self.get_csrf_token()
        }
        r = self.session.put(url, data=md_record.encode("UTF-8"), headers=headers, timeout=get_default_timeout(), proxies=settings.PROXIES)
        
        if r.status_code==201:
            #print md_record
            response = json.loads(r.text)
            
            uuid = None
            id = None
            for child in response:
                #if child == 'uuid':
                #    uuid = response[child]
                if child == 'metadataInfos':
                    for idx in response[child]:
                        id = idx
                        message = response[child][idx][0]['message']
                        uuids = re.findall('\'([^\']*)\'', message)
                        if uuids.__len__() > 0:
                            uuid = uuids[0]

            if uuid and id:
                return [uuid, id]
        else:
            return False    
        raise FailedRequestError(r.status_code, r.content)

    def csw_update_metadata(self, uuid, updated_xml_md):
        metadata = u'<csw:Transaction xmlns:csw="http://www.opengis.net/cat/csw/2.0.2" xmlns:ogc="http://www.opengis.net/ogc" service="CSW" version="2.0.2">'
        metadata +=     u'<csw:Update>'
        metadata +=         updated_xml_md
        metadata +=         u'<csw:Constraint version="1.1.0">'
        metadata +=             u'<ogc:Filter>'
        metadata +=                 u'<ogc:PropertyIsEqualTo>'
        metadata +=                     u'<ogc:PropertyName>identifier</ogc:PropertyName>'
        metadata +=                     u'<ogc:Literal>' + uuid + u'</ogc:Literal>'
        metadata +=                 u'</ogc:PropertyIsEqualTo>'
        metadata +=             u'</ogc:Filter>'
        metadata +=         u'</csw:Constraint>'
        metadata +=     u'</csw:Update>'
        metadata += u'</csw:Transaction>'
        headers = {
            'Accept': 'application/xml',
            'Content-Type': 'application/xml',
            'X-XSRF-TOKEN': self.get_csrf_token()
        }
        csw_transaction_url = self.service_url + "/srv/eng/csw-publication"
        csw_response = self.session.post(csw_transaction_url, headers=headers, data=metadata.encode("UTF-8"), timeout=get_default_timeout(), proxies=settings.PROXIES)
        if csw_response.status_code==200:
            tree = ET.fromstring(csw_response.content)
            ns = {'csw': 'http://www.opengis.net/cat/csw/2.0.2'}
            for total_updated in tree.findall('./csw:TransactionSummary/csw:totalUpdated', ns):
                if total_updated.text == '1':
                    return uuid
        raise FailedRequestError(csw_response.status_code, csw_response.content)

    def gn_update_metadata(self, uuid, layer, abstract, layer_info, ds_type):
        """
        Updates the metadata record based on the layer data (currently just extent).
        It uses a CSW update transaction for the update. Previously, we were deleting and re-inserting
        the record, but that approach removed any existing permissions, user rating, etc, so it was a
        bad idea.
        """
        updated_xml_md = self.get_updated_metadata(layer, uuid, layer_info, ds_type)
        return self.csw_update_metadata(uuid, updated_xml_md)

    def add_thumbnail(self, uuid, thumbnail_url):
        # We use the existing gvSIG Online thumbnail when inserting the metadata,
        # so we don't need to insert using GN internal file storage.
        #
        # If needed, we could use something as:
        ## https://test.gvsigonline.com/geonetwork/srv/api/records/112/processes/thumbnail-add?thumbnail_url=https://test.gvsigonline.com/geonetwork/srv/api/records/597860bc-8cfb-4354-8e18-fbc716269df8/attachments/VPOBMQAX.png&thumbnail_desc=test2&process=thumbnail-add&id=112
        ## 
        pass
    
    def add_thumbnail_attachment(self, uuid, thumbnail_url):
        """
        Adds a thumbnail as an attachment to the metadata record using the Geonetwork internal file store.
        Note this action does NOT add the thumnail to the metadata content (graphicOverview).
        """
        url = self.service_url + "/srv/api/0.1/records/"+uuid+"/attachments?url=" + thumbnail_url
        headers = {
            'X-XSRF-TOKEN': self.get_csrf_token()
        }
        r = self.session.put(url, headers=headers, timeout=get_default_timeout(), proxies=settings.PROXIES)
        if r.status_code==201:
            return True
        else: 
            return False      
        raise FailedRequestError(r.status_code, r.content)
  
    
    def set_metadata_privileges(self, uuid):
        #url = self.service_url + "md.privileges.update?_content_type=json&_1_0=on&_1_1=on&_2_0=on&_2_3=on&uuid=" + uuid
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'X-XSRF-TOKEN': self.get_csrf_token()
        }
        privileges = {
            "privileges": []
        }
        response2 = []
        
        url2 = self.service_url + "/srv/api/0.1/operations"
        r2 = self.session.get(url2, headers=headers, timeout=get_default_timeout(), proxies=settings.PROXIES)
        if r2.status_code==200:
            response2 = json.loads(r2.text)
        
        #Grupos por defecto
        idxs = [-1,0,1]
        for idx in idxs:
            privi_group = {
                "operations": {
                    },
                "group": idx
            }
            
            for operation in response2:
                if operation['name'] == "view" or operation['name'] == "dynamic" or operation['name'] == "download":
                    allowOperation = True
                else:
                    allowOperation = False
                privi_group['operations'][operation['name']] = allowOperation

            privileges["privileges"].append(privi_group)
        
        
        url = self.service_url + "/srv/api/0.1/groups"
        r = self.session.get(url, headers=headers, timeout=get_default_timeout(), proxies=settings.PROXIES)
        if r.status_code==200:
            response = json.loads(r.text)
            #print r.text
            
            #Otros grupos
            for group in response:
                logger.debug(group)
                privi_group = {
                    "operations": {
                        },
                    "group": group['id']
                }
                
                for operation in response2:
                    if operation['name'] == "view" or operation['name'] == "dynamic" or operation['name'] == "download":
                        allowOperation = True
                    else:
                        allowOperation = False
                    privi_group['operations'][operation['name']] = allowOperation
    
                privileges["privileges"].append(privi_group)
        
        
        #url3 = self.service_url + "srv/api/md.privileges.update?_content_type=json&_1_0=on&_1_1=on&_2_0=on&_2_3=on&uuid=" + uuid
        url3 = self.service_url + "/srv/api/0.1/records/"+ uuid +"/sharing"
        headers = {
                'Accept': '*/*',
                'content-type': 'application/json',
                'X-XSRF-TOKEN': self.get_csrf_token()
            }
        r3 = self.session.put(url3, data=json.dumps(privileges), headers=headers, timeout=get_default_timeout(), proxies=settings.PROXIES)
        if r3.status_code==204:
            return True
        else: 
            return False
                   
        raise FailedRequestError(r.status_code, r.content)
    
    def gn_delete_metadata(self, lm):
        #curl -X DELETE --header 'Accept: */*' 'http://localhost:8080/geonetwork/srv/api/0.1/records/159?withBackup=false'
        #NOTE: uuid is an id not in format 97769e85-2e7b-418b-a8c8-0163bfb97aac
        url = self.service_url + "/srv/api/0.1/records/"+str(lm.metadata_id)+"?withBackup=false"
        headers = {
            'Accept': 'application/json',
            'X-XSRF-TOKEN': self.get_csrf_token()
        }
              
        r = self.session.delete(url, headers=headers, timeout=get_default_timeout(), proxies=settings.PROXIES)
        if r.status_code==204:
            return True
        raise FailedRequestError(r.status_code, r.content)
    
   
    def _getXMLConstraints(self, tree, xpath_filter, ns):
        useLimitations = []
        accessConstraints = []
        useConstraints = []
        otherConstraints = []
        for constraintsNode in tree.findall(xpath_filter, ns):
            for useLimitationsNode in constraintsNode.findall('./gmd:MD_Constraints/gmd:useLimitation/gco:CharacterString', ns):
                if useLimitationsNode.text:
                    useLimitations.append(sanitizeXmlText(useLimitationsNode.text))
            for accessConstraintsNode in constraintsNode.findall('./gmd:MD_LegalConstraints/gmd:accessConstraints/gmd:MD_RestrictionCode', ns):
                accessConstraints.append(sanitizeXmlText(getXMLCodeText(accessConstraintsNode, 'codeListValue', ns)))
            for useConstraintsNode in constraintsNode.findall('./gmd:MD_LegalConstraints/gmd:useConstraints/gmd:MD_RestrictionCode', ns):
                useConstraints.append(sanitizeXmlText(getXMLCodeText(useConstraintsNode, ns=ns)))
            for otherConstraintsNode in constraintsNode.findall('./gmd:MD_LegalConstraints/gmd:otherConstraints/gco:CharacterString', ns):
                if otherConstraintsNode.text:
                    otherConstraints.append(sanitizeXmlText(otherConstraintsNode.text))
        return {
                'useLimitations': useLimitations,
                'accessConstraints': accessConstraints,
                'useConstraints': useConstraints,
                'otherConstraints': otherConstraints
                }
    
    def _getResponsibleParty(self, node, ns):
        # TODO: manage mutiplicities (e.g. online resource, phone, etc)
        individualName = getTextFromXMLNode(node, './gmd:individualName/gco:CharacterString/', ns)
        organisationName = getTextFromXMLNode(node, './gmd:organisationName/gco:CharacterString/', ns)
        roleNode = getXMLNode(node, './gmd:role/gco:CharacterString/', ns)
        role = getXMLCodeText(roleNode, ns=ns)
        email = getTextFromXMLNode(node, './gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:electronicMailAddress/gco:CharacterString/', ns)
        phone = getTextFromXMLNode(node, './gmd:contactInfo/gmd:CI_Contact/gmd:phone/gmd:CI_Telephone/gmd:voice/gco:CharacterString/', ns)
        url = getTextFromXMLNode(node, './gmd:contactInfo/gmd:CI_Contact/gmd:onlineResource/gmd:CI_OnlineResource/gmd:linkage/gmd:URL/', ns)
        onlineResources = []
        for onlineResourceNode in node.findall('./gmd:contactInfo/gmd:CI_Contact/gmd:onlineResource/gmd:CI_OnlineResource'):
            onlineResource = self._getOnlineResource(onlineResourceNode, ns)
            onlineResources.append(onlineResource)
        return {
            'individualName': individualName,
            'organisationName': organisationName,
            'role': role,
            'email': email,
            'phone': phone,
            'url': url
            }
        
    def _getOnlineResource(self, node, ns):
        url = getTextFromXMLNode(node, './gmd:linkage/gmd:URL', ns)
        protocol = getTextFromXMLNode(node, './gmd:protocol/gco:CharacterString', ns)
        name = getTextFromXMLNode(node, './gmd:name/gco:CharacterString', ns)
        description = getTextFromXMLNode(node, './gmd:description/gco:CharacterString', ns)
        applicationProfile = getTextFromXMLNode(node, './gmd:applicationProfile/gco:CharacterString', ns)
        function = getTextFromXMLNode(node, './gmd:function/gco:CharacterString', ns)
        return {
            'name': sanitizeXmlText(name),
            'description': sanitizeXmlText(description),
            'applicationProfile': sanitizeXmlText(applicationProfile),
            'function': sanitizeXmlText(function),
            'protocol': sanitizeXmlText(protocol),
            'url': sanitizeXmlText(url)
            }
    def gn_get_metadata_raw(self, metadata_id):
        url = self.service_url + "/srv/api/0.1/records/"+str(metadata_id)
        headers = {
            'Accept': 'application/xml',
            'X-XSRF-TOKEN': self.get_csrf_token()
        }
              
        r = self.session.get(url, headers=headers, timeout=get_default_timeout(), proxies=settings.PROXIES)
        logger.debug('gn_get_metadata_raw: ' + text(r.status_code))
        if r.status_code==200:
            return r.content
        raise FailedRequestError(r.status_code, r.content)
    
    def gn_get_metadata(self, metadata_id):
        #curl -X DELETE --header 'Accept: */*' 'http://localhost:8080/geonetwork/srv/api/0.1/records/97769e85-2e7b-418b-a8c8-0163bfb97aac?withBackup=false'
        url = self.service_url + "/srv/api/0.1/records/"+str(metadata_id)+""
        print ("Getting metadata from uuid:" + str(metadata_id) + " -> " + url)
        headers = {
            'Accept': 'application/xml',
            'X-XSRF-TOKEN': self.get_csrf_token()
        }
              
        r = self.session.get(url, headers=headers, timeout=get_default_timeout(), proxies=settings.PROXIES)
        if r.status_code==200:
            try:
                tree = ET.fromstring(r.content)
                logger.debug(r.content)
                ns = {'gmd': 'http://www.isotc211.org/2005/gmd', 'gco': 'http://www.isotc211.org/2005/gco'}
                
                metadata_id = getTextFromXMLNode(tree, './gmd:fileIdentifier/', ns)
                title = getTextFromXMLNode(tree, './gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:title/', ns)
                abstract = getTextFromXMLNode(tree, './gmd:identificationInfo/gmd:MD_DataIdentification/gmd:abstract/', ns)
                publish_date = getTextFromXMLNode(tree, './gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:date/gmd:CI_Date/gmd:date/', ns)
                
                period_start = ''
                period_end = ''
                aux = tree.findall('./gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent/gmd:extent/', ns)
                if len(aux) > 0 and len(aux[0]) == 2:
                    period_start = aux[0][0].text
                    period_end = aux[0][1].text
                
                categories = []
                for category in tree.findall('./gmd:identificationInfo/gmd:MD_DataIdentification/gmd:topicCategory/gmd:MD_TopicCategoryCode/', ns):
                    categories.append(sanitizeXmlText(category.text))
                
                keywords = []
                for keyword in tree.findall('./gmd:identificationInfo/gmd:MD_DataIdentification/gmd:descriptiveKeywords/gmd:MD_Keywords/gmd:keyword/', ns):
                    keywords.append(sanitizeXmlText(keyword.text))
                
                representation_type = ''
                aux = tree.findall('./gmd:identificationInfo/gmd:MD_DataIdentification/gmd:spatialRepresentationType/', ns)
                if len(aux) > 0:
                    representation_type = aux[0].attrib['codeListValue'] 
                scale = getTextFromXMLNode(tree, './gmd:identificationInfo/gmd:MD_DataIdentification/gmd:spatialResolution/gmd:MD_Resolution/gmd:equivalentScale/gmd:MD_RepresentativeFraction/gmd:denominator/', ns) 
                srs = getTextFromXMLNode(tree, './gmd:referenceSystemInfo/gmd:MD_ReferenceSystem/gmd:referenceSystemIdentifier/gmd:RS_Identifier/gmd:code/', ns)
                
                #https://test.gvsigonline.com/geonetwork/srv/spa/region.getmap.png?mapsrs=EPSG:3857&width=250&background=settings&geomsrs=EPSG:4326&geom=Polygon((-18.1595005217%2043.9729489023,4.96320908311%2043.9729489023,4.96320908311%2025.9993588695,-18.1595005217%2025.9993588695,-18.1595005217%2043.9729489023))
                coords_w = getTextFromXMLNode(tree, './gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:westBoundLongitude/', ns)
                coords_e = getTextFromXMLNode(tree, './gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:eastBoundLongitude/', ns)
                coords_s = getTextFromXMLNode(tree, './gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:southBoundLatitude/', ns)
                coords_n = getTextFromXMLNode(tree, './gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:northBoundLatitude/', ns)
                
                image_url = self.service_url + '/srv/spa/region.getmap.png?mapsrs=EPSG:3857&width=250&background=osm&geomsrs=EPSG:4326&geom=Polygon(('+coords_w+' '+coords_s+','+coords_e+' '+coords_s+','+coords_e+' '+coords_n+','+coords_w+' '+coords_n+','+coords_w+' '+coords_s+'))'
                
                #thumbnails
                thumbnails_urls = []
                for thumbnail_url in tree.findall('./gmd:identificationInfo/gmd:MD_DataIdentification/gmd:graphicOverview/gmd:MD_BrowseGraphic/gmd:fileName/', ns):
                    thumbnails_urls.append(thumbnail_url.text)
                    
                thumbnail_names = []
                for thumbnail_name in tree.findall('./gmd:identificationInfo/gmd:MD_DataIdentification/gmd:graphicOverview/gmd:MD_BrowseGraphic/gmd:fileDescription/', ns):
                    thumbnail_names.append(thumbnail_name.text)
                
                thumbnails = []
                if thumbnails_urls.__len__() == thumbnail_names.__len__():
                    for i in range(0,thumbnails_urls.__len__()):
                        thumbnail = {
                            'url' : sanitizeXmlText(thumbnails_urls[i]),
                            'name': sanitizeXmlText(thumbnail_names[i])
                        }
                        thumbnails.append(thumbnail)
                
                
                resource_constraints = self._getXMLConstraints(tree, './gmd:identificationInfo/gmd:MD_DataIdentification/gmd:resourceConstraints', ns)
                metadata_constraints = self._getXMLConstraints(tree, './gmd:metadataConstraints', ns)
                
                #resources
                resources = []
                for onlineResourceNode in tree.findall('./gmd:distributionInfo/gmd:MD_Distribution/gmd:transferOptions/gmd:MD_DigitalTransferOptions/gmd:onLine/gmd:CI_OnlineResource', ns):
                    onlineResource = self._getOnlineResource(onlineResourceNode, ns)
                    resources.append(onlineResource)
                resource_contacts = []
                for pointOfContact in tree.findall('./gmd:identificationInfo/gmd:MD_DataIdentification/gmd:pointOfContact', ns):
                    contact = {}
                    organisation = pointOfContact.find('./gmd:CI_ResponsibleParty/gmd:organisationName/gco:CharacterString', ns)
                    role = pointOfContact.find('./gmd:CI_ResponsibleParty/gmd:role/gmd:CI_RoleCode', ns)
                    if organisation is not None:
                        contact['organisation'] = sanitizeXmlText(organisation.text)
                    if role is not None:
                        contact['role'] = sanitizeXmlText(getXMLCodeText(role))
                    contactInfoNode = pointOfContact.find('./gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:onlineResource/gmd:CI_OnlineResource', ns)
                    if contactInfoNode is not None:
                        onlineResource = self._getOnlineResource(contactInfoNode, ns)
                        contact['onlineResource'] = onlineResource
                    resource_contacts.append(contact)
                metadata_contacts = []
                for pointOfContact in tree.findall('./gmd:contact', ns):
                    contact = {}
                    organisation = pointOfContact.find('./gmd:CI_ResponsibleParty/gmd:organisationName/gco:CharacterString', ns)
                    role = pointOfContact.find('./gmd:CI_ResponsibleParty/gmd:role/gmd:CI_RoleCode', ns)
                    if organisation is not None:
                        contact['organisation'] = sanitizeXmlText(organisation.text)
                    if role is not None:
                        contact['role'] = sanitizeXmlText(getXMLCodeText(role))
                    contactInfoNode = pointOfContact.find('./gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:onlineResource/gmd:CI_OnlineResource', ns)
                    if contactInfoNode is not None:
                        onlineResource = self._getOnlineResource(contactInfoNode, ns)
                        contact['onlineResource'] = onlineResource
                    metadata_contacts.append(contact)
                responsible_parties = []
                for responsibleParty in tree.findall('./gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:citedResponsibleParty/gmd:CI_ResponsibleParty', ns):
                    contact = {}
                    organisation = responsibleParty.find('./gmd:organisationName/gco:CharacterString', ns)
                    role = responsibleParty.find('./gmd:role/gmd:CI_RoleCode', ns)
                    if organisation is not None:
                        contact['organisation'] = sanitizeXmlText(organisation.text)
                    if role is not None:
                        contact['role'] = sanitizeXmlText(getXMLCodeText(role))
                    contactInfoNode = responsibleParty.find('./gmd:contactInfo/gmd:CI_Contact/gmd:onlineResource/gmd:CI_OnlineResource', ns)
                    if contactInfoNode is not None:
                        onlineResource = self._getOnlineResource(contactInfoNode, ns)
                        contact['onlineResource'] = onlineResource
                    responsible_parties.append(contact)
                contacts = {
                    'metadata_contacts': metadata_contacts,
                    'resource_contacts': resource_contacts,
                    'responsible_parties': responsible_parties
                    }
                
                resource = {
                    'metadata_id': sanitizeXmlText(metadata_id),
                    'title': sanitizeXmlText(title),
                    'abstract': sanitizeXmlText(abstract),
                    'publish_date': sanitizeXmlText(publish_date),
                    'period_start': sanitizeXmlText(period_start),
                    'period_end': sanitizeXmlText(period_end),
                    'categories': categories,
                    'keywords': keywords,
                    'representation_type': sanitizeXmlText(representation_type),
                    'scale': sanitizeXmlText(scale),
                    'srs': sanitizeXmlText(srs),
                    'image_url': sanitizeXmlText(image_url),
                    'thumbnails': thumbnails,
                    'resources': resources,
                    'resource_constraints': resource_constraints,
                    'metadata_constraints': metadata_constraints,
                    'contacts': contacts
                }
                
                return resource
            except Exception as e:
                logger.exception(e)
            #return ET.tostring(tree, encoding='UTF-8')
            #return r.content
        logger.error(r.status_code)
        logger.error(r.content)
        raise FailedRequestError(r.status_code, r.content)
    
    def get_query(self, query):
        url = self.service_url + "/srv/eng/q?" + query
        headers = {
            'Accept': 'application/json',
            'X-XSRF-TOKEN': self.get_csrf_token()
        }
              
        r = self.session.get(url, headers=headers, timeout=get_default_timeout(), proxies=settings.PROXIES)
        if r.status_code==200:
            return r.content
        raise FailedRequestError(r.status_code, r.content)

    def get_updated_metadata(self, layer, uuid, layer_info, ds_type):
        headers = {
            'Accept': 'application/xml',
            'Content-Type': 'application/xml',
            'X-XSRF-TOKEN': self.get_csrf_token()
        }
        md_url = self.service_url + "/srv/api/0.1/records/" + uuid
        md_response = self.session.get(md_url, headers=headers, timeout=get_default_timeout(), proxies=settings.PROXIES)
        if md_response.status_code == 200:
            extent_tuple = self.get_extent(layer_info, ds_type)
            # TODO: we can later generalize this import to call a different module according to the
            # metadata standard of the record to be updated
            
            updater = registry.get_updater(md_response.content)
            return updater.update_all(extent_tuple, layer.thumbnail.url).tostring()
            #return iso19139_2007.update_metadata(md_response.content, extent_tuple, layer.thumbnail.url)
        raise FailedRequestError(md_response.status_code, md_response.content)

    def get_extent(self, layer_info, ds_type):
        minx = "{:f}".format(layer_info[ds_type]['latLonBoundingBox']['minx'])
        miny = "{:f}".format(layer_info[ds_type]['latLonBoundingBox']['miny'])
        maxx = "{:f}".format(layer_info[ds_type]['latLonBoundingBox']['maxx'])
        if layer_info[ds_type]['latLonBoundingBox']['minx'] > layer_info[ds_type]['latLonBoundingBox']['maxx']:
            maxx = "{:f}".format(layer_info[ds_type]['latLonBoundingBox']['minx'] + 1)
        maxy = str(layer_info[ds_type]['latLonBoundingBox']['maxy'])
        if layer_info[ds_type]['latLonBoundingBox']['miny'] > layer_info[ds_type]['latLonBoundingBox']['maxy']:
            maxy = "{:f}".format(layer_info[ds_type]['latLonBoundingBox']['miny'] + 1)
        return (minx, miny, maxx, maxy)
    
                
    def get_online_resources(self, record_uuid):
        """
        Returns a list of OnlineResource objects, describing the online resources
        encoded in the provided metadata_record_uuid
        """
        url = self.service_url + "/srv/api/0.1/records/" + record_uuid + "/related?type=onlines" # /related?type=onlines&start=1&rows=100
        headers = {
            'Accept': 'application/json',
            #'Accept': 'application/xml',
            'X-XSRF-TOKEN': self.get_csrf_token()
        }
              
        r = self.session.get(url, headers=headers, timeout=get_default_timeout(), proxies=settings.PROXIES)
        if r.status_code==200:
            return r.json()
        raise FailedRequestError(r.status_code, r.content)

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