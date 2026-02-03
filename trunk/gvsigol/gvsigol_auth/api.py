# -*- coding: utf-8 -*-

'''
    gvSIG Online.
    Copyright (C) 2025 SCOLAB.

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
from gvsigol_auth import auth_backend
from gvsigol_plugin_baseapi.permissions import IsSuperUser
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response


@api_view(['GET'])
@permission_classes([IsSuperUser])
def get_all_roles(request, *args, **kwargs):
    """
    GET /gvsigonline/auth/get-all-roles/
    Returns all existing roles, e.g. ["role1", "role2"]
    returns 403 si no lo invoca un superusuario
    returns 401 si no está autenticado
    """
    wrapped_data = {"results": auth_backend.get_all_roles_details()}
    return Response(wrapped_data)
