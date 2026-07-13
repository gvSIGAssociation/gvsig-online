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
@author: jrodrigo <jrodrigo@scolab.es>
'''


from django.shortcuts import render, redirect, HttpResponse
from django.http import HttpResponseRedirect, HttpResponseBadRequest, HttpResponseNotFound, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods, require_safe,require_POST, require_GET
from django.shortcuts import render
import json
from django.views.decorators.csrf import csrf_exempt
import gvsigol_plugin_catalog.service as geonetwork_service
from gvsigol_services.models import Layer
from gvsigol_plugin_catalog.models import LayerMetadata
from gvsigol_auth.utils import staff_required
from django.http import JsonResponse
import logging
from gvsigol_plugin_catalog import settings as catalog_settings
from gvsigol_plugin_catalog.metadata_labels import translate_metadata_code, translate_language_codes
from django.utils.translation import gettext as _
from gvsigol_core import utils as core_utils
import os
from builtins import str as text
from urllib.parse import urlencode

logger = logging.getLogger("gvsigol")

def _json_setting(value, default):
    if value is None or value == '':
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default

@require_GET
def get_catalog_config(request):
    try:
        from gvsigol import settings as gvsigol_settings
        if 'gvsigol_plugin_catalog' not in gvsigol_settings.INSTALLED_APPS:
            return JsonResponse({'error': 'Catalog plugin is not installed'}, status=404)
        custom_filters = {}
        if catalog_settings.CATALOG_CUSTOM_FILTER_URL:
            custom_filters = {'url': catalog_settings.CATALOG_CUSTOM_FILTER_URL}
        return JsonResponse({
            'searchField': catalog_settings.CATALOG_SEARCH_FIELD,
            'facetsConfig': _json_setting(catalog_settings.CATALOG_FACETS_CONFIG, {}),
            'facetsOrder': _json_setting(catalog_settings.CATALOG_FACETS_ORDER, []),
            'disabledFacets': _json_setting(catalog_settings.CATALOG_DISABLED_FACETS, []),
            'queryUrl': catalog_settings.CATALOG_QUERY_URL,
            'baseUrl': catalog_settings.CATALOG_BASE_URL,
            'editorPath': catalog_settings.CATALOG_EDITOR_PATH,
            'metadataViewerButton': catalog_settings.METADATA_VIEWER_BUTTON,
            'disableNavbarMenus': str(catalog_settings.DISABLE_CATALOG_NAVBAR_MENUS).lower() in ('true', '1', 'yes'),
            'customFiltersConfig': custom_filters,
            'resultsPerPage': 20,
        })
    except Exception as e:
        logger.exception(e)
        return JsonResponse({'error': str(e)}, status=500)

def get_query(request):
    geonetwork_instance = geonetwork_service.get_instance()
    if geonetwork_instance!=None and request.method == 'GET':
        try:
            query = urlencode(list(request.GET.lists()), doseq=True)
            response = geonetwork_instance.get_query(query)
            if not response:
                return HttpResponse(
                    json.dumps({'summary': {'@count': 0, 'dimension': []}}),
                    content_type='application/json',
                    status=502,
                )
            if isinstance(response, bytes):
                return HttpResponse(response, content_type='application/json')
            aux_response = json.loads(response)
            return HttpResponse(json.dumps(aux_response), content_type='application/json')
        except Exception as e:
            return HttpResponse(status=500, content=str(e))
        
    return HttpResponse(status=500)

def get_metadata_id(request, layer_ws, layer_name):
    logger.debug('get_metadata_id: '+layer_ws+":"+layer_name)
    response = {}
    response['success'] = False
    
    try:
        if request.method == 'GET':
            layers = Layer.objects.filter(name=layer_name)
            for layer in layers:
                if layer.datastore.workspace.name == layer_ws:
                    layerMetadata = LayerMetadata.objects.filter(layer=layer)
                    if layerMetadata and layerMetadata[0].metadata_uuid != None and layerMetadata[0].metadata_uuid != '':
                        md_response = geonetwork_service.get_instance().get_metadata(layerMetadata[0].metadata_uuid)
                        if isinstance(md_response, dict):
                            response = md_response
                            response['success'] = True
                            response['html']= get_metadata_as_html(response, core_utils.get_iso_language(request).part2b)
                        else:
                            logger.debug(type(response))
    except Exception as e:
        logger.exception(e)
    return HttpResponse(json.dumps(response), content_type='application/json')

@login_required()
@staff_required
@require_http_methods(["POST"])
def create_metadata(request, layer_id):
    if request.method == 'POST':
        try:
            layer = Layer.objects.get(id=int(layer_id))
            result = geonetwork_service.get_instance().metadata_insert(layer)
            if not result:
                return JsonResponse({
                    'status': 'error',
                    'error': 'Could not create metadata in GeoNetwork. Check catalog connection and credentials.'
                }, status=502)
            uuid, the_id = result
            lm, _created = LayerMetadata.objects.get_or_create(layer=layer)
            lm.metadata_id = the_id
            lm.metadata_uuid = uuid
            lm.save()
            return JsonResponse({'status': 'ok', 'uuid': uuid, 'id': the_id})
        except Exception as e:
            logger.exception(e)
            return JsonResponse({'status': 'error', 'error': str(e)}, status=500)

def _build_contact_line(contact):
    organisation = contact.get('organisation')
    if not organisation:
        return ''
    role_label = translate_metadata_code(contact.get('role', 'Contact'))
    line = '<p><span class="catalog_detail_attr">' + role_label + ': </span>' + text(organisation)
    if contact.get('email'):
        line += '&nbsp;&nbsp;<a href="mailto:' + text(contact['email']) + '">' + text(contact['email']) + '</a>'
    if contact.get('phone'):
        line += '&nbsp;&nbsp;<span>' + text(contact['phone']) + '</span>'
    online_resource = contact.get('onlineResource') or {}
    resource_url = online_resource.get('url') or contact.get('url')
    if resource_url:
        resource_name = online_resource.get('name') or resource_url
        line += '&nbsp;&nbsp;<a href="' + text(resource_url) + '" target="_blank" rel="noopener noreferrer" class="fa fa-external-link"> ' + text(resource_name) + '</a>'
    line += '</p>'
    return line


def _build_contacts_section_html(contacts, title):
    contacts_html = ''
    for contact in contacts or []:
        contacts_html += _build_contact_line(contact)
    if contacts_html == '':
        return ''
    return '        <h4 class="modal-catalog-title">' + title + '</h4>' + contacts_html


def _build_constraints_section_html(constraints, title):
    if not constraints:
        return ''
    section_html = ''
    for useLimitation in constraints.get('useLimitations', []):
        if useLimitation:
            section_html += '        <span class="catalog_detail_attr">' + _('Use limitation') + ': </span>' + useLimitation + '<br>'
    for accessConstraint in constraints.get('accessConstraints', []):
        if accessConstraint:
            section_html += '        <span class="catalog_detail_attr">' + _('Access constraint') + ': </span>' + translate_metadata_code(accessConstraint) + '<br>'
    for useConstraint in constraints.get('useConstraints', []):
        if useConstraint:
            section_html += '        <span class="catalog_detail_attr">' + _('Use constraint type') + ': </span>' + translate_metadata_code(useConstraint) + '<br>'
    for otherConstraint in constraints.get('otherConstraints', []):
        if otherConstraint:
            section_html += '        <span class="catalog_detail_attr">' + _('Constraint description') + ': </span>' + otherConstraint + '<br>'
    if section_html == '':
        return ''
    return '        <h4 class="modal-catalog-title">' + title + '</h4>' + section_html


def _build_keywords_section_html(response):
    flat_keywords = [kw for kw in response.get('keywords', []) if kw]
    groups = response.get('keyword_groups', []) or []

    grouped_keywords = set()
    group_lines = []
    for group in groups:
        keywords = [kw for kw in group.get('keywords', []) if kw]
        if not keywords:
            continue
        grouped_keywords.update(keywords)
        label_parts = []
        if group.get('type'):
            label_parts.append(translate_metadata_code(group['type']))
        if group.get('thesaurus'):
            label_parts.append(group['thesaurus'])
        label = ' - '.join(label_parts) if label_parts else ''
        badges = ' '.join('<span class="badge">' + text(kw) + '</span>' for kw in keywords)
        group_lines.append((label, badges))

    orphan_keywords = [kw for kw in flat_keywords if kw not in grouped_keywords]
    if not group_lines and not orphan_keywords:
        return ''

    html = '        <h4 class="modal-catalog-title">' + _('Keywords') + '</h4>'
    if orphan_keywords:
        badges = ' '.join('<span class="badge">' + text(kw) + '</span>' for kw in orphan_keywords)
        html += '        ' + badges + '<br />'
    for label, badges in group_lines:
        if label:
            html += '        <span class="catalog_detail_attr">' + text(label) + ':</span> ' + badges + '<br />'
        else:
            html += '        ' + badges + '<br />'
    return html


def _build_online_services_html(resources):
    services_html = ''
    for resource in resources or []:
        if not resource.get('url'):
            continue
        protocol = resource.get('protocol', '')
        if resource.get('name'):
            res_desc = resource.get('name')
        else:
            res_desc = resource.get('description', _('Resource'))
        base_url = getBaseOgcServiceUrl(resource.get('url'))
        service_type = ''
        capabilities_url = ''
        if 'OGC:WMS' in protocol:
            service_type = 'WMS'
            capabilities_url = text(base_url) + '?service=WMS&request=GetCapabilities'
        elif 'OGC:WFS' in protocol:
            service_type = 'WFS'
            capabilities_url = text(base_url) + '?service=WFS&request=GetCapabilities'
        elif 'OGC:WCS' in protocol:
            service_type = 'WCS'
            capabilities_url = text(base_url) + '?service=WCS&request=GetCapabilities'
        else:
            continue
        services_html += (
            '        <div class="catalog-online-service">'
            + '<button type="button" class="catalog-online-service__copy" data-catalog-copy-url="' + capabilities_url + '" title="' + _('Copy URL') + '" aria-label="' + _('Copy URL') + '">'
            + '<svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor" aria-hidden="true"><path d="M16 1H4a2 2 0 0 0-2 2v14h2V3h12V1zm3 4H8a2 2 0 0 0-2 2v16h11a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2zm0 18H8V7h11v16z"/></svg>'
            + '</button>'
            + '<div class="catalog-online-service__content">'
            + '<strong class="catalog-online-service__type">' + service_type + '</strong>'
            + '<span class="catalog-online-service__name">(' + text(res_desc) + ')</span>'
            + '<a class="catalog-online-service__url" href="' + capabilities_url + '" target="_blank" rel="noopener noreferrer">' + capabilities_url + '</a>'
            + '</div></div>'
        )
    if services_html == '':
        return ''
    return '        <h4 class="modal-catalog-title">' + _('Online services') + '</h4><div class="catalog-online-services">' + services_html + '</div>'


def _format_geographic_extent(response, multiline=False):
    west = response.get('extent_west')
    east = response.get('extent_east')
    south = response.get('extent_south')
    north = response.get('extent_north')
    if not all([west, east, south, north]):
        return ''
    parts = [
        _('West') + ': ' + text(west),
        _('East') + ': ' + text(east),
        _('South') + ': ' + text(south),
        _('North') + ': ' + text(north),
    ]
    if multiline:
        return '<br />'.join(parts)
    return '; '.join(parts)


def _format_technical_value(value, translate=False):
    if not value:
        return ''
    display = translate_metadata_code(value) if translate else value
    if isinstance(display, list):
        display = ', '.join(str(item) for item in display if item)
    return text(display) if display else ''


def _build_technical_info_table(response):
    rows = []

    def add_row(label, value, action_html='', translate=False, label_break=False):
        formatted = _format_technical_value(value, translate=translate)
        if not formatted:
            return
        label_html = text(label) + ':'
        if label_break:
            label_html += '<br />'
        rows.append({
            'label': label_html,
            'value': formatted,
            'action': action_html or '',
        })

    add_row(_('Update frequency'), response.get('update_frequency'), translate=True)
    add_row(_('Resource identifier'), response.get('resource_identifier'))
    add_row(_('Representation type'), response.get('representation_type'), translate=True)
    add_row(_('Language'), ', '.join(translate_language_codes(response.get('languages'))))
    add_row(_('Resource status'), response.get('resource_status'), translate=True)
    add_row(_('Hierarchy level'), response.get('hierarchy_level'), translate=True)
    add_row(_('Character set'), response.get('character_set'), translate=True)
    add_row(_('Distribution format'), response.get('distribution_formats'))
    add_row(_('Purpose'), response.get('purpose'))
    add_row(_('Scale'), response.get('scale') and ('1:' + str(response['scale'])))
    add_row(_('Coordinate Reference System'), response.get('srs'))
    add_row(_('Metadata standard'), response.get('metadata_standard_name'))
    add_row(_('Metadata standard version'), response.get('metadata_standard_version'))
    add_row(_('Metadata date stamp'), response.get('date_stamp'))
    add_row(_('Metadata update frequency'), response.get('metadata_update_frequency'), translate=True)
    add_row(_('Update scope'), response.get('update_scope'), translate=True)

    if response.get('metadata_id'):
        gn_md_url = (
            text(catalog_settings.CATALOG_BASE_URL)
            + text(catalog_settings.CATALOG_EDITOR_PATH)
            + '#/metadata/'
            + response.get('metadata_id', '')
        )
        catalog_btn = (
            '<a class="catalog-tech-table__btn" target="_blank" rel="noopener noreferrer" href="'
            + gn_md_url
            + '">'
            + _('Show in Catalog')
            + '</a>'
        )
        rows.append({
            'label': text(_('Metadata identifier')) + ':',
            'value': text(response.get('metadata_id', '')),
            'action': catalog_btn,
        })

    if not rows:
        return ''

    html = '        <table class="catalog-tech-table">'
    for row in rows:
        html += (
            '            <tr>'
            + '<td class="catalog-tech-table__label">' + row['label'] + '</td>'
            + '<td class="catalog-tech-table__value">' + row['value'] + '</td>'
            + '<td class="catalog-tech-table__action">' + row['action'] + '</td>'
            + '</tr>'
        )
    html += '        </table>'
    return html


def _build_download_links_html(response):
    html = '        <h4 class="modal-catalog-title">' + _('Download and links') + '</h4>'
    resources = '        <ul>'
    if len(response['resources']) > 0:
        for resource in response['resources']:
            if resource.get('name'):
                res_desc = resource.get('name')
            else:
                res_desc = resource.get('description', _('Resource'))
            if res_desc == '' and resource.get('url'):
                res_desc = os.path.basename(resource.get('url'))
                if res_desc == '':
                    res_desc = os.path.basename(os.path.dirname(resource.get('url')))
            if resource.get('url'):
                if resource['protocol'] == 'WWW:DOWNLOAD-1.0-http--download':
                    resources += '            <li><div>' + text(res_desc) + '</div>'
                    resources += '                <a href="' + resource['url'] + '" target="_blank" style="float:right; background-color:#ddd; padding:5px; width:140px; text-align:center">' + _('Access resource') + '</a><div style="clear:both;"></div></li>'
                elif 'OGC:WFS' in resource['protocol']:
                    resources += '            <li><div>' + text(res_desc) + '</div>'
                    resources += '                <a href="' + resource['url'] + '?service=WFS&version=1.0.0&request=GetFeature&typeName=' + text(resource['name']) + '&outputFormat=SHAPE-ZIP" target="_blank" style="float:right; background-color:#ddd; padding:5px; width:140px; text-align:center">' + _('Access resource') + '</a><div style="clear:both;"></div></li>'
                elif 'OGC:' not in resource['protocol']:
                    resources += '            <li><div>' + text(res_desc) + '</div>'
                    resources += '                <a href="' + resource['url'] + '" target="_blank" style="float:right; background-color:#ddd; padding:5px; width:140px; text-align:center">' + _('Access resource') + '</a><div style="clear:both;"></div></li>'
    else:
        resources += '<li><p>' + _('No resources available') + '</p></li>'
    resources += '        </ul>'
    html += resources
    html += '            <div style="clear:both"></div>'
    return html


def _build_temporal_extent_html(response):
    temporal_extent_html = ''
    if response.get('publish_date'):
        temporal_extent_html += '        <span class="catalog_detail_attr">' + _('Publication date') + ':</span>'
        temporal_extent_html += '        ' + response.get('publish_date')
        temporal_extent_html += '        <br />'
    if response.get('period_start'):
        temporal_extent_html += '        <span class="catalog_detail_attr">' + _('Period') + ':</span>'
        temporal_extent_html += '        ' + response['period_start'] + ' - ' + response.get('period_end', '')
        temporal_extent_html += '        <br />'
    if not temporal_extent_html:
        return ''
    return '        <h4 class="modal-catalog-title">' + _('Temporal Extent') + '</h4>' + temporal_extent_html


def _build_catalog_sidebar_html(response):
    """Right column: downloads, spatial extent, temporal extent (legacy gvSIGOL order)."""
    html = '    <div class="col-md-4" style="border: 1px solid #ddd; border-radius: 4px; padding: 20px;">'
    for thumbnail in response.get('thumbnails', []):
        html += '            <img src="' + thumbnail['url'] + '" alt="' + thumbnail['name'] + '" style="width:100%"/><br />'
    html += _build_download_links_html(response)
    html += get_extent_map_html(response)
    html += _build_temporal_extent_html(response)
    html += '    </div>'
    return html


def get_metadata_as_html(response, lang='eng'):
    try:
        if response:
            #http://localhost/gvsigonline/catalog/get_metadata/<metadata_id>/?getPanel=true
            html = '<div class="row" style="padding: 20px;">'
            html += '    <div class="col-md-8">'
            html += '        <h4 class="modal-catalog-title" style="font-weight:bold">'+response.get('title', '')+'</h4>'
            html += '        <p>'+response.get('abstract', '')+'</p>'
             
            if len(response['categories'])>0:
                html += '        <span class="catalog_detail_attr">'+_('Categories')+':</span>'
                categories = ", ".join(translate_metadata_code(category) for category in response['categories'])
                html += '        '+ categories
                html += '        <br />'
        
            html += _build_keywords_section_html(response)

            html += _build_contacts_section_html(response['contacts'].get('resource_contacts'), _('Resource Contacts'))
            html += _build_contacts_section_html(response['contacts'].get('metadata_contacts'), _('Metadata Contacts'))
            html += _build_contacts_section_html(response['contacts'].get('responsible_parties'), _('Responsible parties'))
            html += _build_contacts_section_html(response['contacts'].get('distributor_contacts'), _('Distributor contacts'))

            html += _build_constraints_section_html(response.get('resource_constraints'), _('Resource constraints'))
            html += _build_constraints_section_html(response.get('metadata_constraints'), _('Metadata constraints'))
         
            html += '        <h4 class="modal-catalog-title">' + _('Technical information') + '</h4>'
            html += _build_technical_info_table(response)
            html += _build_online_services_html(response.get('resources', []))
                     
            html += '    </div>'

            html += _build_catalog_sidebar_html(response)
            html += '</div>'
             
            return html     
    except Exception as e:
        logger.exception(e)
        #print e
        
    html = '<div class="row" style="padding: 20px;">'
    html += '    <div class="col-md-8">'
    html += '        <h4 class="modal-catalog-title" style="font-weight:bold">' + _('Metadata detail not available') + '</h4>'
    html += '    </div>'
    html += '</div>'
    return html

def get_metadata(request, layer_id):
    try:
        theId = int(layer_id)
        lm = LayerMetadata.objects.get(id=theId)
        if lm.metadata_uuid:
            return get_metadata_from_uuid(request, lm.metadata_uuid)
    except Exception:
        if layer_id:
            return get_metadata_from_uuid(request, layer_id)
    return HttpResponse(status=500)

def get_metadata_from_uuid(request, metadata_uuid):
    # FIXME: we should only query using admin user if the user is admin or staff
    geonetwork_instance = geonetwork_service.get_instance()
    if geonetwork_instance != None and request.method == 'GET':
        try:
            parameters = request.GET
            if 'sharing' in parameters:
                sharing = True
            else:
                sharing = False
            
            if not sharing:
                metadataJsonSummary = geonetwork_instance.get_metadata(metadata_uuid)
                response = {
                    'html': get_metadata_as_html(metadataJsonSummary, core_utils.get_iso_language(request).part2b)
                }
                return  HttpResponse(json.dumps(response, indent=4), content_type='application/json')
            else:
                metadataJsonSummary = geonetwork_instance.get_metadata(metadata_uuid)
                return render(request, 'catalog_details.html', metadataJsonSummary)
            
        except Exception as e:
            logger.exception(e)
            return HttpResponse(status=500, content=str(e))
        
    return HttpResponse(status=500)


def getBaseOgcServiceUrl(url):
    return url.split("?")[0]


def get_extent_map_html(response):
    image_url = response.get('image_url')
    extent_text = _format_geographic_extent(response, multiline=True)
    if not image_url and not extent_text:
        return ''
    html = '        <h4 class="modal-catalog-title">' + _('Spatial Extent') + '</h4>'
    if image_url:
        html += (
            '        <img class="gn-img-thumbnail img-thumbnail gn-img-extent catalog-extent-map" '
            'src="' + text(image_url) + '" style="width:100%"/><br />'
        )
    if extent_text:
        html += '        <span class="catalog_detail_attr">' + _('Geographic bounding box') + ':</span><br />'
        html += '        ' + extent_text
        html += '        <br />'
    return html


def get_extent_image(request, metadata_uuid):
    """Proxy GeoNetwork extents.png — image is always generated by GN API."""
    geonetwork_instance = geonetwork_service.get_instance()
    if geonetwork_instance is None or request.method != 'GET':
        return HttpResponse(status=503)
    width = request.GET.get('width', '250')
    background = request.GET.get('background', 'settings')
    mapsrs = request.GET.get('mapsrs', 'EPSG:3857')
    try:
        xmlapi = geonetwork_instance.xmlapi
        if xmlapi.gn_auth(geonetwork_instance.user, geonetwork_instance.password):
            try:
                content = xmlapi.gn_fetch_extent_image(
                    metadata_uuid,
                    width=width,
                    background=background,
                    mapsrs=mapsrs,
                )
                response = HttpResponse(content, content_type='image/png')
                response['Cache-Control'] = 'public, max-age=3600'
                return response
            finally:
                xmlapi.gn_unauth()
    except Exception as e:
        logger.exception(e)
    return HttpResponse(status=404)


def get_thumbnail(request, metadata_uuid):
    """Proxy metadata thumbnail for browser display."""
    geonetwork_instance = geonetwork_service.get_instance()
    if geonetwork_instance is None or request.method != 'GET':
        return HttpResponse(status=503)
    try:
        xmlapi = geonetwork_instance.xmlapi
        if xmlapi.gn_auth(geonetwork_instance.user, geonetwork_instance.password):
            try:
                content = xmlapi.gn_fetch_thumbnail(metadata_uuid)
                response = HttpResponse(content, content_type='image/png')
                response['Cache-Control'] = 'public, max-age=3600'
                return response
            finally:
                xmlapi.gn_unauth()
    except Exception as e:
        logger.exception(e)
    return HttpResponse(status=404)
