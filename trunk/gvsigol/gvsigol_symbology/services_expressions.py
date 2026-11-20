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
@author: Javi Rodrigo <jrodrigo@scolab.es>
'''

from django.db import transaction
from . import symbolizer_factory, conf_builder
from .models import Style, StyleLayer, Rule, Symbolizer
from . import utils, sld_builder
import json

@transaction.atomic
def create_style(request, json_data, layer, gs, is_preview=False):
    name = json_data.get('name')
    if is_preview:
        name = name + '__tmp'
    claimed = utils.begin_style_creation(gs, name, layer)
    if claimed is False:
        return None
    if claimed is not None:
        return claimed
    is_default = json_data.get('is_default', False)
    is_default = utils.resolve_is_default(layer, is_default, is_preview)

    style = Style(
        name = name,
        title = json_data.get('title'),
        is_default = is_default,
        type = 'EX'
    )
    if json_data.get('minscale') != '':
        style.minscale = json_data.get('minscale')
    else:
        style.minscale = -1
    if json_data.get('maxscale') != '':
        style.maxscale = json_data.get('maxscale')
    else:
        style.maxscale = -1
    style.save()
    style_layer = StyleLayer(
        style = style,
        layer = layer
    )
    style_layer.save()

    for r in json_data.get('rules'):
        json_rule = r.get('rule')

        filter_text = ""
        if json_rule.get('filter').__len__() != 0:
            filter_text = str(json.dumps(json_rule.get('filter')))

        rule = Rule(
            style = style,
            name = json_rule.get('name'),
            title = json_rule.get('title'),
            abstract = '',
            filter = filter_text,
            minscale = json_rule.get('minscale'),
            maxscale = json_rule.get('maxscale'),
            order = json_rule.get('order')
        )
        rule.save()

        for sym in r.get('symbolizers'):
            symbolizer_factory.create_symbolizer_from_json(rule, sym)

    sld_body = sld_builder.build_sld(layer, style)
    return utils.publish_style(gs, layer, style, sld_body, is_preview=is_preview)

@transaction.atomic
def update_style(request, json_data, layer, gs, style, is_preview=False):
    is_default = json_data.get('is_default', False)
    is_default = utils.set_default_style(layer, gs, style=style, is_preview=is_preview, is_default=is_default)

    style.title = json_data.get('title')
    if json_data.get('minscale') != '':
        style.minscale = json_data.get('minscale')
    else:
        style.minscale = -1
    if json_data.get('maxscale') != '':
        style.maxscale = json_data.get('maxscale')
    else:
        style.maxscale = -1
    style.is_default = is_default
    style.save()

    rules = Rule.objects.filter(style=style)
    for ru in rules:
        symbolizers = Symbolizer.objects.filter(rule=ru)
        for symbolizer in symbolizers:
            symbolizer.delete()
        ru.delete()

    for r in json_data.get('rules'):
        json_rule = r.get('rule')

        filter_text = ""
        if json_rule.get('filter').__len__() != 0:

            filter_text = str(json.dumps(json_rule.get('filter')))

        if json_data.get('minscale') != '':
            minscale = json_rule.get('minscale')
        else:
            minscale = -1
        if json_data.get('maxscale') != '':
            maxscale = json_rule.get('maxscale')
        else:
            maxscale = -1

        rule = Rule(
            style = style,
            name = json_rule.get('name'),
            title = json_rule.get('title'),
            abstract = '',
            filter = filter_text,
            minscale = minscale,
            maxscale = maxscale,
            order = json_rule.get('order')
        )
        rule.save()

        for sym in r.get('symbolizers'):
            symbolizer_factory.create_symbolizer_from_json(rule, sym)

    sld_body = sld_builder.build_sld(layer, style)

    if is_preview:
        if gs.createOverwrittenStyle(style.name, sld_body, True): 
            return style
    else:
        if gs.updateStyle(layer, style.name, sld_body): 
            gs.setLayerStyle(layer, style.name, style.is_default)
            return style
        else:
            # try to recover from inconsistent gvsigol - geoserver status
            if utils.reset_geoserver_style(gs, layer, style):
                gs.setLayerStyle(layer, style.name, style.is_default)
                return style

def get_conf(request, layer_id):
    return conf_builder.build_vector_conf(request, layer_id)
