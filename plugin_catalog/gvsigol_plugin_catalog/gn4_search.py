# -*- coding: utf-8 -*-
"""
Adapter between gvSIGOL catalog (GeoNetwork 3.x /q JSON format) and
GeoNetwork 4.x Elasticsearch search API.
"""
import json
import logging
import os
import re
from urllib.parse import parse_qs, unquote, urlparse

from gvsigol_plugin_catalog import settings as catalog_settings

logger = logging.getLogger("gvsigol")

# GN3 facet name -> (ES field, human label)
FACET_DEFINITIONS = {
    'type': ('resourceType', 'Type'),
    'spatialRepresentationType': ('cl_spatialRepresentationType.key', 'Representation type'),
    'cat': ('topicCat', 'Categories'),
    '_cat': ('topicCat', 'Categories'),
    'orgName': ('orgName', 'Organisation'),
    'keyword': ('keyword', 'Keywords'),
    'gemetKeyword': ('th_gemetConcept.default', 'GEMET keywords'),
    'createDateYear': ('createDateYear', 'Year'),
    'denominator': ('denominator', 'Scale'),
    'serviceType': ('cl_serviceType.key', 'Service type'),
    'maintenanceAndUpdateFrequency': (
        'cl_maintenanceAndUpdateFrequency.key',
        'Update frequencies',
    ),
    'sourceCatalog': ('sourceCatalog', 'Source catalog'),
    'format': ('format', 'Format'),
}

# GN3 search field -> GN4 ES / Lucene field
SEARCH_FIELD_MAP = {
    'any': 'anytext',
    'title': 'resourceTitleObject.default',
    'abstract': 'resourceAbstractObject.default',
    'keyword': 'tag.default',
    '_cat': 'topicCat',
    'orgName': 'orgName',
}

SORT_MAP = {
    'relevance': [{'_score': {'order': 'desc'}}],
    'changeDate': [{'changeDate': {'order': 'desc'}}],
    'title': [{'resourceTitleObject.default.keyword': {'order': 'asc'}}],
}

AGGREGATION_SIZE = 30


def _first(params, key, default=''):
    values = params.get(key)
    if not values:
        return default
    return values[0]


def _all(params, key):
    return params.get(key, [])


def _parse_bbox_from_wkt(geometry):
    if not geometry:
        return None
    numbers = re.findall(r'[-+]?\d*\.?\d+', geometry)
    if len(numbers) < 4:
        return None
    coords = [float(n) for n in numbers]
    lons = coords[0::2]
    lats = coords[1::2]
    return min(lons), min(lats), max(lons), max(lats)


def _escape_lucene(value):
    return re.sub(r'([+\-=&|><!(){}[\]^"~*?:\\/])', r'\\\1', value or '')


def _build_text_clauses(params):
    """Build Lucene clauses for free-text and field-specific search params."""
    clauses = []
    search_field = _first(params, 'searchField', catalog_settings.CATALOG_SEARCH_FIELD or 'any')
    if search_field not in params and 'any' in params:
        search_field = 'any'

    handled = set()
    for key in (search_field, 'any', 'title', 'abstract', 'keyword', '_cat', 'orgName'):
        if key in handled or key not in params:
            continue
        handled.add(key)
        es_field = SEARCH_FIELD_MAP.get(key, key)
        for value in _all(params, key):
            value = (value or '').strip()
            if not value:
                continue
            if es_field == 'anytext':
                clauses.append(value)
            else:
                clauses.append('%s:(%s)' % (es_field, _escape_lucene(value)))

    if not clauses:
        return '*'

    seen = set()
    unique = []
    for clause in clauses:
        if clause not in seen:
            seen.add(clause)
            unique.append(clause)
    return ' AND '.join(unique)


def _decode_facet_value(value):
    """Facet values are double-encoded in the UI; decode safely."""
    if not value:
        return value
    decoded = unquote(value)
    if '%' in decoded:
        decoded = unquote(decoded)
    return decoded


def _parse_facet_filters(params):
    """
    Parse facet.q values such as 'type/dataset&spatialRepresentationType/vector'.
    Returns list of (facet_name, facet_value).
    """
    facet_q = _first(params, 'facet.q', '').strip()
    if not facet_q:
        return []

    filters = []
    for part in re.split(r'[&;]', facet_q):
        part = part.strip()
        if not part:
            continue
        if '/' not in part:
            continue
        name, value = part.split('/', 1)
        name = unquote(name).strip()
        value = _decode_facet_value(value.strip())
        if name and value:
            filters.append((name, value))
    return filters


def _facet_filter_clause(facet_name, facet_value):
    field = FACET_DEFINITIONS.get(facet_name, (facet_name, facet_name))[0]
    return {'term': {field: {'value': facet_value}}}


def _date_range_filter(field, date_from='', date_to=''):
    if not date_from and not date_to:
        return None
    range_query = {}
    if date_from:
        range_query['gte'] = date_from
    if date_to:
        range_query['lte'] = date_to
    return {'range': {field: range_query}}


def _geo_filter(geometry):
    bbox = _parse_bbox_from_wkt(geometry)
    if not bbox:
        return None
    minx, miny, maxx, maxy = bbox
    return {
        'geo_shape': {
            'geom': {
                'shape': {
                    'type': 'envelope',
                    'coordinates': [[minx, maxy], [maxx, miny]],
                },
                'relation': 'intersects',
            }
        }
    }


def _build_sort(params):
    sort_by = _first(params, 'sortBy', 'relevance')
    sort_order = _first(params, 'sortOrder', '').lower()
    sort = SORT_MAP.get(sort_by, SORT_MAP['relevance'])
    if sort_by == 'title' and sort_order == 'reverse':
        return [{'resourceTitleObject.default.keyword': {'order': 'desc'}}]
    if sort_by == 'changeDate' and sort_order == 'reverse':
        return [{'changeDate': {'order': 'asc'}}]
    return list(sort)


def _build_aggregations():
  aggs = {}
  for facet_name, (es_field, _label) in FACET_DEFINITIONS.items():
      if facet_name.startswith('_'):
          continue
      aggs[facet_name] = {
          'terms': {
              'field': es_field,
              'size': AGGREGATION_SIZE,
          }
      }
  return aggs


def _format_facet_label(value):
    if not value:
        return value
    return value[0].upper() + value[1:]


def _aggregation_to_dimension(facet_name, aggregation):
    buckets = aggregation.get('buckets', [])
    if not buckets:
        return None

    _es_field, default_label = FACET_DEFINITIONS.get(
        facet_name, (facet_name, facet_name)
    )
    categories = []
    for bucket in buckets:
        key = bucket.get('key')
        if key is None:
            continue
        count = bucket.get('doc_count', 0)
        if count <= 0:
            continue
        str_key = str(key)
        categories.append({
            '@name': '%s/%s' % (facet_name, str_key),
            '@label': _format_facet_label(str_key),
            '@count': str(count),
            '@value': str_key,
        })

    if not categories:
        return None

    return {
        '@name': facet_name,
        '@label': default_label,
        'category': categories,
    }


def _translate_aggregations(es_response):
    aggregations = es_response.get('aggregations', {})
    dimensions = []
    for facet_name in FACET_DEFINITIONS:
        if facet_name.startswith('_'):
            continue
        aggregation = aggregations.get(facet_name)
        if not aggregation:
            continue
        dimension = _aggregation_to_dimension(facet_name, aggregation)
        if dimension:
            dimensions.append(dimension)
    return dimensions


def _localised_text(value):
    if isinstance(value, dict):
        return value.get('default') or next(iter(value.values()), '')
    return value or ''


def _resolve_url(url):
    if not url:
        return url
    if url.startswith('http://') or url.startswith('https://'):
        return url
    base = catalog_settings.CATALOG_BASE_URL.rstrip('/')
    if url.startswith('/'):
        return base + url
    return base + '/' + url


def public_thumbnail_url(url, metadata_uuid=None):
    """
    Return a browser-accessible thumbnail URL.
    GN /geonetwork/media/thumbnails/* requires authentication; gvSIGOL serves
    the same files publicly under /media/thumbnails/*.
    """
    if not url:
        return url
    absolute = _resolve_url(url)
    path = urlparse(absolute).path
    if '/media/thumbnails/' in path:
        basename = os.path.basename(path)
        if basename:
            return catalog_settings.BASE_URL.rstrip('/') + '/media/thumbnails/' + basename
    if metadata_uuid:
        return '/gvsigonline/catalog/get_thumbnail/' + metadata_uuid + '/'
    return absolute


def _legacy_link(link, title):
    name = _localised_text(link.get('nameObject'))
    description = _localised_text(link.get('descriptionObject')) or title
    url = _localised_text(link.get('urlObject'))
    protocol = link.get('protocol', '')
    return '|'.join([name, description, url, protocol, protocol, ''])


def _legacy_image(overview, title, metadata_uuid=None):
    url = overview.get('url', '')
    if not url:
        return None
    url = public_thumbnail_url(url, metadata_uuid)
    name = _localised_text(overview.get('nameObject')) or title
    return '|'.join([name, url])


def _legacy_geobox(source):
    geom = source.get('geom') or []
    if not geom:
        return None
    polygon = geom[0]
    if polygon.get('type') != 'Polygon':
        return None
    coords = polygon.get('coordinates', [[]])[0]
    if not coords:
        return None
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return '|'.join([
        str(min(lons)),
        str(max(lons)),
        str(min(lats)),
        str(max(lats)),
    ])


def _hit_to_legacy_metadata(hit):
    source = hit.get('_source', {})
    title = _localised_text(source.get('resourceTitleObject'))
    abstract = _localised_text(source.get('resourceAbstractObject'))
    uuid = source.get('uuid') or source.get('metadataIdentifier')

    links = [_legacy_link(link, title) for link in source.get('link', [])]
    images = [
        img for img in (
            _legacy_image(overview, title, uuid) for overview in source.get('overview', [])
        ) if img
    ]

    metadata = {
        'defaultTitle': title,
        'title': title,
        'name': title,
        'abstract': abstract,
        'geoBox': _legacy_geobox(source),
        'geonet:info': {
            'uuid': uuid,
        },
    }
    if links:
        metadata['link'] = links if len(links) > 1 else links[0]
    if images:
        metadata['image'] = images if len(images) > 1 else images[0]
    return metadata


def build_es_request(query_string):
    params = parse_qs(query_string, keep_blank_values=True)
    from_value = int(_first(params, 'from', '1') or '1')
    to_value = int(_first(params, 'to', str(from_value + 19)) or str(from_value + 19))
    size = max(1, to_value - from_value + 1)

    bool_query = {
        'must': [{
            'query_string': {
                'query': _build_text_clauses(params),
                'default_operator': 'AND',
            }
        }],
        'filter': [
            {'term': {'isTemplate': {'value': 'n'}}},
        ],
    }

    for facet_name, facet_value in _parse_facet_filters(params):
        bool_query['filter'].append(_facet_filter_clause(facet_name, facet_value))

    creation_range = _date_range_filter(
        'createDate',
        _first(params, 'creationDateFrom', ''),
        _first(params, 'creationDateTo', ''),
    )
    if creation_range:
        bool_query['filter'].append(creation_range)

    record_range = _date_range_filter(
        'changeDate',
        _first(params, 'dateFrom', ''),
        _first(params, 'dateTo', ''),
    )
    if record_range:
        bool_query['filter'].append(record_range)

    geo_filter = _geo_filter(_first(params, 'geometry', ''))
    if geo_filter:
        bool_query['filter'].append(geo_filter)

    request = {
        'from': max(0, from_value - 1),
        'size': size,
        'query': {
            'bool': bool_query,
        },
        'sort': _build_sort(params),
        'aggs': _build_aggregations(),
    }
    return request


def translate_es_response(es_response):
    hits = es_response.get('hits', {})
    total = hits.get('total', {})
    if isinstance(total, dict):
        count = total.get('value', 0)
    else:
        count = total or 0

    metadata = [_hit_to_legacy_metadata(hit) for hit in hits.get('hits', [])]
    legacy = {
        'summary': {
            '@count': count,
            'dimension': _translate_aggregations(es_response),
        },
    }
    if len(metadata) == 1:
        legacy['metadata'] = metadata[0]
    elif metadata:
        legacy['metadata'] = metadata
    return legacy


def search(session, service_url, query_string, headers, timeout, proxies):
    es_request = build_es_request(query_string)
    url = service_url + '/srv/api/search/records/_search'
    request_headers = dict(headers or {})
    request_headers.setdefault('Content-Type', 'application/json')
    request_headers.setdefault('Accept', 'application/json')

    response = session.post(
        url,
        data=json.dumps(es_request),
        headers=request_headers,
        timeout=timeout,
        proxies=proxies,
    )
    if response.status_code != 200:
        logger.error(
            'GeoNetwork 4 search failed: %s %s',
            response.status_code,
            response.text,
        )
        return None

    es_response = response.json()
    legacy = translate_es_response(es_response)
    return json.dumps(legacy).encode('utf-8')
