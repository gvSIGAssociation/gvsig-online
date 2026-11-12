# -*- coding: utf-8 -*-
"""Señales del core para que los plugins amplíen los formularios sin tocar sus vistas."""
from django.dispatch import Signal

# Tras guardar un proyecto desde project_add / project_update (con sus roles ya guardados).
# Argumentos: project, request, created (bool). Los plugins leen sus propios campos de
# request.POST (los que añaden con project_tab_<plugin>.html).
project_form_saved = Signal()
