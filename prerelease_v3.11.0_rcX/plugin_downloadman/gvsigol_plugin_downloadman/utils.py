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
@author: Cesar Martinez <cmartinez@scolab.es>
'''
from gvsigol_services.models import Layer
import logging

logger = logging.getLogger("gvsigol")


def getLayer(id_or_uuid):
    try:
        django_id = int(id_or_uuid)
        return Layer.objects.get(id=django_id)
    except:
        try:
            from gvsigol_plugin_catalog.models import LayerMetadata
            lm = LayerMetadata.objects.get(metadata_uuid=id_or_uuid)
            return lm.layer
        except:
            #logger.exception("Error retrieving layer metadata with uuid: " + id_or_uuid)
            pass


def _getParam(params, name):
    for param in params:
        if param.name == name:
            return param