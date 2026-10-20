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

from gvsigol_services.backend_postgis import Introspect
import json
import logging

logger = logging.getLogger(__name__)


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def get_fields(resource):
    fields = []
    if resource is None:
        return fields
    try:
        feature_type = resource.get('featureType') or {}
        attributes = feature_type.get('attributes') or {}
        fields = _as_list(attributes.get('attribute'))
    except Exception:
        logger.exception('plugin_charts: unable to read layer fields from GeoServer resource')
        fields = []
    return fields


def get_alphanumeric_fields(fields):
    alphanumeric_fields = []
    for field in fields or []:
        if not isinstance(field, dict):
            continue
        binding = field.get('binding') or ''
        if 'jts.geom' not in binding:
            alphanumeric_fields.append(field)
    return alphanumeric_fields


def get_numeric_fields(fields):
    numeric_fields = []
    for field in fields or []:
        if not isinstance(field, dict):
            continue
        binding = field.get('binding') or ''
        if (binding.startswith('java.math') or
            binding == ('java.lang.Number') or
            binding == ('java.lang.Byte') or
            binding == ('java.lang.Float') or
            binding == ('java.lang.Integer') or
            binding == ('java.lang.Long') or
            binding == ('java.lang.Short') or
            binding == ('java.lang.Double')):
            numeric_fields.append(field)
    return numeric_fields


def get_geometry_fields(fields):
    geom_fields = []
    for field in fields or []:
        if not isinstance(field, dict):
            continue
        binding = field.get('binding') or ''
        if binding.startswith('org.locationtech.jts.geom'):
            geom_fields.append(field)
    return geom_fields


def parse_chart_conf(raw_conf):
    """
    Parse chart.conf safely. Accepts JSON string or already-decoded dict.
    Returns {} on invalid/empty content.
    """
    if raw_conf is None or raw_conf == '':
        return {}
    if isinstance(raw_conf, dict):
        return raw_conf
    try:
        conf = json.loads(raw_conf)
        if isinstance(conf, dict):
            return conf
        # Some clients may double-encode JSON.
        if isinstance(conf, str):
            conf2 = json.loads(conf)
            return conf2 if isinstance(conf2, dict) else {}
    except Exception as exc:
        logger.warning('plugin_charts: invalid chart conf JSON: %s', exc)
    return {}
