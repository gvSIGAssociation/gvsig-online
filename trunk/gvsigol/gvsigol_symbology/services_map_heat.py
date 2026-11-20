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
@author: Mehdi Jelassia <mjelassia@scolab.es>
'''

from django.db import transaction
from . import conf_builder
from .models import Style, StyleLayer
from . import utils

@transaction.atomic
def create_style(style_name, style_title, is_default, sld, layer, gs, is_preview=False):
    if is_preview:
        style_name = style_name + '__tmp'
    claimed = utils.begin_style_creation(gs, style_name, layer)
    if claimed is False:
        return None
    if claimed is not None:
        return claimed
    is_default = utils.resolve_is_default(layer, is_default, is_preview)

    style = Style(
        name = style_name,
        title = style_title,
        is_default = is_default,
        minscale = -1,
        maxscale = -1,
        type = 'MC',
        sld = sld
    )
    style.save()

    if not is_preview:
        legend_path = utils.check_custom_legend_path()
        legend_name = style.name + ".png"
        legend_url = utils.generate_heatmap_legend_from_sld(legend_path, sld, legend_name)
        if legend_url:
            style.has_custom_legend = True
            style.custom_legend_url = legend_url
            style.save(update_fields=['has_custom_legend', 'custom_legend_url'])

    style_layer = StyleLayer(
        style = style,
        layer = layer
    )
    style_layer.save()

    sld_body = utils.encode_xml(sld)
    return utils.publish_style(gs, layer, style, sld_body, is_preview=is_preview)

@transaction.atomic
def update_style(style_title, is_default, sld, layer, gs, style, is_preview=False):
    is_default = utils.set_default_style(layer, gs, style=style, is_preview=is_preview, is_default=is_default)

    style.sld = sld
    style.title = style_title
    style.is_default = is_default
    style.save()

    if not is_preview:
        legend_path = utils.check_custom_legend_path()
        legend_name = style.name + ".png"
        legend_url = utils.generate_heatmap_legend_from_sld(legend_path, sld, legend_name)
        style.has_custom_legend = bool(legend_url)
        style.custom_legend_url = legend_url if legend_url else None
        style.save(update_fields=['has_custom_legend', 'custom_legend_url'])

    sld_body = utils.encode_xml(sld)

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
    return conf_builder.build_vector_conf(request, layer_id, alphanumeric_list=False, json_numeric=True, ramp_libraries=True)
