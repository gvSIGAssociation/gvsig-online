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
import json
import re

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
            r = self.session.post(URL)
            if r.status_code==403:
                
                headers = {
                    'X-XSRF-TOKEN': self.get_csrf_token()
                }
                
                r = self.session.post(URL, auth=(user, password), headers=headers)
                if r.status_code==200:
                    return True
                return False
            else:
                return False
        except Exception as e:
            print (e.message)
            return False
        
    def gn_unauth(self):
        self.session.auth = None
        
    def get_csrf_token(self):
        cookie = self.session.cookies.get_dict()
        return cookie.get('XSRF-TOKEN')
    
    def gn_insert_metadata(self, layer, abstract, ws, layer_info, ds_type, md_record=None):
        #curl -X PUT --header 'Content-Type: application/xml' --header 'Accept: application/json' -d '.........XML_code............'  
        # 'http://localhost:8080/geonetwork/srv/api/0.1/records?metadataType=METADATA&assignToCatalog=true&uuidProcessing=generateUUID&transformWith=_none_'
        url = self.service_url + "/srv/api/0.1/records?metadataType=METADATA&assignToCatalog=true&transformWith=_none_"
        headers = {
            'Content-Type': 'application/xml',
            'Accept': 'application/json',
            'X-XSRF-TOKEN': self.get_csrf_token()
        }
        if not md_record:
            xml = self.create_metadata(layer, abstract, ws, layer_info, ds_type)
            md_record = xml.encode('utf-8')
        r = self.session.put(url, data=md_record, headers=headers)
        
        if r.status_code==201:
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
        csw_response = self.session.post(csw_transaction_url, headers=headers, data=metadata.encode("UTF-8"))
        if csw_response.status_code==200:
            tree = ET.fromstring(csw_response.text)
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
        r = self.session.put(url, headers=headers)
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
        r2 = self.session.get(url2, headers=headers)
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
                value = False
                if (operation['name'] == "view" or operation['name'] == "notify") and idx == 1:
                    value = True
                privi_group['operations'][operation['name']] = value

            privileges["privileges"].append(privi_group)
        
        
        url = self.service_url + "/srv/api/0.1/groups"
        r = self.session.get(url, headers=headers)
        if r.status_code==200:
            response = json.loads(r.text)
            
            #Otros grupos
            for group in response:
                privi_group = {
                    "operations": {
                        },
                    "group": group['id']
                }
                
                for operation in response2:
                    value = False
                    if (operation['name'] == "view" or operation['name'] == "edit" or operation['name'] == "download"):
                        value = True
                    privi_group['operations'][operation['name']] = value
    
                privileges["privileges"].append(privi_group)
        
        
        #url3 = self.service_url + "srv/api/md.privileges.update?_content_type=json&_1_0=on&_1_1=on&_2_0=on&_2_3=on&uuid=" + uuid
        url3 = self.service_url + "/srv/api/0.1/records/"+ uuid +"/sharing"
        headers = {
                'Accept': '*/*',
                'content-type': 'application/json',
                'X-XSRF-TOKEN': self.get_csrf_token()
            }
        r3 = self.session.put(url3, data=json.dumps(privileges), headers=headers)
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
              
        r = self.session.delete(url, headers=headers)
        if r.status_code==204:
            return True
        raise FailedRequestError(r.status_code, r.content)
    
    def getTextFromXMLNode(self, tree, ns, filter):
        aux = tree.findall(filter, ns)
        if aux.__len__() > 0:
            return aux[0].text
        
        return ''
    
    def gn_get_metadata(self, metadata_id):
        #curl -X DELETE --header 'Accept: */*' 'http://localhost:8080/geonetwork/srv/api/0.1/records/159?withBackup=false'
        #NOTE: uuid is an id not in format 97769e85-2e7b-418b-a8c8-0163bfb97aac
        url = self.service_url + "/srv/api/0.1/records/"+str(metadata_id)+""
        print ("Getting metadata from uuid:" + str(metadata_id) + " -> " + url)
        headers = {
            'Accept': 'application/xml',
            'X-XSRF-TOKEN': self.get_csrf_token()
        }
              
        r = self.session.get(url, headers=headers)
        if r.status_code==200:
            tree = ET.fromstring(r.text.encode('utf8'))
            ns = {'gmd': 'http://www.isotc211.org/2005/gmd'}
            
            
            metadata_id = self.getTextFromXMLNode(tree, ns, './gmd:fileIdentifier/')
            title = self.getTextFromXMLNode(tree, ns, './gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:title/')
            abstract = self.getTextFromXMLNode(tree, ns, './gmd:identificationInfo/gmd:MD_DataIdentification/gmd:abstract/')
            publish_date = self.getTextFromXMLNode(tree, ns, './gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:date/gmd:CI_Date/gmd:date/')
            
            period_start = ''
            period_end = ''
            aux = tree.findall('./gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent/gmd:extent/', ns)
            if aux.__len__() > 0:
                period_start = aux[0]._children[0].text
                period_end = aux[0]._children[1].text
            
            categories = []
            for category in tree.findall('./gmd:identificationInfo/gmd:MD_DataIdentification/gmd:topicCategory/gmd:MD_TopicCategoryCode/', ns):
                categories.append(category.text)
            
            keywords = []
            for keyword in tree.findall('./gmd:identificationInfo/gmd:MD_DataIdentification/gmd:descriptiveKeywords/gmd:MD_Keywords/gmd:keyword/', ns):
                keywords.append(keyword.text)
            
            representation_type = ''
            aux = tree.findall('./gmd:identificationInfo/gmd:MD_DataIdentification/gmd:spatialRepresentationType/', ns)
            if aux.__len__() > 0:
                representation_type = aux[0].attrib['codeListValue'] 
            scale = self.getTextFromXMLNode(tree, ns, './gmd:identificationInfo/gmd:MD_DataIdentification/gmd:spatialResolution/gmd:MD_Resolution/gmd:equivalentScale/gmd:MD_RepresentativeFraction/gmd:denominator/') 
            srs = self.getTextFromXMLNode(tree, ns, './gmd:referenceSystemInfo/gmd:MD_ReferenceSystem/gmd:referenceSystemIdentifier/gmd:RS_Identifier/gmd:code/') 
            
            #https://test.gvsigonline.com/geonetwork/srv/spa/region.getmap.png?mapsrs=EPSG:3857&width=250&background=settings&geomsrs=EPSG:4326&geom=Polygon((-18.1595005217%2043.9729489023,4.96320908311%2043.9729489023,4.96320908311%2025.9993588695,-18.1595005217%2025.9993588695,-18.1595005217%2043.9729489023))
            coords_w = self.getTextFromXMLNode(tree, ns, './gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:westBoundLongitude/')
            coords_e = self.getTextFromXMLNode(tree, ns, './gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:eastBoundLongitude/')
            coords_s = self.getTextFromXMLNode(tree, ns, './gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:southBoundLatitude/')
            coords_n = self.getTextFromXMLNode(tree, ns, './gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:northBoundLatitude/')
            
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
                        'url' : thumbnails_urls[i],
                        'name': thumbnail_names[i]
                    }
                    thumbnails.append(thumbnail)
            
            #resources
            resources_urls = []
            for resources_url in tree.findall('./gmd:distributionInfo/gmd:MD_Distribution/gmd:transferOptions/gmd:MD_DigitalTransferOptions/gmd:onLine/gmd:CI_OnlineResource/gmd:linkage/', ns):
                resources_urls.append(resources_url.text)
                
            resources_names = []
            for resources_name in tree.findall('./gmd:distributionInfo/gmd:MD_Distribution/gmd:transferOptions/gmd:MD_DigitalTransferOptions/gmd:onLine/gmd:CI_OnlineResource/gmd:name/', ns):
                resources_names.append(resources_name.text)
                
            resources_protocols = []
            for resources_protocol in tree.findall('./gmd:distributionInfo/gmd:MD_Distribution/gmd:transferOptions/gmd:MD_DigitalTransferOptions/gmd:onLine/gmd:CI_OnlineResource/gmd:protocol/', ns):
                resources_protocols.append(resources_protocol.text)
                
            resources_descriptions = []
            for resources_description in tree.findall('./gmd:distributionInfo/gmd:MD_Distribution/gmd:transferOptions/gmd:MD_DigitalTransferOptions/gmd:onLine/gmd:CI_OnlineResource/gmd:description/', ns):
                resources_descriptions.append(resources_description.text)
            
            resources = []
            if resources_names.__len__() == resources_urls.__len__() and resources_protocols.__len__() == resources_urls.__len__() and resources_descriptions.__len__() == resources_urls.__len__():
                for i in range(0,resources_urls.__len__()):
                    res = {
                        'url' : resources_urls[i],
                        'name': resources_names[i],
                        'protocol': resources_protocols[i],
                        'descriptions' : resources_descriptions[i]
                    }
                    resources.append(res)
            
            
            resource = {
                'metadata_id': metadata_id,
                'title': title,
                'abstract': abstract,
                'publish_date': publish_date,
                'period_start': period_start,
                'period_end': period_end,
                'categories': categories,
                'keywords': keywords,
                'representation_type': representation_type,
                'scale': scale,
                'srs': srs,
                'image_url': image_url,
                'thumbnails': thumbnails,
                'resources': resources
            }
            
            return resource
            #return ET.tostring(tree, encoding='UTF-8')
            #return r.content
        raise FailedRequestError(r.status_code, r.content)
    
    def get_query(self, query):
        url = self.service_url + "/srv/eng/q?" + query
        headers = {
            'Accept': 'application/json',
            'X-XSRF-TOKEN': self.get_csrf_token()
        }
              
        r = self.session.get(url, headers=headers)
        if r.status_code==200:
            return r.content
        raise FailedRequestError(r.status_code, r.content)

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

    def create_metadata(self, layer, abstract, ws, layer_info, ds_type):
        minx, miny, maxx, maxy = self.get_extent(layer_info, ds_type)
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
        metadata +=             '<gmd:graphicOverview><gmd:MD_BrowseGraphic>'
        metadata +=                 '<gmd:fileName>'
        metadata +=                     '<gco:CharacterString>' + layer.thumbnail.url + '</gco:CharacterString>'
        metadata +=                 '</gmd:fileName>'
        metadata +=                 '<gmd:fileDescription>'
        metadata +=                     '<gco:CharacterString>gvsigol thumbnail</gco:CharacterString>'
        metadata +=                 '</gmd:fileDescription>'
        metadata +=             '</gmd:MD_BrowseGraphic></gmd:graphicOverview>'
        metadata +=             '<gmd:extent>'
        metadata +=                 '<gmd:EX_Extent>'
        metadata +=                     '<gmd:geographicElement>'
        metadata +=                         '<gmd:EX_GeographicBoundingBox>'
        metadata +=                             '<gmd:westBoundLongitude>'
        metadata +=                                 '<gco:Decimal>' + minx + '</gco:Decimal>'
        metadata +=                             '</gmd:westBoundLongitude>'
        metadata +=                             '<gmd:eastBoundLongitude>'
        metadata +=                                 '<gco:Decimal>' + maxx + '</gco:Decimal>'
        metadata +=                             '</gmd:eastBoundLongitude>'
        metadata +=                             '<gmd:southBoundLatitude>'
        metadata +=                                 '<gco:Decimal>' + miny + '</gco:Decimal>'
        metadata +=                             '</gmd:southBoundLatitude>'
        metadata +=                             '<gmd:northBoundLatitude>'
        metadata +=                                 '<gco:Decimal>' + maxy + '</gco:Decimal>'
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
        if ds_type:
            if ds_type == 'featureType' and ws.wfs_endpoint:
                metadata +=             '<gmd:onLine>'
                metadata +=                 '<gmd:CI_OnlineResource>'
                metadata +=                     '<gmd:linkage>'
                metadata +=                         '<gmd:URL>' + ws.wfs_endpoint + '</gmd:URL>'
                metadata +=                     '</gmd:linkage>'
                metadata +=                     '<gmd:protocol>'
                metadata +=                         '<gco:CharacterString>OGC:WFS</gco:CharacterString>'
                metadata +=                     '</gmd:protocol>'
                metadata +=                     '<gmd:name>'
                metadata +=                         '<gco:CharacterString>' + ws.name + ':' + layer.name + '</gco:CharacterString>'
                metadata +=                     '</gmd:name>'
                metadata +=                     '<gmd:description>'
                metadata +=                         '<gco:CharacterString>' + layer.title + '</gco:CharacterString>'
                metadata +=                     '</gmd:description>'
                metadata +=                     '<gmd:function><gmd:CI_OnLineFunctionCode codeList="http://standards.iso.org/ittf/PubliclyAvailableStandards/ISO_19139_Schemas/resources/codelist/ML_gmxCodelists.xml#CI_OnLineFunctionCode" codeListValue="download"/></gmd:function>'
                metadata +=                 '</gmd:CI_OnlineResource>'
                metadata +=             '</gmd:onLine>'
            elif ds_type in ('coverage', 'imagemosaic') and ws.wcs_endpoint:
                metadata +=             '<gmd:onLine>'
                metadata +=                 '<gmd:CI_OnlineResource>'
                metadata +=                     '<gmd:linkage>'
                metadata +=                         '<gmd:URL>' + ws.wcs_endpoint + '</gmd:URL>'
                metadata +=                     '</gmd:linkage>'
                metadata +=                     '<gmd:protocol>'
                metadata +=                         '<gco:CharacterString>OGC:WCS</gco:CharacterString>'
                metadata +=                     '</gmd:protocol>'
                metadata +=                     '<gmd:name>'
                metadata +=                         '<gco:CharacterString>' + ws.name + ':' + layer.name + '</gco:CharacterString>'
                metadata +=                     '</gmd:name>'
                metadata +=                     '<gmd:description>'
                metadata +=                         '<gco:CharacterString>' + layer.title + '</gco:CharacterString>'
                metadata +=                     '</gmd:description>'
                metadata +=                     '<gmd:function><gmd:CI_OnLineFunctionCode codeList="http://standards.iso.org/ittf/PubliclyAvailableStandards/ISO_19139_Schemas/resources/codelist/ML_gmxCodelists.xml#CI_OnLineFunctionCode" codeListValue="download"/></gmd:function>'
                metadata +=                 '</gmd:CI_OnlineResource>'
                metadata +=             '</gmd:onLine>'
        metadata +=                 '</gmd:MD_DigitalTransferOptions>'
        metadata +=             '</gmd:transferOptions>'
        metadata +=         '</gmd:MD_Distribution>'
        metadata +=     '</gmd:distributionInfo>'
        
        metadata += '</gmd:MD_Metadata>'
        
        return metadata

    def get_updated_metadata(self, layer, uuid, layer_info, ds_type):
        headers = {
            'Accept': 'application/xml',
            'Content-Type': 'application/xml',
            'X-XSRF-TOKEN': self.get_csrf_token()
        }
        md_url = self.service_url + "/srv/api/0.1/records/" + uuid
        md_response = self.session.get(md_url, headers=headers)
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
