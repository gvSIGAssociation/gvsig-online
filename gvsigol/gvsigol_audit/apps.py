# -*- coding: utf-8 -*-

'''
    gvSIG Online.
    Copyright (C) 2024 SCOLAB.

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

from django.apps import AppConfig


class GvsigolAuditConfig(AppConfig):
    name = 'gvsigol_audit'
    verbose_name = "Sistema de Auditoría de gvSIG Online"
    label = 'gvsigol_audit'

    def ready(self):
        # Registrar vistas del core de gvsigol para auditoría
        try:
            from gvsigol_audit.view_audit_registry import register_core_modules
            from django.conf import settings

            gvsigol_path = getattr(settings, 'GVSIGOL_PATH', 'gvsigonline')
            gvsigol_prefix = f'/{gvsigol_path}/'
            register_core_modules(gvsigol_prefix)
        except Exception:
            # Si hay algún error, ignorar
            pass

