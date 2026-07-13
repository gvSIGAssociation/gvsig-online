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
from .xmlutils import getTextFromXMLNode, getXMLNode, getXMLCodeText, sanitizeXmlText
from urllib.parse import quote
from gvsigol_plugin_catalog.settings import GEONETWORK_USE_KEEPALIVE
from gvsigol_plugin_catalog import settings as catalog_settings
from gvsigol_plugin_catalog import gn4_search

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
        if not GEONETWORK_USE_KEEPALIVE:
            self._override_headers = {"Connection": "close"}
            self.session.headers.update(self._override_headers)
        else:
            self._override_headers = {}

    def _apply_override_headers(self, headers):
        """Apply global override headers to the given headers"""
        merged = headers.copy()
        merged['X-XSRF-TOKEN'] = self.get_csrf_token()
        merged.update(self._override_headers)
        return merged
        
    def get_session(self):
        return self.session
    
    def get_service_url(self):
        return self.service_url
    
    def get_auth(self):
        return self.session.auth

    def _request_json(self, method, paths, headers=None, data=None, accepted_statuses=(200,)):
        headers = self._apply_override_headers(headers or {})
        last_error = None
        for path in paths:
            url = self.service_url + path
            response = self.session.request(
                method,
                url,
                headers=headers,
                data=data,
                timeout=get_default_timeout(),
                proxies=settings.PROXIES,
            )
            if response.status_code in accepted_statuses:
                if response.content:
                    return response.json()
                return {}
            if response.status_code != 404:
                last_error = (response.status_code, response.content)
        if last_error:
            raise FailedRequestError(last_error[0], last_error[1])
        return None

    def gn_auth(self, user, password):
        self.session.auth = (user, password)
        try:
            init_urls = [
                self.service_url + "/srv/api/me",
                self.service_url + "/srv/eng/info?type=me",
            ]
            for init_url in init_urls:
                r = self.session.get(
                    init_url,
                    timeout=get_default_timeout(),
                    proxies=settings.PROXIES,
                )
                if r.status_code in (200, 403):
                    break

            headers = self._apply_override_headers({})
            auth_urls = [
                self.service_url + "/srv/api/me",
                self.service_url + "/srv/eng/info?type=me",
            ]
            for auth_url in auth_urls:
                r = self.session.request(
                    'GET' if '/api/me' in auth_url else 'POST',
                    auth_url,
                    auth=(user, password),
                    headers=headers,
                    timeout=get_default_timeout(),
                    proxies=settings.PROXIES,
                )
                if r.status_code == 200:
                    return True
            logger.error(
                "GeoNetwork authentication failed: %s %s",
                r.status_code,
                r.text,
            )
            return False
        except Exception as e:
            logger.exception('Error authenticating')
            print(str(e))
            return False
        
    def gn_unauth(self):
        self.session.auth = None
        
    def get_csrf_token(self):
        cookie = self.session.cookies.get_dict()
        return cookie.get('XSRF-TOKEN')
    
    def _parse_insert_metadata_response(self, response):
        uuid = None
        id = None
        if response.get('uuid'):
            uuid = response.get('uuid')
            id = response.get('id') or response.get('metadataId')
        if 'metadataInfos' in response:
            for idx, infos in response['metadataInfos'].items():
                id = id or idx
                if infos:
                    if infos[0].get('uuid'):
                        uuid = infos[0]['uuid']
                    else:
                        message = infos[0].get('message', '')
                        uuids = re.findall(r"'([^']*)'", message)
                        if uuids:
                            uuid = uuids[0]
                break
        if uuid:
            return [uuid, id or uuid]
        return None

    def gn_insert_metadata(self, md_record):
        #curl -X PUT --header 'Content-Type: application/xml' --header 'Accept: application/json' -d '.........XML_code............'
        paths = [
            "/srv/api/records?metadataType=METADATA&assignToCatalog=true&uuidProcessing=GENERATEUUID&transformWith=_none_",
            "/srv/api/0.1/records?metadataType=METADATA&assignToCatalog=true&uuidProcessing=GENERATEUUID&transformWith=_none_",
        ]
        headers = self._apply_override_headers({
            'Content-Type': 'application/xml',
            'Accept': 'application/json'
        })
        last_error = None
        for path in paths:
            url = self.service_url + path
            r = self.session.put(url, data=md_record.encode("UTF-8"), headers=headers, timeout=get_default_timeout(), proxies=settings.PROXIES)
            if r.status_code == 201:
                response = json.loads(r.text)
                result = self._parse_insert_metadata_response(response)
                if result:
                    return result
            if r.status_code != 404:
                raise FailedRequestError(r.status_code, r.content)
            last_error = (r.status_code, r.content)
        if last_error:
            raise FailedRequestError(last_error[0], last_error[1])
        raise FailedRequestError(404, b'GeoNetwork records API not found')

    def csw_update_metadata(self, uuid, updated_xml_md):
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
        headers = self._apply_override_headers({
            'Accept': 'application/xml',
            'Content-Type': 'application/xml'
        })
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
        quoted = quote(str(uuid), safe='')
        encoded_url = quote(thumbnail_url, safe='')
        paths = [
            "/srv/api/records/" + quoted + "/attachments?url=" + encoded_url,
            "/srv/api/0.1/records/" + quoted + "/attachments?url=" + encoded_url,
        ]
        headers = self._apply_override_headers({})
        for path in paths:
            r = self.session.put(
                self.service_url + path,
                headers=headers,
                timeout=get_default_timeout(),
                proxies=settings.PROXIES,
            )
            if r.status_code == 201:
                return True
            if r.status_code != 404:
                raise FailedRequestError(r.status_code, r.content)
        return False
  
    
    def _set_metadata_privileges_gn4(self, uuid):
        """GeoNetwork 4.x: publish record for the All group."""
        quoted = quote(str(uuid), safe='')
        headers = self._apply_override_headers({'Accept': 'application/json'})
        publish_url = self.service_url + "/srv/api/records/" + quoted + "/publish"
        r = self.session.put(
            publish_url,
            headers=headers,
            timeout=get_default_timeout(),
            proxies=settings.PROXIES,
        )
        if r.status_code in (200, 204):
            return True
        logger.warning(
            'GeoNetwork publish failed for %s: %s %s',
            uuid,
            r.status_code,
            r.text,
        )
        return False

    def set_metadata_privileges(self, uuid):
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }
        privileges = {"privileges": []}
        response2 = self._request_json(
            'GET',
            ["/srv/api/0.1/operations", "/srv/api/operations"],
            headers=headers,
        )
        if not response2:
            return self._set_metadata_privileges_gn4(uuid)

        idxs = [-1, 0, 1]
        for idx in idxs:
            privi_group = {"operations": {}, "group": idx}
            for operation in response2:
                allow_operation = operation['name'] in ("view", "dynamic", "download")
                privi_group['operations'][operation['name']] = allow_operation
            privileges["privileges"].append(privi_group)

        groups = self._request_json(
            'GET',
            ["/srv/api/0.1/groups", "/srv/api/groups"],
            headers=headers,
        ) or []
        for group in groups:
            privi_group = {"operations": {}, "group": group['id']}
            for operation in response2:
                allow_operation = operation['name'] in ("view", "dynamic", "download")
                privi_group['operations'][operation['name']] = allow_operation
            privileges["privileges"].append(privi_group)

        quoted = quote(str(uuid), safe='')
        sharing_paths = [
            "/srv/api/records/" + quoted + "/sharing",
            "/srv/api/0.1/records/" + quoted + "/sharing",
        ]
        put_headers = self._apply_override_headers({
            'Accept': '*/*',
            'Content-Type': 'application/json',
        })
        for path in sharing_paths:
            r = self.session.put(
                self.service_url + path,
                data=json.dumps(privileges),
                headers=put_headers,
                timeout=get_default_timeout(),
                proxies=settings.PROXIES,
            )
            if r.status_code == 204:
                return True
            if r.status_code not in (404, 400):
                logger.warning('Sharing update failed: %s %s', r.status_code, r.text)
        return self._set_metadata_privileges_gn4(uuid)
    
    def gn_delete_metadata(self, lm):
        metadata_uuid = lm.metadata_uuid
        if not metadata_uuid:
            raise FailedRequestError(400, b'Missing metadata UUID')
        quoted = quote(str(metadata_uuid), safe='')
        paths = [
            "/srv/api/records/" + quoted + "?withBackup=false",
        ]
        if lm.metadata_id:
            paths.append(
                "/srv/api/0.1/records/" + str(lm.metadata_id) + "?withBackup=false"
            )
        headers = self._apply_override_headers({'Accept': 'application/json'})
        last_error = None
        for path in paths:
            r = self.session.delete(
                self.service_url + path,
                headers=headers,
                timeout=get_default_timeout(),
                proxies=settings.PROXIES,
            )
            if r.status_code == 204:
                return True
            if r.status_code != 404:
                last_error = (r.status_code, r.content)
        if last_error:
            raise FailedRequestError(last_error[0], last_error[1])
        raise FailedRequestError(404, b'Metadata record not found')
    
   
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
        roleNode = node.find('./gmd:role/gmd:CI_RoleCode', ns)
        role = getXMLCodeText(roleNode, ns=ns)
        email = getTextFromXMLNode(node, './gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:electronicMailAddress/gco:CharacterString/', ns)
        phone = getTextFromXMLNode(node, './gmd:contactInfo/gmd:CI_Contact/gmd:phone/gmd:CI_Telephone/gmd:voice/gco:CharacterString/', ns)
        url = getTextFromXMLNode(node, './gmd:contactInfo/gmd:CI_Contact/gmd:onlineResource/gmd:CI_OnlineResource/gmd:linkage/gmd:URL/', ns)
        onlineResources = []
        for onlineResourceNode in node.findall('./gmd:contactInfo/gmd:CI_Contact/gmd:onlineResource/gmd:CI_OnlineResource', ns):
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

    def _metadata_xml_paths(self, metadata_id):
        quoted = quote(str(metadata_id), safe='')
        return [
            "/srv/api/records/" + quoted + "/formatters/xml",
            "/srv/api/0.1/records/" + quoted,
            "/srv/api/0.1/records/" + quoted + "/formatters/xml",
        ]

    def _fetch_metadata_xml(self, metadata_id):
        headers = self._apply_override_headers({
            'Accept': 'application/xml'
        })
        last_error = None
        for path in self._metadata_xml_paths(metadata_id):
            url = self.service_url + path
            r = self.session.get(
                url,
                headers=headers,
                timeout=get_default_timeout(),
                proxies=settings.PROXIES,
            )
            if r.status_code == 200:
                return r.content
            if r.status_code != 404:
                last_error = (r.status_code, r.content)
        if last_error:
            raise FailedRequestError(last_error[0], last_error[1])
        raise FailedRequestError(404, b'Metadata record not found')

    def _public_catalog_url(self, path):
        base = catalog_settings.CATALOG_BASE_URL.rstrip('/')
        if not path:
            return base
        if path.startswith('http://') or path.startswith('https://'):
            return path
        if path.startswith('/'):
            return base + path
        return base + '/' + path

    def gn_get_raw_metadata_url(self, metadata_id):
        quoted = quote(str(metadata_id), safe='')
        return self._public_catalog_url(
            "/srv/api/records/" + quoted + "/formatters/xml"
        )

    def gn_get_extent_image_url(self, metadata_uuid, width=250):
        """Browser-facing URL for the gvSIGOL extent image proxy."""
        quoted = quote(str(metadata_uuid), safe='')
        url = '/gvsigonline/catalog/get_extent_image/' + quoted + '/'
        if width:
            url += '?width=' + str(width)
        return url

    def gn_fetch_extent_image(self, metadata_uuid, width=None, geometry_index=None,
                              background='settings', mapsrs='EPSG:3857'):
        """
        Fetch the spatial extent preview from GeoNetwork 4.x API
        (GET /srv/api/records/{uuid}/extents.png).
        GN 4.2 only accepts width OR height, not both.
        """
        quoted = quote(str(metadata_uuid), safe='')
        if geometry_index is not None:
            path = '/srv/api/records/' + quoted + '/extents/' + str(geometry_index) + '.png'
        else:
            path = '/srv/api/records/' + quoted + '/extents.png'
        params = {}
        if background:
            params['background'] = background
        if mapsrs:
            params['mapsrs'] = mapsrs
        if width:
            params['width'] = width
        headers = self._apply_override_headers({'Accept': 'image/png'})
        r = self.session.get(
            self.service_url + path,
            headers=headers,
            params=params,
            timeout=get_default_timeout(),
            proxies=settings.PROXIES,
        )
        if r.status_code == 200:
            return r.content
        raise FailedRequestError(r.status_code, r.content)

    def gn_fetch_thumbnail(self, metadata_uuid):
        """Fetch thumbnail bytes for proxying to the browser."""
        content = self._fetch_metadata_xml(metadata_uuid)
        tree = ET.fromstring(content)
        ns = {'gmd': 'http://www.isotc211.org/2005/gmd', 'gco': 'http://www.isotc211.org/2005/gco'}
        for browseGraphic in tree.findall(
            './gmd:identificationInfo/gmd:MD_DataIdentification/gmd:graphicOverview/gmd:MD_BrowseGraphic',
            ns,
        ):
            url_node = browseGraphic.find('gmd:fileName/gco:CharacterString', ns)
            if url_node is None or not url_node.text:
                continue
            public_url = gn4_search.public_thumbnail_url(url_node.text, metadata_uuid)
            if public_url.startswith('http://') or public_url.startswith('https://'):
                r = requests.get(
                    public_url,
                    timeout=get_default_timeout(),
                    proxies=settings.PROXIES,
                    verify=False,
                )
                if r.status_code == 200:
                    return r.content
            gn_url = self._public_catalog_url(url_node.text)
            headers = self._apply_override_headers({'Accept': 'image/*'})
            r = self.session.get(
                gn_url,
                headers=headers,
                timeout=get_default_timeout(),
                proxies=settings.PROXIES,
            )
            if r.status_code == 200:
                return r.content
        raise FailedRequestError(404, b'Thumbnail not found')

    def gn_get_metadata_raw(self, metadata_id):
        content = self._fetch_metadata_xml(metadata_id)
        logger.debug('gn_get_metadata_raw: ok')
        return content

    def _parse_publication_date(self, tree, ns):
        for date_elem in tree.findall(
            './gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:date/gmd:CI_Date',
            ns,
        ):
            date_type_node = date_elem.find('./gmd:dateType/gmd:CI_DateTypeCode', ns)
            date_type = sanitizeXmlText(getXMLCodeText(date_type_node, ns=ns)) if date_type_node is not None else ''
            if date_type and date_type != 'publication':
                continue
            date_value = getTextFromXMLNode(date_elem, './gmd:date/', ns)
            if date_value:
                return sanitizeXmlText(date_value)
        return sanitizeXmlText(getTextFromXMLNode(
            tree,
            './gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:date/gmd:CI_Date/gmd:date/',
            ns,
        ))

    def _parse_update_frequency(self, tree, ns):
        freq_paths = [
            './gmd:identificationInfo/gmd:MD_DataIdentification/gmd:resourceMaintenance/gmd:MD_MaintenanceInformation/gmd:maintenanceAndUpdateFrequency/gmd:MD_MaintenanceFrequencyCode',
            './gmd:metadataMaintenance/gmd:MD_MaintenanceInformation/gmd:maintenanceAndUpdateFrequency/gmd:MD_MaintenanceFrequencyCode',
        ]
        for path in freq_paths:
            freq_node = tree.find(path, ns)
            if freq_node is not None:
                value = sanitizeXmlText(getXMLCodeText(freq_node, ns=ns))
                if value:
                    return value
        return ''

    def _parse_resource_identifier(self, tree, ns):
        return sanitizeXmlText(getTextFromXMLNode(
            tree,
            './gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:identifier/gmd:MD_Identifier/gmd:code/',
            ns,
        ))

    def _parse_languages(self, tree, ns):
        languages = []
        language_paths = [
            './gmd:language',
            './gmd:identificationInfo/gmd:MD_DataIdentification/gmd:language',
        ]
        for path in language_paths:
            for lang_node in tree.findall(path, ns):
                code_node = lang_node.find('./gmd:LanguageCode', ns)
                if code_node is not None:
                    value = sanitizeXmlText(getXMLCodeText(code_node, ns=ns))
                else:
                    value = sanitizeXmlText(getTextFromXMLNode(lang_node, './gco:CharacterString', ns))
                if value and value not in languages:
                    languages.append(value)
        return languages

    def _parse_geographic_place(self, tree, ns):
        places = []
        extent_desc = getTextFromXMLNode(
            tree,
            './gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:description/gco:CharacterString',
            ns,
        )
        if extent_desc:
            places.append(sanitizeXmlText(extent_desc))
        for geo_desc in tree.findall(
            './gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicDescription',
            ns,
        ):
            code = getTextFromXMLNode(geo_desc, './gmd:geographicIdentifier/gmd:MD_Identifier/gmd:code/', ns)
            if code:
                sanitized = sanitizeXmlText(code)
                if sanitized not in places:
                    places.append(sanitized)
        for geo_desc in tree.findall(
            './gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicDescription',
            ns,
        ):
            code = getTextFromXMLNode(geo_desc, './gmd:geographicIdentifier/gmd:MD_Identifier/gmd:code/', ns)
            if code:
                sanitized = sanitizeXmlText(code)
                if sanitized not in places:
                    places.append(sanitized)
        for kw_block in tree.findall(
            './gmd:identificationInfo/gmd:MD_DataIdentification/gmd:descriptiveKeywords/gmd:MD_Keywords',
            ns,
        ):
            type_node = kw_block.find('./gmd:type/gmd:MD_KeywordTypeCode', ns)
            if type_node is None or sanitizeXmlText(getXMLCodeText(type_node, ns=ns)) != 'place':
                continue
            for keyword in kw_block.findall('./gmd:keyword/gco:CharacterString', ns):
                if keyword.text and keyword.text.strip():
                    sanitized = sanitizeXmlText(keyword.text)
                    if sanitized not in places:
                        places.append(sanitized)
        return places

    def _parse_resource_status(self, tree, ns):
        status_node = tree.find(
            './gmd:identificationInfo/gmd:MD_DataIdentification/gmd:status/gmd:MD_ProgressCode',
            ns,
        )
        if status_node is None:
            return ''
        return sanitizeXmlText(getXMLCodeText(status_node, ns=ns))

    def _parse_hierarchy_level(self, tree, ns):
        level_node = tree.find('./gmd:hierarchyLevel/gmd:MD_ScopeCode', ns)
        if level_node is None:
            return ''
        return sanitizeXmlText(getXMLCodeText(level_node, ns=ns))

    def _parse_character_set(self, tree, ns):
        charset_paths = [
            './gmd:identificationInfo/gmd:MD_DataIdentification/gmd:characterSet/gmd:MD_CharacterSetCode',
            './gmd:characterSet/gmd:MD_CharacterSetCode',
        ]
        for path in charset_paths:
            charset_node = tree.find(path, ns)
            if charset_node is not None:
                value = sanitizeXmlText(getXMLCodeText(charset_node, ns=ns))
                if value:
                    return value
        return ''

    def _parse_distribution_formats(self, tree, ns):
        formats = []
        for fmt in tree.findall(
            './gmd:distributionInfo/gmd:MD_Distribution/gmd:distributionFormat/gmd:MD_Format',
            ns,
        ):
            name = getTextFromXMLNode(fmt, './gmd:name/gco:CharacterString', ns)
            version = getTextFromXMLNode(fmt, './gmd:version/gco:CharacterString', ns)
            if not name:
                continue
            label = sanitizeXmlText(name)
            if version:
                label += ' (' + sanitizeXmlText(version) + ')'
            if label not in formats:
                formats.append(label)
        return formats

    def _parse_purpose(self, tree, ns):
        return sanitizeXmlText(getTextFromXMLNode(
            tree,
            './gmd:identificationInfo/gmd:MD_DataIdentification/gmd:purpose/gco:CharacterString',
            ns,
        ))

    def _parse_contacts_from_xpath(self, tree, xpath, ns):
        contacts = []
        for party_wrapper in tree.findall(xpath, ns):
            party_node = party_wrapper
            if not party_wrapper.tag.endswith('CI_ResponsibleParty'):
                party_node = party_wrapper.find('./gmd:CI_ResponsibleParty', ns)
            if party_node is None:
                continue
            party = self._getResponsibleParty(party_node, ns)
            organisation = party.get('organisationName') or party.get('individualName')
            if not organisation:
                continue
            online_resource = None
            for online_resource_node in party_node.findall(
                './gmd:contactInfo/gmd:CI_Contact/gmd:onlineResource/gmd:CI_OnlineResource',
                ns,
            ):
                online_resource = self._getOnlineResource(online_resource_node, ns)
                if online_resource.get('url'):
                    break
            contacts.append({
                'organisation': sanitizeXmlText(organisation),
                'role': sanitizeXmlText(party.get('role', '')),
                'email': sanitizeXmlText(party.get('email', '')),
                'phone': sanitizeXmlText(party.get('phone', '')),
                'url': sanitizeXmlText(party.get('url', '')),
                'onlineResource': online_resource,
            })
        return contacts

    def _parse_metadata_standard_name(self, tree, ns):
        return sanitizeXmlText(getTextFromXMLNode(tree, './gmd:metadataStandardName/gco:CharacterString', ns))

    def _parse_metadata_standard_version(self, tree, ns):
        return sanitizeXmlText(getTextFromXMLNode(tree, './gmd:metadataStandardVersion/gco:CharacterString', ns))

    def _parse_date_stamp(self, tree, ns):
        return sanitizeXmlText(getTextFromXMLNode(tree, './gmd:dateStamp/gco:DateTime', ns))

    def _parse_metadata_update_frequency(self, tree, ns):
        freq_node = tree.find(
            './gmd:metadataMaintenance/gmd:MD_MaintenanceInformation/gmd:maintenanceAndUpdateFrequency/gmd:MD_MaintenanceFrequencyCode',
            ns,
        )
        if freq_node is None:
            return ''
        return sanitizeXmlText(getXMLCodeText(freq_node, ns=ns))

    def _parse_update_scope(self, tree, ns):
        scope_node = tree.find(
            './gmd:identificationInfo/gmd:MD_DataIdentification/gmd:resourceMaintenance/gmd:MD_MaintenanceInformation/gmd:updateScope/gmd:MD_ScopeCode',
            ns,
        )
        if scope_node is None:
            return ''
        return sanitizeXmlText(getXMLCodeText(scope_node, ns=ns))

    def _parse_keyword_groups(self, tree, ns):
        groups = []
        for kw_block in tree.findall(
            './gmd:identificationInfo/gmd:MD_DataIdentification/gmd:descriptiveKeywords/gmd:MD_Keywords',
            ns,
        ):
            keywords = []
            for keyword in kw_block.findall('./gmd:keyword/gco:CharacterString', ns):
                if keyword.text and keyword.text.strip():
                    keywords.append(sanitizeXmlText(keyword.text))
            if not keywords:
                continue
            type_node = kw_block.find('./gmd:type/gmd:MD_KeywordTypeCode', ns)
            keyword_type = sanitizeXmlText(getXMLCodeText(type_node, ns=ns)) if type_node is not None else ''
            thesaurus = getTextFromXMLNode(
                kw_block,
                './gmd:thesaurusName/gmd:CI_Citation/gmd:title/gco:CharacterString',
                ns,
            )
            groups.append({
                'type': keyword_type,
                'keywords': keywords,
                'thesaurus': sanitizeXmlText(thesaurus),
            })
        return groups
    
    def gn_get_metadata(self, metadata_id):
        logger.debug("Getting metadata from uuid: %s", metadata_id)
        record_uuid = metadata_id
        r_content = self._fetch_metadata_xml(metadata_id)
        try:
            tree = ET.fromstring(r_content)
            logger.debug(r_content)
            ns = {'gmd': 'http://www.isotc211.org/2005/gmd', 'gco': 'http://www.isotc211.org/2005/gco'}
                
            metadata_id = getTextFromXMLNode(tree, './gmd:fileIdentifier/', ns)
            title = getTextFromXMLNode(tree, './gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:title/', ns)
            abstract = getTextFromXMLNode(tree, './gmd:identificationInfo/gmd:MD_DataIdentification/gmd:abstract/', ns)
            publish_date = self._parse_publication_date(tree, ns)
            update_frequency = self._parse_update_frequency(tree, ns)
            resource_identifier = self._parse_resource_identifier(tree, ns)
            languages = self._parse_languages(tree, ns)
            geographic_place = self._parse_geographic_place(tree, ns)
            resource_status = self._parse_resource_status(tree, ns)
            hierarchy_level = self._parse_hierarchy_level(tree, ns)
            character_set = self._parse_character_set(tree, ns)
            distribution_formats = self._parse_distribution_formats(tree, ns)
            purpose = self._parse_purpose(tree, ns)
            metadata_standard_name = self._parse_metadata_standard_name(tree, ns)
            metadata_standard_version = self._parse_metadata_standard_version(tree, ns)
            date_stamp = self._parse_date_stamp(tree, ns)
            metadata_update_frequency = self._parse_metadata_update_frequency(tree, ns)
            update_scope = self._parse_update_scope(tree, ns)
            keyword_groups = self._parse_keyword_groups(tree, ns)
            
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
                keyword_text = sanitizeXmlText(keyword.text)
                if keyword_text:
                    keywords.append(keyword_text)
            
            representation_type = ''
            aux = tree.findall('./gmd:identificationInfo/gmd:MD_DataIdentification/gmd:spatialRepresentationType/', ns)
            if len(aux) > 0:
                representation_type = aux[0].attrib['codeListValue'] 
            scale = getTextFromXMLNode(tree, './gmd:identificationInfo/gmd:MD_DataIdentification/gmd:spatialResolution/gmd:MD_Resolution/gmd:equivalentScale/gmd:MD_RepresentativeFraction/gmd:denominator/', ns) 
            srs = getTextFromXMLNode(tree, './gmd:referenceSystemInfo/gmd:MD_ReferenceSystem/gmd:referenceSystemIdentifier/gmd:RS_Identifier/gmd:code/', ns)
            
            coords_w = getTextFromXMLNode(tree, './gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:westBoundLongitude/', ns)
            coords_e = getTextFromXMLNode(tree, './gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:eastBoundLongitude/', ns)
            coords_s = getTextFromXMLNode(tree, './gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:southBoundLatitude/', ns)
            coords_n = getTextFromXMLNode(tree, './gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:northBoundLatitude/', ns)

            image_url = self.gn_get_extent_image_url(record_uuid, width=250)
            
            thumbnails = []
            for browseGraphic in tree.findall('./gmd:identificationInfo/gmd:MD_DataIdentification/gmd:graphicOverview/gmd:MD_BrowseGraphic', ns):
                url_node = browseGraphic.find('gmd:fileName/gco:CharacterString', ns)
                if url_node is not None and url_node.text:
                    url = gn4_search.public_thumbnail_url(
                        sanitizeXmlText(url_node.text),
                        record_uuid,
                    )
                    desc_node = browseGraphic.find('gmd:fileDescription/gco:CharacterString', ns)
                    name = sanitizeXmlText(desc_node.text) if desc_node is not None else ''
                    thumbnail = {
                        'url' : url,
                        'name': name
                    }
                    thumbnails.append(thumbnail)
            
            resource_constraints = self._getXMLConstraints(tree, './gmd:identificationInfo/gmd:MD_DataIdentification/gmd:resourceConstraints', ns)
            metadata_constraints = self._getXMLConstraints(tree, './gmd:metadataConstraints', ns)
            
            #resources
            resources = []
            for onlineResourceNode in tree.findall('./gmd:distributionInfo/gmd:MD_Distribution/gmd:transferOptions/gmd:MD_DigitalTransferOptions/gmd:onLine/gmd:CI_OnlineResource', ns):
                onlineResource = self._getOnlineResource(onlineResourceNode, ns)
                resources.append(onlineResource)
            resource_contacts = self._parse_contacts_from_xpath(
                tree,
                './gmd:identificationInfo/gmd:MD_DataIdentification/gmd:pointOfContact',
                ns,
            )
            metadata_contacts = self._parse_contacts_from_xpath(
                tree,
                './gmd:contact',
                ns,
            )
            responsible_parties = self._parse_contacts_from_xpath(
                tree,
                './gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:citedResponsibleParty/gmd:CI_ResponsibleParty',
                ns,
            )
            distributor_contacts = self._parse_contacts_from_xpath(
                tree,
                './gmd:distributionInfo/gmd:MD_Distribution/gmd:distributor/gmd:MD_Distributor/gmd:distributorContact',
                ns,
            )
            contacts = {
                'metadata_contacts': metadata_contacts,
                'resource_contacts': resource_contacts,
                'responsible_parties': responsible_parties,
                'distributor_contacts': distributor_contacts,
            }
            
            resource = {
                'metadata_id': sanitizeXmlText(metadata_id),
                'title': sanitizeXmlText(title),
                'abstract': sanitizeXmlText(abstract),
                'publish_date': sanitizeXmlText(publish_date),
                'update_frequency': sanitizeXmlText(update_frequency),
                'resource_identifier': sanitizeXmlText(resource_identifier),
                'languages': languages,
                'geographic_place': geographic_place,
                'resource_status': sanitizeXmlText(resource_status),
                'hierarchy_level': sanitizeXmlText(hierarchy_level),
                'character_set': sanitizeXmlText(character_set),
                'distribution_formats': distribution_formats,
                'purpose': sanitizeXmlText(purpose),
                'metadata_standard_name': sanitizeXmlText(metadata_standard_name),
                'metadata_standard_version': sanitizeXmlText(metadata_standard_version),
                'date_stamp': sanitizeXmlText(date_stamp),
                'metadata_update_frequency': sanitizeXmlText(metadata_update_frequency),
                'update_scope': sanitizeXmlText(update_scope),
                'keyword_groups': keyword_groups,
                'period_start': sanitizeXmlText(period_start),
                'period_end': sanitizeXmlText(period_end),
                'categories': categories,
                'keywords': keywords,
                'representation_type': sanitizeXmlText(representation_type),
                'scale': sanitizeXmlText(scale),
                'srs': sanitizeXmlText(srs),
                'extent_west': coords_w,
                'extent_east': coords_e,
                'extent_south': coords_s,
                'extent_north': coords_n,
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
        raise FailedRequestError(500, b'Error parsing metadata XML')
    
    def get_query(self, query):
        headers = self._apply_override_headers({
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        })
        content = gn4_search.search(
            self.session,
            self.service_url,
            query,
            headers,
            get_default_timeout(),
            settings.PROXIES,
        )
        if content is not None:
            return content

        api_version = getattr(catalog_settings, 'CATALOG_API_VERSION', 'gn4')
        if api_version in ('gn4', 'api0.1'):
            raise FailedRequestError(502, b'GeoNetwork 4 search failed')

        # Fallback for GeoNetwork 3.x deployments still exposing /srv/eng/q
        url = self.service_url + "/srv/eng/q?" + query
        r = self.session.get(
            url,
            headers=headers,
            timeout=get_default_timeout(),
            proxies=settings.PROXIES,
        )
        if r.status_code == 200:
            return r.content
        logger.debug(url)
        logger.error(r.status_code)
        logger.error(r.content)
        raise FailedRequestError(r.status_code, r.content)

    def get_updated_metadata(self, layer, uuid, layer_info, ds_type):
        md_content = self._fetch_metadata_xml(uuid)
        extent_tuple = self.get_extent(layer_info, ds_type)
        updater = registry.get_updater(md_content)
        return updater.update_all(extent_tuple, layer.thumbnail.url).tostring()

    def get_extent(self, layer_info, ds_type):
        if ds_type == 'imagemosaic':
            ds_type = 'coverage'
        minx = "{:f}".format(float(layer_info[ds_type]['latLonBoundingBox']['minx']))
        miny = "{:f}".format(float(layer_info[ds_type]['latLonBoundingBox']['miny']))
        maxx = "{:f}".format(float(layer_info[ds_type]['latLonBoundingBox']['maxx']))
        if float(layer_info[ds_type]['latLonBoundingBox']['minx']) > float(layer_info[ds_type]['latLonBoundingBox']['maxx']):
            maxx = "{:f}".format(float(layer_info[ds_type]['latLonBoundingBox']['minx']) + 1)
        maxy = str(layer_info[ds_type]['latLonBoundingBox']['maxy'])
        if float(layer_info[ds_type]['latLonBoundingBox']['miny']) > float(layer_info[ds_type]['latLonBoundingBox']['maxy']):
            maxy = "{:f}".format(float(layer_info[ds_type]['latLonBoundingBox']['miny']) + 1)
        return (minx, miny, maxx, maxy)
    
                
    def get_online_resources(self, record_uuid):
        """
        Returns a list of OnlineResource objects, describing the online resources
        encoded in the provided metadata_record_uuid
        """
        quoted = quote(str(record_uuid), safe='')
        paths = [
            "/srv/api/records/" + quoted + "/related?type=onlines",
            "/srv/api/0.1/records/" + quoted + "/related?type=onlines",
        ]
        headers = self._apply_override_headers({'Accept': 'application/json'})
        last_error = None
        for path in paths:
            r = self.session.get(
                self.service_url + path,
                headers=headers,
                timeout=get_default_timeout(),
                proxies=settings.PROXIES,
            )
            if r.status_code == 200:
                return r.json()
            if r.status_code != 404:
                last_error = (r.status_code, r.content)
        if last_error:
            raise FailedRequestError(last_error[0], last_error[1])
        raise FailedRequestError(404, b'Online resources not found')

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
