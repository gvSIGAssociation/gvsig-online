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

import gvsigol.settings
from gvsigol_auth import auth_backend

def global_settings(request):
    # return any necessary values
    return {
        'GVSIGOL_VERSION': gvsigol.settings.GVSIGOL_VERSION,
        'INSTALLED_APPS': gvsigol.settings.INSTALLED_APPS,
        'GVSIGOL_TOOLS': gvsigol.settings.GVSIGOL_TOOLS,
        'GVSIGOL_ENABLE_ENUMERATIONS': gvsigol.settings.GVSIGOL_ENABLE_ENUMERATIONS,
        'GVSIGOL_SKIN': gvsigol.settings.GVSIGOL_SKIN,
        'GVSIGOL_NAME': gvsigol.settings.GVSIGOL_NAME,
        'GVSIGOL_SURNAME': gvsigol.settings.GVSIGOL_SURNAME,
        'GVSIGOL_NAME_SHORT': gvsigol.settings.GVSIGOL_NAME_SHORT,
        'GVSIGOL_SURNAME_SHORTv': gvsigol.settings.GVSIGOL_SURNAME_SHORT,
        'TEMPORAL_ADVANCED_PARAMETERS': gvsigol.settings.TEMPORAL_ADVANCED_PARAMETERS,
        'PUBLIC_PLUGINS': gvsigol.settings.PUBLIC_PLUGINS,
        'AUTH_GROUPS': auth_backend.check_group_support()
    }