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
import requests
import json
import re
from gvsigol_plugin_catalog.mdstandards import registry
import logging
logger = logging.getLogger("gvsigol")
from .xmlutils import sanitizeXmlText
from urllib.parse import quote, urlparse
from gvsigol_plugin_catalog.settings import GEONETWORK_USE_KEEPALIVE
from gvsigol_plugin_catalog import settings as catalog_settings
from gvsigol_plugin_catalog import gn4_search
from gvsigol_plugin_catalog import oidc_token
import os

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
        self._bearer_token = None
        if not GEONETWORK_USE_KEEPALIVE:
            self._override_headers = {"Connection": "close"}
            self.session.headers.update(self._override_headers)
        else:
            self._override_headers = {}

    def _auth_type(self):
        return (getattr(catalog_settings, 'GEONETWORK_AUTH_TYPE', 'basic') or 'basic').lower()

    def _apply_override_headers(self, headers):
        """Apply global override headers to the given headers"""
        merged = headers.copy()
        csrf = self.get_csrf_token()
        if csrf:
            merged['X-XSRF-TOKEN'] = csrf
        if self._bearer_token:
            merged['Authorization'] = 'Bearer ' + self._bearer_token
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

    def _is_authenticated_me_response(self, response, auth_url):
        """Return True only when GeoNetwork confirms an authenticated user."""
        if '/api/me' in auth_url:
            # Anonymous callers get 204; authenticated users get 200 + JSON body.
            if response.status_code != 200 or not response.content:
                return False
            try:
                payload = response.json()
            except Exception:
                return False
            return bool(payload.get('username') or payload.get('name') or payload.get('id'))
        if response.status_code != 200 or not response.content:
            return False
        return b'authenticated="true"' in response.content or b"authenticated='true'" in response.content

    def _init_csrf_cookie(self, with_auth=False):
        """
        Obtain XSRF-TOKEN (+ session cookie) required by GeoNetwork for PUT/POST/DELETE.

        with_auth=True keeps Authorization/session.auth so the CSRF token matches an
        authenticated session. Required for bearer/OIDC: an anonymous CSRF bootstrap
        often causes 403 on DELETE while PUT/insert may still appear to work.
        """
        init_urls = [
            self.service_url + "/srv/api/me",
            self.service_url + "/srv/eng/info?type=me",
        ]
        for init_url in init_urls:
            headers = self._apply_override_headers(
                {'Accept': 'application/json'} if '/api/me' in init_url else {}
            )
            if not with_auth:
                headers.pop('Authorization', None)
            r = self.session.get(
                init_url,
                headers=headers,
                timeout=get_default_timeout(),
                proxies=settings.PROXIES,
            )
            if r.status_code in (200, 204, 403):
                break

    def _gn_auth_bearer(self, force_refresh=False):
        self.session.auth = None
        try:
            self._bearer_token = oidc_token.get_access_token(force_refresh=force_refresh)
        except Exception:
            logger.exception('Error obtaining GeoNetwork OIDC access token')
            self._bearer_token = None
            return False
        try:
            # Drop previous anonymous session cookies so CSRF matches the bearer session.
            self.session.cookies.clear()
            self._init_csrf_cookie(with_auth=True)
            headers = self._apply_override_headers({'Accept': 'application/json'})
            r = self.session.get(
                self.service_url + "/srv/api/me",
                headers=headers,
                timeout=get_default_timeout(),
                proxies=settings.PROXIES,
            )
            if self._is_authenticated_me_response(r, "/srv/api/me"):
                if not self.get_csrf_token():
                    self._init_csrf_cookie(with_auth=True)
                return True
            # Token may have expired between cache and use; retry once.
            if not force_refresh:
                return self._gn_auth_bearer(force_refresh=True)
            logger.error(
                "GeoNetwork bearer authentication failed: %s %s",
                r.status_code,
                r.text,
            )
            return False
        except Exception:
            logger.exception('Error authenticating with bearer token')
            return False

    def _gn_auth_basic(self, user, password):
        self._bearer_token = None
        self.session.auth = (user, password)
        try:
            self._init_csrf_cookie(with_auth=True)
            headers = self._apply_override_headers({'Accept': 'application/json'})
            auth_urls = [
                self.service_url + "/srv/api/me",
                self.service_url + "/srv/eng/info?type=me",
            ]
            for auth_url in auth_urls:
                req_headers = headers if '/api/me' in auth_url else self._apply_override_headers({})
                r = self.session.request(
                    'GET' if '/api/me' in auth_url else 'POST',
                    auth_url,
                    auth=(user, password),
                    headers=req_headers,
                    timeout=get_default_timeout(),
                    proxies=settings.PROXIES,
                )
                if self._is_authenticated_me_response(r, auth_url):
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

    def gn_auth(self, user, password, force_refresh=False):
        if self._auth_type() == 'bearer':
            return self._gn_auth_bearer(force_refresh=force_refresh)
        return self._gn_auth_basic(user, password)
        
    def gn_unauth(self):
        self.session.auth = None
        self._bearer_token = None
        self.session.headers.pop('Authorization', None)
        
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
        metadata_uuid = getattr(lm, 'metadata_uuid', None) or (lm if isinstance(lm, str) else None)
        metadata_id = getattr(lm, 'metadata_id', None)
        if not metadata_uuid and not metadata_id:
            raise FailedRequestError(400, b'Missing metadata UUID')

        # Refresh CSRF right before mutating calls (important with OIDC/bearer).
        if not self.get_csrf_token():
            self._init_csrf_cookie(with_auth=True)

        quoted = quote(str(metadata_uuid), safe='') if metadata_uuid else None
        paths = []
        if quoted:
            paths.extend([
                "/srv/api/records/" + quoted + "?withBackup=false",
                "/srv/api/records?uuids=" + quoted + "&withBackup=false",
            ])
        if metadata_id:
            paths.extend([
                "/srv/api/records/" + str(metadata_id) + "?withBackup=false",
                "/srv/api/0.1/records/" + str(metadata_id) + "?withBackup=false",
            ])
        headers = self._apply_override_headers({'Accept': 'application/json'})
        success_statuses = (200, 204)
        last_error = None
        for path in paths:
            r = self.session.delete(
                self.service_url + path,
                headers=headers,
                timeout=get_default_timeout(),
                proxies=settings.PROXIES,
            )
            if r.status_code in success_statuses:
                return True
            # Already gone in GeoNetwork: treat as success so local link can be cleaned.
            if r.status_code == 404:
                continue
            last_error = (r.status_code, r.content)
            logger.warning(
                "GeoNetwork metadata delete failed for %s via %s: %s %s",
                metadata_uuid or metadata_id,
                path,
                r.status_code,
                (r.text or '')[:500],
            )
            # Stale CSRF / session: refresh once and retry this path.
            if r.status_code in (401, 403):
                self._init_csrf_cookie(with_auth=True)
                headers = self._apply_override_headers({'Accept': 'application/json'})
                r = self.session.delete(
                    self.service_url + path,
                    headers=headers,
                    timeout=get_default_timeout(),
                    proxies=settings.PROXIES,
                )
                if r.status_code in success_statuses or r.status_code == 404:
                    return True
                last_error = (r.status_code, r.content)
        if last_error:
            raise FailedRequestError(last_error[0], last_error[1])
        # All candidates returned 404 → record already absent.
        return True

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
        """
        Fetch the layer overview thumbnail for catalog cards.

        Prefer the *current* gvSIG Online layer thumbnail (disk), because the URL
        stored in graphicOverview often goes stale (layer recreate, metadata copy,
        media cleanup). Never fall back to GeoNetwork extents.png — that is not
        the layer overview users expect.
        """
        image_bytes = self._layer_thumbnail_bytes_by_uuid(metadata_uuid)
        if image_bytes:
            return image_bytes

        content = self._fetch_metadata_xml(metadata_uuid)
        reader = registry.get_reader(content)
        if reader is not None:
            image_bytes = self._layer_thumbnail_bytes_from_identifier(
                reader.get_resource_identifier()
            )
            if image_bytes:
                return image_bytes
            for overview in reader.get_graphic_overviews() or []:
                url = (overview.get('url') or '').strip()
                if not url:
                    continue
                image_bytes = self._fetch_thumbnail_url(url)
                if image_bytes:
                    return image_bytes

        raise FailedRequestError(404, b'Thumbnail not found')

    def _layer_thumbnail_bytes_by_uuid(self, metadata_uuid):
        try:
            from gvsigol_plugin_catalog.models import LayerMetadata
            lm = (
                LayerMetadata.objects
                .filter(metadata_uuid=metadata_uuid)
                .select_related('layer')
                .first()
            )
            if lm and lm.layer_id:
                return self._read_layer_thumbnail_field(lm.layer)
        except Exception:
            logger.exception(
                'Error resolving layer thumbnail for metadata uuid %s', metadata_uuid
            )
        return None

    def _layer_thumbnail_bytes_from_identifier(self, code):
        try:
            if not code or ':' not in code:
                return None
            workspace_name, layer_name = code.split(':', 1)
            from gvsigol_services.models import Layer
            layer = (
                Layer.objects
                .filter(
                    name=layer_name,
                    datastore__workspace__name=workspace_name,
                )
                .select_related('datastore__workspace')
                .first()
            )
            if layer:
                return self._read_layer_thumbnail_field(layer)
        except Exception:
            logger.exception('Error resolving layer thumbnail from metadata identifier')
        return None

    def _read_layer_thumbnail_field(self, layer):
        """Read bytes from Layer.thumbnail ImageField on disk."""
        try:
            if not layer or not layer.thumbnail:
                return None
            name = getattr(layer.thumbnail, 'name', None) or ''
            if not name or 'no_thumbnail' in name:
                return None
            path = getattr(layer.thumbnail, 'path', None)
            if path and os.path.isfile(path):
                with open(path, 'rb') as handle:
                    data = handle.read()
                if data:
                    return data
            # Fallback: MEDIA_ROOT / thumbnail relative name
            media_root = getattr(settings, 'MEDIA_ROOT', None)
            if media_root and name:
                file_path = os.path.join(media_root, name)
                if os.path.isfile(file_path):
                    with open(file_path, 'rb') as handle:
                        return handle.read()
        except Exception:
            logger.exception(
                'Error reading layer thumbnail for layer id=%s',
                getattr(layer, 'id', None),
            )
        return None

    def _fetch_thumbnail_url(self, url):
        """Download a thumbnail URL (gvSIGOL media or GeoNetwork resource)."""
        if not url:
            return None

        local_bytes = self._read_local_media_thumbnail(url)
        if local_bytes:
            return local_bytes

        absolute = url
        if not (url.startswith('http://') or url.startswith('https://')):
            absolute = self._public_catalog_url(url)

        # Plain GET — gvsigol /media/thumbnails is public; do not send GN Bearer
        try:
            r = requests.get(
                absolute,
                timeout=get_default_timeout(),
                proxies=settings.PROXIES,
                verify=False,
            )
            if r.status_code == 200 and r.content:
                return r.content
            logger.warning(
                'Thumbnail URL returned %s: %s', r.status_code, absolute
            )
        except Exception:
            logger.exception('Error fetching thumbnail URL %s', absolute)

        # GeoNetwork-hosted media/attachments need the authenticated session
        if '/geonetwork/' in absolute or '/srv/api/records/' in absolute:
            try:
                headers = self._apply_override_headers({'Accept': 'image/*'})
                fetch_url = absolute
                parsed_path = urlparse(absolute).path
                service_base = (self.service_url or '').rstrip('/')
                public_base = catalog_settings.CATALOG_BASE_URL.rstrip('/')
                if service_base and public_base and absolute.startswith(public_base):
                    fetch_url = service_base + absolute[len(public_base):]
                elif parsed_path.startswith('/geonetwork/'):
                    suffix = parsed_path.split('/geonetwork', 1)[-1]
                    fetch_url = service_base + suffix
                r = self.session.get(
                    fetch_url,
                    headers=headers,
                    timeout=get_default_timeout(),
                    proxies=settings.PROXIES,
                )
                if r.status_code == 200 and r.content:
                    return r.content
            except Exception:
                logger.exception('Authenticated thumbnail fetch failed for %s', absolute)
        return None

    def _read_local_media_thumbnail(self, url):
        """If URL points to /media/thumbnails/<name>, try reading it from MEDIA_ROOT."""
        try:
            path = urlparse(url).path if '://' in url else url
            marker = '/media/thumbnails/'
            if marker not in path:
                return None
            basename = os.path.basename(path)
            if not basename or basename in ('.', '..'):
                return None
            media_root = getattr(settings, 'MEDIA_ROOT', None)
            if not media_root:
                return None
            file_path = os.path.join(media_root, 'thumbnails', basename)
            if os.path.isfile(file_path):
                with open(file_path, 'rb') as handle:
                    return handle.read()
        except Exception:
            logger.exception('Error reading local media thumbnail for %s', url)
        return None

    def gn_get_metadata_raw(self, metadata_id):
        content = self._fetch_metadata_xml(metadata_id)
        logger.debug('gn_get_metadata_raw: ok')
        return content

    def gn_get_metadata(self, metadata_id):
        logger.debug("Getting metadata from uuid: %s", metadata_id)
        r_content = self._fetch_metadata_xml(metadata_id)
        try:
            reader = registry.get_reader(r_content)
            if reader is None or not hasattr(reader, 'as_catalog_record'):
                raise FailedRequestError(500, b'Unsupported metadata standard')
            resource = reader.as_catalog_record()
            resource['image_url'] = sanitizeXmlText(
                self.gn_get_extent_image_url(metadata_id, width=250)
            )
            for thumbnail in resource.get('thumbnails') or []:
                thumbnail['url'] = gn4_search.public_thumbnail_url(
                    thumbnail.get('url', ''),
                    metadata_id,
                )
            return resource
        except FailedRequestError:
            raise
        except Exception:
            logger.exception('Error parsing metadata XML')
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
        if updater is None:
            raise FailedRequestError(500, b'Unsupported metadata standard')
        thumbnail_url = gn4_search.layer_thumbnail_absolute_url(layer)
        return updater.update_all(extent_tuple, thumbnail_url).tostring()

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
