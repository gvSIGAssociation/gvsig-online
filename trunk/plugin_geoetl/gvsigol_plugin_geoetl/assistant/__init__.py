# -*- coding: utf-8 -*-
"""Asistente de lenguaje natural para el canvas ETL.

La activación real está en ``access.assistant_feature_enabled``. Este paquete
se puede importar sin GeoCopilot y sin un proveedor configurado.
"""

from .access import assistant_available, assistant_feature_enabled

__all__ = ['assistant_available', 'assistant_feature_enabled']
