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
            URL = 'http://localhost:8080/geonetwork/srv/eng/info?type=me'
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
    
    def gn_insert_metadata(self, layer, abstract, ws, layer_info, ds_type):
        #curl -X PUT --header 'Content-Type: application/xml' --header 'Accept: application/json' -d '.........XML_code............'  
        # 'http://localhost:8080/geonetwork/srv/api/0.1/records?metadataType=METADATA&assignToCatalog=true&uuidProcessing=generateUUID&transformWith=_none_'
        url = self.service_url + "0.1/records?metadataType=METADATA&assignToCatalog=true&transformWith=_none_"
        headers = {
            'Content-Type': 'application/xml',
            'Accept': 'application/json',
            'X-XSRF-TOKEN': self.get_csrf_token()
        }
        xml = self.create_metadata(layer, abstract, ws, layer_info, ds_type)
             
        r = self.session.put(url, data=xml.encode('utf-8'), headers=headers)
        
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
        
    
    def add_thumbnail(self, uuid, thumbnail_url):      
        url = self.service_url + "0.1/records/"+uuid+"/attachments?url=" + thumbnail_url
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
        
        url2 = self.service_url + "0.1/operations"
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
        
        
        url = self.service_url + "0.1/groups"
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
        
        
        #url3 = self.service_url + "md.privileges.update?_content_type=json&_1_0=on&_1_1=on&_2_0=on&_2_3=on&uuid=" + uuid
        url3 = self.service_url + "0.1/records/"+ uuid +"/sharing"
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
        url = self.service_url + "0.1/records/"+str(lm.metadata_id)+"?withBackup=false"
        headers = {
            'Accept': 'application/json',
            'X-XSRF-TOKEN': self.get_csrf_token()
        }
              
        r = self.session.delete(url, headers=headers)
        if r.status_code==204:
            return True
        raise FailedRequestError(r.status_code, r.content)
        
    def create_metadata(self, layer, abstract, ws, layer_info, ds_type):
        minx = str(layer_info[ds_type]['latLonBoundingBox']['minx'])
        miny = str(layer_info[ds_type]['latLonBoundingBox']['miny'])
        maxx = str(layer_info[ds_type]['latLonBoundingBox']['maxx'])
        if layer_info[ds_type]['latLonBoundingBox']['minx'] > layer_info[ds_type]['latLonBoundingBox']['maxx']:
            maxx = str(layer_info[ds_type]['latLonBoundingBox']['minx'] + 1)
        maxy = str(layer_info[ds_type]['latLonBoundingBox']['maxy'])
        if layer_info[ds_type]['latLonBoundingBox']['miny'] > layer_info[ds_type]['latLonBoundingBox']['maxy']:
            maxy = str(layer_info[ds_type]['latLonBoundingBox']['miny'] + 1)
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
        metadata +=                                 '<gco:Decimal>' + minx + '</gco:Decimal>'
        metadata +=                             '</gmd:westBoundLongitude>'
        metadata +=                             '<gmd:eastBoundLongitude>'
        metadata +=                                 '<gco:Decimal>' + maxx + '</gco:Decimal>'
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
